"""Explicit Step 6 network audit, separate from recurring price collection.

Use a reviewed official easyJet catalogue snapshot, then intersect the complete
FR/Wizz graphs for every canonical Polish endpoint. Incomplete Wizz metadata
stays pending. --apply adds complete candidates without removing seasonal ones.
"""
import argparse
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.collection_coverage import atomic_json
from scripts.discover_transfer_routes import (
    _http_client, fetch_ryanair, fetch_wizz, fill_timezones, edge_exists,
)
from scripts.search_airports import POLISH_AIRPORTS, TENERIFE_AIRPORTS
from scripts.wizz_schedules import load_wizz_route_data

ROOT = Path(__file__).resolve().parents[1]
TRANSFER_FILE = ROOT / "data/easyjet-transfer-airports.json"


def fresh_snapshot(as_of, relevant):
    with _http_client() as client:
        fr, fr_airports = fetch_ryanair(client)
        wizz, wizz_airports = fetch_wizz(client)
    airports = deepcopy(wizz_airports)
    for code, row in fr_airports.items():
        airports.setdefault(code, {}).update({k: v for k, v in row.items() if v not in (None, "")})
    fill_timezones(airports, relevant)
    return {"as_of": str(as_of), "airports": airports,
            "routes": {"ryanair": sorted(fr), "wizzair": sorted(wizz)}}


def build_plan(network, snapshot, known):
    if not network.get("source") or not network.get("verified_on"):
        raise ValueError("An explicitly reviewed official easyJet network is required")
    if set(network["tenerife_destinations"]) != set(TENERIFE_AIRPORTS):
        raise ValueError("Both Tenerife airports must be reviewed")
    ready, pending, unmatched = [], [], []
    hubs = sorted(set().union(*map(set, network["tenerife_destinations"].values())))
    for hub in hubs:
        meta = snapshot["airports"].get(hub, {})
        tenerife = sorted(t for t, values in network["tenerife_destinations"].items() if hub in values)
        found = False
        for family, carrier in (("ryanair", "Ryanair"), ("wizzair", "Wizz Air")):
            edges = set(map(tuple, snapshot["routes"][family]))
            for polish in POLISH_AIRPORTS:
                if polish == hub or not edge_exists(edges, hub, polish):
                    continue
                found = True
                reasons = []
                if not meta.get("timezone") or not meta.get("country_code"):
                    reasons.append("Missing independently sourced airport timezone/country")
                if meta.get("country_code", "").upper() == "ES":
                    reasons.append("New Spanish easyJet leg needs resident-rule and route-fee review")
                if carrier == "Wizz Air" and not all(p in known for p in ((hub, polish), (polish, hub))):
                    reasons.append("Missing verified Wizz numbers/block times in both directions")
                row = {"hub": hub, "polish_airport": polish, "airline": carrier,
                       "tenerife_airports": tenerife, "reasons": reasons}
                (pending if reasons else ready).append(row)
        if not found:
            unmatched.append(hub)
    return {"schema_version": 1, "as_of": snapshot["as_of"], "easyjet_network": network,
            "ready": ready, "pending": pending, "no_shared_polish_route": unmatched}


def apply_plan(report, snapshot, existing=None):
    document = deepcopy(existing) if existing else {
        "schema_version": 2, "name": "easyJet + Ryanair/Wizz Air — krok 6",
        "purpose": "easyJet only on the Tenerife leg; one same-IATA self-transfer",
        "scope": {"polish_airports": list(POLISH_AIRPORTS), "tenerife_airports": list(TENERIFE_AIRPORTS)},
        "usage_policy": {"step": 6, "flight_data_source": "google_flights_http",
            "discovery_mode": "fixed_allowlist", "do_not_rediscover_each_run": True,
            "update_only_on_explicit_user_request": True,
            "google_family_order": "after Air Europa, shared global limit three including retries",
            "passengers": {"adults": 1, "children": 0, "infants": 0}},
        "easyjet_airline_codes": {"accepted_marketing": ["U2", "EC", "DS"]}, "airports": []}
    for candidate in report["ready"]:
        hub = candidate["hub"]
        row = next((a for a in document["airports"] if a["iata"] == hub), None)
        if row is None:
            meta = snapshot["airports"][hub]
            row = {"iata": hub, "name_pl": meta.get("name", hub),
                   "timezone": meta["timezone"], "country_code": meta["country_code"],
                   "tenerife_airports": candidate["tenerife_airports"],
                   "resident_discount_eligible_on_easyjet_leg": False,
                   "easyjet_resident_fare_multiplier": 1.0, "resident_pricing_method": "none",
                   "resident_eligibility_evidence": {"verified_on": report["as_of"],
                       "source": report["easyjet_network"]["resident_terms"],
                       "reason": "International Tenerife leg; the Canary domestic subsidy does not apply"},
                   "polish_routes": []}
            document["airports"].append(row)
        route = next((r for r in row["polish_routes"] if r["polish_airport"] == candidate["polish_airport"]), None)
        if route is None:
            route = {"polish_airport": candidate["polish_airport"], "airlines": []}
            row["polish_routes"].append(route)
        if candidate["airline"] not in route["airlines"]:
            route["airlines"].append(candidate["airline"])
        row["polish_routes"].sort(key=lambda r: r["polish_airport"])
    document.update(verified_on=report["as_of"], route_network_evidence=report["easyjet_network"],
                    pending_routes=report["pending"], no_shared_polish_route=report["no_shared_polish_route"])
    document["airports"].sort(key=lambda a: a["iata"])
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--easyjet-network", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--refresh-low-cost", action="store_true")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    network = json.loads(args.easyjet_network.read_text())
    if args.refresh_low_cost:
        snapshot = fresh_snapshot(args.as_of, set().union(*map(set, network["tenerife_destinations"].values())))
        atomic_json(args.snapshot, snapshot)
    else:
        snapshot = json.loads(args.snapshot.read_text())
    schedules, _ = load_wizz_route_data()
    report = build_plan(network, snapshot, schedules)
    atomic_json(args.report, report)
    print(json.dumps({key: len(report[key]) for key in ("ready", "pending", "no_shared_polish_route")}))
    if args.apply:
        previous = json.loads(TRANSFER_FILE.read_text()) if TRANSFER_FILE.exists() else None
        atomic_json(TRANSFER_FILE, apply_plan(report, snapshot, previous))


if __name__ == "__main__":
    main()
