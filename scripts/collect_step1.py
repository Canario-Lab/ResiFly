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
import math
import os
from pathlib import Path
import sys
import threading
import time as time_module
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from curl_cffi import requests

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    # Later lazy imports of the shared direct-flight collector must reuse these
    # configured time zones instead of loading a second copy of this module.
    sys.modules.setdefault("scripts.collect_step1", sys.modules[__name__])

from scripts.collection_coverage import collection_entrypoint, publish_document, calendar_collector
from scripts.booking_urls import wizz_booking_url
from scripts.search_airports import ENDPOINT_TIMEZONES, POLISH_AIRPORTS, TENERIFE_AIRPORTS
from scripts.wizz_schedules import read_overrides, resolve_schedule
from scripts.wizz_api import wizz_api_base


ROOT = Path(__file__).resolve().parents[1]
TRANSFER_FILE = ROOT / "data" / "binter-transfer-airports.json"
DEFAULT_OUTPUT = ROOT / "data" / "step1-results.json"

MIN_LAYOVER_MINUTES = 120
MAX_LAYOVER_MINUTES = 24 * 60
BINTER_API = "https://services.bintercanarias.com/main/graphql"
NBP_CACHE_DIR = ROOT / "tmp" / "nbp-rates"
NBP_SHARED_CURRENCIES = ("EUR", "GBP", "HUF", "MAD", "RON", "USD")
NBP_LOOKBACK_DAYS = 7

AIRPORT_TIMEZONES = dict(ENDPOINT_TIMEZONES)
_ryanair_client_version = None
_ryanair_client_lock = threading.Lock()

def configure_airports_from_allowlist(allowlist: dict[str, Any]) -> None:
    """Register transfer-airport time zones stored in an allowlist file."""
    configured = dict(allowlist.get("airport_timezones", {}))
    for airport in allowlist.get("airports", []):
        if airport.get("timezone"):
            configured[airport["iata"]] = airport["timezone"]
    for code, timezone in configured.items():
        ZoneInfo(timezone)
        AIRPORT_TIMEZONES[code] = timezone


class WizzSchedules(dict):
    """Route schedules with optional verified departure-time number overrides."""

    def __init__(self):
        super().__init__()
        self.overrides = {}


def wizz_schedules_from_allowlist(
    allowlist: dict[str, Any],
) -> dict[tuple[str, str], tuple[str, int]]:
    """Read Wizz route identifiers and block times from the Step 1 list."""
    schedules = WizzSchedules()
    for route in allowlist.get("wizz_route_schedules", []):
        key = (route["origin"], route["destination"])
        if key in schedules:
            raise RuntimeError(f"Duplicate Wizz schedule in Step 1 list: {key}")
        duration = int(route["duration_minutes"])
        if duration <= 0:
            raise RuntimeError(f"Invalid Wizz duration in Step 1 list: {key}")
        schedules[key] = (route["flight_number"], duration)
    schedules.overrides = read_overrides(allowlist.get("flight_number_overrides_by_departure_time", []), schedules,
                                        allowlist.get("flight_number_overrides_by_departure_weekday_and_time", []),
                                        allowlist.get("flight_number_overrides_by_departure_date_and_time", []))
    return schedules

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
          token
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

BINTER_IMPORTS_QUERY = """
query booking_getImports(
  $itineraries: [Token!]!
  $passengers: [PassengersTypeInput!]!
) {
  booking_getImports(
    itineraries: $itineraries
    passengers: $passengers
  ) {
    passengerAmounts {
      fare { mainAmount totalAmount currency { code } }
      taxes { mainAmount totalAmount currency { code } }
      suplements { mainAmount totalAmount currency { code } }
      serviceFee { mainAmount totalAmount currency { code } }
      managementFee { mainAmount totalAmount currency { code } }
      mobilidadeDiscounts { mainAmount totalAmount currency { code } }
      passenger {
        typeCode
        residentCode
        isResident
        isSpanishResident
      }
    }
  }
}
"""

BINTER_FINAL_PRICE_COMPONENTS = (
    "fare",
    "taxes",
    "suplements",
    "serviceFee",
    "managementFee",
)


@dataclass(frozen=True)
class CurrencyRate:
    code: str
    pln: float


