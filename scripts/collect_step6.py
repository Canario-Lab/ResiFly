#!/usr/bin/env python3
"""Step 6: easyJet Tenerife leg + Ryanair/Wizz Poland leg, both directions.

The fixed allowlist is discovered separately. Collect every independent full
calendar before matching same-IATA, one-transfer, 2–24 h connections. No price
filtering and no daily-minimum, schedule-template or alternate-source fallback.
"""
import argparse
from copy import deepcopy
from datetime import date, datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.booking_urls import easyjet_booking_url, ryanair_booking_url, wizz_booking_url
from scripts.collection_coverage import collection_entrypoint, publish_document
from scripts.collect_step1 import (
    configure_airports_from_allowlist, date_range, dt, nbp_rates,
)
from scripts.collect_step1c import low_cost_route_matrix, collect_low_cost_legs
from scripts.easyjet_source import collect_legs, MARKETING_CODES, NUMBER
from scripts.search_airports import POLISH_AIRPORTS, TENERIFE_AIRPORTS
from scripts.spanish_resident_fees import apply_resident_price_estimate, validate_resident_price_estimate
from scripts.wizz_schedules import load_wizz_route_data

ROOT = Path(__file__).resolve().parents[1]
TRANSFER_FILE = ROOT / "data/easyjet-transfer-airports.json"
DEFAULT_OUTPUT = ROOT / "data/step6-results.json"


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_allowlist():
    return json.loads(TRANSFER_FILE.read_text(encoding="utf-8"))


def validate_allowlist(allowlist):
    if (allowlist.get("usage_policy", {}).get("step") != 6 or
            allowlist["usage_policy"].get("flight_data_source") != "google_flights_http"):
        raise RuntimeError("Step 6 requires the approved Google Flights HTTP source")
    if set(allowlist.get("scope", {}).get("polish_airports", [])) != set(POLISH_AIRPORTS):
        raise RuntimeError("Step 6 must use every canonical Polish endpoint")
    if set(allowlist.get("easyjet_airline_codes", {}).get("accepted_marketing", [])) != MARKETING_CODES:
        raise RuntimeError("Invalid easyJet airline family")
    schedules, _ = load_wizz_route_data()
    codes = set()
    for airport in allowlist.get("airports", []):
        hub = airport["iata"]
        if not re.fullmatch(r"[A-Z]{3}", hub) or hub in codes or hub in TENERIFE_AIRPORTS:
            raise RuntimeError("Duplicate/invalid easyJet transfer airport")
        codes.add(hub)
        ZoneInfo(airport["timezone"])
        if not airport.get("tenerife_airports") or not set(airport["tenerife_airports"]) <= set(TENERIFE_AIRPORTS):
            raise RuntimeError("Invalid easyJet Tenerife routes")
        eligible = airport.get("resident_discount_eligible_on_easyjet_leg")
        if type(eligible) is not bool or not airport.get("resident_eligibility_evidence", {}).get("source"):
            raise RuntimeError("Missing explicit easyJet resident assessment")
        if eligible:
            if (airport.get("country_code", "").upper() != "ES" or
                    airport.get("resident_pricing_method") != "aena_estimate" or
                    airport.get("easyjet_resident_fare_multiplier") != .25):
                raise RuntimeError("Unverified easyJet resident rule")
        elif (airport.get("easyjet_resident_fare_multiplier") != 1.0 or
              airport.get("resident_pricing_method") != "none" or
              airport.get("country_code", "").upper() == "ES"):
            raise RuntimeError("New Spanish easyJet route requires explicit resident review")
        endpoints = set()
        if not airport.get("polish_routes"):
            raise RuntimeError("easyJet hub has no saved Poland route")
        for route in airport["polish_routes"]:
            polish, airlines = route["polish_airport"], route["airlines"]
            if polish not in POLISH_AIRPORTS or polish == hub or polish in endpoints:
                raise RuntimeError("Invalid/self/duplicate Step 6 Poland route")
            endpoints.add(polish)
            if not airlines or not set(airlines) <= {"Ryanair", "Wizz Air"}:
                raise RuntimeError("Invalid Step 6 Poland carrier")
            if "Wizz Air" in airlines and not all(p in schedules for p in ((hub, polish), (polish, hub))):
                raise RuntimeError("Active Step 6 Wizz route needs verified metadata in both directions")
    if not codes:
        raise RuntimeError("Empty easyJet allowlist")


