"""Offline recovery tests: no source calls or public-price changes."""
from collections import Counter
from concurrent.futures import CancelledError, ThreadPoolExecutor
from contextlib import ExitStack
from datetime import date, timedelta
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from scripts import source_pipeline as pipeline, source_scheduler as scheduler
from scripts.collection_coverage import calendar_collector, record_checked
from scripts.source_repository import Repository, activate_writer
from scripts.source_recovery import (
    deferred_collection, map_jobs, PermanentSourceError, RecoveryExhausted, RecoveryRun,
)

DAY = date(2026, 10, 24)


class SourceRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        clock = patch("scripts.source_recovery.monotonic", return_value=0)
        clock.start()
        self.addCleanup(clock.stop)
        scheduler.start_metrics(self.root / "performance.json")
        self.repo = Repository(self.root / "sources", {"run_id": "same-run"}, True)
        activate_writer(self.repo)
        self.addCleanup(activate_writer, None)
        self.addCleanup(scheduler._stopped.clear)

    def recover(self):
        return deferred_collection(self.root / "recovery.json", self.repo.identity)

    def test_failed_day_is_deferred_until_other_days_finish_and_successes_are_not_replayed(self):
        calls = Counter()
        jobs = [("POZ", "BRS", DAY + timedelta(days=n)) for n in range(3)]

        @calendar_collector("Ryanair", "google_flights_http")
        def collect(origin, destination, start, end):
            calls[start] += 1
            if start == DAY and calls[start] == 1:
                raise RuntimeError("Loading results; private-token-must-not-enter-report")
            return []

        def cooldown(seconds):
            self.assertEqual(seconds, 60)
            self.assertEqual(calls, Counter({job[2]: 1 for job in jobs}))
            self.assertFalse(scheduler._stopped.is_set())

        with self.recover(), patch.object(RecoveryRun, "wait", side_effect=cooldown) as wait:
            rows = list(map_jobs("Ryanair", lambda job: collect(job[0], job[1], job[2], job[2]), jobs, 1))
        self.assertEqual(rows, [[], [], []])
        self.assertEqual(calls[DAY], 2)
        self.assertTrue(all(calls[job[2]] == 1 for job in jobs[1:]))
        self.assertEqual(len(self.repo.rows), 3)
        self.assertEqual(wait.call_count, 1)
        report = json.loads((self.root / "recovery.json").read_text())
        self.assertEqual(report["run_id"], "same-run")
        self.assertEqual(report["groups"]["Ryanair"]["completed"], 3)
        self.assertEqual(report["status"], "complete")
        self.assertNotIn("private-token", json.dumps(report))

    def test_two_additional_rounds_are_bounded_and_never_certify_a_missing_day(self):
        calls = []
        def broken(job):
            calls.append(job)
            raise RuntimeError("incomplete payload")
        with patch.object(RecoveryRun, "wait") as wait:
            with self.assertRaises(RecoveryExhausted), self.recover():
                list(map_jobs("Ryanair", broken, [("POZ", "BRS", DAY)], 3))
        self.assertEqual(len(calls), 3)
        self.assertEqual([call.args[0] for call in wait.call_args_list], [60, 120])
        self.assertFalse(scheduler._stopped.is_set())
        self.assertFalse((self.repo.folder / "complete.json").exists())
        self.assertEqual(self.repo.rows, {})
        report = json.loads((self.root / "recovery.json").read_text())
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["groups"]["Ryanair"]["status"], "exhausted")
        self.assertEqual(report["groups"]["Ryanair"]["pending"], [["POZ", "BRS", str(DAY)]])

    def test_finishing_healthy_jobs_already_counts_towards_cooldown(self):
        clock, calls = [0], Counter()
        def fetch(job):
            calls[job] += 1
            if job[2] == DAY and calls[job] == 1:
                raise RuntimeError("temporary")
            clock[0] = 100
            return []
        jobs = [("POZ", "BRS", DAY + timedelta(days=n)) for n in range(2)]
        with self.recover(), patch("scripts.source_recovery.monotonic", side_effect=lambda: clock[0]), \
             patch.object(RecoveryRun, "wait") as wait:
            list(map_jobs("Ryanair", fetch, jobs, 1))
        wait.assert_not_called()
        self.assertEqual(calls[jobs[0]], 2)
        self.assertEqual(calls[jobs[1]], 1)

    def test_retry_after_is_respected_without_bypassing_the_safety_budget(self):
        calls = []
        def fetch(job):
            calls.append(job)
            if len(calls) == 1:
                error = RuntimeError("throttled")
                error.response = type("Response", (), {"headers": {"Retry-After": "90"}})()
                raise error
            return []
        with self.recover(), patch.object(RecoveryRun, "wait") as wait:
            list(map_jobs("Ryanair", fetch, [("POZ", "BRS", DAY)], 3))
        wait.assert_called_once_with(90)

    def test_excessive_retry_after_is_not_ignored_by_deferred_recovery(self):
        def fetch(job):
            error = RuntimeError("throttled")
            error.response = type("Response", (), {"headers": {"Retry-After": "1000"}})()
            raise error
        with patch.object(RecoveryRun, "wait") as wait:
            with self.assertRaisesRegex(PermanentSourceError, "retry budget"), self.recover():
                list(map_jobs("Ryanair", fetch, [("POZ", "BRS", DAY)], 3))
        wait.assert_not_called()

    def test_cooldown_remains_interruptible_in_small_chunks(self):
        controller = RecoveryRun(self.root / "report.json", self.repo.identity, (60, 120))
        def interrupt(seconds):
            self.assertLessEqual(seconds, 10)
            scheduler._stopped.set()
        with patch.object(scheduler._stopped, "wait", side_effect=interrupt) as wait:
            with self.assertRaises(CancelledError):
                controller.wait(120)
        wait.assert_called_once_with(10)

    def test_integrity_programming_disk_and_interrupt_errors_are_not_replayed(self):
        for error in (PermanentSourceError("changed identity"), KeyError("schedule"),
                      PermissionError("disk"), CancelledError("stopped")):
            scheduler._stopped.clear()
            with self.subTest(error=type(error).__name__), patch.object(RecoveryRun, "wait") as wait:
                with self.assertRaises(type(error)), self.recover():
                    list(map_jobs("Binter", lambda _: (_ for _ in ()).throw(error), [("MAD", "TFN", DAY)], 2))
                wait.assert_not_called()
                self.assertTrue(scheduler._stopped.is_set())

    def test_standalone_collection_keeps_its_original_failure_behaviour(self):
        calls = []
        @calendar_collector("Ryanair", "google_flights_http")
        def broken(origin, destination, start, end):
            calls.append(start)
            raise RuntimeError("source failed")
        with self.assertRaises(RuntimeError), patch.object(RecoveryRun, "wait") as wait:
            list(map_jobs("Ryanair", lambda _: broken("POZ", "BRS", DAY, DAY), [("POZ", "BRS", DAY)], 1))
        self.assertEqual(len(calls), 1)
        self.assertTrue(scheduler._stopped.is_set())
        wait.assert_not_called()

    def test_broad_outage_defers_unattempted_jobs_instead_of_hammering_the_provider(self):
        calls = []
        def broken(job):
            calls.append(job)
            time.sleep(.005)
            raise RuntimeError("provider unavailable")
        jobs = [("POZ", "BRS", DAY + timedelta(days=n)) for n in range(10)]
        with patch("scripts.source_recovery.MAX_FAILED_JOBS_PER_ROUND", 2), patch.object(RecoveryRun, "wait") as wait:
            with self.assertRaises(RecoveryExhausted), self.recover():
                list(map_jobs("Ryanair", broken, jobs, 1))
        self.assertLessEqual(len(calls), 9)  # Two failures + at most one active job, per round.
        self.assertEqual(wait.call_count, 2)
        report = json.loads((self.root / "recovery.json").read_text())
        self.assertEqual(len(report["groups"]["Ryanair"]["pending"]), 10)
        self.assertEqual(self.repo.rows, {})

    def test_real_ryanair_parser_keeps_four_short_attempts_and_recovers_only_the_bad_day(self):
        from scripts import collect_step2, ryanair_google
        from tests.test_ryanair_google import html_for
        calls = Counter()
        def availability(client, origin, destination, day):
            calls[day] += 1
            return "PLN" + html_for([] if day == DAY and calls[day] <= 4 else [None, None, None, None])
        jobs = [("POZ", "BRS", DAY + timedelta(days=n)) for n in range(3)]
        with patch.dict(os.environ, {"RESIFLY_RYANAIR_GOOGLE_CACHE": str(self.root / "ryanair-cache.jsonl")}), \
             patch.object(ryanair_google.GoogleFlightsClient, "availability", availability), \
             patch.object(ryanair_google.time, "sleep"), patch.object(RecoveryRun, "wait") as wait, self.recover():
            list(map_jobs("Ryanair", lambda job: collect_step2.collect_ryanair_route(
                job[0], job[1], job[2], job[2], {}, "google"), jobs, 1))
        self.assertEqual(calls, Counter({DAY: 5, DAY + timedelta(days=1): 1, DAY + timedelta(days=2): 1}))
        wait.assert_called_once_with(60)
        self.assertEqual(len(self.repo.rows), 3)
        self.assertEqual(self.repo.identity, {"run_id": "same-run"})

    def test_air_europa_local_abort_does_not_cancel_other_days_during_recovery(self):
        from scripts import collect_step1d
        from tests.test_step1d_collector import google_html
        allowlist = json.loads(collect_step1d.TRANSFER_FILE.read_text())
        calls = Counter()
        def availability(client, origin, destination, day):
            calls[day] += 1
            if day == DAY and calls[day] <= 4:
                raise RuntimeError("Loading results")
            return google_html()
        jobs = {("MAD", "TFN", DAY + timedelta(days=n)) for n in range(3)}
        with self.recover(), patch.object(collect_step1d.GoogleFlightsClient, "availability", availability), \
             patch.object(collect_step1d.time_module, "sleep"), patch.object(RecoveryRun, "wait") as wait:
            self.assertEqual(collect_step1d.collect_air_europa_legs(jobs, allowlist, 1, 4.3917), [])
        self.assertEqual(calls[DAY], 5)
        self.assertEqual(calls[DAY + timedelta(days=1)], 1)
        self.assertEqual(calls[DAY + timedelta(days=2)], 1)
        self.assertEqual(len(self.repo.rows), 3)
        wait.assert_called_once_with(60)

    def test_recovery_requests_keep_google_three_and_independent_provider_two_limits(self):
        old_file = scheduler._process_file
        scheduler._process_file = None
        self.addCleanup(setattr, scheduler, "_process_file", old_file)
        self.addCleanup(lambda: scheduler._process_file.close() if scheduler._process_file else None)
        calls, events, lock = Counter(), [], threading.Lock()
        jobs = [("POZ", "BRS", DAY + timedelta(days=n)) for n in range(6)]
        def fetch(job, provider="Google", family="Ryanair"):
            with scheduler.request_slot(provider, family):
                with lock:
                    calls[(provider, job)] += 1
                    events.append((time.monotonic(), provider, family, 1))
                time.sleep(.01)
                with lock: events.append((time.monotonic(), provider, family, -1))
            if provider == "Google" and job == jobs[0] and calls[(provider, job)] == 1:
                raise RuntimeError("temporary")
            return []
        with self.recover(), patch.object(scheduler, "ROOT", self.root), patch.object(RecoveryRun, "wait"):
            with ThreadPoolExecutor(max_workers=2) as pool:
                direct = pool.submit(lambda: list(map_jobs("Binter", lambda j: fetch(j, "Binter", None), jobs, 2)))
                list(map_jobs("Ryanair", fetch, jobs, 3))
                list(map_jobs("Iberia", lambda j: fetch(j, "Google", "Iberia"), jobs, 3))
                direct.result()
        active, maximum, families = Counter(), Counter(), Counter()
        for _, provider, family, change in sorted(events):
            active[provider] += change
            maximum[provider] = max(maximum[provider], active[provider])
            if provider == "Google":
                families[family] += change
                self.assertLessEqual(sum(n > 0 for n in families.values()), 1)
        self.assertEqual(maximum["Google"], 3)
        self.assertEqual(maximum["Binter"], 2)
        self.assertEqual(active["Google"], 0)
        self.assertEqual(active["Binter"], 0)


