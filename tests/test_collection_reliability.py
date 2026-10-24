import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from scripts.collector_settings import (
    GOOGLE_FLIGHTS_MAX_WORKERS,
    google_flights_worker_count,
)
from scripts.collect_step1 import _nbp_rates_by_day, nbp_rate


class CollectionReliabilityTests(unittest.TestCase):
    def tearDown(self):
        _nbp_rates_by_day.clear()

    def test_google_flights_workers_are_capped_for_shared_runners(self):
        self.assertEqual(GOOGLE_FLIGHTS_MAX_WORKERS, 3)
        self.assertEqual(google_flights_worker_count(1), 1)
        self.assertEqual(google_flights_worker_count(4), 3)
        self.assertEqual(google_flights_worker_count(20), 3)

    def test_nbp_snapshot_is_fetched_once_and_reused_from_daily_cache(self):
        requested_day = date(2026, 10, 22)
        table_a = [{
            "effectiveDate": "2026-10-21",
            "rates": [
                {"code": "EUR", "mid": 4.3},
                {"code": "GBP", "mid": 5.1},
                {"code": "HUF", "mid": 0.011},
                {"code": "RON", "mid": 0.8},
                {"code": "USD", "mid": 3.9},
            ],
        }]
        table_b = [{
            "effectiveDate": "2026-10-20",
            "rates": [{"code": "MAD", "mid": 0.39}],
        }]

        with tempfile.TemporaryDirectory() as directory:
            with patch("scripts.collect_step1.NBP_CACHE_DIR", Path(directory)):
                with patch(
                    "scripts.collect_step1.get_json",
                    side_effect=[table_a, table_b],
                ) as get_json:
                    self.assertEqual(nbp_rate("EUR", requested_day).pln, 4.3)
                    self.assertEqual(nbp_rate("MAD", requested_day).pln, 0.39)
                    self.assertEqual(get_json.call_count, 2)

                _nbp_rates_by_day.clear()
                with patch("scripts.collect_step1.get_json") as get_json:
                    self.assertEqual(nbp_rate("USD", requested_day).pln, 3.9)
                    get_json.assert_not_called()


if __name__ == "__main__":
    unittest.main()
