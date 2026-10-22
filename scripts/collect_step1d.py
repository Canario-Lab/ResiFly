#!/usr/bin/env python3
"""Build Step 1D: Air Europa + Ryanair or Wizz Air.

Google Flights HTTP is the only source of Air Europa flight numbers, dates,
times and individual flight prices. Route/day minima and timetable templates
are not a fallback. The resident value is explicitly a 25% estimate. Official
Air Europa route/date booking links remain independent from the price source.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import threading
import time as time_module
from typing import Any
from zoneinfo import ZoneInfo

from selectolax.lexbor import LexborHTMLParser

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.collection_coverage import collection_entrypoint, publish_document, calendar_collector
from scripts.booking_urls import air_europa_booking_url
from scripts.collector_settings import GOOGLE_FLIGHTS_MAX_WORKERS, google_flights_worker_count
from scripts.collect_step1b import GoogleFlightsClient, _at, _google_datetime
from scripts.collect_step1 import (
    MAX_LAYOVER_MINUTES,
    MIN_LAYOVER_MINUTES,
    POLISH_AIRPORTS,
    TENERIFE_AIRPORTS,
    CurrencyRate,
    configure_airports_from_allowlist,
    date_range,
    dt,
    nbp_eur_rate,
    serialize_datetime,
)
from scripts.collect_step1c import collect_low_cost_legs


ROOT = Path(__file__).resolve().parents[1]
TRANSFER_FILE = ROOT / "data" / "air-europa-transfer-airports.json"
DEFAULT_OUTPUT = ROOT / "data" / "step1d-results.json"


def cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=6)
    return parser.parse_args()


def validate_allowlist(allowlist: dict[str, Any]) -> None:
    if allowlist.get("usage_policy", {}).get("step") != "1D":
        raise RuntimeError("Lista Air Europa nie jest oznaczona jako krok 1D")
    if not allowlist.get("airports"):
        raise RuntimeError("Lista lotnisk Air Europa jest pusta")
    if allowlist.get("usage_policy", {}).get("flight_data_source") != "google_flights_http":
        raise RuntimeError("Air Europa wymaga wyłącznie indywidualnych ofert Google Flights")
    if allowlist.get("air_europa_airline_codes", {}).get("accepted_marketing") != ["UX"]:
        raise RuntimeError("Nieprawidłowa lista kodów marketingowych Air Europa")
    for airport in allowlist["airports"]:
        code = airport["iata"]
        ZoneInfo(airport["timezone"])
        if not airport.get("resident_discount_eligible_on_air_europa_leg"):
            raise RuntimeError(f"Krok 1D nie może zawierać trasy bez zniżki: {code}")
        if float(airport.get("air_europa_resident_fare_multiplier", 0)) != 0.25:
            raise RuntimeError(f"Nieprawidłowy mnożnik Air Europa dla {code}")
        tenerife_airports = airport.get("tenerife_airports") or []
        if not tenerife_airports or not set(tenerife_airports) <= set(TENERIFE_AIRPORTS):
            raise RuntimeError(f"Nieprawidłowa lista lotnisk Teneryfy dla {code}")
        if not airport.get("polish_routes"):
            raise RuntimeError(f"Brak tras do Polski dla {code}")
        for route in airport["polish_routes"]:
            if route["polish_airport"] not in POLISH_AIRPORTS:
                raise RuntimeError(f"Nieprawidłowe polskie lotnisko dla {code}")
            carriers = set(route.get("airlines") or [])
            if not carriers or not carriers <= {"Ryanair", "Wizz Air"}:
                raise RuntimeError(f"Nieprawidłowy drugi przewoźnik dla {code}")


def low_cost_route_matrix(
    allowlist: dict[str, Any],
) -> list[tuple[str, str, str]]:
    routes: set[tuple[str, str, str]] = set()
    for transfer in allowlist["airports"]:
        for route in transfer["polish_routes"]:
            for carrier in route["airlines"]:
                routes.add((carrier, transfer["iata"], route["polish_airport"]))
                routes.add((carrier, route["polish_airport"], transfer["iata"]))
    return sorted(routes)


def air_europa_route_days(
    allowlist: dict[str, Any],
    start: date,
    end: date,
) -> set[tuple[str, str, date]]:
    """Return every saved Air Europa route/day in both directions.

    Air Europa's calendar must be collected independently of the low-cost
    timetable. Connections are matched only after the complete carrier
    window has been fetched.
    """

    route_days: set[tuple[str, str, date]] = set()
    for transfer in allowlist["airports"]:
        for tenerife in transfer["tenerife_airports"]:
            for day in date_range(start, end):
                route_days.add((tenerife, transfer["iata"], day))
                route_days.add((transfer["iata"], tenerife, day))
    return route_days


def _google_offers(value: Any):
    """Visit all recognized offer buckets, not only Google's first group."""
    if not isinstance(value, list):
        return
    segments = _at(_at(value, 0, []), 2, [])
    if (isinstance(segments, list) and segments and all(
        isinstance(segment, list) and isinstance(_at(segment, 22), list)
        and isinstance(_at(segment, 3), str) and isinstance(_at(segment, 6), str)
        for segment in segments
    )):
        yield value
        return
    for child in value:
        yield from _google_offers(child)


