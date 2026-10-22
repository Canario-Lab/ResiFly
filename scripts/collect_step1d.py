#!/usr/bin/env python3
"""Build Step 1D: Air Europa + Ryanair or Wizz Air.

Air Europa prices come directly from the public branded fare feed embedded in
the carrier's official offer pages.  Google Flights is deliberately not used.
The feed exposes the lowest regular route/day fare but not flight times, so the
collector combines it with the verified, date-bounded timetable templates in
the fixed Step 1D allowlist.  The resident value is explicitly an estimate of
25% of the regular fare.  Price filtering is left to the website.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta
import hashlib
from html import unescape
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from curl_cffi import requests

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.collection_coverage import collection_entrypoint, publish_document, record_checked
from scripts.booking_urls import air_europa_booking_url
from scripts.collect_step1 import (
    AIRPORT_TIMEZONES,
    MAX_LAYOVER_MINUTES,
    MIN_LAYOVER_MINUTES,
    POLISH_AIRPORTS,
    TENERIFE_AIRPORTS,
    CurrencyRate,
    configure_airports_from_allowlist,
    date_range,
    dt,
    money_pln,
    nbp_eur_rate,
    serialize_datetime,
)
from scripts.collect_step1c import collect_low_cost_legs


ROOT = Path(__file__).resolve().parents[1]
TRANSFER_FILE = ROOT / "data" / "air-europa-transfer-airports.json"
DEFAULT_OUTPUT = ROOT / "data" / "step1d-results.json"
NEXT_DATA = re.compile(
    r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.DOTALL,
)


def cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=6)
    return parser.parse_args()


def _walk(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def extract_sputnik_config(page_html: str, tenant: str) -> tuple[str, dict[str, str]]:
    """Extract the temporary fare-feed endpoint/key from Air Europa's page."""

    match = NEXT_DATA.search(page_html)
    if not match:
        raise RuntimeError("Strona Air Europa nie zawiera konfiguracji taryf")
    try:
        page_data = json.loads(unescape(match.group(1)))
    except json.JSONDecodeError as error:
        raise RuntimeError("Nie można odczytać konfiguracji strony Air Europa") from error

    for node in _walk(page_data):
        service = node.get("sputnikSearch")
        if not isinstance(service, dict):
            continue
        config = service.get("config") or service
        if not isinstance(config, dict):
            continue
        endpoint = config.get("endpoint")
        axios = config.get("axiosConfig") or {}
        headers = axios.get("headers") or {}
        if not isinstance(endpoint, str) or not isinstance(headers, dict):
            continue
        normalized_headers = {str(key): str(value) for key, value in headers.items()}
        if not any(key.lower() == "em-api-key" for key in normalized_headers):
            continue
        endpoint = endpoint.replace("%%tenantCode%%", tenant)
        return endpoint, normalized_headers
    raise RuntimeError("Strona Air Europa nie udostępniła klucza do feedu taryf")


class AirEuropaFareClient:
    """Read-only client for the fare feed configured by Air Europa's website."""

    def __init__(self, config_page: str, tenant: str, market: str, language: str):
        response = requests.get(config_page, impersonate="chrome", timeout=60)
        response.raise_for_status()
        self.endpoint, feed_headers = extract_sputnik_config(response.text, tenant)
        self.config_page = config_page
        self.market = market
        self.language = language
        self.headers = {
            **feed_headers,
            "content-type": "application/json",
            "origin": "https://www.aireuropa.com",
            "referer": config_page,
        }

    def search(
        self,
        origin: str,
        destination: str,
        start: date,
        end: date,
    ) -> Any:
        payload = {
            "autoSettings": {"language": self.language, "market": self.market},
            "origins": [origin],
            "destinations": [destination],
            "journeyType": "ONE_WAY",
            "departure": {"start": start.isoformat(), "end": end.isoformat()},
            "routesLimit": 1,
            "faresLimit": 100,
            "faresPerRoute": 100,
        }
        response = requests.post(
            self.endpoint,
            headers=self.headers,
            json=payload,
            impersonate="chrome",
            timeout=60,
        )
        response.raise_for_status()
        return response.json()


