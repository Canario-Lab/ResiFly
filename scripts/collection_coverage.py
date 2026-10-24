"""Fail-closed route/day accounting shared by standalone collectors and batches.

Coverage certifies completed source queries, not that an external source can
never omit a flight. In particular a cheapest-fare response cannot certify a
full Ryanair calendar. Worker threads intentionally share one process recorder.
"""

from collections import defaultdict
from datetime import date, timedelta
from functools import wraps
import importlib
import inspect
import json
import os
from pathlib import Path
import tempfile
import threading
import uuid


_active = None
METHODS = {
    "Ryanair": {"google_flights_http"}, "Wizz Air": {"timetableV2"},
    "Binter": {"booking_search"}, "Iberia": {"google_flights_http"},
    "Vueling": {"google_flights_http"}, "Air Europa": {"google_flights_http"},
    "Volotea": {"official_minprice"}, "Canaryfly": {"booking_calendar", "booking_search"},
}


def days_between(start, end):
    return [start + timedelta(days=n) for n in range((end - start).days + 1)]


def expected_queries(step, start, end):
    """Derive the plan from saved route matrices, never from returned flights."""
    module = importlib.import_module(f"scripts.collect_step{step}")
    expected = set()

    def add(carrier, routes):
        for origin, destination in routes:
            for day in days_between(start, end):
                expected.add((carrier, origin, destination, day.isoformat(), "calendar"))

    if step == "2":
        routes = list(module.route_matrix())
        for carrier in ("Ryanair", "Wizz Air"):
            add(carrier, routes)
    elif step in ("3", "4", "5"):
        routes = module.route_matrix(module.load_allowlist())
        if step == "5":
            for carrier, values in routes.items():
                add(carrier, values)
        else:
            add("Ryanair" if step == "3" else "Wizz Air", routes)
    else:
        allowlist = json.loads(module.TRANSFER_FILE.read_text(encoding="utf-8"))
        if step in ("1", "1b"):
            from scripts.search_airports import POLISH_AIRPORTS
            routes = [(a["iata"], p) for a in allowlist["airports"] for p in POLISH_AIRPORTS]
            routes += [(destination, origin) for origin, destination in routes]
            for carrier in ("Ryanair", "Wizz Air"):
                add(carrier, routes)
        else:
            for carrier, origin, destination in module.low_cost_route_matrix(allowlist):
                add(carrier, [(origin, destination)])
        carrier, planner = {
            "1": ("Binter", "binter_route_days"),
            "1b": ("Iberia", "iberia_route_days"),
            "1c": ("Vueling", "vueling_route_days"),
            "1d": ("Air Europa", "air_europa_route_days"),
            "1e": ("Volotea", "volotea_route_days"),
            "1f": ("Canaryfly", None),
        }[step]
        if planner:
            for origin, destination, day in getattr(module, planner)(allowlist, start, end):
                expected.add((carrier, origin, destination, day.isoformat(), "calendar"))
        else:
            add(carrier, module.canaryfly_routes(allowlist))
    return expected


class Coverage:
    def __init__(self, step, start, end, expected, run_id=None):
        self.step, self.start, self.end = step, start, end
        self.run_id = run_id or str(uuid.uuid4())
        self.expected = set(expected)
        self.completed = {}
        self.published = False
        self.lock = threading.Lock()

    def record(self, carrier, origin, destination, start, end, rows, method, kind="calendar"):
        if method not in METHODS.get(carrier, set()):
            raise RuntimeError(f"Unverified calendar source for {carrier}: {method}")
        counts = defaultdict(int)
        for row in rows:
            counts[row["departure_at"][:10]] += 1
        with self.lock:
            for day in days_between(start, end):
                key = (carrier, origin, destination, day.isoformat(), kind)
                self.completed[key] = (counts[day.isoformat()], method)
                if carrier == "Canaryfly" and kind == "calendar" and counts[day.isoformat()]:
                    self.expected.add((carrier, origin, destination, day.isoformat(), "details"))

    def report(self, error=None):
        with self.lock:
            completed = dict(self.completed)
            expected = set(self.expected)
        missing = expected - completed.keys()
        unexpected = completed.keys() - expected
        routes = defaultdict(list)
        for carrier, origin, destination, day, kind in sorted(expected | completed.keys()):
            key = (carrier, origin, destination, day, kind)
            value = completed.get(key)
            routes[(carrier, origin, destination, kind)].append({
                "date": day, "status": "checked" if value is not None else "missing",
                "flights": value[0] if value is not None else None,
                "method": value[1] if value is not None else None,
            })
        return {
            "schema_version": 1, "run_id": self.run_id, "step": self.step,
            "period_from": self.start.isoformat(), "period_to": self.end.isoformat(),
            "status": "complete" if not error and not missing and not unexpected else "failed",
            "expected_queries": len(expected), "completed_queries": len(completed),
            "missing_queries": len(missing), "unexpected_queries": len(unexpected),
            "error": error,
            "routes": [{"carrier": c, "origin": o, "destination": d, "kind": k, "days": values}
                       for (c, o, d, k), values in sorted(routes.items())],
        }

    def verify(self):
        report = self.report()
        if report["status"] != "complete":
            raise RuntimeError(f"Incomplete source coverage in step {self.step}: "
                               f"{report['missing_queries']} missing, {report['unexpected_queries']} unexpected queries")
        return report


