import json
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo

from scripts.collect_step1 import (
    AIRPORT_TIMEZONES,
    build_connections,
    configure_airports_from_allowlist,
    validate_document,
    wizz_schedules_from_allowlist,
)


ROOT = Path(__file__).resolve().parents[1]


def leg(carrier, number, origin, departure, destination, arrival, regular, resident=None, booking_url=None):
    item = {
        "carrier": carrier,
        "flight_number": number,
        "departure_airport": origin,
        "departure_at": departure,
        "arrival_airport": destination,
        "arrival_at": arrival,
        "price_regular_pln": regular,
        "resident_discount_eligible": carrier == "Binter",
        "price_resident_estimated_pln": resident if resident is not None else regular,
    }
    if booking_url:
        item["booking_url"] = booking_url
    return item


class Step1CollectorTests(unittest.TestCase):
    def test_allowlist_contains_complete_collector_metadata(self):
        allowlist = json.loads(
            (ROOT / "data" / "binter-transfer-airports.json").read_text(
                encoding="utf-8"
            )
        )
        configure_airports_from_allowlist(allowlist)
        for airport in allowlist["airports"]:
            code = airport["iata"]
            self.assertEqual(AIRPORT_TIMEZONES[code], airport["timezone"])
            ZoneInfo(airport["timezone"])
            self.assertIn("resident_discount_eligible_on_binter_leg", airport)
            self.assertIn("binter_resident_fare_multiplier", airport)
        schedules = wizz_schedules_from_allowlist(allowlist)
        self.assertEqual(schedules[("WAW", "MAD")], ("W61471", 230))
        self.assertEqual(schedules[("MAD", "WAW")], ("W61472", 215))

    def test_does_not_filter_expensive_regular_price(self):
        binter = leg(
            "Binter", "NT1", "TFN", "2026-11-01T08:00:00+00:00",
            "MAD", "2026-11-01T12:00:00+01:00", 800, 200,
        )
        wizz = leg(
            "Wizz Air", "W61472", "MAD", "2026-11-01T15:00:00+01:00",
            "WAW", "2026-11-01T18:30:00+01:00", 250,
            booking_url="https://www.wizzair.com/example",
        )
        results = build_connections([wizz], [binter])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["price_total_regular_pln"], 1050)

    def test_both_directions_without_price_limit(self):
        wizz_to_poland = leg(
            "Wizz Air", "W61472", "MAD", "2026-11-01T15:00:00+01:00",
            "WAW", "2026-11-01T18:30:00+01:00", 300,
            booking_url="https://www.wizzair.com/to-poland",
        )
        binter_to_transfer = leg(
            "Binter", "NT1", "TFN", "2026-11-01T08:00:00+00:00",
            "MAD", "2026-11-01T12:00:00+01:00", 650, 162.5,
        )
        wizz_from_poland = leg(
            "Wizz Air", "W61471", "WAW", "2026-11-02T06:00:00+01:00",
            "MAD", "2026-11-02T10:00:00+01:00", 300,
            booking_url="https://www.wizzair.com/from-poland",
        )
        binter_to_tenerife = leg(
            "Binter", "NT2", "MAD", "2026-11-02T13:00:00+01:00",
            "TFN", "2026-11-02T15:00:00+00:00", 699.99, 175,
        )
        results = build_connections(
            [wizz_to_poland, wizz_from_poland],
            [binter_to_transfer, binter_to_tenerife],
        )
        self.assertEqual(len(results), 2)
        self.assertEqual({result["direction"] for result in results}, {
            "tenerife_to_poland", "poland_to_tenerife",
        })

        document = {
            "directions": ["tenerife_to_poland", "poland_to_tenerife"],
            "results": results,
        }
        validate_document(document)


if __name__ == "__main__":
    unittest.main()
