"""Fifteen live endpoints, full calendars, domestic discovery and frozen thirteen."""
import copy
from datetime import date, timedelta
import importlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import collect_step2, collect_step3, collect_step4, collect_step5
from scripts.collection_coverage import Coverage, expected_queries, validate_coverage
from scripts.discover_transfer_routes import discover_candidates
from scripts.search_airports import POLISH_AIRPORTS, ENDPOINT_TIMEZONES, DOMESTIC_TRANSFERS_ALLOWED, validate_polish_transfer
from tests.test_airport_expansion import leg

ROOT = Path(__file__).resolve().parents[1]
THIRTEEN = ("WAW", "WMI", "KTW", "KRK", "GDN", "WRO", "POZ", "LCJ", "RZE", "BZG", "LUZ", "SZY", "RDO")
START, END = date(2026,10,24), date(2026,11,23)


class SzzIegTests(unittest.TestCase):
    def test_saved_new_pairs_match_captured_official_network_when_available(self):
        snapshot_path=ROOT/"tmp/szz-ieg-expansion/audit-SZZ/network-snapshot.json"
        if not snapshot_path.exists(): self.skipTest("Local evidence artifact is not checked in")
        found=discover_candidates(json.loads(snapshot_path.read_text()))
        for step,module,variant in (("step3",collect_step3,None),("step4",collect_step4,None),
                ("step5_variant_a",collect_step5,collect_step5.VARIANT_A),
                ("step5_variant_b",collect_step5,collect_step5.VARIANT_B)):
            config=module.load_allowlist()
            rows=config["airports"] if variant is None else config["variants"][variant]["airports"]
            actual={(r["iata"],p) for r in rows for p in r["polish_airports"] if p in ("SZZ","IEG")}
            expected={(r.iata,p) for r in found[step] for p in r.polish_airports if p in ("SZZ","IEG")}
            self.assertEqual(actual,expected,step)

    def test_registry_and_exact_nine_scopes(self):
        self.assertEqual(POLISH_AIRPORTS, THIRTEEN + ("SZZ", "IEG"))
        for code in ("SZZ", "IEG"):
            self.assertEqual(ENDPOINT_TIMEZONES[code], "Europe/Warsaw")
        files = list((ROOT / "data").glob("*transfer-airports.json"))
        self.assertEqual(len(files), 9)
        for file in files:
            self.assertEqual(json.loads(file.read_text())["scope"]["polish_airports"], list(POLISH_AIRPORTS))

    def test_all_polish_hubs_are_allowed_not_self_routes(self):
        self.assertTrue(DOMESTIC_TRANSFERS_ALLOWED)
        for step in ("step3", "step4", "step5_variant_a", "step5_variant_b"):
            for polish in POLISH_AIRPORTS:
                for hub in POLISH_AIRPORTS:
                    if polish == hub:
                        with self.assertRaises(RuntimeError): validate_polish_transfer(polish, hub, step)
                    else: validate_polish_transfer(polish, hub, step)
        snapshot = {"routes": {"ryanair": [["SZZ","KRK"],["GDN","KRK"],["KRK","TFS"],["IEG","WRO"]],
                               "wizzair": [["WRO","TFS"]], "binter": []}}
        found = discover_candidates(snapshot)
        krk = next(r for r in found["step3"] if r.iata == "KRK")
        self.assertEqual(set(krk.polish_airports), {"SZZ", "GDN"})
        self.assertEqual(next(r for r in found["step5_variant_b"] if r.iata == "WRO").polish_airports, ("IEG",))

    def test_current_verified_routes_not_copied_to_inactive_ieg(self):
        self.assertEqual({r["iata"] for r in collect_step3.load_allowlist()["airports"] if "SZZ" in r["polish_airports"]}, {"DUB","KRK","LPL","STN"})
        krk = next(r for r in collect_step3.load_allowlist()["airports"] if r["iata"] == "KRK")
        self.assertEqual(set(krk["polish_airports"]), {"GDN","SZZ"})
        gdn = next(r for r in collect_step5.load_allowlist()["variants"][collect_step5.VARIANT_B]["airports"] if r["iata"] == "GDN")
        self.assertEqual(set(gdn["polish_airports"]), {"KRK","LUZ","WRO"})
        for step in ("3","4","5"):
            module = importlib.import_module("scripts.collect_step"+step)
            config = module.load_allowlist()
            groups = [config["airports"]] if step != "5" else [v["airports"] for v in config["variants"].values()]
            self.assertFalse(any("IEG" in row["polish_airports"] for group in groups for row in group))

    def test_full_independent_calendars_and_old_coverage_cannot_certify_new_scope(self):
        days = {(START + timedelta(days=n)).isoformat() for n in range(31)}
        plans = {s: expected_queries(s, START, END) for s in ("1","1b","2","3","4","5")}
        self.assertEqual(len(plans["2"]), 120*31)
        for code in ("SZZ","IEG"):
            for step, hubs in (("1", ("FUE","LPA","MAD","PMI","SVQ","VLC")), ("1b",("MAD",)), ("2",("TFN","TFS"))):
                for carrier in ("Ryanair","Wizz Air"):
                    for hub in hubs:
                        for a,b in ((code,hub),(hub,code)):
                            self.assertEqual({day for c,o,d,day,k in plans[step] if (c,o,d)==(carrier,a,b)}, days)
        for a,b in (("SZZ","KRK"),("KRK","SZZ"),("GDN","KRK"),("KRK","GDN"),("TFS","KRK"),("KRK","TFS")):
            self.assertEqual({day for c,o,d,day,k in plans["3"] if (o,d)==(a,b)}, days)
        for subset in (set(THIRTEEN), set(POLISH_AIRPORTS)-{"IEG"}, set(POLISH_AIRPORTS)-{"SZZ"}):
            plan = {q for q in plans["2"] if set(q[1:3]) & subset}
            tracker = Coverage("2",START,END,plan,"incomplete")
            for c,o,d,day,k in plan:
                tracker.record(c,o,d,date.fromisoformat(day),date.fromisoformat(day),[],"google_flights_http" if c=="Ryanair" else "timetableV2")
            with self.assertRaises(RuntimeError): validate_coverage({"collection_coverage":tracker.verify()},"2",START,END)

    def test_all_six_resident_builders_preserve_frozen_thirteen(self):
        for step, carrier in (("1","Binter"),("1b","Iberia"),("1c","Vueling"),("1d","Air Europa"),("1e","Volotea"),("1f","Canaryfly")):
            module = importlib.import_module("scripts.collect_step"+step)
            low = []
            for n,p in enumerate(POLISH_AIRPORTS):
                low += [leg("Ryanair",p,"2026-11-01T06:00:00+01:00","MAD","2026-11-01T09:00:00+01:00",f"FR{n}"),
                        leg("Ryanair","MAD","2026-11-02T16:00:00+01:00",p,"2026-11-02T19:00:00+01:00",f"FR{n+30}")]
            resident = [leg(carrier,"MAD","2026-11-01T12:00:00+01:00","TFN","2026-11-01T14:00:00+00:00"),
                        leg(carrier,"TFN","2026-11-02T08:00:00+00:00","MAD","2026-11-02T12:00:00+01:00")]
            after = module.build_connections(low,resident)
            for code in ("SZZ","IEG"):
                self.assertEqual({r["direction"] for r in after if code in (r["origin_airport"],r["destination_airport"])}, {"poland_to_tenerife","tenerife_to_poland"})
            with patch.object(module,"POLISH_AIRPORTS",THIRTEEN):
                before = module.build_connections([r for r in low if set((r["departure_airport"],r["arrival_airport"])) & set(THIRTEEN)], resident)
            self.assertEqual(before,[r for r in after if set((r["origin_airport"],r["destination_airport"])) & set(THIRTEEN)])

    def test_direct_and_four_transfer_builders_preserve_frozen_thirteen(self):
        for module,hub,a,b,variant in ((collect_step3,"DUB","Ryanair","Ryanair",None),
                (collect_step4,"FCO","Wizz Air","Wizz Air",None),
                (collect_step5,"LTN","Ryanair","Wizz Air",collect_step5.VARIANT_A),
                (collect_step5,"MXP","Wizz Air","Ryanair",collect_step5.VARIANT_B)):
            config=copy.deepcopy(module.load_allowlist())
            group=config["airports"] if variant is None else config["variants"][variant]["airports"]
            next(r for r in group if r["iata"]==hub)["polish_airports"]=list(POLISH_AIRPORTS)
            legs=[leg(a,"TFS","2026-11-01T06:00:00+00:00",hub,"2026-11-01T10:00:00+01:00","XX0"),
                  leg(a,hub,"2026-11-02T12:00:00+01:00","TFS","2026-11-02T15:00:00+00:00","XX1")]
            for n,p in enumerate(POLISH_AIRPORTS):
                legs += [leg(b,hub,"2026-11-01T13:00:00+01:00",p,"2026-11-01T16:00:00+01:00",f"XX{n+2}"),
                         leg(b,p,"2026-11-02T06:00:00+01:00",hub,"2026-11-02T09:00:00+01:00",f"XX{n+30}")]
            after=module.build_connections(legs,config,4.0)
            previous=copy.deepcopy(config)
            groups=[previous["airports"]] if variant is None else [v["airports"] for v in previous["variants"].values()]
            for group in groups:
                for row in group: row["polish_airports"]=[p for p in row["polish_airports"] if p in THIRTEEN]
            with patch.object(module,"POLISH_AIRPORTS",THIRTEEN):
                before=module.build_connections([r for r in legs if not set((r["departure_airport"],r["arrival_airport"])) & {"SZZ","IEG"}],previous,4.0)
            self.assertEqual(before,[r for r in after if not set((r["origin_airport"],r["destination_airport"])) & {"SZZ","IEG"}])
        direct=[leg("Ryanair",p,"2026-11-01T08:00:00+01:00","TFS","2026-11-01T13:00:00+00:00",f"FR{n}") for n,p in enumerate(POLISH_AIRPORTS)]
        with patch.object(collect_step2,"POLISH_AIRPORTS",THIRTEEN):
            before=collect_step2.build_results([r for r in direct if r["departure_airport"] in THIRTEEN])
        self.assertEqual(before,[r for r in collect_step2.build_results(direct) if r["origin_airport"] in THIRTEEN])


if __name__ == "__main__": unittest.main()
