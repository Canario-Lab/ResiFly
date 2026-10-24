#!/usr/bin/env python3
"""Explicit, audited route-only updates. Default: plan only, no HTTP or publication.

This is not a fresh full collection and never edits/re-certifies its parent.
All eleven feeds are rebuilt offline from a new composite source revision.
"""
import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.collection_coverage import METHODS, atomic_json, expected_queries
from scripts.search_steps import STEPS
from scripts.source_repository import Repository, activate_writer
from scripts.source_recovery import deferred_collection, map_jobs

ROOT = Path(__file__).resolve().parents[1]
MAX_INHERITED_AGE = timedelta(hours=24)
GOOGLE = ("Ryanair", "Iberia", "Vueling", "Air Europa", "easyJet")


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def source_environment(run, directory):
    values = {"RESIFLY_COLLECTION_RUN_ID": run,
              "RESIFLY_RYANAIR_GOOGLE_CACHE": str(Path(directory) / "ryanair-current-revision.jsonl")}
    keys = (*values, "RESIFLY_SOURCE_MODE", "RESIFLY_SOURCE_REPOSITORY")
    before = {k: os.environ.get(k) for k in keys}
    try:
        for key in keys:
            os.environ.pop(key, None)
        os.environ.update(values)
        yield
    finally:
        for key, value in before.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def key_id(key):
    return "|".join(key)


def configuration_paths():
    return [ROOT / "data" / n for n in (
        "search-airports.json", "wizz-route-schedules.json", "spanish-resident-fees.json"
    )] + sorted((ROOT / "data").glob("*transfer-airports.json"))


def archive_configuration(folder):
    for path in configuration_paths():
        target = Path(folder) / "configuration" / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != path.read_bytes():
            raise RuntimeError("Archived configuration changed")
        if not target.exists():
            # JSON must keep its exact bytes for the legacy aggregate hash.
            import shutil
            shutil.copyfile(path, target)


def configuration_snapshot(base, identity, revision=None):
    values = {}
    for path in configuration_paths():
        archived = Path(base) / "configuration" / path.name
        if archived.exists():
            values[path.name] = archived.read_bytes()
        else:
            # Legacy batches predate snapshots. Read committed blobs, never run
            # historical code, and accept them only if the aggregate hash matches.
            values[path.name] = subprocess.check_output(
                ["git", "show", f"{revision or 'HEAD'}:data/{path.name}"], cwd=ROOT)
    if hashlib.sha256(b"".join(values.values())).hexdigest() != identity["configuration_hash"]:
        raise RuntimeError("Cannot prove parent configuration; provide its matching --base-ref")
    return {name: json.loads(raw) for name, raw in values.items()}


def parse_route(raw):
    try:
        carrier, origin, destination = raw.split(":")
    except ValueError:
        raise argparse.ArgumentTypeError('Use "Wizz Air:KRK:NCE" (carrier:IATA:IATA)')
    if carrier not in METHODS or not all(re.fullmatch(r"[A-Z]{3}", c) for c in (origin, destination)) or origin == destination:
        raise argparse.ArgumentTypeError("Unknown carrier, invalid IATA or self-route")
    return carrier, origin, destination


def both_directions(routes):
    return {(c, a, b) for c, o, d in routes for a, b in ((o, d), (d, o))}


def validate_configuration_change(previous, current, selected):
    """Existing routes may refresh; additions are narrowly reviewed Step 6 pairs.

    No silent fee, endpoint, hub, source, discount or unrelated schedule changes.
    Other network migrations still need a fresh full collection.
    """
    if set(previous) != set(current):
        raise RuntimeError("Configuration file set changed; full collection required")
    for name in previous:
        before, after = deepcopy(previous[name]), deepcopy(current[name])
        if name == "wizz-route-schedules.json":
            for doc in (before, after):
                for field, rows in list(doc.items()):
                    if isinstance(rows, list):
                        doc[field] = [r for r in rows if not isinstance(r, dict) or
                                      ("Wizz Air", r.get("origin"), r.get("destination")) not in selected]
        elif name == "easyjet-transfer-airports.json":
            for doc in (before, after):
                doc.pop("verified_on", None)
                doc["pending_routes"] = [r for r in doc.get("pending_routes", [])
                    if (r.get("airline"), r.get("hub"), r.get("polish_airport")) not in selected]
                for airport in doc["airports"]:
                    keep = []
                    for route in airport["polish_routes"]:
                        route["airlines"] = [c for c in route["airlines"] if
                            (c, airport["iata"], route["polish_airport"]) not in selected]
                        if route["airlines"]:
                            keep.append(route)
                    airport["polish_routes"] = keep
        if before != after:
            raise RuntimeError(f"Unrelated/unsupported configuration change: {name}")


