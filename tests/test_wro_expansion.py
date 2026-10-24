import copy
from datetime import date, datetime
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import collect_step1, collect_step2, collect_step3, collect_step4, collect_step5
from scripts.collect_five_steps import STEPS, promote_batch, main
from scripts.collection_coverage import expected_queries
from scripts.search_airports import POLISH_AIRPORTS, ENDPOINT_TIMEZONES, validate_polish_transfer
from scripts.booking_urls import wizz_booking_url, ryanair_booking_url
from scripts.verify_wizz_expansion_schedules import required_routes
from scripts.wizz_schedules import read_overrides, resolve_schedule, load_wizz_route_data
from tests.test_airport_expansion import leg
from tests import test_five_step_batch


class WroExpansionTests(unittest.TestCase):
    def test_verified_wro_transfer_permissions_match_reviewed_network(self):
        config = collect_step5.load_allowlist()
        actual = {variant: {r["iata"] for r in data["airports"] if "WRO" in r["polish_airports"]}
                  for variant, data in config["variants"].items()}
        self.assertEqual(actual[collect_step5.VARIANT_A], {"AGP", "BUD", "EIN", "LTN"})
        self.assertEqual(actual[collect_step5.VARIANT_B], {"GDN"})
        self.assertEqual({r["iata"] for r in collect_step4.load_allowlist()["airports"]
                          if "WRO" in r["polish_airports"]}, {"BUD"})

    def test_weekday_and_exact_date_overrides_preserve_verified_block_time(self):
        schedules = {("WRO", "LPA"): ("W61869", 325)}
        overrides = read_overrides([], schedules,
            [{"origin": "WRO", "destination": "LPA", "departure_time": "13:45",
              "departure_weekday": 1, "flight_number": "W61869", "duration_minutes": 330}],
            [{"origin": "WRO", "destination": "LPA", "departure_time": "13:45",
              "departure_date": "2026-11-09", "flight_number": "W61869", "duration_minutes": 335}])
        for stamp, duration in (("2026-11-02T13:45:00+01:00", 330),
                                ("2026-11-04T13:45:00+01:00", 325),
                                ("2026-11-09T13:45:00+01:00", 335)):
            self.assertEqual(resolve_schedule(schedules, overrides, "WRO", "LPA", datetime.fromisoformat(stamp)), ("W61869", duration))

    def test_local_wro_schedules_keep_shared_weekday_overrides(self):
        shared, overrides = load_wizz_route_data()
        document = json.loads((Path(__file__).resolve().parents[1] / "data/binter-transfer-airports.json").read_text())
        local = collect_step1.wizz_schedules_from_allowlist(document)
        for stamp in ("2026-11-02T13:45:00+01:00", "2026-11-04T13:45:00+01:00"):
            departure = datetime.fromisoformat(stamp)
            self.assertEqual(resolve_schedule(shared, overrides, "WRO", "LPA", departure),
                             resolve_schedule(local, local.overrides, "WRO", "LPA", departure))

    def test_schedule_audit_handles_lowercase_country_and_new_tenerife_leg(self):
        snapshot = {"routes": {"ryanair": [["WRO", "NEW"]],
                               "wizzair": [["WRO", "BIO"], ["NEW", "TFS"]], "binter": []},
                    "airports": {"BIO": {"country_code": "es"}}}
        routes = required_routes(snapshot, "WRO")
        for pair in (("WRO", "BIO"), ("BIO", "WRO"), ("NEW", "TFS"), ("TFS", "NEW")):
            self.assertIn(pair, routes)

    def test_wro_retained_with_timezone_and_current_full_direct_coverage(self):
        self.assertEqual(POLISH_AIRPORTS, ("WAW", "WMI", "KTW", "KRK", "GDN", "WRO", "POZ", "LCJ", "RZE", "BZG", "LUZ", "SZY", "RDO", "SZZ", "IEG"))
        self.assertEqual(ENDPOINT_TIMEZONES["WRO"], "Europe/Warsaw")
        plan = expected_queries("2", date(2026, 10, 23), date(2026, 11, 22))
        self.assertEqual(len(plan), 120 * 31)
        for carrier in ("Ryanair", "Wizz Air"):
            for tenerife in ("TFN", "TFS"):
                for origin, destination in (("WRO", tenerife), (tenerife, "WRO")):
                    self.assertEqual(sum(c == carrier and o == origin and d == destination
                                         for c, o, d, day, kind in plan), 31)

    def test_all_resident_builders_accept_wro_both_directions(self):
        for step, carrier in (("1", "Binter"), ("1b", "Iberia"), ("1c", "Vueling"),
                              ("1d", "Air Europa"), ("1e", "Volotea"), ("1f", "Canaryfly")):
            module = importlib.import_module("scripts.collect_step" + step)
            low = [leg("Ryanair", "WRO", "2026-11-01T06:00:00+01:00", "MAD", "2026-11-01T09:00:00+01:00"),
                   leg("Wizz Air", "MAD", "2026-11-02T16:00:00+01:00", "WRO", "2026-11-02T19:00:00+01:00")]
            resident = [leg(carrier, "MAD", "2026-11-01T12:00:00+01:00", "TFN", "2026-11-01T14:00:00+00:00"),
                        leg(carrier, "TFN", "2026-11-02T08:00:00+00:00", "MAD", "2026-11-02T12:00:00+01:00")]
            rows = module.build_connections(low, resident)
            self.assertEqual({r["direction"] for r in rows}, {"poland_to_tenerife", "tenerife_to_poland"}, step)
            self.assertEqual(len(rows), 2, step)

    def test_wro_builders_three_four_and_both_mixed_variants(self):
        for module, hub, first, second, variant in (
            (collect_step3, "AGP", "Ryanair", "Ryanair", None),
            (collect_step4, "BUD", "Wizz Air", "Wizz Air", None),
            (collect_step5, "AGP", "Ryanair", "Wizz Air", collect_step5.VARIANT_A),
            (collect_step5, "BUD", "Wizz Air", "Ryanair", collect_step5.VARIANT_B),
        ):
            # Synthetic permission tests builder support, not a claim of a live WRO route.
            config = copy.deepcopy(module.load_allowlist())
            airports = config["airports"] if variant is None else config["variants"][variant]["airports"]
            rule = next(row for row in airports if row["iata"] == hub)
            rule["polish_airports"] = ["WRO"]
            legs = [leg(first, "TFS", "2026-11-01T06:00:00+00:00", hub, "2026-11-01T10:00:00+01:00"),
                    leg(second, hub, "2026-11-01T13:00:00+01:00", "WRO", "2026-11-01T16:00:00+01:00"),
                    leg(second, "WRO", "2026-11-02T06:00:00+01:00", hub, "2026-11-02T09:00:00+01:00"),
                    leg(first, hub, "2026-11-02T12:00:00+01:00", "TFS", "2026-11-02T15:00:00+00:00")]
            rows = module.build_connections(legs, config, 4.0)
            self.assertEqual(len(rows), 2, (module.__name__, variant))
            module.validate_document({"results": rows}, config)

    def test_gdn_exception_does_not_extend_to_wro_and_no_wro_self_route(self):
        validate_polish_transfer("KRK", "GDN", "step5_variant_b")
        for endpoint, transfer in (("WRO", "GDN"), ("WRO", "WRO"), ("KRK", "WRO")):
            if endpoint == transfer:
                with self.assertRaises(RuntimeError):
                    validate_polish_transfer(endpoint, transfer, "step5_variant_b")
            else:
                validate_polish_transfer(endpoint, transfer, "step5_variant_b")

    def test_wro_booking_links_accept_both_directions(self):
        for origin, destination in (("WRO", "TFS"), ("TFS", "WRO")):
            self.assertIn(f"/{origin}/{destination}/2026-11-01/", wizz_booking_url(origin, destination, "2026-11-01"))
            url = ryanair_booking_url(origin, destination, "2026-11-01")
            self.assertIn("originIata=" + origin, url)
            self.assertIn("destinationIata=" + destination, url)