def validate_allowlist(allowlist: dict[str, Any]) -> None:
    if allowlist.get("usage_policy", {}).get("step") != "1D":
        raise RuntimeError("Lista Air Europa nie jest oznaczona jako krok 1D")
    if not allowlist.get("airports"):
        raise RuntimeError("Lista lotnisk Air Europa jest pusta")
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

    direct_routes = {
        (tenerife, airport["iata"])
        for airport in allowlist["airports"]
        for tenerife in airport["tenerife_airports"]
    }
    direct_routes |= {(destination, origin) for origin, destination in direct_routes}
    schedule_routes = {
        (item["origin"], item["destination"])
        for item in allowlist.get("air_europa_schedule_templates", [])
    }
    missing = direct_routes - schedule_routes
    if missing:
        raise RuntimeError(f"Brak rozkładu Air Europa dla tras: {sorted(missing)}")


def validate_schedule_window(allowlist: dict[str, Any], start: date, end: date) -> None:
    templates = allowlist["air_europa_schedule_templates"]
    first = min(date.fromisoformat(item["valid_from"]) for item in templates)
    last = max(date.fromisoformat(item["valid_to"]) for item in templates)
    if start < first or end > last:
        raise RuntimeError(
            "Okno wyszukiwania wykracza poza zweryfikowany rozkład Air Europa "
            f"({first}–{last}); przed zapisem trzeba odświeżyć szablony w allowliście"
        )


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


def parse_air_europa_fares(
    payload: Any,
    origin: str,
    destination: str,
    airline_code: str = "UX",
) -> dict[date, tuple[float, str]]:
    """Return the lowest official regular fare for each route/day."""

    best: dict[date, tuple[float, str]] = {}
    for record in _walk(payload):
        flight = record.get("outboundFlight")
        price = record.get("priceSpecification")
        if not isinstance(flight, dict) or not isinstance(price, dict):
            continue
        if str(flight.get("departureAirportIataCode", "")).upper() != origin:
            continue
        if str(flight.get("arrivalAirportIataCode", "")).upper() != destination:
            continue
        airline = record.get("airline") or flight.get("airline") or {}
        if str(airline.get("iataCode", "")).upper() != airline_code:
            continue
        raw_day = flight.get("departureDate") or record.get("departureDate")
        try:
            day = date.fromisoformat(str(raw_day)[:10])
            amount = float(price["totalPrice"])
            currency = str(price["currencyCode"]).upper()
        except (KeyError, TypeError, ValueError):
            continue
        if amount <= 0 or not re.fullmatch(r"[A-Z]{3}", currency):
            continue
        previous = best.get(day)
        if previous is None or amount < previous[0]:
            best[day] = (amount, currency)
    return best


def scheduled_departures(
    allowlist: dict[str, Any], origin: str, destination: str, day: date
) -> list[tuple[datetime, datetime]]:
    results: list[tuple[datetime, datetime]] = []
    for template in allowlist["air_europa_schedule_templates"]:
        if (template["origin"], template["destination"]) != (origin, destination):
            continue
        if not date.fromisoformat(template["valid_from"]) <= day <= date.fromisoformat(
            template["valid_to"]
        ):
            continue
        if day.weekday() not in template["weekdays"]:
            continue
        for item in template["departures"]:
            departure = datetime.combine(
                day,
                time.fromisoformat(item["time"]),
                tzinfo=ZoneInfo(AIRPORT_TIMEZONES[origin]),
            )
            arrival = (departure + timedelta(minutes=int(item["duration_minutes"]))).astimezone(
                ZoneInfo(AIRPORT_TIMEZONES[destination])
            )
            results.append((departure, arrival))
    return sorted(results)


