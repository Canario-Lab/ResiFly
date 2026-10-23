import json
from datetime import date
from pathlib import Path
import unittest

from scripts.collect_step1 import CurrencyRate, configure_airports_from_allowlist
from scripts.collect_step1e import (
    build_connections,
    collect_volotea_legs,
    low_cost_route_matrix,
    parse_volotea_response,
    validate_allowlist,
    validate_document,
    volotea_route_days,
)
from scripts.spanish_resident_fees import apply_resident_price_estimate


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


def volotea_leg(origin, departure, destination, arrival, regular=400.0):
    leg = {
        "carrier": "Volotea",
        "flight_number": "V73523",
        "departure_airport": origin,
        "departure_at": departure,
        "arrival_airport": destination,
        "arrival_at": arrival,
        "price_regular_pln": regular,
        "resident_discount_eligible": True,
        "resident_fare_multiplier": 0.25,
        "booking_url": "https://www.volotea.com/es/ofertas-vuelos/tfs/bio/",
        "price_source": "Volotea official MinPrice endpoint",
    }
    apply_resident_price_estimate(leg, 4.0)
    return leg


def fare_payload(
    market="TFS-BIO",
    day="2026-11-15",
    number="3523",
    price=127.47,
    connections=None,
):
    return {
        "Success": True,
        "Content": [{
            "Market": market,
            "Value": [{
                "Market": market,
                "DepartureFlightDate": day,
                "FlightNumber": number,
                "DepartureTime": f"{day}T09:40:00",
                "ArrivalTime": f"{day}T13:50:00",
                "PriceWithFee": price,
                "Taxes": 9.65,
                "ConnectionInformation": connections or [],
            }],
        }],
    }


class FakeFareClient:
    def search(self, origin, destination, day):
        if (origin, destination, day) == ("TFS", "BIO", date(2026, 11, 15)):
            return fare_payload()
        return {"Success": True, "Content": [{"Value": []}]}


