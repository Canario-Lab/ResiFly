import unittest

from scripts.collect_step4 import (
    WIZZ_FLIGHT_NUMBERS_BY_TIME,
    WIZZ_ROUTE_SCHEDULES,
    build_connections,
    route_matrix,
    validate_document,
)


def leg(number, origin, departure, destination, arrival, regular, club):
    return {
        "carrier": "Wizz Air",
        "flight_number": number,
        "departure_airport": origin,
        "departure_at": departure,
        "arrival_airport": destination,
        "arrival_at": arrival,
        "price_regular_pln": regular,
        "price_wizz_discount_club_pln": club,
        "price_resident_estimated_pln": regular,
        "resident_discount_eligible": False,
        "resident_fare_multiplier": 1.0,
        "booking_url": "https://www.wizzair.com/example",
    }


def allowlist():
    return {
        "resident_discount_on_tenerife_leg": {
            "eligible_transfer_airports": ["SCQ"],
            "eligible_fare_multiplier": 0.25,
            "ineligible_fare_multiplier": 1.0,
        },
        "airports": [
            {
                "iata": "SCQ",
                "tenerife_airports": ["TFN"],
                "polish_airports": ["WMI"],
            },
            {
                "iata": "BUD",
                "tenerife_airports": ["TFS"],
                "polish_airports": ["WAW"],
            },
        ],
    }


class Step4CollectorTests(unittest.TestCase):
    def test_wizz_schedule_metadata_is_loaded_from_json(self):
        self.assertEqual(WIZZ_ROUTE_SCHEDULES[("TFS", "BUD")], ("W62494", 305))
        self.assertEqual(
            WIZZ_FLIGHT_NUMBERS_BY_TIME[("WAW", "CRL", "17:30")],
            "W61383",
        )

    def test_route_matrix_comes_only_from_allowlist(self):
        routes = route_matrix(allowlist())
        self.assertEqual(len(routes), 8)
        self.assertIn(("TFN", "SCQ"), routes)
        self.assertIn(("SCQ", "WMI"), routes)
        self.assertNotIn(("TFS", "FCO"), routes)

    def test_both_directions_discount_only_tenerife_leg_and_keep_high_prices(self):
        legs = [
            leg("W47466", "TFN", "2026-12-17T08:00:00+00:00", "SCQ", "2026-12-17T11:55:00+01:00", 1200, 1100),
            leg("W61408", "SCQ", "2026-12-17T15:00:00+01:00", "WMI", "2026-12-17T18:40:00+01:00", 900, 800),
            leg("W61407", "WMI", "2026-12-18T05:45:00+01:00", "SCQ", "2026-12-18T09:35:00+01:00", 1000, 850),
            leg("W47465", "SCQ", "2026-12-18T12:00:00+01:00", "TFN", "2026-12-18T13:40:00+00:00", 1400, 1200),
        ]
        results = build_connections(legs, allowlist())
        self.assertEqual(len(results), 2)
        self.assertEqual({result["direction"] for result in results}, {
            "tenerife_to_poland", "poland_to_tenerife",
        })
        self.assertEqual({result["price_total_regular_pln"] for result in results}, {2100, 2400})
        self.assertEqual({result["price_total_resident_estimated_pln"] for result in results}, {1200, 1350})
        self.assertEqual({result["price_total_wizz_discount_club_pln"] for result in results}, {1900, 2050})
        for result in results:
            tenerife_legs = [
                item for item in result["legs"]
                if "TFN" in {item["departure_airport"], item["arrival_airport"]}
            ]
            self.assertEqual(len(tenerife_legs), 1)
            self.assertTrue(tenerife_legs[0]["resident_discount_eligible"])
        validate_document({"results": results}, allowlist())

    def test_ineligible_transfer_keeps_regular_price(self):
        legs = [
            leg("W62494", "TFS", "2026-11-03T08:00:00+00:00", "BUD", "2026-11-03T14:05:00+01:00", 800, 700),
            leg("W62467", "BUD", "2026-11-03T17:00:00+01:00", "WAW", "2026-11-03T18:15:00+01:00", 500, 450),
        ]
        result = build_connections(legs, allowlist())[0]
        self.assertEqual(result["price_total_regular_pln"], 1300)
        self.assertEqual(result["price_total_resident_estimated_pln"], 1300)
        self.assertEqual(result["price_total_wizz_discount_club_pln"], 1150)
        self.assertTrue(all(not item["resident_discount_eligible"] for item in result["legs"]))


if __name__ == "__main__":
    unittest.main()
