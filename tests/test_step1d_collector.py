import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import (
    collect_step1d as collector,
    collection_coverage as coverage,
    reprice_spanish_resident_estimates as repricer,
)
from scripts.booking_urls import air_europa_booking_url
from scripts.collect_step1 import CurrencyRate, configure_airports_from_allowlist


def google_offer(number="9048", hour=15, price=659, carrier="UX", origin="MAD", destination="TFN", day=date(2026, 11, 1)):
    segment = [None] * 23
    segment[2], segment[3], segment[6] = "Air Europa", origin, destination
    segment[8], segment[10] = [hour, 0], [hour + 1, 55]
    segment[20] = segment[21] = [day.year, day.month, day.day]
    segment[22] = [carrier, number]
    return [[None, None, [segment]], [[None, price]]]


def google_html(*offers, additional=None):
    payload = [None, additional, None, [list(offers)]]
    return '<html>PLN<script class="ds:1">AF_initDataCallback({data:' + json.dumps(payload) + ',sideChannel:{}});</script></html>'


def low_cost_leg(origin, departure, destination, arrival, price=250):
    return {"carrier": "Wizz Air", "flight_number": "W60000", "departure_airport": origin,
            "departure_at": departure, "arrival_airport": destination, "arrival_at": arrival,
            "price_regular_pln": price, "price_resident_estimated_pln": price,
            "resident_discount_eligible": False, "booking_url": "https://www.wizzair.com/example"}


def air_europa_leg(origin, departure, destination, arrival, regular=800):
    fee = {("MAD", "TFN"): 19.57, ("TFN", "MAD"): 8.91}[(origin, destination)]
    resident, fee_pln = collector.resident_price_estimate(regular, .25, fee, 4.0)
    return {"carrier": "Air Europa", "flight_number": "UX9048", "departure_airport": origin,
            "departure_at": departure, "arrival_airport": destination, "arrival_at": arrival,
            "price_regular_pln": regular, "price_resident_estimated_pln": resident,
            "resident_discount_eligible": True, "resident_fare_multiplier": .25,
            "resident_nondiscountable_fees_eur": fee,
            "resident_nondiscountable_fees_pln": fee_pln,
            "resident_estimate_exchange_rate_eur_pln": 4.0,
            "booking_url": air_europa_booking_url(origin, destination, departure),
            "price_source": "Google Flights", "price_scope": "individual_flight_offer"}


