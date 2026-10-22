#!/usr/bin/env python3
"""Reprice saved estimated Spanish resident fares without network requests.

The command preserves collected flights, regular fares, booking links,
generation timestamps and source-coverage certificates. It updates only the
derived resident fields and totals in Steps 1B, 1C, 1D, 1E, 3, 4 and 5.
Binter (1A) and Canaryfly (1F) are excluded because their resident fares come
directly from the carriers.
"""

from __future__ import annotations

from datetime import date, datetime
import importlib
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from scripts.collection_coverage import atomic_json, validate_coverage
from scripts.spanish_resident_fees import (
    apply_resident_price_estimate,
    load_fee_registry,
    nondiscountable_fee_eur,
)


ROOT = Path(__file__).resolve().parents[1]
STEPS = ("1b", "1c", "1d", "1e", "3", "4", "5")


def _path(step: str) -> Path:
    return ROOT / "data" / f"step{step}-results.json"


def _validate_document(step: str, document: dict[str, Any]) -> None:
    module = importlib.import_module(f"scripts.collect_step{step}")
    if step in {"3", "4", "5"}:
        allowlist = module.load_allowlist()
        module.validate_document(document, allowlist)
    else:
        module.validate_document(document)


def _resident_wizz_total(legs: list[dict[str, Any]]) -> float:
    total = 0.0
    for leg in legs:
        resident = float(leg["price_resident_estimated_pln"])
        club = leg.get("price_wizz_discount_club_pln")
        if leg["carrier"] == "Wizz Air" and club is not None:
            total += min(float(club), resident)
        else:
            total += resident
    return round(total, 2)


def reprice_document(
    step: str,
    document: dict[str, Any],
    registry: dict[str, Any],
) -> int:
    start = date.fromisoformat(document["period_from"])
    end = date.fromisoformat(document["period_to"])
    validate_coverage(document, step, start, end)
    eur_pln = float(document["exchange_rates"]["EUR_PLN"]["rate"])
    changed = 0
    for result in document["results"]:
        for leg in result["legs"]:
            if not leg.get("resident_discount_eligible"):
                continue
            fee_eur = nondiscountable_fee_eur(
                leg["departure_airport"], leg["arrival_airport"],
                leg["departure_at"], registry,
            )
            if leg.get("carrier") == "Volotea" and leg.get("price_source_taxes") is not None:
                if round(float(leg["price_source_taxes"]), 2) != fee_eur:
                    raise RuntimeError(
                        "Zapisane podatki Volotei nie zgadzają się z tabelą Aena"
                    )
            apply_resident_price_estimate(
                leg, eur_pln, registry, fee_eur=fee_eur,
            )
            changed += 1
        result["price_total_resident_estimated_pln"] = round(sum(
            float(leg["price_resident_estimated_pln"]) for leg in result["legs"]
        ), 2)
        if "price_total_resident_wizz_discount_club_pln" in result:
            result["price_total_resident_wizz_discount_club_pln"] = (
                _resident_wizz_total(result["legs"])
            )
    document.setdefault("sources", {})["resident_price_estimate"] = (
        "25% of fare component plus fixed non-discountable fees from "
        "data/spanish-resident-fees.json"
    )
    document["derived_prices_updated_at"] = datetime.now(
        ZoneInfo("Atlantic/Canary")
    ).isoformat(timespec="seconds")
    document["derived_price_update"] = {
        "scope": "estimated Spanish resident leg prices and dependent totals only",
        "network_requests": False,
        "source_collection_generated_at": document["generated_at"],
        "collection_run_id": document["collection_coverage"]["run_id"],
        "fee_registry": "data/spanish-resident-fees.json",
        "fee_registry_verified_on": registry["verified_on"],
    }
    _validate_document(step, document)
    return changed


def main() -> None:
    registry = load_fee_registry()
    prepared: list[tuple[Path, dict[str, Any], int]] = []
    for step in STEPS:
        path = _path(step)
        document = json.loads(path.read_text(encoding="utf-8"))
        changed = reprice_document(step, document, registry)
        prepared.append((path, document, changed))
    for path, document, changed in prepared:
        atomic_json(path, document)
        print(f"{path.name}: przeliczono {changed} odcinków bez zapytań sieciowych")


if __name__ == "__main__":
    main()
