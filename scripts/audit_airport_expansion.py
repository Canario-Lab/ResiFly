"""Capture official network evidence for a local airport expansion; no allowlist edits."""

import argparse
from datetime import date
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.discover_transfer_routes import (
    _http_client, fetch_ryanair, fetch_wizz, fetch_binter, existing_metadata,
    fill_timezones, discover_candidates, load_documents, build_plan,
)
from scripts.search_airports import POLISH_AIRPORTS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--endpoint", choices=POLISH_AIRPORTS, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--low-cost-only", action="store_true",
                        help="Capture low-cost evidence only; Binter still requires an independent official route audit")
    args = parser.parse_args()
    documents = load_documents()
    args.output_directory.mkdir(parents=True, exist_ok=True)
    session = _http_client()
    ryanair, ryanair_airports = fetch_ryanair(session)
    wizz, wizz_airports = fetch_wizz(session)
    airports = existing_metadata(documents)
    for source in (wizz_airports, ryanair_airports):
        for code, row in source.items():
            current = airports.setdefault(code, {})
            current.update({key: value for key, value in row.items() if value not in (None, "")})
    snapshot = {
        "schema_version": 1, "as_of": args.as_of.isoformat(), "airports": airports,
        "routes": {"ryanair": sorted(ryanair), "wizzair": sorted(wizz), "binter": []},
        "source_status": {"ryanair": "complete", "wizzair": "complete", "binter": "not_checked"},
    }
    (args.output_directory / "network-snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # Keep the successful low-cost evidence even if Binter discovery fails.
    # Examine every low-cost neighbour of the new endpoint, not only old hubs.
    binter_candidates = {b if a == args.endpoint else a
                         for a, b in ryanair | wizz if args.endpoint in (a, b)}
    try:
        if not args.low_cost_only:
            snapshot["routes"]["binter"] = sorted(fetch_binter(session, args.as_of, binter_candidates))
            snapshot["source_status"]["binter"] = "complete"
    except Exception as error:
        snapshot["source_status"]["binter"] = "failed"
        snapshot["source_errors"] = {"binter": str(error)}
        raise
    finally:
        (args.output_directory / "network-snapshot.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        session.close()
    candidates = discover_candidates(snapshot)
    fill_timezones(airports, {item.iata for rows in candidates.values() for item in rows})
    (args.output_directory / "network-snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = build_plan(snapshot, documents)
    report["source_status"] = snapshot["source_status"]
    if snapshot["source_status"]["binter"] != "complete":
        report["steps"]["step1"]["note"] = "Binter network not checked by this run; requires separate official route review. An empty list is not evidence of no routes."
    (args.output_directory / "discovery-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for carrier, routes in snapshot["routes"].items():
        if snapshot["source_status"][carrier] != "complete":
            print(carrier, "NOT CHECKED; independent official route review required", flush=True)
            continue
        neighbours = sorted({right if left == args.endpoint else left for left, right in routes if args.endpoint in (left, right)})
        print(carrier, args.endpoint + ":", ", ".join(neighbours), flush=True)
    for step, details in report["steps"].items():
        print(step, "ready", len(details.get("ready", [])), "pending", len(details.get("pending", [])), flush=True)


if __name__ == "__main__":
    main()
