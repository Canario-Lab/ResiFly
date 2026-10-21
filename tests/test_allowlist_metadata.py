import json
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


class AllowlistMetadataTests(unittest.TestCase):
    def load(self, name):
        return json.loads((DATA / name).read_text(encoding="utf-8"))

    def test_transfer_allowlists_define_every_transfer_timezone(self):
        for name in (
            "ryanair-transfer-airports.json",
            "wizzair-transfer-airports.json",
            "mixed-transfer-airports.json",
        ):
            document = self.load(name)
            if "airports" in document:
                codes = {item["iata"] for item in document["airports"]}
            else:
                codes = {
                    item["iata"]
                    for variant in document["variants"].values()
                    for item in variant["airports"]
                }
            timezones = document["airport_timezones"]
            self.assertEqual(codes, set(timezones), name)
            for timezone in timezones.values():
                ZoneInfo(timezone)

    def test_shared_wizz_route_registry_is_well_formed(self):
        document = self.load("wizz-route-schedules.json")
        route_keys = set()
        for route in document["routes"]:
            key = (route["origin"], route["destination"])
            self.assertNotIn(key, route_keys)
            route_keys.add(key)
            self.assertGreater(route["duration_minutes"], 0)
            self.assertTrue(route["flight_number"].startswith("W"))

        override_keys = set()
        for item in document["flight_number_overrides_by_departure_time"]:
            key = (item["origin"], item["destination"], item["departure_time"])
            self.assertNotIn(key, override_keys)
            override_keys.add(key)
            self.assertIn((item["origin"], item["destination"]), route_keys)

    def test_step1f_canaryfly_allowlist_has_valid_timezones_and_discount(self):
        document = self.load("canaryfly-transfer-airports.json")
        self.assertEqual(document["usage_policy"]["step"], "1F")
        self.assertEqual(
            {item["iata"] for item in document["airports"]},
            {"FUE", "LPA"},
        )
        for airport in document["airports"]:
            ZoneInfo(airport["timezone"])
            self.assertTrue(
                airport["resident_discount_eligible_on_canaryfly_leg"]
            )
            self.assertEqual(
                airport["canaryfly_resident_fare_multiplier"], 0.25
            )


if __name__ == "__main__":
    unittest.main()
