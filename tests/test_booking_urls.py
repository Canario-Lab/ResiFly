import unittest
from datetime import datetime, timezone

from scripts.booking_urls import ryanair_booking_url, wizz_booking_url


class WizzBookingUrlTests(unittest.TestCase):
    def test_builds_reusable_one_way_url(self):
        self.assertEqual(
            wizz_booking_url("MAD", "WAW", "2026-11-17T19:15:00+01:00"),
            "https://www.wizzair.com/en-gb/booking/select-flight/"
            "MAD/WAW/2026-11-17/null/1/0/0/null",
        )

    def test_accepts_datetime_and_normalizes_airports(self):
        self.assertEqual(
            wizz_booking_url(
                "fue",
                "waw",
                datetime(2026, 10, 27, 16, 45, tzinfo=timezone.utc),
            ),
            "https://www.wizzair.com/en-gb/booking/select-flight/"
            "FUE/WAW/2026-10-27/null/1/0/0/null",
        )

    def test_rejects_invalid_airport_code(self):
        with self.assertRaises(ValueError):
            wizz_booking_url("Madrid", "WAW", "2026-11-17")


class RyanairBookingUrlTests(unittest.TestCase):
    def test_builds_reusable_one_way_url(self):
        url = ryanair_booking_url("wmi", "tfs", "2026-11-18")
        self.assertTrue(url.startswith("https://www.ryanair.com/pl/pl/trip/flights/select?"))
        self.assertIn("dateOut=2026-11-18", url)
        self.assertIn("originIata=WMI", url)
        self.assertIn("destinationIata=TFS", url)
        self.assertNotIn("token", url.lower())


if __name__ == "__main__":
    unittest.main()

