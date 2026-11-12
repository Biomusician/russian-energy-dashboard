"""Iteration 19: the Gulf expansion.

Seven country systems, a regional overview that is national context and nothing else, a campaign
classification that fails closed, a precision policy under which admin-1 is a maximum, and date
and numeral handling for Persian and Arabic sources. Payload tests read what was emitted.
"""
import ast
import copy
import datetime as dt
import importlib.util
import json
import re
from pathlib import Path

import pytest

from pipeline import artifacts, build_systems as B, calendars as C, gulf_context as GC, systems

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web" / "public" / "data"
CURATED = ROOT / "data" / "curated" / "systems"
needs_payload = pytest.mark.skipif(not (WEB / "global" / "gulf.json").exists(), reason="no built payload")
needs_ne = pytest.mark.skipif(not (ROOT / "data" / "raw" / "ne_10m_admin_1.geojson").exists(), reason="no Natural Earth cache")

GULF = ("bh", "ir", "iq", "kw", "om", "qa", "sa", "ae")
NEW = ("ae", "bh", "iq", "ir", "kw", "om", "qa")


def _json(rel):
    return json.loads((WEB / rel).read_text(encoding="utf-8"))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _walk(x, path=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield f"{path}.{k}", k, v
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _walk(v, f"{path}[{i}]")


# --- registry and groups -------------------------------------------------------------------------

def test_the_gulf_group_is_exactly_the_eight_littoral_states():
    assert set(systems.GROUPS["gulf_littoral"]["members"]) == set(GULF)
    assert len(systems.GROUPS["gulf_littoral"]["members"]) == 8


def test_the_gcc_is_exactly_its_six_members_and_never_iran_or_iraq():
    gcc = set(systems.GROUPS["gcc"]["members"])
    assert gcc == {"bh", "kw", "om", "qa", "sa", "ae"}
    assert not gcc & {"ir", "iq"}


def test_opec_membership_is_todays_and_says_who_left():
    """The UAE left OPEC on 2026-05-01. A list copied from an older reference would still hold it."""
    opec = systems.GROUPS["opec"]
    assert set(opec["members"]) == {"ir", "iq", "kw", "sa"}
    assert "ae" in opec["former_members"] and opec["as_of"]
    assert "2026-05-01" in opec["note"]


def test_groups_are_three_separate_facts():
    assert systems.GROUPS["gulf_littoral"]["kind"] == "geographic"
    assert {systems.GROUPS[g]["kind"] for g in ("gcc", "opec")} == {"membership"}
    assert systems.groups_of("ir") == ("gulf_littoral", "opec")
    assert systems.groups_of("qa") == ("gulf_littoral", "gcc")
    assert systems.groups_of("us") == ()


def test_exactly_seven_systems_were_added_and_no_wave_two_country():
    ids = {s["id"] for s in systems.SYSTEMS}
    assert set(NEW) <= ids
    assert not ids & {"ye", "jo", "tr", "az", "sy", "il", "eg", "tw"}
    assert len(systems.COUNTRY_SYSTEMS) == 12


def test_systems_stay_alphabetical_by_name():
    names = [s["name"] for s in systems.SYSTEMS]
    assert names == sorted(names)


def test_every_new_system_is_findable_in_its_own_script():
    for sid in NEW:
        aliases = systems.system(sid)["aliases"]
        assert any(re.search(r"[؀-ۿ]", a) for a in aliases), sid


def test_group_members_are_registered_systems():
    ids = {s["id"] for s in systems.SYSTEMS}
    for g, d in systems.GROUPS.items():
        assert set(d["members"]) <= ids, g


# --- calendars and numerals ----------------------------------------------------------------------

@pytest.mark.parametrize("j,g", [
    ((1403, 1, 1), "2024-03-20"), ((1404, 1, 1), "2025-03-21"), ((1403, 12, 30), "2025-03-20"),
    ((1357, 11, 22), "1979-02-11"), ((1401, 7, 1), "2022-09-23"), ((1400, 1, 1), "2021-03-21"),
    ((1404, 3, 23), "2025-06-13"),
])
def test_solar_hijri_dates_convert_exactly(j, g):
    assert C.jalali_to_gregorian(*j).isoformat() == g


def test_a_solar_hijri_date_that_does_not_exist_is_refused():
    with pytest.raises(ValueError):
        C.jalali_to_gregorian(1404, 12, 30)          # 1404 is not a leap year
    with pytest.raises(ValueError):
        C.jalali_to_gregorian(1404, 13, 1)


def test_persian_and_arabic_digits_normalise():
    assert C.western_digits("۱۴۰۴/۰۳/۲۵") == "1404/03/25"
    assert C.western_digits("١٤٤٧") == "1447"
    assert C.parse_number("۱٬۵۰۰") == 1500
    assert C.parse_number("٣٫٥") == 3.5
    assert C.parse_number("1,500") == 1500


def test_an_ambiguous_number_is_refused_not_guessed():
    # "1,5" is one and a half in Tehran and nonsense in Houston. Not a number until a person says which.
    assert C.parse_number("1,5") is None
    assert C.parse_number("12,34") is None
    assert C.parse_number("1.234.567") is None


def test_a_persian_date_keeps_what_the_source_wrote():
    n = C.normalize_date("۲۵ خرداد ۱۴۰۴", "solar_hijri")
    assert n["normalized_date"] == "2025-06-15"
    assert n["source_date_text"] == "۲۵ خرداد ۱۴۰۴"
    assert n["date_calendar"] == "solar_hijri" and "exact" in n["conversion_basis"].lower()


def test_1404_is_never_read_as_a_gregorian_year():
    with pytest.raises(ValueError):
        C.normalize_date("1404-03-25", "gregorian")
    with pytest.raises(ValueError):
        C.normalize_date("1446-01-01", "gregorian")


def test_a_hijri_conversion_says_it_can_be_a_day_out():
    n = C.normalize_date("1446-01-01", "hijri")
    assert n["normalized_date"] in ("2024-07-07", "2024-07-08")
    assert "day" in n["conversion_basis"].lower() and "tabular" in n["conversion_basis"].lower()


def test_an_unknown_calendar_is_refused():
    with pytest.raises(ValueError):
        C.normalize_date("2025-01-01", "julian")


# --- campaign classification fails closed --------------------------------------------------------

def _campaigns():
    return json.loads((CURATED / "conflict_campaigns.json").read_text(encoding="utf-8"))


def test_the_campaign_register_has_no_problems():
    assert B.campaign_problems(_campaigns()) == []


def test_every_gulf_system_states_a_campaign_classification():
    states = _campaigns()["system_states"]
    assert set(states) == set(GULF)
    for sid, s in states.items():
        assert s["state"] in B.CAMPAIGN_STATES and s["checked"] and s["basis"], sid


def test_a_gulf_system_with_no_classification_fails_the_build():
    doc = _campaigns()
    del doc["system_states"]["om"]
    assert any("om" in p and "no campaign classification" in p for p in B.campaign_problems(doc))


def test_uncertain_restricts_exactly_as_active_does():
    doc = _campaigns()
    uncertain = [sid for sid, s in doc["system_states"].items() if s["state"] == "UNCERTAIN"]
    assert uncertain, "this test needs an uncertain system to mean anything"
    ev = {"event_id": "x", "cause": "kinetic_strike", "date": "2026-03-10"}
    for sid in uncertain:
        assert B.campaign_of(ev, sid, doc) is not None, sid
    assert set(B.RESTRICTING_STATES) == {"ACTIVE_KINETIC_CAMPAIGN", "RECENT_ENDED_CAMPAIGN", "UNCERTAIN"}


@pytest.mark.parametrize("status", ["active", "uncertain"])
def test_an_open_campaign_cannot_switch_its_policy_off(status):
    doc = _campaigns()
    c = next(c for c in doc["campaigns"] if c["system_id"] == "kw")
    c.update(status=status, policy_applied=False)
    assert any("policy is not applied" in p for p in B.campaign_problems(doc))


def test_an_ended_campaign_keeps_its_policy_for_the_release_period():
    doc = _campaigns()
    c = next(c for c in doc["campaigns"] if c["system_id"] == "kw")
    today = dt.date(2026, 11, 11)
    c.update(status="ended", ended="2026-11-01", policy_applied=False)
    assert any("policy lifted before" in p for p in B.campaign_problems(doc, today))
    doc["system_states"]["kw"]["state"] = "NO_ACTIVE_CAMPAIGN"
    c["ended"] = "2026-09-01"
    assert not any("kw" in p for p in B.campaign_problems(doc, today))


def test_a_restricted_state_needs_a_campaign_that_applies_the_policy():
    doc = _campaigns()
    doc["campaigns"] = [c for c in doc["campaigns"] if c["system_id"] != "qa"]
    assert any("qa" in p and "no campaign applying" in p for p in B.campaign_problems(doc))


def test_an_unknown_state_is_refused():
    doc = _campaigns()
    doc["system_states"]["bh"]["state"] = "PROBABLY_FINE"
    assert any("PROBABLY_FINE" in p for p in B.campaign_problems(doc))


def test_irans_campaign_reaches_back_to_the_2025_strikes():
    """Sites struck in June 2025 were reported struck again in 2026, so a 2025 record's recovery
    would be a 2026 target's status."""
    doc = _campaigns()
    ev = {"event_id": "x", "cause": "kinetic_strike", "date": "2025-06-14"}
    assert B.campaign_of(ev, "ir", doc) is not None
    assert B.campaign_of({**ev, "date": "2024-02-14"}, "ir", doc) is None


def test_campaign_register_urls_carry_no_route_or_status_wording():
    text = json.dumps(_campaigns()).lower()
    for word in ("hormuz", "strait", "tanker", "bypass", "chokepoint"):
        assert word not in text, word


@pytest.mark.parametrize("text", [
    "راه‌اندازی مجدد پالایشگاه", "راه اندازی مجدد واحد", "ازسرگیری تولید", "تولید از سر گرفته شد",
    "واحد به مدار بازگشت", "بازگشت به مدار نیروگاه", "تعمیر خط لوله", "بازسازی تاسیسات", "همچنان متوقف است",
    "https://example.ir/news/123/%D8%A8%D8%A7%D8%B2%D8%B3%D8%A7%D8%B2%DB%8C-%D9%88%D8%A7%D8%AD%D8%AF",
    "استئناف الإنتاج", "إعادة تشغيل المصفاة", "production resumed", "back-online",
])
def test_status_wording_is_caught_in_persian_arabic_and_english(text):
    assert B.status_wording(text), text


@pytest.mark.parametrize("text", ["آتش‌سوزی در پالایشگاه", "قطع برق گسترده", "حريق في مصفاة", "fire at a refinery"])
def test_occurrence_wording_is_not_mistaken_for_status(text):
    assert not B.status_wording(text), text


# --- precision: admin-1 is a maximum -------------------------------------------------------------

def _event(**kw):
    base = {"event_id": "kw-2026-03-refinery-attack-1", "cause": "kinetic_strike", "date": "2026-03",
            "geography_precision": "country", "region_code": None, "regions_affected": [],
            "facility_name": None, "facility_name_local": None, "operator": None}
    return {**base, **kw}


COUNTRY_POLICY = {"geography": {"precision_policy": {"kinetic": "country", "reason": "small state"}}}


def test_a_clean_kinetic_record_passes_a_country_level_policy():
    assert B.precision_problems("kw", COUNTRY_POLICY, [_event()]) == []


@pytest.mark.parametrize("change,needle", [
    ({"geography_precision": "admin1", "region_code": "KW-AH"}, "country level only"),
    ({"regions_affected": ["KW-AH"]}, "country level only"),
    ({"facility_name": "Some refinery"}, "facility_name"),
    ({"facility_name_local": "مصفاة"}, "facility_name_local"),
    ({"operator": "Some company"}, "operator"),
    ({"event_id": "kw-2026-03-mina-abdullah-refinery-strike"}, "opaque id"),
])
def test_a_kinetic_record_in_a_small_state_cannot_name_or_place_its_facility(change, needle):
    problems = B.precision_problems("kw", COUNTRY_POLICY, [_event(**change)])
    assert any(needle in p for p in problems), problems


def test_a_non_kinetic_record_may_still_be_placed_in_a_region():
    ev = _event(event_id="kw-2024-08-power-cuts", cause="technical", geography_precision="admin1",
                region_code="KW-AH", facility_name="A plant")
    assert B.precision_problems("kw", COUNTRY_POLICY, [ev]) == []


def test_a_system_can_put_every_record_at_country_level():
    doc = {"geography": {"precision_policy": {"kinetic": "country", "other": "country", "reason": "microstate"}}}
    ev = _event(event_id="bh-2024-08-power-cuts", cause="technical", geography_precision="admin1", region_code="BH-13")
    assert any("every record" in p for p in B.precision_problems("bh", doc, [ev]))


def test_units_drawn_but_never_used_take_no_event():
    doc = {"geography": {"precision_policy": {"kinetic": "country", "no_event_units": ["AE-X01~"], "reason": "r"}}}
    ev = _event(event_id="ae-2024-01-outage", cause="technical", geography_precision="admin1", region_code="AE-X01~")
    assert any("never used for events" in p for p in B.precision_problems("ae", doc, [ev]))


def test_a_precision_policy_must_give_its_reason():
    doc = {"geography": {"precision_policy": {"kinetic": "country"}}}
    assert any("states its reason" in p for p in B.precision_problems("kw", doc, []))


def test_a_converted_date_must_keep_the_source_text_and_basis():
    ev = _event(event_id="ir-2024-02-outage", cause="technical", date_calendar="solar_hijri")
    assert any("conversion basis" in p for p in B.precision_problems("ir", {"geography": {}}, [ev]))
    ev = _event(event_id="ir-2024-02-outage", cause="technical", date_calendar="mayan")
    assert any("unknown calendar" in p for p in B.precision_problems("ir", {"geography": {}}, [ev]))


@pytest.mark.parametrize("sid", NEW)
def test_every_new_system_states_a_precision_policy_and_maturity(sid):
    doc = json.loads((CURATED / sid / "system.json").read_text(encoding="utf-8"))
    policy = doc["geography"]["precision_policy"]
    assert policy["kinetic"] in ("country", "admin1") and len(policy["reason"]) > 60
    assert doc["maturity"] in B.MATURITY


@pytest.mark.parametrize("sid", ("ae", "bh", "kw", "qa"))
def test_the_small_gulf_states_never_place_an_attack_below_country(sid):
    doc = json.loads((CURATED / sid / "system.json").read_text(encoding="utf-8"))
    assert doc["geography"]["precision_policy"]["kinetic"] == "country"


def test_iran_is_fail_closed_while_its_campaign_is_active():
    doc = json.loads((CURATED / "ir" / "system.json").read_text(encoding="utf-8"))
    assert _campaigns()["system_states"]["ir"]["state"] in B.RESTRICTING_STATES
    assert doc["geography"]["precision_policy"]["kinetic"] == "country"


def test_bahrain_places_no_record_in_a_governorate():
    doc = json.loads((CURATED / "bh" / "system.json").read_text(encoding="utf-8"))
    assert doc["geography"]["precision_policy"].get("other") == "country"


def test_the_uae_neutral_zones_take_no_event():
    doc = json.loads((CURATED / "ae" / "system.json").read_text(encoding="utf-8"))
    assert {"AE-X01~", "AE-X02~"} <= set(doc["geography"]["precision_policy"]["no_event_units"])


# --- import gate ---------------------------------------------------------------------------------

def _candidate(**kw):
    base = {"candidate_id": "kw-2026-03-12-refinery-attack-1", "date": "2026-03-12", "date_precision": "day",
            "admin1_code": "KW-AH", "geography_precision": "admin1", "admin1_codes_affected": [],
            "facility_name": "Example Refinery", "facility_name_local": None, "operator": "Example Co",
            "asset_class": "refinery", "cause": "kinetic_strike",
            "summary": "A refinery was reported attacked.", "effect": "A fire was reported.",
            "threshold_basis": "clause 1", "suggested_disposition": "accept",
            "sources": [{"url": "https://example.org/a", "publisher": "Example", "date": "2026-03-12",
                         "language": "ar", "source_role": "media", "opened": True,
                         "title_original": "خبر", "title_en": "News"}]}
    return {**base, **kw}


POLICY = {"kinetic": "country", "reason": "r"}


def test_the_import_gate_gives_a_kinetic_record_an_id_that_names_nothing():
    imp = _load("import_candidates")
    r = _candidate(candidate_id="kw-2026-03-12-example-refinery-strike")
    oid = imp.opaque_id("kw", r)
    assert re.fullmatch(B.OPAQUE_ID.format(cc="kw"), oid), oid
    assert "example" not in oid
    assert imp.opaque_id("kw", r) == oid, "stable for the life of the record"
    assert imp.opaque_id("kw", _candidate()) == "kw-2026-03-12-refinery-attack-1", "an already opaque id is kept"


def test_the_import_gate_holds_a_record_that_names_its_facility_in_text():
    imp = _load("import_candidates")
    r = _candidate(summary="Example Refinery was reported attacked.")
    assert "names the facility" in imp.review("kw", r, {"KW-AH"}, policy=POLICY)


def test_the_import_gate_refuses_a_misread_calendar():
    imp = _load("import_candidates")
    assert "not a Gregorian date" in imp.date_problem(_candidate(date="1404-03-25"))
    r = _candidate(date="2025-06-16", date_calendar="solar_hijri", source_date_text="۲۵ خرداد ۱۴۰۴")
    assert "does not match" in imp.date_problem(r)
    assert imp.date_problem({**r, "date": "2025-06-15"}) is None
    assert "no source text" in imp.date_problem({**r, "source_date_text": None})


def test_kinetic_country_policy_is_by_cause():
    imp = _load("import_candidates")
    assert imp.kinetic_country_policy(POLICY, {"cause": "sabotage"})
    assert not imp.kinetic_country_policy(POLICY, {"cause": "technical"})
    assert not imp.kinetic_country_policy({"kinetic": "admin1"}, {"cause": "kinetic_strike"})


# --- the Gulf context artifact: context, never a score -------------------------------------------

def test_the_gulf_artifact_is_a_registered_global_payload():
    assert GC.OUTPUT in artifacts.GLOBAL_PAYLOADS


def test_a_partial_regional_sum_is_never_published():
    r = GC._region({"a": 1.0, "b": None}, 10.0)
    assert r["value"] is None and r["world_share"] is None and "1 of 2" in r["reason"]
    assert GC._region({"a": 1.0, "b": 2.0}, 10.0) == {"value": 3.0, "world_share": 0.3, "reason": None}


def _extra(**kw):
    m = {"label": "Refining capacity", "unit": "kb/d", "definition": "d", "year": 2024, "source_id": "s",
         "values": {"KWT": 1.0}}
    m.update(kw)
    return {"metrics": {"refining_capacity": m},
            "sources": {"s": {"name": "S", "url": "https://example.org", "redistribution": "permitted_with_attribution"}}}


def test_an_extra_regional_metric_needs_a_licence_that_allows_it():
    GC.validate_extra(_extra())
    doc = _extra()
    doc["sources"]["s"]["redistribution"] = "all_rights_reserved"
    with pytest.raises(ValueError, match="redistribution"):
        GC.validate_extra(doc)


@pytest.mark.parametrize("change,needle", [
    ({"values": {"TUR": 1.0}}, "not a Gulf member"),
    ({"values": {"KWT": -1}}, "non-negative"),
    ({"year": None}, "no year"),
    ({"hormuz_share": 0.4}, "forbidden"),
    ({"facility_count": 3}, "forbidden"),
    ({"importance_rank": 1}, "forbidden"),
])
def test_an_extra_regional_metric_cannot_smuggle_in_what_the_view_refuses(change, needle):
    with pytest.raises(ValueError, match=needle):
        GC.validate_extra(_extra(**change))


def test_no_analytic_module_imports_the_gulf_context():
    """Context never enters a number. Only the build that writes it may import it."""
    allowed = {"build_systems.py", "gulf_context.py"}
    for path in (ROOT / "pipeline").glob("*.py"):
        if path.name in allowed:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [a.name for a in node.names]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            assert not any("gulf_context" in n for n in names), path.name


FORBIDDEN_GULF_KEYS = ("rank", "score", "vulnerab", "critical", "target", "importance", "severity", "route",
                       "strait", "hormuz", "bypass", "chokepoint", "tanker", "facility", "dependen",
                       "coord", "latitude", "longitude", "ais", "restart", "outage")


@needs_payload
def test_the_emitted_gulf_payload_holds_national_context_and_nothing_else():
    d = _json("global/gulf.json")
    assert [s["system_id"] for s in d["systems"]] == [s["id"] for s in systems.SYSTEMS if s["id"] in GULF]
    names = [s["name"] for s in d["systems"]]
    assert names == sorted(names), "alphabetical, never by a figure"
    for path, key, _ in _walk({k: v for k, v in d.items() if k != "recent"}):
        k = key.lower()
        assert not any(k == p or (p in k and p != "ais") for p in FORBIDDEN_GULF_KEYS), path
    for s in d["systems"]:
        assert not {"records", "events", "episodes", "count", "withheld_records"} & set(s), s["system_id"]
        assert isinstance(s["recovery_status_withheld"], bool)


@needs_payload
def test_gulf_memberships_in_the_payload_match_the_registry():
    d = _json("global/gulf.json")
    for s in d["systems"]:
        assert s["gcc_member"] == (s["system_id"] in systems.GROUPS["gcc"]["members"])
        assert s["opec_member"] == (s["system_id"] in systems.GROUPS["opec"]["members"])
    by = {s["system_id"]: s for s in d["systems"]}
    assert not by["ir"]["gcc_member"] and not by["iq"]["gcc_member"]
    assert not by["ae"]["opec_member"]


@needs_payload
def test_a_gulf_null_is_null_and_the_sum_is_refused_when_one_is_missing():
    d = _json("global/gulf.json")
    for mid in d["metrics"]:
        vals = [s["values"][mid] for s in d["systems"]]
        r = d["region"][mid]
        if any(v is None for v in vals):
            assert r["value"] is None and r["reason"]
        else:
            assert r["value"] == pytest.approx(sum(vals), abs=0.01)
        assert all(v is None or v >= 0 for v in vals)
    assert all(m["source_id"] in d["sources"] and m["year"] for m in d["metrics"].values())


@needs_payload
def test_every_restricted_gulf_system_says_recovery_status_is_withheld():
    d = _json("global/gulf.json")
    states = _campaigns()["system_states"]
    for s in d["systems"]:
        if states[s["system_id"]]["state"] in B.RESTRICTING_STATES:
            assert s["recovery_status_withheld"], s["system_id"]


@needs_payload
def test_the_gulf_recent_list_holds_only_gulf_systems_and_no_status_for_campaign_records():
    d = _json("global/gulf.json")
    for ep in d["recent"]["episodes"]:
        assert ep["system_id"] in GULF
        for m in ep["members"]:
            if m["withheld"]:
                assert m["effect"] is None


@needs_payload
def test_the_manifest_carries_groups_and_no_rankable_figure_for_them():
    m = _json("global/manifest.json")
    g = m["groups"]
    assert set(g) == {"gulf_littoral", "gcc", "opec"}
    assert g["gulf_littoral"]["slug"] == "gulf" and g["gulf_littoral"]["context"] == "global/gulf.json"
    assert g["gcc"]["slug"] is None, "a membership is a filter, not a page"
    for d in g.values():
        assert set(d) == {"label", "kind", "note", "slug", "context", "members"}
    by = {s["id"]: s for s in m["systems"]}
    for sid in NEW:
        assert by[sid]["index"] is None and by[sid]["headline"] is None
        assert by[sid]["maturity"] in B.MATURITY and isinstance(by[sid]["campaign_restricted"], bool)
        assert "gulf_littoral" in by[sid]["regional_groups"]
        assert not {"records", "events", "episodes"} & set(by[sid])
    assert "geographic expansion" in m["selection"]["regional_rule"]


@needs_payload
@pytest.mark.parametrize("sid", NEW)
def test_a_new_gulf_system_has_no_index_and_no_zero(sid):
    s = _json(f"systems/{sid}/system.json")
    assert s["index"] is None and s["headline"] is None and s["no_index_reason"]
    assert all(x["state"] in ("CONTEXT_ONLY", "NOT_APPLICABLE", "NOT_YET_RESEARCHED", "INSUFFICIENT_EVIDENCE")
               for x in s["sectors"])
    assert s["campaign_state"]["state"] in B.CAMPAIGN_STATES


@needs_payload
@pytest.mark.parametrize("sid", NEW)
def test_emitted_kinetic_records_obey_the_systems_precision_policy(sid):
    doc = json.loads((CURATED / sid / "system.json").read_text(encoding="utf-8"))
    events = _json(f"systems/{sid}/events.json")["events"]
    assert B.precision_problems(sid, doc, events) == []
    if doc["geography"]["precision_policy"]["kinetic"] == "country":
        for e in events:
            if e["cause"] in B.KINETIC_CAUSES:
                assert e["region_code"] is None and e["facility_name"] is None and e["operator"] is None
                assert e["recovery"]["research_status"] == "WITHHELD_ACTIVE_CAMPAIGN" or e["date"] < "2025-06"


@needs_payload
@pytest.mark.parametrize("sid", NEW)
def test_no_emitted_gulf_event_carries_a_coordinate_or_a_route(sid):
    events = _json(f"systems/{sid}/events.json")
    for path, key, _ in _walk(events):
        assert key.lower() not in ("lat", "lon", "latitude", "longitude", "coordinates", "distance_km", "range_km"), path


@needs_payload
def test_no_gulf_payload_text_weighs_a_country_or_a_facility():
    onboard = _load("onboard_system")
    for sid in NEW:
        s = _json(f"systems/{sid}/system.json")
        assert onboard.loaded_words(s["profile"]) == [], sid


@needs_ne
def test_irans_provinces_have_unique_codes():
    """Natural Earth files Alborz under Tehran's code and uses the pre-2020 numbering, in which
    "IR-07" is Tehran. Today it is Fars: a code from any current source must land where it says."""
    units = {u[0]: u[1] for u in B.units("ir", B.load_admin1(), B.load_admin0())}
    assert len(units) == 31 and set(units) == {f"IR-{i:02d}" for i in range(31)}
    assert units["IR-07"] == "Fars" and units["IR-23"] == "Tehran" and units["IR-30"] == "Alborz"
    assert units["IR-22"] == "Hormozgan" and units["IR-06"] == "Khuzestan" and units["IR-18"] == "Bushehr"


@needs_ne
def test_an_iranian_unit_the_code_table_misses_is_an_error_not_an_old_code(monkeypatch):
    fixes = {k: v for k, v in B.NAME_CODE_FIXES.items() if k != ("IRN", "Fars")}
    monkeypatch.setattr(B, "NAME_CODE_FIXES", fixes)
    with pytest.raises(ValueError, match="name-to-code table"):
        B.units("ir", B.load_admin1(), B.load_admin0())


@needs_ne
@pytest.mark.parametrize("sid,n", [("ae", 9), ("bh", 5), ("iq", 18), ("ir", 31), ("kw", 6), ("om", 11), ("qa", 7)])
def test_drawn_unit_counts_are_the_ones_the_systems_declare(sid, n):
    doc = json.loads((CURATED / sid / "system.json").read_text(encoding="utf-8"))
    assert len(B.units(sid, B.load_admin1(), B.load_admin0())) == n == doc["geography"]["units_expected"]


def test_taiwan_and_the_gulf_islands_are_never_analytic_units():
    for sid in ("ir", "ae"):
        doc = json.loads((CURATED / sid / "system.json").read_text(encoding="utf-8"))
        codes = {r["code"] for r in doc["geography"]["rulings"]}
        assert not any("island" in c.lower() for c in codes)
    assert "TWN" not in systems.system("cn")["admin0_a3"]


# --- what is not an event, and what is never recorded ---------------------------------------------

def _rec(summary, cause="unknown", effect=None):
    return {"event_id": "x", "cause": cause, "summary": summary, "effect": effect, "threshold_basis": None}


@pytest.mark.parametrize("summary", [
    "Crude output was lowered under the OPEC+ agreement on production cuts.",
    "A voluntary production cut of 500,000 barrels a day took effect.",
    "The refinery was shut for planned maintenance.",
    "Exports stopped after sanctions were tightened.",
    "A scheduled turnaround took the unit out of service.",
])
def test_a_policy_decision_or_planned_maintenance_is_not_an_event(summary):
    assert "not a physical disruption" in B.not_a_physical_event(_rec(summary))
    assert "not a physical disruption" in B.not_a_physical_event(_rec(summary, cause="technical"))


@pytest.mark.parametrize("summary", [
    "JODI data show crude production fell by 300,000 barrels a day in March.",
    "Exports declined sharply in the monthly statistics.",
])
def test_an_unexplained_decline_in_a_statistic_is_not_an_event(summary):
    assert "context, never an incident" in B.not_a_physical_event(_rec(summary))


@pytest.mark.parametrize("rec", [
    _rec("A fire during planned maintenance shut the unit."),
    _rec("Production fell after an explosion at a gas plant."),
    _rec("Output was cut after a drone attack.", cause="kinetic_strike"),
    _rec("A storm cut power to 300,000 customers.", cause="natural_hazard"),
    _rec("Fuel supply shortfall forced 2,000 MW offline, the ministry said."),
])
def test_a_named_physical_cause_is_left_to_review(rec):
    assert B.not_a_physical_event(rec) is None


def test_the_import_gate_holds_a_production_cut_and_a_nuclear_site_record():
    imp = _load("import_candidates")
    cut = _candidate(cause="unknown", summary="Output was lowered under the OPEC+ agreement on production cuts.",
                     effect=None, facility_name=None)
    assert "not a physical disruption" in imp.review("kw", cut, {"KW-AH"}, policy={"kinetic": "country", "reason": "r"})
    nuc = _candidate(cause="technical", summary="A unit at the nuclear power plant tripped.", effect=None, facility_name=None)
    assert "nuclear site" in imp.review("ae", nuc, set(), policy={"kinetic": "country", "reason": "r"})
    ship = _candidate(cause="technical", summary="A tanker fire closed the terminal.", effect=None, facility_name=None)
    assert "outside this product" in imp.review("om", ship, set(), policy={"kinetic": "country", "reason": "r"})


def test_nuclear_content_is_a_national_generation_total_and_nothing_else():
    ok = {"metrics": [{"metric": "nuclear_generation", "value": 39, "basis": "country total, net generation"}],
          "significance": ["An estimated 23% of electricity was generated from nuclear in 2024."]}
    assert B.nuclear_problems(ok, []) == []
    for bad in ({"metrics": [{"metric": "nuclear_unit_status", "value": 4}]},
                {"metrics": [{"metric": "generating_capacity", "basis": "includes four reactors"}]},
                {"metrics": [], "significance": ["Uranium enrichment capacity is context."]}):
        assert B.nuclear_problems(bad, []), bad
    ev = {"event_id": "x", "summary": "A drone was reported near the nuclear power plant.", "effect": None,
          "threshold_basis": None, "facility_name": None, "hazard_name": None}
    assert any("nuclear site" in p for p in B.nuclear_problems({}, [ev]))


def test_route_and_shipping_wording_is_refused_in_text_and_in_citation_addresses():
    ev = {"event_id": "x", "summary": "A fire was reported at a refinery.", "effect": None, "threshold_basis": None,
          "hazard_name": None, "capacity_affected": None, "sources": [{"url": "https://example.org/news/refinery-fire"}]}
    assert B.route_problems([ev]) == []
    assert B.route_problems([{**ev, "summary": "Exports through the Strait of Hormuz stopped."}])
    assert B.route_problems([{**ev, "sources": [{"url": "https://example.org/2026/hormuz-will-stay-shut"}]}])
    assert B.route_problems([{**ev, "sources": [{"url": "https://example.org/a", "title_original": "حريق في ناقلة نفط"}]}])
    assert B.route_problems([{**ev, "effect": "Tanker loadings were suspended."}])


def _full_candidate(**kw):
    base = _candidate(threshold_clause=1, capacity_affected=None, hazard_name=None,
                      recovery={"research_status": "NOT_YET_RESEARCHED", "kind": None, "date": None, "evidence": None, "url": None},
                      independent_review={"completed": "2026-11-11", "disposition": "confirmed", "sources_opened": 1})
    return {**base, **kw}


def test_the_import_gate_downgrades_an_attack_record_to_the_country():
    """Whatever the lane wrote. The record that leaves the gate has no region, no facility, no
    operator, no headline, and an id that names nothing."""
    imp = _load("import_candidates")
    ev = imp.to_event("kw", _full_candidate(candidate_id="kw-2026-03-12-example-refinery-strike"), policy=POLICY)
    assert ev["geography_precision"] == "country" and ev["region_code"] is None and ev["regions_affected"] == []
    assert ev["facility_name"] is None and ev["facility_name_local"] is None and ev["operator"] is None
    assert re.fullmatch(B.OPAQUE_ID.format(cc="kw"), ev["event_id"])
    assert all("title_original" not in s and "title_en" not in s for s in ev["sources"])
    assert B.precision_problems("kw", {"geography": {"precision_policy": POLICY}}, [ev]) == []


def test_the_import_gate_leaves_an_accident_in_its_region_with_its_headline():
    imp = _load("import_candidates")
    ev = imp.to_event("kw", _full_candidate(candidate_id="kw-2024-08-01-fire", date="2024-08-01", cause="technical"), policy=POLICY)
    assert ev["geography_precision"] == "admin1" and ev["region_code"] == "KW-AH" and ev["facility_name"] == "Example Refinery"
    assert ev["sources"][0]["title_original"] == "خبر" and ev["sources"][0]["title_en"] == "News"


def test_a_microstate_record_is_the_countrys_whatever_its_cause():
    imp = _load("import_candidates")
    policy = {"kinetic": "country", "other": "country", "reason": "r"}
    ev = imp.to_event("bh", _full_candidate(candidate_id="bh-2024-08-01-fire", date="2024-08-01", cause="technical",
                                            admin1_code="BH-13"), policy=policy)
    assert ev["geography_precision"] == "country" and ev["region_code"] is None
    assert ev["facility_name"] == "Example Refinery", "the attack rule strips the facility; the microstate rule does not"


def test_a_status_bearing_headline_is_never_published():
    imp = _load("import_candidates")
    src = {"url": "https://example.org/a", "publisher": "P", "date": "2024-08-02", "language": "ar",
           "source_role": "media", "opened": True, "title_original": "إعادة تشغيل المصفاة بعد الحريق", "title_en": "Refinery restarted after fire"}
    out = imp._source(src, with_titles=True)
    assert "title_original" not in out and "title_en" not in out
    fa = {**src, "language": "fa", "title_original": "بازگشت به مدار نیروگاه", "title_en": "Plant returns to the grid"}
    assert "title_original" not in imp._source(fa, with_titles=True)
    ok = {**src, "title_original": "حريق في مصفاة", "title_en": "Fire at a refinery"}
    assert imp._source(ok, with_titles=True)["title_original"] == "حريق في مصفاة"
    assert "title_original" not in imp._source(ok, with_titles=False)
    en = {**src, "language": "en", "title_original": "Fire at a refinery"}
    assert "title_original" not in imp._source(en, with_titles=True), "an English headline is the publisher's, not shown"


def test_a_citation_address_with_route_wording_is_dropped_at_the_gate():
    imp = _load("import_candidates")
    r = _full_candidate(candidate_id="kw-2024-08-01-fire", date="2024-08-01", cause="technical")
    r["sources"] = r["sources"] + [{"url": "https://example.org/2024/tanker-traffic-through-hormuz", "publisher": "X",
                                    "date": "2024-08-01", "language": "en", "source_role": "media", "opened": True}]
    ev = imp.to_event("kw", r, policy=POLICY)
    assert [s["url"] for s in ev["sources"]] == ["https://example.org/a"]
    assert ev["review"]["source_count"] == 1


def test_a_citation_address_that_names_the_struck_facility_is_not_published():
    """The record has no facility. Its citation list must not hand it back."""
    imp = _load("import_candidates")
    r = _full_candidate(candidate_id="kw-2026-03-12-refinery-attack-1", facility_name="Shuaiba Example Refinery",
                        facility_name_local="مصفاة الشعيبة", admin1_name="Al Ahmadi")
    clean = r["sources"][0]
    slug = {**clean, "url": "https://example.org/2026/03/shuaiba-refinery-hit"}
    arabic = {**clean, "url": "https://example.org/news/%D8%A7%D9%84%D8%B4%D8%B9%D9%8A%D8%A8%D8%A9-%D8%AD%D8%B1%D9%8A%D9%82"}
    region = {**clean, "url": "https://example.org/news/fire-in-ahmadi-governorate"}
    r["sources"] = [clean, slug, arabic, region]
    ev = imp.to_event("kw", r, policy=POLICY)
    assert [s["url"] for s in ev["sources"]] == ["https://example.org/a"]
    assert ev["review"]["source_count"] == 1
    only = {**r, "sources": [slug, region]}
    assert "only citations name the facility" in imp.review("kw", only, {"KW-AH"}, policy=POLICY)
    assert imp.review("kw", r, {"KW-AH"}, policy=POLICY) is None or "citations" not in imp.review("kw", r, {"KW-AH"}, policy=POLICY)


def test_generic_words_and_the_countrys_own_name_do_not_count_as_naming_a_facility():
    imp = _load("import_candidates")
    r = {"facility_name": "Kuwait National Petroleum Company refinery", "facility_name_local": None, "admin1_name": None}
    assert imp.name_tokens(r) == set()
    assert not imp.names_the_place("https://example.org/kuwait-refinery-fire", imp.name_tokens(r))
    assert imp.name_tokens({"facility_name": "Ras Laffan Industrial City"}) == {"laffan"}


@pytest.mark.parametrize("title", ["Attack on the country's largest refinery", "Key gas hub hit", "هجوم على أكبر مصفاة",
                                   "حمله به بزرگ‌ترین پالایشگاه", "The only LNG terminal is hit"])
def test_a_headline_that_weighs_a_facility_is_not_shown(title):
    imp = _load("import_candidates")
    src = {"url": "https://example.org/a", "publisher": "P", "date": "2024-08-02", "language": "ar",
           "source_role": "media", "opened": True, "title_original": title, "title_en": "gloss"}
    assert "title_original" not in imp._source(src, with_titles=True)


def test_two_lanes_reporting_one_event_keep_the_fuller_record(tmp_path, monkeypatch):
    """A lane that only points at another lane's record must not replace it in the queue: the
    first merge of this pass dropped an accepted record behind a 'duplicate' pointer."""
    ms = _load("merge_sweep")
    sweep = tmp_path / "s"
    sweep.mkdir()
    full = {"candidate_id": "zz-1", "suggested_disposition": "accept", "summary": "full"}
    pointer = {"candidate_id": "zz-1", "suggested_disposition": "duplicate", "summary": "see lane a"}
    held = {"candidate_id": "zz-2", "suggested_disposition": "held", "summary": "held"}
    better = {"candidate_id": "zz-2", "suggested_disposition": "accept", "summary": "resolved"}
    (sweep / "zz_a_candidates.json").write_text(json.dumps([full, held]), encoding="utf-8")
    (sweep / "zz_b_candidates.json").write_text(json.dumps([pointer, better]), encoding="utf-8")
    monkeypatch.setattr(ms, "CANDIDATES", tmp_path)
    ms.main("s", "19", ("zz",))
    queue = {r["candidate_id"]: r for r in json.loads((tmp_path / "zz.json").read_text(encoding="utf-8"))}
    assert queue["zz-1"]["summary"] == "full" and queue["zz-1"]["also_found_by"] == ["zz_b"]
    assert queue["zz-2"]["summary"] == "resolved"
    # Running the merge again changes nothing.
    ms.main("s", "19", ("zz",))
    again = {r["candidate_id"]: r for r in json.loads((tmp_path / "zz.json").read_text(encoding="utf-8"))}
    assert again["zz-1"]["summary"] == "full" and again["zz-2"]["summary"] == "resolved"


def test_no_recent_list_states_a_number_of_systems():
    """It said 'the five country systems' over a list of twelve."""
    for rel in ("global/recent_evidence.json", "global/gulf.json"):
        doc = json.loads((ROOT / "data/processed" / rel).read_text(encoding="utf-8"))
        scope = (doc.get("recent") or doc)["scope"]
        assert not re.search(r"\b(five|six|seven|eight|twelve|\d+)\b", scope), scope


def test_an_address_naming_any_region_the_operator_or_the_method_is_not_published():
    """Found by the blind safety review: the only token from one facility's name was a single word,
    so an address under a regional section of a news site, one naming the operator and one saying
    how the attack was carried out all went through."""
    imp = _load("import_candidates")
    policy = {**POLICY, "unit_words": imp.unit_words([("KW-AH", "Al Ahmadi"), ("KW-JA", "Al Jahra")])}
    r = _full_candidate(candidate_id="kw-2026-03-12-refinery-attack-1", facility_name="Example Refinery",
                        operator="Zedco Petroleum Company", withheld_place_words=["wafra"])
    clean = r["sources"][0]
    r["sources"] = [clean,
                    {**clean, "url": "https://example.org/english/jahra/20260312"},
                    {**clean, "url": "https://example.org/news/zedco-statement"},
                    {**clean, "url": "https://example.org/news/wafra-site-hit"},
                    {**clean, "url": "https://example.org/2026/03/drone-attack-on-energy-site"},
                    {**clean, "url": "https://example.org/a/%D9%85%D8%B3%D9%8A%D8%B1%D8%A9-%D8%AA%D8%B3%D8%AA%D9%87%D8%AF%D9%81"}]
    ev = imp.to_event("kw", r, policy=policy)
    assert [s["url"] for s in ev["sources"]] == ["https://example.org/a"]
    only = {**r, "sources": r["sources"][1:]}
    assert "only citations" in imp.review("kw", only, {"KW-AH"}, policy=policy)
    said = {**r, "summary": "A drone attack was reported on a refinery in Kuwait."}
    assert "how the attack was carried out" in imp.review("kw", said, {"KW-AH"}, policy=policy)


def test_the_build_refuses_method_wording_and_headlines_on_a_record_published_without_its_place():
    ev = _event(event_id="kw-2026-03-12-refinery-attack-1", cause="kinetic_strike", geography_precision="country",
                region_code=None, summary="An attack was reported on a refinery in Kuwait.")
    ev["sources"] = [{"url": "https://example.org/news/missile-strike-reported", "publisher": "P", "date": "2026-03-12"}]
    doc = {"geography": {"precision_policy": {"kinetic": "country", "reason": "x" * 70}}}
    assert any("how the attack was carried out" in p for p in B.precision_problems("kw", doc, [ev]))
    ev["sources"] = [{"url": "https://example.org/a", "publisher": "P", "date": "2026-03-12", "title_original": "عنوان"}]
    assert any("headline" in p for p in B.precision_problems("kw", doc, [ev]))
    ev["sources"] = [{"url": "https://example.org/a", "publisher": "P", "date": "2026-03-12"}]
    assert not [p for p in B.precision_problems("kw", doc, [ev]) if "kw-2026" in p]


def test_a_month_precision_date_does_not_crash_the_late_citation_check():
    e = {"date": "2025-05", "date_precision": "month"}
    assert B.late_citation(e, {"date": "2025-06-03"}) is False
    assert B.late_citation(e, {"date": "2025-07-01"}) is True
    assert B.late_citation({"date": "2025", "date_precision": "year"}, {"date": None}) is True


# --- research-pass honesty -----------------------------------------------------------------------

def _body(**kw):
    base = {"universe_kind": "declared_query_set", "execution": "declared_search_complete", "source_window": "no_census_exists",
            "covered_through": "2026-11-11", "languages_required": ["fa", "en"], "languages_executed": ["fa", "en"],
            "queries_declared": 10, "queries_run": 10, "limitation": "No census exists."}
    return {**base, **kw}


def test_the_pass_writer_never_calls_a_lane_complete_that_missed_a_language_or_a_query():
    w = _load("write_gulf_pass")
    assert w.honest(_body(), False)["execution"] == "declared_search_complete"
    assert w.honest(_body(languages_executed=["en"]), False)["execution"] == "partial"      # English only, Persian required
    assert w.honest(_body(languages_required=["ar", "en"], languages_executed=["ar"]), False)["execution"] == "partial"
    short = w.honest(_body(queries_run=4), True)
    assert short["execution"] == "partial" and short["stopped_by"] == "search_limit"
    blocked = w.honest(_body(universe_kind="report_archive", execution="enumerated_complete", source_window="inaccessible"), False)
    assert blocked["execution"] == "partial"
    assert w.honest(_body(execution="enumerated_complete"), False)["execution"] == "partial", "a query set is never a census"
    idle = w.honest(_body(execution="not_started", queries_run=3), False)
    assert "queries_run" not in idle and idle["languages_executed"] == []


@pytest.mark.parametrize("required,executed", [(["fa"], ["en"]), (["ar", "en"], ["ar"]), (["ar", "en"], ["en"]), (["ku", "en"], ["en"])])
def test_a_lane_run_in_fewer_languages_than_required_cannot_be_complete(required, executed):
    lane = {"lane": "X1", "source_family": "f", "registry": ["A"], "universe_kind": "declared_query_set",
            "execution": "declared_search_complete", "source_window": "no_census_exists", "covered_through": "2026-11-11",
            "languages_required": required, "languages_executed": executed, "queries_declared": 5, "queries_run": 5,
            "limitation": "no census"}
    assert any("required languages" in p for p in B.lane_problems(lane, ["2022-01-01", "2026-11-11"]))


def test_the_pass_writer_takes_names_and_status_out_of_published_lane_text():
    w = _load("write_gulf_pass")
    out = w.public_text("Example Refinery was read. The unit restarted in May. Nothing else found.", ["Example Refinery"])
    assert "Example Refinery" not in out and "restart" not in out.lower() and "Nothing else found." in out


# --- frontend contracts read from source -----------------------------------------------------------

def test_views_are_keyed_on_their_route_so_one_country_never_shows_anothers_data():
    root = (ROOT / "web" / "src" / "Root.tsx").read_text(encoding="utf-8")
    assert "<CountryView key={route.id} id={route.id} />" in root
    assert "<GroupView key={route.id} id={route.id} />" in root
    manifest = (ROOT / "web" / "src" / "global" / "manifest.ts").read_text(encoding="utf-8")
    assert "system.system_id !== entry.id" in manifest, "a payload for another system is refused at load"


def test_the_frontend_holds_no_list_of_gulf_countries():
    """The manifest says which systems and groups exist. A country list in a component would go
    stale the day a system is added, and silently."""
    for path in (ROOT / "web" / "src" / "global").glob("*.ts*"):
        if path.name.endswith(".test.ts"):
            continue
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"""["'](ir|iq|kw|bh|qa|om)["']\s*,\s*["'](ir|iq|kw|bh|qa|om|ae|sa)["']""", text), path.name
        for name in ("Bahrain", "Kuwait", "Qatar", "Oman", "Iraq"):
            assert name not in text, (path.name, name)


