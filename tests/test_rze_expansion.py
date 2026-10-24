"""RZE integration and frozen eight-endpoint regressions; no live HTTP."""
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
from scripts.discover_transfer_routes import discover_candidates
from scripts.search_airports import POLISH_AIRPORTS, ENDPOINT_TIMEZONES, validate_polish_transfer
from scripts.verify_wizz_expansion_schedules import required_routes
from scripts.wizz_schedules import load_wizz_route_data, resolve_schedule
from tests.test_airport_expansion import leg

ROOT = Path(__file__).resolve().parents[1]
EIGHT = ("WAW", "WMI", "KTW", "KRK", "GDN", "WRO", "POZ", "LCJ")
HUBS = {"BRS", "DUB", "EDI", "LTN", "MAN", "MXP", "STN"}
START, END = date(2026, 10, 23), date(2026, 11, 22)


class RzeExpansionTests(unittest.TestCase):
    def test_rze_retained_in_current_registry_and_nine_scopes(self):
        self.assertEqual(POLISH_AIRPORTS, EIGHT + ("RZE", "BZG", "LUZ", "SZY", "RDO"))
        self.assertEqual(ENDPOINT_TIMEZONES["RZE"], "Europe/Warsaw")
        files = list((ROOT / "data").glob("*transfer-airports.json"))
        self.assertEqual(len(files), 9)
        for path in files:
            self.assertEqual(json.loads(path.read_text())["scope"]["polish_airports"], list(POLISH_AIRPORTS))

    def test_exact_officially_reviewed_rze_permissions(self):
        for module, hubs in ((collect_step3, HUBS), (collect_step4, {"FCO"})):
            self.assertEqual({r["iata"] for r in module.load_allowlist()["airports"]
                              if "RZE" in r["polish_airports"]}, hubs)
        config = collect_step5.load_allowlist()["variants"]
        for variant, hubs in ((collect_step5.VARIANT_A, {"FCO"}), (collect_step5.VARIANT_B, {"MXP"})):
            self.assertEqual({r["iata"] for r in config[variant]["airports"]
                              if "RZE" in r["polish_airports"]}, hubs)
        for name in ("binter", "iberia", "vueling", "air-europa", "volotea", "canaryfly"):
            document = json.loads((ROOT / "data" / f"{name}-transfer-airports.json").read_text())
            actual = {r["iata"] for r in document["airports"] if any(
                p.get("polish_airport") == "RZE" for p in r.get("polish_routes", []) + r.get("eligibility_evidence", []))}
            self.assertEqual(actual, {"ALC"} if name == "vueling" else set(), name)

    def test_full_direct_and_saved_transfer_plans(self):
        direct = expected_queries("2", START, END)
        self.assertEqual(len(direct), 104 * 31)
        expected = [("2", c, t) for c in ("Ryanair", "Wizz Air") for t in ("TFN", "TFS")]
        expected += [("1c", "Ryanair", "ALC")]
        expected += [("3", "Ryanair", h) for h in HUBS]
        expected += [("4", "Wizz Air", "FCO"), ("5", "Wizz Air", "FCO"), ("5", "Ryanair", "MXP")]
        for step, carrier, hub in expected:
            plan = expected_queries(step, START, END)
            for a, b in (("RZE", hub), (hub, "RZE")):
                self.assertEqual({day for c, o, d, day, kind in plan if (c, o, d) == (carrier, a, b)},
                                 {(START + timedelta(days=n)).isoformat() for n in range(31)}, (step, a, b))

    @patch("scripts.collect_step1.collect_ryanair_route", return_value=[])
    @patch("scripts.collect_step1.collect_wizz_route", return_value=[])
    def test_actual_full_low_cost_executor_even_with_empty_other_carrier(self, wizz, ryanair):
        collect_step1.collect_low_cost_legs(["MAD", "PMI"], START, END, {}, 2, {})
        for collector in (wizz, ryanair):
            self.assertEqual(collector.call_count, 52)
            calls = {call.args[:4] for call in collector.call_args_list}
            for hub in ("MAD", "PMI"):
                self.assertIn(("RZE", hub, START, END), calls)
                self.assertIn((hub, "RZE", START, END), calls)

    def test_all_six_resident_builders_both_directions_and_frozen_eight(self):
        # Synthetic MAD permissions exercise builders; they do not assert a live RZE/MAD route.
        for step, carrier in (("1", "Binter"), ("1b", "Iberia"), ("1c", "Vueling"),
                              ("1d", "Air Europa"), ("1e", "Volotea"), ("1f", "Canaryfly")):
            module = importlib.import_module("scripts.collect_step" + step)
            low = [leg("Ryanair", p, "2026-11-01T06:00:00+01:00", "MAD", "2026-11-01T09:00:00+01:00", f"FR{n}")
                   for n, p in enumerate(EIGHT + ("RZE",))]
            low += [leg("Ryanair", "MAD", "2026-11-02T16:00:00+01:00", p, "2026-11-02T19:00:00+01:00", f"FR{n}")
                    for n, p in enumerate(EIGHT + ("RZE",))]
            resident = [leg(carrier, "MAD", "2026-11-01T12:00:00+01:00", "TFN", "2026-11-01T14:00:00+00:00"),
                        leg(carrier, "TFN", "2026-11-02T08:00:00+00:00", "MAD", "2026-11-02T12:00:00+01:00")]
            after = module.build_connections(low, resident)
            new = [r for r in after if "RZE" in (r["origin_airport"], r["destination_airport"])]
            self.assertEqual({r["direction"] for r in new}, {"poland_to_tenerife", "tenerife_to_poland"})
            with patch.object(module, "POLISH_AIRPORTS", EIGHT):
                before = module.build_connections([r for r in low if "RZE" not in (r["departure_airport"], r["arrival_airport"])], resident)
            self.assertEqual(before, [r for r in after if r not in new], step)

    def test_direct_and_all_low_cost_variants_frozen_eight_both_directions(self):
        for module, hub, a, b, variant in (
            (collect_step3, "STN", "Ryanair", "Ryanair", None),
            (collect_step4, "FCO", "Wizz Air", "Wizz Air", None),
            (collect_step5, "FCO", "Ryanair", "Wizz Air", collect_step5.VARIANT_A),
            (collect_step5, "MXP", "Wizz Air", "Ryanair", collect_step5.VARIANT_B)):
            config = copy.deepcopy(module.load_allowlist())
            rules = config["airports"] if variant is None else config["variants"][variant]["airports"]
            next(r for r in rules if r["iata"] == hub)["polish_airports"] = list(EIGHT + ("RZE",))
            legs = [leg(a, "TFS", "2026-11-01T06:00:00+00:00", hub, "2026-11-01T10:00:00+01:00", "XX0"),
                    leg(a, hub, "2026-11-02T12:00:00+01:00", "TFS", "2026-11-02T15:00:00+00:00", "XX1")]
            for n, p in enumerate(EIGHT + ("RZE",)):
                legs += [leg(b, hub, "2026-11-01T13:00:00+01:00", p, "2026-11-01T16:00:00+01:00", f"XX{n+2}"),
                         leg(b, p, "2026-11-02T06:00:00+01:00", hub, "2026-11-02T09:00:00+01:00", f"XX{n+20}")]
            after = module.build_connections(legs, config, 4.0)
            new = [r for r in after if "RZE" in (r["origin_airport"], r["destination_airport"])]
            self.assertEqual({r["direction"] for r in new}, {"poland_to_tenerife", "tenerife_to_poland"})
            module.validate_document({"results": after}, config)
            previous = copy.deepcopy(config)
            old_rules = previous["airports"] if variant is None else previous["variants"][variant]["airports"]
            for row in old_rules:
                row["polish_airports"] = [p for p in row["polish_airports"] if p in EIGHT]
            with patch.object(module, "POLISH_AIRPORTS", EIGHT):
                before = module.build_connections([r for r in legs if "RZE" not in (r["departure_airport"], r["arrival_airport"])], previous, 4.0)
            self.assertEqual(before, [r for r in after if r not in new])
        direct = []
        for n, p in enumerate(EIGHT + ("RZE",)):
            direct += [leg("Ryanair", p, "2026-11-01T10:00:00+01:00", "TFS", "2026-11-01T15:00:00+00:00", f"FR{n}"),
                       leg("Ryanair", "TFS", "2026-11-02T10:00:00+00:00", p, "2026-11-02T16:00:00+01:00", f"FR{n+20}")]
        after = collect_step2.build_results(direct)
        with patch.object(collect_step2, "POLISH_AIRPORTS", EIGHT):
            before = collect_step2.build_results([r for r in direct if "RZE" not in (r["departure_airport"], r["arrival_airport"])])
        self.assertEqual(before, [r for r in after if "RZE" not in (r["origin_airport"], r["destination_airport"])])

    def test_verified_rze_fco_schedule_clocks(self):
        schedules, overrides = load_wizz_route_data()
        for a, b, stamp, expected in (
            ("RZE", "FCO", "2026-10-24T08:35:00+02:00", ("W46068", 140)),
            ("RZE", "FCO", "2026-11-02T10:45:00+01:00", ("W46068", 130)),
            ("RZE", "FCO", "2026-11-05T22:45:00+01:00", ("W46068", 130)),
            ("FCO", "RZE", "2026-11-02T07:55:00+01:00", ("W46067", 135))):
            self.assertEqual(resolve_schedule(schedules, overrides, a, b, datetime.fromisoformat(stamp)), expected)

    def test_no_extra_polish_transfer_roles_and_dst_boundaries(self):
        validate_polish_transfer("KRK", "GDN", "step5_variant_b")
        for p, h in (("RZE", "GDN"), ("RZE", "RZE"), ("KRK", "RZE"), ("RZE", "LCJ")):
            with self.assertRaises(RuntimeError):
                validate_polish_transfer(p, h, "step5_variant_b")
        arrival = datetime.fromisoformat("2026-10-25T00:30:00+01:00")
        for wait, count in ((119, 0), (120, 1), (1440, 1), (1441, 0)):
            departure = (arrival.astimezone(timezone.utc) + timedelta(minutes=wait)).astimezone(ZoneInfo("Europe/London"))
            landing = (departure.astimezone(timezone.utc) + timedelta(minutes=150)).astimezone(ZoneInfo("Europe/Warsaw"))
            legs = [leg("Ryanair", "TFS", "2026-10-24T19:00:00+01:00", "STN", arrival.isoformat(), "FR1"),
                    leg("Ryanair", "STN", departure.isoformat(), "RZE", landing.isoformat(), "FR2")]
            rows = collect_step3.build_connections(legs, collect_step3.load_allowlist(), 4.0)
            self.assertEqual(len(rows), count, wait)
            if rows:
                self.assertEqual(rows[0]["layover_minutes"], wait)

    def test_global_new_hub_discovery_configuration_plan_and_idempotence(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            snapshot = {"as_of": "2026-10-23", "routes": {"ryanair": [["RZE", "NEW"], ["NEW", "TFS"]],
                         "wizzair": [], "binter": []}, "airports": {"NEW": {
                             "name": "Synthetic airport", "country_code": "GB", "timezone": "Europe/London"}}}
            self.assertNotIn("NEW", {r["iata"] for r in collect_step3.load_allowlist()["airports"]})
            self.assertEqual([(r.iata, r.polish_airports) for r in discover_candidates(snapshot)["step3"]], [("NEW", ("RZE",))])
            evidence = {"endpoint": "RZE", "snapshot_date": "2026-10-23", "period_from": "2026-10-23", "period_to": "2026-11-22", "routes": []}
            (folder / "snapshot.json").write_text(json.dumps(snapshot))
            (folder / "schedules.json").write_text(json.dumps(evidence))
            argv = ["build", "--endpoint", "RZE", "--snapshot", str(folder / "snapshot.json"), "--schedules", str(folder / "schedules.json"),
                    "--from-date", "2026-10-23", "--baseline-directory", str(ROOT / "data"), "--output-directory", str(folder / "review")]
            with patch("sys.argv", argv):
                build_configuration()
            config = json.loads((folder / "review/ryanair-transfer-airports.json").read_text())
            self.assertEqual(next(r for r in config["airports"] if r["iata"] == "NEW")["polish_airports"], ["RZE"])
            with patch.object(collect_step3, "load_allowlist", return_value=config):
                plan = expected_queries("3", START, START)
            for pair in (("RZE", "NEW"), ("NEW", "RZE"), ("TFS", "NEW"), ("NEW", "TFS")):
                self.assertIn(("Ryanair", *pair, START.isoformat(), "calendar"), plan)
            argv[argv.index("--baseline-directory") + 1] = str(folder / "review")
            argv[argv.index("--output-directory") + 1] = str(folder / "second")
            with patch("sys.argv", argv):
                build_configuration()
            for p in (folder / "review").glob("*.json"):
                self.assertEqual(json.loads(p.read_text()), json.loads((folder / "second" / p.name).read_text()))

    def test_new_wizz_tenerife_leg_variant_b_is_required(self):
        snapshot = {"routes": {"ryanair": [["RZE", "NEW"]], "wizzair": [["NEW", "TFS"]], "binter": []}, "airports": {}}
        required = required_routes(snapshot, "RZE")
        self.assertIn(("NEW", "TFS"), required)
        self.assertIn(("TFS", "NEW"), required)

    def test_eight_endpoint_report_and_missing_single_rze_day_fail(self):
        plan = expected_queries("2", START, START)
        for missing in ({key for key in plan if "RZE" in key[1:3]}, {next(key for key in plan if "RZE" in key[1:3])}):
            tracker = Coverage("2", START, START, plan, "rze-test")
            for c, o, d, day, kind in plan - missing:
                tracker.record(c, o, d, START, START, [], "google_flights_http" if c == "Ryanair" else "timetableV2")
            self.assertEqual(tracker.report()["missing_queries"], len(missing))
            with self.assertRaisesRegex(RuntimeError, "Incomplete source coverage"):
                tracker.verify()
        old = Coverage("2", START, START, {key for key in plan if set(key[1:3]).intersection(EIGHT)}, "old-eight")
        for c, o, d, day, kind in old.expected:
            old.record(c, o, d, START, START, [], "google_flights_http" if c == "Ryanair" else "timetableV2")
        with self.assertRaisesRegex(RuntimeError, "Incomplete source coverage"):
            validate_coverage({"collection_coverage": old.verify()}, "2", START, START)

    def test_endpoint_text_ninth_is_idempotent(self):
        once = refresh_endpoint_text("WAW/WMI/KTW/KRK/GDN/WRO/POZ/LCJ/RZE; wszystkie dziewięć polskich lotnisk.")
        self.assertEqual(refresh_endpoint_text(once), once)
        self.assertEqual(once.count("RZE"), 1)
        self.assertNotIn("dziewięć", once)


if __name__ == "__main__":
    unittest.main()
