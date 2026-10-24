import copy
from datetime import date, datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from scripts import collect_step1, collect_step2, collect_step3, collect_step4, collect_step5
from scripts.build_gdn_config_patch import main as build_configuration
from scripts import audit_airport_expansion
from scripts.collection_coverage import expected_queries, Coverage
from scripts.discover_transfer_routes import Candidate, discover_candidates
from scripts.search_airports import POLISH_AIRPORTS, ENDPOINT_TIMEZONES, validate_polish_transfer
from scripts.verify_wizz_expansion_schedules import required_routes
from scripts.wizz_schedules import load_wizz_route_data, resolve_schedule
from tests.test_airport_expansion import leg

ROOT = Path(__file__).resolve().parents[1]
SIX = ("WAW", "WMI", "KTW", "KRK", "GDN", "WRO")
RYANAIR_HUBS = {"AGP", "BGY", "BHX", "BRS", "BVA", "CRL", "DUB", "EDI",
                "LBA", "LPL", "MAN", "OPO", "SNN", "STN", "TSF", "VLC"}


class PozExpansionTests(unittest.TestCase):
    def test_poz_retained_in_current_endpoint_registry_and_all_scopes(self):
        self.assertEqual(POLISH_AIRPORTS, SIX + ("POZ", "LCJ", "RZE", "BZG", "LUZ", "SZY", "RDO", "SZZ", "IEG"))
        self.assertEqual(ENDPOINT_TIMEZONES["POZ"], "Europe/Warsaw")
        for path in (ROOT / "data").glob("*transfer-airports.json"):
            self.assertEqual(json.loads(path.read_text())["scope"]["polish_airports"], list(POLISH_AIRPORTS))

    def test_exact_reviewed_poz_permissions_no_copied_wro_routes(self):
        self.assertEqual({r["iata"] for r in collect_step3.load_allowlist()["airports"]
                          if "POZ" in r["polish_airports"]}, RYANAIR_HUBS)
        self.assertFalse(any("POZ" in r["polish_airports"] for r in collect_step4.load_allowlist()["airports"]))
        mixed = collect_step5.load_allowlist()["variants"]
        self.assertEqual({r["iata"] for r in mixed[collect_step5.VARIANT_A]["airports"]
                          if "POZ" in r["polish_airports"]}, {"LTN"})
        self.assertFalse(any("POZ" in r["polish_airports"] for r in mixed[collect_step5.VARIANT_B]["airports"]))
        for name, hubs in (("binter", {"PMI", "VLC"}), ("iberia", set()),
                           ("vueling", {"ALC", "BCN", "AGP", "VLC"}),
                           ("air-europa", set()), ("volotea", set()), ("canaryfly", set())):
            config = json.loads((ROOT / "data" / f"{name}-transfer-airports.json").read_text())
            found = {r["iata"] for r in config["airports"]
                     if any(p.get("polish_airport") == "POZ"
                            for p in r.get("polish_routes", []) + r.get("eligibility_evidence", []))}
            self.assertEqual(found, hubs, name)

    def test_full_direct_matrix_both_carriers_both_tenerife_airports_every_day(self):
        plan = expected_queries("2", date(2026, 10, 23), date(2026, 11, 22))
        self.assertEqual(len(plan), 120 * 31)
        for carrier in ("Ryanair", "Wizz Air"):
            for tenerife in ("TFN", "TFS"):
                for origin, destination in (("POZ", tenerife), (tenerife, "POZ")):
                    self.assertEqual(sum(c == carrier and o == origin and d == destination
                                         for c, o, d, day, kind in plan), 31)

    @patch("scripts.collect_step1.collect_ryanair_route", return_value=[])
    @patch("scripts.collect_step1.collect_wizz_route", return_value=[])
    def test_step1a_1b_low_cost_matrix_checks_empty_poz_days_independently(self, wizz, ryanair):
        start, end = date(2026, 10, 23), date(2026, 11, 22)
        collect_step1.collect_low_cost_legs(["MAD", "PMI"], start, end, {}, 2, {})
        for collector in (wizz, ryanair):
            self.assertEqual(collector.call_count, 60)
            calls = {call.args[:4] for call in collector.call_args_list}
            for hub in ("MAD", "PMI"):
                self.assertIn(("POZ", hub, start, end), calls)
                self.assertIn((hub, "POZ", start, end), calls)

    def test_actual_query_plans_include_each_configured_poz_leg_both_directions(self):
        start, end = date(2026, 10, 23), date(2026, 11, 22)
        for step, carrier, hubs in (("1c", "Ryanair", {"ALC", "BCN", "AGP", "VLC"}),
                                    ("3", "Ryanair", RYANAIR_HUBS), ("5", "Wizz Air", {"LTN"})):
            plan = expected_queries(step, start, end)
            for hub in hubs:
                for origin, destination in (("POZ", hub), (hub, "POZ")):
                    self.assertEqual(sum(c == carrier and o == origin and d == destination
                                         for c, o, d, day, kind in plan), 31, (step, hub))

    def test_all_resident_builders_accept_poz_and_preserve_identical_six_endpoint_inputs(self):
        for step, carrier in (("1", "Binter"), ("1b", "Iberia"), ("1c", "Vueling"),
                              ("1d", "Air Europa"), ("1e", "Volotea"), ("1f", "Canaryfly")):
            module = importlib.import_module("scripts.collect_step" + step)
            low = [leg("Ryanair", code, "2026-11-01T06:00:00+01:00", "MAD", "2026-11-01T09:00:00+01:00", f"FR{n}")
                   for n, code in enumerate(SIX + ("POZ",))]
            low += [leg("Ryanair", "MAD", "2026-11-02T16:00:00+01:00", code, "2026-11-02T19:00:00+01:00", f"FR{n}")
                    for n, code in enumerate(SIX + ("POZ",))]
            resident = [leg(carrier, "MAD", "2026-11-01T12:00:00+01:00", "TFN", "2026-11-01T14:00:00+00:00"),
                        leg(carrier, "TFN", "2026-11-02T08:00:00+00:00", "MAD", "2026-11-02T12:00:00+01:00")]
            all_rows = module.build_connections(low, resident)
            poz = [r for r in all_rows if "POZ" in (r["origin_airport"], r["destination_airport"])]
            self.assertEqual({r["direction"] for r in poz}, {"poland_to_tenerife", "tenerife_to_poland"}, step)
            with patch.object(module, "POLISH_AIRPORTS", SIX):
                before = module.build_connections([r for r in low if "POZ" not in (r["departure_airport"], r["arrival_airport"])], resident)
            self.assertEqual(before, [r for r in all_rows if r not in poz], step)

    def test_three_four_and_both_mixed_variants_build_poz_both_directions(self):
        # Synthetic Wizz-Wizz and mixed B permissions test mechanics, not live POZ routes.
        for module, hub, a, b, variant in (
            (collect_step3, "AGP", "Ryanair", "Ryanair", None),
            (collect_step4, "BUD", "Wizz Air", "Wizz Air", None),
            (collect_step5, "LTN", "Ryanair", "Wizz Air", collect_step5.VARIANT_A),
            (collect_step5, "BUD", "Wizz Air", "Ryanair", collect_step5.VARIANT_B)):
            config = copy.deepcopy(module.load_allowlist())
            rules = config["airports"] if variant is None else config["variants"][variant]["airports"]
            next(r for r in rules if r["iata"] == hub)["polish_airports"] = ["POZ"]
            legs = [leg(a, "TFS", "2026-11-01T06:00:00+00:00", hub, "2026-11-01T10:00:00+01:00"),
                    leg(b, hub, "2026-11-01T13:00:00+01:00", "POZ", "2026-11-01T16:00:00+01:00"),
                    leg(b, "POZ", "2026-11-02T06:00:00+01:00", hub, "2026-11-02T09:00:00+01:00"),
                    leg(a, hub, "2026-11-02T12:00:00+01:00", "TFS", "2026-11-02T15:00:00+00:00")]
            rows = module.build_connections(legs, config, 4.0)
            self.assertEqual(len(rows), 2, (module.__name__, variant))
            module.validate_document({"results": rows}, config)

    def test_no_endpoint_as_transfer_expansion(self):
        validate_polish_transfer("KRK", "GDN", "step5_variant_b")
        for endpoint, transfer in (("POZ", "GDN"), ("POZ", "WRO"), ("POZ", "POZ"), ("KRK", "POZ")):
            if endpoint == transfer:
                with self.assertRaises(RuntimeError):
                    validate_polish_transfer(endpoint, transfer, "step5_variant_b")
            else:
                validate_polish_transfer(endpoint, transfer, "step5_variant_b")

    def test_poz_ltn_summer_winter_and_date_override(self):
        schedules, overrides = load_wizz_route_data()
        for origin, destination, stamp, expected in (
            ("POZ", "LTN", "2026-10-24T11:40:00+02:00", ("W95390", 120)),
            ("LTN", "POZ", "2026-11-02T07:45:00+00:00", ("W95389", 125)),
            ("LTN", "POZ", "2026-10-24T07:45:00+01:00", ("W95389", 130))):
            self.assertEqual(resolve_schedule(schedules, overrides, origin, destination, datetime.fromisoformat(stamp)), expected)
        self.assertEqual(overrides[("LTN", "POZ", "07:45")], "W95389")

    def test_detector_new_hub_and_existing_hub_for_poz_not_polish_transfers(self):
        snapshot = {"routes": {"ryanair": [["POZ", "NEW"], ["NEW", "TFS"], ["POZ", "AGP"], ["AGP", "TFS"], ["POZ", "GDN"]],
                               "wizzair": [["GDN", "TFS"]], "binter": []}, "airports": {}}
        candidates = discover_candidates(snapshot)
        self.assertEqual({r.iata for r in candidates["step3"] if "POZ" in r.polish_airports}, {"NEW", "AGP"})
        self.assertTrue(any("POZ" in r.polish_airports and r.iata == "GDN" for r in candidates["step5_variant_b"]))

    def test_schedule_audit_poz_both_needed_legs(self):
        snapshot = {"routes": {"ryanair": [["POZ", "NEW"], ["LTN", "TFS"]],
                               "wizzair": [["NEW", "TFS"], ["POZ", "LTN"]], "binter": []}, "airports": {}}
        required = required_routes(snapshot, "POZ")
        for pair in (("LTN", "POZ"), ("POZ", "LTN"), ("NEW", "TFS"), ("TFS", "NEW")):
            self.assertIn(pair, required)

    def test_coverage_without_poz_does_not_certify_current_registry(self):
        start = date(2026, 10, 23)
        full = expected_queries("2", start, start)
        old = {q for q in full if "POZ" not in q[1:3]}
        tracker = Coverage("2", start, start, full, "test-poz")
        for c, o, d, day, kind in old:
            tracker.record(c, o, d, start, start, [], "google_flights_http" if c == "Ryanair" else "timetableV2", kind)
        with self.assertRaisesRegex(RuntimeError, "Incomplete source coverage"):
            tracker.verify()
        self.assertEqual(tracker.report()["missing_queries"], 8)

    def test_poz_transfer_boundaries_across_midnight_dst(self):
        arrival = datetime.fromisoformat("2026-10-25T00:30:00+01:00")
        for wait, count in ((119, 0), (120, 1), (1440, 1), (1441, 0)):
            departure = (arrival.astimezone(timezone.utc) + timedelta(minutes=wait)).astimezone(ZoneInfo("Europe/London"))
            landing = (departure.astimezone(timezone.utc) + timedelta(minutes=125)).astimezone(ZoneInfo("Europe/Warsaw"))
            legs = [leg("Ryanair", "TFS", "2026-10-24T19:00:00+01:00", "LTN", arrival.isoformat()),
                    leg("Wizz Air", "LTN", departure.isoformat(), "POZ", landing.isoformat())]
            rows = collect_step5.build_connections(legs, collect_step5.load_allowlist(), 4.0)
            self.assertEqual(len(rows), count, wait)
            if rows:
                self.assertEqual(rows[0]["layover_minutes"], wait)

    def test_configuration_builder_rejects_wrong_endpoint_or_window(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            snapshot, evidence = folder / "snapshot.json", folder / "evidence.json"
            snapshot.write_text(json.dumps({"as_of": "2026-10-23"}))
            for endpoint, end in (("WRO", "2026-11-22"), ("POZ", "2026-11-21")):
                evidence.write_text(json.dumps({"endpoint": endpoint, "snapshot_date": "2026-10-23",
                                               "period_from": "2026-10-23", "period_to": end}))
                with patch("sys.argv", ["build", "--endpoint", "POZ", "--snapshot", str(snapshot),
                                        "--schedules", str(evidence), "--from-date", "2026-10-23"]):
                    with self.assertRaisesRegex(RuntimeError, "Mismatched"):
                        build_configuration()

    def test_old_six_direct_and_transfer_results_unchanged_on_frozen_inputs(self):
        for module, hub, a, b, variant in (
            (collect_step3, "AGP", "Ryanair", "Ryanair", None),
            (collect_step4, "BUD", "Wizz Air", "Wizz Air", None),
            (collect_step5, "LTN", "Ryanair", "Wizz Air", collect_step5.VARIANT_A),
            (collect_step5, "BUD", "Wizz Air", "Ryanair", collect_step5.VARIANT_B)):
            config = copy.deepcopy(module.load_allowlist())
            rules = config["airports"] if variant is None else config["variants"][variant]["airports"]
            next(r for r in rules if r["iata"] == hub)["polish_airports"] = list(SIX + ("POZ",))
            legs = [leg(a, "TFS", "2026-11-01T06:00:00+00:00", hub, "2026-11-01T10:00:00+01:00", "XX0")]
            legs += [leg(b, hub, "2026-11-01T13:00:00+01:00", code, "2026-11-01T16:00:00+01:00", f"XX{n+1}")
                     for n, code in enumerate(SIX + ("POZ",))]
            all_rows = module.build_connections(legs, config, 4.0)
            previous_config = copy.deepcopy(config)
            previous_rules = previous_config["airports"] if variant is None else previous_config["variants"][variant]["airports"]
            for rule in previous_rules:
                rule["polish_airports"] = [p for p in rule["polish_airports"] if p != "POZ"]
            with patch.object(module, "POLISH_AIRPORTS", SIX):
                before = module.build_connections([r for r in legs if r["arrival_airport"] != "POZ"], previous_config, 4.0)
            self.assertEqual(before, [r for r in all_rows if r["destination_airport"] != "POZ"], module.__name__)
        direct = [leg("Ryanair", code, "2026-11-01T10:00:00+01:00", "TFS", "2026-11-01T15:00:00+00:00", f"FR{n}")
                  for n, code in enumerate(SIX + ("POZ",))]
        with patch.object(collect_step2, "POLISH_AIRPORTS", SIX):
            before = collect_step2.build_results([r for r in direct if r["departure_airport"] in SIX])
        self.assertEqual(before, [r for r in collect_step2.build_results(direct) if r["origin_airport"] != "POZ"])

    @patch("scripts.audit_airport_expansion.fill_timezones")
    @patch("scripts.audit_airport_expansion.build_plan", return_value={"steps": {"step1": {}}})
    @patch("scripts.audit_airport_expansion.fetch_wizz", return_value=(set(), {}))
    @patch("scripts.audit_airport_expansion.fetch_ryanair", return_value=({("POZ", "NEW")}, {}))
    @patch("scripts.audit_airport_expansion._http_client")
    def test_network_audit_new_hubs_and_partial_failures_are_explicit(self, session, ryanair, wizz, plan, fill):
        with tempfile.TemporaryDirectory() as temp:
            argv = ["audit", "--endpoint", "POZ", "--as-of", "2026-10-23", "--output-directory", temp]
            with patch("scripts.audit_airport_expansion.fetch_binter", side_effect=RuntimeError("GraphQL error")) as binter:
                with patch("sys.argv", argv):
                    with self.assertRaisesRegex(RuntimeError, "GraphQL"):
                        audit_airport_expansion.main()
                self.assertEqual(binter.call_args.args[2], {"NEW"})
            snapshot = json.loads((Path(temp) / "network-snapshot.json").read_text())
            self.assertEqual(snapshot["routes"]["ryanair"], [["POZ", "NEW"]])
            self.assertEqual(snapshot["source_status"]["binter"], "failed")
            self.assertIn("GraphQL", snapshot["source_errors"]["binter"])
            with patch("scripts.audit_airport_expansion.fetch_binter") as binter:
                with patch("sys.argv", argv + ["--low-cost-only"]):
                    audit_airport_expansion.main()
                binter.assert_not_called()
            report = json.loads((Path(temp) / "discovery-report.json").read_text())
            self.assertEqual(report["source_status"]["binter"], "not_checked")
            self.assertIn("not checked", report["steps"]["step1"]["note"])
            session.return_value.close.assert_called()

    def test_configuration_builder_is_idempotent_and_rejects_unreviewed_tenerife_port(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            snapshot, evidence = folder / "snapshot.json", folder / "evidence.json"
            snapshot.write_text(json.dumps({"as_of": "2026-10-23", "airports": {},
                                           "routes": {"ryanair": [], "wizzair": [["POZ", "LTN"]], "binter": []}}))
            evidence.write_text(json.dumps({"endpoint": "POZ", "snapshot_date": "2026-10-23",
                "period_from": "2026-10-23", "period_to": "2026-11-22", "routes": [
                    {"origin": "POZ", "destination": "LTN", "departure_at": "2026-11-01T12:00:00+01:00",
                     "flight_number": "W95390", "duration_minutes": 135, "source": "https://www.google.com/travel/flights"},
                    {"origin": "LTN", "destination": "POZ", "departure_at": "2026-11-01T07:45:00+00:00",
                     "flight_number": "W95389", "duration_minutes": 125, "source": "https://www.google.com/travel/flights"}]}))
            candidates = {s: [] for s in ("step1", "step3", "step4", "step5_variant_a", "step5_variant_b")}
            candidates["step5_variant_a"] = [Candidate("LTN", ("TFS",), ("POZ",))]
            argv = ["build", "--endpoint", "POZ", "--snapshot", str(snapshot), "--schedules", str(evidence),
                    "--from-date", "2026-10-23"]
            with patch("scripts.build_gdn_config_patch.discover_candidates", return_value=candidates):
                for baseline, output in ((ROOT / "data", folder / "first"), (folder / "first", folder / "second")):
                    with patch("sys.argv", argv + ["--baseline-directory", str(baseline), "--output-directory", str(output)]):
                        build_configuration()
                files = list((folder / "first").glob("*.json"))
                self.assertEqual(len(files), 10)
                for path in files:
                    self.assertEqual(json.loads(path.read_text()), json.loads((folder / "second" / path.name).read_text()))
                candidates["step5_variant_a"] = [Candidate("LTN", ("TFN", "TFS"), ("POZ",))]
                with patch("sys.argv", argv + ["--output-directory", str(folder / "third")]):
                    with self.assertRaisesRegex(RuntimeError, "Review new Tenerife airports explicitly"):
                        build_configuration()


if __name__ == "__main__":
    unittest.main()
