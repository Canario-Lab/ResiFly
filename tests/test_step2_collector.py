import unittest
from datetime import date, timedelta

from scripts.collect_step2 import build_results, ryanair_windows, validate_document


def leg(carrier, number, origin, destination, regular):
    return {
        "carrier": carrier,
        "flight_number": number,
        "departure_airport": origin,
        "departure_at": "2026-11-01T10:00:00+01:00",
        "arrival_airport": destination,
        "arrival_at": "2026-11-01T15:30:00+00:00",
        "price_regular_pln": regular,
        "resident_discount_eligible": False,
        "price_resident_estimated_pln": regular,
        "booking_url": "https://example.com/booking",
    }


class Step2CollectorTests(unittest.TestCase):
    def test_ryanair_windows_cover_all_active_dates(self):
        start = date(2026, 10, 20)
        end = start + timedelta(days=30)
        active = [start + timedelta(days=offset) for offset in (0, 1, 6, 7, 13, 30)]
        centers = ryanair_windows(active, start, end)

        for active_date in active:
            self.assertTrue(any(
                center - timedelta(days=2) <= active_date <= center + timedelta(days=4)
                for center in centers
            ))

    def test_keeps_expensive_direct_flight(self):
        results = build_results([leg("Wizz Air", "W61495", "WAW", "TFS", 1820.50)])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["price_total_regular_pln"], 1820.50)

    def test_both_directions_validate(self):
        results = build_results([
            leg("Wizz Air", "W61495", "WAW", "TFS", 829),
            leg("Ryanair", "FR6122", "TFS", "WMI", 399),
        ])
        document = {"results": results}
        validate_document(document)
        self.assertEqual({result["direction"] for result in results}, {
            "poland_to_tenerife",
            "tenerife_to_poland",
        })
        self.assertTrue(all(result["connection_type"] == "direct" for result in results))


if __name__ == "__main__":
    unittest.main()