def certified_repository(folder):
    folder = Path(folder)
    identity = json.loads((folder / "manifest.json").read_text())
    certificate = json.loads((folder / "complete.json").read_text())
    repo = Repository(folder, identity)
    if (certificate.get("status") != "complete" or certificate.get("identity") != identity or
            certificate.get("digests") != repo.digests()):
        raise RuntimeError("Parent/source repository is incomplete or changed after certification")
    if identity.get("collection_mode") == "incremental":
        load_provenance(repo)
    return repo


def load_provenance(repo):
    path = repo.folder / "provenance.json"
    cert = json.loads((repo.folder / "complete.json").read_text())
    if cert.get("provenance_sha256") != digest(path):
        raise RuntimeError("Incremental provenance changed after certification")
    ledger = json.loads(path.read_text())
    if (ledger["lineage"]["revision_id"] != repo.identity["run_id"] or
            set(ledger["observations"]) != {key_id(k) for k in repo.rows}):
        raise RuntimeError("Incomplete incremental observation provenance")
    validate_lineage(ledger["lineage"])
    if not set(ledger["observations"].values()) <= set(ledger["lineage"]["source_runs"]):
        raise RuntimeError("Unknown observation origin")
    return ledger


def validate_lineage(lineage):
    if (lineage.get("mode") != "incremental" or not lineage.get("revision_id") or
            not lineage.get("parent_revision_id") or not lineage.get("rate_snapshot_run_id")):
        raise RuntimeError("Missing incremental lineage")
    updated = datetime.fromisoformat(lineage["updated_at"])
    if updated.tzinfo is None or updated > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise RuntimeError("Invalid partial-update timestamp")
    if not lineage.get("source_runs"):
        raise RuntimeError("Missing source run dates")
    for run, scope in lineage["source_runs"].items():
        first, last = map(datetime.fromisoformat, (scope["collected_from"], scope["collected_to"]))
        if not run or first.tzinfo is None or last.tzinfo is None or first > last or last > updated:
            raise RuntimeError("Invalid observation time range")
        if datetime.now(timezone.utc) - first > MAX_INHERITED_AGE:
            raise RuntimeError("Inherited observations exceed 24 hours; full refresh required")


def baseline(base, revision=None):
    base = Path(base).resolve()
    repo = certified_repository(base / "sources")
    report = json.loads((base / "validation-report.json").read_text())
    if report.get("status") != "complete" or report.get("run_id") != repo.identity["run_id"]:
        raise RuntimeError("Parent batch has not completed validation")
    documents, hashes, union = {}, {}, set()
    for step in STEPS:
        path = base / f"step{step}-results.json"
        doc = json.loads(path.read_text())
        coverage = doc["collection_coverage"]
        side = base / f"step{step}-results.collection-report.json"
        if (coverage != json.loads(side.read_text()) or coverage.get("status") != "complete" or
                coverage.get("run_id") != repo.identity["run_id"] or
                doc["period_from"] != repo.identity["period_from"] or
                doc["period_to"] != repo.identity["period_to"]):
            raise RuntimeError("Parent feeds/coverage do not belong to the certified source batch")
        keys = set()
        for route in coverage["routes"]:
            for day in route["days"]:
                key = (route["carrier"], route["origin"], route["destination"], day["date"], route["kind"])
                observation = repo.rows.get(key)
                if (key in keys or observation is None or day["status"] != "checked" or
                        day["flights"] != len(observation["rows"]) or day["method"] != observation["method"] or
                        day["method"] not in METHODS.get(key[0], set())):
                    raise RuntimeError("Parent coverage disagrees with certified observations")
                keys.add(key)
        if any(coverage.get(f) != v for f, v in (("expected_queries", len(keys)),
                ("completed_queries", len(keys)), ("missing_queries", 0), ("unexpected_queries", 0))):
            raise RuntimeError("Invalid parent coverage counts")
        union |= keys
        documents[step] = doc
        hashes[path.name], hashes[side.name] = digest(path), digest(side)
    if union != set(repo.rows):
        raise RuntimeError("Parent observations do not match its complete feed set")
    if repo.identity.get("collection_mode") == "incremental":
        ledger = load_provenance(repo)
    else:
        performance = json.loads((base / "performance.json").read_text())
        first = performance["started_at"]
        last = max(doc["generated_at"] for doc in documents.values())
        lineage = {"mode": "incremental", "revision_id": repo.identity["run_id"],
            "parent_revision_id": repo.identity["run_id"], "rate_snapshot_run_id": repo.identity["run_id"],
            "last_full_collection_at": last, "updated_at": now(),
            "source_runs": {repo.identity["run_id"]: {"collected_from": first, "collected_to": last}}}
        ledger = {"lineage": lineage,
                  "observations": {key_id(k): repo.identity["run_id"] for k in repo.rows}}
    validate_lineage({**ledger["lineage"], "updated_at": now()})
    return repo, documents, hashes, ledger, configuration_snapshot(base, repo.identity, revision)


