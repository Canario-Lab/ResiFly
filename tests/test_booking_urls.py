import unittest
from datetime import datetime, timezone

from scripts.booking_urls import (
    air_europa_booking_url,
    iberia_booking_url,
    ryanair_booking_url,
    vueling_booking_url,
    wizz_booking_url,
)


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


class IberiaBookingUrlTests(unittest.TestCase):
    def test_builds_stable_canary_resident_search_url(self):
        url = iberia_booking_url("tfn", "mad", "2026-11-03T08:30:00+00:00")
        self.assertTrue(url.startswith("https://www.iberia.com/flights/?"))
        self.assertIn("BEGIN_CITY_01=TFN", url)
        self.assertIn("END_CITY_01=MAD", url)
        self.assertIn("BEGIN_DAY_01=03", url)
        self.assertIn("BEGIN_MONTH_01=202611", url)
        self.assertIn("residentCode=RC", url)
        self.assertNotIn("token", url.lower())
        self.assertTrue(url.endswith("#!/availability"))


class VuelingBookingUrlTests(unittest.TestCase):
    def test_builds_documented_resident_deeplink_without_session_data(self):
        url = vueling_booking_url("tfn", "bcn", "2026-11-03T08:30:00+00:00")
        self.assertTrue(url.startswith("https://tickets.vueling.com/booking?"))
        self.assertIn("o=TFN", url)
        self.assertIn("d=BCN", url)
        self.assertIn("dd=2026-11-03", url)
        self.assertIn("dt=1", url)
        self.assertIn("adt=1", url)
        self.assertIn("c=es-ES", url)
        self.assertNotIn("token", url.lower())


class AirEuropaBookingUrlTests(unittest.TestCase):
    def test_builds_official_deeplink_without_session_data(self):
        url = air_europa_booking_url("tfn", "mad", "2026-10-29T07:05:00+00:00")
        self.assertTrue(url.startswith("https://www.aireuropa.com/es/es/deeplink?"))
        self.assertIn("departure_airport=TFN", url)
        self.assertIn("arrival_airport=MAD", url)
        self.assertIn("departure_date=20261029", url)
        self.assertIn("adults=1", url)
        self.assertIn("trip_type=O", url)
        self.assertNotIn("token", url.lower())


if __name__ == "__main__":
    unittest.main()