class Step1DCollectorTests(unittest.TestCase):
    def setUp(self):
        self.allowlist = json.loads(collector.TRANSFER_FILE.read_text())
        collector.validate_allowlist(self.allowlist)
        configure_airports_from_allowlist(self.allowlist)

    def parse(self, html):
        return collector.parse_google_flights_response(
            html, "MAD", "TFN", date(2026, 11, 1), .25, 4.3685, {"UX"}
        )

    def test_only_google_allowed_without_active_fare_feed_or_templates(self):
        self.assertNotIn("fare_feed", self.allowlist)
        self.assertNotIn("air_europa_schedule_templates", self.allowlist)
        self.assertEqual([a["iata"] for a in self.allowlist["airports"]], ["MAD", "BIO"])
        for airport in self.allowlist["airports"]:
            self.assertEqual(airport["tenerife_airports"], ["TFN"])
            self.assertTrue(airport["resident_discount_eligible_on_air_europa_leg"])
            self.assertEqual(airport["air_europa_resident_fare_multiplier"], .25)
        self.assertEqual(
            self.allowlist["usage_policy"]["resident_estimate_fee_registry"],
            "data/spanish-resident-fees.json",
        )
        self.allowlist["usage_policy"]["flight_data_source"] = "official_route_day_fares"
        with self.assertRaisesRegex(RuntimeError, "Google Flights"):
            collector.validate_allowlist(self.allowlist)

    def test_route_matrix_uses_only_saved_low_cost_pairs(self):
        routes = set(collector.low_cost_route_matrix(self.allowlist))
        for pair in (("Wizz Air", "MAD", "WAW"), ("Ryanair", "KRK", "MAD"), ("Wizz Air", "BIO", "KRK"), ("Wizz Air", "GDN", "MAD")):
            self.assertIn(pair, routes)
        self.assertNotIn(("Ryanair", "BIO", "WAW"), routes)

    def test_route_days_cover_every_day_both_ways_without_template_expiry(self):
        start, end = date(2027, 8, 1), date(2027, 8, 31)
        plan = collector.air_europa_route_days(self.allowlist, start, end)
        self.assertEqual(len(plan), 124)
        for day in (start, date(2027, 8, 15), end):
            for origin, destination in (("MAD", "TFN"), ("TFN", "MAD"), ("BIO", "TFN"), ("TFN", "BIO")):
                self.assertIn((origin, destination, day), plan)

    def test_every_flight_has_own_price_number_and_booking_link(self):
        legs = self.parse(google_html(google_offer("9059", 7, 283), google_offer("9118", 11, 344), google_offer(), google_offer("9057", 19, 257)))
        self.assertEqual([r["price_regular_pln"] for r in legs], [283, 344, 659, 257])
        self.assertEqual([r["flight_number"] for r in legs], ["UX9059", "UX9118", "UX9048", "UX9057"])
        self.assertEqual(legs[2]["price_resident_estimated_pln"], 228.87)
        self.assertEqual(legs[2]["resident_nondiscountable_fees_eur"], 19.57)
        self.assertEqual(legs[2]["resident_nondiscountable_fees_pln"], 85.49)
        self.assertEqual(legs[2]["price_scope"], "individual_flight_offer")
        self.assertEqual(legs[2]["booking_url_scope"], "route_date_search")
        self.assertIn("residentType=SPANISH_RESIDENT_RC", legs[2]["booking_url"])
        self.assertNotIn("token", json.dumps(legs).lower())

    def test_extra_offer_bucket_and_duplicate_fares_are_handled_per_flight(self):
        legs = self.parse(google_html(google_offer(price=700), additional=[google_offer(price=659), google_offer("9059", 7, 283)]))
        self.assertEqual(len(legs), 2)
        self.assertEqual(legs[1]["price_regular_pln"], 659)

    def test_other_carrier_route_or_date_is_not_relabelled(self):
        self.assertEqual(self.parse(google_html(google_offer(carrier="IB"), google_offer(destination="BIO"), google_offer(day=date(2026, 11, 2)))), [])

    def test_high_price_not_filtered_and_overnight_date_not_invented(self):
        value = google_offer(hour=23, price=5000)
        value[0][2][0][10], value[0][2][0][21] = [1, 55], [2026, 11, 2]
        legs = self.parse(google_html(value))
        self.assertEqual(legs[0]["price_regular_pln"], 5000)
        self.assertTrue(legs[0]["arrival_at"].startswith("2026-11-02T01:55"))

    def test_missing_price_cannot_borrow_another_flights_price(self):
        with self.assertRaisesRegex(RuntimeError, "bez ceny"):
            self.parse(google_html(google_offer(price=None), google_offer("9059", 7, 283)))
        self.assertEqual(self.parse(google_html(google_offer(price=None), google_offer()))[0]["price_regular_pln"], 659)

    def test_missing_number_or_clock_cannot_use_placeholder(self):
        with self.assertRaisesRegex(RuntimeError, "numer"):
            self.parse(google_html(google_offer(number="")))
        value = google_offer()
        for invalid in (None, []):
            value[0][2][0][8] = invalid
            with self.assertRaisesRegex(RuntimeError, "godziny"):
                self.parse(google_html(value))

    def test_google_compact_clock_omits_zero_minutes(self):
        value = google_offer()
        value[0][2][0][8] = [15]
        self.assertEqual(self.parse(google_html(value))[0]["departure_at"], "2026-11-01T15:00:00+01:00")

    def test_invalid_clock_is_not_coerced_to_midnight(self):
        for clock in (["15"], [15, ""], [24], [-1, 0], [15, 60], [True, 0], [15, False]):
            value = google_offer()
            value[0][2][0][8] = clock
            with self.assertRaisesRegex(RuntimeError, "godzina"):
                self.parse(google_html(value))

    def test_malformed_source_is_not_a_successful_empty_day(self):
        for html in ("<html>error</html>", '<script class="ds:1">data:{},x:0</script>'):
            with self.assertRaises((RuntimeError, ValueError)):
                self.parse(html)
        self.assertEqual(self.parse(google_html()), [])

    @patch("scripts.source_recovery.ThreadPoolExecutor", wraps=ThreadPoolExecutor)
    @patch("scripts.collect_step1d.GoogleFlightsClient.availability", autospec=True)
    def test_full_calendar_coverage_and_three_worker_cap(self, availability, pool):
        start, end = date(2026, 10, 22), date(2026, 11, 21)
        plan = collector.air_europa_route_days(self.allowlist, start, end)
        expected = {("Air Europa", o, d, str(day), "calendar") for o, d, day in plan}
        tracker = coverage.Coverage("1d", start, end, expected)
        availability.side_effect = lambda client, o, d, day: google_html(google_offer(origin=o, destination=d, day=day, hour=7))
        with patch.object(coverage, "_active", tracker):
            rows = collector.collect_air_europa_legs(plan, self.allowlist, 99, 4.0)
        self.assertEqual(len(rows), 124)
        self.assertEqual(availability.call_count, 124)
        self.assertEqual(pool.call_args.kwargs["max_workers"], 3)
        self.assertEqual(tracker.verify()["completed_queries"], 124)

    def test_old_day_minimum_coverage_is_no_longer_valid(self):
        tracker = coverage.Coverage("1d", date(2026, 11, 1), date(2026, 11, 1), set())
        with self.assertRaisesRegex(RuntimeError, "Unverified"):
            tracker.record("Air Europa", "MAD", "TFN", date(2026, 11, 1), date(2026, 11, 1), [], "official_route_day_fares")

    def test_resident_estimate_discounts_fare_but_not_fixed_fees(self):
        official_example, _ = collector.resident_price_estimate(150.57, .25, 19.57, 1.0)
        self.assertEqual(official_example, 52.32)
        resident, fees_pln = collector.resident_price_estimate(659, .25, 19.57, 4.3685)
        self.assertEqual(fees_pln, 85.49)
        self.assertEqual(resident, 228.87)
        reverse, reverse_fees = collector.resident_price_estimate(659, .25, 8.91, 4.3685)
        self.assertEqual(reverse_fees, 38.92)
        self.assertEqual(reverse, 193.94)
        with self.assertRaisesRegex(RuntimeError, "niższa"):
            collector.resident_price_estimate(20, .25, 19.57, 4.3685)

    @patch("scripts.reprice_spanish_resident_estimates.validate_coverage")
    def test_existing_feed_reprice_is_offline_and_preserves_flight_data(self, validate_coverage):
        result = collector.build_connections([
            low_cost_leg("WAW", "2026-11-01T08:20:00+01:00", "MAD", "2026-11-01T12:05:00+01:00", 183),
        ], [
            air_europa_leg("MAD", "2026-11-01T15:00:00+01:00", "TFN", "2026-11-01T16:55:00+00:00", 659),
        ])[0]
        air_leg = next(leg for leg in result["legs"] if leg["carrier"] == "Air Europa")
        air_leg["price_resident_estimated_pln"] = 164.75
        result["price_total_resident_estimated_pln"] = 347.75
        flight_identity = {
            key: air_leg[key] for key in (
                "flight_number", "departure_airport", "arrival_airport",
                "departure_at", "arrival_at", "price_regular_pln", "booking_url",
            )
        }
        document = {
            "step": "1D", "period_from": "2026-10-22", "period_to": "2026-11-21",
            "generated_at": "2026-10-22T22:28:41+01:00",
            "exchange_rates": {"EUR_PLN": {"rate": 4.3685}},
            "sources": {"air_europa_resident_price": "old"},
            "collection_coverage": {"run_id": "saved-run"}, "results": [result],
        }
        changed = repricer.reprice_document("1d", document, repricer.load_fee_registry())
        self.assertEqual(changed, 1)
        self.assertEqual(air_leg["price_resident_estimated_pln"], 228.87)
        self.assertEqual(result["price_total_resident_estimated_pln"], 411.87)
        self.assertEqual(flight_identity, {key: air_leg[key] for key in flight_identity})
        self.assertFalse(document["derived_price_update"]["network_requests"])
        self.assertEqual(document["generated_at"], "2026-10-22T22:28:41+01:00")
        validate_coverage.assert_called_once()

    @patch("scripts.collect_step1d.GoogleFlightsClient.availability", side_effect=RuntimeError("Google unavailable"))
    @patch("scripts.collect_step1d.collect_low_cost_legs", return_value=[{}])
    @patch("scripts.collect_step1d.nbp_eur_rate", return_value=CurrencyRate("EUR", 4.0))
    def test_failure_preserves_previous_public_file(self, rate, low, availability):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "step1d-results.json"
            output.write_text("previous feed")
            with patch("sys.argv", ["collect_step1d", "--from-date", "2026-11-01", "--days", "0", "--output", str(output)]):
                with self.assertRaises(RuntimeError):
                    collector.main()
            self.assertEqual(output.read_text(), "previous feed")
            report = json.loads(output.with_suffix(".collection-report.json").read_text())
            self.assertEqual(report["status"], "failed")
            self.assertGreater(report["missing_queries"], 0)
            # At most two route/day workers run concurrently. Each worker may
            # retry the same transient Google/parser failure up to four times.
        self.assertLessEqual(availability.call_count, 12)

    def test_builds_both_directions_without_price_limit(self):
        out = collector.build_connections([
            low_cost_leg("MAD", "2026-10-29T14:00:00+01:00", "WAW", "2026-10-29T17:00:00+01:00", 500),
            low_cost_leg("WAW", "2026-10-30T06:00:00+01:00", "MAD", "2026-10-30T09:30:00+01:00", 600),
        ], [
            air_europa_leg("TFN", "2026-10-29T07:05:00+00:00", "MAD", "2026-10-29T10:50:00+01:00", 1000),
            air_europa_leg("MAD", "2026-10-30T15:00:00+01:00", "TFN", "2026-10-30T16:55:00+00:00", 1200),
        ])
        self.assertEqual(len(out), 2)
        self.assertEqual({r["direction"] for r in out}, {"tenerife_to_poland", "poland_to_tenerife"})
        self.assertEqual({r["price_total_regular_pln"] for r in out}, {1500, 1800})
        collector.validate_document({"results": out})
        for field, invalid in (("flight_number", "UX"), ("price_source", "Air Europa official branded fare feed"), ("price_scope", "lowest_official_route_day_fare")):
            broken = copy.deepcopy(out)
            leg = next(leg for leg in broken[0]["legs"] if leg["carrier"] == "Air Europa")
            leg[field] = invalid
            with self.assertRaises(RuntimeError):
                collector.validate_document({"results": broken})


if __name__ == "__main__":
    unittest.main()