def test_the_gulf_view_states_what_it_is_not_and_never_says_zero_disruptions():
    text = (ROOT / "web" / "src" / "global" / "GroupView.tsx").read_text(encoding="utf-8")
    assert "No qualifying records in the current reviewed corpus" in text
    assert "0 disruptions" not in text and "no disruptions" not in text.lower()
    country = (ROOT / "web" / "src" / "global" / "CountryView.tsx").read_text(encoding="utf-8")
    assert "No qualifying records in the current reviewed corpus" in country
    assert "Research preview" in country and "CAMPAIGN_STATE_LABEL" in country


@needs_payload
def test_the_gulf_recent_list_is_in_event_date_order_and_says_it_is_a_backfill():
    recent = _json("global/gulf.json")["recent"]
    dates = [ep["last_date"] for ep in recent["episodes"]]
    assert dates == sorted(dates, reverse=True), "newest event first; never by date added, size or country"
    view = (ROOT / "web" / "src" / "global" / "GroupView.tsx").read_text(encoding="utf-8")
    assert "historical" in view and "backfill" in view and "not a deteriorating region" in view


@needs_payload
def test_no_gulf_payload_carries_shipping_route_or_nuclear_site_material():
    for sid in NEW:
        events = _json(f"systems/{sid}/events.json")["events"]
        system = _json(f"systems/{sid}/system.json")
        assert B.route_problems(events) == [], sid
        assert B.nuclear_problems(system["profile"], events) == [], sid
        assert [e["event_id"] for e in events if B.not_a_physical_event(e)] == [], sid
    gulf = json.dumps({k: v for k, v in _json("global/gulf.json").items() if k != "recent"}, ensure_ascii=False).lower()
    for word in ("tanker", "vessel", "chokepoint", "export route"):
        assert word not in gulf.replace("no route, strait, shipping or tanker information", ""), word


