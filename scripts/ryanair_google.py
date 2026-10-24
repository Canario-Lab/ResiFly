"""Complete Ryanair route/day collection through Google Flights HTTP.

The carrier's public availability endpoint is not reliable enough for the
recurring collection.  Google Flights is queried one route/day at a time and
the normalized response is cached on disk so all ten public feeds in one batch
reuse the same source observation instead of repeatedly asking Google.
"""

from __future__ import annotations

from datetime import date
import json
import math
import os
from pathlib import Path
import re
import threading
import time
from typing import Any

from selectolax.lexbor import LexborHTMLParser

from scripts.booking_urls import ryanair_booking_url
from scripts.collector_settings import GOOGLE_FLIGHTS_MAX_WORKERS
from scripts.collect_step1 import serialize_datetime
from scripts.collect_step1b import GoogleFlightsClient, _at, _google_datetime


ROOT = Path(__file__).resolve().parents[1]
PARSER_VARIANT = "FR_RK_v2"
MARKETING_CODES = {"FR", "RK"}
FLIGHT_NUMBER = re.compile(r"(?:FR|RK)\d{1,5}")
UK_AIRPORTS = {"BHX", "BOH", "BRS", "EDI", "EMA", "LBA", "LPL", "LTN", "MAN", "NCL", "STN"}

_request_slots = threading.BoundedSemaphore(GOOGLE_FLIGHTS_MAX_WORKERS)
_thread_local = threading.local()
_cache_lock = threading.Lock()
_cache_rows: dict[Path, dict[str, dict[str, Any]]] = {}


def _google_offers(value: Any):
    """Visit every recognized Google offer bucket."""
    if not isinstance(value, list):
        return
    segments = _at(_at(value, 0, []), 2, [])
    if (
        isinstance(segments, list)
        and segments
        and all(
            isinstance(segment, list)
            and isinstance(_at(segment, 22), list)
            and isinstance(_at(segment, 3), str)
            and isinstance(_at(segment, 6), str)
            for segment in segments
        )
    ):
        yield value
        return
    for child in value:
        yield from _google_offers(child)


def _valid_clock(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    hour = _at(value, 0, 0)
    minute = _at(value, 1, 0)
    hour = 0 if hour is None else hour
    minute = 0 if minute is None else minute
    return (
        isinstance(hour, int)
        and not isinstance(hour, bool)
        and isinstance(minute, int)
        and not isinstance(minute, bool)
        and 0 <= hour <= 23
        and 0 <= minute <= 59
    )


def parse_google_flights_response(
    html: str,
    origin: str,
    destination: str,
    departure_date: date,
) -> list[dict[str, Any]]:
    """Return every direct FR/RK-marketed flight and its own PLN price."""
    parser = LexborHTMLParser(html)
    node = next(
        (
            candidate
            for candidate in parser.css("script")
            if "ds:1" in (candidate.attributes.get("class") or "").split()
        ),
        None,
    )
    if node is None or "data:" not in node.text():
        raise RuntimeError("Google Flights did not return the Ryanair flight payload")
    raw = node.text().split("data:", 1)[1].lstrip()
    payload, _ = json.JSONDecoder().raw_decode(raw)
    if not isinstance(payload, list) or len(payload) <= 3:
        raise RuntimeError("Unknown Google Flights Ryanair payload")
    if payload[3] is not None and (not isinstance(payload[3], list) or not payload[3]):
        raise RuntimeError("Unknown Google Flights Ryanair results block")

    best: dict[tuple[str, str, str], dict[str, Any]] = {}
    unpriced: set[tuple[str, str, str]] = set()
    for offer in _google_offers(payload):
        segments = _at(_at(offer, 0, []), 2, [])
        if len(segments) != 1:
            continue
        segment = segments[0]
        if str(_at(segment, 3, "")).upper() != origin:
            continue
        if str(_at(segment, 6, "")).upper() != destination:
            continue
        flight = _at(segment, 22, [])
        marketing = str(_at(flight, 0, "")).upper()
        if marketing not in MARKETING_CODES:
            continue
        if not _valid_clock(_at(segment, 8)) or not _valid_clock(_at(segment, 10)):
            raise RuntimeError(f"Incomplete Ryanair clock for {origin}-{destination} {departure_date}")
        departure = _google_datetime(_at(segment, 20), _at(segment, 8), origin)
        arrival = _google_datetime(_at(segment, 21), _at(segment, 10), destination)
        if departure.date() != departure_date:
            continue
        raw_number = str(_at(flight, 1, "")).replace(" ", "").upper()
        number = raw_number if raw_number.startswith(tuple(MARKETING_CODES)) else f"{marketing}{raw_number}"
        if not FLIGHT_NUMBER.fullmatch(number) or arrival <= departure:
            raise RuntimeError(f"Invalid Ryanair number or dates for {origin}-{destination} {departure_date}")
        key = (number, departure.isoformat(), arrival.isoformat())
        amount = _at(_at(_at(offer, 1, []), 0, []), 1)
        if (
            not isinstance(amount, (int, float))
            or isinstance(amount, bool)
            or not math.isfinite(amount)
            or amount <= 0
        ):
            unpriced.add(key)
            continue
        regular = round(float(amount), 2)
        leg = {
            "carrier": "Ryanair",
            "flight_number": number,
            "departure_airport": origin,
            "departure_at": serialize_datetime(departure),
            "arrival_airport": destination,
            "arrival_at": serialize_datetime(arrival),
            "price_regular_pln": regular,
            "resident_discount_eligible": False,
            "price_resident_estimated_pln": regular,
            "booking_url": ryanair_booking_url(origin, destination, departure),
            "booking_url_scope": "route_date_search",
            "price_source": "Google Flights",
            "price_scope": "individual_flight_offer",
            "price_source_currency": "PLN",
            "price_source_amount": regular,
            "price_seller_verified": False,
            "schedule_source": "Google Flights individual flight offer",
        }
        if key not in best or regular < best[key]["price_regular_pln"]:
            best[key] = leg
    missing_prices = unpriced - best.keys()
    if missing_prices:
        raise RuntimeError(
            f"Google Flights returned {len(missing_prices)} Ryanair flights without a usable price "
            f"for {origin}-{destination} {departure_date}"
        )
    return sorted(best.values(), key=lambda leg: (leg["departure_at"], leg["flight_number"]))


def _cache_path(start: date, end: date) -> Path:
    configured = os.environ.get("RESIFLY_RYANAIR_GOOGLE_CACHE")
    if configured:
        return Path(configured).resolve()
    return ROOT / "tmp" / "ryanair-google-cache" / f"{start.isoformat()}--{end.isoformat()}.jsonl"


def _load_cache(path: Path) -> dict[str, dict[str, Any]]:
    with _cache_lock:
        if path in _cache_rows:
            return _cache_rows[path]
        rows: dict[str, dict[str, Any]] = {}
        if path.exists():
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    if number == len(path.read_text(encoding="utf-8").splitlines()):
                        break
                    raise
                if isinstance(row, dict) and isinstance(row.get("key"), str):
                    rows[row["key"]] = row
        _cache_rows[path] = rows
        return rows


def _cache_row_is_current(row: dict[str, Any], origin: str, destination: str) -> bool:
    if row.get("status") != "ok" or not isinstance(row.get("flights"), list):
        return False
    if row.get("parser_variant") == PARSER_VARIANT:
        return True
    # The original diagnostic parser understood FR only.  It remains complete
    # for routes outside the UK; every UK-touching day must be re-read by the
    # FR+RK parser before it can be reused by a public collection.
    return origin not in UK_AIRPORTS and destination not in UK_AIRPORTS and all(
        str(leg.get("flight_number", "")).startswith("FR") for leg in row["flights"]
    )


def _append_cache(path: Path, row: dict[str, Any]) -> None:
    with _cache_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False, separators=(",", ":")))
            stream.write("\n")
            stream.flush()
        _cache_rows.setdefault(path, {})[row["key"]] = row


