"""Iteration 22: the global impact layer's builder, gate and import.

The layer is a second, non-scored corpus (docs/GLOBAL_IMPACT_METHODOLOGY.md). These tests hold the
three things that make it safe to publish:

  * THE GATE refuses, naming the record, everything methodology §13 lists. Each refusal is shown
    with one valid fixture record changed in exactly one way, so a rule that stops firing is seen.
  * THE BUILD is deterministic, serves attempts apart from disruptions, orders nothing by a figure,
    carries no figure per country, and is reachable from no analytic module.
  * THE IMPORT (scripts/import_impacts.py) is the one way in: every blind role accepted, patches in
    role order with safety last, attacks abstracted under a keyed id, duplicates and records held
    from a country system refused, first_published stamped once.

Every record used here is SYNTHETIC (tests/fixtures/impacts22). The import tests run against a
temporary queue: the real one is local, never committed and never read by a test.
"""
import ast
import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

from pipeline import artifacts, build_systems as B, evidence_confidence as EC, global_impacts as G, systems

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "impacts22"
WORLD = ROOT / "data" / "processed" / "global" / "world.geojson"
AS_OF = "2026-11-19"
KEY = b"test-key-not-the-real-one"
# Unit names for the campaign systems, injected so no test needs the Natural Earth cache.
UNIT_NAMES = {"ir": ["khuzestan", "tehran", "bushehr"], "iq": ["basrah", "al basrah", "kurdistan"],
              "sa": ["eastern province"], "ae": ["abu dhabi"], "bh": [], "kw": [], "om": [], "qa": []}

FRA = "imp-2025-03-05-fra-electricity-synthetic-grid-ransomware"
POL = "imp-2024-11-18-pol-telecom-synthetic-network-outage"
ITA = "imp-2025-06-10-ita-water-synthetic-utility-intrusion"
DEU = "imp-2025-09-02-deu-healthcare-synthetic-hospital-it-outage"
USA = "imp-2026-02-14-usa-fuel_supply-synthetic-payment-outage"
JPN = "imp-2026-05-20-jpn-transport-synthetic-dispatch-failure"
UKR = "imp-2025-10-08-ukr-electricity-attack-3fa91c"
BRA = "imp-2024-07-22-bra-electricity-synthetic-storm-blackout"
NLD = "imp-2026-01-09-nld-water-synthetic-attempt"
IRN = "imp-2024-08-irn-electricity-synthetic-heat-shortfall"
KAZ = "imp-2023-01-16-kaz-district_energy-synthetic-heating-failure"
RUS = "imp-2024-01-04-rus-district_energy-synthetic-heating-pipe"
MULTI = "imp-2025-04-28-multi-electricity-synthetic-grid-separation"


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ctx():
    return G.load_context(WORLD, unit_names=copy.deepcopy(UNIT_NAMES),
                          link_states=_json(FIXTURE / "link_health.json")["link_states"])


def docs():
    return copy.deepcopy(G.load_curated(FIXTURE))


def rec(impact_id):
    return copy.deepcopy(next(r for r in _json(FIXTURE / "events.json")["records"] if r["impact_id"] == impact_id))


def entry(n=0):
    return copy.deepcopy(_json(FIXTURE / "regional_context.json")["entries"][n])


def problems(record):
    return G.one_record_problems(record, ctx())


def refused(record, text):
    got = problems(record)
    assert any(text in p for p in got), f"expected a refusal containing {text!r}, got {got}"


def payloads(as_of=AS_OF, events=None, context=None, log=None):
    e, c, lg = docs()
    return G.build_payloads(events or e, context or c, log or lg, ctx(), as_of)


# --- the fixture is valid, synthetic and exercises every branch ---------------------------------------

def test_the_fixture_passes_the_gate_and_every_record_says_it_is_synthetic():
    e, c, lg = docs()
    assert G.gate(e, c, lg, ctx()) == []
    assert 12 <= len(e["records"]) <= 16 and len(c["entries"]) == 6
    for r in e["records"]:
        assert "SYNTHETIC" in r["summary"], r["impact_id"]
        assert all(".example/" in s["url"] and s["publisher"].startswith("Example") for s in r["sources"])
    assert all("SYNTHETIC" in x["claim"] for x in c["entries"])


def test_the_fixture_exercises_every_branch_the_frontend_must_draw():
    records = _json(FIXTURE / "events.json")["records"]
    statuses = {r["attribution"]["status"] for r in records}
    assert statuses == set(EC.ATTRIBUTION_STATUSES)
    assert {r["ai_involvement"]["relation"] for r in records} >= set(EC.AI_RELATIONS)
    tiers = {s["social"]["account_tier"] for r in records for s in r["sources"] if s["medium"] == "social"}
    assert {"S1", "S4"} <= tiers
    assert any(r["publication_policy"] == G.ABSTRACTED for r in records)
    assert any(r["dispute"] for r in records) and any(r["record_kind"] == G.ATTEMPT for r in records)
    assert any(r["country_a3"] == "IRN" for r in records)          # a system under the campaign policy
    assert any(r["technology"] in G.ABSENCE for r in records) and any(r["technology"] is None for r in records)
    served = payloads()[G.IMPACTS_OUT]
    categories = {r["evidence_confidence"]["category"] for r in served["records"] + served["attempts"]}
    assert categories == {"HIGH", "MODERATE", "LIMITED", "PRELIMINARY", "DISPUTED"}
    assert {r["digital_category"] for r in served["records"]} == {"cyber", "it_failure", None}


def test_every_reject_case_in_the_fixture_is_refused_for_its_stated_reason():
    cases = _json(FIXTURE / "rejects.json")["cases"]
    assert len(cases) >= 2
    for case in cases:
        refused(case["record"], case["expect"])


# --- the gate: coordinates ------------------------------------------------------------------------------

def test_gate_refuses_a_coordinate_like_key_anywhere():
    r = rec(FRA)
    r["sources"][0]["lat"] = 48.85
    refused(r, "coordinate-like key")
    r = rec(FRA)
    r["civilian_service_impact"][0]["affected"]["centroid"] = "x"
    refused(r, "coordinate-like key")
    # A key is read by token: "relation" and "is_latest_of_type" are not "lat".
    assert G.coordinate_problems({"relation": "x", "is_latest_of_type": True, "regulator": 1}) == []


def test_gate_refuses_a_number_pair_that_reads_as_a_position():
    r = rec(FRA)
    r["civilian_service_impact"][0]["affected"]["value"] = [48.8566, 2.3522]
    refused(r, "reads as a position")
    r = rec(FRA)
    r["civilian_service_impact"][0]["affected"]["value"] = ["48.8566", "2.3522"]
    refused(r, "reads as a position")
    assert any("side by side" in p for p in G.coordinate_problems({"a": 48.8566, "b": 2.3522}))


@pytest.mark.parametrize("text", ["near 48.8566, 2.3522 on the map", "at 48.857 N", "34°N of the line", "lat 48.85",
                                  "see https://maps.google.com/?q=1"])
def test_gate_refuses_coordinate_text_and_map_links(text):
    r = rec(FRA)
    r["summary"] += " " + text
    refused(r, "coordinate or map-link text")


def test_a_temperature_is_not_a_coordinate():
    r = rec(BRA)
    r["effect"] += " Temperatures reached 45 °C."
    assert not any("coordinate" in p for p in problems(r))


# --- the gate: attacks are the country's ------------------------------------------------------------------

def test_gate_refuses_a_kinetic_or_sabotage_record_that_is_not_abstracted():
    r = rec(UKR)
    r["publication_policy"] = "standard"
    refused(r, "must be country_abstracted")
    r = rec(BRA)
    r["cause_family"] = "sabotage"
    r["attribution"] = {**r["attribution"], "status": "UNKNOWN"}
    refused(r, "must be country_abstracted")
    # A contributing factor that is an attack makes the record an attack record too.
    r = rec(BRA)
    r["contributing_factors"] = ["kinetic"]
    refused(r, "must be country_abstracted")


def test_gate_refuses_a_region_on_an_abstracted_record():
    r = rec(UKR)
    r["admin1"] = {"code": "UA-30", "name": "Kyiv"}
    r["geographic_precision"] = "admin1"
    refused(r, "never carries a region")
    refused(r, "published for the country only")


def test_gate_refuses_a_headline_on_an_abstracted_record():
    for key in ("title_original", "title_en"):
        r = rec(UKR)
        r["sources"][0][key] = "Synthetic headline"
        refused(r, "a headline on a record published without its place")


def test_gate_refuses_method_wording_on_an_abstracted_record_and_in_its_addresses():
    r = rec(UKR)
    r["summary"] = "SYNTHETIC FIXTURE. A drone attack damaged electricity infrastructure in Ukraine."
    refused(r, "how an attack was carried out")
    r = rec(UKR)
    r["sources"][0]["url"] = "https://newsroom.example/synthetic/missile-attack-on-grid"
    refused(r, "citation address states how the attack was carried out")
    # "strikes" is not in the country systems' method list (a labour strike is no leak there); on a
    # record published without its method it is one.
    for slug in ("power-outages-after-strikes-on-grid", "grid-struck-overnight", "explosion-at-substation"):
        r = rec(UKR)
        r["sources"][0]["url"] = f"https://newsroom.example/synthetic/{slug}/123.html"
        refused(r, "citation address states how the attack was carried out")


def test_gate_refuses_status_wording_on_an_abstracted_record_and_in_its_addresses():
    r = rec(UKR)
    r["effect"] = "SYNTHETIC FIXTURE. Power was restored within two days."
    refused(r, "status wording on an abstracted record")
    r = rec(UKR)
    r["sources"][1]["url"] = "https://newsroom.example/synthetic/plant-back-online-after-repair"
    refused(r, "citation address carries status wording")
    r = rec(UKR)
    r["date_end"] = "2025-10-10"
    refused(r, "no end date")


@pytest.mark.parametrize("bad", ["imp-2025-10-08-ukr-electricity-attack-2", "imp-2025-10-08-ukr-electricity-attack-kyivgrid",
                                 "imp-2025-10-08-ukr-electricity-synthetic-kyiv-substation",
                                 "imp-2025-10-08-ukr-electricity-attack-3FA91C"])
def test_gate_refuses_an_abstracted_id_that_is_not_the_keyed_form(bad):
    r = rec(UKR)
    r["impact_id"] = bad
    refused(r, "six hex digits")


def test_a_reviewer_may_abstract_any_record_and_the_same_rules_then_apply():
    r = rec(BRA)
    r["publication_policy"] = G.ABSTRACTED
    r["impact_id"] = "imp-2024-07-22-bra-electricity-event-0a1b2c"
    for s in r["sources"]:
        s.pop("title_en", None)
        s.pop("title_original", None)
    assert problems(r) == []
    # "attack" in the id would assert a cause the record does not state; a headline is still refused.
    r["impact_id"] = "imp-2024-07-22-bra-electricity-attack-0a1b2c"
    refused(r, "an abstracted record's id is imp-2024-07-22-bra-electricity-event-")
    r["sources"][0]["title_en"] = "Synthetic headline"
    refused(r, "a headline on a record published without its place")


# --- the gate: systems under the campaign policy ----------------------------------------------------------

def test_gate_refuses_a_region_on_any_record_in_a_campaign_system():
    r = rec(IRN)
    r["admin1"] = {"code": "IR-06", "name": "Bushehr"}
    r["geographic_precision"] = "admin1"
    refused(r, "campaign-restricted system (ir) carries a region")


def test_gate_refuses_a_campaign_systems_region_name_in_text_or_id():
    r = rec(IRN)
    r["summary"] += " The cuts were longest in Khuzestan."
    refused(r, "names a region of a campaign-restricted system (ir)")
    r = rec(IRN)
    r["impact_id"] = "imp-2024-08-irn-electricity-synthetic-tehran-cuts"
    refused(r, "names a region of a campaign-restricted system (ir)")
    # A multi-country record that includes a campaign system is under the same rule.
    r = rec(MULTI)
    r["countries_a3"] = ["PRT", "IRQ"]
    r["summary"] += " Basrah was affected."
    refused(r, "names a region of a campaign-restricted system (iq)")


def test_gate_refuses_a_headline_in_a_campaign_system():
    r = rec(IRN)
    r["sources"][0]["title_en"] = "Synthetic headline"
    refused(r, "campaign-restricted system (ir) carries a headline")


def test_the_campaign_classification_is_the_country_systems_own():
    states = B.load_campaigns()["system_states"]
    want = {sid for sid in systems.COUNTRY_SYSTEMS if (states.get(sid) or {}).get("state") in B.RESTRICTING_STATES}
    assert ctx()["restricted"] == want and "ir" in want and "us" not in want
    assert G.restricted_systems(rec(IRN), ctx()) == ["ir"] and G.restricted_systems(rec(USA), ctx()) == []


def test_unit_names_fold_articles_and_spare_the_countrys_own_name():
    got = G.name_phrases(["Al-Basrah", "Dhī Qār", "Kuwait"], exclude=("Kuwait",))
    assert got == ["al basrah", "basrah", "dhi qar"]
    assert G.names_in("An outage in Basrah, and in DHI-QAR.", got) == ["basrah", "dhi qar"]
    assert G.names_in("Nothing here names a place.", got) == []


@pytest.mark.skipif(not (ROOT / "data" / "raw" / "ne_10m_admin_1.geojson").exists(), reason="needs the Natural Earth cache")
def test_real_unit_names_are_read_from_the_same_rows_as_the_country_import():
    names = G.system_unit_phrases("iq")
    assert {"basrah", "erbil", "arbil", "kurdistan"} <= set(names)
    assert "iraq" not in names


# --- the gate: route, maritime, technical and loaded wording ------------------------------------------------

@pytest.mark.parametrize("text", ["A tanker was delayed.", "Traffic through the Strait fell.", "A bypass was used.",
                                  "Vessels waited offshore."])
def test_gate_refuses_route_wording_anywhere_in_an_impact_record(text):
    r = rec(FRA)
    r["effect"] += " " + text
    refused(r, "shipping, strait or route wording")


def test_gate_refuses_route_wording_in_a_citation_address_or_headline():
    r = rec(FRA)
    r["sources"][0]["url"] = "https://utility.example/synthetic/hormuz-shipping-update"
    refused(r, "shipping, strait or route wording")
    r = rec(FRA)
    r["sources"][0]["title_en"] = "Synthetic headline about tankers"
    refused(r, "shipping, strait or route wording")


CONTEXT_FORBIDDEN = [
    "The vessel IMO 9321483 was delayed.", "MMSI data showed fewer transits.", "AIS data showed fewer transits.",
    "Vessel-tracking firms reported fewer transits.", "Exports could bypass the strait.", "An alternate route was used.",
    "Cargoes were rerouted.", "Pipeline capacity could replace some transits.", "The country depends on the strait.",
    "Its dependence on the strait is high.", "The strait is a chokepoint.", "Ships sailed under escort.",
    "A convoy crossed the strait.", "Naval forces were deployed.", "A warship was nearby.", "Mines were reported.",
    "Loadings at Ras Tanura fell.", "The port of Example closed.", "MT Example Star was delayed.",
    "Port vulnerability was discussed.", "Fujairah loadings rose.",
]


@pytest.mark.parametrize("text", CONTEXT_FORBIDDEN)
def test_context_gate_refuses_vessel_route_port_dependence_and_naval_wording(text):
    e = entry()
    e["claim"] += " " + text
    assert any("aggregate only" in p for p in G.context_problems([e])), text


@pytest.mark.parametrize("text", [
    "Shipping through the Strait of Hormuz was restricted, in aggregate.", "Transit traffic fell.",
    "Crude exports and LNG cargoes were lower in aggregate.", "Tanker traffic was below its usual level.",
    "The benchmark price rose 20 mt-equivalent is not stated."])
def test_context_gate_allows_the_aggregate_words(text):
    e = entry()
    e["claim"] = "SYNTHETIC. " + text
    assert G.context_problems([e]) == []


def test_context_gate_refuses_weapon_wording_and_a_leaking_address():
    e = entry()
    e["claim"] += " A missile was fired."
    assert any("weapon or method wording" in p for p in G.context_problems([e]))
    e = entry()
    e["sources"][0]["url"] = "https://maritime-agency.example/synthetic/jebel-ali-update"
    assert any("aggregate only" in p for p in G.context_problems([e]))


@pytest.mark.parametrize("text,why", [
    ("The server at 192.168.10.4 was reached.", "an IP address"),
    ("Traffic came from 2001:0db8:85a3:0000:0000:8a2e:0370:7334.", "an IP address"),
    ("The flaw is CVE-2024-12345.", "a CVE identifier"),
    ("Attackers exploited a vulnerability in the billing system.", "exploit or access-method wording"),
    ("The device used a default password.", "exploit or access-method wording"),
    ("Stolen credentials were used.", "exploit or access-method wording"),
    ("The service listened on port 502.", "exploit or access-method wording"),
    ("The Modbus interface was reachable.", "exploit or access-method wording"),
    ("It ran firmware version 2.1.", "exploit or access-method wording"),
    ("A Unitronics PLC was changed.", "exploit or access-method wording"),
    ("The exposed controller model was listed.", "exploit or access-method wording"),
    ("They gained access through a remote login.", "exploit or access-method wording"),
])
def test_gate_refuses_ip_addresses_cve_identifiers_and_exploit_wording(text, why):
    r = rec(FRA)
    r["summary"] += " " + text
    refused(r, why)


def test_technical_checks_read_addresses_for_ip_and_cve_but_not_for_prose_patterns():
    r = rec(FRA)
    r["sources"][0]["url"] = "https://utility.example/synthetic/port-2024-outage"
    assert not any("exploit" in p for p in problems(r))
    r["sources"][0]["url"] = "https://utility.example/advisory/cve-2024-12345"
    refused(r, "a CVE identifier")
    # A broad mechanism is allowed; it is how access was gained that is not.
    assert not any("exploit" in p for p in problems(rec(FRA)))


IMPORTANCE_REFUSED = [
    "the country's largest utility", "the biggest outage in years", "the sole supplier of the region", "a strategic reserve",
    "a vital service", "a key substation failed", "the main power plant tripped", "the only hospital in the district",
    "the only working pump failed", "the most important node", "a critical pipeline", "a major refinery",
    "the backbone of the grid"]
IMPORTANCE_ALLOWED = [
    "Critical infrastructure operators were notified.", "A water main burst.", "A feeder main failed.",
    "A major storm crossed the coast.", "It was a major outage.", "A major incident was declared.",
    "The only source says so.", "Only 40 customers were affected.", "The main reason is not stated.",
    "One patient was in critical condition."]


@pytest.mark.parametrize("text", IMPORTANCE_REFUSED)
def test_gate_refuses_a_claim_of_an_assets_size_or_importance(text):
    for field in ("summary", "effect"):
        r = rec(FRA)
        r[field] += " " + text
        refused(r, "claims an asset's size or importance")


@pytest.mark.parametrize("text", IMPORTANCE_ALLOWED)
def test_the_importance_gate_allows_words_that_say_nothing_about_an_asset(text):
    for field in ("summary", "effect"):
        r = rec(FRA)
        r[field] += " " + text
        assert problems(r) == []


def test_the_importance_words_are_data_and_the_blunt_country_pattern_is_not_used_here():
    words = G.TAXONOMY["importance_wording"]
    assert {"largest", "biggest", "sole", "strategic", "vital", "most important"} <= set(words["always"])
    assert set(words["before_asset_noun"]) == {"key", "main", "major", "critical"}
    assert {"critical infrastructure", "water main", "feeder main", "major storm", "major outage", "major disruption",
            "major incident"} <= set(words["allow_phrases"])
    assert "source" not in words["asset_nouns"] and words["only_within_words"] == 3
    src = (ROOT / "pipeline" / "global_impacts.py").read_text(encoding="utf-8")
    assert "LOADED_WORDING.search" not in src and '"largest"' not in src


