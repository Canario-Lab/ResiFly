"""Offline route-only update tests. Fixtures are disposable, never public fares."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from scripts import incremental_update as update
from scripts import collect_five_steps as batch
from scripts.collection_coverage import atomic_json, expected_queries, record_checked
from scripts.source_pipeline import configuration_hash, adapter_hash, source_report
from scripts.source_repository import Repository, _readers
from scripts import collect_step6 as step6
from tests import test_step6_collector as fixture6
from tests.test_step6_collector import low_leg, DAY


class PartialUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="partial-offline-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / "base"
        self.base.mkdir()
        self.addCleanup(_readers.clear)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(update, "STEPS", ("6",)))
        self.stack.enter_context(patch.object(batch, "STEPS", ("6",)))
        self.stack.enter_context(patch("curl_cffi.requests.Session.request", side_effect=AssertionError("HTTP forbidden")))
        self.stack.enter_context(patch("time.sleep"))
        first = (datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
        identity = {"run_id": "FIXTURE-BASE", "period_from": str(DAY), "period_to": str(DAY),
            "configuration_hash": configuration_hash(), "adapter_hash": adapter_hash(),
            "nbp_rates": {"EUR": 4.3917, "PLN": 1.0, "CHF": 4.7681,
                          "GBP": 5.2498, "HUF": .011972, "RON": .821, "MAD": .397, "USD": 3.9247}}
        self.repo = Repository(self.base / "sources", identity, True)
        fixture = fixture6.EasyJetTests()
        fixture.setUp()
        self.low, self.jet = low_leg(), fixture.jet()
        expected = expected_queries("6", DAY, DAY)
        for key in sorted(expected):
            carrier, origin, destination, raw_day, kind = key
            rows = [self.low] if key[:3] == ("Ryanair", "KRK", "LTN") else [self.jet] if key[:3] == ("easyJet", "LTN", "TFS") else []
            self.repo.record(carrier, origin, destination, DAY, DAY, rows,
                "timetableV2" if carrier == "Wizz Air" else "google_flights_http", kind)
        atomic_json(self.repo.folder / "complete.json", {"status": "complete", "identity": identity, "digests": self.repo.digests()})
        atomic_json(self.base / "performance.json", {"started_at": first})
        update.archive_configuration(self.base)
        with patch.dict(os.environ, {"RESIFLY_SOURCE_MODE": "read", "RESIFLY_SOURCE_REPOSITORY": str(self.repo.folder),
                                    "RESIFLY_COLLECTION_RUN_ID": "FIXTURE-BASE"}), patch("sys.argv", [
                                        "test", "--from-date", str(DAY), "--days", "0", "--output", str(self.base / "step6-results.json")]):
            step6.main()
        atomic_json(self.base / "validation-report.json", {"status": "complete", "run_id": "FIXTURE-BASE"})
        self.assertEqual(len(json.loads((self.base / "step6-results.json").read_text())["results"]), 1)

    def plan(self, carrier="Ryanair", origin="KRK", destination="LTN", base=None):
        return update.plan_update(base or self.base, [(carrier, origin, destination)])

    def fetch_empty(self, repo, selected, start, end, rates):
        self.assertEqual(start, end)
        self.assertEqual(rates["EUR"].pln, 4.3917)
        self.assertEqual(os.environ["RESIFLY_COLLECTION_RUN_ID"], repo.identity["run_id"])
        self.assertNotIn("RESIFLY_SOURCE_MODE", os.environ)
        for carrier, origin, destination in selected:
            record_checked(carrier, origin, destination, start, end, [],
                "timetableV2" if carrier == "Wizz Air" else "google_flights_http")

    def run_update(self, plan=None, name="updated"):
        with patch.object(update, "fetch_selected", side_effect=self.fetch_empty):
            return update.execute(plan or self.plan(), self.root / name)

    def test_plan_only_expands_both_directions_and_retains_other_calendars(self):
        plan = self.plan()
        self.assertEqual(plan["selected"], {("Ryanair", "KRK", "LTN"), ("Ryanair", "LTN", "KRK")})
        self.assertEqual(plan["plan"]["calendar_queries_to_refresh"], 2)
        self.assertEqual(plan["plan"]["affected_steps"], ["6"])
        self.assertIn(("easyJet", "LTN", "TFS", str(DAY), "calendar"), plan["inherited"])
        with self.assertRaisesRegex(RuntimeError, "canonical"):
            self.plan(origin="KRK", destination="XXX")

    def test_missing_parent_certificate_tamper_and_missing_day_fail_closed(self):
        target = self.repo.folder / "ryanair.jsonl"
        original = target.read_bytes()
        target.write_bytes(original + b"\n")
        with self.assertRaisesRegex(RuntimeError, "changed after|Corrupt"):
            self.plan()
        target.write_bytes(original)
        side = self.base / "step6-results.collection-report.json"
        data = json.loads(side.read_text()); data["status"] = "failed"; atomic_json(side, data)
        with self.assertRaisesRegex(RuntimeError, "Parent feeds"):
            self.plan()

    def test_no_arbitrary_config_or_fee_changes_are_allowed(self):
        previous = {p.name: json.loads(p.read_text()) for p in update.configuration_paths()}
        selected = update.both_directions([("Wizz Air", "KRK", "NCE")])
        changed = deepcopy(previous)
        changed["spanish-resident-fees.json"]["arbitrary"] = 1
        with self.assertRaisesRegex(RuntimeError, "Unrelated"):
            update.validate_configuration_change(previous, changed, selected)
        changed = deepcopy(previous)
        changed["wizz-route-schedules.json"]["routes"].append({"origin": "WAW", "destination": "LPL", "flight_number": "W60001"})
        with self.assertRaisesRegex(RuntimeError, "Unrelated"):
            update.validate_configuration_change(previous, changed, selected)
        changed = deepcopy(previous)
        changed["wizz-route-schedules.json"]["routes"].append({"origin": "KRK", "destination": "NCE", "flight_number": "W60001"})
        update.validate_configuration_change(previous, changed, selected)

    def test_additive_step6_pair_is_allowed_but_a_new_hub_or_unselected_pair_is_not(self):
        previous = {p.name: json.loads(p.read_text()) for p in update.configuration_paths()}
        selected = update.both_directions([("Wizz Air", "KRK", "NCE")])
        changed = deepcopy(previous)
        nce = next(a for a in changed["easyjet-transfer-airports.json"]["airports"] if a["iata"] == "NCE")
        nce["polish_routes"].append({"polish_airport": "KRK", "airlines": ["Wizz Air"]})
        update.validate_configuration_change(previous, changed, selected)
        nce["timezone"] = "Europe/London"
        with self.assertRaisesRegex(RuntimeError, "Unrelated"):
            update.validate_configuration_change(previous, changed, selected)

    def test_dispatch_does_not_call_other_providers_and_keeps_full_window(self):
        from scripts import collect_step4 as wizz
        from scripts import easyjet_source
        from scripts.collect_step1 import CurrencyRate
        selected = {("Wizz Air", "KRK", "NCE"), ("Wizz Air", "NCE", "KRK")}
        calls = []
        with patch("scripts.wizz_api.wizz_api_base", return_value="offline"), patch.object(
                wizz, "collect_wizz_route", side_effect=lambda o,d,s,e,r: calls.append((o,d,s,e)) or []), patch.object(
                easyjet_source, "collect_legs", side_effect=AssertionError("Unselected provider requested")):
            update.fetch_selected(self.repo, selected, DAY, DAY+timedelta(days=30), {"EUR": CurrencyRate("EUR",4.3917)})
        self.assertEqual(set(calls), {("KRK","NCE",DAY,DAY+timedelta(days=30)),
                                     ("NCE","KRK",DAY,DAY+timedelta(days=30))})

    def test_refresh_rebuilds_removals_and_keeps_parent_and_other_prices_immutable(self):
        original = {p.name: p.read_bytes() for p in self.repo.folder.iterdir()}
        output = self.run_update()
        doc = json.loads((output / "step6-results.json").read_text())
        self.assertEqual(doc["results"], [])  # Removed flight no longer creates any itinerary.
        self.assertNotEqual(doc["collection_coverage"]["run_id"], "FIXTURE-BASE")
        composite = update.certified_repository(output / "sources")
        key = ("easyJet", "LTN", "TFS", str(DAY), "calendar")
        self.assertEqual(composite.rows[key], self.repo.rows[key])
        ledger = update.load_provenance(composite)
        self.assertEqual(ledger["observations"][update.key_id(key)], "FIXTURE-BASE")
        self.assertEqual(original, {p.name: p.read_bytes() for p in self.repo.folder.iterdir()})
        update.validate_publication(doc, composite)
        self.assertEqual(batch.validate_batch(output, DAY, 0)["6"]["results"], 0)

    def test_fresh_and_inherited_leg_provenance_survive_real_builder(self):
        def fetch(repo, selected, start, end, rates):
            for carrier, origin, destination in selected:
                rows = [self.low] if origin == "KRK" else []
                record_checked(carrier, origin, destination, start, end, rows, "google_flights_http")
        with patch.object(update, "fetch_selected", side_effect=fetch):
            output = update.execute(self.plan(), self.root / "kept")
        doc = json.loads((output / "step6-results.json").read_text())
        low, jet = doc["results"][0]["legs"]
        self.assertEqual(low["source_observation_run_id"], doc["data_lineage"]["revision_id"])
        self.assertEqual(jet["source_observation_run_id"], "FIXTURE-BASE")
        self.assertGreater(doc["results"][0]["price_total_regular_pln"], 1000)
        batch.validate_batch(output, DAY, 0)
        doc["results"][0]["legs"][1]["source_observation_run_id"] = "fake"
        with self.assertRaisesRegex(RuntimeError, "provenance"):
            update.validate_publication(doc)

    def test_failure_does_not_certify_or_publish_and_stage_cannot_overwrite_parent(self):
        with patch.object(update, "fetch_selected", side_effect=RuntimeError("source failed")):
            with self.assertRaisesRegex(RuntimeError, "source failed"):
                update.execute(self.plan(), self.root / "failed")
        self.assertFalse((self.root / "failed/sources/complete.json").exists())
        self.assertEqual(json.loads((self.root / "failed/validation-report.json").read_text())["status"], "failed")
        coverage = json.loads((self.root / "failed/source-coverage.json").read_text())
        self.assertEqual(coverage["status"], "failed")
        self.assertEqual(coverage["missing_queries"], 2)
        with self.assertRaisesRegex(RuntimeError, "empty stage"):
            update.execute(self.plan(), self.base)

    def test_missing_reverse_calendar_is_a_failure_not_empty_availability(self):
        def partial_response(repo, selected, start, end, rates):
            record_checked("Ryanair", "KRK", "LTN", start, end, [], "google_flights_http")
        with patch.object(update, "fetch_selected", side_effect=partial_response):
            with self.assertRaisesRegex(RuntimeError, "sources incomplete"):
                update.execute(self.plan(), self.root / "missing-reverse")
        self.assertFalse((self.root / "missing-reverse/sources/complete.json").exists())
        report = json.loads((self.root / "missing-reverse/source-coverage.json").read_text())
        self.assertEqual(report["missing_queries"], 1)

    def test_provenance_tamper_blocks_reader_and_publication(self):
        output = self.run_update()
        path = output / "sources/provenance.json"
        data = json.loads(path.read_text()); data["lineage"]["updated_at"] = update.now(); atomic_json(path, data)
        with self.assertRaisesRegex(RuntimeError, "provenance changed"):
            update.certified_repository(output / "sources")

    def test_second_partial_update_does_not_reset_old_observation_dates(self):
        output = self.run_update()
        old = json.loads((output / "sources/provenance.json").read_text())
        second = self.run_update(self.plan(base=output), "second")
        new = json.loads((second / "sources/provenance.json").read_text())
        self.assertEqual(new["lineage"]["source_runs"]["FIXTURE-BASE"], old["lineage"]["source_runs"]["FIXTURE-BASE"])
        self.assertEqual(new["lineage"]["last_full_collection_at"], old["lineage"]["last_full_collection_at"])
        self.assertEqual(new["lineage"]["parent_revision_id"], old["lineage"]["revision_id"])

    def test_expired_inherited_prices_cannot_be_made_fresh_by_a_new_revision(self):
        plan = self.plan()
        ledger = deepcopy(plan["ledger"])
        ledger["lineage"]["source_runs"]["FIXTURE-BASE"]["collected_from"] = (datetime.now(timezone.utc)-timedelta(hours=25)).isoformat()
        with self.assertRaisesRegex(RuntimeError, "24 hours"):
            update.validate_lineage(ledger["lineage"])

    def test_compare_and_swap_publication_and_rollback(self):
        output = self.run_update()
        public = self.root / "public"; public.mkdir()
        for suffix in ("results.json", "results.collection-report.json"):
            shutil.copyfile(self.base / f"step6-{suffix}", public / f"step6-{suffix}")
        (public / "step6-results.json").write_text("changed by another update")
        with self.assertRaisesRegex(RuntimeError, "Public base changed"):
            batch.promote_batch(output, public)
        shutil.copyfile(self.base / "step6-results.json", public / "step6-results.json")
        replace = Path.replace
        def fail(path, target):
            if path.name == "step6-results.collection-report.json.pending":
                raise OSError("late publication failure")
            return replace(path, target)
        with patch.object(Path, "replace", fail), self.assertRaisesRegex(OSError, "late publication"):
            batch.promote_batch(output, public)
        self.assertEqual((public / "step6-results.json").read_bytes(), (self.base / "step6-results.json").read_bytes())
        batch.promote_batch(output, public)
        self.assertEqual((public / "step6-results.json").read_bytes(), (output / "step6-results.json").read_bytes())

    def test_carrier_route_parser_is_strict(self):
        self.assertEqual(update.parse_route("Wizz Air:KRK:NCE"), ("Wizz Air", "KRK", "NCE"))
        for value in ("LOT:KRK:NCE", "Wizz Air:KRK:KRK", "Ryanair:krk:NCE", "Ryanair:KRK"):
            with self.assertRaises(Exception):
                update.parse_route(value)


if __name__ == "__main__":
    unittest.main()
