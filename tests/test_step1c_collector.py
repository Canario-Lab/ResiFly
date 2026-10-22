import json
from datetime import date
from pathlib import Path
import unittest

from scripts.collect_step1 import configure_airports_from_allowlist
from scripts.collect_step1c import (
    build_connections,
    low_cost_route_matrix,
    parse_google_flights_response,
    validate_allowlist,
    validate_document,
    vueling_route_days,
)
from scripts.spanish_resident_fees import apply_resident_price_estimate


ROOT = Path(__file__).resolve().parents[1]


def low_cost_leg(origin, departure, destination, arrival, price=250.0):
    return {
        "carrier": "Ryanair",
        "flight_number": "FR1234",
        "departure_airport": origin,
        "departure_at": departure,
        "arrival_airport": destination,
        "arrival_at": arrival,
        "price_regular_pln": price,
        "price_resident_estimated_pln": price,
        "resident_discount_eligible": False,
        "booking_url": "https://www.ryanair.com/example",
    }


def vueling_leg(origin, departure, destination, arrival, regular=800.0):
    leg = {
        "carrier": "Vueling",
        "flight_number": "VY3210",
        "departure_airport": origin,
        "departure_at": departure,
        "arrival_airport": destination,
        "arrival_at": arrival,
        "price_regular_pln": regular,
        "resident_discount_eligible": True,
        "resident_fare_multiplier": 0.25,
        "booking_url": "https://tickets.vueling.com/booking?example=1",
    }
    apply_resident_price_estimate(leg, 4.0)
    return leg


class Step1CCollectorTests(unittest.TestCase):
    def setUp(self):
        self.allowlist = json.loads(
            (ROOT / "data" / "vueling-transfer-airports.json").read_text(
                encoding="utf-8"
            )
        )
        validate_allowlist(self.allowlist)
        configure_airports_from_allowlist(self.allowlist)

    def test_allowlist_contains_only_discount_eligible_vueling_transfers(self):
        self.assertEqual(
            [airport["iata"] for airport in self.allowlist["airports"]],
            ["ALC", "BCN", "BIO", "AGP", "SCQ", "SVQ", "VLC"],
        )
        for airport in self.allowlist["airports"]:
            self.assertEqual(airport["tenerife_airports"], ["TFN"])
            self.assertTrue(
                airport["resident_discount_eligible_on_vueling_leg"]
            )
            self.assertEqual(airport["vueling_resident_fare_multiplier"], 0.25)

    def test_route_matrix_uses_saved_carrier_routes(self):
        routes = set(low_cost_route_matrix(self.allowlist))
        self.assertIn(("Wizz Air", "BCN", "WAW"), routes)
        self.assertIn(("Ryanair", "WMI", "ALC"), routes)
        self.assertNotIn(("Ryanair", "BIO", "WAW"), routes)

    def test_route_days_cover_every_day_in_both_directions(self):
        start = date(2026, 10, 21)
        end = date(2026, 11, 20)
        route_days = vueling_route_days(self.allowlist, start, end)
        route_pairs = sum(
            len(airport["tenerife_airports"])
            for airport in self.allowlist["airports"]
        )
        self.assertEqual(len(route_days), route_pairs * 2 * 31)
        for day in (start, date(2026, 11, 5), end):
            self.assertIn(("TFN", "BCN", day), route_days)
            self.assertIn(("BCN", "TFN", day), route_days)

    @staticmethod
    def google_html(*offers):
        payload = [None] * 8
        payload[3] = [list(offers)]
        return (
            '<html><script class="ds:1">AF_initDataCallback({data:'
            + json.dumps(payload)
            + ', sideChannel: {}});</script></html>'
        )

    @staticmethod
    def google_offer(code, number, price):
        segment = [None] * 23
        segment[2] = "Vueling"
        segment[3] = "TFN"
        segment[6] = "BCN"
        segment[8] = [10, 0]
        segment[10] = [14, 10]
        segment[20] = [2026, 11, 3]
        segment[21] = [2026, 11, 3]
        segment[22] = [code, number, None, "Vueling"]
        return [[code, ["Vueling"], [segment]], [[None, price]]]

    def test_parses_only_vueling_and_applies_resident_estimate(self):
        html = self.google_html(
            self.google_offer("IB", "1574", 400),
            self.google_offer("VY", "3210", 360),
        )
        legs = parse_google_flights_response(
            html,
            "TFN",
            "BCN",
            0.25,
            4.0,
            {"VY"},
        )
        self.assertEqual(len(legs), 1)
        self.assertEqual(legs[0]["carrier"], "Vueling")
        self.assertEqual(legs[0]["flight_number"], "VY3210")
        self.assertEqual(legs[0]["price_regular_pln"], 360.0)
        self.assertEqual(legs[0]["price_resident_estimated_pln"], 116.73)
        self.assertEqual(legs[0]["price_source"], "Google Flights")
        self.assertIn("tickets.vueling.com/booking", legs[0]["booking_url"])
        self.assertIn("dt=1", legs[0]["booking_url"])

    def test_builds_both_directions_without_price_limit(self):
        tenerife_to_transfer = vueling_leg(
            "TFN",
            "2026-11-03T08:00:00+00:00",
            "BCN",
            "2026-11-03T12:10:00+01:00",
            regular=900.0,
        )
        transfer_to_poland = low_cost_leg(
            "BCN",
            "2026-11-03T15:00:00+01:00",
            "WAW",
            "2026-11-03T18:05:00+01:00",
            price=400.0,
        )
        poland_to_transfer = low_cost_leg(
            "WAW",
            "2026-11-04T06:00:00+01:00",
            "BCN",
            "2026-11-04T09:05:00+01:00",
            price=450.0,
        )
        transfer_to_tenerife = vueling_leg(
            "BCN",
            "2026-11-04T13:00:00+01:00",
            "TFN",
            "2026-11-04T15:20:00+00:00",
            regular=1000.0,
        )
        results = build_connections(
            [transfer_to_poland, poland_to_transfer],
            [tenerife_to_transfer, transfer_to_tenerife],
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(
            {result["direction"] for result in results},
            {"tenerife_to_poland", "poland_to_tenerife"},
        )
        self.assertEqual(
            {result["price_total_regular_pln"] for result in results},
            {1300.0, 1450.0},
        )
        validate_document({"results": results})


if __name__ == "__main__":
    unittest.main()