def parse_google_flights_response(
    html: str, origin: str, destination: str, departure_date: date,
    multiplier: float, accepted_marketing: set[str],
) -> list[dict[str, Any]]:
    parser = LexborHTMLParser(html)
    node = next((n for n in parser.css("script") if "ds:1" in (n.attributes.get("class") or "").split()), None)
    if node is None or "data:" not in node.text():
        raise RuntimeError("Google Flights nie zwrócił danych lotów Air Europa")
    raw = node.text().split("data:", 1)[1].lstrip()
    payload, _ = json.JSONDecoder().raw_decode(raw)
    if (not isinstance(payload, list) or len(payload) <= 3 or
        payload[3] is not None and (not isinstance(payload[3], list) or not payload[3])):
        raise RuntimeError("Nieznana struktura odpowiedzi Google Flights dla Air Europa")
    best, unpriced = {}, set()
    for offer in _google_offers(payload):
        segments = _at(_at(offer, 0, []), 2, [])
        if len(segments) != 1:
            continue
        segment = segments[0]
        if _at(segment, 3) != origin or _at(segment, 6) != destination:
            continue
        flight = _at(segment, 22, [])
        marketing = str(_at(flight, 0, "")).upper()
        if marketing not in accepted_marketing:
            continue
        for index in (8, 10):
            clock = _at(segment, index)
            # Google's compact clock arrays omit trailing zero minutes:
            # [15] is 15:00, not an incomplete timestamp. A missing clock
            # object still fails; no timetable or another flight is consulted.
            if not isinstance(clock, list) or not clock:
                raise RuntimeError("Brak pełnej godziny rejsu Air Europa; zapis zablokowany")
            hour, minute = _at(clock, 0, 0), _at(clock, 1, 0)
            hour = 0 if hour is None else hour
            minute = 0 if minute is None else minute
            if (any(not isinstance(part, int) or isinstance(part, bool) for part in (hour, minute)) or
                not 0 <= hour < 24 or not 0 <= minute < 60):
                raise RuntimeError("Nieprawidłowa godzina rejsu Air Europa; zapis zablokowany")
        departure = _google_datetime(_at(segment, 20), _at(segment, 8), origin)
        arrival = _google_datetime(_at(segment, 21), _at(segment, 10), destination)
        if departure.date() != departure_date:
            continue
        number = str(_at(flight, 1, "")).replace(" ", "").upper()
        number = number if number.startswith(marketing) else marketing + number
        if not re.fullmatch(r"UX\d{1,5}", number) or arrival <= departure:
            raise RuntimeError("Nieprawidłowy numer lub daty rejsu Air Europa")
        key = (number, departure.isoformat(), arrival.isoformat())
        amount = _at(_at(_at(offer, 1, []), 0, []), 1)
        if (not isinstance(amount, (int, float)) or isinstance(amount, bool) or
            not math.isfinite(amount) or amount <= 0):
            unpriced.add(key)
            continue
        regular = round(float(amount), 2)
        leg = {
            "carrier": "Air Europa", "flight_number": number,
            "departure_airport": origin, "arrival_airport": destination,
            "departure_at": serialize_datetime(departure), "arrival_at": serialize_datetime(arrival),
            "price_regular_pln": regular, "price_resident_estimated_pln": round(regular * multiplier, 2),
            "resident_discount_eligible": True, "resident_fare_multiplier": multiplier,
            "resident_price_source": "estimate: configured percentage of Google Flights non-resident fare",
            "booking_url": air_europa_booking_url(origin, destination, departure),
            "booking_url_scope": "route_date_search",
            "price_source": "Google Flights", "price_scope": "individual_flight_offer",
            "price_source_currency": "PLN", "price_source_amount": regular,
            "price_seller_verified": False, "schedule_source": "Google Flights individual flight offer",
        }
        if key not in best or regular < best[key]["price_regular_pln"]:
            best[key] = leg
    if unpriced - best.keys():
        raise RuntimeError(f"Google Flights zwrócił rejs Air Europa bez ceny dla {origin}-{destination} {departure_date}; brak zastępowania minimum dnia")
    return sorted(best.values(), key=lambda leg: (leg["departure_at"], leg["flight_number"]))


