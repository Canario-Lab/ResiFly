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

from scripts.collect_step1 import AIRPORT_TIMEZONES, configure_airports_from_allowlist
from scripts.collect_step1b import GoogleFlightsClient, _at, _google_datetime, _google_flights_payload
from scripts.collect_step2 import wizz_timetable
from scripts.discover_transfer_routes import discover_candidates
from scripts.search_airports import POLISH_AIRPORTS, TENERIFE_AIRPORTS
from scripts.collection_coverage import atomic_json
from scripts.wizz_schedules import load_wizz_route_data
from scripts.ryanair_google import _google_offers
from selectolax.lexbor import LexborHTMLParser


def all_google_offers(html):
    script = next((node for node in LexborHTMLParser(html).css("script")
                   if "ds:1" in (node.attributes.get("class") or "").split()), None)
    if script is None or "data:" not in script.text():
        raise RuntimeError("Google Flights did not return technical flight data")
    payload, _ = json.JSONDecoder().raw_decode(script.text().split("data:", 1)[1].lstrip())
    return list(_google_offers(payload))


def technical_rows(html, origin, destination):
    result = []
    for offer in all_google_offers(html):
        segments = _at(_at(offer, 0, []), 2, [])
        if len(segments) != 1:
            continue
        segment = segments[0]
        flight = _at(segment, 22, [])
        if (_at(segment, 3) != origin or _at(segment, 6) != destination
                or _at(flight, 0) not in ("W6", "W4", "W9")):
            continue
        departure = _google_datetime(_at(segment, 20), _at(segment, 8), origin)
        arrival = _google_datetime(_at(segment, 21), _at(segment, 10), destination)
        duration = round((arrival - departure).total_seconds() / 60)
        prefix = _at(flight, 0)
        number = str(_at(flight, 1))
        number = number if number.startswith(prefix) else prefix + number
        if duration <= 0:
            raise RuntimeError(f"Invalid duration for {origin}-{destination}")
        result.append({"origin": origin, "destination": destination,
                       "flight_number": number, "duration_minutes": duration,
                       "departure_at": departure.isoformat(), "arrival_at": arrival.isoformat(),
                       "source": "https://www.google.com/travel/flights"})
    return result


