"""Canonical endpoints shared by collectors and route discovery (no HTTP)."""

import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo


SEARCH_AIRPORTS_FILE = Path(__file__).resolve().parents[1] / "data" / "search-airports.json"
SEARCH_AIRPORTS = json.loads(SEARCH_AIRPORTS_FILE.read_text(encoding="utf-8"))

_rows = SEARCH_AIRPORTS["polish_airports"] + SEARCH_AIRPORTS["tenerife_airports"]
_codes = [row["iata"] for row in _rows]
if len(_codes) != len(set(_codes)) or any(not re.fullmatch(r"[A-Z]{3}", code) for code in _codes):
    raise RuntimeError("Duplicate or invalid endpoint in search-airports.json")
for _row in _rows:
    ZoneInfo(_row["timezone"])

POLISH_AIRPORTS = tuple(row["iata"] for row in SEARCH_AIRPORTS["polish_airports"])
TENERIFE_AIRPORTS = tuple(row["iata"] for row in SEARCH_AIRPORTS["tenerife_airports"])
ENDPOINT_TIMEZONES = {row["iata"]: row["timezone"] for row in _rows}
ENDPOINT_TRANSFER_EXCEPTIONS = {
    (row["step"], row["iata"]): frozenset(row["polish_airports"])
    for row in SEARCH_AIRPORTS.get("endpoint_transfer_exceptions", [])
}


def validate_polish_transfer(polish, transfer, step=""):
    if polish not in POLISH_AIRPORTS or transfer == polish or transfer in TENERIFE_AIRPORTS:
        raise RuntimeError(f"Invalid Poland/transfer pair: {polish}-{transfer}")
    if transfer in POLISH_AIRPORTS and polish not in ENDPOINT_TRANSFER_EXCEPTIONS.get((step, transfer), frozenset()):
        raise RuntimeError(f"Unapproved endpoint-as-transfer role: {step}/{transfer}/{polish}")
