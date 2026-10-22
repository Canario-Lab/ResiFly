import json
from datetime import date
from pathlib import Path
import unittest
from unittest.mock import Mock

from scripts.collect_step1 import CurrencyRate, configure_airports_from_allowlist
from scripts.collect_step1f import (
    available_days_from_calendar,
    build_connections,
    calendar_month_anchors,
    canaryfly_routes,
    collect_canaryfly_available_days,
    collect_canaryfly_legs,
    low_cost_route_matrix,
    parse_canaryfly_search,
    validate_canaryfly_imports_response,
    validate_allowlist,
    validate_document,
)


ROOT = Path(__file__).resolve().parents[1]


def calendar_payload(origin="TFN", destination="FUE"):
    return {
        "data": {
            "booking_calendar": [{
                "trip": {
                    "origin": {"iata": origin},
                    "destination": {"iata": destination},
                    "date": "2026-10-21T00:00:00+00:00",
                },
                "days": [
                    {
                        "date": "2026-10-21T00:00:00+00:00",
                        "enabled": False,
                    },
                    {
                        "date": "2026-10-22T00:00:00+00:00",
                        "enabled": True,
                    },
                    {
                        "date": "2026-11-01T00:00:00+00:00",
                        "enabled": True,
                    },
                ],
            }]
        }
    }


def search_payload(origin="TFN", destination="FUE", day="2026-10-22"):
    return {
        "data": {
            "booking_search": {
                "availability": [{
                    "trip": {
                        "origin": {"iata": origin},
                        "destination": {"iata": destination},
                        "date": f"{day}T00:00:00+00:00",
                    },
                    "flights": [
                        {
                            "flightSegments": [{
                                "origin": {"iata": origin},
                                "destination": {"iata": destination},
                                "departureTime": f"{day}T14:30:00+00:00",
                                "arrivalTime": f"{day}T15:20:00+00:00",
                                "flightNumber": 374,
                                "line": "PM",
                            }],
                            "flightTime": 50,
                            "fares": [
                                {
                                    "token": "fare-token-yd",
                                    "code": "YD",
                                    "class": "Y",
                                    "seats": None,
                                    "bestPrice": True,
                                    "amounts": {
                                        "resident": {
                                            "totalAmount": 30.5,
                                            "currency": {"code": "EUR"},
                                        },
                                        "noResident": {
                                            "totalAmount": 122,
                                            "currency": {"code": "EUR"},
                                        },
                                    },
                                },
                                {
                                    "token": "fare-token-rd",
                                    "code": "RD",
                                    "class": "R",
                                    "seats": 3,
                                    "amounts": {
                                        "resident": {
                                            "totalAmount": 39.5,
                                            "currency": {"code": "EUR"},
                                        },
                                        "noResident": {
                                            "totalAmount": 158,
                                            "currency": {"code": "EUR"},
                                        },
                                    },
                                },
                            ],
                        },
                        {
                            "flightSegments": [
                                {
                                    "origin": {"iata": origin},
                                    "destination": {"iata": "LPA"},
                                    "departureTime": f"{day}T08:30:00+00:00",
                                    "arrivalTime": f"{day}T09:00:00+00:00",
                                    "flightNumber": 616,
                                    "line": "PM",
                                },
                                {
                                    "origin": {"iata": "LPA"},
                                    "destination": {"iata": destination},
                                    "departureTime": f"{day}T09:30:00+00:00",
                                    "arrivalTime": f"{day}T10:10:00+00:00",
                                    "flightNumber": 805,
                                    "line": "PM",
                                },
                            ],
                            "fares": [],
                        },
                    ],
                }]
            }
        }
    }


def amount(main, total):
    return {
        "mainAmount": main,
        "totalAmount": total,
        "currency": {"code": "EUR"},
    }


def imports_payload():
    return {
        "data": {
            "booking_getImports": {
                "passengerAmounts": [{
                    "fare": amount(122, 30.5),
                    "taxes": amount(2.53, 2.53),
                    "suplements": amount(0, 0),
                    "serviceFee": amount(6, 1.5),
                    "managementFee": amount(0, 0),
                    "passenger": {
                        "typeCode": "ADT",
                        "residentCode": "DC",
                        "isResident": True,
                    },
                }],
            }
        }
    }


