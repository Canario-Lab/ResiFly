#!/usr/bin/env python3
"""Build the public Step 1 flight feed from current airline prices.

The collector uses the fixed Binter transfer-airport allowlist, checks both
directions and keeps every chronologically valid self-transfer connection.
Price filtering belongs to the website. Generated JSON files are never edited
by hand.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import hashlib
import json
from pathlib import Path
import sys
import time as time_module
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from curl_cffi import requests

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.booking_urls import ryanair_booking_url, wizz_booking_url


ROOT = Path(__file__).resolve().parents[1]
TRANSFER_FILE = ROOT / "data" / "binter-transfer-airports.json"
DEFAULT_OUTPUT = ROOT / "data" / "step1-results.json"

TENERIFE_AIRPORTS = ("TFN", "TFS")
POLISH_AIRPORTS = ("WAW", "WMI", "KTW", "KRK")
MIN_LAYOVER_MINUTES = 120
MAX_LAYOVER_MINUTES = 24 * 60
WIZZ_API = "https://be.wizzair.com/29.21.0/Api"
BINTER_API = "https://services.bintercanarias.com/main/graphql"

AIRPORT_TIMEZONES = {
    "TFN": "Atlantic/Canary",
    "TFS": "Atlantic/Canary",
    "FUE": "Atlantic/Canary",
    "LPA": "Atlantic/Canary",
    "MAD": "Europe/Madrid",
    "PMI": "Europe/Madrid",
    "SVQ": "Europe/Madrid",
    "VLC": "Europe/Madrid",
    "WAW": "Europe/Warsaw",
    "WMI": "Europe/Warsaw",
    "KTW": "Europe/Warsaw",
    "KRK": "Europe/Warsaw",
    "AGA": "Africa/Casablanca",
    "AGP": "Europe/Madrid",
    "BGY": "Europe/Rome",
    "BHX": "Europe/London",
    "BLQ": "Europe/Rome",
    "BOH": "Europe/London",
    "BRS": "Europe/London",
    "BUD": "Europe/Budapest",
    "BVA": "Europe/Paris",
    "CRL": "Europe/Brussels",
    "DUB": "Europe/Dublin",
    "EDI": "Europe/London",
    "EIN": "Europe/Amsterdam",
    "EMA": "Europe/London",
    "FCO": "Europe/Rome",
    "FMM": "Europe/Berlin",
    "LBA": "Europe/London",
    "LPL": "Europe/London",
    "LTN": "Europe/London",
    "MAN": "Europe/London",
    "MRS": "Europe/Paris",
    "MXP": "Europe/Rome",
    "NAP": "Europe/Rome",
    "NCL": "Europe/London",
    "OPO": "Europe/Lisbon",
    "PSA": "Europe/Rome",
    "RAK": "Africa/Casablanca",
    "SNN": "Europe/Dublin",
    "STN": "Europe/London",
    "TLS": "Europe/Paris",
    "TSF": "Europe/Rome",
    "VIE": "Europe/Vienna",
}

# Wizz's public timetable endpoint exposes departure time and price, but not
# the flight number or scheduled arrival. These stable route identifiers and
# published block times complete that response without using a session URL.
WIZZ_ROUTE_SCHEDULE = {
    ("WAW", "FUE"): ("W61331", 340),
    ("FUE", "WAW"): ("W61332", 325),
    ("KTW", "FUE"): ("W61083", 330),
    ("FUE", "KTW"): ("W61084", 310),
    ("WAW", "MAD"): ("W61471", 230),
    ("MAD", "WAW"): ("W61472", 215),
    ("KTW", "MAD"): ("W61177", 200),
    ("MAD", "KTW"): ("W61178", 205),
    ("WAW", "PMI"): ("W61327", 195),
    ("PMI", "WAW"): ("W61328", 185),
    ("WAW", "SVQ"): ("W61351", 245),
    ("SVQ", "WAW"): ("W61352", 235),
    ("WAW", "VLC"): ("W61337", 205),
    ("VLC", "WAW"): ("W61338", 200),
    ("KRK", "VLC"): ("W62079", 185),
    ("VLC", "KRK"): ("W62080", 190),
}

BINTER_QUERY = """
query booking_search($search: BookingSearchInput!) {
  booking_search(search: $search) {
    messages { text type }
    availability {
      onlyDirectFlights
      trip { origin { iata } destination { iata } date }
      flights {
        flightSegments {
          line
          flightNumber
          origin { iata }
          destination { iata }
          departureTime
          arrivalTime
        }
        flightTime
        fares {
          code
          class
          seats
          bestPrice
          amounts {
            resident { totalAmount currency { code } }
            noResident { totalAmount currency { code } }
          }
        }
      }
    }
  }
}
"""


@dataclass(frozen=True)
class CurrencyRate:
    code: str
    pln: float


def cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--days", type=int, default=30, help="Number of days after from-date, inclusive")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=10)
    return parser.parse_args()


def get_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    impersonate: str | None = None,
    attempts: int = 4,
) -> Any:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                json=payload,
                params=params,
                impersonate=impersonate,
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except Exception as error:  # network errors need a bounded retry
            last_error = error
            if attempt + 1 < attempts:
                time_module.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Request failed after {attempts} attempts: {url}") from last_error


def nbp_rate(currency_code: str, day: date) -> CurrencyRate:
    code = currency_code.upper()
    if code == "PLN":
        return CurrencyRate("PLN", 1.0)
    cursor = day
    for _ in range(8):
        for table in ("a", "b"):
            url = (
                "https://api.nbp.pl/api/exchangerates/rates/"
                f"{table}/{code.lower()}/{cursor.isoformat()}/"
            )
            try:
                payload = get_json("GET", url, params={"format": "json"}, attempts=1)
                return CurrencyRate(code, float(payload["rates"][0]["mid"]))
            except RuntimeError:
                continue
        cursor -= timedelta(days=1)
    raise RuntimeError(
        f"No NBP {code} rate available for {day.isoformat()} or preceding days"
    )


def nbp_eur_rate(day: date) -> CurrencyRate:
    return nbp_rate("EUR", day)


def money_pln(amount: float, currency_code: str, rates: dict[str, CurrencyRate]) -> float:
    code = currency_code.upper()
    if code == "PLN":
        return round(float(amount), 2)
    try:
        return round(float(amount) * rates[code].pln, 2)
    except KeyError as error:
        raise ValueError(f"Unsupported currency: {currency_code}") from error


def local_datetime(raw: str, airport: str) -> datetime:
    # Airline search APIs expose local wall times, even when a misleading UTC
    # offset is appended. Assigning the airport zone preserves the timetable.
    naive = datetime.fromisoformat(raw).replace(tzinfo=None)
    return naive.replace(tzinfo=ZoneInfo(AIRPORT_TIMEZONES[airport]))


def serialize_datetime(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def date_range(start: date, end: date) -> Iterable[date]:
    cursor = start
    while cursor <= end:
        yield cursor
        cursor += timedelta(days=1)


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
    response = get_json(
        "POST",
        f"{WIZZ_API}/search/timetableV2",
        headers={"content-type": "application/json"},
        payload=payload,
        impersonate="safari184",
    )
    return [
        item
        for item in response.get("outboundFlights", [])
        if item.get("departureStation") == origin
        and item.get("arrivalStation") == destination
        and item.get("priceType") == "price"
        and float(item.get("price", {}).get("amount") or 0) > 0
    ]


def collect_wizz_route(
    origin: str,
    destination: str,
    start: date,
    end: date,
    rates: dict[str, CurrencyRate],
) -> list[dict[str, Any]]:
    schedule = WIZZ_ROUTE_SCHEDULE.get((origin, destination))
    if schedule is None:
        return []
    regular = wizz_timetable(origin, destination, start, end, "regular")
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
        legs.append({
            "carrier": "Wizz Air",
            "flight_number": flight_number,
            "departure_airport": origin,
            "departure_at": serialize_datetime(departure),
            "arrival_airport": destination,
            "arrival_at": serialize_datetime(arrival),
            "price_regular_pln": money_pln(price["amount"], price["currencyCode"], rates),
            "price_wizz_discount_club_pln": club_price,
            "resident_discount_eligible": False,
            "price_resident_estimated_pln": money_pln(price["amount"], price["currencyCode"], rates),
            "booking_url": wizz_booking_url(origin, destination, departure),
            "price_source_currency": price["currencyCode"],
            "price_source_amount": float(price["amount"]),
        })
    return legs


def collect_ryanair_route(
    origin: str,
    destination: str,
    start: date,
    end: date,
    rates: dict[str, CurrencyRate],
) -> list[dict[str, Any]]:
    params = {
        "departureAirportIataCode": origin,
        "arrivalAirportIataCode": destination,
        "outboundDepartureDateFrom": start.isoformat(),
        "outboundDepartureDateTo": end.isoformat(),
        "currency": "EUR",
        "limit": 200,
    }
    try:
        response = get_json(
            "GET",
            "https://www.ryanair.com/api/farfnd/3/oneWayFares",
            params=params,
            impersonate="safari184",
            attempts=3,
        )
    except RuntimeError:
        return []
    legs = []
    for fare in response.get("fares", []):
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
        regular_pln = money_pln(price["value"], price["currencyCode"], rates)
        legs.append({
            "carrier": "Ryanair",
            "flight_number": item.get("flightNumber") or "Ryanair",
            "departure_airport": origin,
            "departure_at": serialize_datetime(departure),
            "arrival_airport": destination,
            "arrival_at": serialize_datetime(arrival),
            "price_regular_pln": regular_pln,
            "resident_discount_eligible": False,
            "price_resident_estimated_pln": regular_pln,
            "booking_url": ryanair_booking_url(origin, destination, departure),
            "price_source_currency": price["currencyCode"],
            "price_source_amount": float(price["value"]),
        })
    return legs


def binter_headers() -> dict[str, str]:
    return {
        "X-ENVIRONMENT": "desktop",
        "X-AUTH-TOKEN": "",
        "X-HASH1": "",
        "X-HASH2": "",
        "X-CLIENT-IP": "",
        "X-LANG": "es",
        "Origin": "https://www.bintercanarias.com",
        "Referer": "https://www.bintercanarias.com/",
        "content-type": "application/json",
    }


def lowest_eur_fare(fares: list[dict[str, Any]]) -> tuple[float, float] | None:
    choices: list[tuple[float, float]] = []
    for fare in fares:
        amounts = fare.get("amounts") or {}
        regular = amounts.get("noResident") or {}
        resident = amounts.get("resident") or {}
        if regular.get("currency", {}).get("code") != "EUR":
            continue
        if resident.get("currency", {}).get("code") != "EUR":
            continue
        if fare.get("seats") == 0:
            continue
        choices.append((float(regular["totalAmount"]), float(resident["totalAmount"])))
    return min(choices, key=lambda pair: pair[0]) if choices else None


def collect_binter_trip(
    origin: str,
    destination: str,
    departure_date: date,
    rates: dict[str, CurrencyRate],
) -> list[dict[str, Any]]:
    variables = {
        "search": {
            "trips": [{
                "origin": origin,
                "destination": destination,
                "date": departure_date.isoformat(),
            }],
            "passengers": [{"type": {"code": "ADT", "discounts": []}, "quantity": 1}],
            "flags": [],
        }
    }
    try:
        response = get_json(
            "POST",
            BINTER_API,
            headers=binter_headers(),
            payload={
                "query": BINTER_QUERY,
                "variables": variables,
                "operationName": "booking_search",
            },
            impersonate="safari184",
        )
    except RuntimeError:
        return []
    search = (response.get("data") or {}).get("booking_search") or {}
    legs: list[dict[str, Any]] = []
    for availability in search.get("availability") or []:
        for flight in availability.get("flights") or []:
            segments = flight.get("flightSegments") or []
            if len(segments) != 1:
                continue
            segment = segments[0]
            segment_origin = segment.get("origin", {}).get("iata")
            segment_destination = segment.get("destination", {}).get("iata")
            if segment_origin != origin or segment_destination != destination:
                continue
            fare = lowest_eur_fare(flight.get("fares") or [])
            if fare is None:
                continue
            regular_eur, resident_eur = fare
            departure = local_datetime(segment["departureTime"], origin)
            arrival = local_datetime(segment["arrivalTime"], destination)
            legs.append({
                "carrier": "Binter",
                "flight_number": f"{segment.get('line') or 'NT'}{segment['flightNumber']}",
                "departure_airport": origin,
                "departure_at": serialize_datetime(departure),
                "arrival_airport": destination,
                "arrival_at": serialize_datetime(arrival),
                "price_regular_pln": money_pln(regular_eur, "EUR", rates),
                "resident_discount_eligible": True,
                "price_resident_estimated_pln": money_pln(resident_eur, "EUR", rates),
                "booking_url": "https://www.bintercanarias.com/es/buscar-vuelos",
                "price_source_currency": "EUR",
                "price_source_amount": regular_eur,
            })
    return legs


def collect_low_cost_legs(
    transfers: list[str],
    start: date,
    end: date,
    rates: dict[str, CurrencyRate],
    workers: int,
) -> list[dict[str, Any]]:
    jobs = []
    for transfer in transfers:
        for polish in POLISH_AIRPORTS:
            for origin, destination in ((transfer, polish), (polish, transfer)):
                jobs.append(("Wizz Air", origin, destination))
                jobs.append(("Ryanair", origin, destination))
    legs: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        for carrier, origin, destination in jobs:
            function = collect_wizz_route if carrier == "Wizz Air" else collect_ryanair_route
            future = pool.submit(function, origin, destination, start, end, rates)
            futures[future] = (carrier, origin, destination)
        for future in as_completed(futures):
            carrier, origin, destination = futures[future]
            route_legs = future.result()
            if route_legs:
                print(f"{carrier}: {origin}-{destination}: {len(route_legs)}", flush=True)
                legs.extend(route_legs)
    return legs


def candidate_binter_trips(
    low_cost_legs: list[dict[str, Any]],
    start: date,
    end: date,
) -> set[tuple[str, str, date]]:
    candidates: set[tuple[str, str, date]] = set()
    for leg in low_cost_legs:
        origin = leg["departure_airport"]
        destination = leg["arrival_airport"]
        if origin in POLISH_AIRPORTS:
            transfer = destination
            arrival_date = date.fromisoformat(leg["arrival_at"][:10])
            for tenerife in TENERIFE_AIRPORTS:
                for candidate_date in (arrival_date, arrival_date + timedelta(days=1)):
                    if start <= candidate_date <= end:
                        candidates.add((transfer, tenerife, candidate_date))
        else:
            transfer = origin
            departure_date = date.fromisoformat(leg["departure_at"][:10])
            for tenerife in TENERIFE_AIRPORTS:
                for candidate_date in (departure_date - timedelta(days=1), departure_date):
                    if start <= candidate_date <= end:
                        candidates.add((tenerife, transfer, candidate_date))
    return candidates


def collect_binter_legs(
    candidates: set[tuple[str, str, date]],
    rates: dict[str, CurrencyRate],
    workers: int,
) -> list[dict[str, Any]]:
    legs: list[dict[str, Any]] = []
    ordered = sorted(candidates, key=lambda item: (item[2], item[0], item[1]))
    with ThreadPoolExecutor(max_workers=max(2, min(workers, 6))) as pool:
        futures = {
            pool.submit(collect_binter_trip, origin, destination, day, rates): (origin, destination, day)
            for origin, destination, day in ordered
        }
        done = 0
        for future in as_completed(futures):
            done += 1
            legs.extend(future.result())
            if done % 20 == 0 or done == len(futures):
                print(f"Binter: {done}/{len(futures)} zapytań", flush=True)
    return legs


def dt(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


def connection_id(legs: list[dict[str, Any]]) -> str:
    value = "|".join(
        f"{leg['carrier']}:{leg['flight_number']}:{leg['departure_at']}:{leg['arrival_at']}"
        for leg in legs
    )
    return f"step1-{hashlib.sha256(value.encode()).hexdigest()[:16]}"


def build_connections(
    low_cost_legs: list[dict[str, Any]],
    binter_legs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for low_cost in low_cost_legs:
        low_origin = low_cost["departure_airport"]
        low_destination = low_cost["arrival_airport"]
        poland_to_tenerife = low_origin in POLISH_AIRPORTS
        for binter in binter_legs:
            if poland_to_tenerife:
                if binter["departure_airport"] != low_destination:
                    continue
                if binter["arrival_airport"] not in TENERIFE_AIRPORTS:
                    continue
                layover = round((dt(binter["departure_at"]) - dt(low_cost["arrival_at"])).total_seconds() / 60)
                legs = [low_cost, binter]
            else:
                if binter["arrival_airport"] != low_origin:
                    continue
                if binter["departure_airport"] not in TENERIFE_AIRPORTS:
                    continue
                layover = round((dt(low_cost["departure_at"]) - dt(binter["arrival_at"])).total_seconds() / 60)
                legs = [binter, low_cost]
            if not MIN_LAYOVER_MINUTES <= layover <= MAX_LAYOVER_MINUTES:
                continue

            regular_total = round(sum(float(leg["price_regular_pln"]) for leg in legs), 2)
            resident_total = round(sum(float(leg["price_resident_estimated_pln"]) for leg in legs), 2)
            results.append({
                "id": connection_id(legs),
                "origin_airport": legs[0]["departure_airport"],
                "destination_airport": legs[-1]["arrival_airport"],
                "direction": "poland_to_tenerife" if poland_to_tenerife else "tenerife_to_poland",
                "connection_type": "one_stop",
                "transfer_airport": legs[0]["arrival_airport"],
                "layover_minutes": layover,
                "self_transfer": True,
                "legs": legs,
                "price_total_regular_pln": regular_total,
                "price_total_resident_estimated_pln": resident_total,
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
    if not document["results"]:
        raise RuntimeError("Collector produced no Step 1 connections")
    directions = {result["direction"] for result in document["results"]}
    if directions != {"tenerife_to_poland", "poland_to_tenerife"}:
        raise RuntimeError(f"Both directions are required; got {sorted(directions)}")
    for result in document["results"]:
        if len(result["legs"]) != 2:
            raise RuntimeError(f"Step 1 connection must have two legs: {result['id']}")
        for leg in result["legs"]:
            if leg["carrier"] == "Wizz Air" and not leg.get("booking_url"):
                raise RuntimeError(f"Missing Wizz booking_url in {result['id']}")


def main() -> None:
    args = cli()
    if args.days < 0:
        raise SystemExit("--days must be non-negative")
    end = args.from_date + timedelta(days=args.days)
    allowlist = json.loads(TRANSFER_FILE.read_text(encoding="utf-8"))
    transfers = [airport["iata"] for airport in allowlist["airports"]]

    eur = nbp_eur_rate(args.from_date)
    rates = {"EUR": eur, "PLN": CurrencyRate("PLN", 1.0)}
    print(f"NBP EUR: {eur.pln:.4f} PLN", flush=True)
    low_cost_legs = collect_low_cost_legs(transfers, args.from_date, end, rates, args.workers)
    print(f"Odcinki Ryanair/Wizz Air: {len(low_cost_legs)}", flush=True)
    candidates = candidate_binter_trips(low_cost_legs, args.from_date, end)
    print(f"Zapytania Binter do sprawdzenia: {len(candidates)}", flush=True)
    binter_legs = collect_binter_legs(candidates, rates, args.workers)
    print(f"Odcinki Binter: {len(binter_legs)}", flush=True)
    results = build_connections(low_cost_legs, binter_legs)

    generated_at = datetime.now(ZoneInfo("Atlantic/Canary")).isoformat(timespec="seconds")
    document = {
        "schema_version": 2,
        "generated_at": generated_at,
        "period_from": args.from_date.isoformat(),
        "period_to": end.isoformat(),
        "step": 1,
        "directions": ["tenerife_to_poland", "poland_to_tenerife"],
        "transfer_airports": transfers,
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
            "binter": "Binter booking_search GraphQL",
            "ryanair": "Ryanair Fare Finder",
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
    print(f"Zapisano {len(results)} połączeń do {args.output}", flush=True)
    print(json.dumps(counts, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