def plan_update(base, routes, revision=None):
    parent, docs, hashes, ledger, old_config = baseline(base, revision)
    selected = both_directions(routes)
    current = {p.name: json.loads(p.read_text()) for p in configuration_paths()}
    validate_configuration_change(old_config, current, selected)
    start, end = map(date.fromisoformat, (parent.identity["period_from"], parent.identity["period_to"]))
    expected = set().union(*(expected_queries(s, start, end) for s in STEPS))
    allowed = {(c, o, d) for c, o, d, _, k in expected if k == "calendar"}
    if not selected or not selected <= allowed:
        raise RuntimeError("Every selected route needs both directions in reviewed canonical configuration")
    refresh = {k for k in expected if k[:3] in selected}
    if any(k not in parent.rows and k not in refresh for k in expected):
        raise RuntimeError("Unselected route/calendar is missing; refusing implicit network expansion")
    inherited = {k: row for k, row in parent.rows.items()
                 if k[:3] not in selected and (k in expected or k[4] == "details")}
    affected = [s for s in STEPS if expected_queries(s, start, end) & refresh]
    return {"parent": parent, "documents": docs, "hashes": hashes, "ledger": ledger,
            "selected": selected, "expected": expected, "inherited": inherited,
            "start": start, "end": end, "affected_steps": affected,
            "plan": {"mode": "incremental", "parent_revision_id": parent.identity["run_id"],
                "period_from": str(start), "period_to": str(end),
                "routes": [list(r) for r in sorted(selected)],
                "calendar_queries_to_refresh": len(refresh), "inherited_queries": len(inherited),
                "affected_steps": affected, "builders": list(STEPS),
                "nbp_snapshot": "frozen parent snapshot; not a new exchange-rate collection"}}


def fetch_selected(repo, selected, start, end, rates):
    """Only explicit full route windows; source adapters retain their own limits/retries."""
    from scripts import collect_step1 as binter, collect_step2 as low, collect_step4 as wizz
    from scripts import source_scheduler as scheduler
    modules = {s: importlib.import_module(f"scripts.collect_step{s}") for s in STEPS if s != "2"}
    lists = {s: json.loads(m.TRANSFER_FILE.read_text()) for s, m in modules.items()}
    for s, module in modules.items():
        validator = getattr(module, "validate_allowlist", None)
        if validator:
            validator(lists[s])
        binter.configure_airports_from_allowlist(lists[s])
    if any(c == "Wizz Air" for c, _, _ in selected):
        from scripts.wizz_api import wizz_api_base
        wizz_api_base()
    for carrier in (*GOOGLE, "Wizz Air", "Binter", "Canaryfly", "Volotea"):
        routes = {(o, d) for c, o, d in selected if c == carrier}
        if not routes:
            continue
        if carrier in GOOGLE:
            scheduler.ensure_google_owner()
        days = {(o, d, start + timedelta(days=n)) for o, d in routes for n in range((end-start).days+1)}
        if carrier == "Ryanair":
            list(map_jobs(carrier, lambda j: low.collect_ryanair_route(j[0], j[1], j[2], j[2], rates, "google"), sorted(days), 3))
        elif carrier == "Wizz Air":
            list(map_jobs(carrier, lambda p: wizz.collect_wizz_route(*p, start, end, rates), sorted(routes), 2))
        elif carrier == "easyJet":
            from scripts.easyjet_source import collect_legs
            collect_legs(days, 3)
        elif carrier == "Binter":
            binter.collect_binter_legs(days, rates, 2, {a["iata"]: a for a in lists["1"]["airports"]})
        elif carrier == "Canaryfly":
            module = modules["1f"]
            config = deepcopy(lists["1f"])
            config["airports"] = [a for a in config["airports"] if any(a["iata"] in p for p in routes)]
            available = module.collect_canaryfly_available_days(config, start, end, 2)
            module.collect_canaryfly_legs(available, config, rates, 2)
        elif carrier == "Volotea":
            modules["1e"].collect_volotea_legs(days, lists["1e"], rates, 2)
        else:
            step, planner = {"Iberia": ("1b", "iberia"), "Vueling": ("1c", "vueling"), "Air Europa": ("1d", "air_europa")}[carrier]
            module, config = modules[step], lists[step]
            if carrier == "Air Europa":
                module.collect_air_europa_legs(days, config, 3, rates["EUR"].pln)
            else:
                getattr(module, f"collect_{planner}_legs")(days, {a["iata"]: a for a in config["airports"]},
                    config[f"{planner}_airline_codes"], 3, rates["EUR"].pln)