def low_cost_leg(origin, departure, destination, arrival, carrier="Wizz Air"):
    return {
        "carrier": carrier,
        "flight_number": "W60000" if carrier == "Wizz Air" else "FR1000",
        "departure_airport": origin,
        "departure_at": departure,
        "arrival_airport": destination,
        "arrival_at": arrival,
        "price_regular_pln": 300.0,
        "price_resident_estimated_pln": 300.0,
        "resident_discount_eligible": False,
        "booking_url": "https://example.com/low-cost",
    }


def canaryfly_leg(origin, departure, destination, arrival):
    return {
        "carrier": "Canaryfly",
        "flight_number": "PM374",
        "departure_airport": origin,
        "departure_at": departure,
        "arrival_airport": destination,
        "arrival_at": arrival,
        "price_regular_pln": 488.0,
        "price_resident_estimated_pln": 122.0,
        "resident_discount_eligible": True,
        "resident_price_is_estimate": False,
        "booking_url": "https://www.canaryfly.es/en/cheap-flights/example",
        "price_source": (
            "Canaryfly official booking_search + booking_getImports GraphQL"
        ),
    }


class FakeClient:
    def calendar(self, origin, destination, anchor):
        return calendar_payload(origin, destination)

    def search(self, origin, destination, day):
        return search_payload(origin, destination, day.isoformat())

    def imports(self, fare_token):
        if fare_token != "fare-token-yd":
            raise AssertionError(f"Unexpected fare token: {fare_token}")
        return imports_payload()


