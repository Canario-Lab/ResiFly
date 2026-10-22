#!/usr/bin/env python3
"""Repair final Canaryfly prices in the current Step 1F feed only.

The command does not recollect monthly calendars, low-cost legs or any other
public feed. It refreshes official final prices only for Canaryfly flights
already present in ``data/step1f-results.json`` and applies the result
atomically after every saved route/day has been checked successfully.
"""

from __future__ import annotations

import argparse
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
from scripts.collect_step1 import CurrencyRate, configure_airports_from_allowlist
from scripts.collect_step1f import (
    TRANSFER_FILE,
    collect_canaryfly_legs,
    validate_allowlist,
    validate_document,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "step1f-results.json"
DEFAULT_WORK_ROOT = ROOT / "tmp" / "canaryfly-price-repair"
MAX_WORKERS = 4

CANARYFLY_PRICE_FIELDS = (
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


def canaryfly_leg_key(leg: dict[str, Any]) -> tuple[str, str, str, str, str]:
    try:
        return (
            str(leg["departure_airport"]),
            str(leg["arrival_airport"]),
            str(leg["departure_at"]),
            str(leg["arrival_at"]),
            str(leg["flight_number"]),
        )
    except KeyError as error:
        raise RuntimeError(
            f"Malformed saved Canaryfly leg: missing {error.args[0]}"
        ) from error


def saved_canaryfly_legs(
    document: dict[str, Any],
) -> dict[tuple[str, str, str, str, str], list[dict[str, Any]]]:
    saved: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = {}
    for result in document.get("results", []):
        if not isinstance(result, dict) or not isinstance(result.get("legs"), list):
            raise RuntimeError("Malformed Step 1F result")
        canaryfly = [
            leg for leg in result["legs"] if leg.get("carrier") == "Canaryfly"
        ]
        if len(canaryfly) != 1:
            raise RuntimeError(
                f"Step 1F result {result.get('id')} does not contain exactly "
                "one Canaryfly leg"
            )
        saved.setdefault(canaryfly_leg_key(canaryfly[0]), []).append(canaryfly[0])
    if not saved:
        raise RuntimeError("Current Step 1F feed contains no Canaryfly legs")
    return saved


def route_days_from_keys(
    keys: set[tuple[str, str, str, str, str]],
) -> set[tuple[str, str, date]]:
    return {
        (origin, destination, date.fromisoformat(departure_at[:10]))
        for origin, destination, departure_at, _arrival_at, _number in keys
    }


def fetch_current_canaryfly_prices(
    route_days: set[tuple[str, str, date]],
    eur_pln: float,
    workers: int,
) -> dict[tuple[str, str, str, str, str], dict[str, Any]]:
    allowlist = json.loads(TRANSFER_FILE.read_text(encoding="utf-8"))
    validate_allowlist(allowlist)
    configure_airports_from_allowlist(allowlist)
    rates = {
        "EUR": CurrencyRate("EUR", eur_pln),
        "PLN": CurrencyRate("PLN", 1.0),
    }
    legs = collect_canaryfly_legs(
        route_days,
        allowlist,
        rates,
        max(1, min(int(workers), MAX_WORKERS)),
    )
    live: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for leg in legs:
        key = canaryfly_leg_key(leg)
        previous = live.get(key)
        if previous is not None and any(
            previous.get(field) != leg.get(field)
            for field in CANARYFLY_PRICE_FIELDS
        ):
            raise RuntimeError(f"Conflicting Canaryfly prices for {key}")
        live[key] = leg
    return live


def repair_document(
    source: dict[str, Any],
    live_prices: dict[tuple[str, str, str, str, str], dict[str, Any]],
    repaired_at: str,
) -> tuple[dict[str, Any], dict[str, int]]:
    document = copy.deepcopy(source)
    original_occurrences = saved_canaryfly_legs(document)
    missing = sorted(set(original_occurrences) - set(live_prices))

    removed_results = 0
    if missing:
        missing_set = set(missing)
        retained_results = []
        for result in document["results"]:
            canaryfly = [
                leg for leg in result["legs"] if leg.get("carrier") == "Canaryfly"
            ]
            if canaryfly_leg_key(canaryfly[0]) in missing_set:
                removed_results += 1
            else:
                retained_results.append(result)
        document["results"] = retained_results
        if not retained_results:
            raise RuntimeError(
                "No Step 1F results remain after unavailable Canaryfly flights"
            )

    occurrences = saved_canaryfly_legs(document)
    changed_occurrences = 0
    for key, saved_legs in occurrences.items():
        current = live_prices[key]
        if current.get("resident_price_is_estimate") is not False:
            raise RuntimeError(
                f"Canaryfly final resident price is not official for {key}"
            )
        for leg in saved_legs:
            for field in CANARYFLY_PRICE_FIELDS:
                if field not in current:
                    raise RuntimeError(
                        f"Canaryfly final price missing {field} for {key}"
                    )
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

    document.setdefault("sources", {})["canaryfly"] = (
        "Canaryfly official booking_calendar, booking_search and "
        "booking_getImports GraphQL final totals"
    )
    document["canaryfly_prices_updated_at"] = repaired_at
    document["canaryfly_price_repair"] = {
        "scope": "existing Canaryfly legs and dependent Step 1F totals only",
        "monthly_calendars_recollected": False,
        "other_carriers_recollected": False,
        "source_collection_generated_at": source["generated_at"],
        "collection_run_id": source["collection_coverage"]["run_id"],
        "unique_route_days": len(route_days_from_keys(set(occurrences))),
        "unique_canaryfly_legs": len(occurrences),
        "updated_canaryfly_occurrences": changed_occurrences,
        "unavailable_canaryfly_legs_removed": len(missing),
        "connections_removed_as_unavailable": removed_results,
        "unavailable_canaryfly_flights": [
            {
                "origin": key[0],
                "destination": key[1],
                "departure_at": key[2],
                "arrival_at": key[3],
                "flight_number": key[4],
            }
            for key in missing
        ],
        "source": (
            "official Canaryfly booking_search + booking_getImports GraphQL"
        ),
    }
    validate_document(document)
    return document, {
        "unique_route_days": len(route_days_from_keys(set(occurrences))),
        "unique_canaryfly_legs": len(occurrences),
        "updated_canaryfly_occurrences": changed_occurrences,
        "unavailable_canaryfly_legs_removed": len(missing),
        "connections_removed_as_unavailable": removed_results,
    }


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_optional_coverage_sidecar(
    source_path: Path,
    embedded_coverage: dict[str, Any],
) -> bool:
    sidecar = source_path.with_suffix(".collection-report.json")
    if not sidecar.exists():
        return False
    if json.loads(sidecar.read_text(encoding="utf-8")) != embedded_coverage:
        raise RuntimeError("Step 1F coverage sidecar does not match the current feed")
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
    validate_coverage(source, "1f", start, end)
    if source.get("step") != "1F":
        raise RuntimeError("Input is not a Step 1F feed")
    coverage_sidecar_present = validate_optional_coverage_sidecar(
        source_path,
        source["collection_coverage"],
    )

    saved = saved_canaryfly_legs(source)
    route_days = route_days_from_keys(set(saved))
    eur_pln = float(source["exchange_rates"]["EUR_PLN"]["rate"])
    print(
        f"Do poprawienia: {len(saved)} unikalnych lotów Canaryfly w "
        f"{len(route_days)} trasach/dniach; EUR/PLN {eur_pln:.4f}",
        flush=True,
    )
    live_prices = fetch_current_canaryfly_prices(
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
            raise RuntimeError(
                "Step 1F feed changed during repair; refusing to replace it"
            )
        atomic_json(source_path, repaired)
        if file_sha256(source_path) != report["staged_sha256"]:
            shutil.copy2(backup, source_path)
            raise RuntimeError(
                "Published Step 1F checksum mismatch; restored backup"
            )
        print(f"Podmieniono atomowo {source_path}", flush=True)
    else:
        print("Nie użyto --apply; plik publiczny pozostał bez zmian", flush=True)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