_nbp_rates_by_day: dict[str, dict[str, CurrencyRate]] = {}


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
    empty_market: bool = False,
) -> Any:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            from scripts.source_scheduler import http_request
            response = http_request(lambda address, **kw: requests.request(method, address, **kw),
                url,
                headers=headers,
                json=payload,
                params=params,
                impersonate=impersonate,
                timeout=60,
            )
            if empty_market and response.status_code == 400 and "InvalidMarket" in response.text:
                return {"outboundFlights": []}
            response.raise_for_status()
            return response.json()
        except Exception as error:  # network errors need a bounded retry
            from scripts.source_scheduler import raise_if_stopped
            raise_if_stopped()
            last_error = error
            if attempt + 1 < attempts:
                from scripts.source_scheduler import retry_delay
                time_module.sleep(retry_delay(attempt, error))
    raise RuntimeError(f"Request failed after {attempts} attempts: {url}") from last_error


def _nbp_cache_path(day: date) -> Path:
    return NBP_CACHE_DIR / f"{day.isoformat()}.json"


def _decode_nbp_cache(payload: Any, day: date) -> dict[str, CurrencyRate] | None:
    if not isinstance(payload, dict) or payload.get("requested_for") != day.isoformat():
        return None
    raw_rates = payload.get("rates")
    if not isinstance(raw_rates, dict):
        return None
    required = set(NBP_SHARED_CURRENCIES)
    if not required <= set(raw_rates):
        return None
    try:
        rates = {
            code: CurrencyRate(code, float(raw_rates[code]["pln"]))
            for code in NBP_SHARED_CURRENCIES
        }
    except (KeyError, TypeError, ValueError):
        return None
    rates["PLN"] = CurrencyRate("PLN", 1.0)
    return rates


def _read_nbp_cache(day: date) -> dict[str, CurrencyRate] | None:
    path = _nbp_cache_path(day)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return _decode_nbp_cache(payload, day)


def _fetch_nbp_rates(day: date) -> tuple[dict[str, CurrencyRate], dict[str, Any]]:
    start = day - timedelta(days=NBP_LOOKBACK_DAYS)
    newest: dict[str, tuple[str, str, float]] = {}
    errors: list[Exception] = []
    for table in ("a", "b"):
        url = (
            "https://api.nbp.pl/api/exchangerates/tables/"
            f"{table}/{start.isoformat()}/{day.isoformat()}/"
        )
        try:
            documents = get_json("GET", url, params={"format": "json"})
        except RuntimeError as error:
            errors.append(error)
            continue
        if not isinstance(documents, list):
            continue
        for document in documents:
            effective_date = str(document.get("effectiveDate") or "")
            if not effective_date or effective_date > day.isoformat():
                continue
            for item in document.get("rates") or []:
                code = str(item.get("code") or "").upper()
                if code not in NBP_SHARED_CURRENCIES:
                    continue
                try:
                    value = float(item["mid"])
                except (KeyError, TypeError, ValueError):
                    continue
                previous = newest.get(code)
                if previous is None or effective_date > previous[0]:
                    newest[code] = (effective_date, table.upper(), value)

    missing = sorted(set(NBP_SHARED_CURRENCIES) - set(newest))
    if missing:
        detail = f"; błędy tabel: {len(errors)}" if errors else ""
        raise RuntimeError(
            "NBP nie zwrócił kompletnego dziennego zestawu kursów: "
            f"{', '.join(missing)}{detail}"
        )

    rates = {
        code: CurrencyRate(code, newest[code][2])
        for code in NBP_SHARED_CURRENCIES
    }
    rates["PLN"] = CurrencyRate("PLN", 1.0)
    payload = {
        "requested_for": day.isoformat(),
        "rates": {
            code: {
                "pln": newest[code][2],
                "effective_date": newest[code][0],
                "table": newest[code][1],
            }
            for code in NBP_SHARED_CURRENCIES
        },
    }
    return rates, payload


