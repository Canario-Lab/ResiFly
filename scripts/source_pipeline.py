"""Collect unique source calendars once; build ten feeds without network later.

There remain exactly five search steps. These are source queues, not extra
search steps. One Google queue drains FR, IB, VY, UX in order, alongside four
independent official-source queues. Observations belong to one immutable run.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
import hashlib
import importlib
import json
import os
from pathlib import Path
import threading

from scripts.collection_coverage import Coverage, atomic_json, expected_queries
from scripts.source_repository import Repository, activate_writer
from scripts import source_scheduler as scheduler
from scripts.collector_settings import GOOGLE_FLIGHTS_MAX_WORKERS

ROOT = Path(__file__).resolve().parents[1]
STEPS = ("1", "1b", "1c", "1d", "1e", "1f", "2", "3", "4", "5")


def configuration_hash():
    paths = [ROOT / "data" / name for name in (
        "search-airports.json", "wizz-route-schedules.json", "spanish-resident-fees.json")]
    paths += sorted((ROOT / "data").glob("*transfer-airports.json"))
    return hashlib.sha256(b"".join(p.read_bytes() for p in paths)).hexdigest()


def adapter_hash():
    return hashlib.sha256(b"".join(p.read_bytes() for p in sorted(
        (ROOT / "scripts").glob("*.py")))).hexdigest()


def remaining(repository, carrier, candidates, kind="calendar"):
    return {(o, d, day) for o, d, day in candidates
            if not repository.has([(carrier, o, d, day.isoformat(), kind)])}


def source_report(repository, start, end, expected, error=None):
    tracker = Coverage("sources", start, end, expected, repository.identity["run_id"])
    for key, observation in repository.rows.items():
        carrier, origin, destination, raw_day, kind = key
        day = date.fromisoformat(raw_day)
        tracker.record(carrier, origin, destination, day, day,
                       observation["rows"], observation["method"], kind)
    return tracker.report(error)


def collect_sources(directory, start, end, run_id):
    """Preflight, run bounded source queues, and certify the shared repository."""
    from scripts import collect_step1 as binter, collect_step2 as low, collect_step4 as wizz
    from scripts.wizz_api import wizz_api_base
    from scripts.wizz_schedules import resolve_schedule
    from scripts.spanish_resident_fees import load_fee_registry, nondiscountable_fee_eur

    directory = Path(directory)
    scheduler.start_metrics(directory / "performance.json")
    modules = {step: importlib.import_module(f"scripts.collect_step{step}") for step in STEPS}
    lists = {step: json.loads(module.TRANSFER_FILE.read_text())
             for step, module in modules.items() if step != "2"}
    for step, allowlist in lists.items():
        validator = getattr(modules[step], "validate_allowlist", None)
        if validator:
            validator(allowlist)
        binter.configure_airports_from_allowlist(allowlist)
    rates = binter.nbp_rates(start)
    identity = {"schema_version": 1, "run_id": run_id,
                "period_from": start.isoformat(), "period_to": end.isoformat(),
                "configuration_hash": configuration_hash(), "adapter_hash": adapter_hash(),
                "nbp_rates": {c: r.pln for c, r in rates.items()}, "limits": scheduler.LIMITS,
                "passengers": {"adults": 1, "children": 0, "infants": 0},
                "wizz_price_types": ["regular", "wdc"],
                "google_limit": GOOGLE_FLIGHTS_MAX_WORKERS}
    repository = Repository(directory / "sources", identity, writable=True)
    expected = set().union(*(expected_queries(step, start, end) for step in STEPS))
    # Check all configured eligible estimate routes before the first flight request.
    fees = load_fee_registry()
    for step in ("1b", "1c", "1d", "1e"):
        carrier = {"1b": "Iberia", "1c": "Vueling", "1d": "Air Europa", "1e": "Volotea"}[step]
        for c, origin, destination, day, _ in expected:
            if c == carrier:
                nondiscountable_fee_eur(origin, destination, date.fromisoformat(day), fees)
    for step in ("3", "4", "5"):
        config = lists[step]
        groups = [config["airports"]] if step != "5" else [v["airports"] for v in config["variants"].values()]
        for group in groups:
            for airport in group:
                if not airport.get("resident_discount_eligible_on_tenerife_leg"):
                    continue
                for tenerife in airport["tenerife_airports"]:
                    for origin, destination in ((tenerife, airport["iata"]), (airport["iata"], tenerife)):
                        for day in (start, end):
                            nondiscountable_fee_eur(origin, destination, day, fees)
    scheduler.ensure_google_owner()
    wizz_api_base()  # resolve the public version once, before concurrent work
    activate_writer(repository)
    phase_lock = threading.Lock()
    phases = {}

    def phase(name, function):
        with phase_lock:
            phases[name] = {"status": "running", "started_at": datetime.now().astimezone().isoformat()}
            atomic_json(directory / "source-progress.json", phases)
        try:
            function()
        except BaseException as error:
            scheduler.stop_requests()
            with phase_lock:
                phases[name].update(status="failed", error=f"{type(error).__name__}: {error}"[:1000])
            raise
        else:
            with phase_lock:
                phases[name]["status"] = "complete"
        finally:
            with phase_lock:
                phases[name]["finished_at"] = datetime.now().astimezone().isoformat()
                atomic_json(directory / "source-progress.json", phases)
            scheduler.save_metrics("collecting")

    def route_queue(carrier, function, workers):
        routes = sorted({(o, d) for c, o, d, _, _ in expected if c == carrier})
        def fetch(pair):
            origin, destination = pair
            rows = function(origin, destination, start, end, rates)
            if carrier == "Wizz Air":
                # Shared observations must agree with any step-local metadata.
                for step in ("1", "1b"):
                    local = binter.wizz_schedules_from_allowlist(lists[step])
                    if pair not in local:
                        continue
                    for row in rows:
                        departure = datetime.fromisoformat(row["departure_at"])
                        number, duration = resolve_schedule(local, local.overrides, origin, destination, departure)
                        arrival = datetime.fromisoformat(row["arrival_at"])
                        if (number != row["flight_number"] or
                                round((arrival - departure).total_seconds() / 60) != duration):
                            raise RuntimeError(f"Conflicting Wizz metadata: {pair} {departure}")
            return len(rows)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for index, count in enumerate(pool.map(fetch, routes), 1):
                if index % 10 == 0 or index == len(routes):
                    print(f"Source {carrier}: {index}/{len(routes)} routes", flush=True)
                    scheduler.save_metrics("collecting")

    def google_queue():
        phase("Google Ryanair", lambda: route_queue("Ryanair", lambda o, d, s, e, r:
              low.collect_ryanair_route(o, d, s, e, r, "google"), GOOGLE_FLIGHTS_MAX_WORKERS))
        for step, carrier, planner in (("1b", "Iberia", "iberia"),
                ("1c", "Vueling", "vueling"), ("1d", "Air Europa", "air_europa")):
            module, allowlist = modules[step], lists[step]
            candidates = getattr(module, planner + "_route_days")(allowlist, start, end)
            pending = remaining(repository, carrier, candidates)
            def collect():
                if step == "1d":
                    module.collect_air_europa_legs(pending, allowlist, GOOGLE_FLIGHTS_MAX_WORKERS, rates["EUR"].pln)
                else:
                    getattr(module, "collect_" + planner + "_legs")(
                        pending, {a["iata"]: a for a in allowlist["airports"]},
                        allowlist[planner + "_airline_codes"], GOOGLE_FLIGHTS_MAX_WORKERS, rates["EUR"].pln)
            phase("Google " + carrier, collect)

    def binter_queue():
        candidates = binter.binter_route_days(lists["1"], start, end)
        binter.collect_binter_legs(remaining(repository, "Binter", candidates), rates, 2,
                                 {a["iata"]: a for a in lists["1"]["airports"]})

    def canaryfly_queue():
        module, allowlist = modules["1f"], lists["1f"]
        candidates = module.collect_canaryfly_available_days(allowlist, start, end, 2)
        module.collect_canaryfly_legs(remaining(repository, "Canaryfly", candidates, "details"), allowlist, rates, 2)

    def volotea_queue():
        module, allowlist = modules["1e"], lists["1e"]
        module.collect_volotea_legs(remaining(repository, "Volotea",
            module.volotea_route_days(allowlist, start, end)), allowlist, rates, 2)

    try:
        jobs = [("Google", google_queue), ("Wizz Air", lambda: route_queue("Wizz Air", wizz.collect_wizz_route, 2)),
                ("Binter", binter_queue), ("Canaryfly", canaryfly_queue), ("Volotea", volotea_queue)]
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(phase, name, job) for name, job in jobs]
            for future in as_completed(futures):
                future.result()
        report = source_report(repository, start, end, expected)
        if report["status"] != "complete":
            raise RuntimeError(f"Source coverage incomplete: {report['missing_queries']} missing")
        atomic_json(directory / "source-coverage.json", report)
        atomic_json(repository.folder / "complete.json", {"status": "complete", "identity": identity,
                                                        "digests": repository.digests()})
        scheduler.save_metrics("complete")
        return repository.folder
    except BaseException as error:
        atomic_json(directory / "source-coverage.json", source_report(repository, start, end, expected,
            f"{type(error).__name__}: {error}"[:2000]))
        scheduler.save_metrics("failed")
        raise
    finally:
        activate_writer(None)
