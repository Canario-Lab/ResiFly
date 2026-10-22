#!/usr/bin/env python3
"""Build the public Step 5 mixed Ryanair × Wizz Air connection feed.

The collector reads the two fixed variants from the Step 5 allowlist, checks
both travel directions, requires a 2–24 hour layover, and keeps every valid
connection regardless of price. Price filtering belongs to the website.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
from zoneinfo import ZoneInfo

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.collection_coverage import collection_entrypoint, publish_document
from scripts.collect_step1 import (
    MAX_LAYOVER_MINUTES,
    MIN_LAYOVER_MINUTES,
    POLISH_AIRPORTS,
    TENERIFE_AIRPORTS,
    configure_airports_from_allowlist,
    dt,
    nbp_rate,
)
from scripts.collect_step2 import ryanair_client_version
from scripts.search_airports import validate_polish_transfer
from scripts.collect_step3 import collect_routes as collect_ryanair_routes
from scripts.collect_step4 import collect_routes as collect_wizz_routes


ROOT = Path(__file__).resolve().parents[1]
TRANSFER_FILE = ROOT / "data" / "mixed-transfer-airports.json"
DEFAULT_OUTPUT = ROOT / "data" / "step5-results.json"
SOURCE_CURRENCIES = ("EUR", "GBP", "HUF", "MAD", "PLN", "RON", "USD")

VARIANT_A = "ryanair_tenerife_wizzair_poland"
VARIANT_B = "wizzair_tenerife_ryanair_poland"


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


def load_allowlist(path: Path = TRANSFER_FILE) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def route_matrix(allowlist: dict[str, Any]) -> dict[str, list[tuple[str, str]]]:
    routes: dict[str, set[tuple[str, str]]] = {
        "Ryanair": set(),
        "Wizz Air": set(),
    }
    for variant_key, variant in allowlist["variants"].items():
        tenerife_carrier = variant["tenerife_leg_airline"]
        poland_carrier = variant["poland_leg_airline"]
        for transfer_data in variant["airports"]:
            transfer = transfer_data["iata"]
            for tenerife in transfer_data["tenerife_airports"]:
                routes[tenerife_carrier].add((tenerife, transfer))
                routes[tenerife_carrier].add((transfer, tenerife))
            for polish in transfer_data["polish_airports"]:
                validate_polish_transfer(polish, transfer, "step5_variant_a" if variant_key == VARIANT_A else "step5_variant_b")
                routes[poland_carrier].add((polish, transfer))
                routes[poland_carrier].add((transfer, polish))
    return {carrier: sorted(values) for carrier, values in routes.items()}


def collect_full_calendars(
    routes: dict[str, list[tuple[str, str]]],
    start: date,
    end: date,
    rates: dict[str, Any],
    client_version: str,
    workers: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ryanair_legs = collect_ryanair_routes(
        routes["Ryanair"],
        start,
        end,
        rates,
        client_version,
        workers,
    )
    wizz_legs = collect_wizz_routes(
        routes["Wizz Air"],
        start,
        end,
        rates,
        workers,
    )
    return ryanair_legs, wizz_legs


def discounted_leg(
    leg: dict[str, Any],
    transfer: str,
    eligible_transfers: set[str],
) -> dict[str, Any]:
    result = dict(leg)
    is_tenerife_leg = (
        result["departure_airport"] in TENERIFE_AIRPORTS
        or result["arrival_airport"] in TENERIFE_AIRPORTS
    )
    eligible = is_tenerife_leg and transfer in eligible_transfers
    regular = float(result["price_regular_pln"])
    result["resident_discount_eligible"] = eligible
    result["resident_fare_multiplier"] = 0.25 if eligible else 1.0
    result["price_resident_estimated_pln"] = round(
        regular * result["resident_fare_multiplier"],
        2,
    )
    return result


def connection_id(variant: str, legs: list[dict[str, Any]]) -> str:
    value = variant + "|" + "|".join(
        f"{leg['carrier']}:{leg['flight_number']}:{leg['departure_at']}:{leg['arrival_at']}"
        for leg in legs
    )
    return f"step5-{hashlib.sha256(value.encode()).hexdigest()[:16]}"


def build_connections(
    legs: list[dict[str, Any]],
    allowlist: dict[str, Any],
) -> list[dict[str, Any]]:
    by_carrier_route: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for leg in legs:
        key = (leg["carrier"], leg["departure_airport"], leg["arrival_airport"])
        by_carrier_route.setdefault(key, []).append(leg)

    discount_rules = allowlist["resident_discount_on_tenerife_leg"]
    results: list[dict[str, Any]] = []

    def combine(
        first_routes: list[dict[str, Any]],
        second_routes: list[dict[str, Any]],
        *,
        variant: str,
        transfer: str,
        direction: str,
        eligible_transfers: set[str],
    ) -> None:
        for first in first_routes:
            for second in second_routes:
                layover = round(
                    (dt(second["departure_at"]) - dt(first["arrival_at"])).total_seconds()
                    / 60
                )
                if not MIN_LAYOVER_MINUTES <= layover <= MAX_LAYOVER_MINUTES:
                    continue
                connection_legs = [
                    discounted_leg(first, transfer, eligible_transfers),
                    discounted_leg(second, transfer, eligible_transfers),
                ]
                regular_total = round(
                    sum(float(leg["price_regular_pln"]) for leg in connection_legs),
                    2,
                )
                resident_total = round(
                    sum(
                        float(leg["price_resident_estimated_pln"])
                        for leg in connection_legs
                    ),
                    2,
                )
                wizz_total_parts: list[float] = []
                wizz_total_available = True
                resident_wizz_total = 0.0
                for leg in connection_legs:
                    club = leg.get("price_wizz_discount_club_pln")
                    if leg["carrier"] == "Wizz Air":
                        if club is None:
                            wizz_total_available = False
                            resident_wizz_total += float(
                                leg["price_resident_estimated_pln"]
                            )
                        else:
                            wizz_total_parts.append(float(club))
                            resident_wizz_total += min(
                                float(club),
                                float(leg["price_resident_estimated_pln"]),
                            )
                    else:
                        regular = float(leg["price_regular_pln"])
                        wizz_total_parts.append(regular)
                        resident_wizz_total += float(
                            leg["price_resident_estimated_pln"]
                        )
                wizz_total = None
                if wizz_total_available:
                    wizz_total = round(sum(wizz_total_parts), 2)
                results.append({
                    "id": connection_id(variant, connection_legs),
                    "step": 5,
                    "variant": variant,
                    "origin_airport": connection_legs[0]["departure_airport"],
                    "destination_airport": connection_legs[-1]["arrival_airport"],
                    "direction": direction,
                    "connection_type": "one_stop",
                    "transfer_airport": transfer,
                    "layover_minutes": layover,
                    "self_transfer": True,
                    "legs": connection_legs,
                    "price_total_regular_pln": regular_total,
                    "price_total_wizz_discount_club_pln": wizz_total,
                    "price_total_resident_estimated_pln": resident_total,
                    "price_total_resident_wizz_discount_club_pln": round(
                        resident_wizz_total,
                        2,
                    ),
                })

    for variant_key, variant in allowlist["variants"].items():
        tenerife_carrier = variant["tenerife_leg_airline"]
        poland_carrier = variant["poland_leg_airline"]
        discount_variant = (
            "variant_a" if variant_key == VARIANT_A else "variant_b"
        )
        eligible_transfers = set(
            discount_rules[discount_variant]["eligible_transfer_airports"]
        )
        for transfer_data in variant["airports"]:
            transfer = transfer_data["iata"]
            for tenerife in transfer_data["tenerife_airports"]:
                for polish in transfer_data["polish_airports"]:
                    combine(
                        by_carrier_route.get(
                            (tenerife_carrier, tenerife, transfer), []
                        ),
                        by_carrier_route.get(
                            (poland_carrier, transfer, polish), []
                        ),
                        variant=variant_key,
                        transfer=transfer,
                        direction="tenerife_to_poland",
                        eligible_transfers=eligible_transfers,
                    )
                    combine(
                        by_carrier_route.get(
                            (poland_carrier, polish, transfer), []
                        ),
                        by_carrier_route.get(
                            (tenerife_carrier, transfer, tenerife), []
                        ),
                        variant=variant_key,
                        transfer=transfer,
                        direction="poland_to_tenerife",
                        eligible_transfers=eligible_transfers,
                    )

    unique = {result["id"]: result for result in results}
    return sorted(
        unique.values(),
        key=lambda result: (
            result["legs"][0]["departure_at"],
            result["price_total_regular_pln"],
            result["id"],
        ),
    )


def validate_document(document: dict[str, Any], allowlist: dict[str, Any]) -> None:
    results = document["results"]
    if not results:
        raise RuntimeError("Collector produced no Step 5 connections")
    directions = {result["direction"] for result in results}
    if directions != {"tenerife_to_poland", "poland_to_tenerife"}:
        raise RuntimeError(f"Both directions are required; got {sorted(directions)}")

    discount_rules = allowlist["resident_discount_on_tenerife_leg"]
    variants = allowlist["variants"]
    airport_rules = {
        variant_key: {item["iata"]: item for item in variant["airports"]}
        for variant_key, variant in variants.items()
    }
    for result in results:
        if result["connection_type"] != "one_stop" or len(result["legs"]) != 2:
            raise RuntimeError(f"Step 5 result must contain two legs: {result['id']}")
        if not MIN_LAYOVER_MINUTES <= result["layover_minutes"] <= MAX_LAYOVER_MINUTES:
            raise RuntimeError(f"Invalid layover in {result['id']}")
        variant_key = result.get("variant")
        if variant_key not in variants:
            raise RuntimeError(f"Unknown Step 5 variant in {result['id']}")
        variant = variants[variant_key]
        transfer = result["transfer_airport"]
        rule = airport_rules[variant_key].get(transfer)
        if not rule:
            raise RuntimeError(f"Transfer outside Step 5 allowlist in {result['id']}")
        if result["origin_airport"] in POLISH_AIRPORTS:
            polish = result["origin_airport"]
            tenerife = result["destination_airport"]
        else:
            polish = result["destination_airport"]
            tenerife = result["origin_airport"]
        validate_polish_transfer(polish, transfer, "step5_variant_a" if variant_key == VARIANT_A else "step5_variant_b")
        if polish not in rule["polish_airports"] or tenerife not in rule["tenerife_airports"]:
            raise RuntimeError(f"Route outside Step 5 allowlist in {result['id']}")

        discount_variant = (
            "variant_a" if variant_key == VARIANT_A else "variant_b"
        )
        eligible_transfers = set(
            discount_rules[discount_variant]["eligible_transfer_airports"]
        )
        for leg in result["legs"]:
            if not leg.get("booking_url"):
                raise RuntimeError(f"Missing booking URL in {result['id']}")
            is_tenerife_leg = (
                leg["departure_airport"] in TENERIFE_AIRPORTS
                or leg["arrival_airport"] in TENERIFE_AIRPORTS
            )
            expected_carrier = (
                variant["tenerife_leg_airline"]
                if is_tenerife_leg
                else variant["poland_leg_airline"]
            )
            if leg["carrier"] != expected_carrier:
                raise RuntimeError(f"Incorrect carrier assignment in {result['id']}")
            expected_eligible = is_tenerife_leg and transfer in eligible_transfers
            if leg["resident_discount_eligible"] != expected_eligible:
                raise RuntimeError(f"Incorrect resident discount in {result['id']}")


@collection_entrypoint("5")
def main(args) -> None:
    if args.days < 0:
        raise SystemExit("--days must be non-negative")
    if args.workers < 1:
        raise SystemExit("--workers must be positive")

    end = args.from_date + timedelta(days=args.days)
    allowlist = load_allowlist()
    configure_airports_from_allowlist(allowlist)
    discount_rules = allowlist["resident_discount_on_tenerife_leg"]
    routes = route_matrix(allowlist)
    rates = {code: nbp_rate(code, args.from_date) for code in SOURCE_CURRENCIES}
    print(
        "Kursy NBP: "
        + ", ".join(f"{code}={rate.pln:.4f} PLN" for code, rate in rates.items()),
        flush=True,
    )
    print(
        f"Trasy z zapisanej listy: Ryanair={len(routes['Ryanair'])}, "
        f"Wizz Air={len(routes['Wizz Air'])}",
        flush=True,
    )
    client_version = ryanair_client_version()
    ryanair_legs, wizz_legs = collect_full_calendars(
        routes,
        args.from_date,
        end,
        rates,
        client_version,
        args.workers,
    )
    print(
        f"Odcinki: Ryanair={len(ryanair_legs)}, Wizz Air={len(wizz_legs)}",
        flush=True,
    )
    results = build_connections(ryanair_legs + wizz_legs, allowlist)

    variants_metadata = {
        variant_key: {
            "label": variant["label"],
            "tenerife_leg_airline": variant["tenerife_leg_airline"],
            "poland_leg_airline": variant["poland_leg_airline"],
            "transfer_airports": [item["iata"] for item in variant["airports"]],
        }
        for variant_key, variant in allowlist["variants"].items()
    }
    document = {
        "schema_version": 2,
        "generated_at": datetime.now(ZoneInfo("Atlantic/Canary")).isoformat(
            timespec="seconds"
        ),
        "period_from": args.from_date.isoformat(),
        "period_to": end.isoformat(),
        "step": 5,
        "directions": ["tenerife_to_poland", "poland_to_tenerife"],
        "variants": variants_metadata,
        "carriers": ["Ryanair", "Wizz Air"],
        "layover_minutes": {
            "minimum": MIN_LAYOVER_MINUTES,
            "maximum": MAX_LAYOVER_MINUTES,
        },
        "resident_discount": {
            "eligible_fare_multiplier": discount_rules["eligible_fare_multiplier"],
            "ineligible_fare_multiplier": discount_rules["ineligible_fare_multiplier"],
            "applies_only_to_tenerife_leg": True,
            "variant_a": discount_rules["variant_a"],
            "variant_b": discount_rules["variant_b"],
        },
        "price_filtering": {
            "applied_during_collection": False,
            "controlled_by": "website",
        },
        "exchange_rates": {
            f"{code}_PLN": {
                "rate": rate.pln,
                "source": "NBP tabela A/B" if code != "PLN" else "wartość bazowa",
                "effective_for": args.from_date.isoformat(),
            }
            for code, rate in rates.items()
        },
        "sources": {
            "allowlist": "data/mixed-transfer-airports.json",
            "ryanair": "Ryanair public availability API with daily Fare Finder fallback",
            "wizz_air": "Wizz Air public timetableV2 API",
            "wizz_schedule_map": (
                "verified route flight numbers and published block times in "
                "scripts/collect_step4.py"
            ),
        },
        "results": results,
    }
    validate_document(document, allowlist)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    publish_document(document, args.output)
    counts = {
        "total": len(results),
        "variants": {
            variant: sum(result["variant"] == variant for result in results)
            for variant in allowlist["variants"]
        },
        "directions": {
            direction: sum(result["direction"] == direction for result in results)
            for direction in ("tenerife_to_poland", "poland_to_tenerife")
        },
    }
    print(f"Zapisano {len(results)} połączeń do {args.output}", flush=True)
    print(json.dumps(counts, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
