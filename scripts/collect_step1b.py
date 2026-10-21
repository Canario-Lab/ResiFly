#!/usr/bin/env python3
"""Build Step 1B: Iberia/Iberia Express + Ryanair or Wizz Air.

The collector reads a fixed transfer-airport allowlist, checks both travel
directions and keeps every valid 2–24 hour self-transfer. Price filtering is
left to the website. Regular Iberia prices come from Google Flights and the
resident estimate is calculated explicitly from the configured 25% multiplier.
No real browser, browser session or Iberia access token is required.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import sys
import time as time_module
from typing import Any
from zoneinfo import ZoneInfo

from curl_cffi import requests
from fast_flights import FlightData, Passengers, create_filter
from selectolax.lexbor import LexborHTMLParser

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.booking_urls import iberia_booking_url
from scripts.collect_step1 import (
    AIRPORT_TIMEZONES,
    MAX_LAYOVER_MINUTES,
    MIN_LAYOVER_MINUTES,
    POLISH_AIRPORTS,
    TENERIFE_AIRPORTS,
    CurrencyRate,
    collect_low_cost_legs,
    configure_airports_from_allowlist,
    date_range,
    dt,
    nbp_eur_rate,
    serialize_datetime,
    wizz_schedules_from_allowlist,
)


ROOT = Path(__file__).resolve().parents[1]
TRANSFER_FILE = ROOT / "data" / "iberia-transfer-airports.json"
DEFAULT_OUTPUT = ROOT / "data" / "step1b-results.json"

GOOGLE_FLIGHTS_URL = "https://www.google.com/travel/flights"
GOOGLE_CONSENT_COOKIES = {
    "CONSENT": "YES+",
    # A non-personalized/reject-all consent state. It prevents the European
    # consent interstitial from replacing the flight results HTML.
    "SOCS": "CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg",
}


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
    parser.add_argument("--workers", type=int, default=10)
    return parser.parse_args()


class GoogleFlightsClient:
    """HTTP-only Google Flights client used for regular airline fares."""

    def __init__(self) -> None:
        self.session = requests.Session(impersonate="chrome")

    def _request(self, params: dict[str, str]) -> str:
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                response = self.session.get(
                    GOOGLE_FLIGHTS_URL,
                    params=params,
                    cookies=GOOGLE_CONSENT_COOKIES,
                    headers={"Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8"},
                    timeout=60,
                )
                response.raise_for_status()
                if "Before you continue to Google" in response.text:
                    raise RuntimeError("Google zwrócił ekran zgody zamiast wyników")
                return response.text
            except Exception as error:
                last_error = error
                if attempt + 1 < 4:
                    time_module.sleep(1.5 * (attempt + 1))
        raise RuntimeError(
            "Google Flights nie zwrócił wyników dla zapytania przewoźnika. "
            "Poprzedni plik wynikowy nie został nadpisany."
        ) from last_error

    def availability(
        self,
        origin: str,
        destination: str,
        departure_date: date,
    ) -> str:
        query = create_filter(
            flight_data=[
                FlightData(
                    date=departure_date.isoformat(),
                    from_airport=origin,
                    to_airport=destination,
                )
            ],
            trip="one-way",
            passengers=Passengers(adults=1),
            seat="economy",
            max_stops=0,
        )
        return self._request({
            "tfs": query.as_b64().decode("utf-8"),
            "hl": "pl",
            "gl": "US",
            "tfu": "EgQIABABIgA",
            "curr": "PLN",
        })


def _at(value: Any, index: int, default: Any = None) -> Any:
    return value[index] if isinstance(value, list) and len(value) > index else default


def _google_datetime(date_parts: Any, time_parts: Any, airport: str) -> datetime:
    if not isinstance(date_parts, list) or len(date_parts) < 3:
        raise ValueError("Google Flights nie zwrócił pełnej daty lotu")
    hour = int(_at(time_parts, 0, 0) or 0)
    minute = int(_at(time_parts, 1, 0) or 0)
    return datetime(
        int(date_parts[0]),
        int(date_parts[1]),
        int(date_parts[2]),
        hour,
        minute,
        tzinfo=ZoneInfo(AIRPORT_TIMEZONES[airport]),
    )


def _google_flights_payload(html: str) -> list[Any]:
    parser = LexborHTMLParser(html)
    script = next(
        (
            node
            for node in parser.css("script")
            if "ds:1" in (node.attributes.get("class") or "").split()
        ),
        None,
    )
    if script is None:
        raise RuntimeError("Google Flights nie zwrócił danych lotów")
    text = script.text()
    if "data:" not in text:
        raise RuntimeError("Nieznany format odpowiedzi Google Flights")
    raw = text.split("data:", 1)[1].rsplit(",", 1)[0]
    payload = json.loads(raw)
    try:
        result_block = payload[3]
    except (IndexError, TypeError):
        raise RuntimeError("Nieznana struktura wyników Google Flights")
    if result_block is None:
        return []
    if not isinstance(result_block, list) or not result_block:
        raise RuntimeError("Nieznana struktura wyników Google Flights")
    return result_block[0] or []


def parse_google_flights_response(
    html: str,
    origin: str,
    destination: str,
    multiplier: float,
    accepted_marketing: set[str],
) -> list[dict[str, Any]]:
    """Transform direct Iberia-group offers from Google Flights HTML."""

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
        operating_name = str(_at(segment, 2, "") or _at(flight, 3, ""))
        carrier = (
            "Iberia Express"
            if marketing_code == "I2" or "express" in operating_name.lower()
            else "Iberia"
        )
        regular_pln = round(float(amount), 2)
        leg = {
            "carrier": carrier,
            "flight_number": number,
            "departure_airport": origin,
            "departure_at": serialize_datetime(departure),
            "arrival_airport": destination,
            "arrival_at": serialize_datetime(arrival),
            "price_regular_pln": regular_pln,
            "resident_discount_eligible": True,
            "resident_fare_multiplier": multiplier,
            "price_resident_estimated_pln": round(regular_pln * multiplier, 2),
            "resident_price_source": (
                "estimated as configured percentage of Google Flights regular fare"
            ),
            "booking_url": iberia_booking_url(origin, destination, departure),
            "price_source": "Google Flights",
            "price_source_currency": "PLN",
            "price_source_amount": amount,
        }
        numeric_flight = "".join(character for character in raw_number if character.isdigit())
        key = (numeric_flight or raw_number, leg["departure_at"], leg["arrival_at"])
        previous = best_by_flight.get(key)
        if previous is None or regular_pln < previous["price_regular_pln"]:
            best_by_flight[key] = leg
    return sorted(best_by_flight.values(), key=lambda leg: leg["departure_at"])


def collect_iberia_trip(
    client: GoogleFlightsClient,
    origin: str,
    destination: str,
    departure_date: date,
    multiplier: float,
    accepted_marketing: set[str],
) -> list[dict[str, Any]]:
    return parse_google_flights_response(
        client.availability(origin, destination, departure_date),
        origin,
        destination,
        multiplier,
        accepted_marketing,
    )


def iberia_route_days(
    allowlist: dict[str, Any],
    start: date,
    end: date,
) -> set[tuple[str, str, date]]:
    route_days: set[tuple[str, str, date]] = set()
    for airport in allowlist["airports"]:
        transfer = airport["iata"]
        for tenerife in airport["tenerife_airports"]:
            for day in date_range(start, end):
                route_days.add((transfer, tenerife, day))
                route_days.add((tenerife, transfer, day))
    return route_days


def collect_iberia_legs(
    route_days: set[tuple[str, str, date]],
    transfer_rules: dict[str, dict[str, Any]],
    airline_codes: dict[str, Any],
    workers: int,
) -> list[dict[str, Any]]:
    if not route_days:
        return []
    accepted_marketing = set(airline_codes["accepted_marketing"])
    legs: list[dict[str, Any]] = []
    ordered = sorted(route_days, key=lambda item: (item[2], item[0], item[1]))

    def fetch(candidate: tuple[str, str, date]) -> list[dict[str, Any]]:
        origin, destination, day = candidate
        transfer = destination if origin in TENERIFE_AIRPORTS else origin
        rule = transfer_rules[transfer]
        if not rule["resident_discount_eligible_on_iberia_leg"]:
            raise RuntimeError(f"Lotnisko {transfer} nie ma zniżki wymaganej w 1B")
        multiplier = float(rule["iberia_resident_fare_multiplier"])
        if not 0 < multiplier < 1:
            raise RuntimeError(f"Nieprawidłowy mnożnik zniżki Iberii dla {transfer}")
        return collect_iberia_trip(
            GoogleFlightsClient(),
            origin,
            destination,
            day,
            multiplier,
            accepted_marketing,
        )

    max_workers = min(max(workers, 1), 4)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for index, result in enumerate(executor.map(fetch, ordered), start=1):
            legs.extend(result)
            if index % 10 == 0 or index == len(ordered):
                print(
                    f"Iberia przez Google Flights: {index}/{len(ordered)} zapytań tras/dni",
                    flush=True,
                )
    return legs


def connection_id(legs: list[dict[str, Any]]) -> str:
    value = "|".join(
        f"{leg['carrier']}:{leg['flight_number']}:{leg['departure_at']}:{leg['arrival_at']}"
        for leg in legs
    )
    return f"step1b-{hashlib.sha256(value.encode()).hexdigest()[:16]}"


def build_connections(
    low_cost_legs: list[dict[str, Any]],
    iberia_legs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for low_cost in low_cost_legs:
        low_origin = low_cost["departure_airport"]
        low_destination = low_cost["arrival_airport"]
        poland_to_tenerife = low_origin in POLISH_AIRPORTS
        for iberia in iberia_legs:
            if poland_to_tenerife:
                if iberia["departure_airport"] != low_destination:
                    continue
                if iberia["arrival_airport"] not in TENERIFE_AIRPORTS:
                    continue
                layover = round(
                    (dt(iberia["departure_at"]) - dt(low_cost["arrival_at"]))
                    .total_seconds()
                    / 60
                )
                legs = [low_cost, iberia]
            else:
                if iberia["arrival_airport"] != low_origin:
                    continue
                if iberia["departure_airport"] not in TENERIFE_AIRPORTS:
                    continue
                layover = round(
                    (dt(low_cost["departure_at"]) - dt(iberia["arrival_at"]))
                    .total_seconds()
                    / 60
                )
                legs = [iberia, low_cost]
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
                    sum(
                        float(leg["price_resident_estimated_pln"])
                        for leg in legs
                    ),
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


def validate_allowlist(allowlist: dict[str, Any]) -> None:
    if allowlist.get("usage_policy", {}).get("step") != "1B":
        raise RuntimeError("Lista Iberii nie jest oznaczona jako krok 1B")
    airports = allowlist.get("airports") or []
    if not airports:
        raise RuntimeError("Lista lotnisk Iberii jest pusta")
    for airport in airports:
        ZoneInfo(airport["timezone"])
        if not airport.get("resident_discount_eligible_on_iberia_leg"):
            raise RuntimeError(
                f"Krok 1B nie może zawierać trasy bez zniżki: {airport['iata']}"
            )


def validate_document(document: dict[str, Any]) -> None:
    for result in document["results"]:
        if len(result["legs"]) != 2:
            raise RuntimeError(f"Połączenie 1B musi mieć dwa odcinki: {result['id']}")
        carriers = {leg["carrier"] for leg in result["legs"]}
        if not carriers & {"Iberia", "Iberia Express"}:
            raise RuntimeError(f"Brak odcinka Iberii w {result['id']}")
        if not carriers & {"Ryanair", "Wizz Air"}:
            raise RuntimeError(f"Brak odcinka Wizz/Ryanair w {result['id']}")
        for leg in result["legs"]:
            if not leg.get("booking_url"):
                raise RuntimeError(f"Brak booking_url w {result['id']}")


def main() -> None:
    args = cli()
    if args.days < 0:
        raise SystemExit("--days must be non-negative")
    end = args.from_date + timedelta(days=args.days)
    allowlist = json.loads(TRANSFER_FILE.read_text(encoding="utf-8"))
    validate_allowlist(allowlist)
    configure_airports_from_allowlist(allowlist)
    transfers = [airport["iata"] for airport in allowlist["airports"]]
    transfer_rules = {airport["iata"]: airport for airport in allowlist["airports"]}
    wizz_schedules = wizz_schedules_from_allowlist(allowlist)

    eur = nbp_eur_rate(args.from_date)
    rates = {"EUR": eur, "PLN": CurrencyRate("PLN", 1.0)}
    print(f"NBP EUR: {eur.pln:.4f} PLN", flush=True)
    low_cost_legs = collect_low_cost_legs(
        transfers,
        args.from_date,
        end,
        rates,
        args.workers,
        wizz_schedules,
    )
    if not low_cost_legs:
        raise RuntimeError(
            "Nie pobrano żadnego odcinka Wizz/Ryanair; wynik nie zostanie nadpisany"
        )
    print(f"Odcinki Ryanair/Wizz Air: {len(low_cost_legs)}", flush=True)
    route_days = iberia_route_days(allowlist, args.from_date, end)
    print(
        f"Pełny kalendarz Iberii do sprawdzenia: {len(route_days)} tras/dni",
        flush=True,
    )
    iberia_legs = collect_iberia_legs(
        route_days,
        transfer_rules,
        allowlist["iberia_airline_codes"],
        args.workers,
    )
    if route_days and not iberia_legs:
        raise RuntimeError(
            "Iberia nie zwróciła żadnych odcinków; wynik nie zostanie nadpisany"
        )
    print(f"Odcinki Iberia/Iberia Express: {len(iberia_legs)}", flush=True)
    results = build_connections(low_cost_legs, iberia_legs)

    generated_at = datetime.now(ZoneInfo("Atlantic/Canary")).isoformat(
        timespec="seconds"
    )
    document = {
        "schema_version": 2,
        "generated_at": generated_at,
        "period_from": args.from_date.isoformat(),
        "period_to": end.isoformat(),
        "step": "1B",
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
            "iberia": (
                "Google Flights: regularna cena w PLN; cena rezydenta "
                "oszacowana jako 25% ceny regularnej zgodnie z listą lotnisk"
            ),
            "ryanair": "Ryanair Fare Finder",
            "wizz_air": "Wizz Air timetableV2",
        },
        "result_status": "ok" if results else "no_matching_connections",
        "results": results,
    }
    validate_document(document)
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
