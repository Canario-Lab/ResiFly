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

from scripts.booking_urls import ryanair_booking_url, wizz_booking_url
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
WIZZ_API = "https://be.wizzair.com/29.21.0/Api"
RYANAIR_DATES_API = "https://www.ryanair.com/api/farfnd/v4/oneWayFares"
RYANAIR_FARE_FINDER_API = "https://www.ryanair.com/api/farfnd/3/oneWayFares"
RYANAIR_AVAILABILITY_API = "https://www.ryanair.com/api/booking/v4/en-gb/availability"
RYANAIR_VERSION_PAGE = "https://www.ryanair.com/ie/en/trip/flights/select"

# Wizz's timetable price endpoint omits the arrival time and flight number.
# Direct routes found in the complete airport matrix must have a corresponding
# schedule entry here; otherwise validation fails instead of inventing data.
WIZZ_DIRECT_SCHEDULES = {
    ("WAW", "TFS"): ("W61495", 360),
    ("TFS", "WAW"): ("W61496", 330),
    ("KTW", "TFS"): ("W61081", 345),
    ("TFS", "KTW"): ("W61082", 320),
}


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
            response = requests.post(
                f"{WIZZ_API}/search/timetableV2",
                headers={"content-type": "application/json"},
                json=payload,
                impersonate="safari184",
                timeout=60,
            )
            if response.status_code == 400 and "InvalidMarket" in response.text:
                return []
            response.raise_for_status()
            body = response.json()
            return [
                item
                for item in body.get("outboundFlights", [])
                if item.get("departureStation") == origin
                and item.get("arrivalStation") == destination
                and item.get("priceType") == "price"
                and float(item.get("price", {}).get("amount") or 0) > 0
            ]
        except Exception as error:
            last_error = error
            if attempt + 1 < max_attempts:
                # The public timetable endpoint intermittently returns 503
                # during a complete multi-route scan. Longer exponential
                # backoff prevents a transient throttle from discarding the
                # otherwise complete calendar.
                time_module.sleep(min(3 * (2 ** attempt), 30))
    raise RuntimeError(f"Wizz Air request failed for {origin}-{destination}") from last_error


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
            "add its verified flight number and duration to WIZZ_DIRECT_SCHEDULES"
        )
    club = wizz_timetable(origin, destination, start, end, "wdc")
    club_by_departure = {item["departureDate"]: item for item in club}
    flight_number, duration_minutes = schedule
    legs: list[dict[str, Any]] = []
    for item in regular:
        departure = local_datetime(item["departureDate"], origin)
        arrival = (departure + timedelta(minutes=duration_minutes)).astimezone(
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
            "flight_number": flight_number,
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
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = requests.get(RYANAIR_VERSION_PAGE, impersonate="chrome", timeout=60)
            response.raise_for_status()
            match = re.search(r"Desktop version: (\d+\.\d+\.\d+)", response.text)
            if not match:
                raise RuntimeError("Could not discover the current Ryanair desktop client version")
            return match.group(1)
        except Exception as error:
            last_error = error
            if attempt < 3:
                time_module.sleep(1.5 * (attempt + 1))
    raise RuntimeError("Could not discover the current Ryanair desktop client version") from last_error


def ryanair_available_dates(origin: str, destination: str) -> list[date]:
    url = f"{RYANAIR_DATES_API}/{origin}/{destination}/availabilities"
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = requests.get(url, impersonate="safari184", timeout=60)
            if response.status_code in {400, 404}:
                return []
            response.raise_for_status()
            return [date.fromisoformat(value) for value in response.json()]
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
        "FlexDaysBeforeOut": 2,
        "FlexDaysOut": 4,
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
    """Fallback for markets declined by the full availability endpoint.

    Fare Finder returns only the cheapest result for a date range, so each
    known active date is requested separately to avoid losing travel dates.
    """

    legs_by_key: dict[str, dict[str, Any]] = {}
    for active_date in sorted(day for day in active_dates if start <= day <= end):
        params = {
            "departureAirportIataCode": origin,
            "arrivalAirportIataCode": destination,
            "outboundDepartureDateFrom": active_date.isoformat(),
            "outboundDepartureDateTo": active_date.isoformat(),
            "currency": "EUR",
            "limit": 20,
        }
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                response = requests.get(
                    RYANAIR_FARE_FINDER_API,
                    params=params,
                    impersonate="safari184",
                    timeout=60,
                )
                response.raise_for_status()
                payload = response.json()
                break
            except Exception as error:
                last_error = error
                if attempt < 3:
                    time_module.sleep(1.5 * (attempt + 1))
        else:
            raise RuntimeError(
                f"Ryanair Fare Finder failed for {origin}-{destination} on {active_date}"
            ) from last_error

        for fare in payload.get("fares", []):
            item = fare.get("outbound") or {}
            if item.get("departureAirport", {}).get("iataCode") != origin:
                continue
            if item.get("arrivalAirport", {}).get("iataCode") != destination:
                continue
            price = item.get("price") or {}
            if not price.get("value"):
                continue
            departure = local_datetime(item["departureDate"], origin)
            arrival = local_datetime(item["arrivalDate"], destination)
            currency = price["currencyCode"]
            regular_amount = float(price["value"])
            key = item.get("flightKey") or (
                f"{item.get('flightNumber')}:{departure.isoformat()}:{arrival.isoformat()}"
            )
            legs_by_key[key] = {
                "carrier": "Ryanair",
                "flight_number": str(item.get("flightNumber") or "Ryanair").replace(" ", ""),
                "departure_airport": origin,
                "departure_at": serialize_datetime(departure),
                "arrival_airport": destination,
                "arrival_at": serialize_datetime(arrival),
                "price_regular_pln": money_pln(regular_amount, currency, rates),
                "resident_discount_eligible": False,
                "price_resident_estimated_pln": money_pln(regular_amount, currency, rates),
                "booking_url": ryanair_booking_url(origin, destination, departure),
                "price_source_currency": currency,
                "price_source_amount": regular_amount,
                "price_source": "Ryanair Fare Finder daily fallback",
            }
    return sorted(legs_by_key.values(), key=lambda leg: leg["departure_at"])


def collect_ryanair_route(
    origin: str,
    destination: str,
    start: date,
    end: date,
    rates: dict[str, CurrencyRate],
    client_version: str,
) -> list[dict[str, Any]]:
    active_dates = ryanair_available_dates(origin, destination)
    centers = ryanair_windows(active_dates, start, end)
    if not centers:
        return []

    legs_by_key: dict[str, dict[str, Any]] = {}
    for center in centers:
        try:
            payload = ryanair_availability(origin, destination, center, client_version)
        except RuntimeError as error:
            if "Availability declined" in str(error):
                return collect_ryanair_farefinder_dates(
                    origin,
                    destination,
                    active_dates,
                    start,
                    end,
                    rates,
                )
            raise
        currency = payload["currency"]
        for trip in payload.get("trips", []):
            if trip.get("origin") != origin or trip.get("destination") != destination:
                continue
            for day in trip.get("dates", []):
                for flight in day.get("flights", []):
                    segments = flight.get("segments") or []
                    fare = flight.get("regularFare") or {}
                    adult_fares = [item for item in fare.get("fares", []) if item.get("type") == "ADT"]
                    if len(segments) != 1 or not adult_fares:
                        continue
                    segment = segments[0]
                    times = segment.get("time") or []
                    if len(times) != 2:
                        continue
                    departure = local_datetime(times[0], origin)
                    if not start <= departure.date() <= end:
                        continue
                    arrival = local_datetime(times[1], destination)
                    regular_amount = float(adult_fares[0]["amount"])
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
    return sorted(legs_by_key.values(), key=lambda leg: leg["departure_at"])


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


def main() -> None:
    args = cli()
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
    print(f"Ryanair client version: {client_version}", flush=True)
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
            "ryanair": "Ryanair availability and active-dates APIs",
            "wizz_air": "Wizz Air timetableV2",
        },
        "results": results,
    }
    validate_document(document)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = {
        direction: sum(result["direction"] == direction for result in results)
        for direction in document["directions"]
    }
    print(f"Zapisano {len(results)} lotów bezpośrednich do {args.output}", flush=True)
    print(json.dumps(counts, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
