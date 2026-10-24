#!/usr/bin/env python3
"""Build Step 1E: Volotea + Ryanair or Wizz Air.

Volotea route, schedule and regular-fare data come directly from the carrier's
official public MinPrice endpoint.  Google Flights is deliberately not used.
The Canary resident estimate discounts only the fare component and preserves
fixed Aena fees. Price filtering is left to the website.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any
from zoneinfo import ZoneInfo

from curl_cffi import requests

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.collection_coverage import collection_entrypoint, publish_document, record_checked
from scripts.booking_urls import volotea_booking_url
from scripts.collect_step1 import (
    MAX_LAYOVER_MINUTES,
    MIN_LAYOVER_MINUTES,
    POLISH_AIRPORTS,
    TENERIFE_AIRPORTS,
    CurrencyRate,
    configure_airports_from_allowlist,
    date_range,
    dt,
    local_datetime,
    money_pln,
    nbp_eur_rate,
    serialize_datetime,
)
from scripts.collect_step1c import collect_low_cost_legs
from scripts.spanish_resident_fees import (
    apply_resident_price_estimate,
    nondiscountable_fee_eur,
    validate_resident_price_estimate,
)


ROOT = Path(__file__).resolve().parents[1]
TRANSFER_FILE = ROOT / "data" / "volotea-transfer-airports.json"
DEFAULT_OUTPUT = ROOT / "data" / "step1e-results.json"


def cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=6)
    return parser.parse_args()


def validate_allowlist(allowlist: dict[str, Any]) -> None:
    if allowlist.get("usage_policy", {}).get("step") != "1E":
        raise RuntimeError("Lista Volotei nie jest oznaczona jako krok 1E")
    config = allowlist.get("fare_feed") or {}
    if config.get("endpoint") != "https://api.volotea.com/v1/Cache/MinPrice":
        raise RuntimeError("Nieprawidłowy oficjalny endpoint Volotei")
    if config.get("currency") != "EUR" or config.get("airline_code") != "V7":
        raise RuntimeError("Nieprawidłowa konfiguracja taryf Volotei")
    airports = allowlist.get("airports") or []
    if not airports:
        raise RuntimeError("Lista lotnisk Volotei jest pusta")
    for airport in airports:
        code = airport["iata"]
        ZoneInfo(airport["timezone"])
        if not airport.get("resident_discount_eligible_on_volotea_leg"):
            raise RuntimeError(f"Krok 1E nie może zawierać trasy bez zniżki: {code}")
        if float(airport.get("volotea_resident_fare_multiplier", 0)) != 0.25:
            raise RuntimeError(f"Nieprawidłowy mnożnik Volotei dla {code}")
        tenerife_airports = airport.get("tenerife_airports") or []
        if not tenerife_airports or not set(tenerife_airports) <= set(TENERIFE_AIRPORTS):
            raise RuntimeError(f"Nieprawidłowa lista lotnisk Teneryfy dla {code}")
        for route in airport.get("polish_routes") or []:
            if route["polish_airport"] not in POLISH_AIRPORTS:
                raise RuntimeError(f"Nieprawidłowe polskie lotnisko dla {code}")
            carriers = set(route.get("airlines") or [])
            if not carriers or not carriers <= {"Ryanair", "Wizz Air"}:
                raise RuntimeError(f"Nieprawidłowy drugi przewoźnik dla {code}")
        if not airport.get("polish_routes"):
            raise RuntimeError(f"Brak tras do Polski dla {code}")


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


def volotea_route_days(
    allowlist: dict[str, Any],
    start: date,
    end: date,
) -> set[tuple[str, str, date]]:
    """Return every saved Volotea route/day in both directions.

    The carrier calendar must be collected independently of the low-cost
    timetable.  Connections are matched only after the complete Volotea
    window has been fetched.
    """

    route_days: set[tuple[str, str, date]] = set()
    for transfer in allowlist["airports"]:
        for tenerife in transfer["tenerife_airports"]:
            for day in date_range(start, end):
                route_days.add((tenerife, transfer["iata"], day))
                route_days.add((transfer["iata"], tenerife, day))
    return route_days


class VoloteaFareClient:
    """Read-only client for Volotea's public route/day fare endpoint."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    def search(self, origin: str, destination: str, day: date) -> dict[str, Any]:
        request_data = {
            "Content": [{
                "AnyPeriod": False,
                "FareType": "R",
                "StartDate": day.isoformat(),
                "EndDate": day.isoformat(),
                "Value": [],
                "MarketType": "SSS-*",
                "MarketValue": f"{origin}-{destination}",
                "MaxResults": "99",
                "PriceWithFee": True,
                "ReturnFlightDate": "",
                "userType": "standard",
            }]
        }
        from scripts.source_scheduler import http_request
        response = http_request(requests.get,
            self.endpoint,
            params={"data": json.dumps(request_data, separators=(",", ":"))},
            headers={
                "accept": "application/json, text/plain, */*",
                "origin": "https://www.volotea.com",
                "referer": "https://www.volotea.com/",
            },
            impersonate="chrome",
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("Success") is not True:
            raise RuntimeError(
                f"Oficjalny endpoint Volotei odrzucił {origin}-{destination} "
                f"{day}: {payload.get('Error') or 'brak opisu'}"
            )
        return payload


def parse_volotea_response(
    payload: dict[str, Any],
    origin: str,
    destination: str,
    day: date,
    multiplier: float,
    rates: dict[str, CurrencyRate],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Transform direct Volotea flights from one official route/day response."""

    if payload.get("Success") is not True:
        raise RuntimeError("Odpowiedź Volotei nie ma statusu Success=true")
    currency = str(config["currency"]).upper()
    price_field = str(config["price_field"])
    airline_code = str(config["airline_code"]).upper()
    best: dict[tuple[str, str, str], dict[str, Any]] = {}
    for content in payload.get("Content") or []:
        for record in content.get("Value") or []:
            if str(record.get("Market", "")).upper() != f"{origin}-{destination}":
                continue
            if str(record.get("DepartureFlightDate", ""))[:10] != day.isoformat():
                continue
            if record.get("ConnectionInformation"):
                continue
            try:
                departure = local_datetime(str(record["DepartureTime"]), origin)
                arrival = local_datetime(str(record["ArrivalTime"]), destination)
                amount = float(record[price_field])
            except (KeyError, TypeError, ValueError):
                continue
            if arrival <= departure:
                continue
            if amount <= 0:
                continue
            raw_number = str(record.get("FlightNumber", "")).strip()
            if not re.fullmatch(r"(?:V7)?\d+", raw_number, re.IGNORECASE):
                continue
            number = raw_number.upper()
            if not number.startswith(airline_code):
                number = f"{airline_code}{number}"
            regular_pln = money_pln(amount, currency, rates)
            leg = {
                "carrier": "Volotea",
                "flight_number": number,
                "departure_airport": origin,
                "departure_at": serialize_datetime(departure),
                "arrival_airport": destination,
                "arrival_at": serialize_datetime(arrival),
                "price_regular_pln": regular_pln,
                "resident_discount_eligible": True,
                "resident_fare_multiplier": multiplier,
                "booking_url": volotea_booking_url(origin, destination, departure),
                "price_source": "Volotea official MinPrice endpoint",
                "price_scope": "official_route_flight_fare_with_fees",
                "price_source_currency": currency,
                "price_source_amount": amount,
                "schedule_source": "Volotea official MinPrice endpoint",
            }
            if isinstance(record.get("Taxes"), (int, float)):
                leg["price_source_taxes"] = float(record["Taxes"])
                expected_taxes = nondiscountable_fee_eur(origin, destination, departure)
                if round(float(record["Taxes"]), 2) != expected_taxes:
                    raise RuntimeError(
                        f"Podatki Volotei nie zgadzają się z tabelą Aena dla {origin}-{destination}"
                    )
            apply_resident_price_estimate(leg, rates["EUR"].pln)
            key = (number, leg["departure_at"], leg["arrival_at"])
            previous = best.get(key)
            if previous is None or regular_pln < previous["price_regular_pln"]:
                best[key] = leg
    return sorted(best.values(), key=lambda leg: leg["departure_at"])


def collect_volotea_legs(
    candidates: set[tuple[str, str, date]],
    allowlist: dict[str, Any],
    rates: dict[str, CurrencyRate],
    workers: int,
    client: VoloteaFareClient | None = None,
) -> list[dict[str, Any]]:
    from scripts.source_repository import cached_days
    cached = cached_days("Volotea", candidates, "official_minprice")
    if cached is not None:
        return cached
    if not candidates:
        return []
    config = allowlist["fare_feed"]
    rules = {airport["iata"]: airport for airport in allowlist["airports"]}
    fare_client = client or VoloteaFareClient(config["endpoint"])
    ordered = sorted(candidates, key=lambda item: (item[2], item[0], item[1]))

    from scripts.source_repository import abort_on_source_failure
    @abort_on_source_failure
    def fetch(candidate: tuple[str, str, date]) -> list[dict[str, Any]]:
        origin, destination, day = candidate
        from scripts.source_repository import cached_route
        cached = cached_route("Volotea", origin, destination, day, day)
        if cached is not None:
            return cached
        transfer = destination if origin in TENERIFE_AIRPORTS else origin
        multiplier = float(rules[transfer]["volotea_resident_fare_multiplier"])
        payload = fare_client.search(origin, destination, day)
        result = parse_volotea_response(
            payload, origin, destination, day, multiplier, rates, config
        )
        record_checked("Volotea", origin, destination, day, day, result, "official_minprice")
        return result

    legs: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(max(workers, 1), 4)) as executor:
        for index, found in enumerate(executor.map(fetch, ordered), start=1):
            legs.extend(found)
            if index % 10 == 0 or index == len(ordered):
                print(
                    f"Volotea: {index}/{len(ordered)} oficjalnych zapytań tras/dni",
                    flush=True,
                )
    unique = {
        (leg["flight_number"], leg["departure_at"], leg["arrival_at"]): leg
        for leg in legs
    }
    return sorted(unique.values(), key=lambda leg: leg["departure_at"])


def connection_id(legs: list[dict[str, Any]]) -> str:
    value = "|".join(
        f"{leg['carrier']}:{leg['flight_number']}:{leg['departure_at']}:{leg['arrival_at']}"
        for leg in legs
    )
    return f"step1e-{hashlib.sha256(value.encode()).hexdigest()[:16]}"


def build_connections(
    low_cost_legs: list[dict[str, Any]],
    volotea_legs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for low_cost in low_cost_legs:
        poland_to_tenerife = low_cost["departure_airport"] in POLISH_AIRPORTS
        for volotea in volotea_legs:
            if poland_to_tenerife:
                if volotea["departure_airport"] != low_cost["arrival_airport"]:
                    continue
                if volotea["arrival_airport"] not in TENERIFE_AIRPORTS:
                    continue
                layover = round(
                    (dt(volotea["departure_at"]) - dt(low_cost["arrival_at"]))
                    .total_seconds() / 60
                )
                legs = [low_cost, volotea]
            else:
                if volotea["arrival_airport"] != low_cost["departure_airport"]:
                    continue
                if volotea["departure_airport"] not in TENERIFE_AIRPORTS:
                    continue
                layover = round(
                    (dt(low_cost["departure_at"]) - dt(volotea["arrival_at"]))
                    .total_seconds() / 60
                )
                legs = [volotea, low_cost]
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
            raise RuntimeError(f"Połączenie 1E musi mieć dwa odcinki: {result['id']}")
        carriers = {leg["carrier"] for leg in result["legs"]}
        if "Volotea" not in carriers or not carriers & {"Ryanair", "Wizz Air"}:
            raise RuntimeError(f"Nieprawidłowi przewoźnicy w {result['id']}")
        for leg in result["legs"]:
            if not leg.get("booking_url"):
                raise RuntimeError(f"Brak booking_url w {result['id']}")
            if leg["carrier"] == "Volotea" and leg.get("price_source") != (
                "Volotea official MinPrice endpoint"
            ):
                raise RuntimeError(f"Niedozwolone źródło ceny w {result['id']}")
            if leg["carrier"] == "Volotea":
                validate_resident_price_estimate(leg)


@collection_entrypoint("1e")
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
        raise RuntimeError(str(error).replace("1C", "1E")) from error
    if not low_cost:
        raise RuntimeError(
            "Nie pobrano żadnego odcinka Wizz/Ryanair; wynik 1E nie zostanie nadpisany"
        )
    print(f"Odcinki Ryanair/Wizz Air: {len(low_cost)}", flush=True)

    route_days = volotea_route_days(allowlist, args.from_date, end)
    print(f"Zapytania Volotea do sprawdzenia: {len(route_days)}", flush=True)
    volotea = collect_volotea_legs(route_days, allowlist, rates, args.workers)
    print(f"Odcinki Volotea: {len(volotea)}", flush=True)
    results = build_connections(low_cost, volotea)

    generated_at = datetime.now(ZoneInfo("Atlantic/Canary")).isoformat(
        timespec="seconds"
    )
    document = {
        "schema_version": 2,
        "generated_at": generated_at,
        "period_from": args.from_date.isoformat(),
        "period_to": end.isoformat(),
        "step": "1E",
        "directions": ["tenerife_to_poland", "poland_to_tenerife"],
        "transfer_airports": [airport["iata"] for airport in allowlist["airports"]],
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
            "volotea_routes_schedules_and_prices": (
                "Volotea official route pages and public MinPrice endpoint; "
                "regular fare with fees, no Google Flights"
            ),
            "volotea_resident_price": (
                "estimate: 25% of the official fare component plus fixed Aena fees"
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
