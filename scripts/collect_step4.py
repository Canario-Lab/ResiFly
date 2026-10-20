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

from scripts.booking_urls import wizz_booking_url
from scripts.collect_step1 import (
    AIRPORT_TIMEZONES,
    MAX_LAYOVER_MINUTES,
    MIN_LAYOVER_MINUTES,
    CurrencyRate,
    POLISH_AIRPORTS,
    TENERIFE_AIRPORTS,
    WIZZ_ROUTE_SCHEDULE as STEP1_WIZZ_ROUTE_SCHEDULE,
    dt,
    local_datetime,
    money_pln,
    nbp_rate,
    serialize_datetime,
)
from scripts.collect_step2 import wizz_timetable


ROOT = Path(__file__).resolve().parents[1]
TRANSFER_FILE = ROOT / "data" / "wizzair-transfer-airports.json"
DEFAULT_OUTPUT = ROOT / "data" / "step4-results.json"
SOURCE_CURRENCIES = ("EUR", "HUF", "PLN", "RON")

# Wizz's public timetable price endpoint exposes the departure time and fare,
# but not the flight number or arrival time. The route map below completes the
# official response with published flight identifiers and block times. If a
# newly active allowlisted route has no verified schedule, collection fails
# loudly instead of inventing a flight number or an arrival time.
WIZZ_ROUTE_SCHEDULES: dict[tuple[str, str], tuple[str, int]] = {
    **STEP1_WIZZ_ROUTE_SCHEDULE,
    ("AGA", "KTW"): ("W61078", 285),
    ("KTW", "AGA"): ("W61077", 235),
    ("AGA", "WAW"): ("W61600", 300),
    ("WAW", "AGA"): ("W61599", 260),
    ("AGP", "KRK"): ("W62074", 220),
    ("KRK", "AGP"): ("W62073", 235),
    ("AGP", "KTW"): ("W61074", 220),
    ("KTW", "AGP"): ("W61073", 230),
    ("AGP", "WAW"): ("W61360", 230),
    ("WAW", "AGP"): ("W61359", 250),
    ("BGY", "WMI"): ("W61402", 115),
    ("WMI", "BGY"): ("W61401", 125),
    ("BGY", "WAW"): ("W61432", 120),
    ("WAW", "BGY"): ("W61431", 125),
    ("BLQ", "WAW"): ("W61466", 120),
    ("WAW", "BLQ"): ("W61465", 125),
    ("BBU", "KRK"): ("W62058", 105),
    ("KRK", "BBU"): ("W62057", 100),
    ("BBU", "WAW"): ("W61584", 110),
    ("WAW", "BBU"): ("W61583", 105),
    ("BUD", "KRK"): ("W62419", 75),
    ("KRK", "BUD"): ("W62420", 70),
    ("BUD", "TFS"): ("W62493", 340),
    ("TFS", "BUD"): ("W62494", 305),
    ("BUD", "WAW"): ("W62467", 75),
    ("WAW", "BUD"): ("W62468", 80),
    ("CRL", "WAW"): ("W61382", 120),
    ("WAW", "CRL"): ("W61381", 130),
    ("EIN", "KRK"): ("W62076", 110),
    ("KRK", "EIN"): ("W62075", 120),
    ("EIN", "KTW"): ("W61072", 105),
    ("KTW", "EIN"): ("W61071", 115),
    ("EIN", "WAW"): ("W61372", 110),
    ("WAW", "EIN"): ("W61371", 125),
    ("FCO", "KRK"): ("W62062", 130),
    ("KRK", "FCO"): ("W62061", 125),
    ("FCO", "KTW"): ("W61046", 130),
    ("KTW", "FCO"): ("W61045", 130),
    ("FCO", "TFS"): ("W46035", 285),
    ("TFS", "FCO"): ("W46036", 270),
    ("FCO", "WAW"): ("W61442", 160),
    ("WAW", "FCO"): ("W61441", 150),
    ("GDN", "TFS"): ("W61709", 365),
    ("TFS", "GDN"): ("W61710", 330),
    ("KTW", "LTN"): ("W61001", 150),
    ("LTN", "KTW"): ("W61002", 140),
    ("KTW", "NAP"): ("W61049", 130),
    ("NAP", "KTW"): ("W61050", 130),
    ("KTW", "OPO"): ("W61085", 225),
    ("OPO", "KTW"): ("W61086", 205),
    ("LBA", "WAW"): ("W61316", 150),
    ("WAW", "LBA"): ("W61315", 160),
    ("LPL", "WAW"): ("W61312", 155),
    ("WAW", "LPL"): ("W61311", 170),
    ("KRK", "LTN"): ("W62001", 160),
    ("LTN", "KRK"): ("W62002", 145),
    ("LTN", "WAW"): ("W61302", 145),
    ("WAW", "LTN"): ("W61301", 160),
    ("KRK", "MXP"): ("W62067", 115),
    ("MXP", "KRK"): ("W62068", 110),
    ("MXP", "TFS"): ("W46323", 285),
    ("TFS", "MXP"): ("W46324", 260),
    ("MXP", "WAW"): ("W46387", 135),
    ("WAW", "MXP"): ("W46388", 135),
    ("NAP", "WAW"): ("W61458", 130),
    ("WAW", "NAP"): ("W61457", 145),
    ("OPO", "WAW"): ("W61596", 220),
    ("WAW", "OPO"): ("W61595", 245),
    ("OTP", "TFS"): ("W43021", 375),
    ("TFS", "OTP"): ("W43022", 330),
    ("SCQ", "TFN"): ("W47465", 160),
    ("TFN", "SCQ"): ("W47466", 175),
    ("SCQ", "WMI"): ("W61408", 220),
    ("WMI", "SCQ"): ("W61407", 230),
    ("PSA", "WAW"): ("W61468", 130),
    ("WAW", "PSA"): ("W61467", 135),
    ("RAK", "WAW"): ("W61598", 285),
    ("WAW", "RAK"): ("W61597", 245),
}

