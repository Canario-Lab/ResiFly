import copy
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

from scripts import collect_step6 as step
from scripts.booking_urls import easyjet_booking_url, ryanair_booking_url, wizz_booking_url
from scripts.collection_coverage import Coverage, expected_queries
from scripts.collect_step1 import AIRPORT_TIMEZONES
from scripts.discover_easyjet_routes import build_plan, apply_plan
from scripts.easyjet_source import parse_google_flights_response, collect_trip, collect_legs
from scripts.search_airports import POLISH_AIRPORTS
from scripts.search_steps import STEPS
from scripts.source_pipeline import STEPS as PIPELINE_STEPS

DAY = date(2026, 10, 27)


def offer(price=304, number="2340", marketing="U2", clock=None, arrival_day=None):
    segment = [None] * 23
    segment[3], segment[6] = "TFS", "LTN"
    segment[8], segment[10] = clock or [18, 10], [22, 35]
    segment[20] = [2026, 10, 27]
    day = arrival_day or DAY
    segment[21] = [day.year, day.month, day.day]
    segment[22] = [marketing, number]
    return [[None, None, [segment]], [[None, price]]]


def html(*offers, payload=None):
    return '<div>PLN</div><script class="ds:1">data:' + json.dumps(
        [None, None, None, [list(offers)]] if payload is None else payload) + ',extra:{}</script>'


def low_leg(origin="KRK", destination="LTN", departure="2026-10-27T12:00:00+01:00",
            arrival="2026-10-27T14:00:00+00:00", carrier="Ryanair"):
    booking = ryanair_booking_url if carrier == "Ryanair" else wizz_booking_url
    row = {"carrier": carrier, "flight_number": "FR1" if carrier == "Ryanair" else "W60001",
           "departure_airport": origin, "arrival_airport": destination,
           "departure_at": departure, "arrival_at": arrival,
           "price_regular_pln": 1300, "price_resident_estimated_pln": 1300,
           "resident_discount_eligible": False,
           "booking_url": booking(origin, destination, departure)}
    if carrier == "Wizz Air":
        row["price_wizz_discount_club_pln"] = 1100
    return row


