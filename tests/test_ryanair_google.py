from datetime import date
import json
import unittest

from scripts.collect_step1 import AIRPORT_TIMEZONES
from scripts.ryanair_google import parse_google_flights_response


DAY = date(2026, 10, 25)


def html_for(payload):
    return (
        '<script class="ds:1">data:' + json.dumps(payload)
        + ', extraData:{"commas":[1,2]}, sideChannel:{}</script>'
    )


def offer(origin, destination, departure_clock, arrival_day, arrival_clock, number, price, marketing="FR"):
    segment = [None] * 23
    segment[3] = origin
    segment[6] = destination
    segment[8] = departure_clock
    segment[10] = arrival_clock
    segment[20] = [DAY.year, DAY.month, DAY.day]
    segment[21] = [arrival_day.year, arrival_day.month, arrival_day.day]
    segment[22] = [marketing, number]
    return [[None, None, [segment]], [[None, price]]]


class RyanairGoogleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        AIRPORT_TIMEZONES.update({"WMI": "Europe/Warsaw", "TFS": "Atlantic/Canary", "EDI": "Europe/London"})

    def test_keeps_individual_prices_and_overnight_arrival(self):
        payload = [None, None, None, [[
            offer("WMI", "TFS", [6, 15], DAY, [10, 45], "6121", 219),
            offer("WMI", "TFS", [22], date(2026, 10, 26), [2, 25], "FR6123", 811),
        ]]]
        rows = parse_google_flights_response(html_for(payload), "WMI", "TFS", DAY)
        self.assertEqual(["FR6121", "FR6123"], [row["flight_number"] for row in rows])
        self.assertEqual([219.0, 811.0], [row["price_regular_pln"] for row in rows])
        self.assertIn("dateOut=2026-10-25", rows[0]["booking_url"])

    def test_keeps_ryanair_uk_rk_code(self):
        payload = [None, None, None, [[
            offer("EDI", "TFS", [5, 55], DAY, [10, 45], "2969", 542, marketing="RK"),
        ]]]
        rows = parse_google_flights_response(html_for(payload), "EDI", "TFS", DAY)
        self.assertEqual("RK2969", rows[0]["flight_number"])

    def test_missing_individual_price_fails_closed(self):
        payload = [None, None, None, [[
            offer("WMI", "TFS", [6], DAY, [10], "6121", None),
        ]]]
        with self.assertRaisesRegex(RuntimeError, "without a usable price"):
            parse_google_flights_response(html_for(payload), "WMI", "TFS", DAY)

    def test_valid_empty_day_is_allowed(self):
        self.assertEqual([], parse_google_flights_response(
            html_for([None, None, None, None]), "WMI", "TFS", DAY,
        ))


if __name__ == "__main__":
    unittest.main()
