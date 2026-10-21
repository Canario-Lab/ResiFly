import copy
import unittest

from scripts.discover_transfer_routes import apply_plan, build_plan, discover_candidates


def base_documents(with_schedules=True):
    schedules = []
    if with_schedules:
        for origin, destination, number, duration in (
            ("WAW", "BCN", "W60001", 180),
            ("BCN", "WAW", "W60002", 175),
            ("TFS", "BCN", "W60003", 200),
            ("BCN", "TFS", "W60004", 205),
        ):
            schedules.append(
                {
                    "origin": origin,
                    "destination": destination,
                    "flight_number": number,
                    "duration_minutes": duration,
                }
            )
    discount = {
        "eligible_transfer_airports": [],
        "ineligible_transfer_airports": [],
        "eligible_count": 0,
        "ineligible_count": 0,
    }
    return {
        "step1": {
            "airports": [],
            "wizz_route_schedules": [],
            "excluded_airports": [{"iata": "FNC"}],
        },
        "step3": {
            "airports": [
                {
                    "iata": "OLD",
                    "name_pl": "Stare lotnisko",
                    "country_pl": "Test",
                    "tenerife_airports": ["TFS"],
                    "polish_airports": ["KRK"],
                }
            ],
            "airport_timezones": {"OLD": "Etc/UTC"},
            "resident_discount_on_tenerife_leg": copy.deepcopy(discount),
            "selection_method": {"result_count": 1},
        },
        "step4": {
            "airports": [],
            "airport_timezones": {},
            "resident_discount_on_tenerife_leg": copy.deepcopy(discount),
            "selection_method": {"result_count": 0},
        },
        "step5": {
            "airport_timezones": {},
            "resident_discount_on_tenerife_leg": {
                "variant_a": copy.deepcopy(discount),
                "variant_b": copy.deepcopy(discount),
            },
            "selection_method": {
                "variant_a_result_count": 0,
                "variant_b_result_count": 0,
                "unique_transfer_airport_count": 0,
            },
            "variants": {
                "ryanair_tenerife_wizzair_poland": {"airports": []},
                "wizzair_tenerife_ryanair_poland": {"airports": []},
            },
        },
        "wizz_schedules": {
            "routes": schedules,
            "flight_number_overrides_by_departure_time": [],
        },
    }


def snapshot():
    return {
        "as_of": "2026-10-21",
        "airports": {
            "BCN": {
                "name": "Barcelona",
                "country_code": "ES",
                "country_name": "Spain",
                "timezone": "Europe/Madrid",
            },
            "LPL": {
                "name": "Liverpool",
                "country_code": "GB",
                "country_name": "United Kingdom",
                "timezone": "Europe/London",
            },
        },
        "routes": {
            "binter": [["TFS", "BCN"], ["BCN", "TFS"]],
            "ryanair": [
                ["TFS", "BCN"],
                ["BCN", "KRK"],
                ["TFS", "LPL"],
                ["LPL", "KRK"],
            ],
            "wizzair": [
                ["TFS", "BCN"],
                ["BCN", "TFS"],
                ["BCN", "WAW"],
                ["WAW", "BCN"],
            ],
        },
    }


class RouteDiscoveryTests(unittest.TestCase):
    def test_finds_each_applicable_transfer_variant(self):
        found = discover_candidates(snapshot())
        self.assertEqual([item.iata for item in found["step1"]], ["BCN"])
        self.assertEqual([item.iata for item in found["step3"]], ["BCN", "LPL"])
        self.assertEqual([item.iata for item in found["step4"]], ["BCN"])
        self.assertEqual([item.iata for item in found["step5_variant_a"]], ["BCN"])
        self.assertEqual([item.iata for item in found["step5_variant_b"]], ["BCN"])

    def test_complete_plan_adds_routes_and_never_removes_old_airport(self):
        documents = base_documents(with_schedules=True)
        report = build_plan(snapshot(), documents)
        self.assertFalse(
            any(step["pending"] for step in report["steps"].values())
        )
        changed = apply_plan(snapshot(), documents, report)

        self.assertEqual(
            [item["iata"] for item in changed["step3"]["airports"]],
            ["BCN", "LPL", "OLD"],
        )
        self.assertIn("BCN", changed["step3"]["resident_discount_on_tenerife_leg"]["eligible_transfer_airports"])
        self.assertIn("LPL", changed["step3"]["resident_discount_on_tenerife_leg"]["ineligible_transfer_airports"])
        self.assertEqual(changed["step4"]["airport_timezones"]["BCN"], "Europe/Madrid")
        self.assertEqual(len(changed["step1"]["wizz_route_schedules"]), 2)

    def test_missing_wizz_schedule_skips_only_incomplete_candidates(self):
        documents = base_documents(with_schedules=False)
        report = build_plan(snapshot(), documents)
        self.assertTrue(report["steps"]["step1"]["pending"])
        self.assertTrue(report["steps"]["step4"]["pending"])
        changed = apply_plan(snapshot(), documents, report)
        self.assertEqual(set(changed), {"step3"})
        self.assertNotIn("step1", changed)
        self.assertNotIn("step4", changed)
        self.assertNotIn("step5", changed)

    def test_step1_respects_explicit_exclusion_list(self):
        data = snapshot()
        data["airports"]["FNC"] = {
            "name": "Funchal",
            "country_code": "PT",
            "country_name": "Portugal",
            "timezone": "Atlantic/Madeira",
        }
        data["routes"]["binter"].append(["TFS", "FNC"])
        data["routes"]["ryanair"].append(["FNC", "KRK"])
        report = build_plan(data, base_documents(with_schedules=True))
        self.assertEqual(report["steps"]["step1"]["excluded"][0]["iata"], "FNC")
        self.assertNotIn(
            "FNC",
            [item["iata"] for item in report["steps"]["step1"]["ready"]],
        )


if __name__ == "__main__":
    unittest.main()
