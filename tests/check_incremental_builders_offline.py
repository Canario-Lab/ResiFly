"""Optional local acceptance: real certified parent, synthetic removal, no HTTP.

All source responses for the selected easyJet LPL/TFS route are empty fixture
observations. All eleven real builders run cache-only in a disposable directory.
Nothing is promoted; a compact QA report is the only retained artifact.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import incremental_update as update
from scripts.collection_coverage import atomic_json, record_checked
from scripts.search_steps import STEPS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-batch", required=True, type=Path)
    parser.add_argument("--base-ref")
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    original = {p.name: update.digest(p) for p in (ROOT / "data").glob("step*-results*.json")}
    plan = update.plan_update(args.base_batch, [("easyJet", "LPL", "TFS")], args.base_ref)
    parent_digests = plan["parent"].digests()
    def empty_fixture(repo, selected, start, end, rates):
        assert selected == {("easyJet", "LPL", "TFS"), ("easyJet", "TFS", "LPL")}
        record = start
        while record <= end:
            for carrier, origin, destination in selected:
                record_checked(carrier, origin, destination, record, record, [], "google_flights_http")
            from datetime import timedelta
            record += timedelta(days=1)
    with tempfile.TemporaryDirectory(prefix="partial-all-builders-fixture-") as temp:
        with patch.object(update, "fetch_selected", side_effect=empty_fixture), patch(
                "curl_cffi.requests.Session.request", side_effect=AssertionError("HTTP FORBIDDEN")):
            output = update.execute(plan, Path(temp) / "composite")
        repo = update.certified_repository(output / "sources")
        counts, removed = {}, 0
        for step in STEPS:
            before = plan["documents"][step]["results"]
            doc = json.loads((output / f"step{step}-results.json").read_text())
            expected = [r for r in before if not any(
                (leg["carrier"], leg["departure_airport"], leg["arrival_airport"]) in plan["selected"]
                for leg in r["legs"])]
            actual = deepcopy(doc["results"])
            for result in actual:
                for leg in result["legs"]:
                    leg.pop("source_observation_run_id", None)
            assert actual == expected, f"Unexpected changed price/flight in step {step}"
            removed += len(before)-len(actual)
            counts[step] = len(actual)
            update.validate_publication(doc, repo)
        assert removed > 0
        assert plan["parent"].digests() == parent_digests
        assert original == {p.name: update.digest(p) for p in (ROOT / "data").glob("step*-results*.json")}
        atomic_json(args.report, {"status": "pass", "fixture_only": True,
            "public_data_modified": False, "promoted": False, "all_builders_cache_only": True,
            "refreshed_fixture_route_days": plan["plan"]["calendar_queries_to_refresh"],
            "removed_dependent_results": removed, "all_other_flights_and_prices_unchanged": True,
            "result_counts": counts, "parent_immutable": True})
    print("PASS: disposable partial-update fixture, eleven real cache-only builders, no public changes")


if __name__ == "__main__":
    main()