@pytest.mark.parametrize("text", ["Water was delivered by tanker truck.", "Water tankers supplied the district.",
                                  "Tanker trucks brought drinking water."])
def test_a_road_tanker_delivering_water_is_not_shipping(text):
    r = rec(FRA)
    r["effect"] += " " + text
    assert problems(r) == []
    assert G.TAXONOMY["route_wording_allowed"]["phrases"] == ["water tanker", "water tankers", "tanker truck", "tanker trucks"]


@pytest.mark.parametrize("text", ["A water tanker and an oil tanker waited.", "Tankers queued.", "A tanker was diverted."])
def test_every_other_tanker_is_still_refused(text):
    r = rec(FRA)
    r["effect"] += " " + text
    refused(r, "shipping, strait or route wording")


def test_an_undated_page_is_cited_with_no_date_only_when_it_says_so_and_earns_nothing_for_timeliness():
    base = rec(BRA)
    assert G.serve_record(base, ctx())["evidence_confidence"]["components"]["contemporaneous"]["points"] > 0
    r = rec(BRA)
    r["sources"][1]["date"] = None
    refused(r, "source 's2': no date")
    r["sources"][1]["date_basis"] = "undated_page"
    assert problems(r) == []
    served = G.serve_record(r, ctx())
    assert served["sources"][1]["date"] is None and served["sources"][1]["date_basis"] == "undated_page"
    # Undated earns nothing for "reported at the time": with every source undated the points are gone.
    r["sources"][0].update({"date": None, "date_basis": "undated_page"})
    assert problems(r) == []
    assert G.serve_record(r, ctx())["evidence_confidence"]["components"]["contemporaneous"]["points"] == 0
    # A dated source may not also claim to be undated; no other basis exists; a post is never undated.
    for change, why in (({"date": "2024-07-25", "date_basis": "undated_page"}, "date_basis 'undated_page' goes only with a null date"),
                        ({"date": None, "date_basis": "date_unknown"}, "date_basis 'date_unknown'"),
                        ({"date": "", "date_basis": "undated_page"}, "no date")):
        r = rec(BRA)
        r["sources"][1].update(change)
        refused(r, why)
    r = rec(POL)
    r["sources"][1].update({"date": None, "date_basis": "undated_page"})
    assert r["sources"][1]["medium"] == "social"
    refused(r, "never on a social post")
    out = payloads()
    labels = {v["id"] for v in out[G.IMPACTS_OUT]["vocabularies"]["source_date_bases"]}
    assert labels == {"undated_page"} and "source_date_bases" in out[G.CONTEXT_OUT]["vocabularies"]
    # The same rule holds for a regional-context source.
    e = entry()
    e["sources"][0]["date"] = None
    assert any("no date" in p for p in G.context_problems([e]))
    e["sources"][0]["date_basis"] = "undated_page"
    assert G.context_problems([e]) == []


def test_the_review_block_may_state_a_lead_normalisation_only_with_its_date():
    r = rec(FRA)
    r["review"].update({"lead_normalisation": True, "lead_normalisation_at": "2026-11-21"})
    assert problems(r) == []
    assert G.serve_record(r, ctx())["review"]["lead_normalisation"] is True
    for bad in ({"lead_normalisation": True}, {"lead_normalisation_at": "2026-11-21"},
                {"lead_normalisation": False, "lead_normalisation_at": "2026-11-21"},
                {"lead_normalisation": True, "lead_normalisation_at": "soon"}, {"lead_normalisation": "yes", "lead_normalisation_at": "2026-11-21"}):
        r = rec(FRA)
        r["review"].update(bad)
        refused(r, "review.lead_normalisation is true beside the date")
    e = entry()
    e["review"].update({"lead_normalisation": True, "lead_normalisation_at": "2026-11-21"})
    assert G.context_problems([e]) == []
    e["review"]["lead_normalisation_at"] = None
    assert any("review.lead_normalisation" in p for p in G.context_problems([e]))
    # The lead is never one of the roles.
    r = rec(FRA)
    r["review"]["roles"]["lead"] = "accept_with_correction"
    refused(r, "are not roles of this review")


# --- the gate: claims and sources ---------------------------------------------------------------------------

def test_gate_refuses_a_record_with_no_source_for_occurrence():
    r = rec(DEU)
    for s in r["sources"]:
        s["supports"] = [c for c in s["supports"] if c != "occurrence"] or ["effect"]
    refused(r, "no source supports occurrence")


def test_gate_refuses_a_stated_effect_with_no_source_for_it():
    r = rec(DEU)
    for s in r["sources"]:
        s["supports"] = [c for c in s["supports"] if c != "effect"]
    r["civilian_service_impact"] = []
    refused(r, "no source supports effect")
    r["effect_specificity"] = "vague"
    assert not any("no source supports effect" in p for p in problems(r))


def test_gate_refuses_an_attribution_its_sources_do_not_support():
    r = rec(FRA)
    r["sources"] = [s for s in r["sources"] if s["ref"] != "s3"]      # the government source
    r["attribution"]["source_refs"] = ["s4"]
    refused(r, "ATTRIBUTED needs a formal government or law-enforcement attribution")
    r = rec(POL)
    r["attribution"]["source_refs"] = []
    for s in r["sources"]:
        s["supports"] = [c for c in s["supports"] if c != "attribution"]
    refused(r, "with no source that supports attribution")
    # The rule, not its sentence: a record whose only attribution source is the actor's own claim
    # stands as CLAIMED and is refused as anything firmer, and the gate carries the model's refusal.
    r = rec(ITA)
    assert EC.attribution_problems(r["attribution"], r["sources"]) == []
    assert EC.attribution_confidence(r["attribution"], r["sources"]) == "CLAIM_ONLY"
    for firmer in ("SUSPECTED", "ASSESSED", "ATTRIBUTED"):
        r["attribution"]["status"] = firmer
        said = EC.attribution_problems(r["attribution"], r["sources"])
        assert said, firmer
        assert set(said) <= set(problems(r)), firmer


def test_gate_refuses_an_ai_status_without_an_incident_source_or_a_relation():
    r = rec(USA)
    for s in r["sources"]:
        s["supports"] = [c for c in s["supports"] if c != "ai_involvement"] or ["occurrence"]
    r["ai_involvement"]["source_refs"] = []
    refused(r, "no source that ties AI to this incident")
    r = rec(USA)
    r["ai_involvement"]["relation"] = None
    refused(r, "needs a relation")
    # Assistance and operational cause are never merged: a role belongs to one of them.
    r = rec(USA)
    r["ai_involvement"]["relation"] = "ai_operational_cause"
    refused(r, "never merged")
    r = rec(USA)
    r["review"]["ai_check"] = "not_applicable"
    refused(r, "review.ai_check")


def test_gate_refuses_a_cited_ref_that_names_no_source_or_the_wrong_claim():
    r = rec(FRA)
    r["civilian_service_impact"][0]["source_refs"] = ["s9"]
    refused(r, "name no source")
    r = rec(FRA)
    r["attribution"]["source_refs"] = ["s1"]
    refused(r, "is cited for attribution but does not support it")


def test_gate_refuses_a_social_source_without_tier_or_identity_basis():
    r = rec(POL)
    r["sources"][1]["social"]["account_tier"] = None
    refused(r, "needs an account tier")
    r = rec(POL)
    r["sources"][1]["social"]["identity_basis"] = " "
    refused(r, "needs identity_basis")
    r = rec(POL)
    r["sources"][1]["social"] = None
    refused(r, "needs its account")
    r = rec(POL)
    r["review"]["social_check"] = "not_applicable"
    refused(r, "review.social_check")


@pytest.mark.parametrize("tier", ["S2", "S3", "S4"])
def test_gate_refuses_an_unofficial_post_as_the_sole_evidence_of_occurrence(tier):
    r = rec(POL)
    r["sources"] = [r["sources"][1]]
    r["sources"][0]["social"]["account_tier"] = tier
    r["attribution"] = rec(USA)["attribution"]
    r["civilian_service_impact"][0]["source_refs"] = ["s2"]
    refused(r, "only evidence of occurrence")


def test_an_official_account_may_stand_alone_and_a_weak_post_may_stand_beside_a_real_source():
    r = rec(POL)
    r["sources"] = [r["sources"][1]]
    r["attribution"] = rec(USA)["attribution"]
    r["civilian_service_impact"][0]["source_refs"] = ["s2"]
    assert not any("only evidence" in p for p in problems(r))
    assert not any("only evidence" in p for p in problems(rec(ITA)))


# --- the gate: figures, absences, vocabularies ---------------------------------------------------------------

def test_gate_refuses_a_value_without_a_unit_or_without_the_sources_words():
    r = rec(FRA)
    r["civilian_service_impact"][0]["affected"]["unit"] = None
    refused(r, "a value without a unit")
    r = rec(FRA)
    r["civilian_service_impact"][0]["affected"]["source_says"] = None
    refused(r, "a value without the source's own words")
    r = rec(FRA)
    r["civilian_service_impact"][0]["affected"]["qualifier"] = "roughly"
    refused(r, "qualifier 'roughly'")


def test_gate_refuses_an_absence_written_as_zero_or_as_an_empty_string():
    r = rec(POL)
    r["civilian_service_impact"][0]["affected"]["value"] = 0
    refused(r, "never zero")
    r = rec(POL)
    r["civilian_service_impact"][0]["duration_text"] = ""
    refused(r, "an empty string")
    # The served record keeps a null a null.
    served = next(x for x in payloads()[G.IMPACTS_OUT]["records"] if x["impact_id"] == POL)
    assert served["civilian_service_impact"][0]["affected"]["value"] is None
    assert served["technology"] is None and served["date_end"] is None


def test_null_means_not_applicable_and_unknown_is_written_as_a_word():
    r = rec(FRA)
    r["technology"] = None
    refused(r, "an energy record names a technology or says why not")
    r["technology"] = "unknown"
    assert not any("technology" in p for p in problems(r))
    r = rec(POL)
    r["technology"] = "distribution"
    refused(r, "technology is null (not applicable) outside energy")
    r = rec(FRA)
    r["cyber_mechanism"] = None
    refused(r, "a cyber record names a broad mechanism")
    r = rec(BRA)
    r["cyber_mechanism"] = "ransomware"
    refused(r, "cyber_mechanism is null (not applicable) when no cause is cyber")


def test_an_it_failure_is_the_one_mechanism_on_a_record_that_is_not_cyber():
    assert problems(rec(JPN)) == []
    r = rec(JPN)
    r["cause_family"] = "natural_hazard"
    refused(r, "the one exception is it_outage_affecting_operations on an industrial_technical record")
    r = rec(JPN)
    r["attribution"] = rec(USA)["attribution"]
    assert any("NOT_APPLICABLE" in p for p in problems(r))
    assert G.digital_category(rec(JPN)) == "it_failure" and G.digital_category(rec(FRA)) == "cyber"
    assert G.digital_category(rec(BRA)) is None


VOCAB_CASES = [
    ("record_kind", "incident", "record_kind"), ("date_precision", "week", "date_precision"),
    ("geographic_precision", "city", "geographic_precision"), ("domain", "defence", "domain"),
    ("sector", "ports", "sector"), ("cause_family", "kinetic_strike", "cause_family"),
    ("effect_specificity", "exact", "effect_specificity"), ("inclusion_basis", 7, "inclusion_basis"),
    ("publication_policy", "open", "publication_policy"), ("contributing_factors", ["weather"], "contributing_factors"),
    ("technology", "nuclear", "technology"), ("cyber_mechanism", "phishing", "cyber_mechanism"),
]


@pytest.mark.parametrize("field,value,why", VOCAB_CASES)
def test_gate_refuses_a_value_outside_its_vocabulary(field, value, why):
    r = rec(FRA)
    r[field] = value
    refused(r, why)


@pytest.mark.parametrize("path,value,why", [
    (("sources", 0, "source_role"), "blogger", "source_role"), (("sources", 0, "medium"), "tv", "medium"),
    (("sources", 0, "supports"), ["severity"], "supports"), (("sources", 0, "opened"), None, "opened must be true or false"),
    (("attribution", "status"), "PROVEN", "attribution status"), (("attribution", "actor_type"), "terrorist", "actor_type"),
    (("attribution", "basis"), ["rumour"], "attribution basis"), (("ai_involvement", "status"), "LIKELY", "ai_involvement status"),
    (("civilian_service_impact", 0, "service"), "banking", "is not a sector"),
    (("civilian_service_impact", 0, "geographic_scope"), "citywide", "geographic_scope"),
    (("review", "disposition"), "waved through", "review disposition"),
])
def test_gate_refuses_a_nested_value_outside_its_vocabulary(path, value, why):
    r = rec(FRA)
    cur = r
    for p in path[:-1]:
        cur = cur[p]
    cur[path[-1]] = value
    refused(r, why)


@pytest.mark.parametrize("key", ["rationale", "rank", "severity_score", "operator", "facility_name", "shelf_life_days"])
def test_gate_refuses_a_field_that_is_not_part_of_the_contract(key):
    r = rec(FRA)
    r[key] = "x"
    refused(r, f"field {key!r} is not part of the contract")
    e = entry()
    e[key] = 30
    assert any(f"field {key!r} is not part of the contract" in p for p in G.context_problems([e]))


def test_gate_refuses_a_wrong_country_precision_or_region_shape():
    r = rec(FRA)
    r["country_a3"] = "XXX"
    refused(r, "is not a country on the world map")
    r = rec(DEU)
    r["admin1"] = {"code": "DE-BY", "name": "Bavaria", "city": "Munich"}
    refused(r, "admin1 is null or {code, name}")
    r = rec(DEU)
    r["geographic_precision"] = "country"
    refused(r, "admin1 is set but geographic_precision is not admin1")
    r = rec(MULTI)
    r["countries_a3"] = ["PRT"]
    refused(r, "MULTI needs")
    r = rec(FRA)
    r["sector"] = "telecom"
    refused(r, "belongs to the civilian_service domain")


def test_gate_refuses_an_attempt_filed_as_a_disruption_and_the_reverse():
    r = rec(FRA)
    r["effect"] = "The attack was thwarted and there was no service disruption."
    refused(r, "an attempt is filed as a disruption")
    # One service untouched while another failed is a disruption.
    r["effect"] = "Billing was unavailable for a week. Electricity supply was not affected."
    assert not any("attempt" in p for p in problems(r))
    r = rec(NLD)
    r["civilian_service_impact"] = copy.deepcopy(rec(ITA)["civilian_service_impact"])
    refused(r, "an attempt has no service impact and no inclusion basis")
    r = rec(NLD)
    r["inclusion_basis"] = 5
    refused(r, "an attempt has no service impact and no inclusion basis")
    r = rec(NLD)
    r["sources"][0]["source_role"] = "media"
    refused(r, "an attempt needs an official or operator statement")
    # An attempt may say in words that nothing was disrupted; that is what makes it an attempt.
    r = rec(NLD)
    r["effect"] = "SYNTHETIC. No service disruption was reported."
    r["effect_specificity"] = "described"
    assert problems(r) == []


def test_an_attempts_confidence_never_scores_an_effect_it_did_not_have():
    e, c, lg = docs()
    for r in e["records"]:
        if r["impact_id"] == NLD:
            r["effect"] = "SYNTHETIC. No service disruption was reported."
            r["effect_specificity"] = "quantified"
            r["sources"][0]["supports"] = ["occurrence", "effect"]
    served = G.build_payloads(e, c, lg, ctx(), AS_OF)[G.IMPACTS_OUT]["attempts"][0]
    assert served["evidence_confidence"]["components"]["effect"]["points"] == 0


def test_an_unknown_figure_is_a_word_and_a_unit_may_stand_without_one():
    r = rec(POL)
    r["civilian_service_impact"][0]["affected"] = {"value": "unknown", "unit": "subscribers", "qualifier": None,
                                                   "source_says": "its mobile subscribers (no figure given)"}
    assert problems(r) == []
    r["civilian_service_impact"][0]["affected"]["qualifier"] = "about"
    refused(r, "a qualifier with no value")
    r["civilian_service_impact"][0]["affected"] = {"value": "lots", "unit": "subscribers", "qualifier": "about",
                                                   "source_says": "lots of subscribers"}
    refused(r, "a figure is a positive number")


def test_malice_and_attribution_agree():
    r = rec(FRA)
    r["attribution"] = rec(BRA)["attribution"]
    refused(r, "NOT_APPLICABLE on a malicious act")
    r = rec(BRA)
    r["attribution"] = rec(USA)["attribution"]
    refused(r, "on a record that is not a malicious act")


def test_gate_requires_first_published_and_a_well_formed_id():
    r = rec(FRA)
    del r["first_published"]
    refused(r, "no first_published")
    r = rec(FRA)
    r["first_published"] = "yesterday"
    refused(r, "first_published 'yesterday' is not a date or null")
    r = rec(FRA)
    r["first_published"] = None          # pending its first release: allowed, and served as null
    assert problems(r) == []
    r["last_revised"] = "2026-11-25"
    refused(r, "last_revised on a record pending its first release")
    r = rec(FRA)
    r["impact_id"] = "imp-2025-03-06-fra-electricity-synthetic-grid-ransomware"
    refused(r, "impact_id must be imp-<date>-<a3>-<sector>-<slug>")
    r = rec(FRA)
    r["last_revised"] = "2020-01-01"
    refused(r, "last_revised is a date on or after first_published")
    e, c, lg = docs()
    e["records"].append(rec(FRA))
    assert any("duplicate impact_id" in p for p in G.record_problems(e["records"], ctx()))


@pytest.mark.parametrize("role", G.REVIEW_ROLES)
def test_gate_requires_every_review_role_to_have_accepted(role):
    r = rec(FRA)
    r["review"]["roles"][role] = "reject"
    refused(r, f"review role {role} did not accept")
    r = rec(FRA)
    del r["review"]["roles"][role]
    refused(r, f"review role {role} did not accept")


def test_gate_requires_the_review_block():
    assert set(G.REVIEW_ROLES) == {"evidence", "attribution_source", "safety"}
    r = rec(FRA)
    r["review"] = None
    refused(r, "no review block")
    r = rec(FRA)
    r["review"]["review_status"] = "legacy_single_review"
    refused(r, "review_status must be blind_reviewed")
    r = rec(FRA)
    r["review"]["roles"]["taxonomy"] = "accept"
    refused(r, "are not roles of this review")


def test_a_problem_names_the_record_and_the_build_raises_it():
    e, c, lg = docs()
    e["records"][0]["summary"] += " near 48.8566, 2.3522"
    with pytest.raises(ValueError) as err:
        G.build_payloads(e, c, lg, ctx(), AS_OF)
    assert e["records"][0]["impact_id"] in str(err.value) and "coordinate" in str(err.value)


# --- the gate: the regional context and the research note -----------------------------------------------------

