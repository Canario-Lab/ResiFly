"""Two endpoint migration, a genuinely new NRN hub and frozen ELEVEN regression."""
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
from scripts.search_airports import POLISH_AIRPORTS, ENDPOINT_TIMEZONES, validate_polish_transfer
from scripts.wizz_schedules import load_wizz_route_data
from tests.test_airport_expansion import leg

ROOT = Path(__file__).resolve().parents[1]
ELEVEN = ("WAW", "WMI", "KTW", "KRK", "GDN", "WRO", "POZ", "LCJ", "RZE", "BZG", "LUZ")
TARGET = ELEVEN + ("SZY", "RDO")
START, END = date(2026, 10, 24), date(2026, 11, 23)


class SzyRdoExpansionTests(unittest.TestCase):
    def test_thirteen_registry_and_nine_exact_scopes(self):
        self.assertEqual(POLISH_AIRPORTS, TARGET + ("SZZ", "IEG"))
        for endpoint in ("SZY", "RDO"):
            self.assertEqual(ENDPOINT_TIMEZONES[endpoint], "Europe/Warsaw")
        paths = list((ROOT / "data").glob("*transfer-airports.json"))
        self.assertEqual(len(paths), 10)
        for path in paths:
            self.assertEqual(json.loads(path.read_text())["scope"]["polish_airports"], list(POLISH_AIRPORTS))

    def test_reviewed_permissions_new_nrn_not_all_existing_endpoints(self):
        config = collect_step3.load_allowlist()
        self.assertEqual({r["iata"] for r in config["airports"] if "SZY" in r["polish_airports"]}, {"NRN", "STN"})
        nrn = next(r for r in config["airports"] if r["iata"] == "NRN")
        self.assertEqual(nrn["polish_airports"], ["SZY"])
        self.assertEqual(nrn["tenerife_airports"], ["TFS"])
        self.assertEqual(config["airport_timezones"]["NRN"], "Europe/Berlin")
        self.assertFalse(nrn["resident_discount_eligible_on_tenerife_leg"])
        self.assertEqual(nrn["tenerife_leg_fare_multiplier"], 1.0)
        self.assertIn("NRN", config["resident_discount_on_tenerife_leg"]["ineligible_transfer_airports"])
        for module in (collect_step3, collect_step4):
            self.assertFalse(any("RDO" in r["polish_airports"] for r in module.load_allowlist()["airports"]))
        self.assertFalse(any("SZY" in r["polish_airports"] for r in collect_step4.load_allowlist()["airports"]))
        for variant in collect_step5.load_allowlist()["variants"].values():
            self.assertFalse(any(set(("SZY", "RDO")) & set(r["polish_airports"]) for r in variant["airports"]))
        for name in ("binter", "iberia", "vueling", "air-europa", "volotea", "canaryfly"):
            config = json.loads((ROOT / "data" / f"{name}-transfer-airports.json").read_text())
            self.assertFalse(any(r.get("polish_airport") in ("SZY", "RDO") for a in config["airports"]
                                 for r in a.get("polish_routes", []) + a.get("eligibility_evidence", [])))

    def test_complete_plans_and_actual_executor_even_with_empty_other_carrier(self):
        self.assertEqual(len(list(collect_step2.route_matrix())), 60)
        self.assertEqual(len(expected_queries("2", START, END)), 3720)
        self.assertEqual(len(expected_queries("1", START, END)), 11904)
        self.assertEqual(len(expected_queries("1b", START, END)), 1984)
        for endpoint in ("SZY", "RDO"):
            for step, hubs in (("2", ("TFN", "TFS")), ("1", ("FUE", "LPA", "MAD", "PMI", "SVQ", "VLC")), ("1b", ("MAD",))):
                plan = expected_queries(step, START, END)
                for hub in hubs:
                    for carrier in ("Ryanair", "Wizz Air"):
                        for origin, destination in ((endpoint, hub), (hub, endpoint)):
                            self.assertEqual(sum(c == carrier and o == origin and d == destination
                                                 for c, o, d, day, kind in plan), 31)
        with patch.object(collect_step1, "collect_ryanair_route", return_value=[]) as fr, \
             patch.object(collect_step1, "collect_wizz_route", return_value=[]) as wz:
            collect_step1.collect_low_cost_legs(["MAD", "PMI"], START, END, {}, 2, {})
        for collector in (fr, wz):
            self.assertEqual(collector.call_count, 60)
            actual = {c.args[:4] for c in collector.call_args_list}
            for endpoint in ("SZY", "RDO"):
                for hub in ("MAD", "PMI"):
                    self.assertIn((endpoint, hub, START, END), actual)
                    self.assertIn((hub, endpoint, START, END), actual)

    def test_real_nrn_discovery_matrix_executor_matching_both_directions(self):
        snapshot = {"routes": {"ryanair": [["SZY", "NRN"], ["NRN", "TFS"]], "wizzair": [], "binter": []}}
        candidate = discover_candidates(snapshot)["step3"][0]
        self.assertEqual((candidate.iata, candidate.polish_airports, candidate.tenerife_airports), ("NRN", ("SZY",), ("TFS",)))
        config = collect_step3.load_allowlist()
        matrix = [p for p in collect_step3.route_matrix(config) if "NRN" in p]
        self.assertEqual(set(matrix), {("SZY", "NRN"), ("NRN", "SZY"), ("NRN", "TFS"), ("TFS", "NRN")})
        plan = expected_queries("3", START, END)
        self.assertEqual(sum("NRN" in (o, d) for c, o, d, day, kind in plan), 124)
        with patch.object(collect_step3, "collect_ryanair_route", return_value=[]) as fetch:
            collect_step3.collect_routes(matrix, START, END, {}, "test", 2)
        self.assertEqual({c.args[:4] for c in fetch.call_args_list}, {(a, b, START, END) for a, b in matrix})
        rows = collect_step3.build_connections([
            leg("Ryanair", "SZY", "2026-11-01T06:00:00+01:00", "NRN", "2026-11-01T08:00:00+01:00", "FR1"),
            leg("Ryanair", "NRN", "2026-11-01T12:00:00+01:00", "TFS", "2026-11-01T15:00:00+00:00", "FR2"),
            leg("Ryanair", "TFS", "2026-11-02T06:00:00+00:00", "NRN", "2026-11-02T11:00:00+01:00", "RK3"),
            leg("Ryanair", "NRN", "2026-11-02T14:00:00+01:00", "SZY", "2026-11-02T16:00:00+01:00", "FR4"),
        ], config, 4.0)
        collect_step3.validate_document({"results": rows}, config)
        self.assertEqual({r["direction"] for r in rows}, {"poland_to_tenerife", "tenerife_to_poland"})
        for row in rows:
            self.assertEqual(row["transfer_airport"], "NRN")
            self.assertEqual(row["price_total_regular_pln"], row["price_total_resident_estimated_pln"])

    def test_nrn_bounds_and_different_airport_do_not_match(self):
        config = collect_step3.load_allowlist()
        arrival = datetime.fromisoformat("2026-11-01T10:00:00+01:00")
        for wait, count in ((115, 0), (119, 0), (120, 1), (1440, 1), (1441, 0)):
            departure = arrival + timedelta(minutes=wait)
            first = leg("Ryanair", "SZY", "2026-11-01T08:00:00+01:00", "NRN", arrival.isoformat(), "FR1")
            second = leg("Ryanair", "NRN", departure.isoformat(), "TFS", (departure + timedelta(hours=4)).isoformat(), "FR2")
            self.assertEqual(len(collect_step3.build_connections([first, second], config, 4.0)), count)
            second["departure_airport"] = "DUS"
            self.assertEqual(collect_step3.build_connections([first, second], config, 4.0), [])

    def test_nrn_google_parser_uses_registered_timezone_and_individual_fares(self):
        from scripts.collect_step1 import AIRPORT_TIMEZONES, configure_airports_from_allowlist
        from scripts.ryanair_google import parse_google_flights_response
        from tests.test_ryanair_google import DAY, html_for, offer
        with patch.dict(AIRPORT_TIMEZONES):
            configure_airports_from_allowlist(collect_step3.load_allowlist())
            self.assertEqual(AIRPORT_TIMEZONES["NRN"], "Europe/Berlin")
            payload = [None, None, None, [[
                offer("NRN", "TFS", [8, 30], DAY, [12], "1234", 120),
                offer("NRN", "TFS", [22], date(2026,10,26), [1], "1236", 380),
            ]]]
            rows = parse_google_flights_response(html_for(payload), "NRN", "TFS", DAY)
        self.assertEqual([r["price_regular_pln"] for r in rows], [120, 380])
        self.assertTrue(rows[0]["departure_at"].endswith("+01:00"))
        self.assertTrue(rows[0]["arrival_at"].endswith("+00:00"))
        self.assertTrue(rows[1]["arrival_at"].startswith("2026-10-26"))
        self.assertIn("originIata=NRN", rows[0]["booking_url"])

    def test_old_eleven_or_twelve_coverage_and_one_missing_new_day_rejected(self):
        plan = expected_queries("2", START, START)
        for old, count in ((ELEVEN, 88), (ELEVEN + ("SZY",), 96)):
            subset = {q for q in plan if set(q[1:3]) & set(old)}
            self.assertEqual(len(subset), count)
            self.assert_not_certified(subset)
        for endpoint in ("SZY", "RDO"):
            self.assert_not_certified(plan - {next(q for q in plan if endpoint in q[1:3])})
        tracker = Coverage("2", START, START, plan, "thirteen")
        for c, o, d, day, kind in plan:
            tracker.record(c, o, d, START, START, [], "google_flights_http" if c == "Ryanair" else "timetableV2")
        self.assertEqual(validate_coverage({"collection_coverage": tracker.verify()}, "2", START, START), "thirteen")

    def assert_not_certified(self, subset):
        tracker = Coverage("2", START, START, subset, "partial")
        for c, o, d, day, kind in subset:
            tracker.record(c, o, d, START, START, [], "google_flights_http" if c == "Ryanair" else "timetableV2")
        with self.assertRaisesRegex(RuntimeError, "Incomplete source coverage"):
            validate_coverage({"collection_coverage": tracker.verify()}, "2", START, START)

    def test_no_new_polish_hub_approval_and_new_wizz_hub_stays_pending(self):
        for endpoint in ("SZY", "RDO"):
            for step in ("step3", "step4", "step5_variant_a", "step5_variant_b"):
                for hub in ("GDN", "KRK", endpoint):
                    if endpoint == hub:
                        with self.assertRaises(RuntimeError): validate_polish_transfer(endpoint, hub, step)
                    else:
                        validate_polish_transfer(endpoint, hub, step)
        for old in ("KRK", "LUZ"): validate_polish_transfer(old, "GDN", "step5_variant_b")
        snapshot = {"as_of": str(START), "routes": {"ryanair": [["RDO", "NEW"]], "wizzair": [["NEW", "TFS"]], "binter": []},
                    "airports": {"NEW": {"name": "Synthetic", "country_code": "GB", "timezone": "Europe/London"}}}
        report = build_plan(snapshot, load_documents())
        self.assertIn("NEW", {r["iata"] for r in report["steps"]["step5_variant_b"]["pending"]})
        self.assertNotIn("NEW", {r["iata"] for r in report["steps"]["step5_variant_b"]["ready"]})

    def test_six_resident_builders_preserve_frozen_eleven_both_directions(self):
        for step, carrier in (("1", "Binter"), ("1b", "Iberia"), ("1c", "Vueling"), ("1d", "Air Europa"), ("1e", "Volotea"), ("1f", "Canaryfly")):
            module = importlib.import_module("scripts.collect_step" + step)
            low = []
            for n, p in enumerate(TARGET):
                low += [leg("Ryanair", p, "2026-11-01T06:00:00+01:00", "MAD", "2026-11-01T09:00:00+01:00", f"FR{n}"),
                        leg("Ryanair", "MAD", "2026-11-02T16:00:00+01:00", p, "2026-11-02T19:00:00+01:00", f"FR{n+20}")]
            resident = [leg(carrier, "MAD", "2026-11-01T12:00:00+01:00", "TFN", "2026-11-01T14:00:00+00:00"),
                        leg(carrier, "TFN", "2026-11-02T08:00:00+00:00", "MAD", "2026-11-02T12:00:00+01:00")]
            after = module.build_connections(low, resident)
            for p in ("SZY", "RDO"):
                self.assertEqual({r["direction"] for r in after if p in (r["origin_airport"], r["destination_airport"])}, {"poland_to_tenerife", "tenerife_to_poland"})
            old_legs = [r for r in low if set((r["departure_airport"], r["arrival_airport"])) & set(ELEVEN)]
            with patch.object(module, "POLISH_AIRPORTS", ELEVEN): before = module.build_connections(old_legs, resident)
            self.assertEqual(before, [r for r in after if set((r["origin_airport"], r["destination_airport"])) & set(ELEVEN)], step)

    def test_direct_and_three_low_cost_builders_preserve_frozen_eleven(self):
        for module, hub, a, b, variant in ((collect_step3, "STN", "Ryanair", "Ryanair", None),
                (collect_step4, "FCO", "Wizz Air", "Wizz Air", None),
                (collect_step5, "LTN", "Ryanair", "Wizz Air", collect_step5.VARIANT_A),
                (collect_step5, "MXP", "Wizz Air", "Ryanair", collect_step5.VARIANT_B)):
            config = copy.deepcopy(module.load_allowlist())
            rules = config["airports"] if variant is None else config["variants"][variant]["airports"]
            next(r for r in rules if r["iata"] == hub)["polish_airports"] = list(TARGET)
            legs = [leg(a, "TFS", "2026-11-01T06:00:00+00:00", hub, "2026-11-01T10:00:00+01:00", "XX0"),
                    leg(a, hub, "2026-11-02T12:00:00+01:00", "TFS", "2026-11-02T15:00:00+00:00", "XX1")]
            for n, p in enumerate(TARGET):
                legs += [leg(b, hub, "2026-11-01T13:00:00+01:00", p, "2026-11-01T16:00:00+01:00", f"XX{n+2}"),
                         leg(b, p, "2026-11-02T06:00:00+01:00", hub, "2026-11-02T09:00:00+01:00", f"XX{n+30}")]
            after = module.build_connections(legs, config, 4.0)
            module.validate_document({"results": after}, config)
            previous = copy.deepcopy(config)
            groups = previous.get("variants", {"all": previous}).values()
            for group in groups:
                group["airports"] = [r for r in group["airports"] if r["iata"] != "NRN"]
                for row in group["airports"]: row["polish_airports"] = [p for p in row["polish_airports"] if p in ELEVEN]
            with patch.object(module, "POLISH_AIRPORTS", ELEVEN):
                before = module.build_connections([r for r in legs if not set(("SZY", "RDO")) & set((r["departure_airport"], r["arrival_airport"]))], previous, 4.0)
            self.assertEqual(before, [r for r in after if set(ELEVEN) & set((r["origin_airport"], r["destination_airport"]))])
        direct = [leg("Ryanair", p, "2026-11-01T10:00:00+01:00", "TFS", "2026-11-01T15:00:00+00:00", f"FR{n}") for n, p in enumerate(TARGET)]
        direct += [leg("Ryanair", "TFS", "2026-11-02T10:00:00+00:00", p, "2026-11-02T16:00:00+01:00", f"FR{n+20}") for n, p in enumerate(TARGET)]
        with patch.object(collect_step2, "POLISH_AIRPORTS", ELEVEN):
            before = collect_step2.build_results([r for r in direct if set(ELEVEN) & set((r["departure_airport"], r["arrival_airport"]))])
        self.assertEqual(before, [r for r in collect_step2.build_results(direct) if set(ELEVEN) & set((r["origin_airport"], r["destination_airport"]))])

    def test_chained_reviews_use_baseline_schedules_and_keep_both_endpoints(self):
        known, _ = load_wizz_route_data()
        self.assertNotIn(("NEW", "TFS"), known)
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            snapshot = {"as_of": str(START), "routes": {"ryanair": [["SZY", "NEW"], ["RDO", "NEW"]], "wizzair": [["NEW", "TFS"]], "binter": []},
                        "airports": {"NEW": {"name": "Synthetic", "country_code": "GB", "timezone": "Europe/London"}}}
            (folder / "snapshot.json").write_text(json.dumps(snapshot))
            baseline = ROOT / "data"
            for index, endpoint in enumerate(("SZY", "RDO", "SZY", "SZY")):
                evidence = {"endpoint": endpoint, "snapshot_date": str(START), "period_from": str(START), "period_to": str(END), "routes": []}
                if index == 0:
                    evidence["routes"] = [{"origin": a, "destination": b, "flight_number": n, "duration_minutes": 240,
                                           "departure_at": stamp, "source": "https://www.google.com/travel/flights"}
                                          for a, b, n, stamp in (("NEW", "TFS", "W90001", "2026-11-01T08:00:00+00:00"), ("TFS", "NEW", "W90002", "2026-11-02T08:00:00+00:00"))]
                output = folder / str(index)
                (folder / "schedules.json").write_text(json.dumps(evidence))
                argv = ["build", "--endpoint", endpoint, "--snapshot", str(folder / "snapshot.json"), "--schedules", str(folder / "schedules.json"),
                        "--from-date", str(START), "--baseline-directory", str(baseline), "--output-directory", str(output)]
                with patch("sys.argv", argv): build_configuration()
                if index >= 1:
                    mixed = json.loads((output / "mixed-transfer-airports.json").read_text())
                    row = next(r for r in mixed["variants"][collect_step5.VARIANT_B]["airports"] if r["iata"] == "NEW")
                    self.assertEqual(set(row["polish_airports"]), {"SZY", "RDO"})
                    self.assertEqual(json.loads((output / "wizz-route-schedules.json").read_text()), json.loads((folder / "0/wizz-route-schedules.json").read_text()))
                baseline = output
            for path in (folder / "2").glob("*.json"):
                self.assertEqual(json.loads(path.read_text()), json.loads((folder / "3" / path.name).read_text()))

    def test_thirteen_text_is_idempotent_without_duplicate_endpoint(self):
        for word in ("jedenaście", "dwanaście", "trzynaście"):
            once = refresh_endpoint_text("WAW/WMI/KRK/KTW/GDN/WRO/POZ/LCJ/RZE/BZG/LUZ; wszystkie " + word + " polskich lotnisk.")
            self.assertEqual(refresh_endpoint_text(once), once)
            self.assertEqual(once.count("SZY"), 1)
            self.assertEqual(once.count("RDO"), 1)
            self.assertNotIn(word, once)


if __name__ == "__main__":
    unittest.main()
