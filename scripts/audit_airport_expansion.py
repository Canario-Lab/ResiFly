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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
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
    }
    (args.output_directory / "network-snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # Keep the successful low-cost evidence even if Binter discovery fails.
    existing_binter = {row["iata"] for row in documents["step1"]["airports"]}
    try:
        snapshot["routes"]["binter"] = sorted(fetch_binter(session, args.as_of, existing_binter))
    finally:
        session.close()
    candidates = discover_candidates(snapshot)
    fill_timezones(airports, {item.iata for rows in candidates.values() for item in rows})
    (args.output_directory / "network-snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = build_plan(snapshot, documents)
    (args.output_directory / "discovery-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for carrier, routes in snapshot["routes"].items():
        gdn = sorted({right if left == "GDN" else left for left, right in routes if "GDN" in (left, right)})
        print(carrier, "GDN:", ", ".join(gdn), flush=True)
    for step, details in report["steps"].items():
        print(step, "ready", len(details.get("ready", [])), "pending", len(details.get("pending", [])), flush=True)


if __name__ == "__main__":
    main()
