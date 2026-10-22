import json
from datetime import date, timedelta
from pathlib import Path
import unittest

from scripts.collect_step1 import configure_airports_from_allowlist
from scripts.collect_step1b import (
    build_connections,
    iberia_route_days,
    parse_google_flights_response,
    validate_allowlist,
    validate_document,
)
from scripts.spanish_resident_fees import apply_resident_price_estimate


ROOT = Path(__file__).resolve().parents[1]


def low_cost_leg(origin, departure, destination, arrival, price=250.0):
    return {
        "carrier": "Wizz Air",
        "flight_number": "W61472",
        "departure_airport": origin,
        "departure_at": departure,
        "arrival_airport": destination,
        "arrival_at": arrival,
        "price_regular_pln": price,
        "price_resident_estimated_pln": price,
        "resident_discount_eligible": False,
        "booking_url": "https://www.wizzair.com/example",
    }


def iberia_leg(origin, departure, destination, arrival, regular=800.0):
    leg = {
        "carrier": "Iberia Express",
        "flight_number": "IB1574",
        "departure_airport": origin,
        "departure_at": departure,
        "arrival_airport": destination,
        "arrival_at": arrival,
        "price_regular_pln": regular,
        "resident_discount_eligible": True,
        "resident_fare_multiplier": 0.25,
        "booking_url": "https://www.iberia.com/flights/example",
    }
    apply_resident_price_estimate(leg, 4.0)
    return leg


class Step1BCollectorTests(unittest.TestCase):
    def setUp(self):
        self.allowlist = json.loads(
            (ROOT / "data" / "iberia-transfer-airports.json").read_text(
                encoding="utf-8"
            )
        )
        validate_allowlist(self.allowlist)
        configure_airports_from_allowlist(self.allowlist)

    def test_allowlist_contains_only_discount_eligible_madrid(self):
        self.assertEqual(
            [airport["iata"] for airport in self.allowlist["airports"]],
            ["MAD"],
        )
        airport = self.allowlist["airports"][0]
        self.assertTrue(airport["resident_discount_eligible_on_iberia_leg"])
        self.assertEqual(airport["iberia_resident_fare_multiplier"], 0.25)
        self.assertEqual(set(airport["tenerife_airports"]), {"TFN", "TFS"})

    def test_iberia_route_days_cover_full_window_in_both_directions(self):
        start = date(2026, 10, 21)
        end = start + timedelta(days=30)
        route_days = iberia_route_days(self.allowlist, start, end)
        expected_routes = sum(
            len(airport["tenerife_airports"])
            for airport in self.allowlist["airports"]
        )
        self.assertEqual(len(route_days), expected_routes * 2 * 31)
        for day in (start, start + timedelta(days=15), end):
            self.assertIn(("MAD", "TFN", day), route_days)
            self.assertIn(("TFN", "MAD", day), route_days)

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
    def google_offer(code, number, carrier, price):
        segment = [None] * 23
        segment[2] = carrier if code == "IB" else None
        segment[3] = "TFN"
        segment[6] = "MAD"
        segment[8] = [10, 0]
        segment[10] = [13, 45]
        segment[20] = [2026, 11, 3]
        segment[21] = [2026, 11, 3]
        segment[22] = [code, number, None, carrier]
        return [[code, [carrier], [segment]], [[None, price]]]

    def test_parses_cheapest_direct_iberia_offer_and_applies_multiplier(self):
        html = self.google_html(
            self.google_offer("IB", "1574", "Iberia", 450),
            self.google_offer("I2", "1574", "Iberia Express", 430),
        )
        legs = parse_google_flights_response(
            html,
            "TFN",
            "MAD",
            0.25,
            4.0,
            {"IB", "I2"},
        )
        self.assertEqual(len(legs), 1)
        self.assertEqual(legs[0]["carrier"], "Iberia Express")
        self.assertEqual(legs[0]["flight_number"], "I21574")
        self.assertEqual(legs[0]["price_regular_pln"], 430.0)
        self.assertEqual(legs[0]["price_resident_estimated_pln"], 134.23)
        self.assertEqual(legs[0]["price_source"], "Google Flights")
        self.assertIn("residentCode=RC", legs[0]["booking_url"])

    def test_empty_google_result_is_not_an_error(self):
        payload = [None] * 8
        payload[3] = None
        html = (
            '<html><script class="ds:1">AF_initDataCallback({data:'
            + json.dumps(payload)
            + ', sideChannel: {}});</script></html>'
        )
        self.assertEqual(
            parse_google_flights_response(
                html,
                "TFN",
                "MAD",
                0.25,
                4.0,
                {"IB", "I2"},
            ),
            [],
        )

    def test_builds_both_directions_without_price_limit(self):
        tenerife_to_madrid = iberia_leg(
            "TFN",
            "2026-11-03T08:00:00+00:00",
            "MAD",
            "2026-11-03T11:45:00+01:00",
            regular=900.0,
        )
        madrid_to_poland = low_cost_leg(
            "MAD",
            "2026-11-03T15:00:00+01:00",
            "WAW",
            "2026-11-03T18:35:00+01:00",
            price=400.0,
        )
        poland_to_madrid = low_cost_leg(
            "WAW",
            "2026-11-04T06:00:00+01:00",
            "MAD",
            "2026-11-04T10:00:00+01:00",
            price=450.0,
        )
        madrid_to_tenerife = iberia_leg(
            "MAD",
            "2026-11-04T13:00:00+01:00",
            "TFS",
            "2026-11-04T15:00:00+00:00",
            regular=1000.0,
        )
        results = build_connections(
            [madrid_to_poland, poland_to_madrid],
            [tenerife_to_madrid, madrid_to_tenerife],
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