def _write_nbp_cache(day: date, payload: dict[str, Any]) -> None:
    path = _nbp_cache_path(day)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def nbp_rates(day: date) -> dict[str, CurrencyRate]:
    """Return one shared, complete NBP snapshot for a collection date."""
    key = day.isoformat()
    if os.environ.get("RESIFLY_SOURCE_MODE") == "read":
        from scripts.source_repository import reader
        snapshot = reader().identity
        if snapshot["period_from"] != key:
            raise RuntimeError("Wrong collection date for the frozen NBP snapshot")
        return {code: CurrencyRate(code, float(value)) for code, value in snapshot["nbp_rates"].items()}
    cached = _nbp_rates_by_day.get(key)
    if cached is not None:
        return dict(cached)
    cached = _read_nbp_cache(day)
    if cached is None:
        if os.environ.get("RESIFLY_SOURCE_MODE") == "read":
            raise RuntimeError("Missing NBP snapshot during cache-only feed building")
        cached, payload = _fetch_nbp_rates(day)
        _write_nbp_cache(day, payload)
    _nbp_rates_by_day[key] = cached
    return dict(cached)


def nbp_rate(currency_code: str, day: date) -> CurrencyRate:
    code = currency_code.upper()
    try:
        return nbp_rates(day)[code]
    except KeyError as error:
        raise RuntimeError(f"Nieobsługiwana waluta NBP: {code}") from error


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
        f"{wizz_api_base()}/search/timetableV2",
        headers={"content-type": "application/json"},
        payload=payload,
        impersonate="safari184",
        empty_market=True,
    )
    if not isinstance(response, dict) or not isinstance(response.get("outboundFlights"), list):
        raise RuntimeError(f"Invalid Wizz timetable response {origin}-{destination}")
    return [
        item
        for item in response.get("outboundFlights", [])
        if item.get("departureStation") == origin
        and item.get("arrivalStation") == destination
        and item.get("priceType") == "price"
        and float(item.get("price", {}).get("amount") or 0) > 0
    ]