def test_context_entries_are_dated_as_of_sourced_and_reviewed():
    for key, why in (("date", "date None is not a date"), ("as_of", "as_of None is not a date"),
                     ("first_published", "first_published '11 March' is not a date or null")):
        e = entry()
        e[key] = None if key != "first_published" else "11 March"
        assert any(why in p for p in G.context_problems([e])), key
    e = entry()
    e["first_published"] = None          # pending its first release
    assert G.context_problems([e]) == []
    e["last_revised"] = "2026-11-25"
    assert any("pending its first release" in p for p in G.context_problems([e]))
    e = entry()
    e["sources"] = []
    assert any("no source" in p for p in G.context_problems([e]))
    for role in G.CONTEXT_REVIEW_ROLES:
        e = entry()
        e["review"]["roles"][role] = "reject"
        assert any(f"review role {role} did not accept" in p for p in G.context_problems([e]))
    e = entry()
    e["context_type"] = "current_status"
    assert any("context_type" in p for p in G.context_problems([e]))
    e = entry()
    # A report published today about last week's position: as_of may be earlier than date.
    e["as_of"] = "2026-02-27"
    assert G.context_problems([e]) == []


def test_a_context_metric_needs_its_unit_and_basis_and_a_range_its_upper_value():
    base = next(x for x in _json(FIXTURE / "regional_context.json")["entries"] if x["metric"] and x["metric"].get("qualifier") == "range")
    assert G.context_problems([base]) == []
    for key, why in (("unit", "a metric value without a unit"), ("basis", "a metric without its basis")):
        e = copy.deepcopy(base)
        e["metric"][key] = None
        assert any(why in p for p in G.context_problems([e]))
    e = copy.deepcopy(base)
    del e["metric"]["value_upper"]
    assert any("only for a range" in p for p in G.context_problems([e]))
    e = copy.deepcopy(base)
    e["metric"]["qualifier"] = "exactly"
    assert any("metric.qualifier" in p for p in G.context_problems([e]))
    e = copy.deepcopy(base)
    e["metric"]["value"] = None
    assert any("metric.value is a number" in p for p in G.context_problems([e]))


def test_the_research_note_publishes_process_facts_only():
    lg = docs()[2]
    assert G.log_problems(lg) == []
    for text in ("Two candidates were held for review.", "One record was rejected.", "Three near-misses were set aside."):
        bad = copy.deepcopy(lg)
        bad["source_families"][0]["limitation"] = text
        assert any("held, rejected or candidate work" in p for p in G.log_problems(bad)), text
    # A site that refused the fetcher is a process fact, and is published.
    ok = copy.deepcopy(lg)
    ok["source_families"][0]["limitation"] = "Two archives refused automated fetches."
    assert G.log_problems(ok) == []
    bad = copy.deepcopy(lg)
    bad["source_families"][0]["searches_used"] = 12
    assert any("is not part of the contract" in p for p in G.log_problems(bad))
    bad = copy.deepcopy(lg)
    bad["source_families"][0]["method"] = "Enumerated tanker reports."
    assert any("shipping or route wording in an impact research note" in p for p in G.log_problems(bad))


@pytest.mark.parametrize("field,text", [
    ("limitation", "After 35 requests the site refused; I stopped rather than retry."),
    ("limitation", "Only the items I'm aware of."),
    ("limitation", "Several outlets refused the fetch tool."),
    ("method", "WebSearch, then WebFetch of each page."),
    ("limitation", "Both are after the model's knowledge cutoff."),
    ("limitation", "Named in the task as a family to search."),
    ("limitation", "No later status was researched, by instruction."),
    ("method", "Read data/curated/incidents.csv locally."),
    ("limitation", "Records were read from events.json."),
    ("limitation", "Its attribution is NOT_APPLICABLE."),
    ("status", "not_started"),
    ("limitation", "Already filed by gulf_states."),
    ("limitation", "Left to the water lane."),
    ("limitation", "An earlier pass (na2) found nothing."),
    ("limitation", "Already in the theatre as imp-2024-07-16-rus-electricity-outage."),
])
def test_the_research_note_refuses_first_person_and_pipeline_wording(field, text):
    lg = docs()[2]
    bad = copy.deepcopy(lg)
    bad["source_families"][0][field] = text
    assert any("first-person or pipeline wording" in p for p in G.log_problems(bad)), text
    bad = copy.deepcopy(lg)
    bad["limitations"] = [text]
    assert any("first-person or pipeline wording" in p for p in G.log_problems(bad)), text


def test_the_research_note_keeps_process_facts_in_the_third_person():
    lg = docs()[2]
    for text in ("After about 35 requests the site answered HTTP 520, and requests were stopped rather than repeated.",
                 "AI-related incidents in the US and the EU were searched; CERT-In was not enumerated.",
                 "Reuters and AP refused automated requests; text.npr.org worked.", "not started", "partial"):
        ok = copy.deepcopy(lg)
        ok["source_families"][0]["limitation"] = text
        ok["limitations"] = [text]
        assert G.log_problems(ok) == [], text


# --- the build ---------------------------------------------------------------------------------------------

def test_the_build_is_deterministic_and_independent_of_input_order(tmp_path):
    a, b = payloads(), payloads()
    e, c, lg = docs()
    e["records"].reverse()
    c["entries"].reverse()
    for r in e["records"]:
        r["sources"] = list(r["sources"])
    shuffled = G.build_payloads(e, c, lg, ctx(), AS_OF)
    for name in G.OUTPUTS:
        assert json.dumps(a[name], ensure_ascii=False) == json.dumps(b[name], ensure_ascii=False), name
        assert json.dumps(a[name], ensure_ascii=False) == json.dumps(shuffled[name], ensure_ascii=False), name
    G.write_payloads(a, tmp_path / "one")
    G.write_payloads(b, tmp_path / "two")
    for name in G.OUTPUTS:
        assert (tmp_path / "one" / name).read_bytes() == (tmp_path / "two" / name).read_bytes()
        assert b"\r" not in (tmp_path / "one" / name).read_bytes()


def test_an_empty_corpus_builds_honest_empty_artifacts():
    empty_log = {"window": {"start": "2022-01-01", "end": "present"}, "status": "expanding corpus", "source_families": [],
                 "regions_worked": [], "limitations": [], "latest_research_date": None}
    p = G.build_payloads({"schema_version": 1, "records": []}, {"context_id": "gulf_hormuz", "entries": []},
                         empty_log, ctx(), AS_OF)
    imp, cx = p[G.IMPACTS_OUT], p[G.CONTEXT_OUT]
    assert imp["records"] == [] and imp["attempts"] == [] and imp["countries"] == []
    assert "not a finding that nothing happened" in imp["empty_reason"]
    assert imp["research"]["status"] == "expanding corpus" and imp["research"]["latest_research_date"] is None
    assert cx["entries"] == [] and cx["empty_reason"]
    assert imp["scope_statement"] and any("not a census" in c for c in imp["caveats"])
    assert any("never a rate" in c for c in imp["caveats"])
    assert p[G.METHOD_OUT]["components"]


def test_the_committed_corpus_passes_the_gate():
    e, c, lg = G.load_curated()
    real = G.load_context(WORLD)
    needs_names = any(G.restricted_systems(r, real) for r in e["records"])
    if needs_names and not (ROOT / "data" / "raw" / "ne_10m_admin_1.geojson").exists():
        pytest.skip("a record in a campaign system needs the Natural Earth cache to be checked")
    assert G.gate(e, c, lg, real) == []
    assert e["schema_version"] == 1 and c["context_id"] == "gulf_hormuz" and lg["status"] == "expanding corpus"


def test_attempts_are_served_apart_and_never_among_the_records():
    imp = payloads()[G.IMPACTS_OUT]
    assert [r["impact_id"] for r in imp["attempts"]] == [NLD]
    assert all(r["record_kind"] == "disruption" for r in imp["records"])
    assert NLD not in {r["impact_id"] for r in imp["records"]}
    assert imp["attempts_label"] == "ATTEMPT — NO REPORTED SERVICE DISRUPTION"
    assert len(imp["records"]) + len(imp["attempts"]) == len(_json(FIXTURE / "events.json")["records"])


def test_records_are_newest_first_then_by_id_and_countries_alphabetical():
    imp = payloads()[G.IMPACTS_OUT]
    keys = [((r["date"] + "-01-01")[:10], r["impact_id"]) for r in imp["records"]]
    assert keys == sorted(sorted(keys, key=lambda k: k[1]), key=lambda k: k[0], reverse=True)
    e, c, lg = docs()
    twin = rec(FRA)
    twin["impact_id"] = FRA.replace("synthetic-grid", "synthetic-agrid")
    e["records"].append(twin)
    ids = [r["impact_id"] for r in G.build_payloads(e, c, lg, ctx(), AS_OF)[G.IMPACTS_OUT]["records"]]
    assert ids.index(twin["impact_id"]) + 1 == ids.index(FRA)
    names = [x["name"] for x in imp["countries"]]
    assert names == sorted(names) and len(names) == len(set(names))


# Read by word, so "countries" is not "count".
RANKABLE = re.compile(r"(^|_)(counts?|totals?|rank\w*|scores?|number|n|tally|share|percent|top|most|severity|importance)(_|$)", re.I)


def _keys_outside_records(x, path=""):
    if isinstance(x, dict):
        for k, v in x.items():
            if path == "" and k in ("records", "attempts", "vocabularies", "field_notes"):
                continue
            yield f"{path}.{k}"
            yield from _keys_outside_records(v, f"{path}.{k}")
    elif isinstance(x, list):
        for v in x:
            yield from _keys_outside_records(v, path)


def test_the_artifact_carries_no_count_per_country_and_no_rankable_field():
    imp = payloads()[G.IMPACTS_OUT]
    for row in imp["countries"]:
        assert set(row) <= {"a3", "name", "system_id", "theatre"}, row
        assert not any(isinstance(v, (int, float)) and not isinstance(v, bool) for v in row.values())
    bad = [k for k in _keys_outside_records(imp) if RANKABLE.search(k.rsplit(".", 1)[-1])]
    assert bad == []
    # The only figures a record carries about itself are its own evidence, never a comparison.
    for r in imp["records"]:
        assert not [k for k in r if RANKABLE.search(k) and k != "origin_count"]
    cx = payloads()[G.CONTEXT_OUT]
    assert [k for k in _keys_outside_records(cx) if RANKABLE.search(k.rsplit(".", 1)[-1])] == []


def test_each_served_record_adds_what_the_contract_says():
    imp = payloads()[G.IMPACTS_OUT]
    by_id = {r["impact_id"]: r for r in imp["records"] + imp["attempts"]}
    assert by_id[USA]["system_id"] == "us" and by_id[USA]["country_name"] == "United States of America"
    assert by_id[IRN]["system_id"] == "ir"
    assert by_id[FRA]["system_id"] is None and "theatre" not in by_id[FRA]
    # The theatre is not a country system: no system_id, and the flag comes from the registry.
    assert by_id[RUS]["system_id"] is None and by_id[RUS]["theatre"] is True
    assert set(systems.system(systems.THEATRE)["admin0_a3"]) == {"RUS", "BLR"}
    assert by_id[MULTI]["country_name"] == "Several countries"
    assert [c["name"] for c in by_id[MULTI]["countries"]] == ["Portugal", "Spain"]
    for rid, served in by_id.items():
        raw = rec(rid)
        end = raw["date_end"] if raw["date_end"] not in G.ABSENCE else None
        # The record's own review block goes to the model: the source-and-attribution reviewer
        # checked which sources relay which, so a reviewed record's origin count is a reviewed one.
        assert served["evidence_confidence"] == EC.assess(raw["sources"], raw["date"], end,
                                                          raw["effect_specificity"] or "vague", raw["dispute"],
                                                          review=raw["review"]), rid
        assert served["evidence_confidence"]["components"]["origins"]["basis"] ==                ("reviewed" if EC.origins_reviewed(raw["review"]) else "publishers"), rid
        assert served["attribution"]["confidence"] == EC.attribution_confidence(raw["attribution"], raw["sources"]), rid
        # One way of counting origins: the model's grouping, over every citation.
        assert served["origin_count"] == EC.independent_origins(raw["sources"]), rid
        assert all(s["link_check"] in G.ids("link_states") for s in served["sources"]), rid
        assert {k: v for k, v in served.items() if k in raw and k not in ("attribution", "sources")} == \
               {k: v for k, v in raw.items() if k not in ("attribution", "sources")}, rid
    assert by_id[BRA]["attribution"]["confidence"] is None          # not applicable is null, not "low"
    assert by_id[USA]["attribution"]["confidence"] == "NOT_ESTABLISHED"
    assert by_id[ITA]["attribution"]["confidence"] == "CLAIM_ONLY"
    assert by_id[BRA]["evidence_confidence"]["category"] == "DISPUTED"


def test_link_check_is_the_known_state_or_unchecked():
    imp = payloads()[G.IMPACTS_OUT]
    states = {s["url"]: s["link_check"] for r in imp["records"] for s in r["sources"]}
    assert states["https://utility.example/synthetic/statement"] == "reachable"
    assert states["https://channel.example/synthetic/post/2002"] == "deleted"
    assert states["https://ministry.example/synthetic/statement"] == "unchecked"
    quiet = G.load_context(WORLD, unit_names=UNIT_NAMES, link_states={"https://utility.example/synthetic/statement": "fine"})
    e, c, lg = docs()
    served = G.build_payloads(e, c, lg, quiet, AS_OF)[G.IMPACTS_OUT]
    assert {s["link_check"] for r in served["records"] for s in r["sources"]} == {"unchecked"}
    bad = G.link_problems({"https://nobody.example/x": "reachable", "https://utility.example/synthetic/statement": "fine"}, e, c)
    assert any("not a citation of any published record" in p for p in bad) and any("has state 'fine'" in p for p in bad)


def test_a_record_dated_after_the_build_date_is_not_served():
    imp = payloads(as_of="2025-01-01")[G.IMPACTS_OUT]
    assert imp["records"] and all((r["date"] + "-01-01")[:10] <= "2025-01-01" for r in imp["records"])
    assert FRA not in {r["impact_id"] for r in imp["records"]}
    assert "France" not in {c["name"] for c in imp["countries"]}


def test_the_served_impacts_carry_no_route_wording_anywhere():
    text = json.dumps(payloads()[G.IMPACTS_OUT], ensure_ascii=False)
    assert B.ROUTE_WORDING.search(text) is None
    # The regional context is the one artifact that may: the wording lives there and only there.
    assert "Hormuz" in json.dumps(payloads()[G.CONTEXT_OUT], ensure_ascii=False)


def test_vocabularies_are_served_with_labels_and_definitions():
    imp = payloads()[G.IMPACTS_OUT]
    for name in G.VOCABULARIES:
        assert imp["vocabularies"][name], name
        for row in imp["vocabularies"][name]:
            assert {"id", "label", "definition"} <= set(row) and row["definition"].endswith("."), (name, row)
            assert len(re.findall(r"[.!?](\s|$)", row["definition"])) <= 2, (name, row["id"])
    r = imp["research"]
    assert set(r) == {"window", "status", "source_families", "regions_worked", "limitations", "latest_research_date",
                      "holds_statement"}
    assert r["holds_statement"] is None
    assert all(f["lane"] == "fixture" and "scope" not in f for f in r["source_families"]) and len(r["source_families"]) == 1


def test_the_taxonomy_matches_the_methodology_and_the_confidence_module():
    t = G.TAXONOMY
    assert G.ids("attribution_statuses") == EC.ATTRIBUTION_STATUSES
    assert G.ids("actor_types") == EC.ACTOR_TYPES and G.ids("attribution_bases") == EC.ATTRIBUTION_BASES
    assert G.ids("ai_statuses") == EC.AI_STATUSES and G.ids("ai_relations") == EC.AI_RELATIONS
    assert G.ids("ai_roles") == EC.AI_ROLES and G.ids("claims") == EC.CLAIMS
    assert set(G.ids("effect_specificity")) == set(EC.EFFECT_SPECIFICITY)
    assert [s["id"] for s in t["sectors"] if s["domain"] == "energy"] == ["electricity", "oil_gas", "fuel_supply", "district_energy"]
    assert [s["id"] for s in t["sectors"] if s["domain"] == "civilian_service"] == [
        "water", "wastewater", "desalination", "telecom", "healthcare", "transport", "municipal_services"]
    assert len(t["technologies"]) == 15 and len(t["cyber_mechanisms"]) == 12 and len(t["source_roles"]) == 14
    assert G.ids("cause_families") == ("kinetic", "cyber", "sabotage", "industrial_technical", "natural_hazard",
                                       "supply_shortfall", "civil_disruption", "authority_order", "unknown")
    assert G.ids("inclusion_bases") == (1, 2, 3, 4, 5, 6) and G.ids("social_tiers") == ("S1", "S2", "S3", "S4")
    assert G.ids("absence_words") == ("unknown", "not_researched", "withheld", "no_public_evidence", "source_inaccessible")
    assert G.ids("context_types") == ("shipping_status", "aggregate_trade", "aggregate_supply", "market_response",
                                      "reserve_action", "policy_response", "civilian_environmental")
    assert set(G.ids("link_states")) == {"reachable", "redirected", "blocked", "dead", "error", "deleted", "archived_copy", "unchecked"}
    assert set(B.LINK_STATES) <= set(G.ids("link_states"))
    # The mapping from the country systems' vocabulary covers all of it, and migrates nothing.
    from pipeline.config import ASSET_CLASSES, DISRUPTION_CAUSES
    causes = set(DISRUPTION_CAUSES) | set(B.TAXONOMY_EXTENSIONS["causes"])
    assert set(t["country_cause_to_family"]["map"]) == causes
    assert t["country_cause_to_family"]["map"]["kinetic_strike"] == "kinetic"
    assert set(t["country_cause_to_family"]["map"].values()) - {None} <= set(G.ids("cause_families"))
    classes = set(ASSET_CLASSES) | set(B.TAXONOMY_EXTENSIONS["asset_classes"])
    assert set(t["asset_class_to_technology"]["map"]) == classes
    for row in t["asset_class_to_technology"]["map"].values():
        assert row["sector"] is None or G.SECTOR_DOMAIN[row["sector"]] == "energy"
        assert row["technology"] is None or row["technology"] in G.ids("technologies")
    assert all(r["relation"] in EC.AI_RELATIONS + (None,) for r in t["ai_roles"])


def test_the_confidence_method_artifact_is_the_modules_method_plus_labels():
    m = payloads()[G.METHOD_OUT]
    base = EC.method()
    assert {k: m[k] for k in base} == base
    assert set(m) - set(base) == {"scope_of_use", "labels", "null_means"}
    assert {"attribution_statuses", "ai_statuses", "ai_relations", "ai_roles", "source_roles", "social_tiers"} <= set(m["labels"])
    assert "not a probability" in m["statement"]


# --- the regional context artifact -------------------------------------------------------------------------

def test_context_entries_carry_their_age_and_only_the_newest_of_a_type_is_latest():
    cx = payloads()[G.CONTEXT_OUT]
    by_id = {e["id"]: e for e in cx["entries"]}
    old, new = by_id["ctx-2026-03-05-synthetic-shipping-statement"], by_id["ctx-2026-09-20-synthetic-shipping-statement"]
    assert new["is_latest_of_type"] is True and old["is_latest_of_type"] is False
    assert old["age_days"] == 259 and new["age_days"] == 58       # from each entry's as-of date to the build date
    for ctype in {e["context_type"] for e in cx["entries"]}:
        latest = [e for e in cx["entries"] if e["context_type"] == ctype and e["is_latest_of_type"]]
        assert len(latest) == 1 and latest[0]["as_of"] == max(e["as_of"] for e in cx["entries"] if e["context_type"] == ctype)
    assert [e["date"] for e in cx["entries"]] == sorted((e["date"] for e in cx["entries"]), reverse=True)
    # A later build date ages every statement; it never makes an old one current.
    later = payloads(as_of="2027-01-01")[G.CONTEXT_OUT]
    assert all(e["age_days"] > by_id[e["id"]]["age_days"] for e in later["entries"])


