#!/usr/bin/env python3
"""Build the public Step 2 feed of direct Poland–Tenerife flights.

The collector checks the complete configured airport matrix in both directions,
uses current Wizz Air and Ryanair prices, and deliberately applies no price
limit. Price filtering belongs to the website.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time as time_module
from typing import Any, Iterable
import uuid
from zoneinfo import ZoneInfo

from curl_cffi import requests

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.collection_coverage import collection_entrypoint, publish_document, calendar_collector
from scripts.booking_urls import ryanair_booking_url, wizz_booking_url
from scripts.ryanair_google import collect_route_days as collect_ryanair_google_route_days
from scripts.wizz_api import wizz_api_base
from scripts.wizz_schedules import load_wizz_route_data, resolve_schedule
from scripts.collect_step1 import (
    AIRPORT_TIMEZONES,
    CurrencyRate,
    POLISH_AIRPORTS,
    TENERIFE_AIRPORTS,
    local_datetime,
    money_pln,
    nbp_eur_rate,
    serialize_datetime,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "step2-results.json"
RYANAIR_DATES_API = "https://www.ryanair.com/api/farfnd/v4/oneWayFares"
RYANAIR_AVAILABILITY_API = "https://www.ryanair.com/api/booking/v4/en-gb/availability"
RYANAIR_VERSION_PAGE = "https://www.ryanair.com/ie/en/trip/flights/select"

# The same verified data is used by direct and transfer collectors.
WIZZ_DIRECT_SCHEDULES, WIZZ_DIRECT_OVERRIDES = load_wizz_route_data()


def cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--days", type=int, default=30, help="Number of days after from-date, inclusive")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def route_matrix() -> Iterable[tuple[str, str]]:
    for polish in POLISH_AIRPORTS:
        for tenerife in TENERIFE_AIRPORTS:
            yield polish, tenerife
            yield tenerife, polish


def wizz_timetable(
    origin: str,
    destination: str,
    start: date,
    end: date,
    price_type: str,
) -> list[dict[str, Any]]:
    payload = {
        "flightList": [{
            "departureStation": origin,
            "arrivalStation": destination,
            "from": start.isoformat(),
            "to": end.isoformat(),
        }],
        "adultCount": 1,
        "childCount": 0,
        "infantCount": 0,
        "priceType": price_type,
    }
    last_error: Exception | None = None
    max_attempts = 6
    for attempt in range(max_attempts):
        try:
            from scripts.source_scheduler import http_request
            response = http_request(requests.post,
                f"{wizz_api_base()}/search/timetableV2",
                headers={"content-type": "application/json"},
                json=payload,
                impersonate="safari184",
                timeout=60,
            )
            if response.status_code == 400 and "InvalidMarket" in response.text:
                return []
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict) or not isinstance(body.get("outboundFlights"), list):
                raise RuntimeError(f"Invalid Wizz timetable response {origin}-{destination}")
            return [
                item
                for item in body.get("outboundFlights", [])
                if item.get("departureStation") == origin
                and item.get("arrivalStation") == destination
                and item.get("priceType") == "price"
                and float(item.get("price", {}).get("amount") or 0) > 0
            ]
        except Exception as error:
            from scripts.source_scheduler import raise_if_stopped
            raise_if_stopped()
            last_error = error
            if attempt + 1 < max_attempts:
                # The public timetable endpoint intermittently returns 503
                # during a complete multi-route scan. Longer exponential
                # backoff prevents a transient throttle from discarding the
                # otherwise complete calendar.
                from scripts.source_scheduler import retry_delay
                time_module.sleep(max(min(3 * (2 ** attempt), 30), retry_delay(attempt, error)))
    raise RuntimeError(f"Wizz Air request failed for {origin}-{destination}") from last_error


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
    schedule = WIZZ_DIRECT_SCHEDULES.get((origin, destination))
    if schedule is None:
        raise RuntimeError(
            f"Wizz Air returned a new direct route {origin}-{destination}; "
            "add its verified flight number and duration to data/wizz-route-schedules.json"
        )
    club = wizz_timetable(origin, destination, start, end, "wdc")
    club_by_departure = {item["departureDate"]: item for item in club}
    legs: list[dict[str, Any]] = []
    for item in regular:
        departure = local_datetime(item["departureDate"], origin)
        number, duration = resolve_schedule(WIZZ_DIRECT_SCHEDULES, WIZZ_DIRECT_OVERRIDES, origin, destination, departure)
        arrival = (departure + timedelta(minutes=duration)).astimezone(
            ZoneInfo(AIRPORT_TIMEZONES[destination])
        )
        price = item["price"]
        club_item = club_by_departure.get(item["departureDate"])
        club_price = None
        if club_item:
            club_price = money_pln(
                club_item["price"]["amount"],
                club_item["price"]["currencyCode"],
                rates,
            )
        regular_pln = money_pln(price["amount"], price["currencyCode"], rates)
        legs.append({
            "carrier": "Wizz Air",
            "flight_number": number,
            "departure_airport": origin,
            "departure_at": serialize_datetime(departure),
            "arrival_airport": destination,
            "arrival_at": serialize_datetime(arrival),
            "price_regular_pln": regular_pln,
            "price_wizz_discount_club_pln": club_price,
            "resident_discount_eligible": False,
            "price_resident_estimated_pln": regular_pln,
            "booking_url": wizz_booking_url(origin, destination, departure),
            "price_source_currency": price["currencyCode"],
            "price_source_amount": float(price["amount"]),
        })
    return legs


def ryanair_client_version() -> str:
    """Compatibility token for callers that still pass a source identifier."""
    return "google-flights-http"


def ryanair_available_dates(origin: str, destination: str) -> list[date]:
    url = f"{RYANAIR_DATES_API}/{origin}/{destination}/availabilities"
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = requests.get(url, impersonate="safari184", timeout=60)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list) or any(not isinstance(value, str) for value in payload):
                raise RuntimeError("Invalid Ryanair active-dates response")
            return sorted({date.fromisoformat(value) for value in payload})
        except Exception as error:
            last_error = error
            if attempt < 3:
                time_module.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Ryanair active dates failed for {origin}-{destination}") from last_error


def ryanair_windows(active_dates: list[date], start: date, end: date) -> list[date]:
    remaining = sorted(day for day in active_dates if start <= day <= end)
    centers: list[date] = []
    while remaining:
        first = remaining[0]
        # Ryanair accepts at most two flexible days before the requested date.
        # A 2+4 window still retrieves seven calendar days per request.
        center = min(first + timedelta(days=2), end)
        centers.append(center)
        covered_to = center + timedelta(days=4)
        remaining = [day for day in remaining if day > covered_to]
    return centers


def ryanair_availability(
    origin: str,
    destination: str,
    center: date,
    client_version: str,
    *,
    exact_day: bool = False,
) -> dict[str, Any]:
    params = {
        "ADT": 1,
        "CHD": 0,
        "DateIn": "",
        "DateOut": center.isoformat(),
        "Destination": destination,
        "Disc": 0,
        "INF": 0,
        "Origin": origin,
        "TEEN": 0,
        "promoCode": "",
        "IncludeConnectingFlights": "false",
        "FlexDaysBeforeOut": 0 if exact_day else 2,
        "FlexDaysOut": 0 if exact_day else 4,
        "FlexDaysBeforeIn": 2,
        "FlexDaysIn": 2,
        "RoundTrip": "false",
        "ToUs": "AGREED",
    }
    last_error = ""
    for attempt in range(5):
        headers = {
            "client": "desktop",
            "client-version": client_version,
            "cookie": f"fr-correlation-id={uuid.uuid4()}",
        }
        try:
            response = requests.get(
                RYANAIR_AVAILABILITY_API,
                params=params,
                headers=headers,
                impersonate="chrome",
                timeout=60,
            )
            if response.status_code < 400:
                return response.json()
            last_error = f"HTTP {response.status_code}: {response.text[:300]}"
            if response.status_code == 409 and "Availability declined" in response.text:
                break
            if response.status_code not in {409, 429} and response.status_code < 500:
                break
        except Exception as error:
            last_error = str(error)
        if attempt < 4:
            time_module.sleep(2 * (attempt + 1))
    raise RuntimeError(
        f"Ryanair availability failed for {origin}-{destination} "
        f"around {center}: {last_error}"
    )


def collect_ryanair_farefinder_dates(
    origin: str,
    destination: str,
    active_dates: list[date],
    start: date,
    end: date,
    rates: dict[str, CurrencyRate],
) -> list[dict[str, Any]]:
    """Legacy entry point: a minimum fare cannot certify all flight times."""
    raise RuntimeError(
        f"Ryanair {origin}-{destination} {start}..{end}: Fare Finder is not a "
        "complete flight source; publication blocked. Full availability is required."
    )




@calendar_collector("Ryanair", "google_flights_http")
def collect_ryanair_route(
    origin: str,
    destination: str,
    start: date,
    end: date,
    rates: dict[str, CurrencyRate],
    client_version: str,
) -> list[dict[str, Any]]:
    # ``rates`` and ``client_version`` remain in the signature so the shared
    # Step 1/3/5 call sites stay stable. Google already returns PLN and the
    # persistent route/day cache is shared by all collectors in the batch.
    del rates, client_version
    return collect_ryanair_google_route_days(origin, destination, start, end)


def validate_ryanair_calendar(payload, origin, destination, expected_days):
    if not isinstance(payload, dict) or not isinstance(payload.get("currency"), str) or not payload["currency"] or not isinstance(payload.get("trips"), list):
        raise RuntimeError(f"Invalid Ryanair calendar {origin}-{destination}")
    covered = set()
    for trip in payload["trips"]:
        if not isinstance(trip, dict) or trip.get("origin") != origin or trip.get("destination") != destination or not isinstance(trip.get("dates"), list):
            raise RuntimeError(f"Invalid Ryanair trip {origin}-{destination}")
        for day in trip["dates"]:
            if not isinstance(day, dict) or not isinstance(day.get("flights"), list):
                raise RuntimeError(f"Invalid Ryanair day {origin}-{destination}")
            try:
                departure_day = date.fromisoformat(day["dateOut"][:10])
                covered.add(departure_day)
            except (KeyError, TypeError, ValueError) as error:
                raise RuntimeError(f"Invalid Ryanair date {origin}-{destination}") from error
            for flight in day["flights"]:
                if (not isinstance(flight, dict) or "regularFare" not in flight
                        or not isinstance(flight.get("segments"), list)):
                    raise RuntimeError(f"Malformed Ryanair flight {origin}-{destination} on {departure_day}")
                for segment in flight["segments"]:
                    times = segment.get("time") if isinstance(segment, dict) else None
                    if not isinstance(times, list) or len(times) != 2 or str(times[0])[:10] != departure_day.isoformat():
                        raise RuntimeError(f"Mismatched Ryanair flight date/times {origin}-{destination} on {departure_day}")
    missing = expected_days - covered
    if missing:
        raise RuntimeError(f"Incomplete Ryanair calendar {origin}-{destination}; missing dates: {sorted(missing)}")


def _parse_ryanair_calendar(payload, origin, destination, start, end, rates, legs_by_key):
    currency = payload["currency"]
    for trip in payload.get("trips", []):
        if trip.get("origin") != origin or trip.get("destination") != destination:
            continue
        for day in trip.get("dates", []):
            for flight in day.get("flights", []):
                segments = flight.get("segments") or []
                fare = flight.get("regularFare") or {}
                adult_fares = [item for item in fare.get("fares", []) if item.get("type") == "ADT"]
                if not fare:
                    # A fully returned but sold-out flight is not bookable.
                    continue
                if len(segments) != 1 or not adult_fares:
                    raise RuntimeError(f"Malformed Ryanair flight {origin}-{destination}")
                segment = segments[0]
                times = segment.get("time") or []
                if len(times) != 2:
                    raise RuntimeError(f"Missing Ryanair flight times {origin}-{destination}")
                departure = local_datetime(times[0], origin)
                if not start <= departure.date() <= end:
                    continue
                arrival = local_datetime(times[1], destination)
                regular_amount = float(adult_fares[0]["amount"])
                if not math.isfinite(regular_amount) or regular_amount <= 0:
                    raise RuntimeError(f"Invalid Ryanair fare {origin}-{destination}")
                regular_pln = money_pln(regular_amount, currency, rates)
                key = flight.get("flightKey") or (
                    f"{segment.get('flightNumber')}:{departure.isoformat()}:{arrival.isoformat()}"
                )
                legs_by_key[key] = {
                    "carrier": "Ryanair",
                    "flight_number": str(segment.get("flightNumber") or flight["flightNumber"]).replace(" ", ""),
                    "departure_airport": origin,
                    "departure_at": serialize_datetime(departure),
                    "arrival_airport": destination,
                    "arrival_at": serialize_datetime(arrival),
                    "price_regular_pln": regular_pln,
                    "resident_discount_eligible": False,
                    "price_resident_estimated_pln": regular_pln,
                    "booking_url": ryanair_booking_url(origin, destination, departure),
                    "price_source_currency": currency,
                    "price_source_amount": regular_amount,
                }


def result_id(leg: dict[str, Any]) -> str:
    value = f"{leg['carrier']}:{leg['flight_number']}:{leg['departure_at']}:{leg['arrival_at']}"
    return f"step2-{hashlib.sha256(value.encode()).hexdigest()[:16]}"


def build_results(legs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for leg in legs:
        regular = round(float(leg["price_regular_pln"]), 2)
        results.append({
            "id": result_id(leg),
            "origin_airport": leg["departure_airport"],
            "destination_airport": leg["arrival_airport"],
            "direction": (
                "poland_to_tenerife"
                if leg["departure_airport"] in POLISH_AIRPORTS
                else "tenerife_to_poland"
            ),
            "connection_type": "direct",
            "transfer_airport": None,
            "layover_minutes": 0,
            "self_transfer": False,
            "legs": [leg],
            "price_total_regular_pln": regular,
            "price_total_resident_estimated_pln": regular,
        })
    unique = {result["id"]: result for result in results}
    return sorted(
        unique.values(),
        key=lambda result: (
            result["legs"][0]["departure_at"],
            result["price_total_regular_pln"],
            result["id"],
        ),
    )


def validate_document(document: dict[str, Any]) -> None:
    results = document["results"]
    if not results:
        raise RuntimeError("Collector produced no Step 2 direct flights")
    directions = {result["direction"] for result in results}
    if directions != {"tenerife_to_poland", "poland_to_tenerife"}:
        raise RuntimeError(f"Both directions are required; got {sorted(directions)}")
    for result in results:
        if result["connection_type"] != "direct" or len(result["legs"]) != 1:
            raise RuntimeError(f"Step 2 result must contain exactly one direct leg: {result['id']}")
        leg = result["legs"][0]
        if leg["carrier"] not in {"Wizz Air", "Ryanair"}:
            raise RuntimeError(f"Unsupported Step 2 carrier in {result['id']}")
        if not leg.get("booking_url"):
            raise RuntimeError(f"Missing booking_url in {result['id']}")


@collection_entrypoint("2")
def main(args) -> None:
    if args.days < 0:
        raise SystemExit("--days must be non-negative")
    end = args.from_date + timedelta(days=args.days)
    eur = nbp_eur_rate(args.from_date)
    rates = {"EUR": eur, "PLN": CurrencyRate("PLN", 1.0)}
    print(f"NBP EUR: {eur.pln:.4f} PLN", flush=True)

    legs: list[dict[str, Any]] = []
    for origin, destination in route_matrix():
        route_legs = collect_wizz_route(origin, destination, args.from_date, end, rates)
        if route_legs:
            print(f"Wizz Air: {origin}-{destination}: {len(route_legs)}", flush=True)
            legs.extend(route_legs)

    client_version = ryanair_client_version()
    print("Ryanair source: Google Flights HTTP (FR + RK, max 2 requests)", flush=True)
    for origin, destination in route_matrix():
        route_legs = collect_ryanair_route(
            origin,
            destination,
            args.from_date,
            end,
            rates,
            client_version,
        )
        if route_legs:
            print(f"Ryanair: {origin}-{destination}: {len(route_legs)}", flush=True)
            legs.extend(route_legs)

    results = build_results(legs)
    document = {
        "schema_version": 2,
        "generated_at": datetime.now(ZoneInfo("Atlantic/Canary")).isoformat(timespec="seconds"),
        "period_from": args.from_date.isoformat(),
        "period_to": end.isoformat(),
        "step": 2,
        "directions": ["tenerife_to_poland", "poland_to_tenerife"],
        "airport_matrix": {
            "tenerife": list(TENERIFE_AIRPORTS),
            "poland": list(POLISH_AIRPORTS),
        },
        "carriers": ["Wizz Air", "Ryanair"],
        "price_filtering": {
            "applied_during_collection": False,
            "controlled_by": "website",
        },
        "exchange_rates": {
            "EUR_PLN": {
                "rate": eur.pln,
                "source": "NBP tabela A",
                "effective_for": args.from_date.isoformat(),
            }
        },
        "sources": {
            "ryanair": "Google Flights HTTP individual Ryanair offers (FR and RK)",
            "wizz_air": "Wizz Air timetableV2",
        },
        "results": results,
    }
    validate_document(document)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    publish_document(document, args.output)
    counts = {
        direction: sum(result["direction"] == direction for result in results)
        for direction in document["directions"]
    }
    print(f"Zapisano {len(results)} lotów bezpośrednich do {args.output}", flush=True)
    print(json.dumps(counts, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
