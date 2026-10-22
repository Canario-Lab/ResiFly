"""Print a reviewable apply_patch from captured GDN network/schedule evidence.

This one-time migration never writes source files or generated public feeds.
"""

import argparse
from collections import defaultdict
from dataclasses import replace
import json
from pathlib import Path
import re
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.discover_transfer_routes import (
    airport_from_snapshot, airport_record, discover_candidates,
)
from scripts.search_airports import POLISH_AIRPORTS

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--schedules", type=Path, required=True)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    evidence = json.loads(args.schedules.read_text(encoding="utf-8"))
    candidates = discover_candidates(snapshot)
    by_pair = defaultdict(list)
    for row in evidence["routes"]:
        by_pair[(row["origin"], row["destination"])].append(row)
    verified = {key for key in by_pair if key[::-1] in by_pair}
    documents = {}
    originals = {}
    for path in sorted((ROOT / "data").glob("*transfer-airports.json")):
        originals[path] = path.read_text(encoding="utf-8")
        document = json.loads(originals[path])
        document["scope"]["polish_airports"] = list(POLISH_AIRPORTS)
        document["verified_on"] = snapshot["as_of"]
        for section in (document.get("selection_method", {}), document.get("usage_policy", {})):
            for key, value in section.items():
                if isinstance(value, str):
                    section[key] = re.sub(r"WAW/WMI/KTW/KRK(?!/GDN)", "WAW/WMI/KTW/KRK/GDN", value).replace("wszystkie cztery polskie", "wszystkie pięć polskich")
        if "selection_method" in document:
            selection = document["selection_method"]
            if "excluded_endpoints" in selection and path.name != "mixed-transfer-airports.json":
                selection["excluded_endpoints"] = list(dict.fromkeys(selection["excluded_endpoints"] + ["GDN"]))
            if path.name == "mixed-transfer-airports.json":
                selection["endpoint_transfer_exception"] = "GDN zachowuje istniejącą przesiadkę tylko w wariancie B do KRK; nowe endpointy GDN korzystają z pozostałych zatwierdzonych hubów."
        document["sources"] = [source for source in document.get("sources", []) if source.get("name") != "Weryfikacja rozszerzenia o Gdańsk GDN"]
        document["sources"].append({
            "name": "Weryfikacja rozszerzenia o Gdańsk GDN", "verified_on": snapshot["as_of"],
            "urls": ["https://www.ryanair.com/api/views/locate/3/routes", "https://www.wizzair.com/en-gb"],
            "finding": "Sprawdzono GDN w oficjalnych siatkach obu linii; potwierdzone techniczne rozkłady Wizz zweryfikowano przez Google Flights HTTP. Nie rozszerzano niezwiązanych tras starych endpointów.",
        })
        documents[path.name] = document

    networks = {carrier: {tuple(pair) for pair in rows} for carrier, rows in snapshot["routes"].items()}

    def airlines(hub):
        found = []
        for key, name in (("ryanair", "Ryanair"), ("wizzair", "Wizz Air")):
            if ("GDN", hub) in networks[key] or (hub, "GDN") in networks[key]:
                if key != "wizzair" or ("GDN", hub) in verified:
                    found.append(name)
        return found

    for name in ("binter", "iberia", "vueling", "air-europa", "volotea", "canaryfly"):
        document = documents[f"{name}-transfer-airports.json"]
        for airport in document["airports"]:
            carriers = airlines(airport["iata"])
            if not carriers:
                continue
            if "polish_routes" in airport:
                airport["polish_routes"] = [row for row in airport["polish_routes"] if row["polish_airport"] != "GDN"]
                airport["polish_routes"].append({"polish_airport": "GDN", "airlines": carriers})
            else:
                airport["eligibility_evidence"] = [row for row in airport.get("eligibility_evidence", []) if row.get("polish_airport") != "GDN"]
                airport.setdefault("eligibility_evidence", []).extend({"polish_airport": "GDN", "airline": carrier} for carrier in carriers)

    step_files = {
        "step3": ("ryanair-transfer-airports.json", None),
        "step4": ("wizzair-transfer-airports.json", None),
        "step5_variant_a": ("mixed-transfer-airports.json", "ryanair_tenerife_wizzair_poland"),
        "step5_variant_b": ("mixed-transfer-airports.json", "wizzair_tenerife_ryanair_poland"),
    }
    for step, (filename, variant) in step_files.items():
        document = documents[filename]
        rows = document["airports"] if variant is None else document["variants"][variant]["airports"]
        for candidate in candidates[step]:
            if "GDN" not in candidate.polish_airports:
                continue
            if step in ("step4", "step5_variant_a") and ("GDN", candidate.iata) not in verified:
                continue
            row = next((item for item in rows if item["iata"] == candidate.iata), None)
            if row:
                row["polish_airports"] = list(dict.fromkeys(row["polish_airports"] + ["GDN"]))
            else:
                rows.append(airport_record(airport_from_snapshot(snapshot, candidate.iata), replace(candidate, polish_airports=("GDN",)), step))
                document["airport_timezones"][candidate.iata] = snapshot["airports"][candidate.iata]["timezone"]
        if variant is None:
            document["selection_method"]["result_count"] = len(rows)

    mixed = documents["mixed-transfer-airports.json"]
    for variant, label in (("ryanair_tenerife_wizzair_poland", "variant_a"), ("wizzair_tenerife_ryanair_poland", "variant_b")):
        rows = mixed["variants"][variant]["airports"]
        mixed["selection_method"][label + "_result_count"] = len(rows)
        discount = mixed["resident_discount_on_tenerife_leg"][label]
        for eligible, key in ((True, "eligible_transfer_airports"), (False, "ineligible_transfer_airports")):
            discount[key] = sorted(row["iata"] for row in rows if bool(row.get("resident_discount_eligible_on_tenerife_leg")) == eligible)
    mixed["selection_method"]["unique_transfer_airport_count"] = len({row["iata"] for variant in mixed["variants"].values() for row in variant["airports"]})

    path = ROOT / "data" / "wizz-route-schedules.json"
    originals[path] = path.read_text(encoding="utf-8")
    shared = json.loads(originals[path])
    new_routes, overrides = [], []
    for pair, rows in sorted(by_pair.items()):
        if pair not in verified:
            continue
        rows.sort(key=lambda row: row["departure_at"])
        first = rows[0]
        new_routes.append({key: first[key] for key in ("origin", "destination", "flight_number", "duration_minutes")} | {
            "verified_on": snapshot["as_of"], "schedule_source": "Google Flights HTTP", "source_url": first["source"],
        })
        seen = {}
        for row in rows:
            key = row["departure_at"][11:16]
            value = (row["flight_number"], row["duration_minutes"])
            if key in seen and seen[key] != value:
                raise RuntimeError(f"Conflicting same-time Wizz evidence for {pair} {key}")
            seen[key] = value
        overrides.extend({"origin": pair[0], "destination": pair[1], "departure_time": key, "flight_number": value[0], "duration_minutes": value[1]} for key, value in sorted(seen.items()))
    new_pairs = {(row["origin"], row["destination"]) for row in new_routes}
    shared["routes"] = [row for row in shared["routes"] if (row["origin"], row["destination"]) not in new_pairs] + new_routes
    shared["flight_number_overrides_by_departure_time"] = [row for row in shared["flight_number_overrides_by_departure_time"] if (row["origin"], row["destination"]) not in new_pairs] + overrides
    for name in ("binter", "iberia"):
        document = documents[f"{name}-transfer-airports.json"]
        hubs = {row["iata"] for row in document["airports"]}
        needed = {(a, b) for a, b in new_pairs if (a == "GDN" and b in hubs) or (b == "GDN" and a in hubs)}
        document["wizz_route_schedules"] = [row for row in document["wizz_route_schedules"] if (row["origin"], row["destination"]) not in needed]
        document["wizz_route_schedules"].extend(row for row in new_routes if (row["origin"], row["destination"]) in needed)
        document["flight_number_overrides_by_departure_time"] = [row for row in document.get("flight_number_overrides_by_departure_time", []) if (row["origin"], row["destination"]) not in needed]
        document.setdefault("flight_number_overrides_by_departure_time", []).extend(row for row in overrides if (row["origin"], row["destination"]) in needed)
    documents[path.name] = shared

    print("*** Begin Patch")
    for path, original in originals.items():
        replacement = json.dumps(documents[path.name], ensure_ascii=False, indent=2) + "\n"
        if original == replacement:
            continue
        print(f"*** Update File: {path}")
        print("@@")
        print("\n".join("-" + line for line in original.splitlines()))
        print("\n".join("+" + line for line in replacement.splitlines()))
    print("*** End Patch")


if __name__ == "__main__":
    main()