def enrich_publication(document, report, repo):
    ledger = load_provenance(repo)
    lineage = deepcopy(ledger["lineage"])
    document["data_lineage"] = lineage
    report["data_lineage"] = deepcopy(lineage)
    for route in report["routes"]:
        for day in route["days"]:
            key = (route["carrier"], route["origin"], route["destination"], day["date"], route["kind"])
            day["observation_run_id"] = ledger["observations"][key_id(key)]
    for result in document["results"]:
        for leg in result["legs"]:
            carrier = "Iberia" if leg["carrier"] in ("Iberia", "Iberia Express") else leg["carrier"]
            key = (carrier, leg["departure_airport"], leg["arrival_airport"], leg["departure_at"][:10],
                   "details" if carrier == "Canaryfly" else "calendar")
            leg["source_observation_run_id"] = ledger["observations"][key_id(key)]


def validate_publication(document, repo=None):
    lineage = document.get("data_lineage")
    if lineage is None:
        if "data_lineage" in document.get("collection_coverage", {}):
            raise RuntimeError("Missing public incremental lineage")
        return
    validate_lineage(lineage)
    coverage = document["collection_coverage"]
    if coverage.get("data_lineage") != lineage or coverage["run_id"] != lineage["revision_id"]:
        raise RuntimeError("Incremental publication/coverage lineage mismatch")
    ledger = load_provenance(repo) if repo is not None else None
    if ledger is not None and ledger["lineage"] != lineage:
        raise RuntimeError("Publication differs from certified lineage")
    origins = {}
    for route in coverage["routes"]:
        for day in route["days"]:
            source = day.get("observation_run_id")
            if source not in lineage["source_runs"]:
                raise RuntimeError("Missing observation provenance in coverage")
            key = (route["carrier"], route["origin"], route["destination"], day["date"], route["kind"])
            origins[key] = source
            if ledger is not None:
                observation = repo.rows.get(key)
                if (ledger["observations"].get(key_id(key)) != source or observation is None or
                        len(observation["rows"]) != day["flights"] or observation["method"] != day["method"]):
                    raise RuntimeError("Coverage differs from certified source/provenance")
    for result in document["results"]:
        for leg in result["legs"]:
            carrier = "Iberia" if leg["carrier"] in ("Iberia", "Iberia Express") else leg["carrier"]
            key = (carrier, leg["departure_airport"], leg["arrival_airport"], leg["departure_at"][:10],
                   "details" if carrier == "Canaryfly" else "calendar")
            if leg.get("source_observation_run_id") != origins.get(key) or key not in origins:
                raise RuntimeError("Flight leg provenance disagrees with coverage")


