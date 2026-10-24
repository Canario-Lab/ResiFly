import copy
from datetime import date, datetime
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess
from zoneinfo import ZoneInfo

from scripts.collect_five_steps import STEPS, main, promote_batch, validate_batch
from scripts.collection_coverage import Coverage, expected_queries


class FiveStepBatchTests(unittest.TestCase):
    def write_batch(self, directory):
        documents = {}
        for step in STEPS:
            result = {
                "id": "result-" + step, "direction": "poland_to_tenerife",
                "origin_airport": "GDN", "destination_airport": "TFS",
                "legs": [{
                    "departure_airport": "GDN", "arrival_airport": "TFS",
                    "departure_at": "2026-10-22T10:00:00+02:00",
                    "arrival_at": "2026-10-22T15:00:00+01:00",
                    "booking_url": "https://example.com/booking", "price_regular_pln": 400,
                }],
            }
            document = {
                "schema_version": 2, "step": int(step) if step.isdigit() else step.upper(),
                "period_from": "2026-10-22", "period_to": "2026-11-21",
                "generated_at": datetime.now(ZoneInfo("Atlantic/Canary")).isoformat(),
                "price_filtering": {"applied_during_collection": False},
                "exchange_rates": {"EUR_PLN": {"rate": 4.3, "effective_for": "2026-10-22"}},
                "results": [result],
            }
            tracker = Coverage(step, date(2026, 10, 22), date(2026, 11, 21),
                               expected_queries(step, date(2026, 10, 22), date(2026, 11, 21)), "test-batch")
            for carrier, origin, destination, day, kind in tracker.expected:
                tracker.completed[(carrier, origin, destination, day, kind)] = (0, {
                    "Ryanair": "google_flights_http", "Wizz Air": "timetableV2", "Binter": "booking_search",
                    "Iberia": "google_flights_http", "Vueling": "google_flights_http",
                    "Volotea": "official_minprice", "Air Europa": "google_flights_http", "Canaryfly": "booking_calendar",
                }[carrier])
            document["collection_coverage"] = tracker.verify()
            documents[step] = document
            (directory / f"step{step}-results.json").write_text(json.dumps(document))
            (directory / f"step{step}-results.collection-report.json").write_text(json.dumps(document["collection_coverage"]))
        return documents

    @patch("scripts.collect_five_steps.validate_feed_document")
    def test_complete_gdn_batch_is_validated_as_one_set(self, module):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_batch(directory)
            report = validate_batch(directory, date(2026, 10, 22), 30)
            self.assertEqual(len(report), 10)
            self.assertEqual(report["2"]["polish_airports"], {"GDN": 1})

    @patch("scripts.collect_five_steps.validate_feed_document")
    def test_mixed_scope_period_id_and_exchange_rate_are_rejected(self, module):
        cases = (
            ("step", 9, "Wrong schema/step"),
            ("period_to", "2026-11-20", "Mixed collection periods"),
            ("exchange_rates", {"EUR_PLN": {"rate": 4.4, "effective_for": "2026-10-22"}}, "Mixed daily exchange rates"),
            ("results", "duplicate", "Duplicate result ID"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            documents = self.write_batch(directory)
            path = directory / "step5-results.json"
            for key, value, message in cases:
                document = copy.deepcopy(documents["5"])
                if value == "duplicate":
                    document["results"][0]["id"] = "result-1"
                else:
                    document[key] = value
                path.write_text(json.dumps(document))
                with self.assertRaisesRegex(RuntimeError, message):
                    validate_batch(directory, date(2026, 10, 22), 30)

    @patch("scripts.collect_five_steps.validate_feed_document")
    def test_promotion_preserves_backup_and_rolls_back_failed_replacement(self, validate):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            staging, public = directory / "stage", directory / "public"
            staging.mkdir()
            public.mkdir()
            self.write_batch(staging)
            staged = {step: (staging / f"step{step}-results.json").read_text() for step in STEPS}
            for step in STEPS:
                (public / f"step{step}-results.json").write_text("old-" + step)
            original_replace = Path.replace

            def replace(path, target):
                if path.name == "step3-results.json.pending":
                    raise OSError("simulated replacement failure")
                return original_replace(path, target)

            with patch.object(Path, "replace", replace):
                with self.assertRaisesRegex(OSError, "simulated"):
                    promote_batch(staging, public)
            for step in STEPS:
                self.assertEqual((public / f"step{step}-results.json").read_text(), "old-" + step)
            self.assertEqual(list(public.glob("*.pending")), [])

            promote_batch(staging, public)
            promote_batch(staging, public)
            for step in STEPS:
                filename = f"step{step}-results.json"
                self.assertEqual((public / filename).read_text(), staged[step])
                self.assertEqual((staging / "previous-public-feeds" / filename).read_text(), "old-" + step)

    @patch("scripts.collect_five_steps.validate_feed_document")
    def test_incomplete_old_or_mixed_run_reports_block_promotion(self, validate):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            documents = self.write_batch(directory)
            path = directory / "step5-results.json"
            sidecar = directory / "step5-results.collection-report.json"
            for case in ("missing_report", "missing_day", "failed_sidecar", "different_run", "minimum_fares"):
                with self.subTest(case=case):
                    doc = copy.deepcopy(documents["5"])
                    if case == "missing_report":
                        del doc["collection_coverage"]
                    elif case == "missing_day":
                        doc["collection_coverage"]["routes"][0]["days"].pop()
                    elif case == "different_run":
                        doc["collection_coverage"]["run_id"] = "different"
                    elif case == "minimum_fares":
                        for route in doc["collection_coverage"]["routes"]:
                            if route["carrier"] == "Ryanair":
                                route["days"][0]["method"] = "fare_finder"
                                break
                    path.write_text(json.dumps(doc))
                    report = copy.deepcopy(doc.get("collection_coverage", {}))
                    if case == "failed_sidecar":
                        report["status"] = "failed"
                    sidecar.write_text(json.dumps(report))
                    with self.assertRaises(RuntimeError):
                        promote_batch(directory, directory / "public-never-created")
                    self.assertFalse((directory / "public-never-created").exists())
                    self.assertFalse((directory / "previous-public-feeds").exists())

    @patch("scripts.collect_five_steps.promote_batch")
    @patch("scripts.collect_five_steps.collect_sources", return_value=Path("/unused-mocked-sources"))
    @patch("scripts.collect_five_steps.subprocess.run", side_effect=subprocess.CalledProcessError(1, "collector"))
    def test_failed_batch_replaces_old_success_report_but_never_promotes(self, run, sources, promote):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "validation-report.json").write_text('{"status":"complete"}')
            with patch("sys.argv", ["collect_five_steps", "--from-date", "2026-10-22", "--stage-directory", temporary, "--promote"]):
                with self.assertRaises(subprocess.CalledProcessError):
                    main()
            report = json.loads((directory / "validation-report.json").read_text())
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["current_step"], "1")
            self.assertTrue(report["run_id"])
            self.assertEqual(run.call_args.kwargs["env"]["RESIFLY_COLLECTION_RUN_ID"], report["run_id"])
            promote.assert_not_called()


if __name__ == "__main__":
    unittest.main()