class Step1FCollectorTests(unittest.TestCase):
    def setUp(self):
        self.allowlist = json.loads(
            (ROOT / "data" / "canaryfly-transfer-airports.json").read_text(
                encoding="utf-8"
            )
        )
        validate_allowlist(self.allowlist)
        configure_airports_from_allowlist(self.allowlist)

    def test_allowlist_contains_only_verified_fue_and_lpa_routes(self):
        self.assertEqual(
            [airport["iata"] for airport in self.allowlist["airports"]],
            ["FUE", "LPA"],
        )
        routes = {
            (
                airport["iata"],
                route["polish_airport"],
                tuple(route["airlines"]),
            )
            for airport in self.allowlist["airports"]
            for route in airport["polish_routes"]
        }
        self.assertEqual(routes, {
            ("FUE", "WAW", ("Wizz Air",)),
            ("FUE", "KTW", ("Wizz Air",)),
            ("FUE", "KRK", ("Ryanair",)),
            ("LPA", "KRK", ("Ryanair",)),
        })

    def test_route_matrices_use_only_allowlisted_pairs_in_both_directions(self):
        self.assertEqual(set(canaryfly_routes(self.allowlist)), {
            ("TFN", "FUE"),
            ("FUE", "TFN"),
            ("TFN", "LPA"),
            ("LPA", "TFN"),
        })
        low_cost = set(low_cost_route_matrix(self.allowlist))
        self.assertEqual(len(low_cost), 8)
        self.assertIn(("Wizz Air", "WAW", "FUE"), low_cost)
        self.assertIn(("Ryanair", "LPA", "KRK"), low_cost)

    def test_month_anchors_cover_complete_window_without_day_prefilter(self):
        self.assertEqual(
            calendar_month_anchors(date(2026, 10, 21), date(2026, 11, 20)),
            [date(2026, 10, 21), date(2026, 11, 1)],
        )

    def test_calendar_parser_keeps_every_enabled_day_in_window(self):
        self.assertEqual(
            available_days_from_calendar(
                calendar_payload(),
                "TFN",
                "FUE",
                date(2026, 10, 21),
                date(2026, 11, 20),
            ),
            {date(2026, 10, 22), date(2026, 11, 1)},
        )

    def test_collects_all_saved_route_calendars_before_searching_details(self):
        available = collect_canaryfly_available_days(
            self.allowlist,
            date(2026, 10, 21),
            date(2026, 10, 31),
            2,
            FakeClient(),
        )
        self.assertEqual(len(available), 4)
        for origin, destination in canaryfly_routes(self.allowlist):
            self.assertIn((origin, destination, date(2026, 10, 22)), available)

    def test_parses_direct_schedule_and_exact_official_final_prices(self):
        client = FakeClient()
        legs = parse_canaryfly_search(
            search_payload(),
            "TFN",
            "FUE",
            date(2026, 10, 22),
            0.25,
            {"EUR": CurrencyRate("EUR", 4.0)},
            self.allowlist["fare_feed"],
            client,
        )
        self.assertEqual(len(legs), 1)
        leg = legs[0]
        self.assertEqual(leg["flight_number"], "PM374")
        self.assertEqual(leg["departure_at"], "2026-10-22T14:30:00+01:00")
        self.assertEqual(leg["arrival_at"], "2026-10-22T15:20:00+01:00")
        self.assertEqual(leg["price_regular_pln"], 522.12)
        self.assertEqual(leg["price_resident_estimated_pln"], 138.12)
        self.assertEqual(leg["price_source_amount"], 130.53)
        self.assertEqual(leg["price_source_resident_amount"], 34.53)
        self.assertFalse(leg["resident_price_is_estimate"])
        self.assertEqual(leg["fare_code"], "YD")
        self.assertNotIn("token", leg)
        self.assertTrue(leg["booking_url"].endswith("/2026-10-22"))

    def test_imports_request_uses_canaryfly_dc_resident_code(self):
        from scripts.collect_step1f import CanaryflyClient

        client = CanaryflyClient("https://services.canaryfly.es/graphql/main")
        client._post = Mock(return_value={})
        client.imports("temporary-fare-token")
        query, operation, variables = client._post.call_args.args
        self.assertIn("booking_getImports", query)
        self.assertEqual(operation, "booking_getImports")
        self.assertEqual(variables["itineraries"], [{"token": "temporary-fare-token"}])
        self.assertEqual(
            variables["passengers"],
            [{"type": {"code": "ADT", "discounts": ["DC"]}, "quantity": 1}],
        )

    def test_incomplete_or_nonresident_imports_fail_closed(self):
        incomplete = imports_payload()
        del incomplete["data"]["booking_getImports"]["passengerAmounts"][0]["taxes"]
        with self.assertRaisesRegex(RuntimeError, "brak składnika"):
            validate_canaryfly_imports_response(incomplete, "PM374", "EUR")

        nonresident = imports_payload()
        passenger = nonresident["data"]["booking_getImports"]["passengerAmounts"][0]["passenger"]
        passenger["residentCode"] = "NO"
        passenger["isResident"] = False
        with self.assertRaisesRegex(RuntimeError, "nie potwierdził rezydenta"):
            validate_canaryfly_imports_response(nonresident, "PM374", "EUR")

    def test_available_day_details_are_collected_without_connections(self):
        candidates = {("TFN", "FUE", date(2026, 10, 22))}
        legs = collect_canaryfly_legs(
            candidates,
            self.allowlist,
            {"EUR": CurrencyRate("EUR", 4.0)},
            2,
            FakeClient(),
        )
        self.assertEqual([leg["flight_number"] for leg in legs], ["PM374"])

    def test_builds_both_directions_without_price_limit(self):
        results = build_connections(
            [
                low_cost_leg(
                    "FUE",
                    "2026-10-22T19:00:00+01:00",
                    "WAW",
                    "2026-10-22T23:55:00+02:00",
                ),
                low_cost_leg(
                    "KRK",
                    "2026-10-22T05:00:00+02:00",
                    "FUE",
                    "2026-10-22T09:20:00+01:00",
                    "Ryanair",
                ),
            ],
            [
                canaryfly_leg(
                    "TFN",
                    "2026-10-22T14:30:00+01:00",
                    "FUE",
                    "2026-10-22T15:20:00+01:00",
                ),
                canaryfly_leg(
                    "FUE",
                    "2026-10-22T12:00:00+01:00",
                    "TFN",
                    "2026-10-22T12:50:00+01:00",
                ),
            ],
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(
            {result["direction"] for result in results},
            {"tenerife_to_poland", "poland_to_tenerife"},
        )
        self.assertEqual(
            {result["price_total_regular_pln"] for result in results},
            {788.0},
        )
        validate_document({"results": results})


if __name__ == "__main__":
    unittest.main()
