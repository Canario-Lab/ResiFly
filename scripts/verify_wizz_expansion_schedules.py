"""Verify new endpoint Wizz technical schedules against HTTP Google Flights offers.

Produces local evidence only. Never invents or activates a schedule in an allowlist.
"""

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import sys
import time

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.collect_step1 import AIRPORT_TIMEZONES
from scripts.collect_step1b import GoogleFlightsClient, _at, _google_datetime, _google_flights_payload
from scripts.collect_step2 import wizz_timetable
from scripts.discover_transfer_routes import discover_candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--from-date", type=date.fromisoformat, required=True)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--complete-times", action="store_true")
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    for code, row in snapshot["airports"].items():
        if row.get("timezone"):
            AIRPORT_TIMEZONES[code] = row["timezone"]
    candidates = discover_candidates(snapshot)
    hubs = {
        item.iata for key in ("step4", "step5_variant_a")
        for item in candidates[key] if "GDN" in item.polish_airports
    }
    # The resident variants can also use low-cost Spanish routes not present in 4/5.
    for a, b in snapshot["routes"]["wizzair"]:
        other = b if a == "GDN" else a if b == "GDN" else None
        if other and str(snapshot["airports"].get(other, {}).get("country_code", "")).upper() == "ES":
            hubs.add(other)
    hubs.add("TFS")
    routes = sorted((a, b) for hub in hubs for a, b in (("GDN", hub), (hub, "GDN")))
    result = {"as_of": args.from_date.isoformat(), "source": "Google Flights HTTP direct offers; Wizz timetableV2 dates", "routes": [], "inactive_routes": [], "pending": []}
    if args.output.exists():
        result = json.loads(args.output.read_text(encoding="utf-8"))
    completed = set() if args.complete_times else {(row["origin"], row["destination"]) for row in result["routes"]}
    completed.update(tuple(pair) for pair in result["inactive_routes"])
    client = GoogleFlightsClient()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for origin, destination in routes:
        if (origin, destination) in completed:
            continue
        rows = wizz_timetable(origin, destination, args.from_date, args.from_date + timedelta(days=args.days), "regular")
        dates = sorted({row["departureDate"][:10] for row in rows})
        if not dates:
            result["inactive_routes"].append([origin, destination])
            print(origin, destination, "no active flights", flush=True)
        else:
            verified = [row for row in result["routes"] if (row["origin"], row["destination"]) == (origin, destination)]
            covered = {row["departure_at"][11:16] for row in verified}
            for day in dates:
                expected = {row["departureDate"][11:16] for row in rows if row["departureDate"].startswith(day)}
                if args.complete_times and expected <= covered:
                    continue
                html = client.availability(origin, destination, date.fromisoformat(day))
                for offer in _google_flights_payload(html):
                    segments = _at(_at(offer, 0, []), 2, [])
                    if len(segments) != 1:
                        continue
                    segment = segments[0]
                    flight = _at(segment, 22, [])
                    if _at(segment, 3) != origin or _at(segment, 6) != destination or _at(flight, 0) not in ("W6", "W4", "W9"):
                        continue
                    departure = _google_datetime(_at(segment, 20), _at(segment, 8), origin)
                    arrival = _google_datetime(_at(segment, 21), _at(segment, 10), destination)
                    duration = round((arrival - departure).total_seconds() / 60)
                    number = str(_at(flight, 1))
                    prefix = _at(flight, 0)
                    number = number if number.startswith(prefix) else prefix + number
                    if duration <= 0:
                        raise RuntimeError(f"Invalid duration for {origin}-{destination}")
                    evidence = {"origin": origin, "destination": destination, "flight_number": number, "duration_minutes": duration, "departure_at": departure.isoformat(), "arrival_at": arrival.isoformat(), "source": "https://www.google.com/travel/flights"}
                    if evidence not in verified:
                        verified.append(evidence)
                    covered.add(departure.strftime("%H:%M"))
                if verified and not args.complete_times:
                    break
                time.sleep(0.6)
            if not verified:
                result["pending"].append([origin, destination])
                print(origin, destination, "PENDING technical evidence", flush=True)
            else:
                for row in verified:
                    if row not in result["routes"]:
                        result["routes"].append(row)
                print(origin, destination, [(r["flight_number"], r["duration_minutes"]) for r in verified], flush=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