@needs_payload
def test_every_gulf_event_has_a_source_and_a_blind_review():
    for sid in NEW:
        for e in _json(f"systems/{sid}/events.json")["events"]:
            assert e["sources"] and all(s["url"].startswith("http") for s in e["sources"]), e["event_id"]
            assert e["review"]["review_status"] == "blind_reviewed", e["event_id"]
            assert not any("ewa.bh" in s["url"] or "km.qa" in s["url"] for s in e["sources"]), e["event_id"]


@needs_payload
def test_a_system_with_no_record_says_so_and_claims_no_search_it_did_not_run():
    for sid in NEW:
        s = _json(f"systems/{sid}/system.json")
        if s["event_summary"]["recorded_events"] == 0:
            assert s["maturity"] == "research_preview", sid
        if not s["research_log"]["passes"]:
            assert s["research_freshness"]["completeness"] == "never_systematic", sid


# --- onboarding tool -----------------------------------------------------------------------------

def _draft():
    return ({"system_id": "kw", "reporting_environment": "media_only", "reporting_note": "n",
             "geography": {"unit_label": "governorate", "units_expected": 2, "note": "n",
                           "rulings": [{"code": "KW-AH", "status": "note", "note": "n"}]},
             "sectors": [], "sources": [], "research_gaps": [], "audit_docs": []},
            {"country": "KW", "metrics": [{"metric": "m", "value": 1, "unit": "u", "year": 2024, "source": "s", "url": "https://e.org"}]})


