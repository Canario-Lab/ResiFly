"""Verify missing Step 6 Wizz metadata, without collecting other airline prices.

The official full-window timetable determines which technical clocks need
checking. Google is used only for numbers/block times, never to manufacture a
fare for a Wizz calendar. Unavailable or unverified pairs remain pending.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.collection_coverage import atomic_json
from scripts.collect_step1 import AIRPORT_TIMEZONES
from scripts.collect_step1b import GoogleFlightsClient
from scripts.collect_step2 import wizz_timetable
from scripts.verify_wizz_expansion_schedules import technical_rows
from scripts.wizz_schedules import WIZZ_ROUTE_FILE


def append_verified(document, rows):
    known = {(r["origin"], r["destination"]) for r in document["routes"]}
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["origin"], row["destination"])].append(row)
    for pair, evidence in sorted(grouped.items()):
        if pair in known:
            continue
        values = Counter((r["flight_number"], r["duration_minutes"]) for r in evidence)
        number, duration = values.most_common(1)[0][0]
        document["routes"].append({"origin": pair[0], "destination": pair[1],
            "flight_number": number, "duration_minutes": duration,
            "verification": {"source": "Google Flights HTTP individual Wizz offers",
                "verified_on": date.today().isoformat(), "observations": evidence}})
        by_clock = defaultdict(list)
        for row in evidence:
            by_clock[row["departure_at"][11:16]].append(row)
        for clock, clock_rows in sorted(by_clock.items()):
            options = {(r["flight_number"], r["duration_minutes"]) for r in clock_rows}
            if options == {(number, duration)}:
                continue
            base = {"origin": pair[0], "destination": pair[1], "departure_time": clock}
            if len(options) == 1:
                n, d = next(iter(options))
                document.setdefault("flight_number_overrides_by_departure_time", []).append(
                    {**base, "flight_number": n, "duration_minutes": d})
                continue
            by_weekday = defaultdict(list)
            for row in clock_rows:
                by_weekday[datetime.fromisoformat(row["departure_at"]).isoweekday()].append(row)
            for weekday, day_rows in sorted(by_weekday.items()):
                options = {(r["flight_number"], r["duration_minutes"]) for r in day_rows}
                if len(options) == 1:
                    n, d = next(iter(options))
                    document.setdefault("flight_number_overrides_by_departure_weekday_and_time", []).append(
                        {**base, "departure_weekday": weekday, "flight_number": n, "duration_minutes": d})
                else:
                    # Keep every conflicting dated observation explicitly;
                    # never choose one number/block time arbitrarily.
                    for row in day_rows:
                        document.setdefault("flight_number_overrides_by_departure_date_and_time", []).append(
                            {**base, "departure_date": row["departure_at"][:10],
                             "flight_number": row["flight_number"], "duration_minutes": row["duration_minutes"]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--from-date", type=date.fromisoformat, required=True)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    snapshot = json.loads(args.snapshot.read_text())
    AIRPORT_TIMEZONES.update({c: r["timezone"] for c, r in snapshot["airports"].items() if r.get("timezone")})
    identity = {"period_from": str(args.from_date), "period_to": str(args.from_date + timedelta(days=args.days)),
                "snapshot_date": snapshot["as_of"]}
    result = {**identity, "rows": [], "routes": [], "pending": [], "completed": []}
    if args.output.exists():
        result = json.loads(args.output.read_text())
        if any(result[k] != v for k, v in identity.items()):
            raise RuntimeError("Technical evidence has another date window")
    client = GoogleFlightsClient(family="Wizz technical", attempts=4)
    pairs = {(r["hub"], r["polish_airport"]) for r in plan["pending"] if r["airline"] == "Wizz Air"}
    for left, right in sorted(pairs):
        pair_rows, pair_ready = [], True
        for origin, destination in ((left, right), (right, left)):
            key = [origin, destination]
            if key in result["completed"]:
                pair_rows.extend(r for r in result["rows"] if [r["origin"], r["destination"]] == key)
                continue
            timetable = wizz_timetable(origin, destination, args.from_date,
                                       args.from_date + timedelta(days=args.days), "regular")
            required = {(datetime.fromisoformat(r["departureDate"]).isoweekday(), r["departureDate"][11:16])
                        for r in timetable}
            covered, observed = set(), []
            for raw_day in sorted({r["departureDate"][:10] for r in timetable}):
                day = date.fromisoformat(raw_day)
                clocks = {(day.isoweekday(), r["departureDate"][11:16]) for r in timetable
                          if r["departureDate"].startswith(raw_day)}
                if clocks <= covered:
                    continue
                found = technical_rows(client.availability(origin, destination, day), origin, destination)
                observed.extend(r for r in found if r not in observed)
                covered |= {(datetime.fromisoformat(r["departure_at"]).isoweekday(), r["departure_at"][11:16]) for r in found}
            complete = bool(required) and required <= covered
            result["routes"].append({"origin": origin, "destination": destination,
                "timetable_flights": len(timetable), "required_weekday_clocks": len(required),
                "verified_weekday_clocks": len(required & covered), "complete": complete})
            result["rows"].extend(r for r in observed if r not in result["rows"])
            result["completed"].append(key)
            atomic_json(args.output, result)
            pair_rows.extend(observed)
            print(origin, destination, "verified" if complete else "PENDING", len(timetable), len(observed), flush=True)
        statuses = [r["complete"] for r in result["routes"] if {r["origin"], r["destination"]} == {left, right}]
        pair_ready = len(statuses) == 2 and all(statuses)
        if not pair_ready:
            if [left, right] not in result["pending"]:
                result["pending"].append([left, right])
        elif args.apply:
            document = json.loads(WIZZ_ROUTE_FILE.read_text())
            append_verified(document, pair_rows)
            atomic_json(WIZZ_ROUTE_FILE, document)
        atomic_json(args.output, result)


if __name__ == "__main__":
    main()