@calendar_collector("Air Europa", "google_flights_http")
def collect_air_europa_trip(
    client: GoogleFlightsClient, origin: str, destination: str,
    departure_date: date, multiplier: float, accepted_marketing: set[str],
) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            html = client.availability(origin, destination, departure_date)
            if "PLN" not in html and "zł" not in html:
                raise RuntimeError("Nie potwierdzono waluty PLN odpowiedzi Air Europa Google Flights")
            return parse_google_flights_response(
                html, origin, destination, departure_date, multiplier, accepted_marketing,
            )
        except (RuntimeError, json.JSONDecodeError, ValueError) as error:
            last_error = error
            if attempt + 1 < 4:
                time_module.sleep(1.5 * (attempt + 1))
    raise RuntimeError(
        f"Google Flights Air Europa failed for {origin}-{destination} on {departure_date}; "
        "publication blocked"
    ) from last_error


def collect_air_europa_legs(
    route_days: set[tuple[str, str, date]],
    allowlist: dict[str, Any],
    workers: int,
) -> list[dict[str, Any]]:
    if not route_days:
        return []
    rules = {airport["iata"]: airport for airport in allowlist["airports"]}
    accepted = set(allowlist["air_europa_airline_codes"]["accepted_marketing"])
    ordered = sorted(route_days, key=lambda item: (item[2], item[0], item[1]))
    abort, local = threading.Event(), threading.local()

    def fetch(candidate):
        if abort.is_set():
            raise RuntimeError("Pobieranie Air Europa zatrzymane po błędzie Google Flights")
        origin, destination, day = candidate
        transfer = destination if origin in TENERIFE_AIRPORTS else origin
        try:
            if not hasattr(local, "client"):
                local.client = GoogleFlightsClient()
            return collect_air_europa_trip(local.client, origin, destination, day,
                float(rules[transfer]["air_europa_resident_fare_multiplier"]), accepted)
        except Exception:
            abort.set()
            raise

    max_workers = google_flights_worker_count(workers)
    print(f"Google Flights Air Europa: {max_workers} równoległe zapytania (limit {GOOGLE_FLIGHTS_MAX_WORKERS})", flush=True)
    legs: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for index, result in enumerate(executor.map(fetch, ordered), start=1):
            legs.extend(result)
            if index % 10 == 0 or index == len(ordered):
                print(f"Air Europa przez Google Flights: {index}/{len(ordered)} tras/dni", flush=True)
    return sorted(legs, key=lambda leg: leg["departure_at"])


def connection_id(legs: list[dict[str, Any]]) -> str:
    value = "|".join(
        f"{leg['carrier']}:{leg['flight_number']}:{leg['departure_at']}:{leg['arrival_at']}"
        for leg in legs
    )
    return f"step1d-{hashlib.sha256(value.encode()).hexdigest()[:16]}"