def easyjet_route_days(allowlist, start, end):
    return {(origin, destination, day)
            for airport in allowlist["airports"] for tenerife in airport["tenerife_airports"]
            for origin, destination in ((tenerife, airport["iata"]), (airport["iata"], tenerife))
            for day in date_range(start, end)}


def prepare_easyjet_legs(rows, allowlist, eur_pln):
    """Derive discounts/booking URLs in the builder, keep raw observations immutable."""
    rules = {a["iata"]: a for a in allowlist["airports"]}
    result = deepcopy(rows)
    for leg in result:
        hub = leg["arrival_airport"] if leg["departure_airport"] in TENERIFE_AIRPORTS else leg["departure_airport"]
        rule = rules[hub]
        leg["resident_discount_eligible"] = rule["resident_discount_eligible_on_easyjet_leg"]
        leg["resident_fare_multiplier"] = rule["easyjet_resident_fare_multiplier"]
        if leg["resident_discount_eligible"]:
            apply_resident_price_estimate(leg, eur_pln)
        else:
            leg["price_resident_estimated_pln"] = leg["price_regular_pln"]
            leg["resident_price_method"] = "not_eligible"
        leg["booking_url"] = easyjet_booking_url(leg["departure_airport"], leg["arrival_airport"], leg["departure_at"])
        leg["booking_url_scope"] = "route_date_search"
    return result


def connection_id(legs):
    raw = "|".join(f"{r['carrier']}:{r['flight_number']}:{r['departure_airport']}:{r['arrival_airport']}:{r['departure_at']}:{r['arrival_at']}" for r in legs)
    return "step6-" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def totals(legs):
    regular = sum(float(r["price_regular_pln"]) for r in legs)
    resident = sum(float(r["price_resident_estimated_pln"]) for r in legs)
    club, combined, club_available = 0., 0., True
    for row in legs:
        price = row.get("price_wizz_discount_club_pln") if row["carrier"] == "Wizz Air" else row["price_regular_pln"]
        if price is None:
            club_available = False
            price = row["price_regular_pln"]
        club += float(price)
        combined += min(float(price), float(row["price_resident_estimated_pln"]))
    return {"price_total_regular_pln": round(regular, 2),
            "price_total_resident_estimated_pln": round(resident, 2),
            "price_total_wizz_discount_club_pln": round(club, 2) if club_available else None,
            "price_total_resident_wizz_discount_club_pln": round(combined, 2)}


def build_connections(low_cost, easyjet, allowlist):
    permitted = set(low_cost_route_matrix(allowlist))
    easyjet_routes = {(o, d) for o, d, _ in easyjet_route_days(allowlist, date(2000, 1, 1), date(2000, 1, 1))}
    by_hub = {}
    for row in easyjet:
        if row.get("carrier") != "easyJet" or (row["departure_airport"], row["arrival_airport"]) not in easyjet_routes:
            continue
        hub = row["arrival_airport"] if row["departure_airport"] in TENERIFE_AIRPORTS else row["departure_airport"]
        by_hub.setdefault(hub, []).append(row)
    results = {}
    for low in low_cost:
        if (low["carrier"], low["departure_airport"], low["arrival_airport"]) not in permitted:
            continue
        outbound = low["departure_airport"] in POLISH_AIRPORTS
        hub = low["arrival_airport"] if outbound else low["departure_airport"]
        for jet in by_hub.get(hub, []):
            legs = [low, jet] if outbound else [jet, low]
            if legs[0]["arrival_airport"] != legs[1]["departure_airport"]:
                continue
            if (legs[-1]["arrival_airport"] not in TENERIFE_AIRPORTS if outbound else
                    legs[0]["departure_airport"] not in TENERIFE_AIRPORTS):
                continue
            minutes = (dt(legs[1]["departure_at"]) - dt(legs[0]["arrival_at"])).total_seconds() / 60
            if not 120 <= minutes <= 1440:
                continue
            identifier = connection_id(legs)
            results[identifier] = {"id": identifier, "step": 6,
                "origin_airport": legs[0]["departure_airport"], "destination_airport": legs[-1]["arrival_airport"],
                "direction": "poland_to_tenerife" if outbound else "tenerife_to_poland",
                "connection_type": "one_stop", "transfer_airport": hub,
                "layover_minutes": round(minutes), "self_transfer": True, "legs": deepcopy(legs), **totals(legs)}
    return sorted(results.values(), key=lambda r: (r["legs"][0]["departure_at"], r["price_total_regular_pln"], r["id"]))


