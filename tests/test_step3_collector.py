import unittest

from scripts.collect_step3 import build_connections, route_matrix, validate_document


def leg(number, origin, departure, destination, arrival, regular):
    return {
        "carrier": "Ryanair",
        "flight_number": number,
        "departure_airport": origin,
        "departure_at": departure,
        "arrival_airport": destination,
        "arrival_at": arrival,
        "price_regular_pln": regular,
        "price_resident_estimated_pln": regular,
        "resident_discount_eligible": False,
        "booking_url": "https://www.ryanair.com/example",
    }


def allowlist():
    return {
        "resident_discount_on_tenerife_leg": {
            "eligible_transfer_airports": ["AGP"],
            "eligible_fare_multiplier": 0.25,
            "ineligible_fare_multiplier": 1.0,
        },
        "airports": [
            {
                "iata": "AGP",
                "tenerife_airports": ["TFS"],
                "polish_airports": ["KRK"],
            },
            {
                "iata": "STN",
                "tenerife_airports": ["TFS"],
                "polish_airports": ["WMI"],
            },
        ],
    }


class Step3CollectorTests(unittest.TestCase):
    def test_route_matrix_comes_only_from_allowlist(self):
        routes = route_matrix(allowlist())
        self.assertEqual(len(routes), 8)
        self.assertIn(("TFS", "AGP"), routes)
        self.assertIn(("AGP", "KRK"), routes)
        self.assertNotIn(("TFS", "MAD"), routes)

    def test_both_directions_discount_only_tenerife_leg_and_keep_high_prices(self):
        legs = [
            leg("FR1", "TFS", "2026-11-01T08:00:00+00:00", "AGP", "2026-11-01T11:30:00+01:00", 1200),
            leg("FR2", "AGP", "2026-11-01T14:00:00+01:00", "KRK", "2026-11-01T17:30:00+01:00", 900),
            leg("FR3", "KRK", "2026-11-02T06:00:00+01:00", "AGP", "2026-11-02T09:30:00+01:00", 1000),
            leg("FR4", "AGP", "2026-11-02T12:00:00+01:00", "TFS", "2026-11-02T14:00:00+00:00", 1400),
        ]
        results = build_connections(legs, allowlist())
        self.assertEqual(len(results), 2)
        self.assertEqual({result["direction"] for result in results}, {
            "tenerife_to_poland", "poland_to_tenerife",
        })
        self.assertEqual({result["price_total_regular_pln"] for result in results}, {2100, 2400})
        self.assertEqual({result["price_total_resident_estimated_pln"] for result in results}, {1200, 1350})
        for result in results:
            tenerife_legs = [
                item for item in result["legs"]
                if "TFS" in {item["departure_airport"], item["arrival_airport"]}
            ]
            self.assertEqual(len(tenerife_legs), 1)
            self.assertTrue(tenerife_legs[0]["resident_discount_eligible"])
        validate_document({"results": results}, allowlist())

    def test_ineligible_transfer_keeps_regular_price(self):
        legs = [
            leg("FR5", "TFS", "2026-11-03T08:00:00+00:00", "STN", "2026-11-03T12:20:00+00:00", 800),
            leg("FR6", "STN", "2026-11-03T15:00:00+00:00", "WMI", "2026-11-03T18:20:00+01:00", 500),
        ]
        result = build_connections(legs, allowlist())[0]
        self.assertEqual(result["price_total_regular_pln"], 1300)
        self.assertEqual(result["price_total_resident_estimated_pln"], 1300)
        self.assertTrue(all(not item["resident_discount_eligible"] for item in result["legs"]))


if __name__ == "__main__":
    unittest.main()
