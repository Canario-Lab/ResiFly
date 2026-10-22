"""Shared Aena-fee-aware resident price estimates for Spanish domestic legs."""

from __future__ import annotations

from datetime import date, datetime
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FEE_FILE = ROOT / "data" / "spanish-resident-fees.json"


def load_fee_registry() -> dict[str, Any]:
    registry = json.loads(FEE_FILE.read_text(encoding="utf-8"))
    validate_fee_registry(registry)
    return registry


def validate_fee_registry(registry: dict[str, Any]) -> None:
    if registry.get("schema_version") != 1 or registry.get("currency") != "EUR":
        raise RuntimeError("Nieprawidłowy rejestr opłat rezydenckich")
    start = date.fromisoformat(registry["valid_for_departures_from"])
    end = date.fromisoformat(registry["valid_for_departures_through"])
    if end < start:
        raise RuntimeError("Nieprawidłowy okres obowiązywania opłat rezydenckich")
    peninsula = registry.get("peninsula_departure_fees_eur")
    tenerife = registry.get("tenerife_to_peninsula_departure_fees_eur")
    if not isinstance(peninsula, dict) or not peninsula or set(tenerife or {}) != {"TFN", "TFS"}:
        raise RuntimeError("Rejestr opłat nie zawiera pełnych stawek Teneryfa–półwysep")
    for airport, amount in {**peninsula, **tenerife}.items():
        if (not isinstance(airport, str) or len(airport) != 3 or
                not isinstance(amount, (int, float)) or isinstance(amount, bool) or
                not math.isfinite(amount) or amount <= 0):
            raise RuntimeError(f"Nieprawidłowa stawka opłat dla {airport}")


def _departure_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(value).date()


def nondiscountable_fee_eur(
    origin: str,
    destination: str,
    departure: str | date | datetime,
    registry: dict[str, Any] | None = None,
) -> float:
    registry = registry or load_fee_registry()
    day = _departure_date(departure)
    valid_from = date.fromisoformat(registry["valid_for_departures_from"])
    valid_through = date.fromisoformat(registry["valid_for_departures_through"])
    if not valid_from <= day <= valid_through:
        raise RuntimeError(
            f"Tabela opłat Aena nie obejmuje daty {day}; aktualizacja wymagana przed publikacją"
        )
    peninsula = registry["peninsula_departure_fees_eur"]
    tenerife = registry["tenerife_to_peninsula_departure_fees_eur"]
    if origin in peninsula and destination in tenerife:
        return float(peninsula[origin])
    if origin in tenerife and destination in peninsula:
        return float(tenerife[origin])
    raise RuntimeError(f"Brak opłaty rezydenckiej Aena dla {origin}-{destination}")


def resident_price_estimate(
    regular_pln: float,
    multiplier: float,
    nondiscountable_fees_eur: float,
    eur_pln: float,
) -> tuple[float, float]:
    """Discount only the fare component and return estimate plus fees in PLN."""
    values = (regular_pln, multiplier, nondiscountable_fees_eur, eur_pln)
    if any(not isinstance(value, (int, float)) or isinstance(value, bool)
           or not math.isfinite(value) for value in values):
        raise RuntimeError("Nieprawidłowe dane do wyliczenia ceny rezydenta")
    fees_pln = round(nondiscountable_fees_eur * eur_pln, 2)
    if regular_pln <= 0 or not 0 < multiplier <= 1 or fees_pln <= 0 or regular_pln < fees_pln:
        raise RuntimeError("Cena regularna jest niższa od stałych opłat")
    resident = round((regular_pln - fees_pln) * multiplier + fees_pln, 2)
    return resident, fees_pln


def apply_resident_price_estimate(
    leg: dict[str, Any],
    eur_pln: float,
    registry: dict[str, Any] | None = None,
    *,
    fee_eur: float | None = None,
) -> None:
    """Update only derived resident-price fields on one eligible leg."""
    if not leg.get("resident_discount_eligible", True):
        raise RuntimeError("Nie można zastosować opłat rezydenckich do niekwalifikującego się lotu")
    registry = registry or load_fee_registry()
    expected_fee_eur = nondiscountable_fee_eur(
        leg["departure_airport"], leg["arrival_airport"], leg["departure_at"], registry,
    )
    if fee_eur is not None and round(float(fee_eur), 2) != expected_fee_eur:
        raise RuntimeError("Przekazana opłata nie zgadza się ze wspólną tabelą Aena")
    fee_eur = expected_fee_eur
    multiplier = float(leg.get("resident_fare_multiplier", 0.25))
    resident, fees_pln = resident_price_estimate(
        float(leg["price_regular_pln"]), multiplier, fee_eur, eur_pln,
    )
    leg.update({
        "price_resident_estimated_pln": resident,
        "resident_discount_eligible": True,
        "resident_fare_multiplier": multiplier,
        "resident_nondiscountable_fees_eur": fee_eur,
        "resident_nondiscountable_fees_pln": fees_pln,
        "resident_estimate_exchange_rate_eur_pln": eur_pln,
        "resident_price_source": (
            "estimate: 25% of regular fare excluding fixed non-discountable "
            "Spanish airport fees, plus those fees"
        ),
    })


def validate_resident_price_estimate(
    leg: dict[str, Any],
    registry: dict[str, Any] | None = None,
) -> None:
    registry = registry or load_fee_registry()
    expected_fee_eur = nondiscountable_fee_eur(
        leg["departure_airport"], leg["arrival_airport"], leg["departure_at"], registry,
    )
    if float(leg["resident_nondiscountable_fees_eur"]) != expected_fee_eur:
        raise RuntimeError("Opłata zapisana w odcinku nie zgadza się z tabelą Aena")
    expected, fees_pln = resident_price_estimate(
        float(leg["price_regular_pln"]),
        float(leg["resident_fare_multiplier"]),
        float(leg["resident_nondiscountable_fees_eur"]),
        float(leg["resident_estimate_exchange_rate_eur_pln"]),
    )
    if (float(leg["price_resident_estimated_pln"]) != expected or
            float(leg["resident_nondiscountable_fees_pln"]) != fees_pln):
        raise RuntimeError("Nieprawidłowy szacunek ceny rezydenta")
