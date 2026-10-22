import unittest

from scripts.spanish_resident_fees import (
    apply_resident_price_estimate,
    load_fee_registry,
    nondiscountable_fee_eur,
    resident_price_estimate,
)


class SpanishResidentFeeTests(unittest.TestCase):
    def setUp(self):
        self.registry = load_fee_registry()

    def test_direction_specific_aena_fees(self):
        day = "2026-11-01T12:00:00+01:00"
        expected = {
            ("MAD", "TFN"): 19.57,
            ("BCN", "TFN"): 18.60,
            ("AGP", "TFS"): 11.35,
            ("ALC", "TFN"): 11.35,
            ("BIO", "TFN"): 10.48,
            ("SCQ", "TFN"): 10.48,
            ("SVQ", "TFS"): 10.48,
            ("VLC", "TFN"): 10.48,
            ("TFN", "MAD"): 8.91,
            ("TFS", "BIO"): 9.65,
        }
        for route, amount in expected.items():
            with self.subTest(route=route):
                self.assertEqual(
                    nondiscountable_fee_eur(*route, day, self.registry),
                    amount,
                )

    def test_official_air_europa_example_discounts_only_fare_component(self):
        resident, fees = resident_price_estimate(150.57, 0.25, 19.57, 1.0)
        self.assertEqual(fees, 19.57)
        self.assertEqual(resident, 52.32)

    def test_missing_route_or_expired_table_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "Brak opłaty"):
            nondiscountable_fee_eur(
                "LHR", "TFS", "2026-11-01T12:00:00+00:00", self.registry
            )
        with self.assertRaisesRegex(RuntimeError, "aktualizacja wymagana"):
            nondiscountable_fee_eur(
                "MAD", "TFN", "2027-01-01T12:00:00+01:00", self.registry
            )

    def test_explicit_fee_cannot_override_registry(self):
        leg = {
            "departure_airport": "MAD",
            "arrival_airport": "TFN",
            "departure_at": "2026-11-01T12:00:00+01:00",
            "price_regular_pln": 659.0,
            "resident_discount_eligible": True,
            "resident_fare_multiplier": 0.25,
        }
        with self.assertRaisesRegex(RuntimeError, "wspólną tabelą Aena"):
            apply_resident_price_estimate(
                leg, 4.3685, self.registry, fee_eur=19.00
            )


if __name__ == "__main__":
    unittest.main()
