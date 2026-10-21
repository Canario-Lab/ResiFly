import unittest
from datetime import date
from unittest.mock import patch

from scripts.collect_step5 import (
    VARIANT_A,
    VARIANT_B,
    build_connections,
    collect_full_calendars,
    route_matrix,
    validate_document,
)


def leg(carrier, number, origin, departure, destination, arrival, regular, club=None):
    value = {
        "carrier": carrier,
        "flight_number": number,
        "departure_airport": origin,
        "departure_at": departure,
        "arrival_airport": destination,
        "arrival_at": arrival,
        "price_regular_pln": regular,
        "price_resident_estimated_pln": regular,
        "resident_discount_eligible": False,
        "resident_fare_multiplier": 1.0,
        "booking_url": f"https://example.com/{carrier}/{number}",
    }
    if carrier == "Wizz Air":
        value["price_wizz_discount_club_pln"] = club
    return value


def allowlist():
    return {
        "resident_discount_on_tenerife_leg": {
            "eligible_fare_multiplier": 0.25,
            "ineligible_fare_multiplier": 1.0,
            "variant_a": {
                "eligible_transfer_airports": ["AGP"],
                "ineligible_transfer_airports": [],
            },
            "variant_b": {
                "eligible_transfer_airports": [],
                "ineligible_transfer_airports": ["BUD"],
            },
        },
        "variants": {
            VARIANT_A: {
                "label": "A",
                "tenerife_leg_airline": "Ryanair",
                "poland_leg_airline": "Wizz Air",
                "airports": [{
                    "iata": "AGP",
                    "tenerife_airports": ["TFS"],
                    "polish_airports": ["WAW"],
                }],
            },
            VARIANT_B: {
                "label": "B",
                "tenerife_leg_airline": "Wizz Air",
                "poland_leg_airline": "Ryanair",
                "airports": [{
                    "iata": "BUD",
                    "tenerife_airports": ["TFS"],
                    "polish_airports": ["KRK"],
                }],
            },
        },
    }


class Step5CollectorTests(unittest.TestCase):
    @patch("scripts.collect_step5.collect_wizz_routes", return_value=[])
    @patch("scripts.collect_step5.collect_ryanair_routes", return_value=[])
    def test_both_carriers_receive_the_same_full_calendar_window(
        self,
        collect_ryanair,
        collect_wizz,
    ):
        routes = route_matrix(allowlist())
        start = date(2026, 10, 21)
        end = date(2026, 11, 20)
        collect_full_calendars(routes, start, end, {}, "test-version", 3)
        collect_ryanair.assert_called_once_with(
            routes["Ryanair"], start, end, {}, "test-version", 3
        )
        collect_wizz.assert_called_once_with(
            routes["Wizz Air"], start, end, {}, 3
        )

    def test_route_matrix_assigns_airlines_by_variant_and_both_directions(self):
        routes = route_matrix(allowlist())
        self.assertEqual(set(routes["Ryanair"]), {
            ("TFS", "AGP"), ("AGP", "TFS"),
            ("KRK", "BUD"), ("BUD", "KRK"),
        })
        self.assertEqual(set(routes["Wizz Air"]), {
            ("WAW", "AGP"), ("AGP", "WAW"),
            ("TFS", "BUD"), ("BUD", "TFS"),
        })

    def test_both_variants_both_directions_prices_and_carriers(self):
        legs = [
            leg("Ryanair", "FR1", "TFS", "2026-11-01T08:00:00+00:00", "AGP", "2026-11-01T12:00:00+01:00", 400),
            leg("Wizz Air", "W61", "AGP", "2026-11-01T15:00:00+01:00", "WAW", "2026-11-01T19:00:00+01:00", 600, 500),
            leg("Wizz Air", "W62", "WAW", "2026-11-02T06:00:00+01:00", "AGP", "2026-11-02T10:00:00+01:00", 700, 550),
            leg("Ryanair", "FR2", "AGP", "2026-11-02T13:00:00+01:00", "TFS", "2026-11-02T15:00:00+00:00", 500),
            leg("Wizz Air", "W63", "TFS", "2026-11-03T08:00:00+00:00", "BUD", "2026-11-03T14:00:00+01:00", 800, 650),
            leg("Ryanair", "FR3", "BUD", "2026-11-03T17:00:00+01:00", "KRK", "2026-11-03T18:15:00+01:00", 300),
            leg("Ryanair", "FR4", "KRK", "2026-11-04T07:00:00+01:00", "BUD", "2026-11-04T08:15:00+01:00", 350),
            leg("Wizz Air", "W64", "BUD", "2026-11-04T11:00:00+01:00", "TFS", "2026-11-04T15:00:00+00:00", 900, 700),
        ]
        results = build_connections(legs, allowlist())
        self.assertEqual(len(results), 4)
        self.assertEqual({result["variant"] for result in results}, {VARIANT_A, VARIANT_B})
        self.assertEqual({result["direction"] for result in results}, {
            "tenerife_to_poland", "poland_to_tenerife",
        })
        variant_a = [result for result in results if result["variant"] == VARIANT_A]
        self.assertEqual({result["price_total_regular_pln"] for result in variant_a}, {1000, 1200})
        self.assertEqual({result["price_total_resident_estimated_pln"] for result in variant_a}, {700, 825})
        self.assertEqual({result["price_total_wizz_discount_club_pln"] for result in variant_a}, {900, 1050})
        for result in variant_a:
            tenerife_leg = next(
                item for item in result["legs"]
                if "TFS" in {item["departure_airport"], item["arrival_airport"]}
            )
            self.assertEqual(tenerife_leg["carrier"], "Ryanair")
            self.assertTrue(tenerife_leg["resident_discount_eligible"])
        for result in results:
            self.assertGreater(result["price_total_regular_pln"], 999)
        validate_document({"results": results}, allowlist())

    def test_rejects_layovers_outside_two_to_twenty_four_hours(self):
        legs = [
            leg("Ryanair", "FR1", "TFS", "2026-11-01T08:00:00+00:00", "AGP", "2026-11-01T12:00:00+01:00", 400),
            leg("Wizz Air", "W61", "AGP", "2026-11-01T13:59:00+01:00", "WAW", "2026-11-01T18:00:00+01:00", 600, 500),
        ]
        self.assertEqual(build_connections(legs, allowlist()), [])


if __name__ == "__main__":
    unittest.main()
