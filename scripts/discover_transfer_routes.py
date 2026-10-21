#!/usr/bin/env python3
"""Discover new transfer-route combinations for ResiFly's fixed allowlists.

The weekly price collectors deliberately do not rediscover their route network.
This script is the separate, less frequent network detector.  Its default mode
is read-only: it prints a proposed update.  ``--apply`` writes complete additions
to the allowlist JSON files atomically.  Existing airports and route combinations
are never removed automatically because an airline can temporarily hide a
seasonal route.

Wizz Air's public route map does not expose flight numbers or arrival times.
Consequently a newly discovered Wizz route is only activated when both directed
technical schedules already exist in ResiFly's schedule registry.  Otherwise it
is reported as pending and that incomplete candidate is not activated.  This
prevents the collectors from publishing invented or incomplete flight data.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

STEP1_FILE = DATA / "binter-transfer-airports.json"
STEP3_FILE = DATA / "ryanair-transfer-airports.json"
STEP4_FILE = DATA / "wizzair-transfer-airports.json"
STEP5_FILE = DATA / "mixed-transfer-airports.json"
WIZZ_SCHEDULE_FILE = DATA / "wizz-route-schedules.json"

POLISH_AIRPORTS = ("WAW", "WMI", "KTW", "KRK")
TENERIFE_AIRPORTS = ("TFN", "TFS")
ENDPOINTS = set(POLISH_AIRPORTS + TENERIFE_AIRPORTS)

RYANAIR_ROUTES_URL = "https://www.ryanair.com/api/views/locate/3/routes"
RYANAIR_AIRPORTS_URL = "https://www.ryanair.com/api/views/locate/3/airports/en/active"
WIZZ_HOMEPAGE_URL = "https://www.wizzair.com/en-gb"
WIZZ_API_FALLBACK = "https://be.wizzair.com/29.21.0/Api"
BINTER_API_URL = "https://services.bintercanarias.com/main/graphql"

COUNTRY_NAMES_PL = {
    "AE": "Zjednoczone Emiraty Arabskie",
    "AL": "Albania",
    "AM": "Armenia",
    "AT": "Austria",
    "AZ": "Azerbejdżan",
    "BA": "Bośnia i Hercegowina",
    "BE": "Belgia",
    "BG": "Bułgaria",
    "CH": "Szwajcaria",
    "CY": "Cypr",
    "CZ": "Czechy",
    "DE": "Niemcy",
    "DK": "Dania",
    "EE": "Estonia",
    "EG": "Egipt",
    "ES": "Hiszpania",
    "FI": "Finlandia",
    "FR": "Francja",
    "GB": "Wielka Brytania",
    "GE": "Gruzja",
    "GR": "Grecja",
    "HR": "Chorwacja",
    "HU": "Węgry",
    "IE": "Irlandia",
    "IL": "Izrael",
    "IS": "Islandia",
    "IT": "Włochy",
    "JO": "Jordania",
    "LT": "Litwa",
    "LU": "Luksemburg",
    "LV": "Łotwa",
    "MA": "Maroko",
    "MD": "Mołdawia",
    "ME": "Czarnogóra",
    "MK": "Macedonia Północna",
    "MT": "Malta",
    "NL": "Holandia",
    "NO": "Norwegia",
    "PL": "Polska",
    "PT": "Portugalia",
    "RO": "Rumunia",
    "RS": "Serbia",
    "SA": "Arabia Saudyjska",
    "SE": "Szwecja",
    "SI": "Słowenia",
    "SK": "Słowacja",
    "TN": "Tunezja",
    "TR": "Turcja",
    "UA": "Ukraina",
    "XK": "Kosowo",
}


@dataclass(frozen=True)
class Airport:
    iata: str
    name: str
    country_code: str
    country_name: str
    timezone: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass(frozen=True)
class Candidate:
    iata: str
    tenerife_airports: tuple[str, ...]
    polish_airports: tuple[str, ...]
    polish_evidence: tuple[tuple[str, str], ...] = ()


def cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Detect new Step 1/3/4/5 transfer combinations. The default is a "
            "read-only dry run; use --apply to update allowlists."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Update complete candidates; incomplete Wizz candidates stay pending.",
    )
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=date.today(),
        help="Network snapshot date in YYYY-MM-DD form (default: today).",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="Use an offline detector snapshot instead of contacting airlines.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optionally save the JSON report (useful as a GitHub Actions artifact).",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def edge_exists(routes: set[tuple[str, str]], left: str, right: str) -> bool:
    """Treat a published direct route as usable even if one direction is absent."""
    return (left, right) in routes or (right, left) in routes


def direct_neighbors(routes: set[tuple[str, str]], airport: str) -> set[str]:
    neighbors: set[str] = set()
    for origin, destination in routes:
        if origin == airport:
            neighbors.add(destination)
        if destination == airport:
            neighbors.add(origin)
    return neighbors


def candidate_intersection(
    tenerife_routes: set[tuple[str, str]],
    poland_routes: set[tuple[str, str]],
) -> list[Candidate]:
    """Return transfer airports joining a Tenerife graph to a Poland graph."""
    tenerife_by_transfer: dict[str, set[str]] = {}
    for tenerife in TENERIFE_AIRPORTS:
        for transfer in direct_neighbors(tenerife_routes, tenerife) - ENDPOINTS:
            tenerife_by_transfer.setdefault(transfer, set()).add(tenerife)

    poland_by_transfer: dict[str, set[str]] = {}
    for polish in POLISH_AIRPORTS:
        for transfer in direct_neighbors(poland_routes, polish) - ENDPOINTS:
            poland_by_transfer.setdefault(transfer, set()).add(polish)

    return [
        Candidate(
            iata=transfer,
            tenerife_airports=tuple(sorted(tenerife_by_transfer[transfer])),
            polish_airports=tuple(sorted(poland_by_transfer[transfer])),
        )
        for transfer in sorted(set(tenerife_by_transfer) & set(poland_by_transfer))
    ]


def discover_candidates(snapshot: Mapping[str, Any]) -> dict[str, list[Candidate]]:
    route_data = snapshot["routes"]
    ryanair = {tuple(item) for item in route_data["ryanair"]}
    wizzair = {tuple(item) for item in route_data["wizzair"]}
    binter = {tuple(item) for item in route_data["binter"]}

    low_cost = ryanair | wizzair
    step1_base = candidate_intersection(binter, low_cost)
    step1: list[Candidate] = []
    for candidate in step1_base:
        evidence = []
        for polish in candidate.polish_airports:
            if edge_exists(ryanair, candidate.iata, polish):
                evidence.append((polish, "Ryanair"))
            if edge_exists(wizzair, candidate.iata, polish):
                evidence.append((polish, "Wizz Air"))
        step1.append(
            Candidate(
                iata=candidate.iata,
                tenerife_airports=candidate.tenerife_airports,
                polish_airports=candidate.polish_airports,
                polish_evidence=tuple(sorted(evidence)),
            )
        )

    return {
        "step1": step1,
        "step3": candidate_intersection(ryanair, ryanair),
        "step4": candidate_intersection(wizzair, wizzair),
        "step5_variant_a": candidate_intersection(ryanair, wizzair),
        "step5_variant_b": candidate_intersection(wizzair, ryanair),
    }


def airport_from_snapshot(snapshot: Mapping[str, Any], iata: str) -> Airport:
    try:
        raw = snapshot["airports"][iata]
    except KeyError as error:
        raise ValueError(f"Brak metadanych lotniska {iata}") from error
    timezone = str(raw.get("timezone") or "").strip()
    if not timezone:
        raise ValueError(f"Brak strefy czasowej lotniska {iata}")
    return Airport(
        iata=iata,
        name=str(raw.get("name") or iata),
        country_code=str(raw.get("country_code") or "").upper(),
        country_name=str(raw.get("country_name") or ""),
        timezone=timezone,
        latitude=raw.get("latitude"),
        longitude=raw.get("longitude"),
    )


def schedule_keys(step1: Mapping[str, Any], shared: Mapping[str, Any]) -> set[tuple[str, str]]:
    rows = list(step1.get("wizz_route_schedules", [])) + list(shared.get("routes", []))
    return {(str(row["origin"]), str(row["destination"])) for row in rows}


def schedule_rows(
    step1: Mapping[str, Any], shared: Mapping[str, Any]
) -> dict[tuple[str, str], dict[str, Any]]:
    rows = list(shared.get("routes", [])) + list(step1.get("wizz_route_schedules", []))
    return {
        (str(row["origin"]), str(row["destination"])): copy.deepcopy(row)
        for row in rows
    }


def wizz_pairs_for_candidate(
    candidate: Candidate,
    variant: str,
) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    if variant in {"step4", "step5_variant_b"}:
        for tenerife in candidate.tenerife_airports:
            pairs.add((tenerife, candidate.iata))
    if variant in {"step4", "step5_variant_a"}:
        for polish in candidate.polish_airports:
            pairs.add((polish, candidate.iata))
    if variant == "step1":
        for polish, airline in candidate.polish_evidence:
            if airline == "Wizz Air":
                pairs.add((polish, candidate.iata))
    return pairs


def missing_wizz_schedules(
    candidate: Candidate,
    variant: str,
    known: set[tuple[str, str]],
) -> list[str]:
    missing: list[str] = []
    for left, right in sorted(wizz_pairs_for_candidate(candidate, variant)):
        for origin, destination in ((left, right), (right, left)):
            if (origin, destination) not in known:
                missing.append(f"{origin}-{destination}")
    return missing


def candidate_delta(
    candidate: Candidate,
    document: Mapping[str, Any],
    variant: Optional[str] = None,
) -> bool:
    if variant is None:
        rows = document.get("airports", [])
    else:
        rows = document["variants"][variant]["airports"]
    current = next((item for item in rows if item["iata"] == candidate.iata), None)
    if current is None:
        return True
    if "tenerife_airports" in current and set(candidate.tenerife_airports) - set(current["tenerife_airports"]):
        return True
    if "polish_airports" in current and set(candidate.polish_airports) - set(current["polish_airports"]):
        return True
    if "eligibility_evidence" in current:
        current_evidence = {
            (item["polish_airport"], item["airline"])
            for item in current["eligibility_evidence"]
        }
        if set(candidate.polish_evidence) - current_evidence:
            return True
    return False


def build_plan(
    snapshot: Mapping[str, Any],
    documents: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    candidates = discover_candidates(snapshot)
    known_schedules = schedule_keys(documents["step1"], documents["wizz_schedules"])
    configs = (
        ("step1", "step1", None),
        ("step3", "step3", None),
        ("step4", "step4", None),
        (
            "step5_variant_a",
            "step5",
            "ryanair_tenerife_wizzair_poland",
        ),
        (
            "step5_variant_b",
            "step5",
            "wizzair_tenerife_ryanair_poland",
        ),
    )
    report: dict[str, Any] = {
        "schema_version": 1,
        "as_of": snapshot["as_of"],
        "mode": "route-network-discovery",
        "safety": {
            "removes_existing_routes": False,
            "requires_complete_wizz_schedules": True,
        },
        "steps": {},
    }
    report["steps"]["step2"] = {
        "ready": [],
        "pending": [],
        "discovered_total": 0,
        "note": (
            "Krok 2 nie ma listy lotnisk przesiadkowych. Kolektor zawsze sprawdza "
            "pełną, stałą macierz WAW/WMI/KTW/KRK ↔ TFN/TFS."
        ),
    }

    for plan_key, document_key, variant_key in configs:
        ready: list[dict[str, Any]] = []
        pending: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        document = documents[document_key]
        excluded_step1 = {
            item["iata"] for item in documents["step1"].get("excluded_airports", [])
        }
        for candidate in candidates[plan_key]:
            if plan_key == "step1" and candidate.iata in excluded_step1:
                excluded.append(
                    {
                        "iata": candidate.iata,
                        "reason": "Lotnisko znajduje się na jawnej liście excluded_airports kroku 1.",
                    }
                )
                continue
            if not candidate_delta(candidate, document, variant_key):
                continue
            reasons: list[str] = []
            try:
                airport_from_snapshot(snapshot, candidate.iata)
            except ValueError as error:
                reasons.append(str(error))
            if plan_key != "step3":
                missing = missing_wizz_schedules(candidate, plan_key, known_schedules)
                if missing:
                    reasons.append(
                        "Brak zweryfikowanych rozkładów Wizz: " + ", ".join(missing)
                    )
            serialized = {
                "iata": candidate.iata,
                "tenerife_airports": list(candidate.tenerife_airports),
                "polish_airports": list(candidate.polish_airports),
            }
            if candidate.polish_evidence:
                serialized["polish_evidence"] = [
                    {"polish_airport": polish, "airline": airline}
                    for polish, airline in candidate.polish_evidence
                ]
            if reasons:
                serialized["reasons"] = reasons
                pending.append(serialized)
            else:
                ready.append(serialized)
        report["steps"][plan_key] = {
            "ready": ready,
            "pending": pending,
            "excluded": excluded,
            "discovered_total": len(candidates[plan_key]),
        }
    return report


def country_name_pl(airport: Airport) -> str:
    return COUNTRY_NAMES_PL.get(airport.country_code, airport.country_name or airport.country_code)


def airport_record(airport: Airport, candidate: Candidate, step: str) -> dict[str, Any]:
    record: dict[str, Any] = {
        "iata": airport.iata,
        "name_pl": airport.name,
    }
    if step != "step1":
        eligible = airport.country_code == "ES"
        record["country_pl"] = country_name_pl(airport)
        record["tenerife_airports"] = list(candidate.tenerife_airports)
        record["polish_airports"] = list(candidate.polish_airports)
        record["resident_discount_eligible_on_tenerife_leg"] = eligible
        record["tenerife_leg_fare_multiplier"] = 0.25 if eligible else 1.0
    if step == "step1":
        eligible = airport.country_code == "ES"
        record.update(
            {
                "timezone": airport.timezone,
                "binter_from_tenerife": True,
                "resident_discount_eligible_on_binter_leg": eligible,
                "binter_resident_fare_multiplier": 0.25 if eligible else 1.0,
                "eligibility_evidence": [
                    {"polish_airport": polish, "airline": airline}
                    for polish, airline in candidate.polish_evidence
                ],
            }
        )
    if step.startswith("step5"):
        eligible = airport.country_code == "ES"
        record["resident_discount_eligible_on_tenerife_leg"] = eligible
        record["tenerife_leg_fare_multiplier"] = 0.25 if eligible else 1.0
    return record


def merge_candidate(
    document: dict[str, Any],
    candidate: Candidate,
    airport: Airport,
    step: str,
    variant: Optional[str] = None,
) -> bool:
    rows = document["airports"] if variant is None else document["variants"][variant]["airports"]
    current = next((item for item in rows if item["iata"] == candidate.iata), None)
    changed = False
    if current is None:
        rows.append(airport_record(airport, candidate, step))
        changed = True
    else:
        for key, values in (
            ("tenerife_airports", candidate.tenerife_airports),
            ("polish_airports", candidate.polish_airports),
        ):
            if key in current:
                merged = sorted(set(current[key]) | set(values))
                if merged != current[key]:
                    current[key] = merged
                    changed = True
        if step == "step1":
            old = {
                (item["polish_airport"], item["airline"])
                for item in current.get("eligibility_evidence", [])
            }
            merged_evidence = sorted(old | set(candidate.polish_evidence))
            replacement = [
                {"polish_airport": polish, "airline": airline}
                for polish, airline in merged_evidence
            ]
            if replacement != current.get("eligibility_evidence", []):
                current["eligibility_evidence"] = replacement
                changed = True
    rows.sort(key=lambda item: item["iata"])
    return changed


def refresh_discount_lists(document: dict[str, Any], variant: Optional[str] = None) -> None:
    discount = document.get("resident_discount_on_tenerife_leg")
    if discount is None:
        return
    rows = document["airports"] if variant is None else document["variants"][variant]["airports"]
    eligible = sorted(
        item["iata"]
        for item in rows
        if item.get("resident_discount_eligible_on_tenerife_leg")
        or item.get("iata") in discount.get("eligible_transfer_airports", [])
    )
    all_codes = {item["iata"] for item in rows}
    ineligible = sorted(all_codes - set(eligible))
    target = discount if variant is None else discount[variant]
    target["eligible_transfer_airports"] = eligible
    target["ineligible_transfer_airports"] = ineligible
    if variant is None:
        if "eligible_count" in target:
            target["eligible_count"] = len(eligible)
        if "ineligible_count" in target:
            target["ineligible_count"] = len(ineligible)


def apply_plan(
    snapshot: Mapping[str, Any],
    documents: Mapping[str, Mapping[str, Any]],
    report: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    updated = {key: copy.deepcopy(value) for key, value in documents.items()}
    candidate_lookup = {
        key: {candidate.iata: candidate for candidate in values}
        for key, values in discover_candidates(snapshot).items()
    }
    configs = (
        ("step1", "step1", None),
        ("step3", "step3", None),
        ("step4", "step4", None),
        ("step5_variant_a", "step5", "ryanair_tenerife_wizzair_poland"),
        ("step5_variant_b", "step5", "wizzair_tenerife_ryanair_poland"),
    )
    changed_documents: set[str] = set()
    known_schedule_rows = schedule_rows(documents["step1"], documents["wizz_schedules"])
    for plan_key, document_key, variant_key in configs:
        for item in report["steps"][plan_key]["ready"]:
            candidate = candidate_lookup[plan_key][item["iata"]]
            airport = airport_from_snapshot(snapshot, candidate.iata)
            if merge_candidate(
                updated[document_key], candidate, airport, plan_key, variant_key
            ):
                changed_documents.add(document_key)
                if document_key != "step1":
                    updated[document_key]["airport_timezones"][airport.iata] = airport.timezone
            if plan_key == "step1":
                current_keys = {
                    (row["origin"], row["destination"])
                    for row in updated["step1"].get("wizz_route_schedules", [])
                }
                for left, right in sorted(wizz_pairs_for_candidate(candidate, "step1")):
                    for route_key in ((left, right), (right, left)):
                        if route_key not in current_keys:
                            updated["step1"].setdefault("wizz_route_schedules", []).append(
                                copy.deepcopy(known_schedule_rows[route_key])
                            )
                            current_keys.add(route_key)
                            changed_documents.add("step1")
                updated["step1"].get("wizz_route_schedules", []).sort(
                    key=lambda row: (row["origin"], row["destination"])
                )

    if "step3" in changed_documents:
        refresh_discount_lists(updated["step3"])
        updated["step3"]["selection_method"]["result_count"] = len(updated["step3"]["airports"])
    if "step4" in changed_documents:
        refresh_discount_lists(updated["step4"])
        updated["step4"]["selection_method"]["result_count"] = len(updated["step4"]["airports"])
    if "step5" in changed_documents:
        for variant_key, discount_key in (
            ("ryanair_tenerife_wizzair_poland", "variant_a"),
            ("wizzair_tenerife_ryanair_poland", "variant_b"),
        ):
            rows = updated["step5"]["variants"][variant_key]["airports"]
            eligible = sorted(
                item["iata"]
                for item in rows
                if item.get("resident_discount_eligible_on_tenerife_leg")
            )
            all_codes = {item["iata"] for item in rows}
            target = updated["step5"]["resident_discount_on_tenerife_leg"][discount_key]
            target["eligible_transfer_airports"] = eligible
            target["ineligible_transfer_airports"] = sorted(all_codes - set(eligible))
        variants = updated["step5"]["variants"]
        updated["step5"]["selection_method"]["variant_a_result_count"] = len(
            variants["ryanair_tenerife_wizzair_poland"]["airports"]
        )
        updated["step5"]["selection_method"]["variant_b_result_count"] = len(
            variants["wizzair_tenerife_ryanair_poland"]["airports"]
        )
        updated["step5"]["selection_method"]["unique_transfer_airport_count"] = len(
            {
                item["iata"]
                for variant in variants.values()
                for item in variant["airports"]
            }
        )

    for document_key in changed_documents:
        updated[document_key]["verified_on"] = snapshot["as_of"]
    return {key: updated[key] for key in changed_documents}


def atomic_write_json(path: Path, document: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(document, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _http_client():
    try:
        from curl_cffi import requests
    except ImportError as error:
        raise RuntimeError(
            "Brak zależności curl_cffi. Uruchom: pip install -r "
            "scripts/requirements-flight-collector.txt"
        ) from error
    return requests.Session(impersonate="safari184")


def _response_json(response, label: str) -> Any:
    if response.status_code >= 400:
        raise RuntimeError(f"{label}: HTTP {response.status_code}: {response.text[:300]}")
    try:
        return response.json()
    except ValueError as error:
        raise RuntimeError(f"{label}: odpowiedź nie jest JSON-em") from error


def fetch_ryanair(session) -> tuple[set[tuple[str, str]], dict[str, dict[str, Any]]]:
    route_rows = _response_json(session.get(RYANAIR_ROUTES_URL, timeout=45), "Ryanair routes")
    airport_rows = _response_json(session.get(RYANAIR_AIRPORTS_URL, timeout=45), "Ryanair airports")
    routes = {
        (row["airportFrom"], row["airportTo"])
        for row in route_rows
        if row.get("operator") == "RYANAIR" and not row.get("connectingAirport")
    }
    airports = {
        row["iataCode"]: {
            "name": row.get("name") or row["iataCode"],
            "country_code": row.get("countryCode") or "",
            "country_name": COUNTRY_NAMES_PL.get(row.get("countryCode", ""), ""),
            "timezone": row.get("timeZone") or "",
            "latitude": row.get("latitude")
            or (row.get("coordinates") or {}).get("latitude"),
            "longitude": row.get("longitude")
            or (row.get("coordinates") or {}).get("longitude"),
        }
        for row in airport_rows
    }
    return routes, airports


def wizz_api_base(session) -> str:
    response = session.get(WIZZ_HOMEPAGE_URL, timeout=45)
    if response.status_code < 400:
        match = re.search(r"be\.wizzair\.com/(\d+\.\d+\.\d+)/Api", response.text)
        if match:
            return f"https://be.wizzair.com/{match.group(1)}/Api"
        script_match = re.search(r'src="(/dist/[^"]+\.js)', response.text)
        if script_match:
            script = session.get(
                "https://www.wizzair.com" + script_match.group(1), timeout=45
            )
            if script.status_code < 400:
                match = re.search(
                    r"be\.wizzair\.com/(\d+\.\d+\.\d+)/Api", script.text
                )
                if match:
                    return f"https://be.wizzair.com/{match.group(1)}/Api"
    return WIZZ_API_FALLBACK


def fetch_wizz(session) -> tuple[set[tuple[str, str]], dict[str, dict[str, Any]]]:
    base = wizz_api_base(session)
    payload = _response_json(
        session.get(f"{base}/asset/map", params={"languageCode": "en-gb"}, timeout=45),
        "Wizz Air route map",
    )
    real = {row["iata"]: row for row in payload.get("cities", []) if not row.get("isFakeStation")}
    routes: set[tuple[str, str]] = set()
    for origin, row in real.items():
        for connection in row.get("connections", []):
            destination = connection.get("iata")
            if connection.get("isDirectFlight") and destination in real:
                routes.add((origin, destination))
    airports = {
        iata: {
            "name": row.get("shortName") or iata,
            "country_code": row.get("countryCode") or "",
            "country_name": row.get("countryName") or "",
            "timezone": "",
            "latitude": row.get("latitude"),
            "longitude": row.get("longitude"),
        }
        for iata, row in real.items()
    }
    return routes, airports


def _binter_headers() -> dict[str, str]:
    return {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "origin": "https://www.bintercanarias.com",
        "referer": "https://www.bintercanarias.com/",
        "x-environment": "desktop",
        "x-lang": "es",
        "authorization": "",
        "x-client-ip": "",
        "x-content-hash": "",
    }


def fetch_binter(
    session,
    as_of: date,
    low_cost_candidates: Iterable[str],
) -> set[tuple[str, str]]:
    query = """
    query timetable_get($trips: [TripInput!]!) {
      timetable_get(trips: $trips) {
        trip { origin { iata } destination { iata } date }
        flights {
          flightSegments {
            line
            flightNumber
            origin { iata }
            destination { iata }
            departureTime
            arrivalTime
          }
        }
      }
    }
    """
    trips = []
    for transfer in sorted(set(low_cost_candidates) - ENDPOINTS):
        for tenerife in TENERIFE_AIRPORTS:
            trips.extend(
                (
                    {"origin": tenerife, "destination": transfer, "date": as_of.isoformat()},
                    {"origin": transfer, "destination": tenerife, "date": as_of.isoformat()},
                )
            )
    if not trips:
        return set()
    routes: set[tuple[str, str]] = set()
    for offset in range(0, len(trips), 40):
        payload = {"query": query, "variables": {"trips": trips[offset : offset + 40]}}
        response = _response_json(
            session.post(BINTER_API_URL, headers=_binter_headers(), json=payload, timeout=90),
            "Binter timetable",
        )
        if response.get("errors"):
            raise RuntimeError(f"Binter timetable: {response['errors']}")
        for result in response.get("data", {}).get("timetable_get", []):
            trip = result.get("trip") or {}
            origin = (trip.get("origin") or {}).get("iata")
            destination = (trip.get("destination") or {}).get("iata")
            if not origin or not destination:
                continue
            for flight in result.get("flights") or []:
                segments = flight.get("flightSegments") or []
                if len(segments) != 1:
                    continue
                segment = segments[0]
                if (
                    (segment.get("origin") or {}).get("iata") == origin
                    and (segment.get("destination") or {}).get("iata") == destination
                ):
                    routes.add((origin, destination))
                    break
    return routes


def existing_metadata(documents: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for document_key in ("step3", "step4"):
        document = documents[document_key]
        for row in document["airports"]:
            result[row["iata"]] = {
                "name": row.get("name_pl") or row["iata"],
                "country_name": row.get("country_pl") or "",
                "country_code": "ES"
                if row["iata"] in document["resident_discount_on_tenerife_leg"]["eligible_transfer_airports"]
                else "",
                "timezone": document["airport_timezones"].get(row["iata"], ""),
            }
    for row in documents["step1"]["airports"]:
        result[row["iata"]] = {
            "name": row.get("name_pl") or row["iata"],
            "country_name": "Hiszpania" if row.get("resident_discount_eligible_on_binter_leg") else "",
            "country_code": "ES" if row.get("resident_discount_eligible_on_binter_leg") else "",
            "timezone": row.get("timezone") or "",
        }
    for variant in documents["step5"]["variants"].values():
        for row in variant["airports"]:
            existing = result.setdefault(row["iata"], {})
            existing.setdefault("name", row.get("name_pl") or row["iata"])
            existing.setdefault("country_name", row.get("country_pl") or "")
            existing.setdefault("country_code", "ES" if row.get("resident_discount_eligible_on_tenerife_leg") else "")
            existing.setdefault("timezone", documents["step5"]["airport_timezones"].get(row["iata"], ""))
    return result


def fill_timezones(
    airports: dict[str, dict[str, Any]],
    relevant_codes: Iterable[str],
) -> None:
    relevant = set(relevant_codes)
    unresolved = [
        row
        for iata, row in airports.items()
        if iata in relevant
        and not row.get("timezone")
        and row.get("latitude") is not None
        and row.get("longitude") is not None
    ]
    if not unresolved:
        return
    try:
        from timezonefinder import TimezoneFinder
    except ImportError as error:
        raise RuntimeError(
            "Brak zależności timezonefinder potrzebnej do stref czasowych nowych "
            "lotnisk Wizz Air. Zainstaluj requirements-flight-collector.txt."
        ) from error
    finder = TimezoneFinder()
    for row in unresolved:
        row["timezone"] = finder.timezone_at(
            lat=float(row["latitude"]), lng=float(row["longitude"])
        ) or ""


def fetch_live_snapshot(
    as_of: date,
    documents: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    session = _http_client()
    try:
        ryanair_routes, ryanair_airports = fetch_ryanair(session)
        wizz_routes, wizz_airports = fetch_wizz(session)
        low_cost_candidates: set[str] = set()
        for polish in POLISH_AIRPORTS:
            low_cost_candidates |= direct_neighbors(ryanair_routes | wizz_routes, polish)
        binter_routes = fetch_binter(session, as_of, low_cost_candidates)
    finally:
        session.close()

    airports = existing_metadata(documents)
    for source in (wizz_airports, ryanair_airports):
        for iata, row in source.items():
            current = airports.setdefault(iata, {})
            for key, value in row.items():
                if value not in (None, ""):
                    current[key] = value
    snapshot = {
        "schema_version": 1,
        "as_of": as_of.isoformat(),
        "airports": airports,
        "routes": {
            "ryanair": [list(item) for item in sorted(ryanair_routes)],
            "wizzair": [list(item) for item in sorted(wizz_routes)],
            "binter": [list(item) for item in sorted(binter_routes)],
        },
        "sources": {
            "ryanair_routes": RYANAIR_ROUTES_URL,
            "ryanair_airports": RYANAIR_AIRPORTS_URL,
            "wizz_route_map": WIZZ_HOMEPAGE_URL,
            "binter_timetable": BINTER_API_URL,
        },
    }
    discovered = discover_candidates(snapshot)
    relevant_codes = {
        candidate.iata
        for candidates in discovered.values()
        for candidate in candidates
    }
    fill_timezones(airports, relevant_codes)
    return snapshot


def load_documents() -> dict[str, dict[str, Any]]:
    return {
        "step1": read_json(STEP1_FILE),
        "step3": read_json(STEP3_FILE),
        "step4": read_json(STEP4_FILE),
        "step5": read_json(STEP5_FILE),
        "wizz_schedules": read_json(WIZZ_SCHEDULE_FILE),
    }


def main() -> int:
    args = cli()
    documents = load_documents()
    if args.snapshot:
        snapshot = read_json(args.snapshot)
    else:
        snapshot = fetch_live_snapshot(args.as_of, documents)
    report = build_plan(snapshot, documents)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    sys.stdout.write(rendered)
    if args.report:
        atomic_write_json(args.report, report)
    if not args.apply:
        return 0

    changed = apply_plan(snapshot, documents, report)
    paths = {
        "step1": STEP1_FILE,
        "step3": STEP3_FILE,
        "step4": STEP4_FILE,
        "step5": STEP5_FILE,
    }
    for key, document in changed.items():
        atomic_write_json(paths[key], document)
    print(
        "Zaktualizowano: "
        + (", ".join(str(paths[key].relative_to(ROOT)) for key in sorted(changed)) or "brak zmian")
    )
    pending_count = sum(
        len(step.get("pending", [])) for step in report["steps"].values()
    )
    if pending_count:
        print(
            f"Pominięto {pending_count} niekompletnych kandydatów; szczegóły są w raporcie.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