@calendar_collector("Wizz Air", "timetableV2")
def collect_wizz_route(
    origin: str,
    destination: str,
    start: date,
    end: date,
    rates: dict[str, CurrencyRate],
    schedules: dict[tuple[str, str], tuple[str, int]],
) -> list[dict[str, Any]]:
    regular = wizz_timetable(origin, destination, start, end, "regular")
    if not regular:
        return []
    schedule = schedules.get((origin, destination))
    if schedule is None:
        raise RuntimeError(f"Active Wizz route {origin}-{destination} needs verified local schedule metadata")
    club = wizz_timetable(origin, destination, start, end, "wdc")
    club_by_departure = {item["departureDate"]: item for item in club}
    legs: list[dict[str, Any]] = []
    for item in regular:
        departure = local_datetime(item["departureDate"], origin)
        number, duration = resolve_schedule(schedules, getattr(schedules, "overrides", {}), origin, destination, departure)
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
        legs.append({
            "carrier": "Wizz Air",
            "flight_number": number,
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
    """Use full availability calendars, not the cheapest fare for 31 days.

    The import is deliberately lazy: Step 2 imports the shared date/currency
    helpers from this module. It is safe after module initialization.
    """
    from scripts.collect_step2 import collect_ryanair_route as collect_full_route
    from scripts.collect_step2 import ryanair_client_version

    global _ryanair_client_version
    with _ryanair_client_lock:
        if _ryanair_client_version is None:
            _ryanair_client_version = ryanair_client_version()
    return collect_full_route(origin, destination, start, end, rates, _ryanair_client_version)


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


def _binter_eur_fare_choices(
    fares: list[dict[str, Any]],
) -> list[tuple[float, float, dict[str, Any]]]:
    choices: list[tuple[float, float, dict[str, Any]]] = []
    for fare in fares:
        if not isinstance(fare, dict):
            raise RuntimeError("Malformed Binter fare")
        if fare.get("seats") == 0:
            continue
        amounts = fare.get("amounts") or {}
        regular = amounts.get("noResident") or {}
        resident = amounts.get("resident") or {}
        # Binter returns loyalty-point awards alongside cash fares. These
        # are intentionally outside our EUR cash-price search, not errors.
        if regular.get("currency", {}).get("code") == resident.get("currency", {}).get("code") == "PTS":
            continue
        if regular.get("currency", {}).get("code") != "EUR":
            raise RuntimeError("Binter fare missing regular EUR price")
        if resident.get("currency", {}).get("code") != "EUR":
            raise RuntimeError("Binter fare missing resident EUR price")
        prices = (float(regular["totalAmount"]), float(resident["totalAmount"]))
        if not all(math.isfinite(amount) and amount > 0 for amount in prices):
            raise RuntimeError("Invalid Binter fare amount")
        choices.append((prices[0], prices[1], fare))
    return choices


def lowest_eur_fare(fares: list[dict[str, Any]]) -> tuple[float, float] | None:
    choices = _binter_eur_fare_choices(fares)
    if not choices:
        return None
    regular, resident, _ = min(choices, key=lambda choice: choice[0])
    return regular, resident


def lowest_eur_fare_with_token(
    fares: list[dict[str, Any]],
) -> tuple[float, float, str] | None:
    choices = _binter_eur_fare_choices(fares)
    if not choices:
        return None
    regular, resident, fare = min(choices, key=lambda choice: choice[0])
    token = fare.get("token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Binter cash fare missing import token")
    return regular, resident, token


def _binter_import_amount(
    raw: Any,
    component: str,
    context: str,
) -> tuple[float, float]:
    if not isinstance(raw, dict):
        raise RuntimeError(
            f"{context}: missing {component} amount in booking_getImports; "
            "publication blocked"
        )
    if (raw.get("currency") or {}).get("code") != "EUR":
        raise RuntimeError(
            f"{context}: {component} is not an EUR amount in booking_getImports; "
            "publication blocked"
        )
    try:
        regular = float(raw["mainAmount"])
        resident = float(raw["totalAmount"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError(
            f"{context}: malformed {component} amount in booking_getImports; "
            "publication blocked"
        ) from error
    if not all(math.isfinite(amount) and amount >= 0 for amount in (regular, resident)):
        raise RuntimeError(
            f"{context}: invalid {component} amount in booking_getImports; "
            "publication blocked"
        )
    return regular, resident


def validate_binter_imports_response(
    response: Any,
    context: str,
    resident_discount_eligible: bool,
) -> tuple[float, float]:
    if not isinstance(response, dict) or response.get("errors"):
        raise RuntimeError(
            f"{context}: booking_getImports GraphQL error or invalid response; "
            "publication blocked"
        )
    data = response.get("data")
    imports = data.get("booking_getImports") if isinstance(data, dict) else None
    passenger_amounts = (
        imports.get("passengerAmounts") if isinstance(imports, dict) else None
    )
    if not isinstance(passenger_amounts, list) or len(passenger_amounts) != 1:
        raise RuntimeError(
            f"{context}: missing one-passenger booking_getImports totals; "
            "publication blocked"
        )
    amounts = passenger_amounts[0]
    if not isinstance(amounts, dict):
        raise RuntimeError(
            f"{context}: malformed booking_getImports totals; publication blocked"
        )
    passenger = amounts.get("passenger")
    if not isinstance(passenger, dict) or passenger.get("typeCode") != "ADT":
        raise RuntimeError(
            f"{context}: booking_getImports did not price one adult; "
            "publication blocked"
        )
    if resident_discount_eligible and not (
        passenger.get("residentCode") == "RC"
        or passenger.get("isSpanishResident") is True
    ):
        raise RuntimeError(
            f"{context}: booking_getImports did not apply Spanish resident status; "
            "publication blocked"
        )

    regular_total = 0.0
    resident_total = 0.0
    for component in BINTER_FINAL_PRICE_COMPONENTS:
        regular, resident = _binter_import_amount(
            amounts.get(component), component, context
        )
        regular_total += regular
        resident_total += resident

    mobility = amounts.get("mobilidadeDiscounts")
    if isinstance(mobility, dict):
        mobility_regular, mobility_resident = _binter_import_amount(
            mobility, "mobilidadeDiscounts", context
        )
        if mobility_regular != 0 or mobility_resident != 0:
            raise RuntimeError(
                f"{context}: unsupported non-zero mobility discount; "
                "publication blocked"
            )
    elif mobility not in (None, []):
        raise RuntimeError(
            f"{context}: malformed mobility discount; publication blocked"
        )

    regular_total = round(regular_total, 2)
    resident_total = round(resident_total, 2)
    if regular_total <= 0 or resident_total <= 0:
        raise RuntimeError(
            f"{context}: invalid final booking_getImports total; publication blocked"
        )
    if resident_discount_eligible and resident_total > regular_total:
        raise RuntimeError(
            f"{context}: resident total exceeds regular total; publication blocked"
        )
    return regular_total, resident_total


def fetch_binter_final_prices(
    fare_token: str,
    context: str,
    resident_discount_eligible: bool,
) -> tuple[float, float]:
    passengers = [{
        "type": {
            "code": "ADT",
            "discounts": ["RC"] if resident_discount_eligible else [],
        },
        "quantity": 1,
    }]
    try:
        response = get_json(
            "POST",
            BINTER_API,
            headers=binter_headers(),
            payload={
                "query": BINTER_IMPORTS_QUERY,
                "variables": {
                    "itineraries": [{"token": fare_token}],
                    "passengers": passengers,
                },
                "operationName": "booking_getImports",
            },
            impersonate="safari184",
        )
    except RuntimeError as error:
        raise RuntimeError(
            f"{context}: booking_getImports request failed; publication blocked"
        ) from error
    return validate_binter_imports_response(
        response,
        context,
        resident_discount_eligible,
    )


@calendar_collector("Binter", "booking_search")
def collect_binter_trip(
    origin: str,
    destination: str,
    departure_date: date,
    rates: dict[str, CurrencyRate],
    resident_discount_eligible: bool,
    resident_fare_multiplier: float,
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
    except RuntimeError as error:
        raise RuntimeError(
            f"Binter {origin}-{destination} on {departure_date}: request failed; publication blocked"
        ) from error
    search = validate_binter_response(response, origin, destination, departure_date)
    legs: list[dict[str, Any]] = []
    for availability in search.get("availability") or []:
        for flight in availability["flights"]:
            if not isinstance(flight, dict) or not isinstance(flight.get("flightSegments"), list) or not isinstance(flight.get("fares"), list):
                raise RuntimeError(f"Malformed Binter flight {origin}-{destination} on {departure_date}")
            segments = flight["flightSegments"]
            if len(segments) != 1:
                continue
            segment = segments[0]
            segment_origin = segment.get("origin", {}).get("iata")
            segment_destination = segment.get("destination", {}).get("iata")
            if segment_origin != origin or segment_destination != destination:
                continue
            fare = lowest_eur_fare_with_token(flight.get("fares") or [])
            if fare is None:
                continue
            preview_regular_eur, preview_resident_eur, fare_token = fare
            context = (
                f"Binter {origin}-{destination} on {departure_date} "
                f"flight {segment.get('line') or 'NT'}{segment.get('flightNumber')}"
            )
            regular_eur, resident_eur = fetch_binter_final_prices(
                fare_token,
                context,
                resident_discount_eligible,
            )
            if regular_eur < preview_regular_eur or (
                resident_discount_eligible and resident_eur < preview_resident_eur
            ):
                raise RuntimeError(
                    f"{context}: final booking total is lower than its fare; "
                    "publication blocked"
                )
            effective_resident_eur = (
                resident_eur if resident_discount_eligible else regular_eur
            )
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
                "resident_discount_eligible": resident_discount_eligible,
                "resident_fare_multiplier": resident_fare_multiplier,
                "price_resident_estimated_pln": money_pln(
                    effective_resident_eur,
                    "EUR",
                    rates,
                ),
                "resident_price_is_estimate": False,
                "resident_price_source": (
                    "Binter official booking_getImports final total"
                ),
                "booking_url": "https://www.bintercanarias.com/es/buscar-vuelos",
                "price_source": (
                    "Binter official booking_search + booking_getImports GraphQL"
                ),
                "price_scope": "official_final_payable_total_with_taxes_and_fees",
                "price_source_currency": "EUR",
                "price_source_amount": regular_eur,
                "price_source_resident_amount": effective_resident_eur,
            })
    return legs


def validate_binter_response(response, origin, destination, departure_date):
    context = f"Binter {origin}-{destination} on {departure_date}"
    if not isinstance(response, dict) or response.get("errors"):
        raise RuntimeError(f"{context}: GraphQL error or invalid response; publication blocked")
    data = response.get("data")
    search = data.get("booking_search") if isinstance(data, dict) else None
    if not isinstance(search, dict) or not isinstance(search.get("availability"), list):
        raise RuntimeError(f"{context}: missing availability; publication blocked")
    messages = search.get("messages", [])
    if not isinstance(messages, list) or any(
        not isinstance(message, dict) or any(word in str(message.get("type", "")).upper() for word in ("ERROR", "FATAL"))
        for message in messages
    ):
        raise RuntimeError(f"{context}: booking_search error; publication blocked")
    for item in search["availability"]:
        if not isinstance(item, dict) or not isinstance(item.get("flights"), list):
            raise RuntimeError(f"{context}: malformed availability; publication blocked")
        trip = item.get("trip")
        if not isinstance(trip, dict) or trip.get("origin", {}).get("iata") != origin or trip.get("destination", {}).get("iata") != destination or str(trip.get("date", ""))[:10] != departure_date.isoformat():
            raise RuntimeError(f"{context}: mismatched availability route/date; publication blocked")
    return search


def collect_low_cost_legs(
    transfers: list[str],
    start: date,
    end: date,
    rates: dict[str, CurrencyRate],
    workers: int,
    wizz_schedules: dict[tuple[str, str], tuple[str, int]],
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
            if carrier == "Wizz Air":
                future = pool.submit(
                    collect_wizz_route,
                    origin,
                    destination,
                    start,
                    end,
                    rates,
                    wizz_schedules,
                )
            else:
                future = pool.submit(
                    collect_ryanair_route,
                    origin,
                    destination,
                    start,
                    end,
                    rates,
                )
            futures[future] = (carrier, origin, destination)
        for future in as_completed(futures):
            carrier, origin, destination = futures[future]
            route_legs = future.result()
            if route_legs:
                print(f"{carrier}: {origin}-{destination}: {len(route_legs)}", flush=True)
                legs.extend(route_legs)
    return legs


def binter_route_days(
    allowlist: dict[str, Any],
    start: date,
    end: date,
) -> set[tuple[str, str, date]]:
    route_days: set[tuple[str, str, date]] = set()
    tenerife_airports = allowlist["scope"]["tenerife_airports"]
    for airport in allowlist["airports"]:
        transfer = airport["iata"]
        for tenerife in tenerife_airports:
            for day in date_range(start, end):
                route_days.add((transfer, tenerife, day))
                route_days.add((tenerife, transfer, day))
    return route_days


def collect_binter_legs(
    route_days: set[tuple[str, str, date]],
    rates: dict[str, CurrencyRate],
    workers: int,
    transfer_rules: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    legs: list[dict[str, Any]] = []
    ordered = sorted(route_days, key=lambda item: (item[2], item[0], item[1]))
    with ThreadPoolExecutor(max_workers=max(2, min(workers, 6))) as pool:
        futures = {}
        for origin, destination, day in ordered:
            transfer = destination if origin in TENERIFE_AIRPORTS else origin
            eligible = bool(
                transfer_rules[transfer][
                    "resident_discount_eligible_on_binter_leg"
                ]
            )
            multiplier = float(
                transfer_rules[transfer]["binter_resident_fare_multiplier"]
            )
            if eligible != (multiplier < 1.0):
                raise RuntimeError(
                    f"Inconsistent Binter discount metadata for {transfer}"
                )
            future = pool.submit(
                collect_binter_trip,
                origin,
                destination,
                day,
                rates,
                eligible,
                multiplier,
            )
            futures[future] = (origin, destination, day)
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


@collection_entrypoint("1")
def main(args) -> None:
    if args.days < 0:
        raise SystemExit("--days must be non-negative")
    end = args.from_date + timedelta(days=args.days)
    allowlist = json.loads(TRANSFER_FILE.read_text(encoding="utf-8"))
    configure_airports_from_allowlist(allowlist)
    transfers = [airport["iata"] for airport in allowlist["airports"]]
    transfer_rules = {
        airport["iata"]: airport for airport in allowlist["airports"]
    }
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
    print(f"Odcinki Ryanair/Wizz Air: {len(low_cost_legs)}", flush=True)
    route_days = binter_route_days(allowlist, args.from_date, end)
    print(
        f"Pełny kalendarz Binter do sprawdzenia: {len(route_days)} tras/dni",
        flush=True,
    )
    binter_legs = collect_binter_legs(
        route_days,
        rates,
        args.workers,
        transfer_rules,
    )
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
            "binter": "Binter booking_search + booking_getImports GraphQL final totals",
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
    print(f"Zapisano {len(results)} połączeń do {args.output}", flush=True)
    print(json.dumps(counts, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