def build_connections(
    low_cost_legs: list[dict[str, Any]],
    air_europa_legs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for low_cost in low_cost_legs:
        poland_to_tenerife = low_cost["departure_airport"] in POLISH_AIRPORTS
        for air_europa in air_europa_legs:
            if poland_to_tenerife:
                if air_europa["departure_airport"] != low_cost["arrival_airport"]:
                    continue
                if air_europa["arrival_airport"] not in TENERIFE_AIRPORTS:
                    continue
                layover = round(
                    (dt(air_europa["departure_at"]) - dt(low_cost["arrival_at"]))
                    .total_seconds() / 60
                )
                legs = [low_cost, air_europa]
            else:
                if air_europa["arrival_airport"] != low_cost["departure_airport"]:
                    continue
                if air_europa["departure_airport"] not in TENERIFE_AIRPORTS:
                    continue
                layover = round(
                    (dt(low_cost["departure_at"]) - dt(air_europa["arrival_at"]))
                    .total_seconds() / 60
                )
                legs = [air_europa, low_cost]
            if not MIN_LAYOVER_MINUTES <= layover <= MAX_LAYOVER_MINUTES:
                continue
            results.append({
                "id": connection_id(legs),
                "origin_airport": legs[0]["departure_airport"],
                "destination_airport": legs[-1]["arrival_airport"],
                "direction": (
                    "poland_to_tenerife" if poland_to_tenerife else "tenerife_to_poland"
                ),
                "connection_type": "one_stop",
                "transfer_airport": legs[0]["arrival_airport"],
                "layover_minutes": layover,
                "self_transfer": True,
                "legs": legs,
                "price_total_regular_pln": round(
                    sum(float(leg["price_regular_pln"]) for leg in legs), 2
                ),
                "price_total_resident_estimated_pln": round(
                    sum(float(leg["price_resident_estimated_pln"]) for leg in legs), 2
                ),
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
    for result in document["results"]:
        if len(result["legs"]) != 2:
            raise RuntimeError(f"Połączenie 1D musi mieć dwa odcinki: {result['id']}")
        carriers = {leg["carrier"] for leg in result["legs"]}
        if "Air Europa" not in carriers or not carriers & {"Ryanair", "Wizz Air"}:
            raise RuntimeError(f"Nieprawidłowi przewoźnicy w {result['id']}")
        for leg in result["legs"]:
            if not leg.get("booking_url"):
                raise RuntimeError(f"Brak booking_url w {result['id']}")
            if leg["carrier"] == "Air Europa":
                if leg.get("price_source") != "Google Flights" or leg.get("price_scope") != "individual_flight_offer":
                    raise RuntimeError(f"Niedozwolone źródło lub zakres ceny w {result['id']}")
                if not re.fullmatch(r"UX\d{1,5}", leg.get("flight_number", "")):
                    raise RuntimeError(f"Brak pełnego numeru lotu Air Europa w {result['id']}")
                expected_url = air_europa_booking_url(leg["departure_airport"], leg["arrival_airport"], leg["departure_at"])
                if leg["booking_url"] != expected_url:
                    raise RuntimeError(f"Nietrwały lub nieprawidłowy link Air Europa w {result['id']}")


@collection_entrypoint("1d")
def main(args) -> None:
    if args.days < 0:
        raise SystemExit("--days must be non-negative")
    end = args.from_date + timedelta(days=args.days)
    allowlist = json.loads(TRANSFER_FILE.read_text(encoding="utf-8"))
    validate_allowlist(allowlist)
    configure_airports_from_allowlist(allowlist)

    eur = nbp_eur_rate(args.from_date)
    rates = {"EUR": eur, "PLN": CurrencyRate("PLN", 1.0)}
    print(f"NBP EUR: {eur.pln:.4f} PLN", flush=True)
    try:
        low_cost = collect_low_cost_legs(
            allowlist, args.from_date, end, rates, args.workers
        )
    except RuntimeError as error:
        raise RuntimeError(str(error).replace("1C", "1D")) from error
    if not low_cost:
        raise RuntimeError(
            "Nie pobrano żadnego odcinka Wizz/Ryanair; wynik 1D nie zostanie nadpisany"
        )

    route_days = air_europa_route_days(allowlist, args.from_date, end)
    print(f"Dni tras Air Europa do sprawdzenia: {len(route_days)}", flush=True)
    air_europa = collect_air_europa_legs(route_days, allowlist, args.workers)
    if route_days and not air_europa:
        raise RuntimeError(
            "Google Flights nie zwrócił użytecznych indywidualnych ofert Air Europa; "
            "wynik 1D nie zostanie nadpisany"
        )
    results = build_connections(low_cost, air_europa)
    generated_at = datetime.now(ZoneInfo("Atlantic/Canary")).isoformat(timespec="seconds")
    document = {
        "schema_version": 2,
        "generated_at": generated_at,
        "period_from": args.from_date.isoformat(),
        "period_to": end.isoformat(),
        "step": "1D",
        "directions": ["tenerife_to_poland", "poland_to_tenerife"],
        "transfer_airports": [airport["iata"] for airport in allowlist["airports"]],
        "price_filtering": {"applied_during_collection": False, "controlled_by": "website"},
        "exchange_rates": {
            "EUR_PLN": {
                "rate": eur.pln,
                "source": "NBP tabela A",
                "effective_for": args.from_date.isoformat(),
            }
        },
        "sources": {
            "air_europa_routes_and_prices": (
                "Google Flights HTTP only: individual Air Europa flight numbers, "
                "dates, times and regular fares; no day-minimum or timetable-template fallback"
            ),
            "air_europa_resident_price": (
                "estimate: 25% of Google Flights regular flight fare; taxes may not "
                "receive the full resident discount"
            ),
            "ryanair": "Google Flights HTTP individual Ryanair offers (FR and RK)",
            "wizz_air": "Wizz Air timetableV2",
        },
        "result_status": "ok" if results else "no_matching_connections",
        "results": results,
    }
    validate_document(document)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    publish_document(document, args.output)
    print(f"Zapisano {len(results)} połączeń do {args.output}", flush=True)


if __name__ == "__main__":
    main()
