"""One host-wide Google owner, bounded HTTP attempts and safe timing metadata."""
from collections import defaultdict
from concurrent.futures import CancelledError
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import fcntl
import os
from pathlib import Path
import threading
import time
from urllib.parse import urlparse
from scripts.collector_settings import GOOGLE_FLIGHTS_MAX_WORKERS
from scripts.source_recovery import PermanentSourceError

ROOT = Path(__file__).resolve().parents[1]
_lock = threading.RLock()
_condition = threading.Condition(_lock)
_owner = None
_active_google = 0
_process_file = None
LIMITS = {"Google": GOOGLE_FLIGHTS_MAX_WORKERS, "Wizz Air": 2, "Binter": 2, "Canaryfly": 2, "Volotea": 2}
_slots = {p: threading.BoundedSemaphore(n) for p, n in LIMITS.items()}
_metrics = None
_stopped = threading.Event()


def start_metrics(path):
    global _metrics
    with _lock:
        _stopped.clear()
        _metrics = {"path": Path(path), "started_at": datetime.now(timezone.utc).isoformat(),
                    "start": time.monotonic(), "providers": defaultdict(lambda: {
                        "attempts": 0, "errors": 0, "active": 0, "max_in_flight": 0,
                        "seconds": 0.0, "statuses": defaultdict(int)}), "events": []}


def save_metrics(status):
    if _metrics is None:
        return
    from scripts.collection_coverage import atomic_json
    with _lock:
        atomic_json(_metrics["path"], {"status": status, "started_at": _metrics["started_at"],
            "elapsed_seconds": time.monotonic() - _metrics["start"],
            "limits": LIMITS,
            "providers": dict(_metrics["providers"]), "events": _metrics["events"]})


def stop_requests():
    _stopped.set()
    with _condition:
        _condition.notify_all()


def raise_if_stopped():
    if _stopped.is_set():
        raise CancelledError("Source collection stopped after an earlier failure")


def retry_delay(attempt, error=None):
    """Respect Retry-After without multiplying the outer four-attempt budget."""
    delay = 1.5 * (attempt + 1)
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        response = getattr(error, "response", None)
        raw = (getattr(response, "headers", None) or {}).get("Retry-After")
        if raw:
            try:
                seconds = float(raw)
            except (TypeError, ValueError):
                try:
                    seconds = (parsedate_to_datetime(raw) - datetime.now(timezone.utc)).total_seconds()
                except (TypeError, ValueError):
                    seconds = 0
            if seconds > 120:
                raise PermanentSourceError("Retry-After exceeds the local retry budget; collection blocked")
            delay = max(delay, seconds)
        error = error.__cause__
    return delay


def _direct_host_slot(provider):
    """OS-backed slots also bound another standalone process's direct HTTP."""
    folder = ROOT / "tmp/locks"
    folder.mkdir(parents=True, exist_ok=True)
    while True:
        raise_if_stopped()
        for index in range(LIMITS[provider]):
            stream = (folder / f"{provider.lower().replace(' ', '-')}-{index}.lock").open("a+")
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return stream
            except OSError:
                stream.close()
        _stopped.wait(.05)


def ensure_google_owner():
    """Hold an advisory process lock until process exit; never bypass another run."""
    global _process_file
    with _lock:
        if _process_file is None:
            path = ROOT / "tmp/locks/google-collection.lock"
            path.parent.mkdir(parents=True, exist_ok=True)
            stream = path.open("a+")
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                stream.close()
                raise PermanentSourceError("Another Google collection owns this host; refusing concurrent runner")
            _process_file = stream


@contextmanager
def request_slot(provider, family=None):
    global _owner, _active_google
    if os.environ.get("RESIFLY_SOURCE_MODE") == "read":
        raise PermanentSourceError("Network forbidden during cache-only feed building")
    raise_if_stopped()
    if provider == "Google":
        ensure_google_owner()
        family = family or "technical"
        with _condition:
            while _owner not in (None, family):
                raise_if_stopped()
                _condition.wait()
            _owner = family
            _active_google += 1
    slot = _slots.get(provider)
    if slot:
        slot.acquire()
    began = time.monotonic()
    entered = False
    host_slot = None
    try:
        raise_if_stopped()
        if provider in LIMITS and provider != "Google":
            host_slot = _direct_host_slot(provider)
        with _lock:
            if _metrics is not None:
                row = _metrics["providers"][provider]
                row["attempts"] += 1
                row["active"] += 1
                row["max_in_flight"] = max(row["max_in_flight"], row["active"])
                entered = True
        yield
    finally:
        with _lock:
            if entered and _metrics is not None:
                row = _metrics["providers"][provider]
                if row["active"]:
                    row["active"] -= 1
                    row["seconds"] += time.monotonic() - began
            if provider == "Google":
                _active_google -= 1
                if not _active_google:
                    _owner = None
                    _condition.notify_all()
        if slot:
            slot.release()
        if host_slot:
            host_slot.close()


def http_request(function, url, *, family=None, **kwargs):
    host = urlparse(url).hostname or "unknown"
    provider = ("Google" if host.endswith("google.com") else
                "Wizz Air" if host.endswith("wizzair.com") else
                "Binter" if host.endswith("bintercanarias.com") else
                "Canaryfly" if host.endswith("canaryfly.es") else
                "Volotea" if host.endswith("volotea.com") else host)
    began = None
    status = None
    error = False
    try:
        with request_slot(provider, family):
            began = time.monotonic()
            response = function(url, **kwargs)
            status = response.status_code
            error = status >= 400
            return response
    except Exception:
        error = True
        raise
    finally:
        with _lock:
            if _metrics is not None and began is not None:
                row = _metrics["providers"][provider]
                row["errors"] += int(error)
                row["statuses"][str(status)] += 1
                # No URLs, bodies, cookies, fare tokens or credentials.
                _metrics["events"].append({"provider": provider, "family": family,
                    "at": began - _metrics["start"], "seconds": time.monotonic() - began,
                    "status": status, "error": error})