def validate_document(document, allowlist=None):
    allowlist = load_allowlist() if allowlist is None else allowlist
    validate_allowlist(allowlist)
    permitted = set(low_cost_route_matrix(allowlist))
    for result in document["results"]:
        legs = result["legs"]
        if len(legs) != 2 or sum(r["carrier"] == "easyJet" for r in legs) != 1:
            raise RuntimeError("Step 6 requires easyJet and exactly one low-cost leg")
        low = next(r for r in legs if r["carrier"] != "easyJet")
        if (low["carrier"], low["departure_airport"], low["arrival_airport"]) not in permitted:
            raise RuntimeError("Unallowlisted Step 6 Poland leg")
        jet = next(r for r in legs if r["carrier"] == "easyJet")
        if (jet.get("price_source") != "Google Flights" or jet.get("price_scope") != "individual_flight_offer"
                or not NUMBER.fullmatch(jet.get("flight_number", ""))):
            raise RuntimeError("Invalid easyJet number or individual-fare source")
        if jet.get("resident_discount_eligible"):
            validate_resident_price_estimate(jet)
        elif jet.get("price_resident_estimated_pln") != jet["price_regular_pln"]:
            raise RuntimeError("Discount on an ineligible easyJet leg")
        for leg in legs:
            builder = {"easyJet": easyjet_booking_url, "Ryanair": ryanair_booking_url, "Wizz Air": wizz_booking_url}[leg["carrier"]]
            if leg.get("booking_url") != builder(leg["departure_airport"], leg["arrival_airport"], leg["departure_at"]):
                raise RuntimeError("Invalid Step 6 booking URL")
            for field in ("price_regular_pln", "price_resident_estimated_pln"):
                if type(leg[field]) not in (int, float) or not math.isfinite(leg[field]) or leg[field] <= 0:
                    raise RuntimeError("Invalid Step 6 fare")
        # Rebuild using the canonical rules: direction, same IATA, chronology,
        # discount eligibility and totals cannot be bypassed by edited results.
        prepared = prepare_easyjet_legs([jet], allowlist, float(document["exchange_rates"]["EUR_PLN"]["rate"]))
        expected = build_connections([low], prepared, allowlist)
        if len(expected) != 1 or expected[0] != result:
            raise RuntimeError("Invalid Step 6 connection, resident rule or totals")


@collection_entrypoint("6")
def main(args):
    end = args.from_date + timedelta(days=args.days)
    allowlist = load_allowlist()
    validate_allowlist(allowlist)
    configure_airports_from_allowlist(allowlist)
    rates = nbp_rates(args.from_date)
    low = collect_low_cost_legs(allowlist, args.from_date, end, rates, args.workers)
    jet = prepare_easyjet_legs(collect_legs(easyjet_route_days(allowlist, args.from_date, end), args.workers), allowlist, rates["EUR"].pln)
    results = build_connections(low, jet, allowlist)
    document = {"schema_version": 2, "step": 6,
        "generated_at": datetime.now(ZoneInfo("Atlantic/Canary")).isoformat(timespec="seconds"),
        "period_from": str(args.from_date), "period_to": str(end),
        "directions": ["poland_to_tenerife", "tenerife_to_poland"],
        "transfer_airports": [a["iata"] for a in allowlist["airports"]],
        "price_filtering": {"applied_during_collection": False, "controlled_by": "website"},
        "exchange_rates": {f"{code}_PLN": {"rate": rate.pln, "source": "NBP wspólny snapshot A/B", "effective_for": str(args.from_date)}
                           for code, rate in rates.items() if code != "PLN"},
        "sources": {"easyjet": "Google Flights HTTP only, individual direct offers for one adult",
                    "ryanair": "Google Flights HTTP FR/RK", "wizz_air": "Official timetableV2 regular/WDC"},
        "result_status": "ok" if results else "no_matching_connections", "results": results}
    validate_document(document, allowlist)
    publish_document(document, args.output)
    print(f"Saved {len(results)} Step 6 connections to {args.output}", flush=True)


if __name__ == "__main__":
    main()
