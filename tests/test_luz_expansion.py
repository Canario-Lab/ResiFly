"""LUZ integration and frozen TEN; permanent, narrowly scoped GDN approval."""
import copy
from datetime import date, datetime, timedelta
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import collect_step1, collect_step2, collect_step3, collect_step4, collect_step5
from scripts.build_gdn_config_patch import main as build_configuration, refresh_endpoint_text
from scripts.collection_coverage import Coverage, expected_queries, validate_coverage
from scripts.discover_transfer_routes import discover_candidates, build_plan, load_documents
from scripts.search_airports import POLISH_AIRPORTS, ENDPOINT_TIMEZONES, ENDPOINT_TRANSFER_EXCEPTIONS, validate_polish_transfer
from scripts.verify_wizz_expansion_schedules import required_routes
from scripts.wizz_schedules import load_wizz_route_data, resolve_schedule
from tests.test_airport_expansion import leg

ROOT = Path(__file__).resolve().parents[1]
TEN = ("WAW", "WMI", "KTW", "KRK", "GDN", "WRO", "POZ", "LCJ", "RZE", "BZG")
START, END = date(2026, 10, 24), date(2026, 11, 23)


class LuzExpansionTests(unittest.TestCase):
    def test_eleventh_endpoint_and_exact_nine_scopes(self):
        self.assertEqual(POLISH_AIRPORTS, TEN + ("LUZ",))
        self.assertEqual(ENDPOINT_TIMEZONES["LUZ"], "Europe/Warsaw")
        paths = list((ROOT / "data").glob("*transfer-airports.json"))
        self.assertEqual(len(paths), 9)
        for path in paths:
            self.assertEqual(json.loads(path.read_text())["scope"]["polish_airports"], list(POLISH_AIRPORTS))

    def test_exact_reviewed_luz_permissions_not_copied_from_bzg(self):
        self.assertEqual({r["iata"] for r in collect_step3.load_allowlist()["airports"] if "LUZ" in r["polish_airports"]}, {"BGY", "DUB", "LTN"})
        self.assertFalse(any("LUZ" in r["polish_airports"] for r in collect_step4.load_allowlist()["airports"]))
        mixed = collect_step5.load_allowlist()["variants"]
        for variant, expected in ((collect_step5.VARIANT_A, {"LTN"}), (collect_step5.VARIANT_B, {"GDN"})):
            self.assertEqual({r["iata"] for r in mixed[variant]["airports"] if "LUZ" in r["polish_airports"]}, expected)
        for name in ("binter", "iberia", "vueling", "air-europa", "volotea", "canaryfly"):
            config = json.loads((ROOT / "data" / f"{name}-transfer-airports.json").read_text())
            self.assertFalse(any(p.get("polish_airport") == "LUZ" for r in config["airports"]
                                 for p in r.get("polish_routes", []) + r.get("eligibility_evidence", [])), name)

    def test_permanent_gdn_only_for_krk_luz_and_only_variant_b(self):
        self.assertEqual(ENDPOINT_TRANSFER_EXCEPTIONS, {("step5_variant_b", "GDN"): frozenset({"KRK", "LUZ"})})
        for polish in ("KRK", "LUZ"):
            validate_polish_transfer(polish, "GDN", "step5_variant_b")
        for polish in set(POLISH_AIRPORTS) - {"KRK", "LUZ"}:
            with self.assertRaises(RuntimeError): validate_polish_transfer(polish, "GDN", "step5_variant_b")
        for step in ("step1", "step3", "step4", "step5_variant_a"):
            with self.assertRaises(RuntimeError): validate_polish_transfer("LUZ", "GDN", step)
        for polish, hub in (("LUZ", "LUZ"), ("GDN", "GDN"), ("KRK", "LUZ")):
            with self.assertRaises(RuntimeError): validate_polish_transfer(polish, hub, "step5_variant_b")
        snapshot = {"routes": {"ryanair": [["LUZ", "GDN"], ["KRK", "GDN"], ["WRO", "GDN"]],
                               "wizzair": [["GDN", "TFS"]], "binter": []}, "airports": {}}
        rows = discover_candidates(snapshot)
        gdn = next(r for r in rows["step5_variant_b"] if r.iata == "GDN")
        self.assertEqual(set(gdn.polish_airports), {"KRK", "LUZ"})
        self.assertFalse(any(r.iata == "GDN" for r in rows["step3"] + rows["step4"] + rows["step5_variant_a"]))

    def test_complete_direct_and_saved_leg_calendars(self):
        self.assertEqual(len(list(collect_step2.route_matrix())), 44)
        self.assertEqual(len(expected_queries("2", START, END)), 88 * 31)
        requirements = [("2", c, t) for c in ("Ryanair", "Wizz Air") for t in ("TFN", "TFS")]
        requirements += [("3", "Ryanair", h) for h in ("BGY", "DUB", "LTN")]
        requirements += [("5", "Wizz Air", "LTN"), ("5", "Ryanair", "GDN")]
        requirements += [("1", c, h) for c in ("Ryanair", "Wizz Air") for h in ("FUE", "LPA", "MAD", "PMI", "SVQ", "VLC")]
        requirements += [("1b", c, "MAD") for c in ("Ryanair", "Wizz Air")]
        days = {(START + timedelta(days=n)).isoformat() for n in range(31)}
        for step, carrier, hub in requirements:
            plan = expected_queries(step, START, END)
            for a, b in (("LUZ", hub), (hub, "LUZ")):
                self.assertEqual({day for c, o, d, day, kind in plan if (c, o, d) == (carrier, a, b)}, days, (step, carrier, a, b))
        plan = expected_queries("5", START, END)
        for a, b in (("GDN", "TFS"), ("TFS", "GDN")):
            self.assertEqual({day for c, o, d, day, kind in plan if (c, o, d) == ("Wizz Air", a, b)}, days)

    @patch("scripts.collect_step1.collect_ryanair_route", return_value=[])
    @patch("scripts.collect_step1.collect_wizz_route", return_value=[])
    def test_actual_executor_full_matrix_despite_empty_other_carrier(self, wizz, ryanair):
        collect_step1.collect_low_cost_legs(["MAD", "PMI"], START, END, {}, 2, {})
        for collector in (wizz, ryanair):
            self.assertEqual(collector.call_count, 44)
            for hub in ("MAD", "PMI"):
                self.assertIn((hub, "LUZ", START, END), {c.args[:4] for c in collector.call_args_list})
                self.assertIn(("LUZ", hub, START, END), {c.args[:4] for c in collector.call_args_list})

    def test_six_resident_builders_both_directions_preserve_frozen_ten(self):
        # Synthetic MAD exercises all mechanics, not a real LUZ/MAD permission.
        for step, carrier in (("1", "Binter"), ("1b", "Iberia"), ("1c", "Vueling"),
                              ("1d", "Air Europa"), ("1e", "Volotea"), ("1f", "Canaryfly")):
            module = importlib.import_module("scripts.collect_step" + step)
            low = []
            for n, p in enumerate(TEN + ("LUZ",)):
                low += [leg("Ryanair", p, "2026-11-01T06:00:00+01:00", "MAD", "2026-11-01T09:00:00+01:00", f"FR{n}"),
                        leg("Ryanair", "MAD", "2026-11-02T16:00:00+01:00", p, "2026-11-02T19:00:00+01:00", f"FR{n+20}")]
            resident = [leg(carrier, "MAD", "2026-11-01T12:00:00+01:00", "TFN", "2026-11-01T14:00:00+00:00"),
                        leg(carrier, "TFN", "2026-11-02T08:00:00+00:00", "MAD", "2026-11-02T12:00:00+01:00")]
            after = module.build_connections(low, resident)
            new = [r for r in after if "LUZ" in (r["origin_airport"], r["destination_airport"])]
            self.assertEqual({r["direction"] for r in new}, {"poland_to_tenerife", "tenerife_to_poland"})
            with patch.object(module, "POLISH_AIRPORTS", TEN):
                before = module.build_connections([r for r in low if "LUZ" not in (r["departure_airport"], r["arrival_airport"])], resident)
            self.assertEqual(before, [r for r in after if r not in new], step)

    def test_direct_and_low_cost_builders_preserve_frozen_ten(self):
        for module, hub, a, b, variant in (
            (collect_step3, "DUB", "Ryanair", "Ryanair", None),
            (collect_step4, "FCO", "Wizz Air", "Wizz Air", None),
            (collect_step5, "LTN", "Ryanair", "Wizz Air", collect_step5.VARIANT_A),
            (collect_step5, "MXP", "Wizz Air", "Ryanair", collect_step5.VARIANT_B)):
            config = copy.deepcopy(module.load_allowlist())
            rules = config["airports"] if variant is None else config["variants"][variant]["airports"]
            next(r for r in rules if r["iata"] == hub)["polish_airports"] = list(TEN + ("LUZ",))
            legs = [leg(a, "TFS", "2026-11-01T06:00:00+00:00", hub, "2026-11-01T10:00:00+01:00", "XX0"),
                    leg(a, hub, "2026-11-02T12:00:00+01:00", "TFS", "2026-11-02T15:00:00+00:00", "XX1")]
            for n, p in enumerate(TEN + ("LUZ",)):
                legs += [leg(b, hub, "2026-11-01T13:00:00+01:00", p, "2026-11-01T16:00:00+01:00", f"XX{n+2}"),
                         leg(b, p, "2026-11-02T06:00:00+01:00", hub, "2026-11-02T09:00:00+01:00", f"XX{n+30}")]
            after = module.build_connections(legs, config, 4.0)
            new = [r for r in after if "LUZ" in (r["origin_airport"], r["destination_airport"])]
            self.assertEqual({r["direction"] for r in new}, {"poland_to_tenerife", "tenerife_to_poland"})
            module.validate_document({"results": after}, config)
            previous = copy.deepcopy(config)
            old = previous["airports"] if variant is None else previous["variants"][variant]["airports"]
            for row in old: row["polish_airports"] = [p for p in row["polish_airports"] if p in TEN]
            with patch.object(module, "POLISH_AIRPORTS", TEN):
                before = module.build_connections([r for r in legs if "LUZ" not in (r["departure_airport"], r["arrival_airport"])], previous, 4.0)
            self.assertEqual(before, [r for r in after if r not in new])
        direct = [leg("Ryanair", p, "2026-11-01T10:00:00+01:00", "TFS", "2026-11-01T15:00:00+00:00", f"FR{n}") for n, p in enumerate(TEN + ("LUZ",))]
        direct += [leg("Ryanair", "TFS", "2026-11-02T10:00:00+00:00", p, "2026-11-02T16:00:00+01:00", f"FR{n+20}") for n, p in enumerate(TEN + ("LUZ",))]
        with patch.object(collect_step2, "POLISH_AIRPORTS", TEN):
            before = collect_step2.build_results([r for r in direct if "LUZ" not in (r["departure_airport"], r["arrival_airport"])])
        self.assertEqual(before, [r for r in collect_step2.build_results(direct) if "LUZ" not in (r["origin_airport"], r["destination_airport"])])

    def test_gdn_real_permission_both_directions_and_120_1440_bounds(self):
        config = collect_step5.load_allowlist()
        for wait, count in ((115, 0), (119, 0), (120, 1), (1440, 1), (1441, 0)):
            arrival = datetime.fromisoformat("2026-11-01T14:00:00+01:00")
            departure = arrival + timedelta(minutes=wait)
            legs = [leg("Wizz Air", "TFS", "2026-11-01T08:00:00+00:00", "GDN", arrival.isoformat(), "W61710"),
                    leg("Ryanair", "GDN", departure.isoformat(), "LUZ", (departure+timedelta(minutes=75)).isoformat(), "FR6112")]
            self.assertEqual(len(collect_step5.build_connections(legs, config, 4.0)), count)
        legs = [leg("Ryanair", "LUZ", "2026-11-01T06:00:00+01:00", "GDN", "2026-11-01T07:15:00+01:00", "FR6111"),
                leg("Wizz Air", "GDN", "2026-11-01T10:00:00+01:00", "TFS", "2026-11-01T15:00:00+00:00", "W61709"),
                leg("Wizz Air", "TFS", "2026-11-02T08:00:00+00:00", "GDN", "2026-11-02T14:00:00+01:00", "W61710"),
                leg("Ryanair", "GDN", "2026-11-02T17:00:00+01:00", "LUZ", "2026-11-02T18:15:00+01:00", "FR6112")]
        rows = collect_step5.build_connections(legs, config, 4.0)
        self.assertEqual({r["direction"] for r in rows}, {"poland_to_tenerife", "tenerife_to_poland"})
        collect_step5.validate_document({"results":rows}, config)

    def test_verified_wizz_uk_season_times_and_previous_rze_exception(self):
        schedules, overrides = load_wizz_route_data()
        for a, b, stamp, expected in (
            ("LUZ", "LTN", "2026-10-24T10:10:00+02:00", ("W92065", 165)),
            ("LUZ", "LTN", "2026-10-26T10:00:00+01:00", ("W92065", 175)),
            ("LTN", "LUZ", "2026-10-24T05:55:00+01:00", ("W92066", 160)),
            ("LTN", "LUZ", "2026-10-25T17:20:00+00:00", ("W92066", 155)),
            ("RZE", "FCO", "2026-10-24T08:35:00+02:00", ("W46068", 140))):
            self.assertEqual(resolve_schedule(schedules, overrides, a, b, datetime.fromisoformat(stamp)), expected)

    def test_old_ten_report_or_missing_one_luz_day_fail_closed(self):
        plan = expected_queries("2", START, START)
        old_plan = {key for key in plan if set(key[1:3]).intersection(TEN)}
        self.assertEqual(len(old_plan), 80)
        for subset in (old_plan, plan - {next(k for k in plan if "LUZ" in k[1:3])}):
            tracker = Coverage("2", START, START, subset, "luz-test")
            for c, o, d, day, kind in subset:
                tracker.record(c,o,d,START,START,[], "google_flights_http" if c == "Ryanair" else "timetableV2")
            with self.assertRaisesRegex(RuntimeError, "Incomplete source coverage"):
                validate_coverage({"collection_coverage":tracker.verify()}, "2", START, START)

    def test_global_new_mixed_hub_requires_both_technical_directions(self):
        snapshot = {"as_of": "2026-10-23", "routes": {"ryanair":[["LUZ","NEW"]], "wizzair":[["NEW","TFS"]], "binter":[]},
                    "airports":{"NEW":{"name":"Synthetic airport","country_code":"GB","timezone":"Europe/London"}}}
        self.assertIn(("NEW","TFS"), required_routes(snapshot,"LUZ"))
        self.assertIn(("TFS","NEW"), required_routes(snapshot,"LUZ"))
        report=build_plan(snapshot,load_documents())
        self.assertIn("NEW", {r["iata"] for r in report["steps"]["step5_variant_b"]["pending"]})
        self.assertNotIn("NEW", {r["iata"] for r in report["steps"]["step5_variant_b"]["ready"]})

    def test_global_new_hub_configuration_executor_and_plan(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            snapshot = {"as_of":"2026-10-23", "routes":{"ryanair":[["LUZ","NEW"],["NEW","TFS"]],
                        "wizzair":[["NEW","TFS"]], "binter":[]},
                        "airports":{"NEW":{"name":"Synthetic airport","country_code":"GB","timezone":"Europe/London"}}}
            evidence = {"endpoint":"LUZ", "snapshot_date":"2026-10-23", "period_from":str(START), "period_to":str(END),
                        "routes":[{"origin":a,"destination":b,"flight_number":n,"duration_minutes":240,
                                   "departure_at":stamp,"source":"https://www.google.com/travel/flights"}
                                  for a,b,n,stamp in (("TFS","NEW","W90001","2026-11-01T08:00:00+00:00"),
                                                      ("NEW","TFS","W90002","2026-11-02T08:00:00+00:00"))]}
            (folder/'snapshot.json').write_text(json.dumps(snapshot))
            (folder/'schedules.json').write_text(json.dumps(evidence))
            argv=['build','--endpoint','LUZ','--snapshot',str(folder/'snapshot.json'),'--schedules',str(folder/'schedules.json'),
                  '--from-date',str(START),'--baseline-directory',str(ROOT/'data'),'--output-directory',str(folder/'review')]
            with patch('sys.argv',argv): build_configuration()
            for module, filename, step in ((collect_step3,'ryanair-transfer-airports.json','3'),
                                           (collect_step5,'mixed-transfer-airports.json','5')):
                config=json.loads((folder/'review'/filename).read_text())
                matrix=module.route_matrix(config)
                with patch.object(module,'load_allowlist',return_value=config): plan=expected_queries(step,START,END)
                carrier_pairs={'Ryanair':matrix} if step=='3' else matrix
                for carrier,pairs in carrier_pairs.items():
                    for a,b in pairs:
                        if 'NEW' in (a,b):
                            self.assertEqual(sum(c==carrier and o==a and d==b for c,o,d,day,kind in plan),31)
                if step=='3':
                    with patch.object(module,'collect_ryanair_route',return_value=[]) as fetch:
                        module.collect_routes([p for p in matrix if 'NEW' in p],START,END,{},'test',2)
                    self.assertEqual({c.args[:4] for c in fetch.call_args_list},
                                     {(a,b,START,END) for a,b in matrix if 'NEW' in (a,b)})
                else:
                    with patch.object(module,'collect_ryanair_routes',return_value=[]) as ryanair, \
                         patch.object(module,'collect_wizz_routes',return_value=[]) as wizz:
                        module.collect_full_calendars(matrix,START,END,{},'test',2)
                    self.assertEqual(ryanair.call_args.args[:3],(matrix['Ryanair'],START,END))
                    self.assertEqual(wizz.call_args.args[:3],(matrix['Wizz Air'],START,END))
            argv[argv.index('--baseline-directory')+1]=str(folder/'review')
            argv[argv.index('--output-directory')+1]=str(folder/'second')
            with patch('sys.argv',argv): build_configuration()
            for path in (folder/'review').glob('*.json'):
                self.assertEqual(json.loads(path.read_text()),json.loads((folder/'second'/path.name).read_text()))

    def test_eleventh_endpoint_text_idempotence(self):
        text="WAW/WMI/KTW/KRK/GDN/WRO/POZ/LCJ/RZE/BZG; wszystkie dziesięć polskich lotnisk."
        once=refresh_endpoint_text(text)
        self.assertEqual(refresh_endpoint_text(once),once)
        self.assertEqual(once.count("LUZ"),1)
        self.assertNotIn("dziesięć",once)

    def test_new_tenerife_airport_at_existing_hub_requires_explicit_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            snapshot={"as_of":"2026-10-23", "routes":{"ryanair":[["LUZ","LTN"],["TFN","LTN"]],
                      "wizzair":[],"binter":[]}, "airports":{}}
            evidence={"endpoint":"LUZ","snapshot_date":"2026-10-23","period_from":str(START),"period_to":str(END),"routes":[]}
            (folder/'snapshot.json').write_text(json.dumps(snapshot))
            (folder/'schedules.json').write_text(json.dumps(evidence))
            argv=['build','--endpoint','LUZ','--snapshot',str(folder/'snapshot.json'),'--schedules',str(folder/'schedules.json'),
                  '--from-date',str(START),'--baseline-directory',str(ROOT/'data'),'--output-directory',str(folder/'review')]
            with patch('sys.argv',argv), self.assertRaisesRegex(RuntimeError,'Review new Tenerife airports explicitly'):
                build_configuration()
            self.assertFalse((folder/'review/ryanair-transfer-airports.json').exists())


if __name__ == "__main__":
    unittest.main()
