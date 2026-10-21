#!/usr/bin/env python3
"""Build Step 1B: Iberia/Iberia Express + Ryanair or Wizz Air.

The collector reads a fixed transfer-airport allowlist, checks both travel
directions and keeps every valid 2–24 hour self-transfer. Price filtering is
left to the website. Iberia's short-lived anonymous access token is discovered
from the current public web application, used only in memory and never written
to a result file.
"""

from __future__ import annotations

import argparse
import copy
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import sys
import time as time_module
from typing import Any, Iterable
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from curl_cffi import requests

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
    candidate_binter_trips,
    collect_low_cost_legs,
    configure_airports_from_allowlist,
    dt,
    local_datetime,
    money_pln,
    nbp_eur_rate,
    serialize_datetime,
    wizz_schedules_from_allowlist,
)


ROOT = Path(__file__).resolve().parents[1]
TRANSFER_FILE = ROOT / "data" / "iberia-transfer-airports.json"
DEFAULT_OUTPUT = ROOT / "data" / "step1b-results.json"

IBERIA_WEB_ENTRY = "https://www.iberia.com/flights/"
ENV_SCRIPT_PATTERN = re.compile(r"(?:src=[\"']|\b)(env-[\w.-]+\.js)")
ENV_VALUE_PATTERN = re.compile(
    r"window\.env\.(?P<name>[A-Za-z0-9_]+)\s*=\s*['\"](?P<value>[^'\"]+)['\"]"
)
APP_VERSION_PATTERN = re.compile(r"web-booking-main-([\w-]+)\.js")


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


