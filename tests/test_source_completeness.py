from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import collect_step1 as binter
from scripts import collect_step2 as ryanair
from scripts import collect_step3, collect_step5, collection_coverage as coverage


DAY = date(2026, 11, 1)
RATES = {"EUR": binter.CurrencyRate("EUR", 4.3), "PLN": binter.CurrencyRate("PLN", 1)}


def calendar(day=DAY, flights=None, origin="WMI", destination="MAD"):
    if flights is None:
        flights = [flight("FR1", "14:00", "17:00", 20), flight("FR2", "09:00", "12:00", 40)]
    return {"currency": "EUR", "trips": [{"origin": origin, "destination": destination, "dates": [{
        "dateOut": day.isoformat() + "T00:00:00", "flights": flights,
    }]}]}


def flight(number, departure, arrival, price):
    return {"flightKey": number, "flightNumber": number, "regularFare": {"fares": [{"type": "ADT", "amount": price}]},
            "segments": [{"flightNumber": number, "time": [f"{DAY}T{departure}:00", f"{DAY}T{arrival}:00"]}]}


def binter_response(flights=None):
    return {"data": {"booking_search": {"messages": [], "availability": [{
        "trip": {"origin": {"iata": "TFN"}, "destination": {"iata": "MAD"}, "date": str(DAY)},
        "flights": [] if flights is None else flights,
    }]}}}


def binter_amount(regular, resident):
    return {
        "mainAmount": regular,
        "totalAmount": resident,
        "currency": {"code": "EUR"},
    }


def binter_imports_response():
    return {"data": {"booking_getImports": {"passengerAmounts": [{
        "fare": binter_amount(375, 93.75),
        "taxes": binter_amount(8.91, 8.91),
        "suplements": binter_amount(0, 0),
        "serviceFee": binter_amount(12, 3),
        "managementFee": binter_amount(0, 0),
        "mobilidadeDiscounts": [],
        "passenger": {
            "typeCode": "ADT",
            "residentCode": "RC",
            "isResident": True,
            "isSpanishResident": True,
        },
    }]}}}


