"""Immutable run-scoped normalized observations; no tokens or raw HTTP payloads."""
from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import threading
from functools import wraps
from scripts.source_recovery import PermanentSourceError, can_defer

_writer = None
_readers = {}


def day_keys(carrier, origin, destination, start, end, kind="calendar"):
    return [(carrier, origin, destination, (start + timedelta(days=n)).isoformat(), kind)
            for n in range((end - start).days + 1)]


class Repository:
    def __init__(self, folder, identity, writable=False):
        from scripts.collection_coverage import atomic_json
        self.folder, self.identity = Path(folder), identity
        self.lock, self.rows = threading.RLock(), {}
        self.writable = writable
        manifest = self.folder / "manifest.json"
        if manifest.exists():
            if json.loads(manifest.read_text()) != identity:
                raise PermanentSourceError("Source repository identity mismatch")
        elif writable:
            self.folder.mkdir(parents=True, exist_ok=True)
            atomic_json(manifest, identity)
        else:
            raise PermanentSourceError("Missing source repository manifest")
        for path in self.folder.glob("*.jsonl"):
            lines = path.read_text().splitlines()
            for index, line in enumerate(lines):
                try:
                    row = json.loads(line)
                except ValueError:
                    raise PermanentSourceError(f"Corrupt source repository {path.name}:{index + 1}")
                key = tuple(row["key"])
                if key in self.rows:
                    raise PermanentSourceError("Duplicate source observation")
                self.rows[key] = row

    def has(self, keys):
        with self.lock:
            return all(tuple(k) in self.rows for k in keys)

    def digests(self):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(self.folder.glob("*.jsonl"))}

    def read(self, carrier, origin, destination, start, end, kind="calendar"):
        with self.lock:
            result = []
            for key in day_keys(carrier, origin, destination, start, end, kind):
                row = self.rows.get(key)
                if row is None:
                    raise PermanentSourceError("Missing current source observation: " + str(key))
                result.extend(deepcopy(row["rows"]))
            return result

    def record(self, carrier, origin, destination, start, end, rows, method, kind="calendar"):
        if not self.writable:
            raise PermanentSourceError("Read-only source repository")
        pending = []
        for key in day_keys(carrier, origin, destination, start, end, kind):
            values = [r for r in rows if r["departure_at"][:10] == key[3]]
            pending.append({"key": key, "method": method, "rows": values})
        with self.lock:
            path = self.folder / (carrier.lower().replace(" ", "-") + ".jsonl")
            with path.open("a", encoding="utf-8") as stream:
                for row in pending:
                    key = tuple(row["key"])
                    if key in self.rows:
                        if self.rows[key] != json.loads(json.dumps(row)):
                            raise PermanentSourceError("Attempt to mutate a completed source observation")
                        continue
                    encoded = json.dumps(row, ensure_ascii=False, allow_nan=False)
                    if any('"' + k + '"' in encoded for k in ("token", "cookies", "authorization", "api_key")):
                        raise PermanentSourceError("Secret field in normalized source observation")
                    stream.write(encoded + "\n")
                    stream.flush()
                    self.rows[key] = json.loads(encoded)


def activate_writer(repository):
    global _writer
    _writer = repository


def record_source(*args):
    if _writer is not None:
        _writer.record(*args)


def abort_on_source_failure(function):
    """Defer request failures only inside the bounded full-batch job runner."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except BaseException as error:
            if _writer is not None and not can_defer(error):
                from scripts.source_scheduler import stop_requests
                stop_requests()
            raise
    return wrapped


def reader():
    folder = os.environ.get("RESIFLY_SOURCE_REPOSITORY")
    if os.environ.get("RESIFLY_SOURCE_MODE") != "read":
        return None
    if not folder:
        raise RuntimeError("Cache-only mode requires a source repository")
    if folder not in _readers:
        identity = json.loads((Path(folder) / "manifest.json").read_text())
        if identity["run_id"] != os.environ.get("RESIFLY_COLLECTION_RUN_ID"):
            raise RuntimeError("Source repository belongs to a different run")
        from scripts.source_pipeline import configuration_hash, adapter_hash
        if identity["configuration_hash"] != configuration_hash():
            raise RuntimeError("Source repository configuration changed")
        if identity["adapter_hash"] != adapter_hash():
            raise RuntimeError("Source repository adapters changed")
        certificate = json.loads((Path(folder) / "complete.json").read_text())
        if certificate.get("identity") != identity or certificate.get("status") != "complete":
            raise RuntimeError("Source repository is not complete")
        repository = Repository(folder, identity)
        if certificate.get("digests") != repository.digests():
            raise RuntimeError("Source repository observations changed after certification")
        _readers[folder] = repository
    return _readers[folder]


def cached_route(carrier, origin, destination, start, end, kind="calendar"):
    repository = reader()
    if repository is None:
        repository = _writer
        if repository is None or not repository.has(day_keys(carrier, origin, destination, start, end, kind)):
            return None
    return repository.read(carrier, origin, destination, start, end, kind)


def cached_days(carrier, candidates, method, kind="calendar"):
    if reader() is None:
        return None
    from scripts.collection_coverage import record_checked
    rows = []
    for origin, destination, day in sorted(candidates):
        found = cached_route(carrier, origin, destination, day, day, kind)
        record_checked(carrier, origin, destination, day, day, found, method, kind)
        rows.extend(found)
    return rows
