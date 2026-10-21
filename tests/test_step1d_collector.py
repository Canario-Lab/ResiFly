import json
from datetime import date
from pathlib import Path
import unittest

from scripts.collect_step1 import CurrencyRate, configure_airports_from_allowlist
from scripts.collect_step1d import (
    air_europa_route_days,
    build_connections,
    collect_air_europa_legs,
    extract_sputnik_config,
    low_cost_route_matrix,
    parse_air_europa_fares,
    scheduled_departures,
    validate_allowlist,
    validate_document,
)


ROOT = Path(__file__).resolve().parents[1]


def low_cost_leg(origin, departure, destination, arrival, price=250.0):
    return {
        "carrier": "Wizz Air",
        "flight_number": "W60000",
        "departure_airport": origin,
        "departure_at": departure,
        "arrival_airport": destination,
        "arrival_at": arrival,
        "price_regular_pln": price,
        "price_resident_estimated_pln": price,
        "resident_discount_eligible": False,
        "booking_url": "https://www.wizzair.com/example",
    }


def air_europa_leg(origin, departure, destination, arrival, regular=800.0):
    return {
        "carrier": "Air Europa",
        "flight_number": "UX",
        "departure_airport": origin,
        "departure_at": departure,
        "arrival_airport": destination,
        "arrival_at": arrival,
        "price_regular_pln": regular,
        "price_resident_estimated_pln": regular * 0.25,
        "resident_discount_eligible": True,
        "resident_fare_multiplier": 0.25,
        "booking_url": "https://www.aireuropa.com/es/es/deeplink?example=1",
        "price_source": "Air Europa official branded fare feed",
    }


class FakeFareClient:
    def search(self, origin, destination, start, end):
        return [{
            "outboundFlight": {
                "departureAirportIataCode": origin,
                "arrivalAirportIataCode": destination,
                "departureDate": "2026-10-29",
            },
            "airline": {"iataCode": "UX"},
            "priceSpecification": {
                "totalPrice": 100,
                "currencyCode": "EUR",
            },
        }]


class Step1DCollectorTests(unittest.TestCase):
    def setUp(self):
        self.allowlist = json.loads(
            (ROOT / "data" / "air-europa-transfer-airports.json").read_text(
                encoding="utf-8"
            )
        )
        validate_allowlist(self.allowlist)
        configure_airports_from_allowlist(self.allowlist)

    def test_allowlist_contains_only_verified_discount_routes(self):
        self.assertEqual(
            [airport["iata"] for airport in self.allowlist["airports"]],
            ["MAD", "BIO"],
        )
        for airport in self.allowlist["airports"]:
            self.assertEqual(airport["tenerife_airports"], ["TFN"])
            self.assertTrue(
                airport["resident_discount_eligible_on_air_europa_leg"]
            )
            self.assertEqual(
                airport["air_europa_resident_fare_multiplier"], 0.25
            )

    def test_route_matrix_uses_only_saved_low_cost_pairs(self):
        routes = set(low_cost_route_matrix(self.allowlist))
        self.assertIn(("Wizz Air", "MAD", "WAW"), routes)
        self.assertIn(("Ryanair", "KRK", "MAD"), routes)
        self.assertIn(("Wizz Air", "BIO", "KRK"), routes)
        self.assertNotIn(("Ryanair", "BIO", "WAW"), routes)

    def test_route_days_cover_every_day_in_both_directions(self):
        start = date(2026, 10, 21)
        end = date(2026, 11, 20)
        route_days = air_europa_route_days(self.allowlist, start, end)
        route_pairs = sum(
            len(airport["tenerife_airports"])
            for airport in self.allowlist["airports"]
        )
        self.assertEqual(len(route_days), route_pairs * 2 * 31)
        for day in (start, date(2026, 11, 5), end):
            self.assertIn(("TFN", "MAD", day), route_days)
            self.assertIn(("MAD", "TFN", day), route_days)

    def test_extracts_dynamic_key_from_official_page_config(self):
        next_data = {
            "props": {"servicesConfig": {"sputnikSearch": {"config": {
                "endpoint": "https://example.test/%%tenantCode%%/search",
                "axiosConfig": {"headers": {"EM-API-Key": "temporary"}},
            }}}}
        }
        html = (
            '<script id="__NEXT_DATA__" type="application/json">'
            + json.dumps(next_data)
            + "</script>"
        )
        endpoint, headers = extract_sputnik_config(html, "ux")
        self.assertEqual(endpoint, "https://example.test/ux/search")
        self.assertEqual(headers["EM-API-Key"], "temporary")

    def test_parses_only_direct_air_europa_fares_and_keeps_lowest(self):
        def fare(code, amount, destination="MAD"):
            return {
                "outboundFlight": {
                    "departureAirportIataCode": "TFN",
                    "arrivalAirportIataCode": destination,
                    "departureDate": "2026-10-29",
                },
                "airline": {"iataCode": code},
                "priceSpecification": {
                    "totalPrice": amount,
                    "currencyCode": "EUR",
                },
            }

        fares = parse_air_europa_fares(
            [fare("UX", 120), fare("UX", 92.91), fare("IB", 50), fare("UX", 20, "BIO")],
            "TFN",
            "MAD",
        )
        self.assertEqual(len(fares), 1)
        amount, currency = fares[next(iter(fares))]
        self.assertEqual(amount, 92.91)
        self.assertEqual(currency, "EUR")

    def test_expands_official_route_day_fare_over_saved_schedule(self):
        candidates = {("TFN", "MAD", date(2026, 10, 29))}
        legs = collect_air_europa_legs(
            candidates,
            self.allowlist,
            {"EUR": CurrencyRate("EUR", 4.0)},
            FakeFareClient(),
        )
        self.assertEqual(len(legs), 3)
        self.assertEqual(legs[0]["departure_at"][11:16], "07:05")
        self.assertEqual(legs[0]["price_regular_pln"], 400.0)
        self.assertEqual(legs[0]["price_resident_estimated_pln"], 100.0)
        self.assertEqual(
            legs[0]["price_source"], "Air Europa official branded fare feed"
        )
        self.assertEqual(legs[0]["price_scope"], "lowest_official_route_day_fare")

    def test_bilbao_schedule_is_tuesday_and_thursday(self):
        self.assertEqual(len(scheduled_departures(self.allowlist, "TFN", "BIO", date(2026, 10, 27))), 1)
        self.assertEqual(len(scheduled_departures(self.allowlist, "TFN", "BIO", date(2026, 10, 28))), 0)

    def test_builds_both_directions_without_price_limit(self):
        out = build_connections(
            [
                low_cost_leg("MAD", "2026-10-29T14:00:00+01:00", "WAW", "2026-10-29T17:00:00+01:00", 500),
                low_cost_leg("WAW", "2026-10-30T06:00:00+01:00", "MAD", "2026-10-30T09:30:00+01:00", 600),
            ],
            [
                air_europa_leg("TFN", "2026-10-29T07:05:00+00:00", "MAD", "2026-10-29T10:50:00+01:00", 1000),
                air_europa_leg("MAD", "2026-10-30T15:00:00+01:00", "TFN", "2026-10-30T16:55:00+00:00", 1200),
            ],
        )
        self.assertEqual(len(out), 2)
        self.assertEqual(
            {item["direction"] for item in out},
            {"tenerife_to_poland", "poland_to_tenerife"},
        )
        self.assertEqual(
            {item["price_total_regular_pln"] for item in out},
            {1500.0, 1800.0},
        )
        validate_document({"results": out})


if __name__ == "__main__":
    unittest.main()