def execute(plan, directory):
    from scripts.source_pipeline import configuration_hash, adapter_hash, source_report
    from scripts.collect_step1 import CurrencyRate
    from scripts import source_scheduler as scheduler
    from scripts.collect_five_steps import validate_batch
    directory = Path(directory).resolve()
    if directory.exists() and any(directory.iterdir()):
        raise RuntimeError("Use a new empty stage directory; parent is never overwritten")
    if directory == ROOT / "data" or ROOT / "data" in directory.parents:
        raise RuntimeError("Staging must be outside public data")
    directory.mkdir(parents=True, exist_ok=True)
    identity = deepcopy(plan["parent"].identity)
    run = str(uuid.uuid4())
    identity.update(run_id=run, collection_mode="incremental", parent_run_id=plan["parent"].identity["run_id"],
                    configuration_hash=configuration_hash(), adapter_hash=adapter_hash())
    archive_configuration(directory)
    repo = Repository(directory / "sources", identity, True)
    begun = now()
    atomic_json(directory / "incremental-plan.json", plan["plan"])
    atomic_json(directory / "public-baseline.json", plan["hashes"])
    status = {"status": "running", "run_id": run, "mode": "incremental"}
    try:
        grouped = {}
        for key, row in sorted(plan["inherited"].items()):
            grouped.setdefault(key[0], []).append(json.dumps(row, ensure_ascii=False, allow_nan=False))
        # New repository only. Exact parent observations, without relabeling them.
        for carrier, lines in grouped.items():
            path = repo.folder / (carrier.lower().replace(" ", "-") + ".jsonl")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        repo = Repository(repo.folder, identity, True)
        rates = {c: CurrencyRate(c, float(v)) for c, v in identity["nbp_rates"].items()}
        if not rates or any(not math.isfinite(r.pln) or r.pln <= 0 for r in rates.values()):
            raise RuntimeError("Invalid frozen parent exchange rates")
        scheduler.start_metrics(directory / "performance.json")
        activate_writer(repo)
        try:
            with source_environment(run, directory), deferred_collection(directory / "source-recovery.json", identity):
                fetch_selected(repo, plan["selected"], plan["start"], plan["end"], rates)
        finally:
            activate_writer(None)
        report = source_report(repo, plan["start"], plan["end"], plan["expected"])
        if report["status"] != "complete":
            raise RuntimeError("Partial sources incomplete; no feed may be published")
        finished = now()
        lineage = deepcopy(plan["ledger"]["lineage"])
        lineage.update(revision_id=run, parent_revision_id=plan["parent"].identity["run_id"], updated_at=finished,
                       refreshed_routes=[list(r) for r in sorted(plan["selected"])])
        lineage["source_runs"][run] = {"collected_from": begun, "collected_to": finished}
        observations = {key_id(k): (plan["ledger"]["observations"][key_id(k)] if k in plan["inherited"] else run)
                        for k in repo.rows}
        # Drop ancestors no longer used after repeated partial refreshes.
        lineage["source_runs"] = {r: v for r, v in lineage["source_runs"].items() if r in set(observations.values())}
        validate_lineage(lineage)
        atomic_json(repo.folder / "provenance.json", {"lineage": lineage, "observations": observations})
        atomic_json(directory / "source-coverage.json", report)
        atomic_json(repo.folder / "complete.json", {"status": "complete", "identity": identity,
            "digests": repo.digests(), "provenance_sha256": digest(repo.folder / "provenance.json")})
        scheduler.save_metrics("complete")
        env = dict(os.environ, RESIFLY_SOURCE_MODE="read", RESIFLY_SOURCE_REPOSITORY=str(repo.folder),
                   RESIFLY_COLLECTION_RUN_ID=run)
        # Build every consumer, including removals, without a single network call.
        for step in STEPS:
            command = [sys.executable, str(ROOT / "scripts" / f"collect_step{step}.py"),
                "--from-date", str(plan["start"]), "--days", str((plan["end"]-plan["start"]).days),
                "--output", str(directory / f"step{step}-results.json")]
            with (directory / f"step{step}.log").open("w") as log:
                subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        summary = validate_batch(directory, plan["start"], (plan["end"]-plan["start"]).days, run)
        status.update(status="complete", steps=summary, data_lineage=lineage)
        return directory
    except BaseException as error:
        status.update(status="failed", error_type=type(error).__name__)
        atomic_json(directory / "source-coverage.json", source_report(
            repo, plan["start"], plan["end"], plan["expected"], type(error).__name__))
        scheduler.save_metrics("failed")
        raise
    finally:
        atomic_json(directory / "validation-report.json", status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-batch", required=True, type=Path)
    parser.add_argument("--base-ref", help="Git revision matching a legacy parent's configuration hash")
    parser.add_argument("--route", required=True, action="append", type=parse_route,
                        help='Example: "Wizz Air:KRK:NCE"; always checks both directions')
    parser.add_argument("--stage-directory", type=Path)
    parser.add_argument("--collect", action="store_true", help="Explicitly fetch only selected full calendars")
    parser.add_argument("--promote", action="store_true", help="Replace local public files only after complete validation")
    args = parser.parse_args()
    if (args.collect and not args.stage_directory) or (args.promote and not args.collect):
        parser.error("--collect needs --stage-directory; --promote needs --collect")
    plan = plan_update(args.base_batch, args.route, args.base_ref)
    print(json.dumps(plan["plan"], ensure_ascii=False, indent=2), flush=True)
    if args.collect:
        directory = execute(plan, args.stage_directory)
        if args.promote:
            from scripts.collect_five_steps import promote_batch
            promote_batch(directory, expected_public_hashes=plan["hashes"])
        print("Partial update complete. No Git writes.")


if __name__ == "__main__":
    main()