def collect_air_europa_legs(
    route_days: set[tuple[str, str, date]],
    allowlist: dict[str, Any],
    rates: dict[str, CurrencyRate],
    client: AirEuropaFareClient,
) -> list[dict[str, Any]]:
    if not route_days:
        return []
    config = allowlist["fare_feed"]
    rules = {airport["iata"]: airport for airport in allowlist["airports"]}
    grouped_route_days: dict[tuple[str, str], set[date]] = {}
    for origin, destination, day in route_days:
        grouped_route_days.setdefault((origin, destination), set()).add(day)

    legs: list[dict[str, Any]] = []
    for origin, destination in sorted(grouped_route_days):
        days = grouped_route_days[(origin, destination)]
        payload = client.search(origin, destination, min(days), max(days))
        fares = parse_air_europa_fares(
            payload, origin, destination, config["airline_code"]
        )
        transfer = destination if origin in TENERIFE_AIRPORTS else origin
        multiplier = float(rules[transfer]["air_europa_resident_fare_multiplier"])
        for day in sorted(days):
            if day not in fares:
                continue
            amount, currency = fares[day]
            regular_pln = money_pln(amount, currency, rates)
            for departure, arrival in scheduled_departures(
                allowlist, origin, destination, day
            ):
                legs.append({
                    "carrier": "Air Europa",
                    "flight_number": "UX",
                    "departure_airport": origin,
                    "departure_at": serialize_datetime(departure),
                    "arrival_airport": destination,
                    "arrival_at": serialize_datetime(arrival),
                    "price_regular_pln": regular_pln,
                    "resident_discount_eligible": True,
                    "resident_fare_multiplier": multiplier,
                    "price_resident_estimated_pln": round(regular_pln * multiplier, 2),
                    "resident_price_source": (
                        "estimated as configured percentage of Air Europa official "
                        "regular route-day fare"
                    ),
                    "booking_url": air_europa_booking_url(origin, destination, departure),
                    "price_source": "Air Europa official branded fare feed",
                    "price_scope": "lowest_official_route_day_fare",
                    "price_source_currency": currency,
                    "price_source_amount": amount,
                    "schedule_source": (
                        "Air Europa official booking results; verified timetable "
                        f"template {allowlist['verified_on']}"
                    ),
                })
        print(
            f"Air Europa: {origin}-{destination}: {len(fares)} dni z ceną",
            flush=True,
        )
        record_checked("Air Europa", origin, destination, min(days), max(days),
                       [leg for leg in legs if leg["departure_airport"] == origin and leg["arrival_airport"] == destination],
                       "official_route_day_fares")
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
            if leg["carrier"] == "Air Europa" and leg.get("price_source") != (
                "Air Europa official branded fare feed"
            ):
                raise RuntimeError(f"Niedozwolone źródło ceny w {result['id']}")


@collection_entrypoint("1d")
def main(args) -> None:
    if args.days < 0:
        raise SystemExit("--days must be non-negative")
    end = args.from_date + timedelta(days=args.days)
    allowlist = json.loads(TRANSFER_FILE.read_text(encoding="utf-8"))
    validate_allowlist(allowlist)
    validate_schedule_window(allowlist, args.from_date, end)
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
    config = allowlist["fare_feed"]
    client = AirEuropaFareClient(
        config["config_page"],
        config["tenant"],
        config["market"],
        config["language"],
    )
    air_europa = collect_air_europa_legs(route_days, allowlist, rates, client)
    if route_days and not air_europa:
        raise RuntimeError(
            "Oficjalny feed Air Europa nie zwrócił użytecznych cen; "
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
                "Air Europa official offer pages and their branded public fare feed; "
                "regular route-day fare, no Google Flights"
            ),
            "air_europa_resident_price": (
                "estimate: 25% of official regular route-day fare; taxes may not "
                "receive the full resident discount"
            ),
            "ryanair": "Ryanair full availability and active-dates APIs; no minimum-fare substitution",
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
