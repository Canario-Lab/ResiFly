#!/usr/bin/env python3
"""Collect all five steps (1A–1F and 2–5) into one local staging directory.

No Git operations. Public feeds are untouched unless --promote is explicitly set
and the entire batch validates. All collectors receive the same explicit date.
"""

import argparse
from collections import Counter
from datetime import date, datetime, timedelta
import importlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid
from zoneinfo import ZoneInfo

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.search_airports import POLISH_AIRPORTS, TENERIFE_AIRPORTS
from scripts.collection_coverage import atomic_json, validate_coverage

ROOT = Path(__file__).resolve().parents[1]
STEPS = ("1", "1b", "1c", "1d", "1e", "1f", "2", "3", "4", "5")


def validate_feed_document(step, document):
    module = importlib.import_module(f"scripts.collect_step{step}")
    if step in ("3", "4", "5"):
        module.validate_document(document, module.load_allowlist())
    else:
        module.validate_document(document)


def validate_batch(directory, start, days, expected_run_id=None):
    ids = set()
    summary = {}
    exchange_rates = {}
    expected_end = date.fromordinal(start.toordinal() + days).isoformat()
    run_id = expected_run_id
    for step in STEPS:
        document = json.loads((directory / f"step{step}-results.json").read_text(encoding="utf-8"))
        expected_step = int(step) if step.isdigit() else step.upper()
        if document.get("schema_version") != 2 or document.get("step") != expected_step:
            raise RuntimeError(f"Wrong schema/step in feed {step}")
        if document["period_from"] != start.isoformat() or document["period_to"] != expected_end:
            raise RuntimeError(f"Mixed collection periods in step {step}")
        generated = datetime.fromisoformat(document["generated_at"])
        if generated.tzinfo is None or generated.astimezone(ZoneInfo("Atlantic/Canary")).date() != datetime.now(ZoneInfo("Atlantic/Canary")).date():
            raise RuntimeError(f"Old collection file in step {step}")
        if document.get("price_filtering", {}).get("applied_during_collection") is not False:
            raise RuntimeError(f"Price filtering must remain on the website: step {step}")
        for currency, rate in document.get("exchange_rates", {}).items():
            value = (rate["rate"], rate["effective_for"])
            if currency in exchange_rates and exchange_rates[currency] != value:
                raise RuntimeError(f"Mixed daily exchange rates for {currency}")
            exchange_rates[currency] = value
        coverage_run = validate_coverage(document, step, start, start + timedelta(days=days))
        sidecar = directory / f"step{step}-results.collection-report.json"
        if not sidecar.exists() or json.loads(sidecar.read_text(encoding="utf-8")) != document["collection_coverage"]:
            raise RuntimeError(f"Missing, failed or stale collection report in step {step}")
        if run_id is None:
            run_id = coverage_run
        if coverage_run != run_id:
            raise RuntimeError(f"Mixed collection runs in step {step}")
        validate_feed_document(step, document)
        for result in document["results"]:
            if result["id"] in ids:
                raise RuntimeError(f"Duplicate result ID: {result['id']}")
            ids.add(result["id"])
            origin, destination = result["origin_airport"], result["destination_airport"]
            if result["direction"] not in ("poland_to_tenerife", "tenerife_to_poland"):
                raise RuntimeError(f"Unknown direction: {result['id']}")
            if result["direction"] == "poland_to_tenerife":
                valid = origin in POLISH_AIRPORTS and destination in TENERIFE_AIRPORTS
            else:
                valid = origin in TENERIFE_AIRPORTS and destination in POLISH_AIRPORTS
            if not valid or result.get("transfer_airport") in (origin, destination):
                raise RuntimeError(f"Invalid endpoint/transfer: {result['id']}")
            legs = result["legs"]
            if legs[0]["departure_airport"] != origin or legs[-1]["arrival_airport"] != destination:
                raise RuntimeError(f"Broken route: {result['id']}")
            for leg in legs:
                if leg["departure_airport"] == leg["arrival_airport"] or not leg.get("booking_url"):
                    raise RuntimeError(f"Invalid leg: {result['id']}")
                if datetime.fromisoformat(leg["arrival_at"]) <= datetime.fromisoformat(leg["departure_at"]):
                    raise RuntimeError(f"Invalid chronology: {result['id']}")
                if not math.isfinite(float(leg["price_regular_pln"])) or float(leg["price_regular_pln"]) <= 0:
                    raise RuntimeError(f"Invalid fare: {result['id']}")
            if len(legs) == 2:
                if legs[0]["arrival_airport"] != legs[1]["departure_airport"] or legs[0]["arrival_airport"] != result["transfer_airport"]:
                    raise RuntimeError(f"Disconnected transfer: {result['id']}")
                wait = round((datetime.fromisoformat(legs[1]["departure_at"]) - datetime.fromisoformat(legs[0]["arrival_at"])).total_seconds() / 60)
                if not 120 <= wait <= 1440 or wait != result["layover_minutes"]:
                    raise RuntimeError(f"Invalid layover: {result['id']}")
        summary[step] = {
            "results": len(document["results"]),
            "directions": dict(Counter(row["direction"] for row in document["results"])),
            "polish_airports": dict(Counter(row["origin_airport"] if row["direction"] == "poland_to_tenerife" else row["destination_airport"] for row in document["results"])),
            "gdn_as_transfer": sum(row.get("transfer_airport") == "GDN" for row in document["results"]),
            "gdn_endpoint_directions": dict(Counter(row["direction"] for row in document["results"] if "GDN" in (row["origin_airport"], row["destination_airport"]))),
            "variants": dict(Counter(row.get("variant", step) for row in document["results"])),
            "gdn_endpoint_variants": dict(Counter(row.get("variant", step) for row in document["results"] if "GDN" in (row["origin_airport"], row["destination_airport"]))),
        }
    return summary