DEC = {"date": "2026-11-11", "precision_policy": {"kinetic": "country", "reason": "r"}}


def test_onboarding_writes_the_leads_policy_and_a_preview_maturity():
    ob = _load("onboard_system")
    doc, prof = ob.assemble("kw", *_draft(), DEC, {"KW-AH", "KW-JA"})
    assert doc["geography"]["precision_policy"]["kinetic"] == "country"
    assert doc["maturity"] == "research_preview" and len(prof["metrics"]) == 1


@pytest.mark.parametrize("mutate,needle", [
    (lambda d, p, dec: d["geography"].update(units_expected=3), "Natural Earth draws 2"),
    (lambda d, p, dec: d["geography"]["rulings"].append({"code": "KW-ZZ", "status": "note", "note": "n"}), "not a drawn unit"),
    (lambda d, p, dec: d["geography"]["rulings"][0].update(status="abolished_unassigned"), "unknown status"),
    (lambda d, p, dec: dec.pop("precision_policy"), "no precision policy"),
    (lambda d, p, dec: p["metrics"][0].pop("url"), "needs source, url and year"),
    (lambda d, p, dec: p.update(significance=["A critical chokepoint for supply."]), "loaded wording"),
    (lambda d, p, dec: d.update(reporting_environment="vibes"), "unknown reporting environment"),
    (lambda d, p, dec: d.update(system_id="qa"), "draft is for"),
])
def test_onboarding_refuses_a_draft_that_is_not_ready(mutate, needle):
    ob = _load("onboard_system")
    d, p = _draft()
    dec = copy.deepcopy(DEC)
    mutate(d, p, dec)
    with pytest.raises(ValueError, match=needle):
        ob.assemble("kw", d, p, dec, {"KW-AH", "KW-JA"})