class WroBatchTests(unittest.TestCase):
    @patch("scripts.collect_five_steps.validate_feed_document")
    def test_promotion_rolls_back_sidecars_including_previously_missing_ones(self, validate):
        with tempfile.TemporaryDirectory() as temp:
            staging, public = Path(temp) / "stage", Path(temp) / "public"
            staging.mkdir()
            public.mkdir()
            test_five_step_batch.FiveStepBatchTests().write_batch(staging)
            for step in STEPS:
                (public / f"step{step}-results.json").write_text("old-" + step)
            existing = public / "step1-results.collection-report.json"
            existing.write_text("old-report")
            original_replace = Path.replace

            def replace(path, target):
                if path.name == "step3-results.collection-report.json.pending":
                    raise OSError("report replacement failed")
                return original_replace(path, target)

            with patch.object(Path, "replace", replace):
                with self.assertRaisesRegex(OSError, "report replacement"):
                    promote_batch(staging, public)
            self.assertEqual(existing.read_text(), "old-report")
            self.assertEqual(len(list(public.glob("*.collection-report.json"))), 1)
            for step in STEPS:
                self.assertEqual((public / f"step{step}-results.json").read_text(), "old-" + step)
            promote_batch(staging, public)
            for item in staging.glob("step*-results*.json"):
                self.assertEqual(item.read_bytes(), (public / item.name).read_bytes())
            manifest = json.loads((staging / "previous-public-feeds/manifest.json").read_text())
            self.assertFalse(manifest["step2-results.collection-report.json"]["existed"])
            self.assertEqual((staging / "previous-public-feeds/step1-results.collection-report.json").read_text(), "old-report")

    @patch("scripts.collect_five_steps.subprocess.run", side_effect=RuntimeError("probe stop"))
    @patch("scripts.collect_five_steps.collect_sources", return_value=Path("/mocked-sources"))
    def test_new_runs_isolate_cache_and_resume_keeps_same_identity(self, sources, run):
        with tempfile.TemporaryDirectory() as temp:
            def launch(run_id):
                with patch("sys.argv", ["collect_five_steps", "--from-date", "2026-10-23", "--stage-directory", temp, "--run-id", run_id]):
                    with self.assertRaisesRegex(RuntimeError, "probe stop"):
                        main()
                return run.call_args.kwargs["env"]["RESIFLY_RYANAIR_GOOGLE_CACHE"]
            first = launch("run-a")
            self.assertEqual(first, launch("run-a"))
            self.assertNotEqual(first, launch("run-b"))
            with patch("sys.argv", ["collect_five_steps", "--from-date", "2026-10-24", "--stage-directory", temp, "--run-id", "run-a"]):
                with self.assertRaisesRegex(RuntimeError, "changed dates"):
                    main()


if __name__ == "__main__":
    unittest.main()