def collect_route_days(origin: str, destination: str, start: date, end: date) -> list[dict[str, Any]]:
    """Collect and cache every day in an inclusive route window."""
    path = _cache_path(start, end)
    rows = _load_cache(path)
    legs: list[dict[str, Any]] = []
    day = start
    while day <= end:
        key = f"{origin}|{destination}|{day.isoformat()}"
        cached = rows.get(key)
        if cached is not None and _cache_row_is_current(cached, origin, destination):
            legs.extend(cached["flights"])
            day = date.fromordinal(day.toordinal() + 1)
            continue

        last_error: Exception | None = None
        flights: list[dict[str, Any]] | None = None
        for attempt in range(4):
            try:
                if not hasattr(_thread_local, "client"):
                    _thread_local.client = GoogleFlightsClient(family="Ryanair")
                with _request_slots:
                    html = _thread_local.client.availability(origin, destination, day)
                if "PLN" not in html and "zł" not in html:
                    raise RuntimeError("Google Flights response did not confirm PLN currency")
                flights = parse_google_flights_response(html, origin, destination, day)
                last_error = None
                break
            except (RuntimeError, json.JSONDecodeError, ValueError) as error:
                last_error = error
                if attempt + 1 < 4:
                    from scripts.source_scheduler import retry_delay
                    time.sleep(retry_delay(attempt, error))
        if last_error is not None or flights is None:
            raise RuntimeError(
                f"Ryanair Google Flights failed for {origin}-{destination} on {day}; "
                "publication blocked"
            ) from last_error
        row = {
            "key": key,
            "origin": origin,
            "destination": destination,
            "date": day.isoformat(),
            "status": "ok",
            "parser_variant": PARSER_VARIANT,
            "source": "google_flights_http",
            "flights": flights,
        }
        _append_cache(path, row)
        legs.extend(flights)
        day = date.fromordinal(day.toordinal() + 1)

    unique = {
        (leg["flight_number"], leg["departure_at"], leg["arrival_at"]): leg
        for leg in legs
    }
    return sorted(unique.values(), key=lambda leg: (leg["departure_at"], leg["flight_number"]))
