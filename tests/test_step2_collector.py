import unittest
from datetime import date, timedelta
from unittest.mock import Mock, patch

from scripts.collect_step2 import (
    build_results,
    route_matrix,
    ryanair_windows,
    validate_document,
    wizz_timetable,
)


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
    @patch("scripts.collect_step2.time_module.sleep")
    @patch("scripts.collect_step2.requests.post")
    def test_wizz_full_calendar_recovers_from_transient_503(self, post, sleep):
        failure = Mock(status_code=503, text="")
        failure.raise_for_status.side_effect = RuntimeError("HTTP 503")
        success = Mock(status_code=200, text="")
        success.raise_for_status.return_value = None
        success.json.return_value = {
            "outboundFlights": [{
                "departureStation": "NAP",
                "arrivalStation": "KTW",
                "departureDate": "2026-10-25T10:00:00",
                "priceType": "price",
                "price": {"amount": 99, "currencyCode": "EUR"},
            }]
        }
        post.side_effect = [failure, success]

        rows = wizz_timetable(
            "NAP",
            "KTW",
            date(2026, 10, 21),
            date(2026, 11, 20),
            "regular",
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(3)

    def test_route_matrix_covers_every_airport_pair_in_both_directions(self):
        routes = set(route_matrix())
        self.assertEqual(len(routes), 16)
        for polish in ("WAW", "WMI", "KRK", "KTW"):
            for tenerife in ("TFN", "TFS"):
                self.assertIn((polish, tenerife), routes)
                self.assertIn((tenerife, polish), routes)

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
