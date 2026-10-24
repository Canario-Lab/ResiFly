"""Print a reviewable endpoint-only apply_patch from network/schedule evidence.

This one-time migration never writes source files or generated public feeds.
"""

import argparse
from collections import defaultdict, Counter
from datetime import date, datetime, timedelta
from dataclasses import replace
import difflib
import json
from pathlib import Path
import re
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.discover_transfer_routes import (
    airport_from_snapshot, airport_record, discover_candidates,
    missing_wizz_schedules, schedule_keys, refresh_discount_lists,
)
from scripts.search_airports import POLISH_AIRPORTS
from scripts.collection_coverage import atomic_json

ROOT = Path(__file__).resolve().parents[1]


def refresh_endpoint_text(value):
    """Refresh legacy endpoint lists without duplicating the latest addition."""
    value = re.sub(r"\bWAW/WMI/(?:KTW/KRK|KRK/KTW)(?:/[A-Z]{3})*",
                   "/".join(POLISH_AIRPORTS), value)
    return re.sub(r"wszystkie (?:pięć|sześć|siedem|osiem|dziewięć|dziesięć|jedenaście|dwanaście|trzynaście) polskich lotnisk[ao]?",
                  "wszystkie polskie lotniska z rejestru endpointów", value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", choices=POLISH_AIRPORTS, default="GDN")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--schedules", type=Path, required=True)
    parser.add_argument("--from-date", type=date.fromisoformat, required=True)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--baseline-directory", type=Path, default=ROOT / "data")
    parser.add_argument("--output-directory", type=Path,
                        help="Write review copies outside data/ instead of printing a patch")
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    evidence = json.loads(args.schedules.read_text(encoding="utf-8"))
    endpoint = args.endpoint
    if evidence.get("endpoint") != endpoint or evidence.get("snapshot_date") != snapshot["as_of"]:
        raise RuntimeError("Mismatched endpoint or snapshot in schedule evidence")
    if (evidence.get("period_from") != args.from_date.isoformat()
            or evidence.get("period_to") != (args.from_date + timedelta(days=args.days)).isoformat()):
        raise RuntimeError("Mismatched calendar window in schedule evidence")
    candidates = discover_candidates(snapshot)
    by_pair = defaultdict(list)
    for row in evidence["routes"]:
        by_pair[(row["origin"], row["destination"])].append(row)
    verified = {key for key in by_pair if key[::-1] in by_pair}
    documents = {}
    originals = {}
    for source in sorted(args.baseline_directory.glob("*transfer-airports.json")):
        path = ROOT / "data" / source.name
        originals[path] = source.read_text(encoding="utf-8")
        document = json.loads(originals[path])
        document["scope"]["polish_airports"] = list(POLISH_AIRPORTS)
        document["verified_on"] = snapshot["as_of"]
        for section in (document.get("selection_method", {}), document.get("usage_policy", {})):
            for key, value in section.items():
                if isinstance(value, str):
                    section[key] = refresh_endpoint_text(value)
        if "selection_method" in document:
            selection = document["selection_method"]
            if "excluded_endpoints" in selection and path.name != "mixed-transfer-airports.json":
                selection["excluded_endpoints"] = list(dict.fromkeys(selection["excluded_endpoints"] + [endpoint]))
            if path.name == "mixed-transfer-airports.json":
                selection["excluded_endpoints"] = list(dict.fromkeys(selection["excluded_endpoints"] + [endpoint]))
        source_name = "Weryfikacja rozszerzenia o " + endpoint
        document["sources"] = [source for source in document.get("sources", []) if source.get("name") != source_name]
        document["sources"].append({
            "name": source_name, "verified_on": snapshot["as_of"],
            "urls": ["https://www.ryanair.com/api/views/locate/3/routes", "https://www.wizzair.com/en-gb"],
            "finding": (
                f"Sprawdzono {endpoint} w oficjalnych siatkach Ryanaira i Wizz. "
                f"Materiał techniczny Wizz zawiera {len(evidence['routes'])} obserwacji; "
                f"nierozstrzygnięte trasy: {len(evidence.get('pending', []))}, "
                f"nieaktywne w oknie: {len(evidence.get('inactive_routes', []))}. "
                "Dowody mają własne daty; brak obserwacji nie poświadcza rozkładu. "
                "Nie przeniesiono cen z audytu technicznego. Zachowano trasy pozostałych endpointów."
            ),
        })
        documents[path.name] = document

    networks = {carrier: {tuple(pair) for pair in rows} for carrier, rows in snapshot["routes"].items()}

    def airlines(hub):
        found = []
        for key, name in (("ryanair", "Ryanair"), ("wizzair", "Wizz Air")):
            if (endpoint, hub) in networks[key] or (hub, endpoint) in networks[key]:
                if key != "wizzair" or (endpoint, hub) in verified:
                    found.append(name)
        return found

    for name in ("binter", "iberia", "vueling", "air-europa", "volotea", "canaryfly"):
        document = documents[f"{name}-transfer-airports.json"]
        for airport in document["airports"]:
            carriers = airlines(airport["iata"])
            if not carriers:
                continue
            if "polish_routes" in airport:
                airport["polish_routes"] = [row for row in airport["polish_routes"] if row["polish_airport"] != endpoint]
                airport["polish_routes"].append({"polish_airport": endpoint, "airlines": carriers})
            else:
                airport["eligibility_evidence"] = [row for row in airport.get("eligibility_evidence", []) if row.get("polish_airport") != endpoint]
                airport.setdefault("eligibility_evidence", []).extend({"polish_airport": endpoint, "airline": carrier} for carrier in carriers)

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
            if endpoint not in candidate.polish_airports:
                continue
            isolated = replace(candidate, polish_airports=(endpoint,))
            # Chained endpoint reviews must use the chosen input configuration,
            # not an unrelated live checkout that may lack the first addition.
            known = schedule_keys(documents["binter-transfer-airports.json"], json.loads((args.baseline_directory / "wizz-route-schedules.json").read_text())) | verified
            if missing_wizz_schedules(isolated, step, known):
                continue
            row = next((item for item in rows if item["iata"] == candidate.iata), None)
            if row:
                missing_tenerife = set(candidate.tenerife_airports) - set(row["tenerife_airports"])
                if missing_tenerife:
                    raise RuntimeError(f"Review new Tenerife airports explicitly for {step}/{candidate.iata}: {sorted(missing_tenerife)}")
                row["polish_airports"] = list(dict.fromkeys(row["polish_airports"] + [endpoint]))
            else:
                rows.append(airport_record(airport_from_snapshot(snapshot, candidate.iata), isolated, step))
                document["airport_timezones"][candidate.iata] = snapshot["airports"][candidate.iata]["timezone"]
        if variant is None:
            refresh_discount_lists(document)
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
    originals[path] = (args.baseline_directory / path.name).read_text(encoding="utf-8")
    shared = json.loads(originals[path])
    new_routes, overrides, weekday_overrides, dated_overrides = [], [], [], []
    for pair, rows in sorted(by_pair.items()):
        if pair not in verified:
            continue
        rows.sort(key=lambda row: row["departure_at"])
        first = rows[0]
        new_routes.append({key: first[key] for key in ("origin", "destination", "flight_number", "duration_minutes")} | {
            "verified_on": snapshot["as_of"], "schedule_source": "Google Flights HTTP", "source_url": first["source"],
        })
        seen = defaultdict(list)
        for row in rows:
            key = row["departure_at"][11:16]
            seen[key].append(row)
        for clock, records in sorted(seen.items()):
            value_for = lambda row: (row["flight_number"], row["duration_minutes"])
            base = Counter(value_for(row) for row in records).most_common(1)[0][0]
            common = {"origin": pair[0], "destination": pair[1], "departure_time": clock}
            overrides.append({**common, "flight_number": base[0], "duration_minutes": base[1]})
            by_weekday = defaultdict(list)
            for row in records:
                by_weekday[datetime.fromisoformat(row["departure_at"]).isoweekday()].append(row)
            for weekday, records in by_weekday.items():
                weekly = Counter(value_for(row) for row in records).most_common(1)[0][0]
                if weekly != base:
                    weekday_overrides.append({**common, "departure_weekday": weekday,
                                              "flight_number": weekly[0], "duration_minutes": weekly[1]})
                by_date = {}
                for row in records:
                    day, value = row["departure_at"][:10], value_for(row)
                    if day in by_date and by_date[day] != value:
                        raise RuntimeError(f"Conflicting same-day/time Wizz evidence: {pair}/{day}/{clock}")
                    by_date[day] = value
                dated_overrides.extend({**common, "departure_date": day,
                                        "flight_number": value[0], "duration_minutes": value[1]}
                                       for day, value in by_date.items() if value != weekly)
    new_pairs = {(row["origin"], row["destination"]) for row in new_routes}
    shared["routes"] = [row for row in shared["routes"] if (row["origin"], row["destination"]) not in new_pairs] + new_routes
    shared["flight_number_overrides_by_departure_time"] = [row for row in shared["flight_number_overrides_by_departure_time"] if (row["origin"], row["destination"]) not in new_pairs] + overrides
    for field, additions in (("flight_number_overrides_by_departure_weekday_and_time", weekday_overrides),
                             ("flight_number_overrides_by_departure_date_and_time", dated_overrides)):
        if additions or field in shared:
            shared[field] = [row for row in shared.get(field, []) if (row["origin"], row["destination"]) not in new_pairs] + additions
    for name in ("binter", "iberia"):
        document = documents[f"{name}-transfer-airports.json"]
        hubs = {row["iata"] for row in document["airports"]}
        needed = {(a, b) for a, b in new_pairs if (a == endpoint and b in hubs) or (b == endpoint and a in hubs)}
        document["wizz_route_schedules"] = [row for row in document["wizz_route_schedules"] if (row["origin"], row["destination"]) not in needed]
        document["wizz_route_schedules"].extend(row for row in new_routes if (row["origin"], row["destination"]) in needed)
        document["flight_number_overrides_by_departure_time"] = [row for row in document.get("flight_number_overrides_by_departure_time", []) if (row["origin"], row["destination"]) not in needed]
        document.setdefault("flight_number_overrides_by_departure_time", []).extend(row for row in overrides if (row["origin"], row["destination"]) in needed)
        for field in ("flight_number_overrides_by_departure_weekday_and_time", "flight_number_overrides_by_departure_date_and_time"):
            additions = [row for row in shared.get(field, []) if (row["origin"], row["destination"]) in needed]
            if additions or field in document:
                document[field] = [row for row in document.get(field, []) if (row["origin"], row["destination"]) not in needed] + additions
    documents[path.name] = shared

    if args.output_directory:
        output = args.output_directory.resolve()
        if output == (ROOT / "data").resolve() or (ROOT / "data").resolve() in output.parents:
            raise RuntimeError("Review configuration must stay outside public data")
        for name, document in documents.items():
            atomic_json(output / name, document)
        print("Wrote review configuration:", output)
        return

    print("*** Begin Patch")
    for path, original in originals.items():
        replacement = json.dumps(documents[path.name], ensure_ascii=False, indent=2) + "\n"
        if original == replacement:
            continue
        print(f"*** Update File: {path}")
        # One whole-file hunk: repeated JSON fragments are otherwise ambiguous
        # to apply_patch when numeric unified-diff offsets are omitted.
        for line in list(difflib.unified_diff(original.splitlines(), replacement.splitlines(), n=100000))[2:]:
            print("@@" if line.startswith("@@") else line)
    print("*** End Patch")


if __name__ == "__main__":
    main()
