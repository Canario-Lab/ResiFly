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
from scripts.build_gdn_config_patch import main as build_configuration, refresh_endpoint_text
from scripts.collection_coverage import Coverage, expected_queries
from scripts.discover_transfer_routes import discover_candidates
from scripts.search_airports import POLISH_AIRPORTS, ENDPOINT_TIMEZONES, validate_polish_transfer
from scripts.verify_wizz_expansion_schedules import required_routes
from tests.test_airport_expansion import leg

ROOT = Path(__file__).resolve().parents[1]
SEVEN = ("WAW", "WMI", "KTW", "KRK", "GDN", "WRO", "POZ")
RYANAIR_HUBS = {"AGP", "BGY", "BHX", "CRL", "DUB", "STN"}


class LcjExpansionTests(unittest.TestCase):
    def test_lcj_retained_in_current_endpoint_registry_and_nine_scopes(self):
        self.assertEqual(POLISH_AIRPORTS, SEVEN + ("LCJ", "RZE", "BZG", "LUZ", "SZY", "RDO"))
        self.assertEqual(ENDPOINT_TIMEZONES["LCJ"], "Europe/Warsaw")
        paths = list((ROOT / "data").glob("*transfer-airports.json"))
        self.assertEqual(len(paths), 9)
        for path in paths:
            self.assertEqual(json.loads(path.read_text())["scope"]["polish_airports"], list(POLISH_AIRPORTS))

    def test_exact_reviewed_lcj_permissions(self):
        self.assertEqual({r["iata"] for r in collect_step3.load_allowlist()["airports"]
                          if "LCJ" in r["polish_airports"]}, RYANAIR_HUBS)
        self.assertFalse(any("LCJ" in r["polish_airports"] for r in collect_step4.load_allowlist()["airports"]))
        self.assertFalse(any("LCJ" in r["polish_airports"]
                             for v in collect_step5.load_allowlist()["variants"].values() for r in v["airports"]))
        for name in ("binter", "iberia", "vueling", "air-europa", "volotea", "canaryfly"):
            config = json.loads((ROOT / "data" / f"{name}-transfer-airports.json").read_text())
            found = {r["iata"] for r in config["airports"]
                     if any(p.get("polish_airport") == "LCJ"
                            for p in r.get("polish_routes", []) + r.get("eligibility_evidence", []))}
            self.assertEqual(found, {"ALC", "AGP"} if name == "vueling" else set(), name)

    def test_full_direct_matrix_and_each_lcj_day(self):
        plan = expected_queries("2", date(2026, 10, 23), date(2026, 11, 22))
        self.assertEqual(len(plan), 104 * 31)
        for carrier in ("Ryanair", "Wizz Air"):
            for tenerife in ("TFN", "TFS"):
                for origin, destination in (("LCJ", tenerife), (tenerife, "LCJ")):
                    self.assertEqual(sum(c == carrier and o == origin and d == destination
                                         for c, o, d, day, kind in plan), 31)

    @patch("scripts.collect_step1.collect_ryanair_route", return_value=[])
    @patch("scripts.collect_step1.collect_wizz_route", return_value=[])
    def test_full_low_cost_matrix_includes_lcj_even_when_empty(self, wizz, ryanair):
        start, end = date(2026, 10, 23), date(2026, 11, 22)
        collect_step1.collect_low_cost_legs(["MAD", "PMI"], start, end, {}, 2, {})
        for collector in (wizz, ryanair):
            self.assertEqual(collector.call_count, 52)
            calls = {call.args[:4] for call in collector.call_args_list}
            for hub in ("MAD", "PMI"):
                self.assertIn(("LCJ", hub, start, end), calls)
                self.assertIn((hub, "LCJ", start, end), calls)

    def test_saved_lcj_legs_have_complete_independent_query_plans(self):
        start, end = date(2026, 10, 23), date(2026, 11, 22)
        for step, hubs in (("1c", {"ALC", "AGP"}), ("3", RYANAIR_HUBS)):
            plan = expected_queries(step, start, end)
            for hub in hubs:
                for origin, destination in (("LCJ", hub), (hub, "LCJ")):
                    self.assertEqual(sum(c == "Ryanair" and o == origin and d == destination
                                         for c, o, d, day, kind in plan), 31)

    def test_resident_builders_both_directions_and_frozen_seven_regression(self):
        for step, carrier in (("1", "Binter"), ("1b", "Iberia"), ("1c", "Vueling"),
                              ("1d", "Air Europa"), ("1e", "Volotea"), ("1f", "Canaryfly")):
            module = importlib.import_module("scripts.collect_step" + step)
            low = [leg("Ryanair", p, "2026-11-01T06:00:00+01:00", "MAD", "2026-11-01T09:00:00+01:00", f"FR{n}")
                   for n, p in enumerate(SEVEN + ("LCJ",))]
            low += [leg("Ryanair", "MAD", "2026-11-02T16:00:00+01:00", p, "2026-11-02T19:00:00+01:00", f"FR{n}")
                    for n, p in enumerate(SEVEN + ("LCJ",))]
            resident = [leg(carrier, "MAD", "2026-11-01T12:00:00+01:00", "TFN", "2026-11-01T14:00:00+00:00"),
                        leg(carrier, "TFN", "2026-11-02T08:00:00+00:00", "MAD", "2026-11-02T12:00:00+01:00")]
            rows = module.build_connections(low, resident)
            lcj = [r for r in rows if "LCJ" in (r["origin_airport"], r["destination_airport"])]
            self.assertEqual({r["direction"] for r in lcj}, {"poland_to_tenerife", "tenerife_to_poland"})
            with patch.object(module, "POLISH_AIRPORTS", SEVEN):
                before = module.build_connections([r for r in low if "LCJ" not in (r["departure_airport"], r["arrival_airport"])], resident)
            self.assertEqual(before, [r for r in rows if r not in lcj], step)

    def test_three_four_and_both_mixed_variants_both_directions(self):
        # Synthetic permissions verify support, not a claim of live Wizz LCJ routes.
        for module, hub, a, b, variant in (
            (collect_step3, "AGP", "Ryanair", "Ryanair", None),
            (collect_step4, "BUD", "Wizz Air", "Wizz Air", None),
            (collect_step5, "LTN", "Ryanair", "Wizz Air", collect_step5.VARIANT_A),
            (collect_step5, "BUD", "Wizz Air", "Ryanair", collect_step5.VARIANT_B)):
            config = copy.deepcopy(module.load_allowlist())
            rules = config["airports"] if variant is None else config["variants"][variant]["airports"]
            next(r for r in rules if r["iata"] == hub)["polish_airports"] = ["LCJ"]
            legs = [leg(a, "TFS", "2026-11-01T06:00:00+00:00", hub, "2026-11-01T10:00:00+01:00"),
                    leg(b, hub, "2026-11-01T13:00:00+01:00", "LCJ", "2026-11-01T16:00:00+01:00"),
                    leg(b, "LCJ", "2026-11-02T06:00:00+01:00", hub, "2026-11-02T09:00:00+01:00"),
                    leg(a, hub, "2026-11-02T12:00:00+01:00", "TFS", "2026-11-02T15:00:00+00:00")]
            rows = module.build_connections(legs, config, 4.0)
            self.assertEqual(len(rows), 2)
            module.validate_document({"results": rows}, config)

    def test_no_new_polish_transfer_roles(self):
        validate_polish_transfer("KRK", "GDN", "step5_variant_b")
        for p, hub in (("LCJ", "GDN"), ("LCJ", "POZ"), ("LCJ", "WRO"), ("LCJ", "LCJ"), ("KRK", "LCJ")):
            with self.assertRaises(RuntimeError):
                validate_polish_transfer(p, hub, "step5_variant_b")

    def test_lcj_transfer_boundaries_across_midnight_and_dst(self):
        arrival = datetime.fromisoformat("2026-10-25T00:30:00+01:00")
        for wait, count in ((119, 0), (120, 1), (1440, 1), (1441, 0)):
            departure = (arrival.astimezone(timezone.utc) + timedelta(minutes=wait)).astimezone(ZoneInfo("Europe/London"))
            landing = (departure.astimezone(timezone.utc) + timedelta(minutes=135)).astimezone(ZoneInfo("Europe/Warsaw"))
            legs = [leg("Ryanair", "TFS", "2026-10-24T19:00:00+01:00", "STN", arrival.isoformat(), "FR1"),
                    leg("Ryanair", "STN", departure.isoformat(), "LCJ", landing.isoformat(), "FR2")]
            rows = collect_step3.build_connections(legs, collect_step3.load_allowlist(), 4.0)
            self.assertEqual(len(rows), count, wait)
            if rows:
                self.assertEqual(rows[0]["layover_minutes"], wait)

    def test_frozen_seven_direct_and_transfer_results_and_ids_unchanged(self):
        for module, hub, a, b, variant in (
            (collect_step3, "AGP", "Ryanair", "Ryanair", None),
            (collect_step4, "BUD", "Wizz Air", "Wizz Air", None),
            (collect_step5, "LTN", "Ryanair", "Wizz Air", collect_step5.VARIANT_A),
            (collect_step5, "BUD", "Wizz Air", "Ryanair", collect_step5.VARIANT_B)):
            config = copy.deepcopy(module.load_allowlist())
            rules = config["airports"] if variant is None else config["variants"][variant]["airports"]
            next(r for r in rules if r["iata"] == hub)["polish_airports"] = list(SEVEN + ("LCJ",))
            legs = [leg(a, "TFS", "2026-11-01T06:00:00+00:00", hub, "2026-11-01T10:00:00+01:00", "XX0")]
            legs += [leg(b, hub, "2026-11-01T13:00:00+01:00", p, "2026-11-01T16:00:00+01:00", f"XX{n+1}")
                     for n, p in enumerate(SEVEN + ("LCJ",))]
            after = module.build_connections(legs, config, 4.0)
            previous = copy.deepcopy(config)
            old_rules = previous["airports"] if variant is None else previous["variants"][variant]["airports"]
            for rule in old_rules:
                rule["polish_airports"] = [p for p in rule["polish_airports"] if p in SEVEN]
            with patch.object(module, "POLISH_AIRPORTS", SEVEN):
                before = module.build_connections([r for r in legs if r["arrival_airport"] != "LCJ"], previous, 4.0)
            self.assertEqual(before, [r for r in after if r["destination_airport"] != "LCJ"])
        direct = [leg("Ryanair", p, "2026-11-01T10:00:00+01:00", "TFS", "2026-11-01T15:00:00+00:00", f"FR{n}")
                  for n, p in enumerate(POLISH_AIRPORTS)]
        with patch.object(collect_step2, "POLISH_AIRPORTS", SEVEN):
            before = collect_step2.build_results([r for r in direct if r["departure_airport"] in SEVEN])
        self.assertEqual(before, [r for r in collect_step2.build_results(direct) if r["origin_airport"] in SEVEN])

    def test_completely_new_hub_discovered_built_and_planned(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            snapshot = {"as_of": "2026-10-23", "routes": {"ryanair": [["LCJ", "NEW"], ["NEW", "TFS"]],
                         "wizzair": [], "binter": []}, "airports": {"NEW": {
                             "name": "Synthetic new airport", "country_code": "GB", "timezone": "Europe/London"}}}
            self.assertNotIn("NEW", {r["iata"] for r in collect_step3.load_allowlist()["airports"]})
            found = discover_candidates(snapshot)["step3"]
            self.assertEqual([(r.iata, r.polish_airports) for r in found], [("NEW", ("LCJ",))])
            evidence = {"endpoint": "LCJ", "snapshot_date": "2026-10-23", "period_from": "2026-10-23",
                        "period_to": "2026-11-22", "routes": []}
            (folder / "snapshot.json").write_text(json.dumps(snapshot))
            (folder / "evidence.json").write_text(json.dumps(evidence))
            argv = ["build", "--endpoint", "LCJ", "--snapshot", str(folder / "snapshot.json"),
                    "--schedules", str(folder / "evidence.json"), "--from-date", "2026-10-23",
                    "--baseline-directory", str(ROOT / "data"), "--output-directory", str(folder / "review")]
            with patch("sys.argv", argv):
                build_configuration()
            config = json.loads((folder / "review/ryanair-transfer-airports.json").read_text())
            new = next(r for r in config["airports"] if r["iata"] == "NEW")
            self.assertEqual(new["polish_airports"], ["LCJ"])
            with patch.object(collect_step3, "load_allowlist", return_value=config):
                plan = expected_queries("3", date(2026, 10, 23), date(2026, 10, 23))
            for pair in (("LCJ", "NEW"), ("NEW", "LCJ"), ("TFS", "NEW"), ("NEW", "TFS")):
                self.assertIn(("Ryanair", *pair, "2026-10-23", "calendar"), plan)
            retry = argv.copy()
            retry[retry.index("--baseline-directory") + 1] = str(folder / "review")
            retry[retry.index("--output-directory") + 1] = str(folder / "second")
            with patch("sys.argv", retry):
                build_configuration()
            for path in (folder / "review").glob("*.json"):
                self.assertEqual(json.loads(path.read_text()), json.loads((folder / "second" / path.name).read_text()))

    def test_wizz_required_routes_includes_new_tenerife_leg_for_variant_b(self):
        snapshot = {"routes": {"ryanair": [["LCJ", "NEW"]], "wizzair": [["NEW", "TFS"]], "binter": []}, "airports": {}}
        required = required_routes(snapshot, "LCJ")
        self.assertIn(("NEW", "TFS"), required)
        self.assertIn(("TFS", "NEW"), required)

    def test_missing_lcj_requests_cannot_certify_current_endpoints(self):
        start = date(2026, 10, 23)
        plan = expected_queries("2", start, start)
        tracker = Coverage("2", start, start, plan, "test-lcj")
        for c, o, d, day, kind in plan:
            if "LCJ" not in (o, d):
                tracker.record(c, o, d, start, start, [], "google_flights_http" if c == "Ryanair" else "timetableV2")
        self.assertEqual(tracker.report()["missing_queries"], 8)
        with self.assertRaisesRegex(RuntimeError, "Incomplete source coverage"):
            tracker.verify()

    def test_endpoint_text_is_idempotent_for_lcj(self):
        original = "Trasy z WAW/WMI/KTW/KRK/GDN/WRO/POZ/LCJ. wszystkie osiem polskich lotnisk."
        once = refresh_endpoint_text(original)
        self.assertEqual(refresh_endpoint_text(once), once)
        self.assertEqual(once.count("LCJ"), 1)
        self.assertNotIn("osiem", once)


if __name__ == "__main__":
    unittest.main()