class EasyJetTests(unittest.TestCase):
    def setUp(self):
        AIRPORT_TIMEZONES.update({"TFS": "Atlantic/Canary", "LTN": "Europe/London"})
        self.config = step.load_allowlist()

    def jet(self, departure="2026-10-27T16:00:00+00:00", arrival="2026-10-27T20:35:00+00:00", reverse=False):
        row = parse_google_flights_response(html(offer()), "TFS", "LTN", DAY)[0]
        if not reverse:
            row["departure_airport"], row["arrival_airport"] = "LTN", "TFS"
        row.update(departure_at=departure, arrival_at=arrival)
        return step.prepare_easyjet_legs([row], self.config, 4.3917)[0]

    def test_parser_individual_prices_all_groups_and_family_codes(self):
        payload = [None, None, None, [[offer(), offer(355, "2304", clock=[12, 55])]],
                   [offer(804, "1026", "DS"), offer(500, "1001", "EC"), offer(300, "2340")]]
        rows = parse_google_flights_response(html(payload=payload), "TFS", "LTN", DAY)
        self.assertEqual({r["flight_number"]: r["price_regular_pln"] for r in rows},
                         {"U22340": 300, "U22304": 355, "DS1026": 804, "EC1001": 500})
        self.assertTrue(all(r["price_passengers"]["adults"] == 1 for r in rows))

    def test_unpriced_flight_missing_number_clock_or_date_never_becomes_zero(self):
        cases = [offer(None), offer(number=""), offer(clock=[24])]
        missing = offer(); missing[0][2][0][8] = None; cases.append(missing)
        missing = offer(); missing[0][2][0][20] = None; cases.append(missing)
        for value in cases:
            with self.subTest(value=value), self.assertRaises((RuntimeError, ValueError)):
                parse_google_flights_response(html(value), "TFS", "LTN", DAY)
        with self.assertRaises(RuntimeError):
            parse_google_flights_response("loading results PLN", "TFS", "LTN", DAY)

    def test_empty_day_and_overnight_are_distinct_from_failure(self):
        self.assertEqual(parse_google_flights_response(html(payload=[None, None, None, None]), "TFS", "LTN", DAY), [])
        row = offer(arrival_day=DAY + timedelta(days=1))
        row[0][2][0][8], row[0][2][0][10] = [22], [2, 35]
        parsed = parse_google_flights_response(html(row), "TFS", "LTN", DAY)
        self.assertTrue(parsed[0]["arrival_at"].startswith("2026-10-28"))
        self.assertEqual(parse_google_flights_response(html(offer(marketing="FR")), "TFS", "LTN", DAY), [])
        self.assertEqual(len(parse_google_flights_response(html(offer(None), offer()), "TFS", "LTN", DAY)), 1)

    def test_stable_booking_link_has_one_adult_own_date_and_no_session(self):
        url = easyjet_booking_url("ltn", "tfs", "2026-11-01T07:00:00+00:00")
        parts, query = urlparse(url), parse_qs(urlparse(url).query)
        self.assertEqual((parts.netloc, parts.path), ("www.easyjet.com", "/deeplink"))
        self.assertEqual((query["dep"], query["dest"], query["dd"], query["apax"]),
                         (["LTN"], ["TFS"], ["2026-11-01"], ["1"]))
        self.assertFalse(set(query) & {"token", "session", "cookies", "rdfn", "xdfn"})

    def test_full_independent_plan_both_directions_and_shared_registry(self):
        start, end = DAY, DAY + timedelta(days=30)
        planned = expected_queries("6", start, end)
        for carrier, origin, destination in step.low_cost_route_matrix(self.config):
            self.assertEqual(sum(q[:3] == (carrier, origin, destination) for q in planned), 31)
        for origin, destination, day in step.easyjet_route_days(self.config, start, end):
            self.assertIn(("easyJet", origin, destination, str(day), "calendar"), planned)
        self.assertEqual(set(self.config["scope"]["polish_airports"]), set(POLISH_AIRPORTS))
        self.assertEqual(STEPS, PIPELINE_STEPS)
        self.assertEqual(len(STEPS), 11)
        tracker = Coverage("6", start, end, planned)
        self.assertEqual(tracker.report()["missing_queries"], len(planned))

    def test_both_directions_and_boundary_minutes_prices_above_ui_cap(self):
        low = low_leg()
        for minutes, expected in ((119, 0), (120, 1), (1440, 1), (1441, 0)):
            departure = datetime.fromisoformat(low["arrival_at"]) + timedelta(minutes=minutes)
            jet = self.jet(departure.isoformat(), (departure + timedelta(hours=4)).isoformat())
            self.assertEqual(len(step.build_connections([low], [jet], self.config)), expected)
        jet = self.jet()
        out = step.build_connections([low], [jet], self.config)[0]
        self.assertEqual(out["direction"], "poland_to_tenerife")
        self.assertGreater(out["price_total_regular_pln"], 1000)
        back = step.build_connections([low_leg("LTN", "KRK", "2026-10-28T07:00:00+00:00", "2026-10-28T10:00:00+01:00")],
                                     [self.jet(reverse=True)], self.config)[0]
        self.assertEqual(back["direction"], "tenerife_to_poland")

    def test_wrong_iata_or_carrier_never_matches_and_wdc_only_applies_to_wizz(self):
        jet = self.jet()
        self.assertEqual(step.build_connections([low_leg(destination="LGW")], [jet], self.config), [])
        low = low_leg(origin="WAW", carrier="Wizz Air")
        result = step.build_connections([low], [jet], self.config)[0]
        self.assertEqual(result["price_total_wizz_discount_club_pln"], 1404)
        self.assertEqual(result["price_total_resident_estimated_pln"], 1604)
        self.assertEqual(jet["price_regular_pln"], jet["price_resident_estimated_pln"])

    def test_validator_rejects_edited_resident_fare_route_and_totals(self):
        rows = step.build_connections([low_leg()], [self.jet()], self.config)
        document = {"results": rows, "exchange_rates": {"EUR_PLN": {"rate": 4.3917}}}
        step.validate_document(document, self.config)
        for target, key, value in (("result", "layover_minutes", 119),
                                   ("result", "price_total_regular_pln", 1),
                                   ("jet", "price_resident_estimated_pln", 50),
                                   ("jet", "booking_url", "https://example.com/session")):
            damaged = copy.deepcopy(document)
            row = damaged["results"][0]
            (row if target == "result" else row["legs"][1])[key] = value
            with self.assertRaises(RuntimeError):
                step.validate_document(damaged, self.config)

    @patch("scripts.easyjet_source.time.sleep")
    def test_http_errors_are_retried_with_bounded_budget_not_empty_success(self, sleep):
        client = Mock()
        client.availability.side_effect = [RuntimeError("HTTP 429")] * 4
        with self.assertRaisesRegex(RuntimeError, "publication blocked"):
            collect_trip(client, "TFS", "LTN", DAY)
        self.assertEqual(client.availability.call_count, 4)
        client.availability.side_effect = [RuntimeError("loading"), html(offer())]
        self.assertEqual(len(collect_trip(client, "TFS", "LTN", DAY)), 1)

    def test_discovery_new_hub_all_endpoints_pending_wizz_and_no_iata_alias(self):
        network = {"verified_on": str(DAY), "source": "https://www.easyjet.com/en/flights-timetables",
                   "resident_terms": "https://www.easyjet.com/en/terms-and-conditions/large-families",
                   "tenerife_destinations": {"TFS": ["BFS", "CDG"], "TFN": []}}
        snapshot = {"as_of": str(DAY), "airports": {"BFS": {"timezone": "Europe/London", "country_code": "GB"},
                    "CDG": {"timezone": "Europe/Paris", "country_code": "FR"}},
                    "routes": {"ryanair": [["BFS", p] for p in POLISH_AIRPORTS] + [["BVA", "WMI"]],
                               "wizzair": [["BFS", "WAW"]]}}
        report = build_plan(network, snapshot, {})
        self.assertEqual(len(report["ready"]), len(POLISH_AIRPORTS))
        self.assertEqual(len(report["pending"]), 1)
        self.assertEqual(report["no_shared_polish_route"], ["CDG"])
        config = apply_plan(report, snapshot)
        self.assertEqual(len(config["airports"]), 1)
        self.assertEqual(config, apply_plan(report, snapshot, config))


if __name__ == "__main__":
    unittest.main()