def record_checked(carrier, origin, destination, start, end, rows, method, kind="calendar"):
    from scripts.source_repository import record_source
    record_source(carrier, origin, destination, start, end, rows, method, kind)
    if _active is not None:
        _active.record(carrier, origin, destination, start, end, rows, method, kind)


def calendar_collector(carrier, method):
    def decorate(function):
        signature = inspect.signature(function)

        from scripts.source_repository import abort_on_source_failure
        @abort_on_source_failure
        @wraps(function)
        def wrapped(*args, **kwargs):
            bound = signature.bind(*args, **kwargs).arguments
            start = bound.get("start", bound.get("departure_date"))
            end = bound.get("end", start)
            from scripts.source_repository import cached_route
            result = cached_route(carrier, bound["origin"], bound["destination"], start, end)
            if result is None:
                result = function(*args, **kwargs)
            record_checked(carrier, bound["origin"], bound["destination"], start, end, result, method)
            return result
        return wrapped
    return decorate


def atomic_json(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", suffix=".pending", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(document, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def publish_document(document, output):
    if _active is None:
        raise RuntimeError("No collection coverage session; refusing to publish")
    report = _active.verify()
    document["collection_coverage"] = report
    atomic_json(Path(output).with_suffix(".collection-report.json"), report)
    atomic_json(output, document)
    _active.published = True


def collection_entrypoint(step):
    """Set up coverage before source requests, preserve the old feed on failure."""
    def decorate(function):
        @wraps(function)
        def wrapped():
            global _active
            args = function.__globals__["cli"]()
            if args.days < 0:
                raise SystemExit("--days must be non-negative")
            end = args.from_date + timedelta(days=args.days)
            if _active is not None:
                raise RuntimeError("A collection is already running in this process")
            tracker = Coverage(step, args.from_date, end, expected_queries(step, args.from_date, end),
                               os.environ.get("RESIFLY_COLLECTION_RUN_ID"))
            _active = tracker
            try:
                result = function(args)
                tracker.verify()
                if not tracker.published:
                    raise RuntimeError("Collector exited without a verified publication")
                return result
            except BaseException as error:
                atomic_json(Path(args.output).with_suffix(".collection-report.json"),
                            tracker.report(f"{type(error).__name__}: {error}"[:2000]))
                raise
            finally:
                _active = None
        return wrapped
    return decorate


def validate_coverage(document, step, start, end):
    report = document.get("collection_coverage")
    if not isinstance(report, dict) or report.get("schema_version") != 1 or report.get("status") != "complete":
        raise RuntimeError(f"Missing or failed source coverage in step {step}; recollect with the current collectors")
    if report.get("step") != step or report.get("period_from") != start.isoformat() or report.get("period_to") != end.isoformat() or not report.get("run_id"):
        raise RuntimeError(f"Wrong coverage scope in step {step}")
    expected = expected_queries(step, start, end)
    completed = set()
    for route in report.get("routes", []):
        for day in route["days"]:
            key = (route["carrier"], route["origin"], route["destination"], day["date"], route["kind"])
            if (day["status"] != "checked" or day.get("method") not in METHODS.get(route["carrier"], set())
                    or type(day.get("flights")) is not int or day["flights"] < 0 or key in completed):
                raise RuntimeError(f"Invalid coverage entry in step {step}")
            completed.add(key)
    # Canaryfly details are required only for days actually available in its
    # independently collected complete monthly calendars.
    if step == "1f":
        for route in report["routes"]:
            if route["carrier"] == "Canaryfly" and route["kind"] == "calendar":
                expected |= {("Canaryfly", route["origin"], route["destination"], day["date"], "details")
                             for day in route["days"] if day["flights"] > 0}
    if completed != expected or report.get("expected_queries") != len(expected) or report.get("completed_queries") != len(completed) or report.get("missing_queries") != 0 or report.get("unexpected_queries") != 0:
        raise RuntimeError(f"Incomplete source coverage in step {step}")
    return report["run_id"]
