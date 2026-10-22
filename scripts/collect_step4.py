#!/usr/bin/env python3
"""Build the public Step 4 Wizz Air + Wizz Air connection feed.

The collector reads the fixed Step 4 transfer-airport allowlist, checks both
travel directions, requires a 2–24 hour layover, and keeps every valid
connection regardless of price. Price filtering belongs to the website.
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

from scripts.collection_coverage import collection_entrypoint, publish_document, calendar_collector
from scripts.booking_urls import wizz_booking_url
from scripts.search_airports import validate_polish_transfer
from scripts.collect_step1 import (
    AIRPORT_TIMEZONES,
    MAX_LAYOVER_MINUTES,
    MIN_LAYOVER_MINUTES,
    CurrencyRate,
    POLISH_AIRPORTS,
    TRANSFER_FILE as STEP1_TRANSFER_FILE,
    TENERIFE_AIRPORTS,
    configure_airports_from_allowlist,
    dt,
    local_datetime,
    money_pln,
    nbp_rate,
    serialize_datetime,
    wizz_schedules_from_allowlist,
)
from scripts.collect_step2 import wizz_timetable
from scripts.spanish_resident_fees import (
    apply_resident_price_estimate,
    validate_resident_price_estimate,
)
from scripts.wizz_schedules import WIZZ_ROUTE_FILE, load_wizz_route_data, resolve_schedule


ROOT = Path(__file__).resolve().parents[1]
TRANSFER_FILE = ROOT / "data" / "wizzair-transfer-airports.json"
DEFAULT_OUTPUT = ROOT / "data" / "step4-results.json"
SOURCE_CURRENCIES = ("EUR", "HUF", "PLN", "RON")
STEP1_ALLOWLIST = json.loads(STEP1_TRANSFER_FILE.read_text(encoding="utf-8"))

_SHARED_WIZZ_SCHEDULES, WIZZ_FLIGHT_NUMBERS_BY_TIME = load_wizz_route_data()
WIZZ_ROUTE_SCHEDULES: dict[tuple[str, str], tuple[str, int]] = {
    **wizz_schedules_from_allowlist(STEP1_ALLOWLIST),
    **_SHARED_WIZZ_SCHEDULES,
}


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
            validate_polish_transfer(polish, code, "step4")
            routes.add((polish, code))
            routes.add((code, polish))
    return sorted(routes)


def schedule_for(origin: str, destination: str, departure: datetime) -> tuple[str, int]:
    return resolve_schedule(WIZZ_ROUTE_SCHEDULES, WIZZ_FLIGHT_NUMBERS_BY_TIME, origin, destination, departure)


@calendar_collector("Wizz Air", "timetableV2")
def collect_wizz_route(
    origin: str,
    destination: str,
    start: date,
    end: date,
    rates: dict[str, CurrencyRate],
) -> list[dict[str, Any]]:
    regular = wizz_timetable(origin, destination, start, end, "regular")
    if not regular:
        return []
    club = wizz_timetable(origin, destination, start, end, "wdc")
    club_by_departure = {item["departureDate"]: item for item in club}
    legs: list[dict[str, Any]] = []
    for item in regular:
        departure = local_datetime(item["departureDate"], origin)
        flight_number, duration_minutes = schedule_for(origin, destination, departure)
        arrival = (departure + timedelta(minutes=duration_minutes)).astimezone(
            ZoneInfo(AIRPORT_TIMEZONES[destination])
        )
        price = item["price"]
        regular_pln = money_pln(price["amount"], price["currencyCode"], rates)
        club_item = club_by_departure.get(item["departureDate"])
        club_price = None
        if club_item:
            club_price = money_pln(
                club_item["price"]["amount"],
                club_item["price"]["currencyCode"],
                rates,
            )
        legs.append({
            "carrier": "Wizz Air",
            "flight_number": flight_number,
            "departure_airport": origin,
            "departure_at": serialize_datetime(departure),
            "arrival_airport": destination,
            "arrival_at": serialize_datetime(arrival),
            "price_regular_pln": regular_pln,
            "price_wizz_discount_club_pln": club_price,
            "resident_discount_eligible": False,
            "resident_fare_multiplier": 1.0,
            "price_resident_estimated_pln": regular_pln,
            "booking_url": wizz_booking_url(origin, destination, departure),
            "price_source_currency": price["currencyCode"],
            "price_source_amount": float(price["amount"]),
        })
    return legs


def collect_routes(
    routes: Iterable[tuple[str, str]],
    start: date,
    end: date,
    rates: dict[str, CurrencyRate],
    workers: int,
) -> list[dict[str, Any]]:
    ordered = list(routes)
    legs: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(collect_wizz_route, origin, destination, start, end, rates): (
                origin,
                destination,
            )
            for origin, destination in ordered
        }
        done = 0
        for future in as_completed(futures):
            done += 1
            origin, destination = futures[future]
            route_legs = future.result()
            if route_legs:
                print(f"Wizz Air: {origin}-{destination}: {len(route_legs)}", flush=True)
                legs.extend(route_legs)
            if done % 10 == 0 or done == len(futures):
                print(f"Trasy Wizz Air: {done}/{len(futures)}", flush=True)
    return legs


def discounted_leg(
    leg: dict[str, Any],
    transfer: str,
    eligible_transfers: set[str],
    eur_pln: float,
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
    result["price_resident_estimated_pln"] = regular
    if eligible:
        apply_resident_price_estimate(result, eur_pln)
    return result


def connection_id(legs: list[dict[str, Any]]) -> str:
    value = "|".join(
        f"{leg['flight_number']}:{leg['departure_at']}:{leg['arrival_at']}"
        for leg in legs
    )
    return f"step4-{hashlib.sha256(value.encode()).hexdigest()[:16]}"


def build_connections(
    legs: list[dict[str, Any]],
    allowlist: dict[str, Any],
    eur_pln: float,
) -> list[dict[str, Any]]:
    by_route: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for leg in legs:
        key = (leg["departure_airport"], leg["arrival_airport"])
        by_route.setdefault(key, []).append(leg)

    eligible_transfers = set(
        allowlist["resident_discount_on_tenerife_leg"]["eligible_transfer_airports"]
    )
    results: list[dict[str, Any]] = []

    def combine(
        first_routes: list[dict[str, Any]],
        second_routes: list[dict[str, Any]],
        transfer: str,
        direction: str,
    ) -> None:
        for first in first_routes:
            for second in second_routes:
                layover = round(
                    (dt(second["departure_at"]) - dt(first["arrival_at"])).total_seconds()
                    / 60
                )
                if not MIN_LAYOVER_MINUTES <= layover <= MAX_LAYOVER_MINUTES:
                    continue
                connection_legs = [
                    discounted_leg(first, transfer, eligible_transfers, eur_pln),
                    discounted_leg(second, transfer, eligible_transfers, eur_pln),
                ]
                regular_total = round(
                    sum(float(leg["price_regular_pln"]) for leg in connection_legs),
                    2,
                )
                resident_total = round(
                    sum(float(leg["price_resident_estimated_pln"]) for leg in connection_legs),
                    2,
                )
                club_prices = [
                    leg.get("price_wizz_discount_club_pln")
                    for leg in connection_legs
                ]
                club_total = None
                if all(price is not None for price in club_prices):
                    club_total = round(sum(float(price) for price in club_prices), 2)
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
                    "price_total_wizz_discount_club_pln": club_total,
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
        raise RuntimeError("Collector produced no Step 4 connections")
    directions = {result["direction"] for result in results}
    if directions != {"tenerife_to_poland", "poland_to_tenerife"}:
        raise RuntimeError(f"Both directions are required; got {sorted(directions)}")

    transfer_rules = {airport["iata"]: airport for airport in allowlist["airports"]}
    eligible_transfers = set(
        allowlist["resident_discount_on_tenerife_leg"]["eligible_transfer_airports"]
    )
    for result in results:
        if result["connection_type"] != "one_stop" or len(result["legs"]) != 2:
            raise RuntimeError(f"Step 4 result must contain two legs: {result['id']}")
        if not MIN_LAYOVER_MINUTES <= result["layover_minutes"] <= MAX_LAYOVER_MINUTES:
            raise RuntimeError(f"Invalid layover in {result['id']}")
        transfer = result["transfer_airport"]
        if transfer not in transfer_rules:
            raise RuntimeError(f"Transfer outside Step 4 allowlist in {result['id']}")
        rule = transfer_rules[transfer]
        if result["origin_airport"] in POLISH_AIRPORTS:
            polish = result["origin_airport"]
            tenerife = result["destination_airport"]
        else:
            polish = result["destination_airport"]
            tenerife = result["origin_airport"]
        validate_polish_transfer(polish, transfer, "step4")
        if polish not in rule["polish_airports"] or tenerife not in rule["tenerife_airports"]:
            raise RuntimeError(f"Route outside Step 4 allowlist in {result['id']}")
        for leg in result["legs"]:
            if leg["carrier"] != "Wizz Air" or not leg.get("booking_url"):
                raise RuntimeError(f"Invalid Wizz Air leg in {result['id']}")
            is_tenerife_leg = (
                leg["departure_airport"] in TENERIFE_AIRPORTS
                or leg["arrival_airport"] in TENERIFE_AIRPORTS
            )
            expected_eligible = is_tenerife_leg and transfer in eligible_transfers
            if leg["resident_discount_eligible"] != expected_eligible:
                raise RuntimeError(f"Incorrect resident discount in {result['id']}")
            if expected_eligible:
                validate_resident_price_estimate(leg)


@collection_entrypoint("4")
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
    legs = collect_routes(routes, args.from_date, end, rates, args.workers)
    print(f"Odcinki Wizz Air: {len(legs)}", flush=True)
    results = build_connections(legs, allowlist, rates["EUR"].pln)

    discount_rule = allowlist["resident_discount_on_tenerife_leg"]
    document = {
        "schema_version": 2,
        "generated_at": datetime.now(ZoneInfo("Atlantic/Canary")).isoformat(timespec="seconds"),
        "period_from": args.from_date.isoformat(),
        "period_to": end.isoformat(),
        "step": 4,
        "directions": ["tenerife_to_poland", "poland_to_tenerife"],
        "transfer_airports": [airport["iata"] for airport in allowlist["airports"]],
        "carriers": ["Wizz Air"],
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
            "allowlist": "data/wizzair-transfer-airports.json",
            "wizz_air": "Wizz Air public timetableV2 API",
            "schedule_map": "verified route flight numbers and published block times in scripts/collect_step4.py",
            "resident_price_estimate": "25% of fare component plus fixed Aena fees",
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