def test_the_context_artifact_has_no_status_flag_and_no_shelf_life():
    cx = payloads()[G.CONTEXT_OUT]
    # The artifact's own fields and each statement's: the research note's "status" is the research's.
    keys = set(cx) | {k for e in cx["entries"] for k in e} | {k for e in cx["entries"] if e["metric"] for k in e["metric"]}
    assert not {k for k in keys if re.search(r"(^|_)(status|current|open|closed|shelf|expires|valid)(_|$)", k)}
    assert "no open or closed flag" in cx["not_built"] and "not a current status" in cx["latest_note"]
    assert cx["context_id"] == "gulf_hormuz" and len(cx["context_types"]) == 7
    assert all(e["metric"] is None or {"value", "unit", "basis"} <= set(e["metric"]) for e in cx["entries"])
    assert [f["family"] for f in cx["research"]["source_families"]] == ["Synthetic agency statements"]


# --- registration and isolation ---------------------------------------------------------------------------

def test_the_three_artifacts_are_declared_and_the_build_is_wired_once():
    assert set(G.OUTPUTS) <= set(artifacts.GLOBAL_PAYLOADS)
    for name in G.OUTPUTS:
        assert f"data/processed/{name}" in artifacts.required_paths()
        assert f"web/public/data/{name}" in artifacts.required_paths()
    run = (ROOT / "pipeline" / "run.py").read_text(encoding="utf-8")
    assert run.count("global_impacts.build(") == 1
    assert run.index("build_systems.build(snapshot)") < run.index("global_impacts.build(") < run.index("_mirror_to_web()")


ANALYTIC = ("build_index.py", "explain.py", "recovery.py", "lifecycle.py", "diff_builds.py")


def _imports(path):
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            names |= {node.module or ""} | {a.name for a in node.names}
        elif isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
    return names


def test_no_analytic_module_imports_the_impact_layer_or_the_confidence_module():
    for name in ANALYTIC:
        got = _imports(ROOT / "pipeline" / name)
        leaked = {n for n in got if re.search(r"global_impacts|evidence_confidence", n)}
        assert leaked == set(), (name, leaked)
        assert "global_impacts" not in (ROOT / "pipeline" / name).read_text(encoding="utf-8"), name
    # The country build never reads the impact corpus either: a record cannot reach a country's events.
    text = (ROOT / "pipeline" / "build_systems.py").read_text(encoding="utf-8")
    assert "global_impacts" not in text and "impact_id" not in text


def test_the_builder_reads_the_curated_corpus_and_never_the_queue():
    text = (ROOT / "pipeline" / "global_impacts.py").read_text(encoding="utf-8")
    assert "candidates" not in re.sub(r'"""[\s\S]*?"""|#.*', "", text)
    assert G.IMPACTS_CURATED == ROOT / "data" / "curated" / "global_impacts"


def test_no_impact_record_reaches_the_snapshot_or_a_countrys_events():
    snapshot = ROOT / "data" / "processed" / "snapshot.json"
    if not snapshot.exists():
        pytest.skip("no built payload")
    assert "impact_id" not in snapshot.read_text(encoding="utf-8")
    for sid in systems.COUNTRY_SYSTEMS:
        text = (ROOT / "data" / "processed" / systems.root(sid) / "events.json").read_text(encoding="utf-8")
        assert "impact_id" not in text and '"imp-' not in text, sid


def test_the_built_artifacts_on_disk_are_the_curated_corpus_as_built():
    out = ROOT / "data" / "processed" / G.IMPACTS_OUT
    if not out.exists():
        pytest.skip("no built impact payload yet: the build must be rerun")
    served = _json(out)
    e, c, lg = G.load_curated()
    known = {r["impact_id"] for r in e["records"] if (r["date"] + "-01-01")[:10] <= served["as_of"]}
    assert {r["impact_id"] for r in served["records"] + served["attempts"]} == known
    assert all(r["record_kind"] == "disruption" for r in served["records"])
    assert B.ROUTE_WORDING.search(out.read_text(encoding="utf-8")) is None


# --- the import ------------------------------------------------------------------------------------------

I = _script("import_impacts")
S = _script("stamp_first_published")
DAY1, DAY2 = "2026-11-20", "2026-11-27"


def candidate(base, **changes):
    """A fixture record as a lane would file it: no review block, no stamps."""
    r = rec(base)
    for k in ("review", "first_published", "last_revised"):
        r.pop(k, None)
    r.update(changes)
    return r


def accept(ids, **extra):
    return {i: {"verdict": "accept", "reason": "Checked.", **extra} for i in ids}


def make_queue(tmp, lanes, reviews=None, context=None, logs=None, country=None, published=None, extra_files=None):
    """A temporary queue, curated directory and country queues. `reviews` is {role: {lane: verdicts}};
    left out, every role accepts every candidate and the evidence role opened every source."""
    queue, curated, cq, sc = tmp / "queue", tmp / "curated", tmp / "country_queues", tmp / "systems"
    for lane, cands in lanes.items():
        (queue / lane).mkdir(parents=True, exist_ok=True)
        if cands is not None:
            (queue / lane / "candidates.json").write_text(json.dumps(cands, ensure_ascii=False), encoding="utf-8")
    for lane, entries in (context or {}).items():
        (queue / lane).mkdir(parents=True, exist_ok=True)
        (queue / lane / "context_entries.json").write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    for lane, doc in (logs or {}).items():
        (queue / lane / "lane_log.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    if reviews is None:
        reviews = {}
        for role in I.ROLE_ORDER:
            reviews[role] = {}
            for lane, cands in lanes.items():
                v = accept([c["impact_id"] for c in cands or []])
                if role == "evidence":
                    for c in cands or []:
                        v[c["impact_id"]]["sources_opened"] = [s["ref"] for s in c["sources"]]
                reviews[role][lane] = v
            for lane, entries in (context or {}).items():
                if role in I.CONTEXT_ROLES:
                    reviews[role].setdefault(lane, {}).update(
                        accept([x["id"] for x in entries], **({"sources_opened": ["s1"]} if role == "evidence" else {})))
    for role, by_lane in reviews.items():
        (queue / "reviews" / role).mkdir(parents=True, exist_ok=True)
        for lane, verdicts in by_lane.items():
            (queue / "reviews" / role / f"{lane}.json").write_text(json.dumps(
                {"lane": lane, "role": role, "reviewed_at": "2026-11-19", "verdicts": verdicts}, ensure_ascii=False), encoding="utf-8")
    curated.mkdir(parents=True, exist_ok=True)
    (curated / "events.json").write_text(json.dumps({"schema_version": 1, "records": []}), encoding="utf-8")
    (curated / "regional_context.json").write_text(json.dumps({"context_id": "gulf_hormuz", "schema_version": 1, "entries": []}), encoding="utf-8")
    (curated / "research_log.json").write_text(json.dumps(
        {"window": {"start": "2022-01-01", "end": "present"}, "status": "expanding corpus", "source_families": [],
         "regions_worked": [], "limitations": [], "latest_research_date": None}), encoding="utf-8")
    cq.mkdir(parents=True, exist_ok=True)
    for sid, rows in (country or {}).items():
        (cq / f"{sid}.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        (sc / sid).mkdir(parents=True, exist_ok=True)
        (sc / sid / "events.json").write_text(json.dumps(
            {"system_id": sid, "events": [{"event_id": i} for i in (published or {}).get(sid, [])]}), encoding="utf-8")
    for rel, doc in (extra_files or {}).items():
        (queue / rel).parent.mkdir(parents=True, exist_ok=True)
        (queue / rel).write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return {"queue": queue, "curated": curated, "country_queues": cq, "systems_curated": sc}


def run(paths, date=DAY1):
    return I.run(date=date, ctx=ctx(), key=KEY, **paths)


def curated_records(paths):
    return {r["impact_id"]: r for r in _json(paths["curated"] / "events.json")["records"]}


def reasons(report, cid):
    return " | ".join(x for r in report["refused"] if r["candidate_id"] == cid for x in r["reasons"])


def review_file(paths, role, lane):
    return paths["queue"] / "reviews" / role / f"{lane}.json"


def edit_review(paths, role, lane, cid, **changes):
    path = review_file(paths, role, lane)
    doc = _json(path)
    doc["verdicts"][cid].update(changes)
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def stamp_release(paths, date):
    """What the release lead does in the release commit: date everything pending."""
    return S.stamp(date, curated=paths["curated"])


def test_import_publishes_only_what_every_role_accepted_and_leaves_first_published_pending(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), candidate(POL)], "na": [candidate(USA)]})
    report = run(paths)
    got = curated_records(paths)
    assert set(got) == {FRA, POL, USA} == set(report["imported"])
    # Imported is not published: nothing is dated until a release serves it.
    assert all(r["first_published"] is None and "last_revised" not in r for r in got.values())
    assert got[FRA]["review"]["roles"] == {"evidence": "accept", "attribution_source": "accept", "safety": "accept"}
    assert got[FRA]["review"]["review_status"] == "blind_reviewed" and got[FRA]["review"]["disposition"] == "confirmed"
    assert got[USA]["review"]["ai_check"] == "passed" and got[FRA]["review"]["ai_check"] == "not_applicable"
    assert got[POL]["review"]["social_check"] == "passed"
    assert report["by_lane"] == {"europe": {"imported": 2, "refused": 0, "not_reviewed": 0},
                                 "na": {"imported": 1, "refused": 0, "not_reviewed": 0}}
    # What it wrote is exactly what the build will accept.
    e, c, lg = G.load_curated(paths["curated"])
    assert G.gate(e, c, lg, ctx()) == []
    assert _json(paths["queue"] / "import_report.json") == report


def test_import_is_idempotent_and_never_restamps(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), candidate(BRA)]}, context={"hormuz": [
        {k: v for k, v in entry().items() if k not in ("review", "first_published")}]})
    run(paths)
    files = [paths["curated"] / n for n in ("events.json", "regional_context.json", "research_log.json")] + \
            [paths["queue"] / "import_report.json"]
    first = [p.read_bytes() for p in files]
    run(paths)
    assert [p.read_bytes() for p in files] == first
    assert all(b"\r" not in b for b in first)
    # Never the run date, on any run: still pending until a release dates it.
    run(paths, date=DAY2)
    assert all(r["first_published"] is None for r in curated_records(paths).values())
    assert _json(paths["curated"] / "regional_context.json")["entries"][0]["first_published"] is None
    stamp_release(paths, DAY1)
    # A later run, with nothing changed, keeps the release's date and marks no revision.
    run(paths, date=DAY2)
    got = curated_records(paths)
    assert all(r["first_published"] == DAY1 and "last_revised" not in r for r in got.values())
    assert _json(paths["curated"] / "regional_context.json")["entries"][0]["first_published"] == DAY1


def test_a_changed_record_keeps_first_published_and_gains_last_revised(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), candidate(BRA)]})
    run(paths)
    stamp_release(paths, DAY1)
    edit_review(paths, "safety", "europe", FRA, verdict="accept_with_correction",
                set={"summary": "SYNTHETIC FIXTURE. A reworded summary of the incident in France."})
    run(paths, date=DAY2)
    got = curated_records(paths)
    assert got[FRA]["first_published"] == DAY1 and got[FRA]["last_revised"] == DAY2
    assert got[FRA]["summary"].endswith("in France.") and got[FRA]["review"]["disposition"] == "corrected"
    assert got[BRA]["first_published"] == DAY1 and "last_revised" not in got[BRA]
    run(paths, date="2026-12-05")
    assert curated_records(paths)[FRA]["last_revised"] == DAY2


def test_patches_apply_in_role_order_and_safety_wins(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA)]})
    edit_review(paths, "evidence", "europe", FRA, verdict="accept_with_correction",
                set={"summary": "SYNTHETIC FIXTURE. The evidence reviewer's wording.", "effect_specificity": "quantified",
                     "sources[s2].language": "fr", "civilian_service_impact[0].duration_text": None})
    edit_review(paths, "attribution_source", "europe", FRA, verdict="accept_with_correction",
                set={"summary": "SYNTHETIC FIXTURE. The attribution reviewer's wording.", "attribution.as_of": "2025-04-21"})
    edit_review(paths, "safety", "europe", FRA, verdict="accept_with_correction",
                set={"summary": "SYNTHETIC FIXTURE. The safety reviewer's wording."})
    run(paths)
    got = curated_records(paths)[FRA]
    assert got["summary"] == "SYNTHETIC FIXTURE. The safety reviewer's wording."
    assert got["attribution"]["as_of"] == "2025-04-21"
    assert next(s for s in got["sources"] if s["ref"] == "s2")["language"] == "fr"
    assert got["civilian_service_impact"][0]["duration_text"] is None


def test_opened_is_what_the_evidence_reviewer_opened_whatever_the_lane_wrote(tmp_path):
    c = candidate(FRA)
    for s in c["sources"]:
        s["opened"] = True
    paths = make_queue(tmp_path, {"europe": [c]})
    edit_review(paths, "evidence", "europe", FRA, sources_opened=["s1", "s3"])
    run(paths)
    got = curated_records(paths)[FRA]
    assert {s["ref"]: s["opened"] for s in got["sources"]} == {"s1": True, "s2": False, "s3": True, "s4": False}


def test_a_reviewer_can_remove_a_source(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA)]})
    edit_review(paths, "safety", "europe", FRA, verdict="accept_with_correction", remove_sources=["s2"],
                set={"civilian_service_impact[0].source_refs": ["s1"]})
    run(paths)
    assert [s["ref"] for s in curated_records(paths)[FRA]["sources"]] == ["s1", "s3", "s4"]


@pytest.mark.parametrize("role", ["evidence", "attribution_source", "safety"])
def test_a_role_that_did_not_review_or_rejected_stops_the_record(tmp_path, role):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), candidate(POL)]})
    doc = _json(review_file(paths, role, "europe"))
    del doc["verdicts"][FRA]
    doc["verdicts"][POL] = {"verdict": "reject", "reason": "duplicate of another record"}
    review_file(paths, role, "europe").write_text(json.dumps(doc), encoding="utf-8")
    report = run(paths)
    assert curated_records(paths) == {}
    assert f"not reviewed by {role}" in reasons(report, FRA)
    assert f"rejected by {role}: duplicate of another record" in reasons(report, POL)


def test_a_candidate_no_reviewer_mentions_is_not_imported(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA)], "asia": [candidate(JPN)]},
                       reviews={role: {"europe": accept([FRA], sources_opened=["s1"])} for role in I.ROLE_ORDER})
    report = run(paths)
    assert set(curated_records(paths)) == {FRA}
    assert report["not_reviewed"] == [{"lane": "asia", "candidate_id": JPN}] and report["refused"] == []


def test_an_unknown_verdict_or_an_unusable_patch_refuses_the_record(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), candidate(POL)]})
    edit_review(paths, "safety", "europe", FRA, verdict="fine")
    edit_review(paths, "evidence", "europe", POL, set={"sources[s9].supports": ["occurrence"]})
    report = run(paths)
    assert curated_records(paths) == {}
    assert "is not one of" in reasons(report, FRA) and "no sources[s9]" in reasons(report, POL)


def test_set_path_addresses_sources_by_ref_and_lists_by_index():
    r = {"sources": [{"ref": "s1", "supports": []}, {"ref": "s2", "supports": []}], "attribution": {"status": "UNKNOWN"},
         "civilian_service_impact": [{"affected": {"value": 1}}]}
    I.set_path(r, "sources[s2].supports", ["effect"])
    I.set_path(r, "attribution.status", "ASSESSED")
    I.set_path(r, "civilian_service_impact[0].affected.value", None)
    I.set_path(r, "summary", "x")
    assert r["sources"][1]["supports"] == ["effect"] and r["sources"][0]["supports"] == []
    assert r["attribution"]["status"] == "ASSESSED" and r["civilian_service_impact"][0]["affected"]["value"] is None
    with pytest.raises(ValueError):
        I.set_path(r, "civilian_service_impact[3].affected", None)


def _attack_candidate():
    c = candidate(UKR, impact_id="imp-2025-10-08-ukr-electricity-kyiv-substation-strike", publication_policy="standard",
                  admin1={"code": "UA-30", "name": "Kyiv"}, geographic_precision="admin1", date_end="2025-10-09")
    for s in c["sources"]:
        s["title_en"] = "Synthetic headline naming a place"
        s["title_original"] = "Synthetic headline naming a place"
    return c


def test_an_attack_record_is_abstracted_and_given_a_keyed_id(tmp_path):
    c = _attack_candidate()
    paths = make_queue(tmp_path, {"europe": [c]})
    # Even a reviewer's rename does not replace the keyed id.
    edit_review(paths, "safety", "europe", c["impact_id"], verdict="accept_with_correction",
                set={"impact_id": "imp-2025-10-08-ukr-electricity-renamed-by-hand"})
    report = run(paths)
    got = curated_records(paths)
    assert len(got) == 1
    rid, r = next(iter(got.items()))
    stem = "imp-2025-10-08-ukr-electricity-attack-"
    assert rid.startswith(stem) and re.fullmatch(r"[0-9a-f]{6}", rid[len(stem):])
    assert rid == I.abstract_id(c, c["impact_id"], KEY) and rid != I.abstract_id(c, c["impact_id"], b"another key")
    assert r["publication_policy"] == "country_abstracted" and r["admin1"] is None and r["geographic_precision"] == "country"
    assert r["date_end"] is None and not any("title_en" in s or "title_original" in s for s in r["sources"])
    text = (paths["curated"] / "events.json").read_text(encoding="utf-8")
    assert "kyiv" not in text.lower() and "renamed-by-hand" not in text
    assert report["renamed"] == {f"europe/{c['impact_id']}": rid}
    # The id is stable: a second run mints the same one.
    run(paths)
    assert set(curated_records(paths)) == {rid}


def test_the_keyed_id_is_not_a_plain_hash_of_the_queue_id():
    import hashlib
    c = _attack_candidate()
    token = I.abstract_id(c, c["impact_id"], KEY).rsplit("-", 1)[1]
    for material in (c["impact_id"], f"impact|{c['impact_id']}"):
        assert token not in (hashlib.sha1(material.encode()).hexdigest()[:6], hashlib.sha256(material.encode()).hexdigest()[:6])
    text = (ROOT / "scripts" / "import_impacts.py").read_text(encoding="utf-8")
    assert "opaque_key()" in text and "print(key" not in text


def test_a_reviewer_can_rename_a_candidate_and_the_old_id_never_reaches_the_curated_file(tmp_path):
    old = "imp-2025-09-02-deu-healthcare-example-hospital-munich"
    new = "imp-2025-09-02-deu-healthcare-synthetic-hospital-it-incident"
    paths = make_queue(tmp_path, {"europe": [candidate(DEU, impact_id=old)]})
    edit_review(paths, "safety", "europe", old, verdict="accept_with_correction", set={"impact_id": new})
    report = run(paths)
    assert set(curated_records(paths)) == {new} and report["renamed"] == {f"europe/{old}": new}
    assert "munich" not in (paths["curated"] / "events.json").read_text(encoding="utf-8")
    run(paths)
    assert set(curated_records(paths)) == {new}


