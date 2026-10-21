#!/usr/bin/env python3
"""Regenerate deterministic booking links in existing public result feeds."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.booking_urls import (
    air_europa_booking_url,
    iberia_booking_url,
    ryanair_booking_url,
    volotea_booking_url,
    vueling_booking_url,
    wizz_booking_url,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILES = tuple(sorted((ROOT / "data").glob("step*-results.json")))


def booking_url_for_leg(leg: dict[str, Any]) -> str | None:
    departure = datetime.fromisoformat(leg["departure_at"])
    origin = leg["departure_airport"]
    destination = leg["arrival_airport"]
    if leg.get("carrier") == "Ryanair":
        return ryanair_booking_url(origin, destination, departure)
    if leg.get("carrier") == "Wizz Air":
        return wizz_booking_url(origin, destination, departure)
    if leg.get("carrier") in {"Iberia", "Iberia Express"}:
        return iberia_booking_url(origin, destination, departure)
    if leg.get("carrier") == "Vueling":
        return vueling_booking_url(origin, destination, departure)
    if leg.get("carrier") == "Air Europa":
        return air_europa_booking_url(origin, destination, departure)
    if leg.get("carrier") == "Volotea":
        return volotea_booking_url(origin, destination, departure)
    return None


def refresh_document(document: dict[str, Any]) -> int:
    changed = 0
    for result in document.get("results", []):
        for leg in result.get("legs", []):
            expected = booking_url_for_leg(leg)
            if expected is not None and leg.get("booking_url") != expected:
                leg["booking_url"] = expected
                changed += 1
    return changed


def refresh_file(path: Path) -> int:
    document = json.loads(path.read_text(encoding="utf-8"))
    changed = refresh_document(document)
    if changed:
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, default=DEFAULT_FILES)
    args = parser.parse_args()
    for path in args.files:
        print(f"{path}: {refresh_file(path)} updated links")


if __name__ == "__main__":
    main()
