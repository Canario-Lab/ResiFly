import copy
from datetime import date, datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from scripts import collect_step1, collect_step2, collect_step3, collect_step4, collect_step5
from scripts.booking_urls import ryanair_booking_url, wizz_booking_url
from scripts.discover_transfer_routes import discover_candidates
from scripts.search_airports import POLISH_AIRPORTS, ENDPOINT_TIMEZONES
from scripts.wizz_schedules import load_wizz_route_data, read_overrides, resolve_schedule

ROOT = Path(__file__).resolve().parents[1]


def leg(carrier, origin, departure, destination, arrival, number="W60001"):
    return {
        "carrier": carrier, "flight_number": number,
        "departure_airport": origin, "arrival_airport": destination,
        "departure_at": departure, "arrival_at": arrival,
        "price_regular_pln": 900, "price_resident_estimated_pln": 225 if carrier not in ("Ryanair", "Wizz Air") else 900,
        "price_wizz_discount_club_pln": 800 if carrier == "Wizz Air" else None,
        "resident_discount_eligible": carrier not in ("Ryanair", "Wizz Air"),
        "resident_fare_multiplier": 1.0, "booking_url": "https://example.com/booking",
    }


class AirportExpansionTests(unittest.TestCase):
    def test_all_nine_allowlist_scopes_use_exactly_seven_endpoints(self):
        self.assertEqual(POLISH_AIRPORTS, ("WAW", "WMI", "KTW", "KRK", "GDN", "WRO", "POZ"))
        self.assertEqual(ENDPOINT_TIMEZONES["GDN"], "Europe/Warsaw")
        files = list((ROOT / "data").glob("*transfer-airports.json"))
        self.assertEqual(len(files), 9)
        for path in files:
            document = json.loads(path.read_text())
            self.assertEqual(document["scope"]["polish_airports"], list(POLISH_AIRPORTS), path.name)

    def test_each_resident_variant_builds_both_gdn_directions(self):
        for suffix, carrier in (("1", "Binter"), ("1b", "Iberia"), ("1c", "Vueling"), ("1d", "Air Europa"), ("1e", "Volotea"), ("1f", "Canaryfly")):
            with self.subTest(step=suffix):
                module = importlib.import_module("scripts.collect_step" + suffix)
                low = [
                    leg("Wizz Air", "MAD", "2026-11-01T15:00:00+01:00", "GDN", "2026-11-01T18:30:00+01:00"),
                    leg("Wizz Air", "GDN", "2026-11-02T06:00:00+01:00", "MAD", "2026-11-02T09:30:00+01:00"),
                ]
                resident = [
                    leg(carrier, "TFN", "2026-11-01T08:00:00+00:00", "MAD", "2026-11-01T12:00:00+01:00", "XX1"),
                    leg(carrier, "MAD", "2026-11-02T13:00:00+01:00", "TFN", "2026-11-02T15:00:00+00:00", "XX2"),
                ]
                results = module.build_connections(low, resident)
                self.assertEqual(len(results), 2)
                self.assertEqual({row["direction"] for row in results}, {"tenerife_to_poland", "poland_to_tenerife"})
                self.assertTrue(all("GDN" in (row["origin_airport"], row["destination_airport"]) for row in results))

    def test_verified_gdn_schedules_exist_both_ways_and_resolve_time_overrides(self):
        schedules, overrides = load_wizz_route_data()
        for hub in ("AGA", "AGP", "ALC", "BCN", "BUD", "EIN", "FCO", "LTN", "MAD", "MXP", "PMI", "TFS"):
            self.assertIn(("GDN", hub), schedules)
            self.assertIn((hub, "GDN"), schedules)
        self.assertEqual(schedules[("WAW", "TFS")], ("W61495", 360))
        for key, number in overrides.items():
            if "GDN" not in key[:2]:
                continue
            departure = datetime.fromisoformat("2026-11-01T" + key[2] + ":00+01:00")
            resolved, duration = resolve_schedule(schedules, overrides, key[0], key[1], departure)
            self.assertEqual(resolved, number)
            self.assertGreater(duration, 0)

    def test_local_resident_wizz_schedules_match_shared_gdn_metadata(self):
        shared, shared_overrides = load_wizz_route_data()
        for carrier in ("binter", "iberia"):
            document = json.loads((ROOT / "data" / f"{carrier}-transfer-airports.json").read_text())
            local = collect_step1.wizz_schedules_from_allowlist(document)
            for pair, schedule in local.items():
                if "GDN" in pair:
                    self.assertEqual(schedule, shared[pair])
            for key, number in local.overrides.items():
                if "GDN" in key[:2]:
                    self.assertEqual(number, shared_overrides[key])
                    self.assertEqual(local.overrides.durations.get(key), shared_overrides.durations.get(key))

    @patch("scripts.collect_step1.collect_ryanair_route", return_value=[])
    @patch("scripts.collect_step1.collect_wizz_route", return_value=[])
    def test_resident_full_matrix_queries_gdn_both_carriers_even_when_empty(self, wizz, ryanair):
        start, end = date(2026, 10, 22), date(2026, 11, 21)
        collect_step1.collect_low_cost_legs(["MAD", "PMI"], start, end, {}, 2, {})
        for collector in (wizz, ryanair):
            self.assertEqual(collector.call_count, 28)
            calls = {call.args[:4] for call in collector.call_args_list}
            for hub in ("MAD", "PMI"):
                self.assertIn(("GDN", hub, start, end), calls)
                self.assertIn((hub, "GDN", start, end), calls)

    def test_gdn_direct_results_validate_both_directions(self):
        results = collect_step2.build_results([
            leg("Wizz Air", "GDN", "2026-11-01T10:00:00+01:00", "TFS", "2026-11-01T14:55:00+00:00", "W61709"),
            leg("Wizz Air", "TFS", "2026-11-02T15:30:00+00:00", "GDN", "2026-11-02T22:05:00+01:00", "W61710"),
        ])
        collect_step2.validate_document({"results": results})
        self.assertEqual(len(results), 2)

    @patch("scripts.collect_step2.wizz_timetable")
    def test_direct_wizz_collector_reads_verified_gdn_schedule(self, timetable):
        timetable.return_value = [{"departureDate": "2026-11-01T10:00:00", "price": {"amount": 500, "currencyCode": "PLN"}}]
        for origin, destination, number, duration in (("GDN", "TFS", "W61709", 355), ("TFS", "GDN", "W61710", 335)):
            rows = collect_step2.collect_wizz_route(origin, destination, date(2026, 11, 1), date(2026, 11, 21), {})
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["flight_number"], number)
            elapsed = datetime.fromisoformat(rows[0]["arrival_at"]) - datetime.fromisoformat(rows[0]["departure_at"])
            self.assertEqual(elapsed.total_seconds() / 60, duration)

    @patch("scripts.collect_step1.wizz_timetable")
    def test_resident_wizz_collector_applies_number_and_duration_overrides(self, timetable):
        timetable.return_value = [{"departureDate": f"2026-11-01T{hour}:00:00", "price": {"amount": 500, "currencyCode": "PLN"}} for hour in ("10", "20")]
        schedules = collect_step1.WizzSchedules()
        schedules[("GDN", "MAD")] = ("W60001", 120)
        schedules.overrides = read_overrides([{"origin": "GDN", "destination": "MAD", "departure_time": "20:00", "flight_number": "W60002", "duration_minutes": 150}], schedules)
        with patch.dict(collect_step1.AIRPORT_TIMEZONES, {"MAD": "Europe/Madrid"}):
            rows = collect_step1.collect_wizz_route("GDN", "MAD", date(2026, 11, 1), date(2026, 11, 21), {}, schedules)
        self.assertEqual([row["flight_number"] for row in rows], ["W60001", "W60002"])
        self.assertEqual([(datetime.fromisoformat(row["arrival_at"]) - datetime.fromisoformat(row["departure_at"])).total_seconds() / 60 for row in rows], [120, 150])

    def test_gdn_layover_boundaries_across_midnight_and_dst(self):
        arrival = datetime.fromisoformat("2026-10-25T00:30:00+02:00")
        for wait, expected in ((119, 0), (120, 1), (1440, 1), (1441, 0)):
            departure = (arrival.astimezone(timezone.utc) + timedelta(minutes=wait)).astimezone(ZoneInfo("Europe/Madrid"))
            landing = (departure.astimezone(timezone.utc) + timedelta(hours=3)).astimezone(ZoneInfo("Europe/Warsaw"))
            legs = [
                leg("Ryanair", "TFS", "2026-10-24T19:00:00+01:00", "AGP", arrival.isoformat(), "FR1"),
                leg("Wizz Air", "AGP", departure.isoformat(), "GDN", landing.isoformat(), "W61614"),
            ]
            results = collect_step5.build_connections(
                legs, collect_step5.load_allowlist(), 4.0
            )
            self.assertEqual(len(results), expected, wait)
            if results:
                self.assertEqual(results[0]["layover_minutes"], wait)

    def test_adding_endpoint_does_not_change_old_resident_results_or_ids(self):
        for suffix, carrier in (("1", "Binter"), ("1b", "Iberia"), ("1c", "Vueling"), ("1d", "Air Europa"), ("1e", "Volotea"), ("1f", "Canaryfly")):
            module = importlib.import_module("scripts.collect_step" + suffix)
            low = [leg("Ryanair", "MAD", "2026-11-01T15:00:00+01:00", polish, "2026-11-01T18:00:00+01:00", f"FR{index}") for index, polish in enumerate(POLISH_AIRPORTS)]
            resident = [leg(carrier, "TFN", "2026-11-01T08:00:00+00:00", "MAD", "2026-11-01T12:00:00+01:00", "XX1")]
            previous_endpoints = ("WAW", "WMI", "KTW", "KRK", "GDN")
            with patch.object(module, "POLISH_AIRPORTS", previous_endpoints):
                before = module.build_connections([row for row in low if row["arrival_airport"] in previous_endpoints], resident)
            after = [row for row in module.build_connections(low, resident) if row["destination_airport"] in previous_endpoints]
            self.assertEqual(before, after, suffix)

    def test_gdn_endpoint_in_steps_three_four_and_both_mixed_variants(self):
        for module, hub, tenerife_carrier, polish_carrier in (
            (collect_step3, "AGP", "Ryanair", "Ryanair"),
            (collect_step4, "BUD", "Wizz Air", "Wizz Air"),
            (collect_step5, "AGP", "Ryanair", "Wizz Air"),
            (collect_step5, "BUD", "Wizz Air", "Ryanair"),
        ):
            with self.subTest(step=module.__name__, hub=hub):
                legs = [
                    leg(tenerife_carrier, "TFS", "2026-11-01T08:00:00+00:00", hub, "2026-11-01T12:00:00+01:00", "TEST1"),
                    leg(polish_carrier, hub, "2026-11-01T15:00:00+01:00", "GDN", "2026-11-01T18:00:00+01:00", "TEST2"),
                    leg(polish_carrier, "GDN", "2026-11-02T06:00:00+01:00", hub, "2026-11-02T09:00:00+01:00", "TEST3"),
                    leg(tenerife_carrier, hub, "2026-11-02T12:00:00+01:00", "TFS", "2026-11-02T15:00:00+00:00", "TEST4"),
                ]
                results = module.build_connections(legs, module.load_allowlist(), 4.0)
                self.assertEqual(len(results), 2)
                module.validate_document({"results": results}, module.load_allowlist())

    def test_gdn_transfer_to_krk_survives_endpoint_expansion(self):
        legs = [
            leg("Wizz Air", "TFS", "2026-11-01T08:00:00+00:00", "GDN", "2026-11-01T14:00:00+01:00", "W61710"),
            leg("Ryanair", "GDN", "2026-11-01T17:00:00+01:00", "KRK", "2026-11-01T18:00:00+01:00", "FR1"),
            leg("Ryanair", "KRK", "2026-11-02T07:00:00+01:00", "GDN", "2026-11-02T08:00:00+01:00", "FR2"),
            leg("Wizz Air", "GDN", "2026-11-02T11:00:00+01:00", "TFS", "2026-11-02T16:00:00+00:00", "W61709"),
        ]
        results = collect_step5.build_connections(
            legs, collect_step5.load_allowlist(), 4.0
        )
        self.assertEqual(len(results), 2)
        self.assertTrue(all(row["transfer_airport"] == "GDN" for row in results))
        self.assertTrue(all(row["price_total_regular_pln"] == row["price_total_resident_estimated_pln"] for row in results))
        collect_step5.validate_document({"results": results}, collect_step5.load_allowlist())

    @patch("scripts.collect_step1.wizz_timetable", return_value=[{"departureDate": "2026-11-01T10:00:00"}])
    def test_active_wizz_without_schedule_fails_instead_of_silently_disappearing(self, timetable):
        with self.assertRaisesRegex(RuntimeError, "verified local schedule"):
            collect_step1.collect_wizz_route("GDN", "XXX", date(2026, 11, 1), date(2026, 11, 2), {}, {})
        timetable.assert_called_once()

    @patch("scripts.collect_step2.ryanair_client_version", return_value="3.222.0")
    @patch("scripts.collect_step2.collect_ryanair_route", side_effect=RuntimeError("HTTP 503 after retries"))
    def test_ryanair_source_failure_propagates(self, collect_route, version):
        with patch.object(collect_step1, "_ryanair_client_version", None):
            with self.assertRaisesRegex(RuntimeError, "503"):
                collect_step1.collect_ryanair_route("GDN", "MAD", date(2026, 11, 1), date(2026, 11, 2), {})

    @patch("scripts.collect_step2.time_module.sleep")
    @patch("scripts.collect_step2.requests.get")
    def test_ryanair_truncated_calendar_cannot_be_published(self, get, sleep):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {"fares": [{}] * 20}
        with self.assertRaisesRegex(RuntimeError, "not a complete flight source"):
            collect_step2.collect_ryanair_farefinder_dates("GDN", "MAD", [date(2026, 11, 1)], date(2026, 11, 1), date(2026, 11, 21), {})
        get.assert_not_called()

    @patch("scripts.collect_step2.ryanair_client_version", return_value="3.222.0")
    @patch("scripts.collect_step2.collect_ryanair_route")
    def test_resident_ryanair_uses_complete_calendar_and_one_client_version(self, collect_route, version):
        expected = [leg("Ryanair", "GDN", f"2026-11-{day}T10:00:00+01:00", "MAD", f"2026-11-{day}T13:30:00+01:00", "FR1") for day in ("01", "10", "21")]
        collect_route.return_value = expected
        start, end = date(2026, 11, 1), date(2026, 11, 21)
        with patch.object(collect_step1, "_ryanair_client_version", None):
            self.assertEqual(collect_step1.collect_ryanair_route("GDN", "MAD", start, end, {}), expected)
            collect_step1.collect_ryanair_route("MAD", "GDN", start, end, {})
        version.assert_called_once()
        collect_route.assert_any_call("GDN", "MAD", start, end, {}, "3.222.0")
        collect_route.assert_any_call("MAD", "GDN", start, end, {}, "3.222.0")

    @patch("scripts.collect_step1.time_module.sleep")
    @patch("scripts.collect_step1.requests.request")
    def test_wizz_503_is_not_treated_as_an_empty_market(self, request, sleep):
        request.return_value = Mock(status_code=503, text="Unavailable")
        request.return_value.raise_for_status.side_effect = RuntimeError("HTTP 503")
        with self.assertRaisesRegex(RuntimeError, "Request failed"):
            collect_step1.get_json("POST", "https://example.com", empty_market=True, attempts=2)
        self.assertEqual(request.call_count, 2)

    @patch("scripts.collect_step1.requests.request")
    def test_invalid_wizz_market_is_empty_without_swallowing_other_failures(self, request):
        request.return_value = Mock(status_code=400, text="InvalidMarket")
        self.assertEqual(collect_step1.get_json("POST", "https://example.com", empty_market=True), {"outboundFlights": []})
        request.return_value.raise_for_status.assert_not_called()

    def test_gdn_discovery_expands_existing_hub_and_preserves_only_grandfathered_transfer(self):
        snapshot = {"routes": {
            "ryanair": [["TFS", "AGP"], ["AGP", "GDN"], ["GDN", "KRK"], ["GDN", "KTW"]],
            "wizzair": [["TFS", "GDN"], ["TFS", "BUD"], ["BUD", "GDN"]], "binter": [],
        }}
        found = discover_candidates(snapshot)
        self.assertIn("GDN", next(row for row in found["step3"] if row.iata == "AGP").polish_airports)
        gdn = next(row for row in found["step5_variant_b"] if row.iata == "GDN")
        self.assertEqual(gdn.polish_airports, ("KRK",))
        self.assertFalse(any(row.iata == "GDN" for row in found["step3"]))
        self.assertIn("GDN", next(row for row in found["step4"] if row.iata == "BUD").polish_airports)

    def test_all_production_route_matrices_have_no_self_route(self):
        for module in (collect_step3, collect_step4, collect_step5):
            routes = module.route_matrix(module.load_allowlist())
            if isinstance(routes, dict):
                routes = [pair for pairs in routes.values() for pair in pairs]
            self.assertTrue(all(a != b for a, b in routes))
        bad = copy.deepcopy(collect_step5.load_allowlist())
        gdn = next(row for row in bad["variants"][collect_step5.VARIANT_B]["airports"] if row["iata"] == "GDN")
        gdn["polish_airports"].append("GDN")
        with self.assertRaisesRegex(RuntimeError, "Invalid Poland/transfer"):
            collect_step5.route_matrix(bad)

    def test_self_transfer_is_rejected_by_result_validator_too(self):
        allowlist = copy.deepcopy(collect_step5.load_allowlist())
        rule = next(row for row in allowlist["variants"][collect_step5.VARIANT_B]["airports"] if row["iata"] == "GDN")
        rule["polish_airports"].append("GDN")
        rows = [{
            "id": direction, "direction": direction, "variant": collect_step5.VARIANT_B,
            "connection_type": "one_stop", "layover_minutes": 120, "transfer_airport": "GDN",
            "origin_airport": origin, "destination_airport": destination, "legs": [{}, {}],
        } for direction, origin, destination in (("tenerife_to_poland", "TFS", "GDN"), ("poland_to_tenerife", "GDN", "TFS"))]
        with self.assertRaisesRegex(RuntimeError, "Invalid Poland/transfer"):
            collect_step5.validate_document({"results": rows}, allowlist)

    def test_gdn_transfer_exception_cannot_spread_to_other_polish_airports(self):
        allowlist = copy.deepcopy(collect_step5.load_allowlist())
        rule = next(row for row in allowlist["variants"][collect_step5.VARIANT_B]["airports"] if row["iata"] == "GDN")
        rule["polish_airports"].append("KTW")
        with self.assertRaisesRegex(RuntimeError, "Unapproved endpoint-as-transfer"):
            collect_step5.route_matrix(allowlist)

    def test_stable_booking_links_accept_gdn_both_ways(self):
        for origin, destination in (("GDN", "TFS"), ("TFS", "GDN")):
            self.assertIn(f"/{origin}/{destination}/2026-11-01/", wizz_booking_url(origin, destination, "2026-11-01"))
            self.assertIn("originIata=" + origin, ryanair_booking_url(origin, destination, "2026-11-01"))


if __name__ == "__main__":
    unittest.main()
