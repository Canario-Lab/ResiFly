#!/usr/bin/env python3
"""Repair final Binter prices in the current Step 1 feed only.

The command does not recollect routes, schedules, low-cost legs or any other
public feed. It refreshes official final prices only for Binter flights already
present in ``data/step1-results.json`` and applies the result atomically after
every saved flight has been matched exactly.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any
from zoneinfo import ZoneInfo

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.collection_coverage import atomic_json, validate_coverage
from scripts.collect_step1 import (
    CurrencyRate,
    TRANSFER_FILE,
    collect_binter_trip,
    configure_airports_from_allowlist,
    validate_document,
)
from scripts.search_airports import TENERIFE_AIRPORTS


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "step1-results.json"
DEFAULT_WORK_ROOT = ROOT / "tmp" / "binter-price-repair"
MAX_WORKERS = 4

BINTER_PRICE_FIELDS = (
    "price_regular_pln",
    "price_resident_estimated_pln",
    "resident_price_is_estimate",
    "resident_price_source",
    "price_source",
    "price_scope",
    "price_source_currency",
    "price_source_amount",
    "price_source_resident_amount",
)


def cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Atomically replace the input after a complete verified repair",
    )
    return parser.parse_args()


def binter_leg_key(leg: dict[str, Any]) -> tuple[str, str, str, str, str]:
    try:
        return (
            str(leg["departure_airport"]),
            str(leg["arrival_airport"]),
            str(leg["departure_at"]),
            str(leg["arrival_at"]),
            str(leg["flight_number"]),
        )
    except KeyError as error:
        raise RuntimeError(f"Malformed saved Binter leg: missing {error.args[0]}") from error


def saved_binter_legs(
    document: dict[str, Any],
) -> dict[tuple[str, str, str, str, str], list[dict[str, Any]]]:
    saved: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = {}
    for result in document.get("results", []):
        if not isinstance(result, dict) or not isinstance(result.get("legs"), list):
            raise RuntimeError("Malformed Step 1 result")
        binter = [leg for leg in result["legs"] if leg.get("carrier") == "Binter"]
        if len(binter) != 1:
            raise RuntimeError(
                f"Step 1 result {result.get('id')} does not contain exactly one Binter leg"
            )
        saved.setdefault(binter_leg_key(binter[0]), []).append(binter[0])
    if not saved:
        raise RuntimeError("Current Step 1 feed contains no Binter legs")
    return saved


def route_days_from_keys(
    keys: set[tuple[str, str, str, str, str]],
) -> set[tuple[str, str, date]]:
    return {
        (origin, destination, date.fromisoformat(departure_at[:10]))
        for origin, destination, departure_at, _arrival_at, _number in keys
    }


def transfer_rules() -> dict[str, dict[str, Any]]:
    allowlist = json.loads(TRANSFER_FILE.read_text(encoding="utf-8"))
    configure_airports_from_allowlist(allowlist)
    return {airport["iata"]: airport for airport in allowlist["airports"]}


def fetch_current_binter_prices(
    route_days: set[tuple[str, str, date]],
    eur_pln: float,
    workers: int,
) -> dict[tuple[str, str, str, str, str], dict[str, Any]]:
    rules = transfer_rules()
    rates = {
        "EUR": CurrencyRate("EUR", eur_pln),
        "PLN": CurrencyRate("PLN", 1.0),
    }

    def collect(origin: str, destination: str, day: date) -> list[dict[str, Any]]:
        transfer = destination if origin in TENERIFE_AIRPORTS else origin
        try:
            rule = rules[transfer]
        except KeyError as error:
            raise RuntimeError(
                f"Saved Binter route {origin}-{destination} uses an unknown transfer airport"
            ) from error
        return collect_binter_trip(
            origin,
            destination,
            day,
            rates,
            bool(rule["resident_discount_eligible_on_binter_leg"]),
            float(rule["binter_resident_fare_multiplier"]),
        )

    live: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    ordered = sorted(route_days, key=lambda item: (item[2], item[0], item[1]))
    worker_count = max(1, min(int(workers), MAX_WORKERS))
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = {
            pool.submit(collect, origin, destination, day): (origin, destination, day)
            for origin, destination, day in ordered
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            origin, destination, day = futures[future]
            try:
                legs = future.result()
            except Exception as error:
                raise RuntimeError(
                    f"Binter price repair failed for {origin}-{destination} on {day}"
                ) from error
            for leg in legs:
                key = binter_leg_key(leg)
                previous = live.get(key)
                if previous is not None and any(
                    previous.get(field) != leg.get(field)
                    for field in BINTER_PRICE_FIELDS
                ):
                    raise RuntimeError(f"Conflicting Binter prices for {key}")
                live[key] = leg
            if completed % 10 == 0 or completed == len(ordered):
                print(
                    f"Binter price repair: {completed}/{len(ordered)} tras/dni, "
                    f"{len(live)} lotów z ceną końcową",
                    flush=True,
                )
    return live


def repair_document(
    source: dict[str, Any],
    live_prices: dict[tuple[str, str, str, str, str], dict[str, Any]],
    repaired_at: str,
) -> tuple[dict[str, Any], dict[str, int]]:
    document = copy.deepcopy(source)
    original_occurrences = saved_binter_legs(document)
    missing = sorted(set(original_occurrences) - set(live_prices))

    removed_results = 0
    if missing:
        missing_set = set(missing)
        retained_results = []
        for result in document["results"]:
            binter = [leg for leg in result["legs"] if leg.get("carrier") == "Binter"]
            if binter_leg_key(binter[0]) in missing_set:
                removed_results += 1
            else:
                retained_results.append(result)
        document["results"] = retained_results
        if not retained_results:
            raise RuntimeError("No Step 1 results remain after unavailable Binter flights")

    occurrences = saved_binter_legs(document)

    changed_occurrences = 0
    for key, saved_legs in occurrences.items():
        current = live_prices[key]
        if current.get("resident_price_is_estimate") is not False:
            raise RuntimeError(f"Binter final resident price is not official for {key}")
        for leg in saved_legs:
            for field in BINTER_PRICE_FIELDS:
                if field not in current:
                    raise RuntimeError(f"Binter final price missing {field} for {key}")
                leg[field] = current[field]
            changed_occurrences += 1

    for result in document["results"]:
        result["price_total_regular_pln"] = round(
            sum(float(leg["price_regular_pln"]) for leg in result["legs"]), 2
        )
        result["price_total_resident_estimated_pln"] = round(
            sum(
                float(leg["price_resident_estimated_pln"])
                for leg in result["legs"]
            ),
            2,
        )

    document.setdefault("sources", {})["binter"] = (
        "Binter booking_search + booking_getImports GraphQL final totals"
    )
    document["binter_prices_updated_at"] = repaired_at
    document["binter_price_repair"] = {
        "scope": "existing Binter legs and dependent Step 1 totals only",
        "other_carriers_recollected": False,
        "source_collection_generated_at": source["generated_at"],
        "collection_run_id": source["collection_coverage"]["run_id"],
        "unique_route_days": len(route_days_from_keys(set(occurrences))),
        "unique_binter_legs": len(occurrences),
        "updated_binter_occurrences": changed_occurrences,
        "unavailable_binter_legs_removed": len(missing),
        "connections_removed_as_unavailable": removed_results,
        "unavailable_binter_flights": [
            {
                "origin": key[0],
                "destination": key[1],
                "departure_at": key[2],
                "arrival_at": key[3],
                "flight_number": key[4],
            }
            for key in missing
        ],
        "source": "official Binter booking_search + booking_getImports GraphQL",
    }
    validate_document(document)
    return document, {
        "unique_route_days": len(route_days_from_keys(set(occurrences))),
        "unique_binter_legs": len(occurrences),
        "updated_binter_occurrences": changed_occurrences,
        "unavailable_binter_legs_removed": len(missing),
        "connections_removed_as_unavailable": removed_results,
    }


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_optional_coverage_sidecar(
    source_path: Path,
    embedded_coverage: dict[str, Any],
) -> bool:
    """Validate a historical sidecar when present without manufacturing one.

    Some previously published Step 1 feeds contain the complete coverage report
    only inside the public JSON.  The embedded report is always validated by
    ``validate_coverage`` before this helper runs.  If an older sidecar exists,
    it must still match byte-for-byte at the JSON-data level.
    """

    sidecar = source_path.with_suffix(".collection-report.json")
    if not sidecar.exists():
        return False
    if json.loads(sidecar.read_text(encoding="utf-8")) != embedded_coverage:
        raise RuntimeError("Step 1 coverage sidecar does not match the current feed")
    return True


def main() -> None:
    args = cli()
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    source_path = args.input.resolve()
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes)
    start = date.fromisoformat(source["period_from"])
    end = date.fromisoformat(source["period_to"])
    validate_coverage(source, "1", start, end)
    validate_document(source)

    coverage_sidecar_present = validate_optional_coverage_sidecar(
        source_path,
        source["collection_coverage"],
    )

    saved = saved_binter_legs(source)
    route_days = route_days_from_keys(set(saved))
    eur_pln = float(source["exchange_rates"]["EUR_PLN"]["rate"])
    print(
        f"Do poprawienia: {len(saved)} unikalnych lotów Bintera w "
        f"{len(route_days)} trasach/dniach; EUR/PLN {eur_pln:.4f}",
        flush=True,
    )
    live_prices = fetch_current_binter_prices(
        route_days,
        eur_pln,
        args.workers,
    )
    repaired_at = datetime.now(ZoneInfo("Atlantic/Canary")).isoformat(
        timespec="seconds"
    )
    repaired, counts = repair_document(source, live_prices, repaired_at)

    stamp = repaired_at.replace(":", "-")
    work_directory = DEFAULT_WORK_ROOT / stamp
    work_directory.mkdir(parents=True, exist_ok=False)
    staged = work_directory / source_path.name
    backup = work_directory / f"{source_path.stem}.before.json"
    report_path = work_directory / "repair-report.json"
    atomic_json(staged, repaired)
    backup.write_bytes(source_bytes)
    report = {
        "status": "complete",
        "applied": bool(args.apply),
        "input": str(source_path),
        "backup": str(backup),
        "staged": str(staged),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "staged_sha256": file_sha256(staged),
        "repaired_at": repaired_at,
        "coverage_sidecar_present": coverage_sidecar_present,
        **counts,
    }
    atomic_json(report_path, report)

    if args.apply:
        if source_path.read_bytes() != source_bytes:
            raise RuntimeError("Step 1 feed changed during repair; refusing to replace it")
        atomic_json(source_path, repaired)
        if file_sha256(source_path) != report["staged_sha256"]:
            shutil.copy2(backup, source_path)
            raise RuntimeError("Published Step 1 checksum mismatch; restored backup")
        print(f"Podmieniono atomowo {source_path}", flush=True)
    else:
        print("Nie użyto --apply; plik publiczny pozostał bez zmian", flush=True)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