class RyanairCompletenessTests(unittest.TestCase):
    @patch("scripts.collect_step2.collect_ryanair_google_route_days")
    def test_keeps_both_flights_and_more_expensive_one_can_be_only_valid_connection(self, google):
        def google_leg(number, departure, arrival, price):
            return {"carrier": "Ryanair", "flight_number": number,
                    "departure_airport": "WMI", "arrival_airport": "MAD",
                    "departure_at": f"{DAY}T{departure}:00+01:00",
                    "arrival_at": f"{DAY}T{arrival}:00+01:00",
                    "price_regular_pln": price, "price_resident_estimated_pln": price,
                    "resident_discount_eligible": False, "booking_url": "https://example.com"}
        google.return_value = [google_leg("FR1", "14:00", "17:00", 86), google_leg("FR2", "09:00", "12:00", 172)]
        legs = ryanair.collect_ryanair_route("WMI", "MAD", DAY, DAY, RATES, "test")
        self.assertEqual({leg["flight_number"] for leg in legs}, {"FR1", "FR2"})
        resident_leg = {"carrier": "Binter", "flight_number": "NT1", "departure_airport": "MAD",
                        "arrival_airport": "TFN", "departure_at": f"{DAY}T18:00:00+01:00",
                        "arrival_at": f"{DAY}T20:00:00+00:00", "price_regular_pln": 800,
                        "price_resident_estimated_pln": 200, "resident_discount_eligible": True}
        connections = binter.build_connections(legs, [resident_leg])
        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0]["legs"][0]["flight_number"], "FR2")

    @patch("scripts.collect_step2.collect_ryanair_google_route_days", return_value=[])
    @patch("scripts.collect_step2.collect_ryanair_farefinder_dates")
    def test_verified_empty_google_window_does_not_use_minimum_fares(self, minimum, google):
        self.assertEqual(ryanair.collect_ryanair_route("WMI", "MAD", DAY, DAY + timedelta(days=1), RATES, "test"), [])
        google.assert_called_once_with("WMI", "MAD", DAY, DAY + timedelta(days=1))
        minimum.assert_not_called()

    @patch("scripts.collect_step2.collect_ryanair_google_route_days", side_effect=RuntimeError("Google route/day failed; publication blocked"))
    def test_failed_daily_google_source_propagates_in_steps_3_and_5(self, google):
        with self.assertRaisesRegex(RuntimeError, "publication blocked"):
            collect_step3.collect_routes([("WMI", "MAD")], DAY, DAY, RATES, "test", 1)
        with patch("scripts.collect_step5.collect_wizz_routes") as wizz:
            with self.assertRaisesRegex(RuntimeError, "publication blocked"):
                collect_step5.collect_full_calendars({"Ryanair": [("WMI", "MAD")], "Wizz Air": []}, DAY, DAY, RATES, "test", 1)
            wizz.assert_not_called()

    @patch("scripts.collect_step2.collect_ryanair_google_route_days", side_effect=RuntimeError("missing route/day"))
    def test_missing_google_route_day_is_rejected(self, google):
        with self.assertRaisesRegex(RuntimeError, "missing route/day"):
            ryanair.collect_ryanair_route("WMI", "MAD", DAY, DAY + timedelta(days=1), RATES, "test")

    @patch("scripts.collect_step2.time_module.sleep")
    @patch("scripts.collect_step2.requests.get")
    def test_ambiguous_http_errors_and_malformed_date_index_are_not_empty_calendars(self, get, sleep):
        for payload in ({}, {"error": "oops"}, [None]):
            response = Mock(status_code=200)
            response.json.return_value = payload
            get.return_value = response
            with self.assertRaisesRegex(RuntimeError, "active dates failed"):
                ryanair.ryanair_available_dates("WMI", "MAD")
        response.raise_for_status.side_effect = RuntimeError("HTTP 404")
        with self.assertRaisesRegex(RuntimeError, "active dates failed"):
            ryanair.ryanair_available_dates("WMI", "MAD")
        response.raise_for_status.side_effect = None
        response.json.return_value = []
        self.assertEqual(ryanair.ryanair_available_dates("WMI", "MAD"), [])

    @patch("scripts.collect_step2.requests.get")
    def test_exact_day_request_uses_zero_flexible_days(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = calendar(flights=[])
        ryanair.ryanair_availability("WMI", "MAD", DAY, "test", exact_day=True)
        self.assertEqual(get.call_args.kwargs["params"]["FlexDaysBeforeOut"], 0)
        self.assertEqual(get.call_args.kwargs["params"]["FlexDaysOut"], 0)


class BinterCompletenessTests(unittest.TestCase):
    @patch("scripts.collect_step1.get_json")
    def test_http_graphql_and_schema_failures_are_not_empty_availability(self, get):
        get.side_effect = RuntimeError("HTTP 503 after retries")
        with self.assertRaisesRegex(RuntimeError, "TFN-MAD.*2026-11-01.*publication blocked"):
            binter.collect_binter_trip("TFN", "MAD", DAY, RATES, True, .25)
        get.side_effect = None
        for response in ({}, {"errors": [{"message": "failed"}]}, {"data": {"booking_search": None}},
                         {"data": {"booking_search": {"availability": None}}},
                         {"data": {"booking_search": {"availability": [], "messages": [{"type": "ERROR", "text": "failed"}]}}}):
            get.return_value = response
            with self.subTest(response=response), self.assertRaises(RuntimeError):
                binter.collect_binter_trip("TFN", "MAD", DAY, RATES, True, .25)

    @patch("scripts.collect_step1.get_json")
    def test_valid_empty_and_sold_out_days_are_accepted_but_wrong_route_is_not(self, get):
        get.return_value = binter_response()
        self.assertEqual(binter.collect_binter_trip("TFN", "MAD", DAY, RATES, True, .25), [])
        get.return_value["data"]["booking_search"]["availability"][0]["trip"]["date"] = "2026-11-02"
        with self.assertRaisesRegex(RuntimeError, "mismatched"):
            binter.collect_binter_trip("TFN", "MAD", DAY, RATES, True, .25)
        self.assertIsNone(binter.lowest_eur_fare([{"seats": 0}]))

    def test_binter_loyalty_points_do_not_hide_or_invalidate_cash_fares(self):
        def fare(currency, regular, resident):
            return {"seats": None, "amounts": {"noResident": {"currency": {"code": currency}, "totalAmount": regular},
                                               "resident": {"currency": {"code": currency}, "totalAmount": resident}}}
        self.assertEqual(binter.lowest_eur_fare([fare("PTS", 8000, 8000), fare("EUR", 150, 37.5)]), (150, 37.5))
        with self.assertRaises(RuntimeError):
            binter.lowest_eur_fare([{"seats": 2, "amounts": {}}])

    @patch("scripts.collect_step1.get_json")
    def test_uses_official_final_totals_instead_of_fare_list_amounts(self, get):
        search = binter_response([{
            "flightSegments": [{
                "line": "NT",
                "flightNumber": 6072,
                "origin": {"iata": "TFN"},
                "destination": {"iata": "MAD"},
                "departureTime": f"{DAY}T10:05:00+00:00",
                "arrivalTime": f"{DAY}T13:55:00+01:00",
            }],
            "fares": [{
                "seats": None,
                "token": "opaque-fare-token",
                "amounts": {
                    "noResident": {
                        "currency": {"code": "EUR"},
                        "totalAmount": 375,
                    },
                    "resident": {
                        "currency": {"code": "EUR"},
                        "totalAmount": 93.75,
                    },
                },
            }],
        }])
        get.side_effect = [search, binter_imports_response()]

        legs = binter.collect_binter_trip(
            "TFN", "MAD", DAY, RATES, True, .25
        )

        self.assertEqual(len(legs), 1)
        leg = legs[0]
        self.assertEqual(leg["price_regular_pln"], 1702.41)
        self.assertEqual(leg["price_resident_estimated_pln"], 454.34)
        self.assertEqual(leg["price_source_amount"], 395.91)
        self.assertEqual(leg["price_source_resident_amount"], 105.66)
        self.assertFalse(leg["resident_price_is_estimate"])
        self.assertNotIn("opaque-fare-token", str(leg))

        imports_call = get.call_args_list[1].kwargs["payload"]
        self.assertEqual(imports_call["operationName"], "booking_getImports")
        self.assertEqual(
            imports_call["variables"]["itineraries"],
            [{"token": "opaque-fare-token"}],
        )
        self.assertEqual(
            imports_call["variables"]["passengers"][0]["type"]["discounts"],
            ["RC"],
        )

    def test_incomplete_or_non_resident_final_price_is_rejected(self):
        context = "Binter TFN-MAD test"
        with self.assertRaisesRegex(RuntimeError, "booking_getImports"):
            binter.validate_binter_imports_response(
                {"errors": [{"message": "failed"}]}, context, True
            )
        incomplete = binter_imports_response()
        del incomplete["data"]["booking_getImports"]["passengerAmounts"][0]["taxes"]
        with self.assertRaisesRegex(RuntimeError, "missing taxes"):
            binter.validate_binter_imports_response(incomplete, context, True)
        non_resident = binter_imports_response()
        passenger = non_resident["data"]["booking_getImports"]["passengerAmounts"][0]["passenger"]
        passenger["residentCode"] = None
        passenger["isSpanishResident"] = False
        with self.assertRaisesRegex(RuntimeError, "resident status"):
            binter.validate_binter_imports_response(non_resident, context, True)

    @patch("scripts.collect_step1.nbp_eur_rate", return_value=RATES["EUR"])
    @patch("scripts.collect_step1.collect_low_cost_legs", return_value=[])
    @patch("scripts.collect_step1.get_json", side_effect=RuntimeError("HTTP 503"))
    def test_real_collector_failure_leaves_previous_feed_byte_identical(self, get, low_cost, nbp):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "step1-results.json"
            original = b'{"old":"preserve this exact file"}\n'
            output.write_bytes(original)
            args = Mock(from_date=DAY, days=0, output=output, workers=2)
            with patch("scripts.collect_step1.cli", return_value=args):
                with self.assertRaisesRegex(RuntimeError, "publication blocked"):
                    binter.main()
            self.assertEqual(output.read_bytes(), original)
            report = json.loads(output.with_suffix(".collection-report.json").read_text())
            self.assertEqual(report["status"], "failed")
            self.assertIn("Binter", report["error"])
            self.assertGreater(report["missing_queries"], 0)


class CoverageTests(unittest.TestCase):
    @patch("builtins.print")
    @patch("scripts.collect_step1.nbp_eur_rate", return_value=RATES["EUR"])
    @patch("scripts.collect_step1.wizz_timetable", return_value=[])
    @patch("scripts.collect_step1.get_json", return_value={"data": {"booking_search": {"messages": [], "availability": []}}})
    @patch("scripts.collect_step2.ryanair_client_version", return_value="test")
    @patch("scripts.collect_step2.collect_ryanair_google_route_days", return_value=[])
    def test_successful_standalone_step1_records_every_planned_empty_route_and_day(self, google, version, get, wizz, nbp, print_mock):
        def source_reply(*args, **kwargs):
            if kwargs["payload"]["operationName"] == "booking_getImports":
                return binter_imports_response()
            trip = kwargs["payload"]["variables"]["search"]["trips"][0]
            if {trip["origin"], trip["destination"]} != {"TFN", "MAD"}:
                return {"data": {"booking_search": {"messages": [], "availability": []}}}
            reply = binter_response([{
                "flightSegments": [{"line": "NT", "flightNumber": 1, "origin": {"iata": trip["origin"]},
                                    "destination": {"iata": trip["destination"]},
                                    "departureTime": f"{DAY}T08:00:00+00:00" if trip["origin"] == "TFN" else f"{DAY}T14:00:00+01:00",
                                    "arrivalTime": f"{DAY}T12:00:00+01:00" if trip["origin"] == "TFN" else f"{DAY}T16:00:00+00:00"}],
                "fares": [{"seats": None, "token": "opaque-test-token", "amounts": {
                    "noResident": {"currency": {"code": "EUR"}, "totalAmount": 100},
                    "resident": {"currency": {"code": "EUR"}, "totalAmount": 25}}}],
            }])
            reply["data"]["booking_search"]["availability"][0]["trip"] = {
                "origin": {"iata": trip["origin"]}, "destination": {"iata": trip["destination"]}, "date": str(DAY)}
            return reply
        get.side_effect = source_reply
        wizz.side_effect = lambda origin, destination, start, end, price_type: ([{
            "departureDate": f"{DAY}T18:00:00" if origin == "MAD" else f"{DAY}T06:00:00", "price": {"currencyCode": "EUR", "amount": 50},
        }] if {origin, destination} == {"MAD", "WAW"} else [])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "step1-results.json"
            args = Mock(from_date=DAY, days=0, output=output, workers=2)
            with patch("scripts.collect_step1.cli", return_value=args), patch.object(binter, "_ryanair_client_version", None):
                binter.main()
            document = json.loads(output.read_text())
            self.assertEqual(len(document["results"]), 2)
            self.assertEqual(document["collection_coverage"]["completed_queries"], len(coverage.expected_queries("1", DAY, DAY)))
            self.assertEqual(coverage.validate_coverage(document, "1", DAY, DAY), document["collection_coverage"]["run_id"])

    @patch("builtins.print")
    @patch("scripts.collect_step2.nbp_eur_rate", return_value=RATES["EUR"])
    @patch("scripts.collect_step2.wizz_timetable", return_value=[])
    @patch("scripts.collect_step2.ryanair_client_version", return_value="test")
    @patch("scripts.collect_step2.collect_ryanair_google_route_days", return_value=[])
    def test_successful_step2_certifies_all_forty_route_carrier_pairs(self, google, version, wizz, nbp, print_mock):
        wizz.side_effect = lambda origin, destination, start, end, price_type: ([{
            "departureDate": f"{DAY}T10:00:00", "price": {"currencyCode": "EUR", "amount": 50},
        }] if {origin, destination} == {"WAW", "TFS"} else [])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "step2-results.json"
            args = Mock(from_date=DAY, days=0, output=output)
            with patch("scripts.collect_step2.cli", return_value=args):
                ryanair.main()
            document = json.loads(output.read_text())
            self.assertEqual(document["collection_coverage"]["completed_queries"], 40)
            coverage.validate_coverage(document, "2", DAY, DAY)

    def test_missing_request_blocks_standalone_publish_but_valid_empty_queries_pass(self):
        expected = {("Binter", "TFN", "MAD", str(DAY), "calendar"),
                    ("Binter", "MAD", "TFN", str(DAY), "calendar")}
        tracker = coverage.Coverage("1", DAY, DAY, expected, "test-run")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            output.write_text("old")
            with patch.object(coverage, "_active", tracker):
                coverage.record_checked("Binter", "TFN", "MAD", DAY, DAY, [], "booking_search")
                with self.assertRaisesRegex(RuntimeError, "1 missing"):
                    coverage.publish_document({"results": []}, output)
                self.assertEqual(output.read_text(), "old")
                coverage.record_checked("Binter", "MAD", "TFN", DAY, DAY, [], "booking_search")
                coverage.publish_document({"results": []}, output)
                report = json.loads(output.read_text())["collection_coverage"]
                self.assertEqual(report["status"], "complete")
                self.assertEqual(report["completed_queries"], 2)

    def test_canaryfly_available_calendar_day_requires_details(self):
        key = ("Canaryfly", "TFN", "LPA", str(DAY), "calendar")
        tracker = coverage.Coverage("1f", DAY, DAY, {key})
        tracker.record("Canaryfly", "TFN", "LPA", DAY, DAY, [{"departure_at": str(DAY)}], "booking_calendar")
        with self.assertRaisesRegex(RuntimeError, "1 missing"):
            tracker.verify()
        tracker.record("Canaryfly", "TFN", "LPA", DAY, DAY, [], "booking_search", "details")
        self.assertEqual(tracker.verify()["status"], "complete")

    def test_all_saved_route_plans_include_both_directions_and_entire_window(self):
        for step in ("1", "1b", "1c", "1d", "1e", "1f", "2", "3", "4", "5"):
            plan = coverage.expected_queries(step, DAY, DAY + timedelta(days=1))
            for carrier, origin, destination, day, kind in plan:
                self.assertIn((carrier, destination, origin, day, kind), plan)
                self.assertIn((carrier, origin, destination, str(DAY), kind), plan)
                self.assertIn((carrier, origin, destination, str(DAY + timedelta(days=1)), kind), plan)

    def test_atomic_serialization_failure_cannot_truncate_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            output.write_text("old")
            with self.assertRaises(ValueError):
                coverage.atomic_json(output, {"price": float("nan")})
            self.assertEqual(output.read_text(), "old")
            self.assertEqual(list(Path(directory).glob("*.pending")), [])

    @patch("scripts.collect_step2.time_module.sleep")
    @patch("scripts.collect_step2.requests.post")
    @patch("scripts.collect_step2.wizz_api_base", return_value="https://example.com")
    def test_missing_wizz_response_structure_cannot_be_certified_as_empty(self, base, post, sleep):
        response = Mock(status_code=200)
        response.json.return_value = {}
        post.return_value = response
        with self.assertRaisesRegex(RuntimeError, "Wizz Air request failed"):
            ryanair.wizz_timetable("WAW", "TFS", DAY, DAY, "regular")
        with patch("scripts.collect_step1.get_json", return_value={}), patch("scripts.collect_step1.wizz_api_base", return_value="https://example.com"):
            with self.assertRaisesRegex(RuntimeError, "Invalid Wizz timetable"):
                binter.wizz_timetable("WAW", "TFS", DAY, DAY, "regular")


if __name__ == "__main__":
    unittest.main()