def required_routes(snapshot, endpoint):
    candidates = discover_candidates(snapshot)
    pairs = {(endpoint, tenerife) for tenerife in TENERIFE_AIRPORTS}
    for key in ("step4", "step5_variant_a"):
        pairs.update((endpoint, row.iata) for row in candidates[key]
                     if endpoint in row.polish_airports)
    for left, right in snapshot["routes"]["wizzair"]:
        other = right if left == endpoint else left if right == endpoint else None
        if other and str(snapshot["airports"].get(other, {}).get("country_code", "")).upper() == "ES":
            pairs.add((endpoint, other))
    known, _ = load_wizz_route_data()
    for key in ("step4", "step5_variant_b"):
        for row in candidates[key]:
            if endpoint not in row.polish_airports:
                continue
            for tenerife in row.tenerife_airports:
                if (tenerife, row.iata) not in known or (row.iata, tenerife) not in known:
                    pairs.add((tenerife, row.iata))
    return sorted({pair for left, right in pairs for pair in ((left, right), (right, left))})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", choices=POLISH_AIRPORTS, default="GDN")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--from-date", type=date.fromisoformat, required=True)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--complete-times", action="store_true")
    parser.add_argument("--inactive-probe-date", action="append", type=date.fromisoformat, default=[],
                        help="Verify technical metadata of published seasonal routes; never collect future fares")
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    for config in (Path(__file__).resolve().parents[1] / "data").glob("*transfer-airports.json"):
        configure_airports_from_allowlist(json.loads(config.read_text(encoding="utf-8")))
    for code, row in snapshot["airports"].items():
        if row.get("timezone"):
            AIRPORT_TIMEZONES[code] = row["timezone"]
    routes = required_routes(snapshot, args.endpoint)
    identity = {"endpoint": args.endpoint, "period_from": args.from_date.isoformat(),
                "period_to": (args.from_date + timedelta(days=args.days)).isoformat(),
                "snapshot_date": snapshot["as_of"]}
    result = {**identity, "as_of": args.from_date.isoformat(), "source": "Google Flights HTTP direct offers; Wizz timetableV2 dates", "routes": [], "inactive_routes": [], "pending": [], "completed_routes": []}
    if args.output.exists():
        result = json.loads(args.output.read_text(encoding="utf-8"))
        if any(result.get(key) != value for key, value in identity.items()):
            raise RuntimeError("Schedule evidence belongs to another endpoint/date window")
    completed = {tuple(pair) for pair in result.get("completed_routes", [])}
    verified_pairs = {(row["origin"], row["destination"]) for row in result["routes"]}
    if args.inactive_probe_date:
        completed -= {tuple(pair) for pair in result["inactive_routes"]} - verified_pairs
    client = GoogleFlightsClient()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for origin, destination in routes:
        if (origin, destination) in completed:
            continue
        rows = wizz_timetable(origin, destination, args.from_date, args.from_date + timedelta(days=args.days), "regular")
        dates = sorted({row["departureDate"][:10] for row in rows})
        if not dates:
            if [origin, destination] not in result["inactive_routes"]:
                result["inactive_routes"].append([origin, destination])
            print(origin, destination, "no active flights", flush=True)
            published = {tuple(pair) for pair in snapshot["routes"]["wizzair"]}
            if (origin, destination) in published or (destination, origin) in published:
                for probe in args.inactive_probe_date:
                    technical = technical_rows(client.availability(origin, destination, probe), origin, destination)
                    result["routes"].extend(row for row in technical if row not in result["routes"])
                    atomic_json(args.output, result)
                    if technical:
                        print(origin, destination, "seasonal technical evidence", [(r["flight_number"], r["duration_minutes"], r["departure_at"]) for r in technical], flush=True)
                        break
        else:
            verified = [row for row in result["routes"] if (row["origin"], row["destination"]) == (origin, destination)]
            covered = {(row["departure_at"][:10], row["departure_at"][11:16]) for row in verified}
            # Sold-out days may be absent from Google. Nearby dates can still
            # verify the route/hour's technical number and block time, never a fare.
            dates = sorted(set(dates) | {(args.from_date + timedelta(days=n)).isoformat()
                                         for n in range(min(args.days + 1, 7))})
            for day in dates:
                expected = {(day, row["departureDate"][11:16]) for row in rows if row["departureDate"].startswith(day)}
                if expected and expected <= covered:
                    continue
                html = client.availability(origin, destination, date.fromisoformat(day))
                for offer in all_google_offers(html):
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
                    covered.add((departure.date().isoformat(), departure.strftime("%H:%M")))
                result["routes"] = [row for row in result["routes"] if (row["origin"], row["destination"]) != (origin, destination)] + verified
                atomic_json(args.output, result)
                time.sleep(0.6)
            if not verified:
                result["pending"].append([origin, destination])
                print(origin, destination, "PENDING technical evidence", flush=True)
            else:
                expected_clocks = {row["departureDate"][11:16] for row in rows}
                verified_clocks = {row["departure_at"][11:16] for row in verified}
                if expected_clocks - verified_clocks:
                    raise RuntimeError(f"Missing Google route/hour technical evidence: {origin}-{destination} {sorted(expected_clocks-verified_clocks)}")
                for row in verified:
                    if row not in result["routes"]:
                        result["routes"].append(row)
                print(origin, destination, [(r["flight_number"], r["duration_minutes"]) for r in verified], flush=True)
        if [origin, destination] not in result["completed_routes"]:
            result["completed_routes"].append([origin, destination])
        atomic_json(args.output, result)
        time.sleep(0.5)


if __name__ == "__main__":
    main()