# Some routes have more than one Wizz flight number. The timetable API still
# identifies the departure time, which is enough to choose the published
# service deterministically for the current schedule.
WIZZ_FLIGHT_NUMBERS_BY_TIME: dict[tuple[str, str, str], str] = {
    ("BGY", "WAW", "20:30"): "W61434",
    ("BGY", "WAW", "20:40"): "W61434",
    ("BGY", "WAW", "20:50"): "W61434",
    ("BGY", "WAW", "20:55"): "W61434",
    ("BGY", "WAW", "21:00"): "W61434",
    ("WAW", "BGY", "17:45"): "W61433",
    ("WAW", "BGY", "18:00"): "W61433",
    ("BUD", "WAW", "20:25"): "W62469",
    ("WAW", "BUD", "22:05"): "W62470",
    ("WAW", "CRL", "17:30"): "W61383",
    ("WAW", "CRL", "17:50"): "W61383",
    ("FCO", "KRK", "05:30"): "W42032",
    ("FCO", "KRK", "05:40"): "W42032",
    ("FCO", "KRK", "16:15"): "W62032",
    ("KRK", "FCO", "08:15"): "W42031",
    ("KRK", "FCO", "08:25"): "W42031",
    ("KRK", "FCO", "08:55"): "W42031",
    ("KRK", "FCO", "13:30"): "W62031",
    ("FCO", "WAW", "18:20"): "W41446",
    ("FCO", "WAW", "18:25"): "W41446",
    ("FCO", "WAW", "18:30"): "W41446",
    ("FCO", "WAW", "20:35"): "W61446",
    ("WAW", "FCO", "21:20"): "W41445",
    ("WAW", "FCO", "21:25"): "W41445",
    ("WAW", "FCO", "21:30"): "W41445",
    ("MXP", "WAW", "21:05"): "W66389",
    ("WAW", "MXP", "13:30"): "W66390",
    ("WAW", "MXP", "18:15"): "W66390",
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
            routes.add((polish, code))
            routes.add((code, polish))
    return sorted(routes)


def schedule_for(origin: str, destination: str, departure: datetime) -> tuple[str, int]:
    try:
        default_number, duration_minutes = WIZZ_ROUTE_SCHEDULES[(origin, destination)]
    except KeyError as error:
        raise RuntimeError(
            f"Wizz Air returned a newly active allowlisted route {origin}-{destination}; "
            "add its verified flight number and duration to WIZZ_ROUTE_SCHEDULES"
        ) from error
    time_key = departure.strftime("%H:%M")
    number = WIZZ_FLIGHT_NUMBERS_BY_TIME.get(
        (origin, destination, time_key),
        default_number,
    )
    return number, duration_minutes


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
    result["price_resident_estimated_pln"] = round(
        regular * result["resident_fare_multiplier"],
        2,
    )
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
                    discounted_leg(first, transfer, eligible_transfers),
                    discounted_leg(second, transfer, eligible_transfers),
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


def main() -> None:
    args = cli()
    if args.days < 0:
        raise SystemExit("--days must be non-negative")
    if args.workers < 1:
        raise SystemExit("--workers must be positive")

    end = args.from_date + timedelta(days=args.days)
    allowlist = load_allowlist()
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
    results = build_connections(legs, allowlist)

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
        },
        "results": results,
    }
    validate_document(document, allowlist)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    counts = {
        direction: sum(result["direction"] == direction for result in results)
        for direction in document["directions"]
    }
    print(f"Zapisano {len(results)} połączeń do {args.output}", flush=True)
    print(json.dumps(counts, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