class IberiaWebClient:
    """Small client for the public search API used by iberia.com.

    Endpoint addresses and the anonymous web-client credential are read from
    Iberia's current ``env-*.js`` file. The resulting bearer token is kept only
    on this object and expires shortly after the collection.
    """

    def __init__(self) -> None:
        self.session = requests.Session(impersonate="chrome")
        self.services_url = ""
        self.app_version = ""
        self.access_token = ""
        self._bootstrap()

    @staticmethod
    def _browser_headers() -> dict[str, str]:
        return {
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Origin": "https://www.iberia.com",
            "Referer": IBERIA_WEB_ENTRY,
        }

    def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                response = self.session.request(method, url, timeout=60, **kwargs)
                response.raise_for_status()
                return response
            except Exception as error:
                last_error = error
                if attempt + 1 < 4:
                    time_module.sleep(1.5 * (attempt + 1))
        raise RuntimeError(
            "Iberia odrzuciła zapytanie do swojej publicznej wyszukiwarki. "
            "Poprzedni plik wynikowy nie został nadpisany."
        ) from last_error

    def _bootstrap(self) -> None:
        page = self._request(
            "GET",
            IBERIA_WEB_ENTRY,
            headers=self._browser_headers(),
        ).text
        env_match = ENV_SCRIPT_PATTERN.search(page)
        if not env_match:
            raise RuntimeError("Nie znaleziono aktualnego pliku env wyszukiwarki Iberii")
        env_url = urljoin(IBERIA_WEB_ENTRY, env_match.group(1))
        env_text = self._request(
            "GET",
            env_url,
            headers=self._browser_headers(),
        ).text
        env = {
            match.group("name"): match.group("value")
            for match in ENV_VALUE_PATTERN.finditer(env_text)
        }
        required = {"services", "auth", "globalAuthorizationToken"}
        if not required <= env.keys():
            raise RuntimeError(
                f"Plik env Iberii nie zawiera pól: {sorted(required - env.keys())}"
            )

        version_match = APP_VERSION_PATTERN.search(page)
        self.app_version = (
            version_match.group(1).replace("-", ".") if version_match else "unknown"
        )
        token_url = (
            env["auth"].rstrip("/")
            + "/auth/realms/commercial_platform/protocol/openid-connect/token"
        )
        token_response = self._request(
            "POST",
            token_url,
            headers={
                **self._browser_headers(),
                "Authorization": env["globalAuthorizationToken"],
                "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            },
            data="grant_type=client_credentials",
        ).json()
        self.access_token = str(token_response.get("access_token") or "")
        if not self.access_token:
            raise RuntimeError("Iberia nie zwróciła anonimowego tokenu wyszukiwarki")
        self.services_url = env["services"].rstrip("/")

    def availability(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        *,
        canary_resident: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "isPetFlight": False,
            "slices": [{
                "origin": origin,
                "destination": destination,
                "date": departure_date.isoformat(),
            }],
            "passengers": [{"passengerType": "ADULT", "count": 1}],
            "marketCode": "ES",
            "preferredCabin": "ECONOMY",
        }
        if canary_resident:
            payload["specialDiscounts"] = [
                {"type": "RES", "discountType": "CANARIAS"}
            ]
        headers = {
            **self._browser_headers(),
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "X-Request-AppVersion": self.app_version,
            "X-Request-OsVersion": "Mac OS|10.15.7",
            "X-Request-Device": "desktop|Chrome|141.0.0.0",
            "X-Observations-Origin-Page": "home",
            "X-Observations-Current-Page": "availability",
        }
        response = self._request(
            "POST",
            f"{self.services_url}/sse-avm/rs/v2/availability",
            headers=headers,
            json=payload,
        ).json()
        if isinstance(response.get("data"), dict):
            return response["data"]
        return response


def _place_code(place: Any) -> str:
    if not isinstance(place, dict):
        return ""
    return str(
        place.get("code")
        or (place.get("airport") or {}).get("code")
        or place.get("iata")
        or ""
    ).upper()


def _price_amount(price: Any) -> float | None:
    if isinstance(price, (int, float)):
        return float(price)
    if not isinstance(price, dict):
        return None
    for key in ("total", "fare", "amount", "value"):
        value = price.get(key)
        if isinstance(value, (int, float)) and float(value) > 0:
            return float(value)
    return None


def _currency_code(payload: dict[str, Any], price: Any) -> str:
    if isinstance(price, dict):
        currency = price.get("currency") or price.get("currencyCode")
        if isinstance(currency, dict):
            currency = currency.get("code")
        if currency:
            return str(currency).upper()
    currencies = (payload.get("contextMetadata") or {}).get("currencies") or []
    if currencies:
        currency = currencies[0]
        if isinstance(currency, dict):
            currency = currency.get("code")
        if currency:
            return str(currency).upper()
    return "EUR"


def _iter_priced_slices(payload: dict[str, Any]) -> Iterable[tuple[dict[str, Any], Any]]:
    for destination in payload.get("originDestinations") or []:
        for slice_data in destination.get("slices") or []:
            yield slice_data, slice_data.get("price")
    for offer in payload.get("offers") or []:
        offer_price = offer.get("price")
        for slice_data in offer.get("slices") or []:
            yield slice_data, slice_data.get("price") or offer_price


def parse_iberia_response(
    payload: dict[str, Any],
    origin: str,
    destination: str,
    rates: dict[str, CurrencyRate],
    accepted_marketing: set[str],
    accepted_operating: set[str],
) -> list[dict[str, Any]]:
    """Transform direct Iberia-group flights from an availability response."""

    best_by_flight: dict[tuple[str, str, str], dict[str, Any]] = {}
    for slice_data, price_data in _iter_priced_slices(payload):
        segments = slice_data.get("segments") or []
        if len(segments) != 1:
            continue
        segment = segments[0]
        if _place_code(segment.get("departure")) != origin:
            continue
        if _place_code(segment.get("arrival")) != destination:
            continue
        flight = segment.get("flight") or {}
        marketing = flight.get("marketingCarrier") or {}
        operating = flight.get("operationalCarrier") or {}
        marketing_code = str(
            marketing.get("code") or flight.get("operationalDisclosure") or ""
        ).upper()
        operating_code = str(operating.get("code") or marketing_code).upper()
        if marketing_code not in accepted_marketing:
            continue
        if operating_code and operating_code not in accepted_operating:
            continue
        amount = _price_amount(price_data)
        if amount is None:
            continue
        currency = _currency_code(payload, price_data)
        if currency not in rates:
            continue
        raw_number = str(
            flight.get("marketingFlightNumber")
            or flight.get("flightNumber")
            or segment.get("flightNumber")
            or ""
        ).strip()
        if not raw_number:
            continue
        number = raw_number if raw_number.upper().startswith(marketing_code) else f"{marketing_code}{raw_number}"
        departure = local_datetime(segment["departureDateTime"], origin)
        arrival = local_datetime(segment["arrivalDateTime"], destination)
        operating_name = str(operating.get("name") or "")
        carrier = (
            "Iberia Express"
            if operating_code == "I2" or "express" in operating_name.lower()
            else "Iberia"
        )
        regular_pln = money_pln(amount, currency, rates)
        leg = {
            "carrier": carrier,
            "flight_number": number,
            "departure_airport": origin,
            "departure_at": serialize_datetime(departure),
            "arrival_airport": destination,
            "arrival_at": serialize_datetime(arrival),
            "price_regular_pln": regular_pln,
            "resident_discount_eligible": True,
            "resident_fare_multiplier": 0.25,
            "price_resident_estimated_pln": regular_pln,
            "booking_url": iberia_booking_url(origin, destination, departure),
            "price_source_currency": currency,
            "price_source_amount": amount,
        }
        key = (number, leg["departure_at"], leg["arrival_at"])
        previous = best_by_flight.get(key)
        if previous is None or regular_pln < previous["price_regular_pln"]:
            best_by_flight[key] = leg
    return sorted(best_by_flight.values(), key=lambda leg: leg["departure_at"])


def apply_resident_prices(
    regular_legs: list[dict[str, Any]],
    resident_legs: list[dict[str, Any]],
    multiplier: float,
) -> list[dict[str, Any]]:
    resident_by_flight = {
        (leg["flight_number"], leg["departure_at"], leg["arrival_at"]): leg
        for leg in resident_legs
    }
    merged: list[dict[str, Any]] = []
    for regular in regular_legs:
        leg = copy.deepcopy(regular)
        key = (leg["flight_number"], leg["departure_at"], leg["arrival_at"])
        discounted = resident_by_flight.get(key)
        regular_price = float(leg["price_regular_pln"])
        actual_price = (
            float(discounted["price_regular_pln"]) if discounted is not None else None
        )
        if actual_price is not None and 0 < actual_price < regular_price:
            leg["price_resident_estimated_pln"] = round(actual_price, 2)
            leg["resident_price_source"] = "Iberia availability with CANARIAS discount"
        else:
            leg["price_resident_estimated_pln"] = round(regular_price * multiplier, 2)
            leg["resident_price_source"] = "estimated from configured multiplier"
        leg["resident_fare_multiplier"] = multiplier
        merged.append(leg)
    return merged


def collect_iberia_trip(
    client: IberiaWebClient,
    origin: str,
    destination: str,
    departure_date: date,
    rates: dict[str, CurrencyRate],
    multiplier: float,
    accepted_marketing: set[str],
    accepted_operating: set[str],
) -> list[dict[str, Any]]:
    regular = parse_iberia_response(
        client.availability(
            origin,
            destination,
            departure_date,
            canary_resident=False,
        ),
        origin,
        destination,
        rates,
        accepted_marketing,
        accepted_operating,
    )
    resident = parse_iberia_response(
        client.availability(
            origin,
            destination,
            departure_date,
            canary_resident=True,
        ),
        origin,
        destination,
        rates,
        accepted_marketing,
        accepted_operating,
    )
    return apply_resident_prices(regular, resident, multiplier)


def collect_iberia_legs(
    candidates: set[tuple[str, str, date]],
    rates: dict[str, CurrencyRate],
    transfer_rules: dict[str, dict[str, Any]],
    airline_codes: dict[str, Any],
) -> list[dict[str, Any]]:
    if not candidates:
        return []
    client = IberiaWebClient()
    accepted_marketing = set(airline_codes["accepted_marketing"])
    accepted_operating = set(airline_codes["accepted_operating"])
    legs: list[dict[str, Any]] = []
    ordered = sorted(candidates, key=lambda item: (item[2], item[0], item[1]))
    for index, (origin, destination, day) in enumerate(ordered, start=1):
        transfer = destination if origin in TENERIFE_AIRPORTS else origin
        rule = transfer_rules[transfer]
        if not rule["resident_discount_eligible_on_iberia_leg"]:
            raise RuntimeError(f"Lotnisko {transfer} nie ma zniżki wymaganej w 1B")
        multiplier = float(rule["iberia_resident_fare_multiplier"])
        if not 0 < multiplier < 1:
            raise RuntimeError(f"Nieprawidłowy mnożnik zniżki Iberii dla {transfer}")
        legs.extend(
            collect_iberia_trip(
                client,
                origin,
                destination,
                day,
                rates,
                multiplier,
                accepted_marketing,
                accepted_operating,
            )
        )
        if index % 10 == 0 or index == len(ordered):
            print(f"Iberia: {index}/{len(ordered)} zapytań tras/dni", flush=True)
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
    candidates = candidate_binter_trips(low_cost_legs, args.from_date, end)
    print(f"Zapytania Iberia do sprawdzenia: {len(candidates)}", flush=True)
    iberia_legs = collect_iberia_legs(
        candidates,
        rates,
        transfer_rules,
        allowlist["iberia_airline_codes"],
    )
    if candidates and not iberia_legs:
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
            "iberia": "Publiczna wyszukiwarka Iberia availability z rabatem CANARIAS",
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
