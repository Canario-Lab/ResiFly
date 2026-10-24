"""Individual easyJet offers via the approved Google Flights HTTP source.

One adult, economy, one-way, direct only. All recognized offer buckets are
inspected. No daily-minimum expansion, timetable template or official API
fallback. HTTP attempts use the same host-wide cap/family lock as FR/IB/VY/UX.
"""
from datetime import date, timezone
import json
import math
import re
import threading
import time

from selectolax.lexbor import LexborHTMLParser

from scripts.collect_step1 import serialize_datetime
from scripts.collect_step1b import GoogleFlightsClient, _at, _google_datetime
from scripts.collection_coverage import calendar_collector
from scripts.collector_settings import google_flights_worker_count
from scripts.ryanair_google import _google_offers, _valid_clock
from scripts.source_recovery import map_jobs

MARKETING_CODES = {"U2", "EC", "DS"}
NUMBER = re.compile(r"(?:U2|EC|DS)\d{1,5}")


def parse_google_flights_response(html, origin, destination, departure_date):
    """Keep each direct flight's own lowest PLN offer, not another flight's fare."""
    if "PLN" not in html and "zł" not in html:
        raise RuntimeError("easyJet Google Flights did not confirm PLN")
    node = next((n for n in LexborHTMLParser(html).css("script")
                 if "ds:1" in (n.attributes.get("class") or "").split()), None)
    if node is None or "data:" not in node.text():
        raise RuntimeError("easyJet Google Flights did not return flight data")
    payload, _ = json.JSONDecoder().raw_decode(node.text().split("data:", 1)[1].lstrip())
    if (not isinstance(payload, list) or len(payload) <= 3 or
            payload[3] is not None and (not isinstance(payload[3], list) or not payload[3])):
        raise RuntimeError("Unknown easyJet Google Flights results structure")
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
        if marketing not in MARKETING_CODES:
            continue
        if not all(_valid_clock(_at(segment, index)) for index in (8, 10)):
            raise RuntimeError("Incomplete easyJet departure/arrival clock")
        departure = _google_datetime(_at(segment, 20), _at(segment, 8), origin)
        arrival = _google_datetime(_at(segment, 21), _at(segment, 10), destination)
        if departure.date() != departure_date:
            raise RuntimeError("easyJet Google Flights returned the wrong departure day")
        raw_number = str(_at(flight, 1, "")).replace(" ", "").upper()
        number = raw_number if raw_number.startswith(marketing) else marketing + raw_number
        if not NUMBER.fullmatch(number) or arrival.astimezone(timezone.utc) <= departure.astimezone(timezone.utc):
            raise RuntimeError("Invalid easyJet flight number or chronology")
        key = (number, departure.isoformat(), arrival.isoformat())
        amount = _at(_at(_at(offer, 1, []), 0, []), 1)
        if type(amount) not in (int, float) or not math.isfinite(amount) or amount <= 0:
            unpriced.add(key)
            continue
        regular = round(float(amount), 2)
        row = {"carrier": "easyJet", "marketing_carrier_code": marketing,
               "flight_number": number, "departure_airport": origin, "arrival_airport": destination,
               "departure_at": serialize_datetime(departure), "arrival_at": serialize_datetime(arrival),
               "price_regular_pln": regular, "price_resident_estimated_pln": regular,
               "resident_discount_eligible": False, "resident_fare_multiplier": 1.0,
               "price_source": "Google Flights", "price_scope": "individual_flight_offer",
               "price_source_currency": "PLN", "price_source_amount": regular,
               "price_passengers": {"adults": 1, "children": 0, "infants": 0},
               "price_seller_verified": False,
               "schedule_source": "Google Flights individual flight offer"}
        # Preserve a supplied operator label, never infer EC/DS from geography.
        operator = _at(segment, 2)
        if isinstance(operator, str) and operator.strip():
            row["operating_carrier_name"] = operator
        if key not in best or regular < best[key]["price_regular_pln"]:
            best[key] = row
    if unpriced - best.keys():
        raise RuntimeError(f"easyJet flights without individual prices: {origin}-{destination} {departure_date}")
    return sorted(best.values(), key=lambda r: (r["departure_at"], r["flight_number"]))


@calendar_collector("easyJet", "google_flights_http")
def collect_trip(client, origin, destination, departure_date):
    last_error = None
    for attempt in range(4):
        try:
            return parse_google_flights_response(client.availability(origin, destination, departure_date),
                                                 origin, destination, departure_date)
        except (RuntimeError, ValueError) as error:
            last_error = error
            if attempt < 3:
                from scripts.source_scheduler import retry_delay
                time.sleep(retry_delay(attempt, error))
    raise RuntimeError(f"easyJet Google Flights failed for {origin}-{destination} {departure_date}; publication blocked") from last_error


def collect_legs(route_days, workers):
    local = threading.local()
    def fetch(item):
        if not hasattr(local, "client"):
            local.client = GoogleFlightsClient(family="easyJet")
        return collect_trip(local.client, *item)
    ordered = sorted(route_days, key=lambda item: (item[2], item[0], item[1]))
    rows = []
    for index, found in enumerate(map_jobs("easyJet", fetch, ordered,
                                          google_flights_worker_count(workers)), 1):
        rows.extend(found)
        if index % 50 == 0 or index == len(ordered):
            print(f"easyJet Google Flights: {index}/{len(ordered)} route/days", flush=True)
    return rows
