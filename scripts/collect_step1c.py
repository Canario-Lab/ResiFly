#!/usr/bin/env python3
"""Build Step 1C: Vueling + Ryanair or Wizz Air.

The collector reads the fixed Vueling transfer-airport allowlist, checks both
travel directions and keeps every valid 2–24 hour self-transfer.  Vueling's
own website is the primary route-list source.  Regular Vueling fares are read
from Google Flights by HTTP and the Canary resident estimate discounts only the
fare component while preserving fixed Aena fees. Price filtering is left to the website.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import sys
import time as time_module
from typing import Any
from zoneinfo import ZoneInfo

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.collection_coverage import collection_entrypoint, publish_document, record_checked
from scripts.booking_urls import vueling_booking_url
from scripts.collector_settings import (
    GOOGLE_FLIGHTS_MAX_WORKERS,
    google_flights_worker_count,
)
from scripts.spanish_resident_fees import (
    apply_resident_price_estimate,
    validate_resident_price_estimate,
)
from scripts.collect_step1 import (
    MAX_LAYOVER_MINUTES,
    MIN_LAYOVER_MINUTES,
    POLISH_AIRPORTS,
    TENERIFE_AIRPORTS,
    CurrencyRate,
    collect_ryanair_route,
    configure_airports_from_allowlist,
    date_range,
    dt,
    nbp_eur_rate,
    serialize_datetime,
)
from scripts.collect_step1b import (
    GoogleFlightsClient,
    _at,
    _google_datetime,
    _google_flights_payload,
)
from scripts.collect_step4 import collect_wizz_route


ROOT = Path(__file__).resolve().parents[1]
TRANSFER_FILE = ROOT / "data" / "vueling-transfer-airports.json"
DEFAULT_OUTPUT = ROOT / "data" / "step1c-results.json"


def cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-date", type=date.fromisoformat, default=date.today())
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days after from-date, inclusive",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def validate_allowlist(allowlist: dict[str, Any]) -> None:
    if allowlist.get("usage_policy", {}).get("step") != "1C":
        raise RuntimeError("Lista Vuelinga nie jest oznaczona jako krok 1C")
    airports = allowlist.get("airports") or []
    if not airports:
        raise RuntimeError("Lista lotnisk Vuelinga jest pusta")
    for airport in airports:
        code = airport["iata"]
        ZoneInfo(airport["timezone"])
        if not airport.get("resident_discount_eligible_on_vueling_leg"):
            raise RuntimeError(f"Krok 1C nie może zawierać trasy bez zniżki: {code}")
        if float(airport.get("vueling_resident_fare_multiplier", 0)) != 0.25:
            raise RuntimeError(f"Nieprawidłowy mnożnik Vuelinga dla {code}")
        tenerife_airports = airport.get("tenerife_airports") or []
        if not tenerife_airports or not set(tenerife_airports) <= set(TENERIFE_AIRPORTS):
            raise RuntimeError(f"Nieprawidłowa lista lotnisk Teneryfy dla {code}")
        polish_routes = airport.get("polish_routes") or []
        if not polish_routes:
            raise RuntimeError(f"Brak tras do Polski dla {code}")
        for route in polish_routes:
            if route["polish_airport"] not in POLISH_AIRPORTS:
                raise RuntimeError(f"Nieprawidłowe polskie lotnisko dla {code}")
            carriers = set(route.get("airlines") or [])
            if not carriers or not carriers <= {"Ryanair", "Wizz Air"}:
                raise RuntimeError(f"Nieprawidłowy przewoźnik drugiego odcinka dla {code}")


def low_cost_route_matrix(
    allowlist: dict[str, Any],
) -> list[tuple[str, str, str]]:
    routes: set[tuple[str, str, str]] = set()
    for transfer in allowlist["airports"]:
        code = transfer["iata"]
        for route in transfer["polish_routes"]:
            polish = route["polish_airport"]
            for carrier in route["airlines"]:
                routes.add((carrier, code, polish))
                routes.add((carrier, polish, code))
    return sorted(routes)


def collect_low_cost_legs(
    allowlist: dict[str, Any],
    start: date,
    end: date,
    rates: dict[str, CurrencyRate],
    workers: int,
) -> list[dict[str, Any]]:
    routes = low_cost_route_matrix(allowlist)
    legs: list[dict[str, Any]] = []

    # Wizz's timetable endpoint is sensitive to short request bursts.  Keep
    # these requests sequential and retry a whole route after a bounded pause;
    # this makes the collector suitable for a shared GitHub Actions runner.
    for carrier, origin, destination in routes:
        if carrier != "Wizz Air":
            continue
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                route_legs = collect_wizz_route(
                    origin,
                    destination,
                    start,
                    end,
                    rates,
                )
                if route_legs:
                    print(
                        f"Wizz Air: {origin}-{destination}: {len(route_legs)}",
                        flush=True,
                    )
                    legs.extend(route_legs)
                last_error = None
                break
            except RuntimeError as error:
                last_error = error
                if attempt < 2:
                    time_module.sleep(10 * (attempt + 1))
        if last_error is not None:
            raise RuntimeError(
                f"Wizz Air nie zwrócił trasy {origin}-{destination}; "
                "wynik 1C nie zostanie nadpisany"
            ) from last_error
        time_module.sleep(0.4)

    ryanair_routes = [route for route in routes if route[0] == "Ryanair"]
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(
                    collect_ryanair_route,
                    origin,
                    destination,
                    start,
                    end,
                    rates,
            ): (carrier, origin, destination)
            for carrier, origin, destination in ryanair_routes
        }
        for future in as_completed(futures):
            carrier, origin, destination = futures[future]
            route_legs = future.result()
            if route_legs:
                print(f"{carrier}: {origin}-{destination}: {len(route_legs)}", flush=True)
                legs.extend(route_legs)
    return legs


def vueling_route_days(
    allowlist: dict[str, Any],
    start: date,
    end: date,
) -> set[tuple[str, str, date]]:
    """Return every saved Vueling route/day in both directions.

    Vueling's calendar must be collected independently of the low-cost
    timetable. Connections are matched only after the complete Vueling
    window has been fetched.
    """

    route_days: set[tuple[str, str, date]] = set()
    for transfer in allowlist["airports"]:
        for tenerife in transfer["tenerife_airports"]:
            for day in date_range(start, end):
                route_days.add((tenerife, transfer["iata"], day))
                route_days.add((transfer["iata"], tenerife, day))
    return route_days


def parse_google_flights_response(
    html: str,
    origin: str,
    destination: str,
    multiplier: float,
    eur_pln: float,
    accepted_marketing: set[str],
) -> list[dict[str, Any]]:
    """Transform direct, Vueling-marketed Google Flights offers."""

    best_by_flight: dict[tuple[str, str, str], dict[str, Any]] = {}
    for offer in _google_flights_payload(html):
        flight_group = _at(offer, 0, [])
        segments = _at(flight_group, 2, [])
        if len(segments) != 1:
            continue
        segment = segments[0]
        if str(_at(segment, 3, "")).upper() != origin:
            continue
        if str(_at(segment, 6, "")).upper() != destination:
            continue

        flight = _at(segment, 22, [])
        marketing_code = str(_at(flight, 0, "")).upper()
        if marketing_code not in accepted_marketing:
            continue
        raw_number = str(_at(flight, 1, "")).strip()
        if not raw_number:
            continue

        price_block = _at(_at(offer, 1, []), 0, [])
        amount = _at(price_block, 1)
        if not isinstance(amount, (int, float)) or float(amount) <= 0:
            continue
        try:
            departure = _google_datetime(_at(segment, 20), _at(segment, 8), origin)
            arrival = _google_datetime(_at(segment, 21), _at(segment, 10), destination)
        except (TypeError, ValueError):
            continue

        number = (
            raw_number
            if raw_number.upper().startswith(marketing_code)
            else f"{marketing_code}{raw_number}"
        )
        regular_pln = round(float(amount), 2)
        leg = {
            "carrier": "Vueling",
            "flight_number": number,
            "departure_airport": origin,
            "departure_at": serialize_datetime(departure),
            "arrival_airport": destination,
            "arrival_at": serialize_datetime(arrival),
            "price_regular_pln": regular_pln,
            "resident_discount_eligible": True,
            "resident_fare_multiplier": multiplier,
            "booking_url": vueling_booking_url(origin, destination, departure),
            "price_source": "Google Flights",
            "price_source_currency": "PLN",
            "price_source_amount": amount,
        }
        apply_resident_price_estimate(leg, eur_pln)
        numeric_flight = "".join(character for character in raw_number if character.isdigit())
        key = (numeric_flight or raw_number, leg["departure_at"], leg["arrival_at"])
        previous = best_by_flight.get(key)
        if previous is None or regular_pln < previous["price_regular_pln"]:
            best_by_flight[key] = leg
    return sorted(best_by_flight.values(), key=lambda leg: leg["departure_at"])


def collect_vueling_legs(
    route_days: set[tuple[str, str, date]],
    transfer_rules: dict[str, dict[str, Any]],
    airline_codes: dict[str, Any],
    workers: int,
    eur_pln: float,
) -> list[dict[str, Any]]:
    from scripts.source_repository import cached_days
    cached = cached_days("Vueling", route_days, "google_flights_http")
    if cached is not None:
        return cached
    if not route_days:
        return []
    accepted_marketing = set(airline_codes["accepted_marketing"])
    ordered = sorted(route_days, key=lambda item: (item[2], item[0], item[1]))

    from scripts.source_repository import abort_on_source_failure
    @abort_on_source_failure
    def fetch(candidate: tuple[str, str, date]) -> list[dict[str, Any]]:
        origin, destination, day = candidate
        from scripts.source_repository import cached_route
        cached = cached_route("Vueling", origin, destination, day, day)
        if cached is not None:
            return cached
        transfer = destination if origin in TENERIFE_AIRPORTS else origin
        rule = transfer_rules[transfer]
        multiplier = float(rule["vueling_resident_fare_multiplier"])
        client = GoogleFlightsClient(family="Vueling")
        last_error: Exception | None = None
        result = None
        for attempt in range(4):
            try:
                html = client.availability(origin, destination, day)
                result = parse_google_flights_response(
                    html,
                    origin,
                    destination,
                    multiplier,
                    eur_pln,
                    accepted_marketing,
                )
                last_error = None
                break
            except (RuntimeError, json.JSONDecodeError, ValueError) as error:
                last_error = error
                if attempt + 1 < 4:
                    from scripts.source_scheduler import retry_delay
                    time_module.sleep(retry_delay(attempt, error))
        if last_error is not None or result is None:
            raise RuntimeError(
                f"Google Flights Vueling failed for {origin}-{destination} on {day}; "
                "publication blocked"
            ) from last_error
        record_checked("Vueling", origin, destination, day, day, result, "google_flights_http")
        return result

    legs: list[dict[str, Any]] = []
    max_workers = google_flights_worker_count(workers)
    print(
        "Google Flights: "
        f"{max_workers} równoległe zapytania "
        f"(bezpieczny limit {GOOGLE_FLIGHTS_MAX_WORKERS})",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for index, result in enumerate(executor.map(fetch, ordered), start=1):
            legs.extend(result)
            if index % 20 == 0 or index == len(ordered):
                print(
                    f"Vueling przez Google Flights: {index}/{len(ordered)} zapytań tras/dni",
                    flush=True,
                )
    return legs


def connection_id(legs: list[dict[str, Any]]) -> str:
    value = "|".join(
        f"{leg['carrier']}:{leg['flight_number']}:{leg['departure_at']}:{leg['arrival_at']}"
        for leg in legs
    )
    return f"step1c-{hashlib.sha256(value.encode()).hexdigest()[:16]}"


def build_connections(
    low_cost_legs: list[dict[str, Any]],
    vueling_legs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for low_cost in low_cost_legs:
        low_origin = low_cost["departure_airport"]
        low_destination = low_cost["arrival_airport"]
        poland_to_tenerife = low_origin in POLISH_AIRPORTS
        for vueling in vueling_legs:
            if poland_to_tenerife:
                if vueling["departure_airport"] != low_destination:
                    continue
                if vueling["arrival_airport"] not in TENERIFE_AIRPORTS:
                    continue
                layover = round(
                    (dt(vueling["departure_at"]) - dt(low_cost["arrival_at"]))
                    .total_seconds()
                    / 60
                )
                legs = [low_cost, vueling]
            else:
                if vueling["arrival_airport"] != low_origin:
                    continue
                if vueling["departure_airport"] not in TENERIFE_AIRPORTS:
                    continue
                layover = round(
                    (dt(low_cost["departure_at"]) - dt(vueling["arrival_at"]))
                    .total_seconds()
                    / 60
                )
                legs = [vueling, low_cost]
            if not MIN_LAYOVER_MINUTES <= layover <= MAX_LAYOVER_MINUTES:
                continue
            results.append({
                "id": connection_id(legs),
                "origin_airport": legs[0]["departure_airport"],
                "destination_airport": legs[-1]["arrival_airport"],
                "direction": (
                    "poland_to_tenerife"
                    if poland_to_tenerife
                    else "tenerife_to_poland"
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
                    sum(float(leg["price_resident_estimated_pln"]) for leg in legs),
                    2,
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
            raise RuntimeError(f"Połączenie 1C musi mieć dwa odcinki: {result['id']}")
        carriers = {leg["carrier"] for leg in result["legs"]}
        if "Vueling" not in carriers:
            raise RuntimeError(f"Brak odcinka Vuelinga w {result['id']}")
        if not carriers & {"Ryanair", "Wizz Air"}:
            raise RuntimeError(f"Brak odcinka Wizz/Ryanair w {result['id']}")
        for leg in result["legs"]:
            if not leg.get("booking_url"):
                raise RuntimeError(f"Brak booking_url w {result['id']}")
            if leg["carrier"] == "Vueling":
                validate_resident_price_estimate(leg)


@collection_entrypoint("1c")
def main(args) -> None:
    if args.days < 0:
        raise SystemExit("--days must be non-negative")
    end = args.from_date + timedelta(days=args.days)
    allowlist = json.loads(TRANSFER_FILE.read_text(encoding="utf-8"))
    validate_allowlist(allowlist)
    configure_airports_from_allowlist(allowlist)
    transfers = [airport["iata"] for airport in allowlist["airports"]]
    transfer_rules = {airport["iata"]: airport for airport in allowlist["airports"]}

    eur = nbp_eur_rate(args.from_date)
    rates = {"EUR": eur, "PLN": CurrencyRate("PLN", 1.0)}
    print(f"NBP EUR: {eur.pln:.4f} PLN", flush=True)
    low_cost_legs = collect_low_cost_legs(
        allowlist,
        args.from_date,
        end,
        rates,
        args.workers,
    )
    if not low_cost_legs:
        raise RuntimeError(
            "Nie pobrano żadnego odcinka Wizz/Ryanair; wynik nie zostanie nadpisany"
        )
    print(f"Odcinki Ryanair/Wizz Air: {len(low_cost_legs)}", flush=True)
    route_days = vueling_route_days(allowlist, args.from_date, end)
    print(f"Zapytania Vueling do sprawdzenia: {len(route_days)}", flush=True)
    vueling_legs = collect_vueling_legs(
        route_days,
        transfer_rules,
        allowlist["vueling_airline_codes"],
        args.workers,
        eur.pln,
    )
    if route_days and not vueling_legs:
        raise RuntimeError(
            "Vueling nie zwrócił żadnych odcinków; wynik nie zostanie nadpisany"
        )
    print(f"Odcinki Vueling: {len(vueling_legs)}", flush=True)
    results = build_connections(low_cost_legs, vueling_legs)

    generated_at = datetime.now(ZoneInfo("Atlantic/Canary")).isoformat(
        timespec="seconds"
    )
    document = {
        "schema_version": 2,
        "generated_at": generated_at,
        "period_from": args.from_date.isoformat(),
        "period_to": end.isoformat(),
        "step": "1C",
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
            "vueling_routes": "Vueling official Tenerife route page",
            "vueling_prices": (
                "Google Flights: regularna cena w PLN; cena rezydenta "
                "oszacowana jako 25% części taryfowej plus stałe opłaty Aena"
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
    counts = {
        direction: sum(result["direction"] == direction for result in results)
        for direction in document["directions"]
    }
    print(f"Zapisano {len(results)} połączeń do {args.output}", flush=True)
    print(json.dumps(counts, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
