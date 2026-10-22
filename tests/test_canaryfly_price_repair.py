import copy
import unittest

from scripts.reprice_canaryfly_final_prices import (
    canaryfly_leg_key,
    repair_document,
    saved_canaryfly_legs,
)


def canaryfly_leg(number="PM374", regular=532.96, resident=133.24):
    return {
        "carrier": "Canaryfly",
        "flight_number": number,
        "departure_airport": "TFN",
        "departure_at": "2026-10-24T14:30:00+01:00",
        "arrival_airport": "FUE",
        "arrival_at": "2026-10-24T15:20:00+01:00",
        "price_regular_pln": regular,
        "resident_discount_eligible": True,
        "resident_fare_multiplier": 0.25,
        "price_resident_estimated_pln": resident,
        "resident_price_is_estimate": False,
        "booking_url": "https://www.canaryfly.es/example",
        "price_source": "Canaryfly official booking_search GraphQL",
        "price_source_currency": "EUR",
        "price_source_amount": 122.0,
        "price_source_resident_amount": 30.5,
    }


def low_cost_leg():
    return {
        "carrier": "Wizz Air",
        "flight_number": "W60000",
        "departure_airport": "FUE",
        "departure_at": "2026-10-24T18:00:00+01:00",
        "arrival_airport": "WAW",
        "arrival_at": "2026-10-24T23:30:00+02:00",
        "price_regular_pln": 300.0,
        "price_resident_estimated_pln": 300.0,
        "resident_discount_eligible": False,
        "booking_url": "https://example.com",
    }


def result(identifier, number="PM374"):
    canaryfly = canaryfly_leg(number)
    low = low_cost_leg()
    return {
        "id": identifier,
        "origin_airport": "TFN",
        "destination_airport": "WAW",
        "direction": "tenerife_to_poland",
        "connection_type": "one_stop",
        "transfer_airport": "FUE",
        "layover_minutes": 160,
        "self_transfer": True,
        "legs": [canaryfly, low],
        "price_total_regular_pln": 832.96,
        "price_total_resident_estimated_pln": 433.24,
    }


def document():
    return {
        "generated_at": "2026-10-22T22:29:10+01:00",
        "period_from": "2026-10-22",
        "period_to": "2026-11-21",
        "collection_coverage": {"run_id": "saved-run"},
        "sources": {"canaryfly": "old"},
        "results": [result("one"), result("two")],
    }


def final_leg(number="PM374"):
    leg = canaryfly_leg(number, 570.22, 150.84)
    leg.update({
        "resident_price_is_estimate": False,
        "resident_price_source": "Canaryfly official booking_getImports final total",
        "price_source": (
            "Canaryfly official booking_search + booking_getImports GraphQL"
        ),
        "price_scope": "official_final_payable_total_with_taxes_and_fees",
        "price_source_currency": "EUR",
        "price_source_amount": 130.53,
        "price_source_resident_amount": 34.53,
    })
    return leg


class CanaryflyPriceRepairTests(unittest.TestCase):
    def test_updates_duplicate_occurrences_and_dependent_totals_only(self):
        source = document()
        original_low_cost = copy.deepcopy(source["results"][0]["legs"][1])
        live = final_leg()
        repaired, counts = repair_document(
            source,
            {canaryfly_leg_key(live): live},
            "2026-10-23T01:00:00+01:00",
        )
        self.assertEqual(counts["unique_canaryfly_legs"], 1)
        self.assertEqual(counts["updated_canaryfly_occurrences"], 2)
        self.assertEqual(repaired["results"][0]["legs"][1], original_low_cost)
        self.assertEqual(repaired["results"][0]["price_total_regular_pln"], 870.22)
        self.assertEqual(
            repaired["results"][0]["price_total_resident_estimated_pln"],
            450.84,
        )
        self.assertEqual(source["results"][0]["price_total_regular_pln"], 832.96)

    def test_unavailable_saved_flight_removes_only_affected_connections(self):
        source = document()
        source["results"][1] = result("two", "PM376")
        original = copy.deepcopy(source)
        live = final_leg("PM376")
        repaired, counts = repair_document(
            source,
            {canaryfly_leg_key(live): live},
            "2026-10-23T01:00:00+01:00",
        )
        self.assertEqual([item["id"] for item in repaired["results"]], ["two"])
        self.assertEqual(counts["unavailable_canaryfly_legs_removed"], 1)
        self.assertEqual(counts["connections_removed_as_unavailable"], 1)
        self.assertEqual(source, original)

    def test_requires_exactly_one_canaryfly_leg_per_result(self):
        source = document()
        source["results"][0]["legs"] = [low_cost_leg()]
        with self.assertRaisesRegex(RuntimeError, "exactly one"):
            saved_canaryfly_legs(source)


if __name__ == "__main__":
    unittest.main()
