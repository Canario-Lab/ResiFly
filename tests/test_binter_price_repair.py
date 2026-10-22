import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.reprice_binter_final_prices import (
    binter_leg_key,
    repair_document,
    saved_binter_legs,
    validate_optional_coverage_sidecar,
)


def binter_leg(regular=400.0, resident=100.0):
    return {
        "carrier": "Binter",
        "flight_number": "NT6072",
        "departure_airport": "TFN",
        "departure_at": "2026-10-23T10:05:00+01:00",
        "arrival_airport": "MAD",
        "arrival_at": "2026-10-23T13:55:00+02:00",
        "price_regular_pln": regular,
        "resident_discount_eligible": True,
        "resident_fare_multiplier": 0.25,
        "price_resident_estimated_pln": resident,
        "booking_url": "https://www.bintercanarias.com/es/buscar-vuelos",
        "price_source_currency": "EUR",
        "price_source_amount": 100.0,
    }


def low_cost_leg():
    return {
        "carrier": "Ryanair",
        "flight_number": "FR1",
        "departure_airport": "WMI",
        "departure_at": "2026-10-23T05:00:00+02:00",
        "arrival_airport": "MAD",
        "arrival_at": "2026-10-23T08:00:00+02:00",
        "price_regular_pln": 200.0,
        "price_resident_estimated_pln": 200.0,
        "resident_discount_eligible": False,
        "booking_url": "https://example.com",
    }


def result(identifier):
    binter = binter_leg()
    low = low_cost_leg()
    return {
        "id": identifier,
        "origin_airport": "WMI",
        "destination_airport": "MAD",
        "direction": "poland_to_tenerife",
        "connection_type": "one_stop",
        "transfer_airport": "MAD",
        "layover_minutes": 125,
        "self_transfer": True,
        "legs": [low, binter],
        "price_total_regular_pln": 600.0,
        "price_total_resident_estimated_pln": 300.0,
    }


def document():
    reverse = result("reverse")
    reverse["direction"] = "tenerife_to_poland"
    return {
        "generated_at": "2026-10-22T22:21:03+01:00",
        "period_from": "2026-10-22",
        "period_to": "2026-11-21",
        "directions": ["tenerife_to_poland", "poland_to_tenerife"],
        "collection_coverage": {"run_id": "saved-run"},
        "sources": {"binter": "old"},
        "results": [result("one"), reverse],
    }


class BinterPriceRepairTests(unittest.TestCase):
    def test_missing_historical_sidecar_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "step1-results.json"
            source.write_text("{}", encoding="utf-8")
            self.assertFalse(validate_optional_coverage_sidecar(source, {"run_id": "x"}))

    def test_existing_sidecar_must_match_embedded_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "step1-results.json"
            source.write_text("{}", encoding="utf-8")
            sidecar = source.with_suffix(".collection-report.json")
            sidecar.write_text(json.dumps({"run_id": "different"}), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                validate_optional_coverage_sidecar(source, {"run_id": "x"})

    def test_existing_matching_sidecar_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "step1-results.json"
            source.write_text("{}", encoding="utf-8")
            coverage = {"run_id": "x"}
            source.with_suffix(".collection-report.json").write_text(
                json.dumps(coverage),
                encoding="utf-8",
            )
            self.assertTrue(validate_optional_coverage_sidecar(source, coverage))

    def test_updates_duplicate_occurrences_and_dependent_totals_only(self):
        source = document()
        original_low_cost = copy.deepcopy(source["results"][0]["legs"][0])
        live = binter_leg(1729.53, 461.35)
        live.update({
            "resident_price_is_estimate": False,
            "resident_price_source": "official final total",
            "price_source": "official GraphQL",
            "price_scope": "official_final_payable_total_with_taxes_and_fees",
            "price_source_currency": "EUR",
            "price_source_amount": 395.91,
            "price_source_resident_amount": 105.66,
        })
        repaired, counts = repair_document(
            source,
            {binter_leg_key(live): live},
            "2026-10-22T23:30:00+01:00",
        )
        self.assertEqual(counts["unique_binter_legs"], 1)
        self.assertEqual(counts["updated_binter_occurrences"], 2)
        self.assertEqual(repaired["results"][0]["legs"][0], original_low_cost)
        self.assertEqual(repaired["results"][0]["price_total_regular_pln"], 1929.53)
        self.assertEqual(repaired["results"][0]["price_total_resident_estimated_pln"], 661.35)
        self.assertEqual(source["results"][0]["price_total_regular_pln"], 600.0)

    def test_unavailable_saved_flight_removes_only_affected_connection(self):
        source = document()
        second_binter = source["results"][1]["legs"][1]
        second_binter["flight_number"] = "NT6073"
        retained_forward = result("forward-retained")
        retained_forward_binter = retained_forward["legs"][1]
        retained_forward_binter["flight_number"] = "NT6074"
        source["results"].append(retained_forward)
        original = copy.deepcopy(source)

        def final_price(leg):
            live = copy.deepcopy(leg)
            live.update({
                "resident_price_is_estimate": False,
                "resident_price_source": "official final total",
                "price_source": "official GraphQL",
                "price_scope": "official_final_payable_total_with_taxes_and_fees",
                "price_source_currency": "EUR",
                "price_source_amount": 395.91,
                "price_source_resident_amount": 105.66,
            })
            return live

        reverse_live = final_price(second_binter)
        forward_live = final_price(retained_forward_binter)
        repaired, counts = repair_document(
            source,
            {
                binter_leg_key(reverse_live): reverse_live,
                binter_leg_key(forward_live): forward_live,
            },
            "2026-10-22T23:30:00+01:00",
        )
        self.assertEqual(
            [item["id"] for item in repaired["results"]],
            ["reverse", "forward-retained"],
        )
        self.assertEqual(counts["unavailable_binter_legs_removed"], 1)
        self.assertEqual(counts["connections_removed_as_unavailable"], 1)
        self.assertEqual(source, original)

    def test_requires_exactly_one_binter_leg_per_result(self):
        source = document()
        source["results"][0]["legs"] = [low_cost_leg()]
        with self.assertRaisesRegex(RuntimeError, "exactly one"):
            saved_binter_legs(source)


if __name__ == "__main__":
    unittest.main()
