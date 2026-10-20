import unittest

from scripts.collect_step1 import build_connections, validate_document


def leg(carrier, number, origin, departure, destination, arrival, regular, resident=None, booking_url=None):
    item = {
        "carrier": carrier,
        "flight_number": number,
        "departure_airport": origin,
        "departure_at": departure,
        "arrival_airport": destination,
        "arrival_at": arrival,
        "price_regular_pln": regular,
        "resident_discount_eligible": carrier == "Binter",
        "price_resident_estimated_pln": resident if resident is not None else regular,
    }
    if booking_url:
        item["booking_url"] = booking_url
    return item


class Step1CollectorTests(unittest.TestCase):
    def test_limit_uses_regular_total_not_resident_total(self):
        binter = leg(
            "Binter", "NT1", "TFN", "2026-11-01T08:00:00+00:00",
            "MAD", "2026-11-01T12:00:00+01:00", 800, 200,
        )
        wizz = leg(
            "Wizz Air", "W61472", "MAD", "2026-11-01T15:00:00+01:00",
            "WAW", "2026-11-01T18:30:00+01:00", 250,
            booking_url="https://www.wizzair.com/example",
        )
        self.assertEqual(build_connections([wizz], [binter], 1000), [])

    def test_both_directions_and_strict_limit(self):
        wizz_to_poland = leg(
            "Wizz Air", "W61472", "MAD", "2026-11-01T15:00:00+01:00",
            "WAW", "2026-11-01T18:30:00+01:00", 300,
            booking_url="https://www.wizzair.com/to-poland",
        )
        binter_to_transfer = leg(
            "Binter", "NT1", "TFN", "2026-11-01T08:00:00+00:00",
            "MAD", "2026-11-01T12:00:00+01:00", 650, 162.5,
        )
        wizz_from_poland = leg(
            "Wizz Air", "W61471", "WAW", "2026-11-02T06:00:00+01:00",
            "MAD", "2026-11-02T10:00:00+01:00", 300,
            booking_url="https://www.wizzair.com/from-poland",
        )
        binter_to_tenerife = leg(
            "Binter", "NT2", "MAD", "2026-11-02T13:00:00+01:00",
            "TFN", "2026-11-02T15:00:00+00:00", 699.99, 175,
        )
        results = build_connections(
            [wizz_to_poland, wizz_from_poland],
            [binter_to_transfer, binter_to_tenerife],
            1000,
        )
        self.assertEqual(len(results), 2)
        self.assertEqual({result["direction"] for result in results}, {
            "tenerife_to_poland", "poland_to_tenerife",
        })
        self.assertTrue(all(result["price_total_regular_pln"] < 1000 for result in results))

        document = {
            "directions": ["tenerife_to_poland", "poland_to_tenerife"],
            "results": results,
        }
        validate_document(document, 1000)


if __name__ == "__main__":
    unittest.main()