class Step1ECollectorTests(unittest.TestCase):
    def setUp(self):
        self.allowlist = json.loads(
            (ROOT / "data" / "volotea-transfer-airports.json").read_text(
                encoding="utf-8"
            )
        )
        validate_allowlist(self.allowlist)
        configure_airports_from_allowlist(self.allowlist)

    def test_allowlist_contains_only_bilbao_and_saved_wizz_routes(self):
        self.assertEqual(
            [airport["iata"] for airport in self.allowlist["airports"]],
            ["BIO"],
        )
        airport = self.allowlist["airports"][0]
        self.assertEqual(airport["tenerife_airports"], ["TFS"])
        self.assertEqual(airport["volotea_resident_fare_multiplier"], 0.25)
        self.assertEqual(
            {(item["polish_airport"], tuple(item["airlines"])) for item in airport["polish_routes"]},
            {("WAW", ("Wizz Air",)), ("KRK", ("Wizz Air",)), ("WRO", ("Wizz Air",))},
        )

    def test_route_matrix_uses_only_saved_pairs_in_both_directions(self):
        routes = set(low_cost_route_matrix(self.allowlist))
        self.assertEqual(routes, {
            ("Wizz Air", "BIO", "KRK"),
            ("Wizz Air", "BIO", "WAW"),
            ("Wizz Air", "KRK", "BIO"),
            ("Wizz Air", "WAW", "BIO"),
            ("Wizz Air", "WRO", "BIO"),
            ("Wizz Air", "BIO", "WRO"),
        })

    def test_parses_official_direct_flight_price_schedule_and_number(self):
        legs = parse_volotea_response(
            fare_payload(),
            "TFS",
            "BIO",
            date(2026, 11, 15),
            0.25,
            {"EUR": CurrencyRate("EUR", 4.0)},
            self.allowlist["fare_feed"],
        )
        self.assertEqual(len(legs), 1)
        leg = legs[0]
        self.assertEqual(leg["flight_number"], "V73523")
        self.assertEqual(leg["departure_at"], "2026-11-15T09:40:00+00:00")
        self.assertEqual(leg["arrival_at"], "2026-11-15T13:50:00+01:00")
        self.assertEqual(leg["price_regular_pln"], 509.88)
        self.assertEqual(leg["price_resident_estimated_pln"], 156.42)
        self.assertIn("departureDate=2026-11-15", leg["booking_url"])
        self.assertEqual(leg["price_source_taxes"], 9.65)

    def test_rejects_wrong_market_wrong_day_and_connections(self):
        config = self.allowlist["fare_feed"]
        rates = {"EUR": CurrencyRate("EUR", 4.0)}
        for payload in (
            fare_payload(market="TFS-OVD"),
            fare_payload(day="2026-11-16"),
            fare_payload(connections=[{"StationCode": "MAD"}]),
        ):
            self.assertEqual(
                parse_volotea_response(
                    payload, "TFS", "BIO", date(2026, 11, 15), 0.25, rates, config
                ),
                [],
            )

    def test_empty_official_day_is_valid_and_other_days_are_kept(self):
        candidates = {
            ("TFS", "BIO", date(2026, 11, 14)),
            ("TFS", "BIO", date(2026, 11, 15)),
        }
        legs = collect_volotea_legs(
            candidates,
            self.allowlist,
            {"EUR": CurrencyRate("EUR", 4.0)},
            2,
            FakeFareClient(),
        )
        self.assertEqual([leg["flight_number"] for leg in legs], ["V73523"])

    def test_route_days_cover_every_day_in_both_directions(self):
        route_days = volotea_route_days(
            self.allowlist,
            date(2026, 10, 21),
            date(2026, 11, 20),
        )
        self.assertEqual(len(route_days), 62)
        for day in (date(2026, 10, 21), date(2026, 11, 15), date(2026, 11, 20)):
            self.assertIn(("TFS", "BIO", day), route_days)
            self.assertIn(("BIO", "TFS", day), route_days)

    def test_uses_airport_timezones_even_when_volotea_offsets_are_wrong(self):
        payload = fare_payload()
        record = payload["Content"][0]["Value"][0]
        record["Market"] = "BIO-TFS"
        record["Taxes"] = 10.48
        record["DepartureTime"] = "2026-11-15T06:45:00+00:00"
        record["ArrivalTime"] = "2026-11-15T09:00:00+01:00"
        legs = parse_volotea_response(
            payload,
            "BIO",
            "TFS",
            date(2026, 11, 15),
            0.25,
            {"EUR": CurrencyRate("EUR", 4.0)},
            self.allowlist["fare_feed"],
        )
        self.assertEqual(legs[0]["departure_at"], "2026-11-15T06:45:00+01:00")
        self.assertEqual(legs[0]["arrival_at"], "2026-11-15T09:00:00+00:00")

    def test_builds_both_directions_without_price_limit(self):
        results = build_connections(
            [
                low_cost_leg(
                    "BIO", "2026-11-15T17:00:00+01:00",
                    "WAW", "2026-11-15T20:10:00+01:00", 900,
                ),
                low_cost_leg(
                    "KRK", "2026-11-15T05:00:00+01:00",
                    "BIO", "2026-11-15T08:20:00+01:00", 800,
                ),
            ],
            [
                volotea_leg(
                    "TFS", "2026-11-15T09:40:00+01:00",
                    "BIO", "2026-11-15T13:50:00+01:00", 400,
                ),
                volotea_leg(
                    "BIO", "2026-11-15T12:00:00+01:00",
                    "TFS", "2026-11-15T14:15:00+00:00", 500,
                ),
            ],
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(
            {item["direction"] for item in results},
            {"tenerife_to_poland", "poland_to_tenerife"},
        )
        self.assertEqual(
            {item["price_total_regular_pln"] for item in results},
            {1300.0},
        )
        validate_document({"results": results})


if __name__ == "__main__":
    unittest.main()