def test_a_rename_that_collides_with_another_record_is_refused(tmp_path):
    twin = candidate(FRA, impact_id="imp-2025-03-05-fra-electricity-synthetic-second-utility")
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), twin]},
                       extra_files={"distinct_events.json": [[FRA, twin["impact_id"]]]})
    edit_review(paths, "safety", "europe", twin["impact_id"], verdict="accept_with_correction", set={"impact_id": FRA})
    # The run FAILS and writes nothing: neither record is chosen, neither overwrites the other.
    with pytest.raises(SystemExit) as err:
        run(paths)
    assert "id collision" in str(err.value) and FRA in str(err.value)
    assert curated_records(paths) == {} and not (paths["queue"] / "import_report.json").exists()
    report = I.run(date=DAY1, ctx=ctx(), key=KEY, write=False, **paths)
    assert "id collision" in reasons(report, FRA) and "id collision" in reasons(report, twin["impact_id"])
    assert report["collisions"] == [{"impact_id": FRA, "candidates": sorted([f"europe/{FRA}", f"europe/{twin['impact_id']}"])}]


def test_two_lanes_filing_one_incident_under_the_same_id_are_told_apart_by_lane(tmp_path):
    paths = make_queue(tmp_path, {"eurasia": [candidate(POL)], "telecom_transport": [candidate(POL)], "asia": [candidate(JPN)]})
    with pytest.raises(SystemExit):
        run(paths)
    assert curated_records(paths) == {}
    # The lead holds one lane's copy, by lane and id: the other is published, and nothing collides.
    (paths["queue"] / "lead_holds.json").write_text(json.dumps(
        {"_note": "local", "holds": {f"telecom_transport/{POL}": f"duplicate of eurasia/{POL}"}}), encoding="utf-8")
    report = run(paths)
    assert set(curated_records(paths)) == {POL, JPN} and report["collisions"] == []
    assert report["by_lane"]["eurasia"]["imported"] == 1 and report["by_lane"]["telecom_transport"]["refused"] == 1
    assert report["lead_holds"]["duplicates_across_lanes"] == 1


def test_two_published_records_three_days_apart_are_a_warning_for_the_lead(tmp_path, capsys):
    later = candidate(FRA, impact_id="imp-2025-03-08-fra-electricity-synthetic-second-incident", date="2025-03-08")
    far = candidate(FRA, impact_id="imp-2025-03-20-fra-electricity-synthetic-third-incident", date="2025-03-20", date_end=None)
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), later, far]})
    report = run(paths)
    assert len(curated_records(paths)) == 3
    assert report["possible_duplicates"] == [[FRA, later["impact_id"]]]
    I.print_report(report)
    assert "WARNING possible duplicate" in capsys.readouterr().out
    (paths["queue"] / "distinct_events.json").write_text(json.dumps([[FRA, later["impact_id"]]]), encoding="utf-8")
    assert run(paths)["possible_duplicates"] == []


def test_roles_may_each_rename_a_record_and_the_last_in_role_order_wins(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(DEU)]})
    edit_review(paths, "evidence", "europe", DEU, set={"impact_id": "imp-2025-09-02-deu-healthcare-first-name"})
    edit_review(paths, "safety", "europe", DEU, set={"impact_id": "imp-2025-09-02-deu-healthcare-last-name"})
    report = run(paths)
    assert set(curated_records(paths)) == {"imp-2025-09-02-deu-healthcare-last-name"}
    assert report["renamed"] == {f"europe/{DEU}": "imp-2025-09-02-deu-healthcare-last-name"}


def test_a_corrected_date_moves_the_ids_stem_with_it(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(BRA)]})
    edit_review(paths, "evidence", "europe", BRA, verdict="accept_with_correction", set={"date": "2024-07-23"})
    report = run(paths)
    new = BRA.replace("2024-07-22", "2024-07-23")
    assert set(curated_records(paths)) == {new} and report["renamed"] == {f"europe/{BRA}": new}


def test_the_same_event_filed_by_two_lanes_is_refused_until_a_reviewer_chooses(tmp_path):
    twin = candidate(FRA, impact_id="imp-2025-03-06-fra-electricity-synthetic-other-lane-copy", date="2025-03-06")
    paths = make_queue(tmp_path, {"europe": [candidate(FRA)], "ai": [twin], "asia": [candidate(JPN)]})
    report = run(paths)
    assert set(curated_records(paths)) == {JPN}
    assert "looks like the same event" in reasons(report, FRA) and "looks like the same event" in reasons(report, twin["impact_id"])
    # A reviewer rejects the copy as a duplicate: an ordinary reject, and the other is published.
    edit_review(paths, "evidence", "ai", twin["impact_id"], verdict="reject", reason=f"duplicate of {FRA}")
    report = run(paths)
    assert set(curated_records(paths)) == {FRA, JPN}
    assert f"duplicate of {FRA}" in reasons(report, twin["impact_id"])


def test_two_events_two_days_apart_or_in_different_sectors_are_not_duplicates(tmp_path):
    later = candidate(FRA, impact_id="imp-2025-03-07-fra-electricity-synthetic-second-incident", date="2025-03-07")
    other = candidate(POL, impact_id="imp-2025-03-05-fra-telecom-synthetic-network-outage", date="2025-03-05", country_a3="FRA")
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), later, other]})
    run(paths)
    assert len(curated_records(paths)) == 3


def test_the_lead_can_rule_two_same_day_records_distinct(tmp_path):
    twin = candidate(FRA, impact_id="imp-2025-03-05-fra-electricity-synthetic-second-utility")
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), twin]},
                       extra_files={"distinct_events.json": [[FRA, twin["impact_id"]]]})
    run(paths)
    assert set(curated_records(paths)) == {FRA, twin["impact_id"]}


def _country_row(cid, date="2026-02-14", asset_class="oil_terminal", cause="technical", disposition="held",
                 reason="Below the inclusion threshold: clause 3 not met.", **extra):
    return {"candidate_id": cid, "date": date, "asset_class": asset_class, "cause": cause,
            "suggested_disposition": disposition, "disposition_reason": reason, "sources": [], **extra}


def test_a_candidate_matching_a_record_held_from_a_country_system_is_refused(tmp_path):
    held = _country_row("us-2026-02-14-synthetic-held-terminal", date="2026-02-15")
    paths = make_queue(tmp_path, {"na": [candidate(USA)], "europe": [candidate(FRA)]}, country={"us": [held]})
    report = run(paths)
    assert set(curated_records(paths)) == {FRA}
    assert "matches a record held or rejected in the country system's queue" in reasons(report, USA)
    match = report["reconcile"][0]
    assert match["country_candidate_id"] == held["candidate_id"] and match["system_id"] == "us"
    assert match["hold_fields"]["suggested_disposition"] == "held" and "threshold" in match["hold_fields"]["disposition_reason"]


def test_a_published_country_record_or_one_far_in_date_or_class_is_no_match(tmp_path):
    rows = [_country_row("us-2026-02-14-synthetic-published-terminal"),
            _country_row("us-2026-03-01-synthetic-held-later", date="2026-03-01"),
            _country_row("us-2026-02-14-synthetic-held-refinery", asset_class="refinery"),
            _country_row("us-2026-02-14-synthetic-duplicate", disposition="duplicate",
                         duplicate_of="us-2026-02-14-synthetic-published-terminal")]
    paths = make_queue(tmp_path, {"na": [candidate(USA)]}, country={"us": rows},
                       published={"us": ["us-2026-02-14-synthetic-published-terminal"]})
    report = run(paths)
    assert set(curated_records(paths)) == {USA} and report["reconcile"] == []


def test_a_month_precision_country_record_matches_any_day_of_its_month(tmp_path):
    held = _country_row("us-2026-02-synthetic-held-month", date="2026-02")
    paths = make_queue(tmp_path, {"na": [candidate(USA)]}, country={"us": [held]})
    assert curated_records(paths) == {} and "reconcile with us" in reasons(run(paths), USA)


DIFFERENT = "A different event: the country record concerns another operator's terminal, two states away."


def _ruled_distinct(tmp_path, held, reason=DIFFERENT, cand=None, key=f"na/{USA}"):
    return make_queue(tmp_path, {"na": [cand or candidate(USA)]}, country={"us": [held]}, extra_files={
        "reconcile_distinct.json": {key: [{"country_candidate_id": held["candidate_id"], "reason": reason}]}})


@pytest.mark.parametrize("held,kind", [
    (_country_row("us-2026-02-14-synthetic-held-terminal"), "threshold"),
    (_country_row("us-2026-02-14-synthetic-held-attack", cause="kinetic_strike", reason="Below the inclusion threshold."), "campaign"),
    (_country_row("us-2026-02-14-synthetic-held-safety", reason="Held by the safety reviewer: facility-level status wording."), "safety"),
    (_country_row("us-2026-02-14-synthetic-held-evidence", disposition="insufficient_evidence", reason="One unopened source."), "evidence"),
    (_country_row("us-2026-02-14-synthetic-held-evidence-2", reason="Below threshold and the only source could not be verified."), "evidence"),
    (_country_row("us-2026-02-14-synthetic-held-silent", reason=None), "unclear"),
    (_country_row("us-2026-02-14-synthetic-held-dup", disposition="duplicate", duplicate_of="us-missing"), "unclear"),
])
def test_no_hold_from_a_country_system_can_be_overridden_whatever_it_was_for(tmp_path, held, kind, capsys):
    """Owner ruling: a restriction on publishing an event carries over; the stricter policy wins.
    The first form of this script had an override for a below-threshold hold. There is none now,
    and the file that carried it is not read, in either of its shapes."""
    override = {"country_candidate_id": held["candidate_id"], "reason": "The country threshold does not bind this layer."}
    paths = make_queue(tmp_path, {"na": [candidate(USA)]}, country={"us": [held]}, extra_files={
        "reconcile_allow.json": {USA: override, f"na/{USA}": [override]}})
    report = run(paths)
    assert curated_records(paths) == {}
    assert report["reconcile"][0]["hold_kind"] == kind
    assert report["reconcile"][0]["outcome"] == "refused: matches a record held or rejected in the country system's queue"
    assert "matches a record held" in reasons(report, USA)
    assert report["ignored_files"] == ["reconcile_allow.json"]
    I.print_report(report)
    assert "NOT READ reconcile_allow.json" in capsys.readouterr().out


def test_the_lead_can_rule_a_match_a_different_event_and_must_say_why(tmp_path, capsys):
    held = _country_row("us-2026-02-14-synthetic-held-terminal")
    paths = _ruled_distinct(tmp_path, held)
    report = run(paths)
    assert set(curated_records(paths)) == {USA} and report["ignored_files"] == []
    match = report["reconcile"][0]
    assert match["outcome"] == f"a different event, by the lead's ruling: {DIFFERENT}" and match["hold_kind"] == "threshold"
    I.print_report(report)
    assert "country-queue matches: 0 refused, 1 ruled a different event by the lead" in capsys.readouterr().out
    # The reason is the lead's, in the local report; nothing of it is published.
    assert "different event" not in (paths["curated"] / "events.json").read_text(encoding="utf-8")


def test_a_ruling_without_a_reason_for_another_record_or_under_a_bare_id_changes_nothing(tmp_path):
    held = _country_row("us-2026-02-14-synthetic-held-terminal")
    report = run(paths := _ruled_distinct(tmp_path / "a", held, reason="  "))
    assert curated_records(paths) == {} and "the ruling that this is a different event gives no reason" in reasons(report, USA)
    other = make_queue(tmp_path / "b", {"na": [candidate(USA)]}, country={"us": [held]}, extra_files={
        "reconcile_distinct.json": {f"na/{USA}": [{"country_candidate_id": "us-some-other-record", "reason": DIFFERENT}]}})
    assert curated_records(other) == {} and "matches a record held" in reasons(run(other), USA)
    # Lane-qualified, like every other key of the queue: a bare id names no candidate.
    bare = _ruled_distinct(tmp_path / "c", held, key=USA)
    assert curated_records(bare) == {} and "matches a record held" in reasons(run(bare), USA)
    # Two country records match: ruling one of them distinct leaves the other in force.
    second = _country_row("us-2026-02-15-synthetic-held-terminal-2", date="2026-02-15")
    both = make_queue(tmp_path / "d", {"na": [candidate(USA)]}, country={"us": [held, second]}, extra_files={
        "reconcile_distinct.json": {f"na/{USA}": [{"country_candidate_id": held["candidate_id"], "reason": DIFFERENT}]}})
    report = run(both)
    assert curated_records(both) == {} and second["candidate_id"] in reasons(report, USA)
    assert held["candidate_id"] not in reasons(report, USA)


def test_an_attack_record_can_never_be_ruled_distinct_from_a_held_country_record(tmp_path):
    held = _country_row("us-2026-02-14-synthetic-held-terminal")
    for family in ("sabotage", "kinetic"):
        paths = _ruled_distinct(tmp_path / family, held, cand=candidate(USA, cause_family=family, cyber_mechanism=None))
        report = run(paths)
        assert curated_records(paths) == {}
        assert report["reconcile"][0]["outcome"] == "refused: an attack record is never ruled distinct from a held country record"


def test_a_record_that_stops_being_accepted_is_withdrawn_and_others_are_left_alone(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), candidate(BRA)]})
    # A record from an earlier pass, whose lane is no longer in the queue, stays as it is.
    doc = _json(paths["curated"] / "events.json")
    doc["records"].append(rec(JPN))
    (paths["curated"] / "events.json").write_text(json.dumps(doc), encoding="utf-8")
    run(paths)
    assert set(curated_records(paths)) == {FRA, BRA, JPN}
    edit_review(paths, "safety", "europe", BRA, verdict="reject", reason="Fails the abstraction rule.")
    report = run(paths, date=DAY2)
    assert set(curated_records(paths)) == {FRA, JPN} and report["withdrawn"] == [BRA]
    assert curated_records(paths)[JPN] == rec(JPN)


def test_the_import_runs_the_builds_gate_and_writes_contract_fields_only(tmp_path):
    bad = candidate(FRA)
    bad["summary"] += " The server at 192.168.10.4 was reached."
    extra = candidate(POL, rationale="why the lane filed it", near_miss=True)
    extra["sources"][0]["notes_for_reviewer"] = "x"
    paths = make_queue(tmp_path, {"europe": [bad, extra]})
    report = run(paths)
    got = curated_records(paths)
    assert set(got) == {POL} and "gate: " in reasons(report, FRA) and "an IP address" in reasons(report, FRA)
    assert "rationale" not in got[POL] and "near_miss" not in got[POL]
    assert all("notes_for_reviewer" not in s for s in got[POL]["sources"])


def test_a_lanes_own_qualifier_word_is_written_in_the_vocabulary(tmp_path):
    c = candidate(FRA)
    c["civilian_service_impact"][0]["affected"]["qualifier"] = "roughly"
    paths = make_queue(tmp_path, {"europe": [c]})
    report = run(paths)
    assert curated_records(paths)[FRA]["civilian_service_impact"][0]["affected"]["qualifier"] == "about"
    assert report["notes"][FRA] == ["qualifier 'roughly' written as about"]
    # A qualifier beside no figure qualifies nothing: it is removed, and the report says so.
    c = candidate(POL)
    c["civilian_service_impact"][0]["affected"].update({"value": "unknown", "qualifier": "over"})
    paths = make_queue(tmp_path / "b", {"europe": [c]})
    report = run(paths)
    assert curated_records(paths)[POL]["civilian_service_impact"][0]["affected"]["qualifier"] is None
    assert "removed" in report["notes"][POL][0]


def test_a_lanes_hyphenated_sector_in_an_id_is_written_as_the_vocabulary_writes_it(tmp_path):
    lane_id = USA.replace("fuel_supply", "fuel-supply")
    assert lane_id != USA
    paths = make_queue(tmp_path, {"na": [candidate(USA, impact_id=lane_id)]})
    report = run(paths)
    assert set(curated_records(paths)) == {USA} and report["renamed"] == {f"na/{lane_id}": USA}


def test_a_hold_is_classified_from_its_reasons_not_from_the_names_of_the_review_roles():
    roles = {"disposition": "corrected", "roles": {"evidence": "accept", "safety": "accept_with_correction", "taxonomy": "accept"}}
    strict = _country_row("us-x", reason="Strict reading (iteration 20). Held: [C5-EXTENT] the source states extent, not a customer count.",
                          lead_hold={"iteration": 20, "basis": "strict reading of the inclusion clauses", "tag": "[C5-EXTENT]"},
                          independent_review=roles)
    assert I.hold_kind(strict, "us", {}, frozenset()) == "threshold"
    # A reason that even mentions an attack or the campaign rule is not a clear threshold hold.
    mention = _country_row("iq-x", reason="Below the threshold. Not an attack, so the campaign rule does not apply.")
    assert I.hold_kind(mention, "iq", {}, frozenset({"iq"})) == "campaign"
    assert I.hold_kind(mention, "us", {}, frozenset()) == "safety"
    owner = _country_row("ir-x", reason="Held by default under the plan; the lead's open decision.")
    assert I.hold_kind(owner, "ir", {}, frozenset({"ir"})) == "unclear"
    accepted_then_held = _country_row("kw-x", disposition="accept", reason="Below the threshold.")
    assert I.hold_kind(accepted_then_held, "kw", {}, frozenset()) == "unclear"
    dup = _country_row("us-y", disposition="duplicate", duplicate_of="us-x", reason="Same event.")
    assert I.hold_kind(dup, "us", {"us-x": strict}, frozenset()) == "threshold"
    assert "roles" in I.hold_fields(strict)["independent_review"]      # still copied to the local report


def test_a_record_in_a_campaign_system_loses_its_headlines(tmp_path):
    c = candidate(IRN)
    c["sources"][0]["title_en"] = "Synthetic headline"
    paths = make_queue(tmp_path, {"iran_power2": [c]})
    run(paths)
    assert "title_en" not in curated_records(paths)[IRN]["sources"][0]


def test_lanes_without_candidates_second_pass_lanes_and_unknown_side_files_are_tolerated(tmp_path):
    paths = make_queue(tmp_path, {"na": None, "na2": [candidate(USA)], "oceania2": []}, extra_files={
        "na/near_misses.json": [{"impact_id": "imp-x", "summary": "not a candidate"}],
        "social/addenda.json": {}, "social/lane_log.json": {"lane": "social", "source_families": [{"family": "x"}]},
        "social/scratchpad/notes.json": [1, 2],
        "na2/attribution_addenda.json": {"x": 1}, "na2/date_fixes.json": {"y": 2}, "na2/rationale.json": {USA: "why"}})
    report = run(paths)
    assert set(curated_records(paths)) == {USA}
    assert report["by_lane"]["na2"]["imported"] == 1 and report["refused"] == [] and report["not_reviewed"] == []
    # A folder with no candidates and no context entries is not a lane: found by looking, not by a list.
    assert [p.name for p in I.lane_dirs(paths["queue"])] == ["na2", "oceania2"]
    assert set(report["by_lane"]) == {"na2", "oceania2"} and report["research_log"]["lanes"] == []


def test_context_entries_need_two_roles_and_pass_the_context_gate(tmp_path):
    def raw(n):
        return {k: v for k, v in entry(n).items() if k not in ("review", "first_published")}
    good, bad, lonely = raw(0), raw(1), raw(2)
    bad["claim"] += " Cargoes were rerouted."
    paths = make_queue(tmp_path, {}, context={"hormuz": [good, bad, lonely]})
    doc = _json(review_file(paths, "safety", "hormuz"))
    del doc["verdicts"][lonely["id"]]
    review_file(paths, "safety", "hormuz").write_text(json.dumps(doc), encoding="utf-8")
    report = run(paths)
    entries = _json(paths["curated"] / "regional_context.json")["entries"]
    assert [e["id"] for e in entries] == [good["id"]] == report["context"]["imported"]
    assert entries[0]["first_published"] is None and entries[0]["review"]["roles"] == {"evidence": "accept", "safety": "accept"}
    why = {r["candidate_id"]: " | ".join(r["reasons"]) for r in report["context"]["refused"]}
    assert "aggregate only" in why[bad["id"]] and "not reviewed by safety" in why[lonely["id"]]


