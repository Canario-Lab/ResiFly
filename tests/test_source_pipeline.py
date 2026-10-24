import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from scripts import source_scheduler as scheduler
from scripts.collection_coverage import calendar_collector
from scripts.source_repository import Repository, activate_writer, cached_route, reader
from scripts.source_pipeline import configuration_hash, adapter_hash, remaining, source_report

DAY = date(2026, 10, 24)


class SourceRepositoryTests(unittest.TestCase):
    def tearDown(self):
        activate_writer(None)

    def test_empty_day_is_saved_but_missing_day_is_not_available(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Repository(temp, {"run_id": "one"}, True)
            repo.record("Ryanair", "SZZ", "KRK", DAY, DAY, [], "google_flights_http")
            self.assertEqual(repo.read("Ryanair", "SZZ", "KRK", DAY, DAY), [])
            with self.assertRaisesRegex(RuntimeError, "Missing current"):
                repo.read("Ryanair", "SZZ", "KRK", DAY, DAY + timedelta(days=1))
            self.assertEqual(remaining(repo, "Ryanair", {("SZZ", "KRK", DAY)}), set())
            with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
                Repository(temp, {"run_id": "other"}, True)
            with self.assertRaisesRegex(RuntimeError, "mutate"):
                repo.record("Ryanair", "SZZ", "KRK", DAY, DAY,
                            [{"departure_at": str(DAY)}], "google_flights_http")

    def test_parallel_writers_and_independent_canaryfly_details_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Repository(temp, {"run_id": "one"}, True)
            days = [DAY + timedelta(days=n) for n in range(31)]
            with ThreadPoolExecutor(max_workers=3) as pool:
                list(pool.map(lambda day: repo.record("Ryanair", "SZZ", "STN", day, day,
                    [], "google_flights_http"), days))
            self.assertEqual(len(Repository(temp, repo.identity).rows), 31)
            plan = {(c, o, d, day.isoformat(), "calendar") for c, o, d, day in
                    [("Canaryfly", "TFN", "LPA", DAY)]}
            repo = Repository(Path(temp) / "cf", {"run_id": "one"}, True)
            repo.record("Canaryfly", "TFN", "LPA", DAY, DAY,
                        [{"departure_at": str(DAY)}], "booking_calendar")
            self.assertEqual(source_report(repo, DAY, DAY, plan)["missing_queries"], 1)
            repo.record("Canaryfly", "TFN", "LPA", DAY, DAY, [], "booking_search", "details")
            self.assertEqual(source_report(repo, DAY, DAY, plan)["status"], "complete")

    def test_certified_reader_forbids_network_and_reuses_observation(self):
        with tempfile.TemporaryDirectory() as temp:
            identity = {"run_id": "one", "configuration_hash": configuration_hash(), "adapter_hash": adapter_hash()}
            repo = Repository(temp, identity, True)
            repo.record("Ryanair", "SZZ", "KRK", DAY, DAY, [], "google_flights_http")
            (Path(temp) / "complete.json").write_text(json.dumps({"status": "complete", "identity": identity, "digests": repo.digests()}))
            environment = {"RESIFLY_SOURCE_MODE": "read", "RESIFLY_SOURCE_REPOSITORY": temp,
                           "RESIFLY_COLLECTION_RUN_ID": "one"}
            with patch.dict(os.environ, environment):
                @calendar_collector("Ryanair", "google_flights_http")
                def forbidden(origin, destination, start, end):
                    self.fail("Cached builder attempted to fetch")
                self.assertEqual(forbidden("SZZ", "KRK", DAY, DAY), [])
                with self.assertRaisesRegex(RuntimeError, "Missing current"):
                    forbidden("IEG", "TFS", DAY, DAY)
                with self.assertRaisesRegex(RuntimeError, "Network forbidden"):
                    with scheduler.request_slot("Google", "Ryanair"):
                        self.fail("Network was allowed")
            # New process/read path must reject changed normalized observations.
            from scripts.source_repository import _readers
            _readers.pop(temp, None)
            (Path(temp) / "ryanair.jsonl").write_text("")
            with patch.dict(os.environ, environment), self.assertRaisesRegex(RuntimeError, "changed after"):
                reader()

    def test_failure_does_not_certify_repository_and_secrets_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            identity = {"run_id": "one", "configuration_hash": configuration_hash(), "adapter_hash": adapter_hash()}
            repo = Repository(temp, identity, True)
            with self.assertRaisesRegex(RuntimeError, "Secret field"):
                repo.record("Binter", "TFN", "MAD", DAY, DAY,
                    [{"departure_at": str(DAY), "token": "not-to-be-saved"}], "booking_search")
            with patch.dict(os.environ, {"RESIFLY_SOURCE_MODE": "read", "RESIFLY_SOURCE_REPOSITORY": temp,
                                        "RESIFLY_COLLECTION_RUN_ID": "one"}), self.assertRaises(FileNotFoundError):
                reader()


class SourceSchedulerTests(unittest.TestCase):
    def test_retry_after_and_exception_release_all_slots(self):
        error = RuntimeError("throttled")
        error.response = type("Response", (), {"headers": {"Retry-After": "7"}})()
        self.assertEqual(scheduler.retry_delay(0,error),7)
        error.response.headers["Retry-After"]="1000"
        with self.assertRaisesRegex(RuntimeError,"retry budget"): scheduler.retry_delay(0,error)
        with tempfile.TemporaryDirectory() as temp, patch.object(scheduler,"ROOT",Path(temp)):
            scheduler.start_metrics(Path(temp)/"metrics.json")
            for _ in range(3):
                with self.assertRaisesRegex(OSError,"offline"):
                    scheduler.http_request(lambda *a,**kw: (_ for _ in ()).throw(OSError("offline")), "https://services.bintercanarias.com/main/graphql")
            scheduler.save_metrics("failed")
            report=json.loads((Path(temp)/"metrics.json").read_text())
            self.assertEqual(report["providers"]["Binter"]["active"],0)
            self.assertEqual(report["providers"]["Binter"]["attempts"],3)
            self.assertEqual(len(report["events"]),3)
            self.assertNotIn("graphql",json.dumps(report))

    def test_global_three_slots_and_one_family_with_official_source_overlap(self):
        with tempfile.TemporaryDirectory() as temp:
            # Isolate the unit-test lock from a genuine collection on this host.
            process_file = scheduler._process_file
            scheduler._process_file = None
            self.addCleanup(setattr, scheduler, "_process_file", process_file)
            root_patch = patch.object(scheduler, "ROOT", Path(temp))
            root_patch.start()
            self.addCleanup(root_patch.stop)
            self.addCleanup(lambda: scheduler._process_file.close() if scheduler._process_file else None)
            scheduler.start_metrics(Path(temp) / "metrics.json")
            events, lock = [], threading.Lock()
            def request(provider, family):
                with scheduler.request_slot(provider, family):
                    with lock: events.append((provider, family, time.monotonic(), True))
                    time.sleep(.025)
                    with lock: events.append((provider, family, time.monotonic(), False))
            with ThreadPoolExecutor(max_workers=12) as pool:
                futures = [pool.submit(request, "Google", family) for family in ["Ryanair"]*6 + ["Iberia"]*3]
                futures += [pool.submit(request, "Binter", None) for _ in range(3)]
                for future in futures: future.result()
            active, maximum, overlap, official = {}, 0, False, 0
            for provider, family, _, entered in sorted(events, key=lambda e: e[2]):
                if provider == "Google":
                    active[family] = active.get(family, 0) + (1 if entered else -1)
                else:
                    official += 1 if entered else -1
                self.assertLessEqual(sum(bool(n) for n in active.values()), 1)
                maximum = max(maximum, sum(active.values()))
                overlap |= bool(official and sum(active.values()))
            self.assertEqual(maximum, 3)
            self.assertTrue(overlap)
            scheduler.save_metrics("complete")
            report = json.loads((Path(temp) / "metrics.json").read_text())
            self.assertEqual(report["providers"]["Google"]["max_in_flight"], 3)
            self.assertLessEqual(report["providers"]["Binter"]["max_in_flight"], 2)
            # A separate collector process cannot create three additional slots.
            result = subprocess.run([sys.executable, "-c", f"from pathlib import Path; import scripts.source_scheduler as s; s.ROOT=Path({temp!r}); s.ensure_google_owner()"], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"Another Google collection", result.stderr)


if __name__ == "__main__":
    unittest.main()
