"""BZG integration, complete query plans and frozen nine-endpoint regressions."""
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
from scripts.collection_coverage import Coverage, expected_queries, validate_coverage
from scripts.discover_transfer_routes import discover_candidates, build_plan, load_documents
from scripts.search_airports import POLISH_AIRPORTS, ENDPOINT_TIMEZONES, validate_polish_transfer
from scripts.verify_wizz_expansion_schedules import required_routes
from scripts.wizz_schedules import load_wizz_route_data, resolve_schedule
from tests.test_airport_expansion import leg

ROOT = Path(__file__).resolve().parents[1]
NINE = ("WAW", "WMI", "KTW", "KRK", "GDN", "WRO", "POZ", "LCJ", "RZE")
HUBS = {"BHX", "BRS", "DUB", "LTN", "STN"}
START, END = date(2026, 10, 23), date(2026, 11, 22)


class BzgExpansionTests(unittest.TestCase):
    def test_tenth_endpoint_and_nine_exact_scopes(self):
        self.assertEqual(POLISH_AIRPORTS, NINE + ("BZG",))
        self.assertEqual(ENDPOINT_TIMEZONES["BZG"], "Europe/Warsaw")
        paths = list((ROOT / "data").glob("*transfer-airports.json"))
        self.assertEqual(len(paths), 9)
        for path in paths:
            self.assertEqual(json.loads(path.read_text())["scope"]["polish_airports"], list(POLISH_AIRPORTS))

    def test_exact_reviewed_permissions_without_invented_wizz_or_mixed_routes(self):
        self.assertEqual({r["iata"] for r in collect_step3.load_allowlist()["airports"] if "BZG" in r["polish_airports"]}, HUBS)
        self.assertFalse(any("BZG" in r["polish_airports"] for r in collect_step4.load_allowlist()["airports"]))
        for variant in collect_step5.load_allowlist()["variants"].values():
            self.assertFalse(any("BZG" in r["polish_airports"] for r in variant["airports"]))
        for name in ("binter", "iberia", "vueling", "air-europa", "volotea", "canaryfly"):
            document = json.loads((ROOT / "data" / f"{name}-transfer-airports.json").read_text())
            actual = {r["iata"] for r in document["airports"] if any(p.get("polish_airport") == "BZG"
                      for p in r.get("polish_routes", []) + r.get("eligibility_evidence", []))}
            self.assertEqual(actual, {"ALC"} if name == "vueling" else set(), name)

    def test_complete_saved_bzg_calendars_and_direct_matrix(self):
        self.assertEqual(len(list(collect_step2.route_matrix())), 40)
        self.assertEqual(len(expected_queries("2", START, END)), 80 * 31)
        expected = [("2", c, t) for c in ("Ryanair", "Wizz Air") for t in ("TFN", "TFS")]
        expected += [("1c", "Ryanair", "ALC")] + [("3", "Ryanair", h) for h in HUBS]
        expected += [("1", c, h) for c in ("Ryanair", "Wizz Air") for h in ("FUE", "LPA", "MAD", "PMI", "SVQ", "VLC")]
        expected += [("1b", c, "MAD") for c in ("Ryanair", "Wizz Air")]
        for step, carrier, hub in expected:
            plan = expected_queries(step, START, END)
            for a, b in (("BZG", hub), (hub, "BZG")):
                self.assertEqual({day for c, o, d, day, kind in plan if (c, o, d) == (carrier, a, b)},
                                 {(START + timedelta(days=n)).isoformat() for n in range(31)}, (step, a, b))

    @patch("scripts.collect_step1.collect_ryanair_route", return_value=[])
    @patch("scripts.collect_step1.collect_wizz_route", return_value=[])
    def test_actual_executor_queries_bzg_both_carriers_even_if_other_is_empty(self, wizz, ryanair):
        collect_step1.collect_low_cost_legs(["MAD", "PMI"], START, END, {}, 2, {})
        for collector in (wizz, ryanair):
            self.assertEqual(collector.call_count, 40)
            calls = {call.args[:4] for call in collector.call_args_list}
            for h in ("MAD", "PMI"):
                self.assertIn(("BZG", h, START, END), calls)
                self.assertIn((h, "BZG", START, END), calls)

    def test_six_resident_builders_both_directions_and_frozen_nine(self):
        # Synthetic MAD permissions exercise mechanics, not a live BZG/MAD route.
        for step, carrier in (("1", "Binter"), ("1b", "Iberia"), ("1c", "Vueling"),
                              ("1d", "Air Europa"), ("1e", "Volotea"), ("1f", "Canaryfly")):
            module = importlib.import_module("scripts.collect_step" + step)
            low = [leg("Ryanair", p, "2026-11-01T06:00:00+01:00", "MAD", "2026-11-01T09:00:00+01:00", f"FR{n}") for n, p in enumerate(NINE + ("BZG",))]
            low += [leg("Ryanair", "MAD", "2026-11-02T16:00:00+01:00", p, "2026-11-02T19:00:00+01:00", f"FR{n}") for n, p in enumerate(NINE + ("BZG",))]
            resident = [leg(carrier, "MAD", "2026-11-01T12:00:00+01:00", "TFN", "2026-11-01T14:00:00+00:00"),
                        leg(carrier, "TFN", "2026-11-02T08:00:00+00:00", "MAD", "2026-11-02T12:00:00+01:00")]
            after = module.build_connections(low, resident)
            new = [r for r in after if "BZG" in (r["origin_airport"], r["destination_airport"])]
            self.assertEqual({r["direction"] for r in new}, {"poland_to_tenerife", "tenerife_to_poland"})
            with patch.object(module, "POLISH_AIRPORTS", NINE):
                before = module.build_connections([r for r in low if "BZG" not in (r["departure_airport"], r["arrival_airport"])], resident)
            self.assertEqual(before, [r for r in after if r not in new], step)

    def test_direct_and_low_cost_variants_preserve_frozen_nine_both_directions(self):
        for module, hub, a, b, variant in (
            (collect_step3, "STN", "Ryanair", "Ryanair", None),
            (collect_step4, "FCO", "Wizz Air", "Wizz Air", None),
            (collect_step5, "FCO", "Ryanair", "Wizz Air", collect_step5.VARIANT_A),
            (collect_step5, "MXP", "Wizz Air", "Ryanair", collect_step5.VARIANT_B)):
            config = copy.deepcopy(module.load_allowlist())
            rules = config["airports"] if variant is None else config["variants"][variant]["airports"]
            next(r for r in rules if r["iata"] == hub)["polish_airports"] = list(NINE + ("BZG",))
            legs = [leg(a, "TFS", "2026-11-01T06:00:00+00:00", hub, "2026-11-01T10:00:00+01:00", "XX0"),
                    leg(a, hub, "2026-11-02T12:00:00+01:00", "TFS", "2026-11-02T15:00:00+00:00", "XX1")]
            for n, p in enumerate(NINE + ("BZG",)):
                legs += [leg(b, hub, "2026-11-01T13:00:00+01:00", p, "2026-11-01T16:00:00+01:00", f"XX{n+2}"),
                         leg(b, p, "2026-11-02T06:00:00+01:00", hub, "2026-11-02T09:00:00+01:00", f"XX{n+20}")]
            after = module.build_connections(legs, config, 4.0)
            new = [r for r in after if "BZG" in (r["origin_airport"], r["destination_airport"])]
            self.assertEqual({r["direction"] for r in new}, {"poland_to_tenerife", "tenerife_to_poland"})
            module.validate_document({"results": after}, config)
            previous = copy.deepcopy(config)
            old_rules = previous["airports"] if variant is None else previous["variants"][variant]["airports"]
            for row in old_rules:
                row["polish_airports"] = [p for p in row["polish_airports"] if p in NINE]
            with patch.object(module, "POLISH_AIRPORTS", NINE):
                before = module.build_connections([r for r in legs if "BZG" not in (r["departure_airport"], r["arrival_airport"])], previous, 4.0)
            self.assertEqual(before, [r for r in after if r not in new])
        direct = []
        for n, p in enumerate(NINE + ("BZG",)):
            direct += [leg("Ryanair", p, "2026-11-01T10:00:00+01:00", "TFS", "2026-11-01T15:00:00+00:00", f"FR{n}"),
                       leg("Ryanair", "TFS", "2026-11-02T10:00:00+00:00", p, "2026-11-02T16:00:00+01:00", f"FR{n+20}")]
        with patch.object(collect_step2, "POLISH_AIRPORTS", NINE):
            before = collect_step2.build_results([r for r in direct if "BZG" not in (r["departure_airport"], r["arrival_airport"])])
        self.assertEqual(before, [r for r in collect_step2.build_results(direct) if "BZG" not in (r["origin_airport"], r["destination_airport"])])

    def test_preserved_rze_schedule_and_no_invented_bzg_schedule(self):
        schedules, overrides = load_wizz_route_data()
        self.assertFalse(any("BZG" in pair for pair in schedules))
        self.assertEqual(resolve_schedule(schedules, overrides, "RZE", "FCO", datetime.fromisoformat("2026-11-02T10:45:00+01:00")), ("W46068", 130))
        self.assertEqual(resolve_schedule(schedules, overrides, "RZE", "FCO", datetime.fromisoformat("2026-10-24T08:35:00+02:00")), ("W46068", 140))

    def test_exact_same_airport_transfer_roles_and_dst_boundaries(self):
        validate_polish_transfer("KRK", "GDN", "step5_variant_b")
        for p, h in (("BZG", "GDN"), ("BZG", "BZG"), ("KRK", "BZG")):
            with self.assertRaises(RuntimeError):
                validate_polish_transfer(p, h, "step5_variant_b")
        arrival = datetime.fromisoformat("2026-10-25T00:30:00+01:00")
        for wait, count in ((115, 0), (119, 0), (120, 1), (1440, 1), (1441, 0)):
            departure = (arrival.astimezone(timezone.utc) + timedelta(minutes=wait)).astimezone(ZoneInfo("Europe/London"))
            landing = (departure.astimezone(timezone.utc) + timedelta(minutes=150)).astimezone(ZoneInfo("Europe/Warsaw"))
            legs = [leg("Ryanair", "TFS", "2026-10-24T19:00:00+01:00", "STN", arrival.isoformat(), "FR1"),
                    leg("Ryanair", "STN", departure.isoformat(), "BZG", landing.isoformat(), "FR2")]
            rows = collect_step3.build_connections(legs, collect_step3.load_allowlist(), 4.0)
            self.assertEqual(len(rows), count)

    def test_global_new_hub_discovery_configuration_plan_and_idempotence(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            snapshot = {"as_of": "2026-10-23", "routes": {"ryanair": [["BZG", "NEW"], ["NEW", "TFS"]], "wizzair": [], "binter": []},
                        "airports": {"NEW": {"name": "Synthetic airport", "country_code": "GB", "timezone": "Europe/London"}}}
            self.assertNotIn("NEW", {r["iata"] for r in collect_step3.load_allowlist()["airports"]})
            self.assertEqual([(r.iata, r.polish_airports) for r in discover_candidates(snapshot)["step3"]], [("NEW", ("BZG",))])
            evidence = {"endpoint": "BZG", "snapshot_date": "2026-10-23", "period_from": "2026-10-23", "period_to": "2026-11-22", "routes": []}
            (folder / "snapshot.json").write_text(json.dumps(snapshot))
            (folder / "schedules.json").write_text(json.dumps(evidence))
            argv = ["build", "--endpoint", "BZG", "--snapshot", str(folder / "snapshot.json"), "--schedules", str(folder / "schedules.json"),
                    "--from-date", "2026-10-23", "--baseline-directory", str(ROOT / "data"), "--output-directory", str(folder / "review")]
            with patch("sys.argv", argv): build_configuration()
            config = json.loads((folder / "review/ryanair-transfer-airports.json").read_text())
            self.assertEqual(next(r for r in config["airports"] if r["iata"] == "NEW")["polish_airports"], ["BZG"])
            with patch.object(collect_step3, "load_allowlist", return_value=config): plan = expected_queries("3", START, START)
            for a, b in (("BZG", "NEW"), ("NEW", "BZG"), ("TFS", "NEW"), ("NEW", "TFS")):
                self.assertIn(("Ryanair", a, b, START.isoformat(), "calendar"), plan)
            argv[argv.index("--baseline-directory") + 1] = str(folder / "review")
            argv[argv.index("--output-directory") + 1] = str(folder / "second")
            with patch("sys.argv", argv): build_configuration()
            for p in (folder / "review").glob("*.json"):
                self.assertEqual(json.loads(p.read_text()), json.loads((folder / "second" / p.name).read_text()))

    def test_new_wizz_tenerife_leg_required_and_missing_poland_schedule_pending(self):
        snapshot = {"as_of": "2026-10-23", "routes": {"ryanair": [["BZG", "NEW"]], "wizzair": [["NEW", "TFS"]], "binter": []}, "airports": {}}
        self.assertIn(("NEW", "TFS"), required_routes(snapshot, "BZG"))
        self.assertIn(("TFS", "NEW"), required_routes(snapshot, "BZG"))
        snapshot["routes"] = {"ryanair": [["TFS", "NEW"]], "wizzair": [["BZG", "NEW"]], "binter": []}
        snapshot["airports"] = {"NEW": {"name": "Synthetic airport", "country_code": "GB", "timezone": "Europe/London"}}
        report = build_plan(snapshot, load_documents())
        self.assertIn("NEW", {r["iata"] for r in report["steps"]["step5_variant_a"]["pending"]})
        self.assertNotIn("NEW", {r["iata"] for r in report["steps"]["step5_variant_a"]["ready"]})

    def test_old_nine_report_and_single_missing_bzg_route_day_fail(self):
        plan = expected_queries("2", START, START)
        for missing in ({key for key in plan if "BZG" in key[1:3]}, {next(key for key in plan if "BZG" in key[1:3])}):
            tracker = Coverage("2", START, START, plan, "bzg-test")
            for c, o, d, day, kind in plan - missing:
                tracker.record(c, o, d, START, START, [], "google_flights_http" if c == "Ryanair" else "timetableV2")
            self.assertEqual(tracker.report()["missing_queries"], len(missing))
            with self.assertRaisesRegex(RuntimeError, "Incomplete source coverage"): tracker.verify()
        old = Coverage("2", START, START, {key for key in plan if "BZG" not in key[1:3]}, "old-nine")
        for c, o, d, day, kind in old.expected:
            old.record(c, o, d, START, START, [], "google_flights_http" if c == "Ryanair" else "timetableV2")
        with self.assertRaisesRegex(RuntimeError, "Incomplete source coverage"):
            validate_coverage({"collection_coverage": old.verify()}, "2", START, START)

    def test_tenth_endpoint_text_is_idempotent(self):
        once = refresh_endpoint_text("WAW/WMI/KTW/KRK/GDN/WRO/POZ/LCJ/RZE/BZG; wszystkie dziewięć polskich lotnisk.")
        self.assertEqual(refresh_endpoint_text(once), once)
        self.assertEqual(once.count("BZG"), 1)
        self.assertNotIn("dziewięć", once)


if __name__ == "__main__":
    unittest.main()