class FullSourceRecoveryTests(unittest.TestCase):
    def collect(self, root, persistent):
        """Real pipeline/repository/coverage, only source responses are fixtures."""
        from scripts import collect_step1 as binter, collect_step2 as low, collect_step4 as wizz
        from scripts import collect_step1b as ib, collect_step1c as vy, collect_step1d as ux
        from scripts import collect_step1e as v7, collect_step1f as cf
        from scripts import collect_step6 as step6, easyjet_source as ej
        end = DAY + timedelta(days=1)
        carriers = {"Ryanair": ("POZ", "BRS", "google_flights_http"),
                    "Wizz Air": ("GDN", "TFS", "timetableV2"),
                    "Binter": ("MAD", "TFN", "booking_search"),
                    "Iberia": ("MAD", "TFN", "google_flights_http"),
                    "Vueling": ("MAD", "TFN", "google_flights_http"),
                    "Air Europa": ("MAD", "TFN", "google_flights_http"),
                    "Volotea": ("BIO", "TFS", "official_minprice"),
                    "Canaryfly": ("TFN", "LPA", "booking_calendar"),
                    "easyJet": ("LTN", "TFS", "google_flights_http")}
        plan = {(c, o, d, str(day), "calendar") for c, (o, d, _) in carriers.items() for day in (DAY, end)}
        calls, google_order = Counter(), []
        @calendar_collector("Ryanair", "google_flights_http")
        def ryanair(origin, destination, start, finish, rates, version):
            self.assertEqual(start, finish)  # Every day continues independently.
            calls[("Ryanair", start)] += 1
            google_order.append("Ryanair")
            if start == DAY and (persistent or calls[("Ryanair", start)] == 1):
                raise RuntimeError("loading")
            return []
        @calendar_collector("Wizz Air", "timetableV2")
        def wizz_route(origin, destination, start, end, rates):
            calls[("Wizz Air", start)] += 1
            return []
        def bulk(carrier):
            def collect(candidates, *args):
                def fetch(job):
                    origin, destination, day = job
                    calls[(carrier, day)] += 1
                    if carrier in ("Iberia", "Vueling", "Air Europa", "easyJet"):
                        google_order.append(carrier)
                    record_checked(carrier, origin, destination, day, day, [], carriers[carrier][2])
                    return []
                return [row for rows in map_jobs(carrier, fetch, sorted(candidates), 2) for row in rows]
            return collect
        def cf_calendar(*args):
            bulk("Canaryfly")({("TFN", "LPA", day) for day in (DAY, end)})
            return set()
        with ExitStack() as stack:
            stack.enter_context(patch.object(pipeline, "expected_queries", side_effect=lambda step, *_: plan if step == "2" else set()))
            stack.enter_context(patch.object(binter, "nbp_rates", return_value={"EUR": binter.CurrencyRate("EUR", 4.3917)}))
            stack.enter_context(patch("scripts.wizz_api.wizz_api_base", return_value="offline-fixture"))
            stack.enter_context(patch.object(scheduler, "ensure_google_owner"))
            stack.enter_context(patch.object(low, "collect_ryanair_route", ryanair))
            stack.enter_context(patch.object(wizz, "collect_wizz_route", wizz_route))
            for module, planner, collector, carrier in (
                (binter, "binter_route_days", "collect_binter_legs", "Binter"),
                (ib, "iberia_route_days", "collect_iberia_legs", "Iberia"),
                (vy, "vueling_route_days", "collect_vueling_legs", "Vueling"),
                (ux, "air_europa_route_days", "collect_air_europa_legs", "Air Europa"),
                (v7, "volotea_route_days", "collect_volotea_legs", "Volotea")):
                origin, destination, _ = carriers[carrier]
                stack.enter_context(patch.object(module, planner, return_value={(origin, destination, day) for day in (DAY, end)}))
                stack.enter_context(patch.object(module, collector, bulk(carrier)))
            stack.enter_context(patch.object(cf, "collect_canaryfly_available_days", cf_calendar))
            stack.enter_context(patch.object(step6, "easyjet_route_days", return_value={("LTN", "TFS", day) for day in (DAY, end)}))
            stack.enter_context(patch.object(ej, "collect_legs", bulk("easyJet")))
            stack.enter_context(patch.object(cf, "collect_canaryfly_legs", return_value=[]))
            stack.enter_context(patch.object(RecoveryRun, "wait"))
            if persistent:
                with self.assertRaises(RecoveryExhausted):
                    pipeline.collect_sources(root, DAY, end, "fixed-run")
            else:
                pipeline.collect_sources(root, DAY, end, "fixed-run")
        # Every later family ran, without concurrent family queues.
        compressed = [c for i, c in enumerate(google_order) if i == 0 or c != google_order[i - 1]]
        self.assertEqual(compressed, ["Ryanair", "Iberia", "Vueling", "Air Europa", "easyJet"])
        self.assertEqual(calls[("Ryanair", DAY)], 3 if persistent else 2)
        self.assertEqual(calls[("Ryanair", end)], 1)
        for carrier in ("Wizz Air", "Binter", "Canaryfly", "Volotea", "Iberia", "Vueling", "Air Europa", "easyJet"):
            self.assertGreater(calls[(carrier, DAY)], 0)
        report = json.loads((root / "source-coverage.json").read_text())
        self.assertEqual(report["run_id"], "fixed-run")
        self.assertEqual(report["missing_queries"], 1 if persistent else 0)
        self.assertEqual(report["status"], "failed" if persistent else "complete")
        self.assertEqual((root / "sources/complete.json").exists(), not persistent)
        self.assertFalse(scheduler._stopped.is_set())

    def test_full_batch_recovers_without_new_run_or_duplicate_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            self.collect(Path(temp), False)

    def test_exhausted_source_still_finishes_other_families_and_never_certifies(self):
        with tempfile.TemporaryDirectory() as temp:
            self.collect(Path(temp), True)


if __name__ == "__main__":
    unittest.main()
