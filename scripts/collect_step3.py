#!/usr/bin/env python3
"""Build the public Step 3 Ryanair + Ryanair connection feed.

The collector reads the fixed transfer-airport allowlist, checks both travel
directions, requires a 2–24 hour layover, and keeps every valid connection
regardless of price. Price filtering belongs to the website.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable
from zoneinfo import ZoneInfo

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.collection_coverage import collection_entrypoint, publish_document
from scripts.collect_step1 import (
    MAX_LAYOVER_MINUTES,
    MIN_LAYOVER_MINUTES,
    CurrencyRate,
    POLISH_AIRPORTS,
    TENERIFE_AIRPORTS,
    configure_airports_from_allowlist,
    dt,
    nbp_rate,
)
from scripts.collect_step2 import collect_ryanair_route, ryanair_client_version
from scripts.search_airports import validate_polish_transfer


ROOT = Path(__file__).resolve().parents[1]
TRANSFER_FILE = ROOT / "data" / "ryanair-transfer-airports.json"
DEFAULT_OUTPUT = ROOT / "data" / "step3-results.json"
SOURCE_CURRENCIES = ("EUR", "GBP", "HUF", "MAD", "PLN")


def cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--days", type=int, default=30, help="Number of days after from-date, inclusive")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def load_allowlist(path: Path = TRANSFER_FILE) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def route_matrix(allowlist: dict[str, Any]) -> list[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for transfer in allowlist["airports"]:
        code = transfer["iata"]
        for tenerife in transfer["tenerife_airports"]:
            routes.add((tenerife, code))
            routes.add((code, tenerife))
        for polish in transfer["polish_airports"]:
            validate_polish_transfer(polish, code, "step3")
            routes.add((polish, code))
            routes.add((code, polish))
    return sorted(routes)


def collect_routes(
    routes: Iterable[tuple[str, str]],
    start: date,
    end: date,
    rates: dict[str, CurrencyRate],
    client_version: str,
    workers: int,
) -> list[dict[str, Any]]:
    ordered = list(routes)
    legs: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(
                collect_ryanair_route,
                origin,
                destination,
                start,
                end,
                rates,
                client_version,
            ): (origin, destination)
            for origin, destination in ordered
        }
        done = 0
        for future in as_completed(futures):
            done += 1
            origin, destination = futures[future]
            route_legs = future.result()
            if route_legs:
                print(f"Ryanair: {origin}-{destination}: {len(route_legs)}", flush=True)
                legs.extend(route_legs)
            if done % 20 == 0 or done == len(futures):
                print(f"Trasy Ryanair: {done}/{len(futures)}", flush=True)
    return legs


def discounted_leg(
    leg: dict[str, Any],
    transfer: str,
    eligible_transfers: set[str],
) -> dict[str, Any]:
    result = dict(leg)
    is_tenerife_leg = (
        result["departure_airport"] in TENERIFE_AIRPORTS
        or result["arrival_airport"] in TENERIFE_AIRPORTS
    )
    eligible = is_tenerife_leg and transfer in eligible_transfers
    regular = float(result["price_regular_pln"])
    result["resident_discount_eligible"] = eligible
    result["resident_fare_multiplier"] = 0.25 if eligible else 1.0
    result["price_resident_estimated_pln"] = round(regular * result["resident_fare_multiplier"], 2)
    return result


def connection_id(legs: list[dict[str, Any]]) -> str:
    value = "|".join(
        f"{leg['flight_number']}:{leg['departure_at']}:{leg['arrival_at']}"
        for leg in legs
    )
    return f"step3-{hashlib.sha256(value.encode()).hexdigest()[:16]}"


def build_connections(
    legs: list[dict[str, Any]],
    allowlist: dict[str, Any],
) -> list[dict[str, Any]]:
    by_route: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for leg in legs:
        key = (leg["departure_airport"], leg["arrival_airport"])
        by_route.setdefault(key, []).append(leg)

    discount_rule = allowlist["resident_discount_on_tenerife_leg"]
    eligible_transfers = set(discount_rule["eligible_transfer_airports"])
    results: list[dict[str, Any]] = []

    def combine(
        first_routes: list[dict[str, Any]],
        second_routes: list[dict[str, Any]],
        transfer: str,
        direction: str,
    ) -> None:
        for first in first_routes:
            for second in second_routes:
                layover = round((dt(second["departure_at"]) - dt(first["arrival_at"])).total_seconds() / 60)
                if not MIN_LAYOVER_MINUTES <= layover <= MAX_LAYOVER_MINUTES:
                    continue
                connection_legs = [
                    discounted_leg(first, transfer, eligible_transfers),
                    discounted_leg(second, transfer, eligible_transfers),
                ]
                regular_total = round(sum(float(leg["price_regular_pln"]) for leg in connection_legs), 2)
                resident_total = round(
                    sum(float(leg["price_resident_estimated_pln"]) for leg in connection_legs),
                    2,
                )
                results.append({
                    "id": connection_id(connection_legs),
                    "origin_airport": connection_legs[0]["departure_airport"],
                    "destination_airport": connection_legs[-1]["arrival_airport"],
                    "direction": direction,
                    "connection_type": "one_stop",
                    "transfer_airport": transfer,
                    "layover_minutes": layover,
                    "self_transfer": True,
                    "legs": connection_legs,
                    "price_total_regular_pln": regular_total,
                    "price_total_resident_estimated_pln": resident_total,
                })

    for transfer_data in allowlist["airports"]:
        transfer = transfer_data["iata"]
        for tenerife in transfer_data["tenerife_airports"]:
            for polish in transfer_data["polish_airports"]:
                combine(
                    by_route.get((tenerife, transfer), []),
                    by_route.get((transfer, polish), []),
                    transfer,
                    "tenerife_to_poland",
                )
                combine(
                    by_route.get((polish, transfer), []),
                    by_route.get((transfer, tenerife), []),
                    transfer,
                    "poland_to_tenerife",
                )

    unique = {result["id"]: result for result in results}
    return sorted(
        unique.values(),
        key=lambda result: (
            result["legs"][0]["departure_at"],
            result["price_total_regular_pln"],
            result["id"],
        ),
    )


def validate_document(document: dict[str, Any], allowlist: dict[str, Any]) -> None:
    results = document["results"]
    if not results:
        raise RuntimeError("Collector produced no Step 3 connections")
    directions = {result["direction"] for result in results}
    if directions != {"tenerife_to_poland", "poland_to_tenerife"}:
        raise RuntimeError(f"Both directions are required; got {sorted(directions)}")

    transfer_rules = {airport["iata"]: airport for airport in allowlist["airports"]}
    eligible_transfers = set(
        allowlist["resident_discount_on_tenerife_leg"]["eligible_transfer_airports"]
    )
    for result in results:
        if result["connection_type"] != "one_stop" or len(result["legs"]) != 2:
            raise RuntimeError(f"Step 3 result must contain two legs: {result['id']}")
        if not MIN_LAYOVER_MINUTES <= result["layover_minutes"] <= MAX_LAYOVER_MINUTES:
            raise RuntimeError(f"Invalid layover in {result['id']}")
        transfer = result["transfer_airport"]
        if transfer not in transfer_rules:
            raise RuntimeError(f"Transfer outside Step 3 allowlist in {result['id']}")
        rule = transfer_rules[transfer]
        if result["origin_airport"] in POLISH_AIRPORTS:
            polish = result["origin_airport"]
            tenerife = result["destination_airport"]
        else:
            polish = result["destination_airport"]
            tenerife = result["origin_airport"]
        validate_polish_transfer(polish, transfer, "step3")
        if polish not in rule["polish_airports"] or tenerife not in rule["tenerife_airports"]:
            raise RuntimeError(f"Route outside Step 3 allowlist in {result['id']}")
        for leg in result["legs"]:
            if leg["carrier"] != "Ryanair" or not leg.get("booking_url"):
                raise RuntimeError(f"Invalid Ryanair leg in {result['id']}")
            is_tenerife_leg = (
                leg["departure_airport"] in TENERIFE_AIRPORTS
                or leg["arrival_airport"] in TENERIFE_AIRPORTS
            )
            expected_eligible = is_tenerife_leg and transfer in eligible_transfers
            if leg["resident_discount_eligible"] != expected_eligible:
                raise RuntimeError(f"Incorrect resident discount in {result['id']}")


@collection_entrypoint("3")
def main(args) -> None:
    if args.days < 0:
        raise SystemExit("--days must be non-negative")
    if args.workers < 1:
        raise SystemExit("--workers must be positive")

    end = args.from_date + timedelta(days=args.days)
    allowlist = load_allowlist()
    configure_airports_from_allowlist(allowlist)
    routes = route_matrix(allowlist)
    rates = {code: nbp_rate(code, args.from_date) for code in SOURCE_CURRENCIES}
    print(
        "Kursy NBP: "
        + ", ".join(f"{code}={rate.pln:.4f} PLN" for code, rate in rates.items()),
        flush=True,
    )
    print(f"Trasy z zapisanej listy: {len(routes)}", flush=True)

    client_version = ryanair_client_version()
    print("Ryanair source: Google Flights HTTP (FR + RK, max 2 requests)", flush=True)
    legs = collect_routes(routes, args.from_date, end, rates, client_version, args.workers)
    print(f"Odcinki Ryanair: {len(legs)}", flush=True)
    results = build_connections(legs, allowlist)

    discount_rule = allowlist["resident_discount_on_tenerife_leg"]
    document = {
        "schema_version": 2,
        "generated_at": datetime.now(ZoneInfo("Atlantic/Canary")).isoformat(timespec="seconds"),
        "period_from": args.from_date.isoformat(),
        "period_to": end.isoformat(),
        "step": 3,
        "directions": ["tenerife_to_poland", "poland_to_tenerife"],
        "transfer_airports": [airport["iata"] for airport in allowlist["airports"]],
        "carriers": ["Ryanair"],
        "layover_minutes": {
            "minimum": MIN_LAYOVER_MINUTES,
            "maximum": MAX_LAYOVER_MINUTES,
        },
        "resident_discount": {
            "eligible_transfer_airports": discount_rule["eligible_transfer_airports"],
            "eligible_fare_multiplier": discount_rule["eligible_fare_multiplier"],
            "ineligible_fare_multiplier": discount_rule["ineligible_fare_multiplier"],
            "applies_only_to_tenerife_leg": True,
        },
        "price_filtering": {
            "applied_during_collection": False,
            "controlled_by": "website",
        },
        "exchange_rates": {
            f"{code}_PLN": {
                "rate": rate.pln,
                "source": "NBP tabela A/B" if code != "PLN" else "wartość bazowa",
                "effective_for": args.from_date.isoformat(),
            }
            for code, rate in rates.items()
        },
        "sources": {
            "allowlist": "data/ryanair-transfer-airports.json",
            "ryanair": "Google Flights HTTP individual Ryanair offers (FR and RK)",
        },
        "results": results,
    }
    validate_document(document, allowlist)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    publish_document(document, args.output)
    counts = {
        direction: sum(result["direction"] == direction for result in results)
        for direction in document["directions"]
    }
    print(f"Zapisano {len(results)} połączeń do {args.output}", flush=True)
    print(json.dumps(counts, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