def test_the_research_note_takes_process_facts_only_from_each_lane_log(tmp_path):
    logs = {"europe": {"lane": "europe", "scope": "Europe, 2022-01-01 to 2026-11-19", "searches_used": 14,
                       "source_families": [
                           {"family": "National cyber agency archives", "method": "Enumerated the public incident archive.",
                            "what_was_enumerated": "412 notices", "window": "2022-01-01 to 2026-11-19", "status": "partial",
                            "limitation": "Two archives publish no dates."},
                           {"family": "Operator releases", "method": "Site search.", "window": "2025", "status": "partial",
                            "limitation": "Three candidates were held for review."}],
                       "unresolved_claims": ["a named claim"], "unfinished": ["a query"], "inaccessible_sources": ["a site"]},
            "ai": {"lane": "ai", "scope": "thematic", "source_families": []}}
    paths = make_queue(tmp_path, {"europe": [candidate(FRA)], "ai": []}, logs=logs)
    report = run(paths)
    lg = _json(paths["curated"] / "research_log.json")
    assert lg["source_families"] == [{"lane": "europe", "scope": "impacts", "research_pass": "i22-europe",
                                      "family": "National cyber agency archives",
                                      "method": "Enumerated the public incident archive.",
                                      "window": "2022-01-01 to 2026-11-19", "status": "partial",
                                      "limitation": "Two archives publish no dates."}]
    assert lg["regions_worked"] == ["Europe"] and lg["latest_research_date"] == "2026-11-19"
    assert lg["status"] == "expanding corpus"
    text = json.dumps(lg)
    assert not re.search(r"412|searches|unresolved|unfinished|inaccessible|named claim|held", text)
    assert report["research_log"]["families_dropped"][0]["family"] == "Operator releases"
    assert G.log_problems(lg) == []
    # Rerunning replaces the lane's entries; it does not append them again.
    run(paths)
    assert _json(paths["curated"] / "research_log.json") == lg


def test_the_import_never_writes_a_review_or_a_stamp_the_lane_supplied(tmp_path):
    c = candidate(FRA)
    c["review"] = {"reviewed_at": "2020-01-01", "review_status": "blind_reviewed",
                   "roles": {"evidence": "accept", "attribution_source": "accept", "safety": "accept"},
                   "ai_check": "not_applicable", "social_check": "not_applicable", "disposition": "confirmed"}
    c["first_published"] = "2020-01-01"
    paths = make_queue(tmp_path, {"europe": [c]}, reviews={role: {} for role in I.ROLE_ORDER})
    report = run(paths)
    assert curated_records(paths) == {} and report["not_reviewed"] == [{"lane": "europe", "candidate_id": FRA}]
    paths = make_queue(tmp_path / "b", {"europe": [c]})
    run(paths)
    got = curated_records(paths)[FRA]
    assert got["first_published"] is None and got["review"]["reviewed_at"] == "2026-11-19"


