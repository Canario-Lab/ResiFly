#!/usr/bin/env python3
"""Build Step 1F: Canaryfly + Ryanair or Wizz Air.

The fixed allowlist defines eligible transfer airports and Polish routes.
Canaryfly dates, schedules, flight numbers, regular fares and resident fares
come directly from its official public GraphQL service. The complete monthly
calendar for every saved route is fetched before any connection matching.
Price filtering is left to the website.
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

from scripts.collection_coverage import collection_entrypoint, publish_document, record_checked
from scripts.booking_urls import canaryfly_booking_url
from scripts.collect_step1 import (
    MAX_LAYOVER_MINUTES,
    MIN_LAYOVER_MINUTES,
    POLISH_AIRPORTS,
    TENERIFE_AIRPORTS,
    CurrencyRate,
    configure_airports_from_allowlist,
    dt,
    get_json,
    local_datetime,
    money_pln,
    nbp_eur_rate,
    serialize_datetime,
)
from scripts.collect_step1c import collect_low_cost_legs


ROOT = Path(__file__).resolve().parents[1]
TRANSFER_FILE = ROOT / "data" / "canaryfly-transfer-airports.json"
DEFAULT_OUTPUT = ROOT / "data" / "step1f-results.json"

CANARYFLY_CALENDAR_QUERY = """
query booking_calendar($search: BookingSearchInput!, $calendarRange: String!) {
  booking_calendar(search: $search, calendarRange: $calendarRange) {
    trip { origin { iata name } destination { iata name } date }
    days {
      date
      enabled
      bestPrice
      fare
      fareAmounts { resident noResident }
      taxAmount
      currency { code }
    }
  }
}
"""

CANARYFLY_SEARCH_QUERY = """
query booking_search($search: BookingSearchInput!) {
  booking_search(search: $search) {
    availability {
      trip { origin { iata name } destination { iata name } date }
      flights {
        flightSegments {
          line
          flightNumber
          origin { iata name }
          destination { iata name }
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
    parser.add_argument("--workers", type=int, default=6)
    return parser.parse_args()


def validate_allowlist(allowlist: dict[str, Any]) -> None:
    if allowlist.get("usage_policy", {}).get("step") != "1F":
        raise RuntimeError("Lista Canaryfly nie jest oznaczona jako krok 1F")
    config = allowlist.get("fare_feed") or {}
    if config.get("endpoint") != "https://services.canaryfly.es/graphql/main":
        raise RuntimeError("Nieprawidłowy oficjalny endpoint Canaryfly")
    if config.get("calendar_range") != "MONTHLY":
        raise RuntimeError("Krok 1F musi pobierać pełne kalendarze miesięczne")
    if config.get("currency") != "EUR" or config.get("airline_code") != "PM":
        raise RuntimeError("Nieprawidłowa konfiguracja taryf Canaryfly")
    airports = allowlist.get("airports") or []
    if not airports:
        raise RuntimeError("Lista lotnisk Canaryfly jest pusta")
    for airport in airports:
        code = airport["iata"]
        ZoneInfo(airport["timezone"])
        if not airport.get("resident_discount_eligible_on_canaryfly_leg"):
            raise RuntimeError(f"Krok 1F nie może zawierać trasy bez zniżki: {code}")
        if float(airport.get("canaryfly_resident_fare_multiplier", 0)) != 0.25:
            raise RuntimeError(f"Nieprawidłowy mnożnik Canaryfly dla {code}")
        tenerife_airports = airport.get("tenerife_airports") or []
        if not tenerife_airports or not set(tenerife_airports) <= set(
            TENERIFE_AIRPORTS
        ):
            raise RuntimeError(f"Nieprawidłowa lista lotnisk Teneryfy dla {code}")
        polish_routes = airport.get("polish_routes") or []
        if not polish_routes:
            raise RuntimeError(f"Brak tras do Polski dla {code}")
        for route in polish_routes:
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


def canaryfly_routes(
    allowlist: dict[str, Any],
) -> list[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for transfer in allowlist["airports"]:
        for tenerife in transfer["tenerife_airports"]:
            routes.add((tenerife, transfer["iata"]))
            routes.add((transfer["iata"], tenerife))
    return sorted(routes)


def calendar_month_anchors(start: date, end: date) -> list[date]:
    """Return one safe query date in each calendar month of the window."""

    anchors: list[date] = []
    cursor = date(start.year, start.month, 1)
    final = date(end.year, end.month, 1)
    while cursor <= final:
        anchors.append(start if cursor.year == start.year and cursor.month == start.month else cursor)
        cursor = (
            date(cursor.year + 1, 1, 1)
            if cursor.month == 12
            else date(cursor.year, cursor.month + 1, 1)
        )
    return anchors


def booking_search_input(origin: str, destination: str, day: date) -> dict[str, Any]:
    return {
        "trips": [{
            "origin": origin,
            "destination": destination,
            "date": day.isoformat(),
        }],
        "passengers": [{"type": {"code": "ADT", "discounts": []}, "quantity": 1}],
        "flags": [],
    }


class CanaryflyClient:
    """Read-only client for Canaryfly's official public GraphQL service."""

    def __init__(self, endpoint: str, calendar_range: str = "MONTHLY"):
        self.endpoint = endpoint
        self.calendar_range = calendar_range

    @staticmethod
    def headers() -> dict[str, str]:
        return {
            "accept": "application/json",
            "content-type": "application/json",
            "origin": "https://www.canaryfly.es",
            "referer": "https://www.canaryfly.es/",
        }

    def _post(
        self,
        query: str,
        operation: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        payload = get_json(
            "POST",
            self.endpoint,
            headers=self.headers(),
            payload={
                "query": query,
                "variables": variables,
                "operationName": operation,
            },
            impersonate="chrome",
        )
        if not isinstance(payload, dict) or payload.get("errors"):
            raise RuntimeError(
                f"Oficjalny endpoint Canaryfly odrzucił {operation}: "
                f"{payload.get('errors') if isinstance(payload, dict) else payload!r}"
            )
        return payload

    def calendar(
        self,
        origin: str,
        destination: str,
        anchor: date,
    ) -> dict[str, Any]:
        return self._post(
            CANARYFLY_CALENDAR_QUERY,
            "booking_calendar",
            {
                "search": booking_search_input(origin, destination, anchor),
                "calendarRange": self.calendar_range,
            },
        )

    def search(
        self,
        origin: str,
        destination: str,
        day: date,
    ) -> dict[str, Any]:
        return self._post(
            CANARYFLY_SEARCH_QUERY,
            "booking_search",
            {"search": booking_search_input(origin, destination, day)},
        )


def available_days_from_calendar(
    payload: dict[str, Any],
    origin: str,
    destination: str,
    start: date,
    end: date,
) -> set[date]:
    ranges = (payload.get("data") or {}).get("booking_calendar")
    if not isinstance(ranges, list) or not ranges:
        raise RuntimeError(
            f"Canaryfly nie zwrócił kalendarza {origin}-{destination}"
        )
    found_matching_range = False
    available: set[date] = set()
    for calendar_range in ranges:
        trip = calendar_range.get("trip") or {}
        if trip.get("origin", {}).get("iata") != origin:
            continue
        if trip.get("destination", {}).get("iata") != destination:
            continue
        found_matching_range = True
        for item in calendar_range.get("days") or []:
            try:
                day = date.fromisoformat(str(item["date"])[:10])
            except (KeyError, TypeError, ValueError):
                continue
            if start <= day <= end and item.get("enabled") is True:
                available.add(day)
    if not found_matching_range:
        raise RuntimeError(
            f"Kalendarz Canaryfly nie zawiera żądanej trasy {origin}-{destination}"
        )
    return available


def collect_canaryfly_available_days(
    allowlist: dict[str, Any],
    start: date,
    end: date,
    workers: int,
    client: CanaryflyClient | None = None,
) -> set[tuple[str, str, date]]:
    config = allowlist["fare_feed"]
    fare_client = client or CanaryflyClient(
        config["endpoint"], config["calendar_range"]
    )
    jobs = [
        (origin, destination, anchor)
        for origin, destination in canaryfly_routes(allowlist)
        for anchor in calendar_month_anchors(start, end)
    ]
    available: set[tuple[str, str, date]] = set()

    def fetch(job: tuple[str, str, date]) -> tuple[str, str, set[date]]:
        origin, destination, anchor = job
        payload = fare_client.calendar(origin, destination, anchor)
        days = available_days_from_calendar(
            payload, origin, destination, start, end
        )
        month_end = (anchor.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        record_checked("Canaryfly", origin, destination, max(start, anchor), min(end, month_end),
                       [{"departure_at": day.isoformat()} for day in days if anchor <= day <= month_end],
                       "booking_calendar")
        return origin, destination, days

    with ThreadPoolExecutor(max_workers=min(max(workers, 1), 4)) as pool:
        futures = {pool.submit(fetch, job): job for job in jobs}
        for index, future in enumerate(as_completed(futures), start=1):
            origin, destination, days = future.result()
            available.update((origin, destination, day) for day in days)
            if index % 4 == 0 or index == len(futures):
                print(
                    f"Canaryfly: {index}/{len(futures)} pełnych kalendarzy miesięcznych",
                    flush=True,
                )
    return available


def lowest_canaryfly_fare(
    fares: Iterable[dict[str, Any]],
    currency: str,
) -> tuple[float, float, dict[str, Any]] | None:
    choices: list[tuple[float, float, dict[str, Any]]] = []
    for fare in fares:
        if fare.get("seats") == 0:
            continue
        amounts = fare.get("amounts") or {}
        regular = amounts.get("noResident") or {}
        resident = amounts.get("resident") or {}
        if regular.get("currency", {}).get("code") != currency:
            continue
        if resident.get("currency", {}).get("code") != currency:
            continue
        try:
            regular_amount = float(regular["totalAmount"])
            resident_amount = float(resident["totalAmount"])
        except (KeyError, TypeError, ValueError):
            continue
        if regular_amount <= 0 or resident_amount <= 0:
            continue
        if resident_amount > regular_amount:
            continue
        choices.append((regular_amount, resident_amount, fare))
    return min(choices, key=lambda item: item[0]) if choices else None


def parse_canaryfly_search(
    payload: dict[str, Any],
    origin: str,
    destination: str,
    day: date,
    multiplier: float,
    rates: dict[str, CurrencyRate],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    search = (payload.get("data") or {}).get("booking_search")
    if not isinstance(search, dict):
        raise RuntimeError(
            f"Canaryfly nie zwrócił wyników wyszukiwania {origin}-{destination} {day}"
        )
    currency = str(config["currency"]).upper()
    airline_code = str(config["airline_code"]).upper()
    best: dict[tuple[str, str, str], dict[str, Any]] = {}
    for availability in search.get("availability") or []:
        for flight in availability.get("flights") or []:
            segments = flight.get("flightSegments") or []
            if len(segments) != 1:
                continue
            segment = segments[0]
            if segment.get("origin", {}).get("iata") != origin:
                continue
            if segment.get("destination", {}).get("iata") != destination:
                continue
            if str(segment.get("departureTime", ""))[:10] != day.isoformat():
                continue
            selected = lowest_canaryfly_fare(flight.get("fares") or [], currency)
            if selected is None:
                continue
            regular_amount, resident_amount, fare = selected
            try:
                departure = local_datetime(segment["departureTime"], origin)
                arrival = local_datetime(segment["arrivalTime"], destination)
                number = int(segment["flightNumber"])
            except (KeyError, TypeError, ValueError):
                continue
            if arrival <= departure:
                continue
            line = str(segment.get("line") or airline_code).upper()
            if line != airline_code:
                continue
            regular_pln = money_pln(regular_amount, currency, rates)
            resident_pln = money_pln(resident_amount, currency, rates)
            leg = {
                "carrier": "Canaryfly",
                "flight_number": f"{line}{number}",
                "departure_airport": origin,
                "departure_at": serialize_datetime(departure),
                "arrival_airport": destination,
                "arrival_at": serialize_datetime(arrival),
                "price_regular_pln": regular_pln,
                "resident_discount_eligible": True,
                "resident_fare_multiplier": multiplier,
                "price_resident_estimated_pln": resident_pln,
                "resident_price_is_estimate": False,
                "resident_price_source": (
                    "Canaryfly official booking_search resident total"
                ),
                "booking_url": canaryfly_booking_url(
                    origin, destination, departure
                ),
                "price_source": "Canaryfly official booking_search GraphQL",
                "price_scope": "official_flight_specific_lowest_available_fare",
                "price_source_currency": currency,
                "price_source_amount": regular_amount,
                "price_source_resident_amount": resident_amount,
                "fare_code": fare.get("code"),
                "schedule_source": "Canaryfly official booking_search GraphQL",
            }
            key = (leg["flight_number"], leg["departure_at"], leg["arrival_at"])
            previous = best.get(key)
            if previous is None or regular_pln < previous["price_regular_pln"]:
                best[key] = leg
    return sorted(best.values(), key=lambda leg: leg["departure_at"])


def collect_canaryfly_legs(
    candidates: set[tuple[str, str, date]],
    allowlist: dict[str, Any],
    rates: dict[str, CurrencyRate],
    workers: int,
    client: CanaryflyClient | None = None,
) -> list[dict[str, Any]]:
    if not candidates:
        return []
    config = allowlist["fare_feed"]
    rules = {airport["iata"]: airport for airport in allowlist["airports"]}
    fare_client = client or CanaryflyClient(
        config["endpoint"], config["calendar_range"]
    )
    ordered = sorted(candidates, key=lambda item: (item[2], item[0], item[1]))

    def fetch(candidate: tuple[str, str, date]) -> list[dict[str, Any]]:
        origin, destination, day = candidate
        transfer = destination if origin in TENERIFE_AIRPORTS else origin
        multiplier = float(rules[transfer]["canaryfly_resident_fare_multiplier"])
        result = parse_canaryfly_search(
            fare_client.search(origin, destination, day),
            origin,
            destination,
            day,
            multiplier,
            rates,
            config,
        )
        record_checked("Canaryfly", origin, destination, day, day, result, "booking_search", "details")
        return result

    legs: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(max(workers, 1), 4)) as pool:
        futures = {pool.submit(fetch, item): item for item in ordered}
        for index, future in enumerate(as_completed(futures), start=1):
            legs.extend(future.result())
            if index % 10 == 0 or index == len(futures):
                print(
                    f"Canaryfly: {index}/{len(futures)} dostępnych tras/dni",
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
    return f"step1f-{hashlib.sha256(value.encode()).hexdigest()[:16]}"


def build_connections(
    low_cost_legs: list[dict[str, Any]],
    canaryfly_legs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for low_cost in low_cost_legs:
        poland_to_tenerife = low_cost["departure_airport"] in POLISH_AIRPORTS
        for canaryfly in canaryfly_legs:
            if poland_to_tenerife:
                if canaryfly["departure_airport"] != low_cost["arrival_airport"]:
                    continue
                if canaryfly["arrival_airport"] not in TENERIFE_AIRPORTS:
                    continue
                layover = round(
                    (
                        dt(canaryfly["departure_at"])
                        - dt(low_cost["arrival_at"])
                    ).total_seconds()
                    / 60
                )
                legs = [low_cost, canaryfly]
            else:
                if canaryfly["arrival_airport"] != low_cost["departure_airport"]:
                    continue
                if canaryfly["departure_airport"] not in TENERIFE_AIRPORTS:
                    continue
                layover = round(
                    (
                        dt(low_cost["departure_at"])
                        - dt(canaryfly["arrival_at"])
                    ).total_seconds()
                    / 60
                )
                legs = [canaryfly, low_cost]
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


def validate_document(document: dict[str, Any]) -> None:
    for result in document["results"]:
        if len(result["legs"]) != 2:
            raise RuntimeError(f"Połączenie 1F musi mieć dwa odcinki: {result['id']}")
        carriers = {leg["carrier"] for leg in result["legs"]}
        if "Canaryfly" not in carriers or not carriers & {"Ryanair", "Wizz Air"}:
            raise RuntimeError(f"Nieprawidłowi przewoźnicy w {result['id']}")
        for leg in result["legs"]:
            if not leg.get("booking_url"):
                raise RuntimeError(f"Brak booking_url w {result['id']}")
            if leg["carrier"] == "Canaryfly":
                if leg.get("price_source") != (
                    "Canaryfly official booking_search GraphQL"
                ):
                    raise RuntimeError(f"Niedozwolone źródło ceny w {result['id']}")
                if leg.get("resident_price_is_estimate") is not False:
                    raise RuntimeError(
                        f"Cena rezydencka Canaryfly musi pochodzić z API: {result['id']}"
                    )


@collection_entrypoint("1f")
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
    low_cost = collect_low_cost_legs(
        allowlist, args.from_date, end, rates, args.workers
    )
    if not low_cost:
        raise RuntimeError(
            "Nie pobrano żadnego odcinka Wizz/Ryanair; wynik 1F nie zostanie nadpisany"
        )
    print(f"Odcinki Ryanair/Wizz Air: {len(low_cost)}", flush=True)

    available_days = collect_canaryfly_available_days(
        allowlist, args.from_date, end, args.workers
    )
    print(
        f"Dostępne trasy/dni Canaryfly po pełnym skanie: {len(available_days)}",
        flush=True,
    )
    canaryfly = collect_canaryfly_legs(
        available_days, allowlist, rates, args.workers
    )
    if available_days and not canaryfly:
        raise RuntimeError(
            "Canaryfly nie zwrócił szczegółów żadnego dostępnego dnia; "
            "wynik 1F nie zostanie nadpisany"
        )
    print(f"Odcinki Canaryfly: {len(canaryfly)}", flush=True)
    results = build_connections(low_cost, canaryfly)

    generated_at = datetime.now(ZoneInfo("Atlantic/Canary")).isoformat(
        timespec="seconds"
    )
    document = {
        "schema_version": 2,
        "generated_at": generated_at,
        "period_from": args.from_date.isoformat(),
        "period_to": end.isoformat(),
        "step": "1F",
        "directions": ["tenerife_to_poland", "poland_to_tenerife"],
        "transfer_airports": [
            airport["iata"] for airport in allowlist["airports"]
        ],
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
            "canaryfly": (
                "Canaryfly official booking_calendar and booking_search GraphQL; "
                "full monthly calendars plus flight-specific regular and resident fares"
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