def promote_batch(directory, public_directory=ROOT / "data"):
    """Replace a validated batch, preserving the old set and rolling back errors."""
    first = json.loads((directory / "step1-results.json").read_text(encoding="utf-8"))
    start, end = date.fromisoformat(first["period_from"]), date.fromisoformat(first["period_to"])
    validate_batch(directory, start, (end - start).days)
    backup = directory / "previous-public-feeds"
    backup.mkdir(exist_ok=True)
    pending = []
    with tempfile.TemporaryDirectory(prefix="promotion-rollback-", dir=directory) as rollback:
        rollback = Path(rollback)
        try:
            # Prepare every file before replacing the first public feed.
            for step in STEPS:
                filename = f"step{step}-results.json"
                target = public_directory / filename
                shutil.copy2(target, rollback / filename)
                if not (backup / filename).exists():
                    shutil.copy2(target, backup / filename)
                temporary = target.with_suffix(".json.pending")
                if temporary.exists():
                    raise RuntimeError(f"Unexpected pending feed; refusing to overwrite: {temporary}")
                pending.append(temporary)
                shutil.copyfile(directory / filename, temporary)
            replaced = []
            try:
                for temporary in pending:
                    target = temporary.with_suffix("")
                    temporary.replace(target)
                    replaced.append(target)
            except Exception:
                for target in replaced:
                    shutil.copy2(rollback / target.name, target)
                raise
        finally:
            for temporary in pending:
                if temporary.exists():
                    temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-date", type=date.fromisoformat, required=True)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--stage-directory", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--run-id", help="Reuse the same batch ID when resuming a failed collection")
    parser.add_argument("--refresh-steps", nargs="+", choices=STEPS, default=list(STEPS), help="Refresh selected feeds; still validate the complete ten-feed batch")
    args = parser.parse_args()
    if args.days < 0 or args.workers < 1:
        parser.error("--days must be non-negative and --workers must be positive")
    directory = args.stage_directory.resolve()
    public = (ROOT / "data").resolve()
    if directory == public or public in directory.parents:
        parser.error("Staging must be outside the public data directory")
    directory.mkdir(parents=True, exist_ok=True)
    if not args.validate_only and set(args.refresh_steps) != set(STEPS) and not args.run_id:
        parser.error("A partial retry requires --run-id from the original failed batch report")
    run_id = args.run_id or (None if args.validate_only else str(uuid.uuid4()))
    report = {"status": "running", "run_id": run_id, "from_date": args.from_date.isoformat(), "days": args.days}
    try:
        if not args.validate_only:
            atomic_json(directory / "validation-report.json", report)
            environment = dict(os.environ, RESIFLY_COLLECTION_RUN_ID=run_id)
            for step in STEPS:
                if step not in args.refresh_steps:
                    continue
                report["current_step"] = step
                output = directory / f"step{step}-results.json"
                command = [sys.executable, str(ROOT / "scripts" / f"collect_step{step}.py"), "--from-date", args.from_date.isoformat(), "--days", str(args.days), "--output", str(output)]
                if step != "2":
                    command += ["--workers", str(args.workers)]
                print(f"Collecting step {step}", flush=True)
                with (directory / f"step{step}.log").open("w", encoding="utf-8") as log:
                    subprocess.run(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT, check=True)
                print(f"Finished step {step}", flush=True)
        summary = validate_batch(directory, args.from_date, args.days, run_id)
        if run_id is None:
            run_id = json.loads((directory / "step1-results.json").read_text(encoding="utf-8"))["collection_coverage"]["run_id"]
        report.update(status="complete", run_id=run_id, polish_airports=list(POLISH_AIRPORTS), steps=summary)
        if args.promote:
            promote_batch(directory)
            print("Promoted complete local batch. No Git operations performed.", flush=True)
    except Exception as error:
        report.update(status="failed", error=f"{type(error).__name__}: {error}")
        atomic_json(directory / "validation-report.json", report)
        raise
    atomic_json(directory / "validation-report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