def test_the_real_queue_is_never_committed_and_never_read_by_the_build():
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/candidates/*" in ignore
    assert I.QUEUE == ROOT / "data" / "candidates" / "impacts22"
    run_py = (ROOT / "pipeline" / "run.py").read_text(encoding="utf-8")
    assert "import_impacts" not in run_py and "impacts22" not in run_py


# --- what the real review files do (lead's list, iteration 22) ---------------------------------------------

def test_a_lead_hold_refuses_a_record_whatever_the_reviewers_said_and_the_published_note_says_nothing(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), candidate(BRA)]},
                       extra_files={"lead_holds.json": {FRA: "Owner decision pending."}})
    report = run(paths)
    assert set(curated_records(paths)) == {BRA}
    assert "lead hold: Owner decision pending." in reasons(report, FRA)
    assert report["lead_holds"] == {"count": 1, "duplicates_across_lanes": 0, "safety_grounds": 0, "other_grounds": 1}
    # The published research note carries NUMBERS only: no reason, no lane, no id of what is held.
    note = _json(paths["curated"] / "research_log.json")
    assert note["lead_holds"] == {"held": 1, "duplicates_across_lanes": 0, "safety_grounds": 0, "other_grounds": 1}
    text = json.dumps(note)
    assert "Owner decision" not in text and FRA not in text and "europe" not in text
    assert G.log_problems(note) == []
    e, c, lg = G.load_curated(paths["curated"])
    served = G.build_payloads(e, c, lg, ctx(), AS_OF)[G.IMPACTS_OUT]["research"]
    assert served["holds_statement"] == "1 reviewed record is held by the lead and not published: 1 on other grounds."
    # A reason in words is refused in the note: a sentence can identify what a number cannot.
    for bad in ({**note, "lead_holds": {**note["lead_holds"], "reason": "x"}}, {**note, "lead_holds": "one held in Example"},
                {**note, "lead_holds": {**note["lead_holds"], "held": 5}}):
        assert any("lead_holds is numbers only" in p for p in G.log_problems(bad))
    # Lifting the hold takes the count out again.
    (paths["queue"] / "lead_holds.json").write_text(json.dumps({"holds": {}}), encoding="utf-8")
    run(paths)
    assert "lead_holds" not in _json(paths["curated"] / "research_log.json") and set(curated_records(paths)) == {FRA, BRA}
    # A record imported earlier and held now is withdrawn.
    other = make_queue(tmp_path / "b", {"europe": [candidate(FRA)]})
    run(other)
    (other["queue"] / "lead_holds.json").write_text(json.dumps({FRA: "Held."}), encoding="utf-8")
    assert run(other)["withdrawn"] == [FRA] and curated_records(other) == {}


def test_opened_falls_back_to_the_lanes_own_record_only_where_the_reviewer_lists_nothing(tmp_path):
    c = candidate(FRA)
    c["sources"][0]["opened"], c["sources"][1]["opened"] = True, "yes"
    c["sources"][2]["opened"], c["sources"][3]["opened"] = False, None
    paths = make_queue(tmp_path, {"europe": [c]})
    doc = _json(review_file(paths, "evidence", "europe"))
    del doc["verdicts"][FRA]["sources_opened"]
    review_file(paths, "evidence", "europe").write_text(json.dumps(doc), encoding="utf-8")
    run(paths)
    got = {s["ref"]: s["opened"] for s in curated_records(paths)[FRA]["sources"]}
    assert got == {"s1": True, "s2": False, "s3": False, "s4": False}


def test_a_removed_source_takes_its_citations_with_it_and_a_record_left_with_none_is_refused(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), candidate(DEU)]})
    # One verdict both corrects and removes s2; a later role corrects it again: neither is an error.
    edit_review(paths, "evidence", "europe", FRA, verdict="accept_with_correction",
                set={"sources[s2].language": "fr"}, remove_sources=["s2"])
    edit_review(paths, "safety", "europe", FRA, set={"sources[s2].derived_claim": "Reworded."})
    edit_review(paths, "evidence", "europe", DEU, verdict="accept_with_correction", remove_sources=["s1", "s2"])
    report = run(paths)
    got = curated_records(paths)
    assert set(got) == {FRA}
    assert [s["ref"] for s in got[FRA]["sources"]] == ["s1", "s3", "s4"]
    assert got[FRA]["civilian_service_impact"][0]["source_refs"] == ["s1"]
    assert "no source" in reasons(report, DEU)


def test_a_citation_the_reviewers_narrowed_is_no_longer_cited_for_that_claim(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA)]})
    edit_review(paths, "attribution_source", "europe", FRA, verdict="accept_with_correction",
                set={"sources[s2].supports": ["occurrence"]})
    report = run(paths)
    got = curated_records(paths)[FRA]
    assert got["civilian_service_impact"][0]["source_refs"] == ["s1"]
    assert "a source no longer cited for a claim it does not support" in report["notes"][FRA]


def test_set_paths_take_list_indexes_and_a_null_on_a_stray_key_deletes_it(tmp_path):
    c = candidate(FRA, lane_flags=["check date"], date_end="unknown")
    c["attribution"]["competing"] = [{"actor": "Example Group Z", "note": "SYNTHETIC. Another firm named Example Group Z.",
                                      "status": "SUSPECTED", "basis": ["cybersecurity_firm"], "source_refs": ["s4"]}]
    c["sources"][0]["access_note"] = "opened on the second try"
    paths = make_queue(tmp_path, {"europe": [c]})
    edit_review(paths, "safety", "europe", FRA, verdict="accept_with_correction",
                set={"lane_flags": None, "sources[3].attribution_basis": "cyber_firm",
                     "civilian_service_impact[0].affected.value": 118000})
    report = run(paths)
    got = curated_records(paths)[FRA]
    assert "lane_flags" not in got and got["date_end"] is None
    assert got["civilian_service_impact"][0]["affected"]["value"] == 118000
    assert got["sources"][3]["attribution_basis"] == "cybersecurity_firm"
    assert got["attribution"]["competing"] == [{"actor": "Example Group Z", "basis": ["cybersecurity_firm"], "source_refs": ["s4"],
                                                "statement": "SYNTHETIC. Another firm named Example Group Z."}]
    notes = " | ".join(report["notes"][FRA])
    assert "lane_flags" in notes and "sources.access_note" in notes and "written as null" in notes


def test_a_dispute_that_is_not_an_object_is_refused_not_crashed_on(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(BRA, dispute="the regulator disagrees")]})
    report = run(paths)
    assert curated_records(paths) == {} and "dispute needs about" in reasons(report, BRA)
    r = rec(BRA)
    r["dispute"] = "the regulator disagrees"
    refused(r, "dispute needs about")


def test_a_reported_self_claim_makes_a_claimed_attribution_claim_only():
    r = rec(ITA)
    r["sources"][1] = {**rec(FRA)["sources"][1], "ref": "s2", "supports": ["attribution"], "attribution_basis": "actor_self_claim"}
    r["review"]["social_check"] = "not_applicable"
    assert problems(r) == []
    assert EC.attribution_confidence(r["attribution"], r["sources"]) == "CLAIM_ONLY"
    # An abstracted attack record may carry an attribution a cited source states.
    k = rec(UKR)
    k["attribution"] = {"status": "ASSESSED", "actor": "Example State", "actor_type": "state", "basis": ["government"],
                        "as_of": "2025-10-08", "statement": "SYNTHETIC. The ministry attributed the attack to Example State.",
                        "competing": [], "source_refs": ["s1"]}
    k["sources"][0]["supports"] = ["occurrence", "effect", "attribution"]
    assert problems(k) == []


def test_an_attempt_filed_with_a_basis_or_an_impact_row_loses_them_at_import(tmp_path):
    c = candidate(NLD, inclusion_basis=5, civilian_service_impact=copy.deepcopy(rec(ITA)["civilian_service_impact"]))
    paths = make_queue(tmp_path, {"europe": [c]})
    run(paths)
    got = curated_records(paths)[NLD]
    assert got["inclusion_basis"] is None and got["civilian_service_impact"] == []


def _addendum(ref="s9"):
    return {"ref": ref, "url": "https://social-platform.example/synthetic/post/9009", "publisher": "Example Utility (official account)",
            "date": "2025-03-05", "language": "fr", "source_role": "operator", "medium": "social",
            "social": {"platform": "Example Platform", "handle": "@example_utility", "display_name": "Example Utility",
                       "account_tier": "S1", "identity_basis": "Linked from the operator's own site (synthetic).",
                       "posted_at": "2025-03-05T08:00:00Z"},
            "supports": ["occurrence"], "opened": False, "derived_claim": "Synthetic: the operator's account announces the incident."}


def test_a_social_addendum_is_added_only_when_every_role_accepted_it_and_its_record_was_imported(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), candidate(BRA), candidate(DEU)]}, extra_files={
        "social/addenda.json": {FRA: [_addendum("s9"), _addendum("s8")], BRA: [_addendum("s9")], DEU: [_addendum("s9")]}})
    edit_review(paths, "safety", "europe", DEU, verdict="reject", reason="Fails abstraction.")
    assert I.ADDENDA_ROLES == ("attribution_source", "safety"), "the social check and safety, not the evidence role"
    for role in I.ADDENDA_ROLES:
        verdicts = accept([f"{FRA}#s9", f"{DEU}#s9"], **({"sources_opened": ["s9"]} if role == "attribution_source" else {}))
        verdicts[f"{FRA}#s8"] = {"verdict": "reject" if role == "safety" else "accept", "reason": "Not the official account."}
        path = review_file(paths, role, "social")
        path.write_text(json.dumps({"lane": "social", "role": role, "reviewed_at": "2026-11-19", "verdicts": verdicts}), encoding="utf-8")
    report = run(paths)
    got = curated_records(paths)
    assert set(got) == {FRA, BRA}
    added = next(s for s in got[FRA]["sources"] if s["ref"] == "s9")
    assert added["opened"] is True and added["social"]["account_tier"] == "S1"
    assert [s["ref"] for s in got[FRA]["sources"]] == ["s1", "s2", "s3", "s4", "s9"]
    assert got[FRA]["review"]["social_check"] == "passed"
    assert [s["ref"] for s in got[BRA]["sources"]] == ["s1", "s2"]            # its addendum was never reviewed
    outcomes = {(a["candidate_id"], a["ref"]): a["outcome"] for a in report["addenda"]}
    assert outcomes[(FRA, "s9")] == "added" and "rejected by safety" in outcomes[(FRA, "s8")]
    assert outcomes[(BRA, "s9")] == "not added: not reviewed" and (DEU, "s9") not in outcomes
    run(paths)
    assert curated_records(paths) == got


def test_a_dry_run_reports_everything_and_writes_nothing(tmp_path, capsys):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), candidate(BRA)]})
    edit_review(paths, "safety", "europe", BRA, verdict="reject", reason="Fails abstraction.")
    before = {p: p.read_bytes() for p in paths["curated"].iterdir()}
    report = I.run(date=DAY1, ctx=ctx(), key=KEY, write=False, **paths)
    assert report["imported"] == [FRA] and "Fails abstraction." in reasons(report, BRA)
    assert {p: p.read_bytes() for p in paths["curated"].iterdir()} == before
    assert not (paths["queue"] / "import_report.json").exists()
    I.print_report(report)
    out = capsys.readouterr().out
    assert "europe: 1 imported, 1 refused, 0 not reviewed" in out and "rejected by safety: Fails abstraction." in out
    assert "--dry-run" in (ROOT / "scripts" / "import_impacts.py").read_text(encoding="utf-8")


def test_authority_order_is_a_cause_that_is_not_malicious_and_not_cyber():
    r = rec(POL)
    r.update({"cause_family": "authority_order", "cyber_mechanism": None, "attribution": rec(BRA)["attribution"],
              "summary": "SYNTHETIC FIXTURE. Mobile internet in Poland was shut down by order of the Example Ministry during an exam period.",
              "sources": [rec(POL)["sources"][0]]})
    r["sources"][0]["supports"] = ["occurrence", "effect"]
    r["civilian_service_impact"][0]["source_refs"] = ["s1"]
    r["review"]["social_check"] = "not_applicable"
    assert problems(r) == [] and G.digital_category(r) is None
    r["attribution"] = rec(USA)["attribution"]
    refused(r, "on a record that is not a malicious act")
    assert "authority_order" in G.NOT_MALICIOUS and "authority_order" not in G.MALICIOUS


# --- the lead's normalisation pass -----------------------------------------------------------------------------

LEAD_DAY = "2026-11-21"
ESP = "imp-2025-12-01-esp-wastewater-synthetic-plant-disruption"


def lead_file(paths, lane, verdicts, reviewed_at=LEAD_DAY):
    path = review_file(paths, "lead", lane)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"lane": lane, "role": "lead", "verdicts": verdicts}
    if reviewed_at:
        doc["reviewed_at"] = reviewed_at
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def normalise(**changes):
    return {"verdict": "accept_with_correction", **changes}


def test_the_leads_normalisation_applies_after_safety_and_the_review_block_says_so(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), candidate(BRA)]})
    edit_review(paths, "safety", "europe", FRA, verdict="accept_with_correction", set={"summary": "SYNTHETIC. The safety reviewer's wording."})
    lead_file(paths, "europe", {FRA: normalise(set={"summary": "SYNTHETIC. The lead's spelling of the same sentence."},
                                               reason="Vocabulary.")})
    report = run(paths)
    got = curated_records(paths)
    assert got[FRA]["summary"] == "SYNTHETIC. The lead's spelling of the same sentence."
    review = got[FRA]["review"]
    assert review["lead_normalisation"] is True and review["lead_normalisation_at"] == LEAD_DAY
    assert review["reviewed_at"] == "2026-11-19" and review["disposition"] == "corrected"
    # The lead is not a role and changes no verdict.
    assert review["roles"] == {"evidence": "accept", "attribution_source": "accept", "safety": "accept_with_correction"}
    assert "lead_normalisation" not in got[BRA]["review"] and got[BRA]["review"]["disposition"] == "confirmed"
    assert report["lead_normalised"] == [f"europe/{FRA}"]
    assert G.record_problems(list(got.values()), ctx()) == []
    run(paths)
    assert curated_records(paths) == got


@pytest.mark.parametrize("role", ["evidence", "attribution_source", "safety"])
def test_the_leads_normalisation_cannot_rescue_a_record_a_role_rejected_or_did_not_review(tmp_path, role):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), candidate(BRA)]})
    edit_review(paths, role, "europe", FRA, verdict="reject", reason="Fails the contract.")
    doc = _json(review_file(paths, role, "europe"))
    del doc["verdicts"][BRA]
    review_file(paths, role, "europe").write_text(json.dumps(doc), encoding="utf-8")
    lead_file(paths, "europe", {FRA: normalise(set={"summary": "SYNTHETIC. Rewritten."}), BRA: normalise(set={"summary": "SYNTHETIC. Rewritten."})})
    report = run(paths)
    assert curated_records(paths) == {}
    assert f"rejected by {role}: Fails the contract." in reasons(report, FRA) and f"not reviewed by {role}" in reasons(report, BRA)
    assert report["lead_normalised"] == []


@pytest.mark.parametrize("patch,why", [
    ({"verdict": "accept", "set": {"summary": "SYNTHETIC. Rewritten."}}, "its verdict is 'accept'"),
    ({"verdict": "reject", "reason": "The lead disagrees."}, "its verdict is 'reject'"),
    ({"set": {"summary": "SYNTHETIC. Rewritten."}}, "its verdict is None"),
    (normalise(sources_opened=["s1"]), "a normalisation has `set`, `remove_sources` and `add_sources` only"),
    (normalise(set={"admin1": {"code": "FR-IDF", "name": "Île-de-France"}, "geographic_precision": "admin1"}),
     "it would give a region to a record the reviewers accepted without one"),
    (normalise(set={"no_such_list[3].x": 1}), "lead correction could not be applied"),
])
def test_a_lead_patch_that_oversteps_refuses_the_record(tmp_path, patch, why):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), candidate(BRA)]})
    lead_file(paths, "europe", {FRA: patch})
    report = run(paths)
    assert set(curated_records(paths)) == {BRA}
    assert why in reasons(report, FRA) and ("lead normalisation refused" in reasons(report, FRA) or "lead correction" in reasons(report, FRA))


def test_a_lead_file_without_a_date_refuses_its_patches(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA)]})
    lead_file(paths, "europe", {FRA: normalise(set={"summary": "SYNTHETIC. Rewritten."})}, reviewed_at=None)
    assert "the lead's file gives no reviewed_at date" in reasons(run(paths), FRA) and curated_records(paths) == {}


def test_a_lead_patch_cannot_change_an_attacks_cause_or_weaken_an_abstracted_records_policy(tmp_path):
    attack = _attack_candidate()
    factor = candidate(BRA, contributing_factors=["sabotage"])
    paths = make_queue(tmp_path, {"eurasia": [attack], "europe": [candidate(BRA, publication_policy="country_abstracted")],
                                  "asia": [factor]})
    lead_file(paths, "eurasia", {attack["impact_id"]: normalise(set={"cause_family": "industrial_technical"})})
    lead_file(paths, "europe", {BRA: normalise(set={"publication_policy": "standard"})})
    lead_file(paths, "asia", {BRA: normalise(set={"contributing_factors": []})})
    report = run(paths)
    assert curated_records(paths) == {}
    why = {r["lane"]: " | ".join(r["reasons"]) for r in report["refused"]}
    assert "it would change the cause of a kinetic or sabotage record" in why["eurasia"]
    assert "it would publish a country-abstracted record at a weaker policy" in why["europe"]
    assert "it would change the cause of a kinetic or sabotage record" in why["asia"]


def test_a_lead_patch_cannot_mark_a_source_opened(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA)]})
    edit_review(paths, "evidence", "europe", FRA, sources_opened=["s1", "s2", "s3"])
    lead_file(paths, "europe", {FRA: normalise(set={"sources[s4].opened": True, "sources[s4].publisher": "Example Agency"})})
    run(paths)
    s4 = next(x for x in curated_records(paths)[FRA]["sources"] if x["ref"] == "s4")
    assert s4["opened"] is False and s4["publisher"] == "Example Agency"


def _added(ref="s9", **changes):
    src = {"ref": ref, "url": "https://example.org/synthetic/later-operator-statement", "publisher": "Example Operator",
           "date": "2025-03-20", "language": "en", "source_role": "operator", "medium": "web", "social": None,
           "supports": ["effect"], "opened": True,
           "derived_claim": "SYNTHETIC. A later operator statement that service had come back."}
    src.update(changes)
    return src


def test_a_lead_patch_can_append_a_source_never_opened_and_never_in_place_of_one(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA)]})
    before = {s["ref"]: s for s in rec(FRA)["sources"]}
    lead_file(paths, "europe", {FRA: normalise(add_sources=[_added(added_by=None)], reason="Dates the observed end.")})
    run(paths)
    got = {s["ref"]: s for s in curated_records(paths)[FRA]["sources"]}
    # Appended, and opened is false whatever the patch said: the lead is not the evidence reviewer.
    # It is marked as the lead's, whatever the patch said, so it never counts as a reviewed origin.
    assert set(got) == set(before) | {"s9"} and got["s9"]["opened"] is False and got["s9"]["added_by"] == "lead"
    assert all("added_by" not in got[ref] for ref in before)
    assert got["s9"]["url"] == _added()["url"]
    for ref, s in before.items():
        assert {k: v for k, v in got[ref].items() if k != "opened"} == {k: v for k, v in s.items() if k != "opened"}


@pytest.mark.parametrize("added,why", [
    ([_added(ref="s1")], "reuses a ref the record already has or had"),
    ([_added(url=None)], "added source 's9': source 's9': no url"),
    ([_added(medium="pamphlet")], "medium 'pamphlet' is not in the vocabulary"),
    ([_added(url="https://x.com/example/status/1")], "medium must be 'social'"),
    ([_added(supports=[])], "supports [] must name at least one of"),
    ([_added(date="20 March")], "is not a date"),
    ([_added(), _added(ref="s10")], "repeats an address the record already cites"),
    ({"ref": "s9"}, "add_sources is a non-empty list of sources"),
])
def test_a_source_the_lead_appends_runs_through_every_source_validator(tmp_path, added, why):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), candidate(BRA)]})
    lead_file(paths, "europe", {FRA: normalise(add_sources=added)})
    report = run(paths)
    assert set(curated_records(paths)) == {BRA}
    assert "lead normalisation refused" in reasons(report, FRA) and why in reasons(report, FRA)


def test_a_lead_patch_cannot_reuse_the_ref_of_a_source_it_removes(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(FRA)]})
    lead_file(paths, "europe", {FRA: normalise(remove_sources=["s4"], add_sources=[_added(ref="s4")])})
    assert "reuses a ref the record already has or had" in reasons(run(paths), FRA)
    assert curated_records(paths) == {}


@pytest.mark.parametrize("renamer", ["safety", "lead"])
def test_a_record_served_under_a_reviewers_or_the_leads_name_and_then_held_is_withdrawn(tmp_path, renamer):
    # Found in the iteration-22 closure: a hold refused the candidate before its new name was read, so
    # the record served under that name stayed in the curated file as if it came from elsewhere.
    # Written with a stem the import rewrites (no day), as the served case was: the record is served
    # under the rebuilt name, which is neither the filed id nor the name as the reviewer typed it.
    typed = "imp-2025-03-fra-electricity-synthetic-renamed-record"
    renamed = "imp-2025-03-05-fra-electricity-synthetic-renamed-record"
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), candidate(BRA)]})
    if renamer == "lead":
        lead_file(paths, "europe", {FRA: normalise(set={"impact_id": typed})})
    else:
        edit_review(paths, "safety", "europe", FRA, verdict="accept_with_correction", set={"impact_id": typed})
    run(paths)
    assert set(curated_records(paths)) == {renamed, BRA}
    (paths["queue"] / "lead_holds.json").write_text(json.dumps({"holds": {f"europe/{FRA}": "Owner decision pending."}}),
                                                     encoding="utf-8")
    report = run(paths)
    assert set(curated_records(paths)) == {BRA} and report["withdrawn"] == [renamed]


def test_a_lead_patch_can_say_a_page_is_undated_and_nothing_else_makes_a_source_dateless(tmp_path):
    undated = candidate(BRA)
    undated["sources"][1]["date"] = None
    paths = make_queue(tmp_path, {"europe": [undated]})
    assert "source 's2': no date" in reasons(run(paths), BRA)
    lead_file(paths, "europe", {BRA: normalise(set={"sources[s2].date_basis": "undated_page"})})
    run(paths)
    s2 = curated_records(paths)[BRA]["sources"][1]
    assert s2["date"] is None and s2["date_basis"] == "undated_page"
    assert "date_basis" not in curated_records(paths)[BRA]["sources"][0]


def test_the_leads_normalisation_works_for_context_entries_with_their_two_roles(tmp_path):
    def raw(n):
        return {k: v for k, v in entry(n).items() if k not in ("review", "first_published")}
    fixed, untouched, rejected = raw(2), raw(3), raw(1)
    fixed["metric"]["value_upper"] = 12
    paths = make_queue(tmp_path, {}, context={"hormuz": [fixed, untouched, rejected]})
    edit_review(paths, "safety", "hormuz", rejected["id"], verdict="reject", reason="Names a route.")
    report = run(paths)
    why = {r["candidate_id"]: " | ".join(r["reasons"]) for r in report["context"]["refused"]}
    assert "value_upper is given for a range, and only for a range" in why[fixed["id"]]
    lead_file(paths, "hormuz", {fixed["id"]: normalise(set={"metric.value_upper": None}),
                                rejected["id"]: normalise(set={"claim": "Rewritten."})})
    report = run(paths)
    entries = {e["id"]: e for e in _json(paths["curated"] / "regional_context.json")["entries"]}
    assert set(entries) == {fixed["id"], untouched["id"]}
    assert entries[fixed["id"]]["review"] == {"reviewed_at": "2026-11-19", "roles": {"evidence": "accept", "safety": "accept"},
                                              "lead_normalisation": True, "lead_normalisation_at": LEAD_DAY}
    assert entries[fixed["id"]]["metric"]["value_upper"] is None
    assert "lead_normalisation" not in entries[untouched["id"]]["review"]
    assert "rejected by safety" in " | ".join(next(r for r in report["context"]["refused"] if r["candidate_id"] == rejected["id"])["reasons"])
    e, c, lg = G.load_curated(paths["curated"])
    assert G.context_problems(c["entries"]) == []


# --- what shape() writes mechanically ---------------------------------------------------------------------------

def test_an_abstracted_energy_record_that_names_no_technology_says_it_is_withheld(tmp_path):
    attack = _attack_candidate()
    attack["technology"] = None
    named = candidate(BRA, publication_policy="country_abstracted")
    paths = make_queue(tmp_path, {"eurasia": [attack], "europe": [named, candidate(JPN, publication_policy="country_abstracted")]})
    report = run(paths)
    got = {r["country_a3"]: r for r in curated_records(paths).values()}
    assert got["UKR"]["technology"] == "withheld" and got["BRA"]["technology"] == "transmission"
    assert got["JPN"]["technology"] is None                     # not an energy record: not applicable stays null
    assert any("technology written as withheld" in n for n in report["notes"][got["UKR"]["impact_id"]])
    # A record that is NOT abstracted is not helped: its technology is a reviewer's to state.
    plain = candidate(BRA, technology=None)
    other = make_queue(tmp_path / "b", {"europe": [plain]})
    assert "an energy record names a technology or says why not" in reasons(run(other), BRA)


def test_an_empty_or_unknown_end_date_is_written_as_null(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(BRA, date_end=""), candidate(POL, date_end="unknown")]})
    run(paths)
    got = curated_records(paths)
    assert got[BRA]["date_end"] is None and got[POL]["date_end"] is None


def test_unknown_attribution_on_a_cause_that_is_not_malicious_is_written_not_applicable_and_never_the_reverse(tmp_path):
    storm = candidate(BRA)
    storm["attribution"].update({"status": "UNKNOWN", "actor": "Nobody", "actor_type": "unknown"})
    intrusion = candidate(FRA)
    intrusion["attribution"] = copy.deepcopy(rec(BRA)["attribution"])       # NOT_APPLICABLE on a cyberattack
    unknown_cause = candidate("imp-2024-05-zaf-municipal_services-synthetic-city-systems")
    paths = make_queue(tmp_path, {"europe": [storm, intrusion], "africa_latam": [unknown_cause]})
    report = run(paths)
    got = curated_records(paths)
    a = got[BRA]["attribution"]
    assert (a["status"], a["actor"], a["actor_type"]) == ("NOT_APPLICABLE", None, None)
    assert any("written as NOT_APPLICABLE" in n for n in report["notes"][BRA])
    assert FRA not in got and "attribution is NOT_APPLICABLE on a malicious act" in reasons(report, FRA)
    # A cause nobody has established is neither: its UNKNOWN stays UNKNOWN.
    assert got[unknown_cause["impact_id"]]["attribution"]["status"] == "UNKNOWN"


def test_a_competing_attribution_whose_source_did_not_survive_is_dropped_and_said(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(ESP)]})
    run(paths)
    assert len(curated_records(paths)[ESP]["attribution"]["competing"]) == 2
    edit_review(paths, "safety", "europe", ESP, verdict="accept_with_correction", remove_sources=["s3"])
    r = I.apply_reviews(candidate(ESP), {role: _json(review_file(paths, role, "europe"))["verdicts"][ESP] for role in I.ROLE_ORDER})[0]
    notes = []
    I.normalise(r, notes)
    assert [c["source_refs"] for c in r["attribution"]["competing"]] == [["s2"]]
    assert any("1 competing attribution(s) dropped" in n for n in notes)
    # With every competing attribution gone a DISPUTED status no longer stands, and the gate says so.
    edit_review(paths, "safety", "europe", ESP, remove_sources=["s2", "s3"])
    report = run(paths)
    assert curated_records(paths) == {} and "DISPUTED" in reasons(report, ESP)


def test_a_date_written_at_coarser_precision_moves_the_ids_date_segment(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(BRA)]})
    edit_review(paths, "evidence", "europe", BRA, verdict="accept_with_correction", set={"date_precision": "month"})
    report = run(paths)
    new = "imp-2024-07-bra-electricity-synthetic-storm-blackout"
    assert set(curated_records(paths)) == {new} and curated_records(paths)[new]["date"] == "2024-07"
    assert report["renamed"] == {f"europe/{BRA}": new}


# --- social addenda follow the surviving record ---------------------------------------------------------------

def _social_reviews(paths, keys):
    for role in I.ADDENDA_ROLES:
        verdicts = accept(keys, **({"sources_opened": [k.split("#")[1] for k in keys]} if role == "evidence" else {}))
        review_file(paths, role, "social").write_text(json.dumps(
            {"lane": "social", "role": role, "reviewed_at": "2026-11-19", "verdicts": verdicts}), encoding="utf-8")


def test_addenda_of_a_copy_held_as_a_duplicate_go_to_the_record_that_survives(tmp_path):
    twin = candidate(FRA, impact_id="imp-2025-03-06-fra-electricity-synthetic-other-lane-copy", date="2025-03-06")
    tid = twin["impact_id"]
    other = _addendum("s1")                         # the survivor already has an s1: the moved source is renumbered
    other["url"] = "https://social-platform.example/synthetic/post/7007"
    paths = make_queue(tmp_path, {"europe": [candidate(FRA)], "ai": [twin]}, extra_files={
        "lead_holds.json": {"holds": {f"ai/{tid}": f"lead hold: duplicate of europe/{FRA} (better sourced)"}},
        "social/addenda.json": {FRA: [_addendum("s9")], tid: [other, _addendum("s8")]}})
    _social_reviews(paths, [f"{FRA}#s9", f"{tid}#s1", f"{tid}#s8"])
    report = run(paths)
    got = curated_records(paths)
    assert set(got) == {FRA}
    assert "lead hold: duplicate of europe/" in reasons(report, tid) and "lead hold: lead hold" not in reasons(report, tid)
    urls = {s["ref"]: s["url"] for s in got[FRA]["sources"]}
    assert urls["s9"].endswith("/9009") and urls["s5"].endswith("/7007") and len(urls) == 6
    outcomes = {(a["ref"], a.get("moved_from")): a["outcome"] for a in report["addenda"]}
    assert outcomes[("s9", None)] == "added" and outcomes[("s5", f"ai/{tid}")] == "added"
    # The same address twice is one source: the held copy's second addendum repeats the survivor's own.
    assert outcomes[("s8", f"ai/{tid}")] == "not added: the record already cites this address"
    assert report["lead_holds"]["duplicates_across_lanes"] == 1
    assert G.record_problems(list(got.values()), ctx()) == []
    run(paths)
    assert curated_records(paths) == got


def test_addenda_of_a_held_copy_stay_put_when_the_hold_names_no_survivor_or_they_were_not_accepted(tmp_path):
    twin = candidate(FRA, impact_id="imp-2025-03-06-fra-electricity-synthetic-other-lane-copy", date="2025-03-06")
    tid = twin["impact_id"]
    other = _addendum("s7")
    other["url"] = "https://social-platform.example/synthetic/post/7007"
    paths = make_queue(tmp_path, {"europe": [candidate(FRA)], "ai": [twin]}, extra_files={
        "lead_holds.json": {"holds": {f"ai/{tid}": "Owner decision pending."}}, "social/addenda.json": {tid: [other]}})
    _social_reviews(paths, [f"{tid}#s7"])
    report = run(paths)
    assert [s["ref"] for s in curated_records(paths)[FRA]["sources"]] == ["s1", "s2", "s3", "s4"] and report["addenda"] == []
    # Named as the survivor, but a role rejected the addendum: it is not added.
    (paths["queue"] / "lead_holds.json").write_text(json.dumps({"holds": {f"ai/{tid}": f"duplicate of europe/{FRA}"}}), encoding="utf-8")
    edit_review(paths, "safety", "social", f"{tid}#s7", verdict="reject", reason="Not the official account.")
    report = run(paths)
    assert [s["ref"] for s in curated_records(paths)[FRA]["sources"]] == ["s1", "s2", "s3", "s4"]
    assert "rejected by safety" in report["addenda"][0]["outcome"] and report["addenda"][0]["moved_from"] == f"ai/{tid}"


def test_regional_context_names_its_group_from_the_registry():
    """The served context file names the registry group it describes, so no page pairs a file and a
    group by hand; exactly one registry group names this file."""
    from pipeline import systems
    got = payloads()[G.CONTEXT_OUT]
    assert got["group"] == G.context_group()
    assert systems.GROUPS[got["group"]]["regional_context"] == G.CONTEXT_OUT
    assert [g for g, d in systems.GROUPS.items() if d.get("regional_context")] == [got["group"]]


# --- iteration-22 release closure: first_published means first SERVED (B1) -----------------------------

def test_the_import_never_writes_its_run_date_as_first_published(tmp_path):
    """Imported is not published. Whatever --date the import runs with, a new record or context entry
    is pending (null) until a release serves it, and a change before that release is no revision."""
    raw = {k: v for k, v in entry().items() if k not in ("review", "first_published")}
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), candidate(BRA)]}, context={"hormuz": [raw]})
    run(paths, date=DAY2)
    text = (paths["curated"] / "events.json").read_text(encoding="utf-8")
    text += (paths["curated"] / "regional_context.json").read_text(encoding="utf-8")
    assert DAY2 not in text
    got = curated_records(paths)
    assert all(r["first_published"] is None for r in got.values())
    edit_review(paths, "safety", "europe", FRA, verdict="accept_with_correction",
                set={"summary": "SYNTHETIC FIXTURE. Reworded before the first release."})
    run(paths, date="2026-12-01")
    got = curated_records(paths)
    assert got[FRA]["summary"].endswith("first release.")
    assert got[FRA]["first_published"] is None and "last_revised" not in got[FRA]
    e, c, lg = G.load_curated(paths["curated"])
    assert G.gate(e, c, lg, ctx()) == []
    served = G.build_payloads(e, c, lg, ctx(), AS_OF)
    # Served as null, never as an invented date.
    assert all(r["first_published"] is None for r in served[G.IMPACTS_OUT]["records"])
    assert all(x["first_published"] is None for x in served[G.CONTEXT_OUT]["entries"])
    assert "pending its first release" in served[G.IMPACTS_OUT]["field_notes"]["first_published"]


def _stamp_dir(tmp_path):
    e, c, _ = docs()
    for r in e["records"]:
        r.pop("last_revised", None)
    e["records"][0]["first_published"] = "2026-11-12"
    for r in e["records"][1:]:
        r["first_published"] = None
    c["entries"][0]["first_published"] = "2026-11-10"
    for x in c["entries"][1:]:
        x["first_published"] = None
    tmp_path.mkdir(parents=True, exist_ok=True)
    S.write_json(tmp_path / "events.json", e)
    S.write_json(tmp_path / "regional_context.json", c)
    return tmp_path, len(e["records"]), len(c["entries"])


def test_stamp_first_published_fills_nulls_only_and_is_idempotent(tmp_path):
    d, n_rec, n_ctx = _stamp_dir(tmp_path)
    before = (d / "events.json").read_bytes()
    counts = S.stamp(DAY1, curated=d, write=False)
    assert counts == {"events.json": {"stamped": n_rec - 1, "kept": 1},
                      "regional_context.json": {"stamped": n_ctx - 1, "kept": 1}}
    assert (d / "events.json").read_bytes() == before, "a dry run wrote"
    S.stamp(DAY1, curated=d)
    recs = _json(d / "events.json")["records"]
    assert recs[0]["first_published"] == "2026-11-12", "a date already there was overwritten"
    assert all(r["first_published"] == DAY1 for r in recs[1:])
    ents = _json(d / "regional_context.json")["entries"]
    assert ents[0]["first_published"] == "2026-11-10" and all(x["first_published"] == DAY1 for x in ents[1:])
    once = [(d / n).read_bytes() for n in ("events.json", "regional_context.json")]
    assert S.stamp(DAY2, curated=d) == {"events.json": {"stamped": 0, "kept": n_rec},
                                        "regional_context.json": {"stamped": 0, "kept": n_ctx}}
    assert [(d / n).read_bytes() for n in ("events.json", "regional_context.json")] == once
    assert all(b"\r" not in b for b in once)
    _, _, lg = docs()
    assert G.gate(_json(d / "events.json"), _json(d / "regional_context.json"), lg, ctx()) == []


@pytest.mark.parametrize("bad", ["2026-13-01", "20261120", "tomorrow", "2026-11-1", "", "2026-02-30"])
def test_stamp_first_published_refuses_a_malformed_date(tmp_path, bad):
    d, _, _ = _stamp_dir(tmp_path)
    before = (d / "events.json").read_bytes()
    with pytest.raises(ValueError, match="is not a YYYY-MM-DD date"):
        S.stamp(bad, curated=d)
    assert (d / "events.json").read_bytes() == before


def test_stamp_first_published_refuses_to_go_backwards(tmp_path):
    d, _, _ = _stamp_dir(tmp_path)
    before = [(d / n).read_bytes() for n in ("events.json", "regional_context.json")]
    # The newest date already there is 2026-11-12 (a record); an entry's older date does not lower the bar.
    with pytest.raises(ValueError, match="before 2026-11-12"):
        S.stamp("2026-11-11", curated=d)
    assert [(d / n).read_bytes() for n in ("events.json", "regional_context.json")] == before
    assert S.stamp("2026-11-12", curated=d)["events.json"]["stamped"] > 0      # the same day is not backwards


def test_the_committed_corpus_dates_first_published_or_leaves_it_pending():
    e, c, _ = G.load_curated()
    for row in e["records"] + c["entries"]:
        assert row.get("first_published") is None or G._date_ok(row["first_published"])
        assert not ("last_revised" in row and row.get("first_published") is None)


def test_a_reimport_of_a_pending_record_or_entry_keeps_it_pending(tmp_path):
    """After the migration every curated record and entry is pending (null). The next real import must
    keep each one null, changed or not, and add no last_revised: the old stamp wrote the run date onto
    anything whose first_published was empty."""
    raw = {k: v for k, v in entry().items() if k not in ("review", "first_published")}
    paths = make_queue(tmp_path, {"europe": [candidate(FRA), candidate(BRA)]}, context={"hormuz": [raw]})
    run(paths)
    # The curated files as the migration leaves them: a pending record that was once given a run date.
    events = _json(paths["curated"] / "events.json")
    assert all(r["first_published"] is None for r in events["records"])
    edit_review(paths, "safety", "europe", FRA, verdict="accept_with_correction",
                set={"summary": "SYNTHETIC FIXTURE. Reworded at the re-import."})
    run(paths, date=DAY2)
    got = curated_records(paths)
    assert got[FRA]["summary"].endswith("re-import.")
    for r in got.values():
        assert r["first_published"] is None and "last_revised" not in r, r["impact_id"]
    ent = _json(paths["curated"] / "regional_context.json")["entries"][0]
    assert ent["first_published"] is None and "last_revised" not in ent


# --- iteration-22 release closure: ties in the regional context are kept and listed (S2) ----------------

def test_latest_by_type_lists_every_statement_that_shares_the_newest_as_of_date():
    e, c, lg = docs()
    tie = copy.deepcopy(next(x for x in c["entries"] if x["id"] == "ctx-2026-09-20-synthetic-shipping-statement"))
    tie["id"] = "ctx-2026-09-20-synthetic-shipping-second-statement"
    tie["claim"] = "SYNTHETIC FIXTURE. A second authority's statement as of the same day."
    c["entries"].append(tie)
    cx = G.build_payloads(e, c, lg, ctx(), AS_OF)[G.CONTEXT_OUT]
    shipping = sorted(x["id"] for x in cx["entries"] if x["context_type"] == "shipping_status" and x["is_latest_of_type"])
    # No tie-break: both are the latest, and the map says so.
    assert shipping == ["ctx-2026-09-20-synthetic-shipping-second-statement", "ctx-2026-09-20-synthetic-shipping-statement"]
    assert cx["latest_by_type"]["shipping_status"] == shipping
    for ctype, ids in cx["latest_by_type"].items():
        assert ids == sorted(x["id"] for x in cx["entries"] if x["context_type"] == ctype and x["is_latest_of_type"])
    assert set(cx["latest_by_type"]) == {x["context_type"] for x in cx["entries"]}
    assert [k for k in cx["latest_by_type"]] == [t["id"] for t in cx["context_types"] if t["id"] in cx["latest_by_type"]]
    assert "none is chosen" in cx["latest_note"]
    # Without the tie, one statement per type.
    plain = payloads()[G.CONTEXT_OUT]["latest_by_type"]
    assert all(len(ids) == 1 for ids in plain.values())
    empty = G.build_payloads(e, {"context_id": "gulf_hormuz", "entries": []}, lg, ctx(), AS_OF)[G.CONTEXT_OUT]
    assert empty["latest_by_type"] == {}


def test_the_served_context_lists_its_ties():
    out = ROOT / "data" / "processed" / G.CONTEXT_OUT
    if not out.exists():
        pytest.skip("no built regional context yet")
    cx = _json(out)
    for ctype, ids in cx["latest_by_type"].items():
        assert ids == sorted(x["id"] for x in cx["entries"] if x["context_type"] == ctype and x["is_latest_of_type"])


# --- iteration-22 release closure: the served precision wording distinguishes attack records (B2) -------

GULF_ATTACK_COUNTRY = {"bh", "ir", "iq", "kw", "om", "qa", "ae"}


def _recent_scope(system_ids, scope="The Gulf country systems."):
    return B.recent_evidence({sid: (systems.system(sid)["name"], [], []) for sid in system_ids}, scope=scope,
                             regional=True)["scope"]


def test_the_recent_lists_say_where_attack_records_are_placed_and_saudi_keeps_its_policy():
    """'First-level region at most' was true and misleading: seven Gulf systems place an attack record for
    the country only, Saudi Arabia keeps first-level region on its page (owner decision, option B), and a
    campaign-covered record is the country's in any list that sets records side by side."""
    members = sorted(systems.GROUPS["gulf_littoral"]["members"])
    # The policies the sentence reads. Changing Saudi Arabia's is an owner decision (option C), not this test's.
    policy = {sid: (_json(B.SYSTEMS_CURATED / sid / "system.json")["geography"].get("precision_policy") or {})
              for sid in members}
    assert {s for s, p in policy.items() if p.get("kinetic") == "country"} == GULF_ATTACK_COUNTRY
    assert policy["sa"].get("kinetic") in (None, "admin1")
    for scope in (_recent_scope(members), _recent_scope(list(systems.COUNTRY_SYSTEMS), "The country systems.")):
        assert "Precision is first-level region at most." not in scope
        assert ("An attack or sabotage record is placed for the country only in Iran, Iraq, Kuwait, Oman, Qatar and "
                "United Arab Emirates") in scope
        assert "Bahrain places every record for the country only." in scope
        assert "Saudi Arabia" in scope.split("In ")[-2] + scope.split("In ")[-1]
        assert "attack records keep first-level region on the country page under the current policy" in scope
        assert "a record covered by the campaign policy is shown for the country only" in scope
        assert not re.search(r"\b(five|six|seven|eight|twelve|\d+)\b", scope), scope
    gulf = _recent_scope(members)
    assert "In Saudi Arabia, attack records keep first-level region" in gulf
    assert "Canada" not in gulf


def test_the_impact_scope_says_an_attack_record_is_the_countrys_everywhere():
    imp = payloads()[G.IMPACTS_OUT]
    assert "An attack or sabotage record is published for the country only, in every country" in imp["scope_statement"]
    assert "first-level-region precision, never finer" in imp["scope_statement"]


def test_the_built_recent_lists_carry_the_policy_sentence():
    for rel in ("global/recent_evidence.json", "global/gulf.json"):
        path = ROOT / "data" / "processed" / rel
        if not path.exists():
            pytest.skip("no build yet")
        doc = _json(path)
        scope = (doc.get("recent") or doc)["scope"]
        assert "Precision is first-level region at most." not in scope
        assert "attack records keep first-level region on the country page" in scope


# --- iteration-22 release closure: the confidence model's validators gate the import and the build (S5) ---

def _with_source_change(base, ref, **change):
    c = candidate(base)
    for s in c["sources"]:
        if s["ref"] == ref:
            s.update(change)
    return c


def test_the_import_refuses_a_citation_the_confidence_model_refuses(tmp_path):
    """EC.source_problems reads a shortened link, a social-platform post filed as a web page and an
    unreadable date as the model would read them, and the import gate refuses them, naming the record."""
    assert "bit.ly" in EC.METHOD["shortener_hosts"] and "x.com" in EC.METHOD["social_hosts"]
    short = _with_source_change(FRA, "s1", url="https://bit.ly/3SynthFx")
    post = _with_source_change(BRA, "s1", url="https://x.com/example_operator/status/1234567890")
    paths = make_queue(tmp_path, {"europe": [short], "latam": [post], "na": [candidate(USA)]})
    report = run(paths)
    assert set(curated_records(paths)) == {USA}
    assert "a shortened link is not a citation" in reasons(report, FRA)
    assert "the address is on a social platform: medium must be 'social'" in reasons(report, BRA)
    # The build refuses the same records, by the same function.
    e, c, lg = docs()
    for r in e["records"]:
        if r["impact_id"] == FRA:
            r["sources"][0]["url"] = "https://bit.ly/3SynthFx"
    with pytest.raises(ValueError, match="a shortened link is not a citation"):
        G.build_payloads(e, c, lg, ctx(), AS_OF)
    # And a context entry.
    x = entry()
    x["sources"][0]["url"] = "https://bit.ly/3SynthCx"
    assert any("a shortened link" in p for p in G.context_problems([x]))


@pytest.mark.parametrize("about, why", [
    ("attribution", "is recorded in its own block (attribution.competing)"),
    ("ai_involvement", "is recorded in its own block"),
    ("severity", "dispute.about 'severity' is not one of"),
])
def test_the_build_refuses_a_dispute_the_confidence_model_refuses(about, why):
    """The gate's shape check takes any string for `about`; what it may be is the model's validator's call."""
    assert EC.DISPUTE_ABOUT == G.ids("dispute_about")
    e, c, lg = docs()
    r = next(x for x in e["records"] if x["impact_id"] == BRA)
    r["dispute"]["about"] = about
    with pytest.raises(ValueError, match=re.escape(why)):
        G.build_payloads(e, c, lg, ctx(), AS_OF)
    refused(r, why)
    r["dispute"]["about"] = "cause"
    assert problems(r) == []


def test_an_s1_account_whose_identity_rests_on_a_badge_is_refused_and_the_rest_is_left_to_review():
    r = rec(POL)
    social = next(s for s in r["sources"] if s["medium"] == "social")["social"]
    assert social["account_tier"] == "S1" and problems(r) == []
    for badge in ("Verified account", "blue tick", "Official verified profile on X"):
        social["identity_basis"] = badge
        refused(r, "an S1 account's identity_basis names only a platform badge")
    # Whether a stated basis really is the organisation's own site is the reviewer's reading.
    social["identity_basis"] = "Listed on the operator's contact page (synthetic)."
    assert problems(r) == []
    # S2 to S4 are never sole evidence anyway; the badge rule is S1's.
    social["account_tier"], social["identity_basis"] = "S2", "Verified account"
    assert not any("platform badge" in p for p in problems(r))


# --- iteration-22 release closure: a self-claim is not a competing attribution (B6/B7) ------------------

SELF_CLAIM = {"actor": "Example Group G", "actor_type": "hacktivist",
              "statement": "SYNTHETIC. Example Group G claimed the incident on its own channel, as Example Daily "
                           "reported; the claim is unverified.", "source_refs": ["s2"]}


def test_a_competing_entry_resting_only_on_a_self_claim_is_refused_and_belongs_in_self_claims():
    r = rec(DEU)
    r["attribution"]["competing"] = [{**SELF_CLAIM, "basis": ["actor_self_claim"]}]
    refused(r, "attribution.competing[0] rests only on the actor's own claim")
    refused(r, "put it in attribution.self_claims")
    # The build refuses it too.
    e, c, lg = docs()
    e["records"] = [r if x["impact_id"] == DEU else x for x in e["records"]]
    with pytest.raises(ValueError, match="put it in attribution.self_claims"):
        G.build_payloads(e, c, lg, ctx(), AS_OF)
    # A self-claim AND an independent basis is a credible alternative: allowed, and the record is disputed.
    r["attribution"]["competing"][0]["basis"] = ["actor_self_claim", "government"]
    assert not any("own claim" in p for p in problems(r))
    assert EC.attribution_confidence(r["attribution"], r["sources"]) == "DISPUTED"
    # A competing entry needs a basis from the vocabulary.
    r["attribution"]["competing"][0]["basis"] = []
    refused(r, "attribution.competing[0]: basis must list who advances it")


def test_a_competing_entry_whose_every_source_is_the_actors_own_claim_is_refused():
    r = rec(DEU)
    r["sources"][1]["attribution_basis"] = "media_investigation"
    r["sources"].append(dict(CHANNEL))
    r["attribution"]["competing"] = [{**SELF_CLAIM, "basis": ["government"], "source_refs": ["s3"]}]
    refused(r, "every source it cites is the actor's own claim")


def test_self_claims_are_provenance_and_never_make_a_record_disputed():
    base = rec(DEU)
    before = EC.attribution_confidence(base["attribution"], base["sources"])
    r = rec(DEU)
    r["attribution"]["self_claims"] = [dict(SELF_CLAIM)]
    assert problems(r) == []
    got = EC.attribution_confidence(r["attribution"], r["sources"])
    assert got == before and got != "DISPUTED"
    served = next(x for x in payloads(events={"schema_version": 1, "records": [r]})[G.IMPACTS_OUT]["records"])
    assert served["attribution"]["self_claims"] == [SELF_CLAIM] and served["attribution"]["confidence"] == before
    # A second group's own channel, cited only for its claim, is not evidence about who did it: it does
    # not turn the press reporting the first attribution into relays of a claim.
    r["sources"].append(dict(CHANNEL))
    r["attribution"]["self_claims"][0]["source_refs"] = ["s3"]
    assert problems(r) == []
    assert EC.attribution_confidence(r["attribution"], r["sources"]) == before


def test_a_self_claim_needs_its_actor_type_statement_and_sources_that_resolve():
    for change, why in ((dict(actor=""), "no actor"), (dict(actor_type="group"), "actor_type 'group'"),
                        (dict(statement=" "), "no statement"), (dict(source_refs=[]), "attribution.self_claims[0]: no source"),
                        (dict(source_refs=["s9"]), "source_refs ['s9'] name no source"),
                        (dict(rank=1), "field 'rank' is not part of the contract")):
        r = rec(DEU)
        r["attribution"]["self_claims"] = [{**SELF_CLAIM, **change}]
        refused(r, why)
    r = rec(DEU)
    r["attribution"]["self_claims"] = [{**SELF_CLAIM, "source_refs": ["s1"]}]     # s1 does not support attribution
    refused(r, "is cited for attribution but does not support it")
    r["attribution"]["self_claims"] = {"actor": "x"}
    refused(r, "attribution.self_claims are lists")


CHANNEL = {"ref": "s3", "url": "https://channel.example/synthetic/post/7070", "publisher": "Example Group G channel",
           "date": "2025-09-03", "language": "en", "source_role": "actor_self_claim", "medium": "web", "social": None,
           "supports": ["attribution"], "opened": True, "derived_claim": "Synthetic: Example Group G claims the incident."}


def test_the_leads_normalisation_can_move_a_self_claim_out_of_competing(tmp_path):
    c = candidate(DEU)
    c["attribution"]["competing"] = [{**SELF_CLAIM, "basis": ["actor_self_claim"]}]
    paths = make_queue(tmp_path, {"europe": [c]})
    report = run(paths)
    assert curated_records(paths) == {} and "put it in attribution.self_claims" in reasons(report, DEU)
    lead_file(paths, "europe", {DEU: normalise(set={"attribution.competing": [], "attribution.self_claims": [dict(SELF_CLAIM)]})})
    report = run(paths)
    got = curated_records(paths)[DEU]
    assert got["attribution"]["competing"] == [] and got["attribution"]["self_claims"] == [SELF_CLAIM]
    assert got["review"]["lead_normalisation"] is True
    e, cx, lg = G.load_curated(paths["curated"])
    served = G.build_payloads(e, cx, lg, ctx(), AS_OF)[G.IMPACTS_OUT]["records"][0]
    assert served["attribution"]["confidence"] not in ("DISPUTED", None)


def test_a_self_claim_whose_only_source_a_reviewer_removed_is_dropped_and_said(tmp_path):
    c = candidate(DEU)
    c["sources"].append(dict(CHANNEL))
    c["attribution"]["self_claims"] = [{**SELF_CLAIM, "source_refs": ["s3"]}]
    paths = make_queue(tmp_path, {"europe": [c]})
    run(paths)
    assert curated_records(paths)[DEU]["attribution"]["self_claims"][0]["source_refs"] == ["s3"]
    edit_review(paths, "safety", "europe", DEU, verdict="accept_with_correction", remove_sources=["s3"])
    report = run(paths)
    got = curated_records(paths)[DEU]
    assert got["attribution"]["self_claims"] == [] and [s["ref"] for s in got["sources"]] == ["s1", "s2"]
    assert any("1 self-claim(s) dropped" in n for n in report["notes"][DEU])


# --- iteration-22 release closure: an end date is observed, never planned (B11) -----------------------

def test_an_end_date_after_the_newest_source_is_refused():
    r = rec(DEU)                                   # sources dated 2025-09-02 and 2025-09-20
    assert problems(r) == []
    r["date_end"] = "2025-09-20"                   # the newest source's own day: it could have seen it
    assert problems(r) == []
    r["date_end"] = "2025-09-21"
    refused(r, "date_end 2025-09-21 is after 2025-09-20, the newest date among its sources")
    # Judged against the NEWEST source, not the first: an end between the two is fine.
    r["date_end"] = "2025-09-10"
    assert problems(r) == []
    # Precision is read conservatively on both sides.
    r["date_end"] = "2025-09"                      # could mean any day of September
    assert problems(r) == []
    r["sources"][1]["date"] = "2025-09"            # a month-dated source could be from the 30th
    r["date_end"] = "2025-09-30"
    assert problems(r) == []
    r["date_end"] = "2025-10"
    refused(r, "date_end 2025-10 is after 2025-09")


def test_the_end_date_rule_does_not_guess_at_an_undated_page():
    r = rec(DEU)
    r["date_end"] = "2025-10-01"
    refused(r, "the newest date among its sources")
    r["sources"][1]["date"], r["sources"][1]["date_basis"] = None, "undated_page"
    assert not any("newest date among its sources" in p for p in problems(r))


def test_the_import_refuses_a_planned_end_date(tmp_path):
    paths = make_queue(tmp_path, {"europe": [candidate(DEU, date_end="2025-10-15"), candidate(FRA)]})
    report = run(paths)
    assert set(curated_records(paths)) == {FRA}
    assert "is after 2025-09-20, the newest date among its sources" in reasons(report, DEU)
