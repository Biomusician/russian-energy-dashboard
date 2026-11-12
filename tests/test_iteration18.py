"""Iteration 18: the coverage model, national energy context and the cross-system artifacts.

These read the emitted payloads where they can: a helper-only assurance is how earlier iterations
shipped defects under a green suite.
"""
import ast
import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

from pipeline import artifacts, build_systems as B, global_context as G, systems

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web" / "public" / "data"
needs_payload = pytest.mark.skipif(not (WEB / "global" / "energy_context.json").exists(), reason="no built payload")
needs_ne = pytest.mark.skipif(not (ROOT / "data" / "raw" / "ne_10m_admin_1.geojson").exists(), reason="no Natural Earth cache")


def _json(rel):
    return json.loads((WEB / rel).read_text(encoding="utf-8"))


def _curated_context():
    return json.loads(G.CONTEXT_FILE.read_text(encoding="utf-8"))


def _lane(**kw):
    base = {"lane": "X1", "source_family": "f", "registry": ["A"], "universe_kind": "declared_query_set",
            "execution": "declared_search_complete", "source_window": "no_census_exists", "covered_through": "2026-11-10",
            "languages_required": ["en"], "languages_executed": ["en"], "queries_declared": 5, "queries_run": 5,
            "limitation": "no census"}
    return {**base, **kw}


WIN = ["2022-01-01", "2026-11-10"]


# --- coverage vocabulary -------------------------------------------------------------------------

def test_a_valid_declared_query_set_passes():
    assert B.lane_problems(_lane(), WIN) == []


@pytest.mark.parametrize("change,needle", [
    ({"execution": "enumerated_complete"}, "can never be enumerated_complete"),
    ({"universe_kind": "census"}, "only a declared query set"),
    ({"source_window": "current_through_end_date"}, "no_census_exists"),
    ({"queries_run": 4}, "every declared query"),
    ({"languages_required": ["zh", "en"]}, "required languages"),
    ({"execution": "bogus"}, "execution"),
    ({"source_window": "bogus"}, "source_window"),
    ({"languages_required": []}, "names no required language"),
    ({"facility_notes": "hit twice"}, "unexpected fields"),
    ({"covered_through": "2027-01-01"}, "after the window end"),
])
def test_a_lane_cannot_claim_more_than_it_did(change, needle):
    assert any(needle in x for x in B.lane_problems(_lane(**change), WIN)), change


def test_a_source_that_refused_is_never_searched():
    lane = _lane(universe_kind="census", execution="enumerated_complete", source_window="inaccessible")
    assert any("refused access" in x for x in B.lane_problems(lane, WIN))


def test_publisher_not_released_needs_an_earlier_covered_through():
    lane = _lane(universe_kind="census", execution="enumerated_complete", source_window="publisher_not_yet_released",
                 queries_declared=None, queries_run=None, covered_through="2026-11-10")
    assert any("publisher_not_yet_released" in x for x in B.lane_problems(lane, WIN))
    assert B.lane_problems({**lane, "covered_through": "2025-12-31"}, WIN) == []


def test_a_partial_lane_must_say_what_remains():
    lane = _lane(execution="partial", limitation=None)
    assert any("states no limitation" in x for x in B.lane_problems(lane, WIN))


def test_not_started_cannot_record_work():
    assert any("not_started" in x for x in B.lane_problems(_lane(execution="not_started", queries_run=3), WIN))


@pytest.mark.parametrize("ex,win,state", [
    ("enumerated_complete", "publisher_not_yet_released", "current_through_latest_release"),
    ("enumerated_complete", "current_through_end_date", "universe_searched"),
    ("declared_search_complete", "no_census_exists", "declared_query_set_run"),
    ("partial", "no_census_exists", "partially_searched"),
    ("partial", "inaccessible", "blocked_by_source"),
    ("not_started", "inaccessible", "blocked_by_source"),
    ("not_started", "unknown", "not_started"),
])
def test_the_reader_state_keeps_analyst_work_and_publisher_availability_apart(ex, win, state):
    assert B.lane_summary_state({"execution": ex, "source_window": win}) == state


def test_a_waiting_publisher_and_a_barely_begun_lane_never_share_a_state():
    wait = B.lane_summary_state({"execution": "enumerated_complete", "source_window": "publisher_not_yet_released"})
    begun = B.lane_summary_state({"execution": "partial", "source_window": "no_census_exists"})
    assert wait != begun


def test_blocked_or_unknown_sources_do_not_count_as_done():
    assert not B._lane_done({"execution": "enumerated_complete", "source_window": "inaccessible"})
    assert B._lane_done({"execution": "declared_search_complete", "source_window": "no_census_exists"})
    assert not B._lane_done({"execution": "partial", "source_window": "no_census_exists"})


@pytest.mark.parametrize("sid", systems.COUNTRY_SYSTEMS)
def test_earlier_passes_keep_the_status_they_were_logged_with(sid):
    """DO NOT MOVE THE GOALPOSTS. A pass logged before iteration 18 keeps the binary status it was
    logged with; a pass from iteration 18 on uses the two-dimension vocabulary. By date, not by
    position: a system onboarded later has no early pass, and a later pass must not rewrite one."""
    log = json.loads((ROOT / "data" / "curated" / "systems" / sid / "research_log.json").read_text(encoding="utf-8"))
    for p in (p for p in log["passes"] if p["kind"] == "systematic"):
        if p["date"] < "2026-11-10":
            assert all("execution" not in lane and "status" in lane for lane in p["lanes"]), p["date"]
        else:
            assert all("execution" in lane and "status" not in lane for lane in p["lanes"]), p["date"]


@needs_payload
@pytest.mark.parametrize("sid", systems.COUNTRY_SYSTEMS)
def test_the_emitted_lane_states_match_the_log(sid):
    p = _json(f"systems/{sid}/system.json")
    systematic = [x for x in p["research_log"]["passes"] if x["kind"] == "systematic"]
    if not systematic:
        # Onboarded, not yet searched. Says so; claims no lane.
        assert p["research_freshness"]["completeness"] == "never_systematic"
        assert not p["research_freshness"].get("lane_states")
        return
    newest = systematic[-1]
    want = {}
    for lane in newest["lanes"]:
        s = B.lane_summary_state(lane)
        want[s] = want.get(s, 0) + 1
    assert p["research_freshness"]["lane_states"] == want
    assert "percent" not in json.dumps(p["research_freshness"]).lower()


# --- the national context file ---------------------------------------------------------------------

import datetime as dt  # noqa: E402

TODAY = dt.date(2026, 11, 10)


def test_the_committed_context_is_valid():
    G.validate(_curated_context(), TODAY)


@pytest.mark.parametrize("mutate,needle", [
    (lambda d: d.__setitem__("comparison_year", 2026), "not a finished year"),
    (lambda d: d.__setitem__("comparison_year", 2031), "not a finished year"),
    (lambda d: d.__delitem__("comparison_year"), "missing or not a year"),
    (lambda d: d["source"].__delitem__("release"), "source.release"),
    (lambda d: d["source"].__setitem__("redistribution", "unclear"), "licence"),
    (lambda d: d["source"].__setitem__("retrieved", "2027-01-01"), "future"),
    (lambda d: d["metrics"]["coal_production"].__setitem__("unit", "thousand tonnes"), "canonical unit"),
    (lambda d: d["metrics"]["coal_production"].__delitem__("definition"), "definition"),
    (lambda d: d["countries"][0]["values"].__setitem__("total_production", -1), "non-negative"),
    (lambda d: d["countries"][0]["values"].__setitem__("coal_production", 465000.0), "unit error"),
    (lambda d: d["countries"][0]["values"].__setitem__("total_production", "12"), "non-negative"),
    (lambda d: d["countries"][0]["roles"].__setitem__("overall", "chokepoint"), "unknown role"),
    (lambda d: d["countries"][0].__setitem__("rank", 1), "forbidden field"),
    (lambda d: d["countries"][0].__setitem__("incident_count", 0), "forbidden field"),
    (lambda d: d["countries"][0]["newer"].__setitem__("oil_production", {"year": 2023, "value": 1}), "not a finished year"),
    (lambda d: d["countries"][0]["newer"].__setitem__("oil_production", {"year": 2026, "value": 1}), "not a finished year"),
    (lambda d: d["countries"].append(copy.deepcopy(d["countries"][0])), "duplicate country"),
    (lambda d: d["countries"].clear(), "no countries"),
])
def test_a_context_file_that_could_mislead_is_refused(mutate, needle):
    d = _curated_context()
    mutate(d)
    with pytest.raises(ValueError, match=needle):
        G.validate(d, TODAY)


def _script():
    spec = importlib.util.spec_from_file_location("bgc", ROOT / "scripts" / "build_global_context.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_unit_conversion_and_no_fallback_to_another_year():
    s = _script()
    series = {"INTL.7-1-XXX-MT.A": {"data": [["2023", 900000.0], ["2024", 465000.0]]},
              "INTL.26-1-XXX-BCM.A": {"data": [["2023", 12.5], ["2024", "NA"]]},
              "INTL.53-1-XXX-TBPD.A": {"data": [["2024", -0.2], ["2025", 3.0]]}}
    values, newer = s.row_for(series, "XXX")
    assert values["coal_production"] == 465.0          # thousand tonnes to million tonnes
    assert values["gas_production"] is None            # 2023 is never borrowed for a 2024 map
    assert values["oil_production"] is None            # a net-loss figure is not a production level
    assert values["total_production"] is None          # absent series is null, never zero
    assert newer["oil_production"] == {"year": 2025, "value": 3.0}


@pytest.mark.parametrize("prod,cons,want", [
    (120, 100, "net_producer"), (80, 100, "net_consumer"), (100, 100, "about_balanced"),
    (None, 100, None), (0, 0, None), (5, 0, "net_producer"),
])
def test_the_broad_role_rule(prod, cons, want):
    assert _script().role(prod, cons) == want


# --- what the context layer may touch --------------------------------------------------------------

def test_no_analytic_module_can_reach_national_context():
    """CONTEXT IS NOT SCORING. Only the builder that writes the artifact imports it."""
    importers = []
    for f in (ROOT / "pipeline").glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.ImportFrom):
                names = [a.name for a in node.names] + [node.module or ""]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            if any("global_context" in n for n in names):
                importers.append(f.name)
    assert sorted(set(importers)) == ["build_systems.py"]
    src = (ROOT / "pipeline" / "build_systems.py").read_text(encoding="utf-8")
    calls = [m.start() for m in re.finditer(r"global_context\.", src)]
    assert len(calls) == 1 and "def build(theatre_snapshot)" in src[:calls[0]]
    assert "energy_context" not in src


def test_the_daily_build_never_fetches_world_data():
    src = (ROOT / "pipeline" / "global_context.py").read_text(encoding="utf-8")
    assert "fetch" not in re.sub(r'""".*?"""', "", src, flags=re.S)
    assert "fetching" not in src.split('"""')[2]


@needs_ne
def test_changing_the_context_source_changes_context_and_not_one_disruption_figure(tmp_path, monkeypatch):
    """A new EIA release updates values and vintage, and nothing else (brief §178)."""
    from pipeline import outputs
    monkeypatch.setitem(outputs._target, "root", tmp_path)
    a1, a0 = B.load_admin1(), B.load_admin0()
    before = B.build_system("sa", a1, a0, "2026-11-10")
    ev_before = (tmp_path / "systems" / "sa" / "events.json").read_bytes()
    world = B.build_world.__wrapped__(a1, a0) if hasattr(B.build_world, "__wrapped__") else {"type": "FeatureCollection", "features": []}
    d = _curated_context()
    d["source"]["release"] = "2027-10-16"
    d["source"]["retrieved"] = "2026-11-10"
    d["countries"][0]["values"]["total_production"] = 1.234
    f = tmp_path / "ctx.json"
    f.write_text(json.dumps(d), encoding="utf-8")
    monkeypatch.setattr(G, "CONTEXT_FILE", f)
    out = G.build(world, today=TODAY)
    assert out["source"]["release"] == "2027-10-16"
    assert any(r["values"]["total_production"] == 1.234 for r in out["countries"])
    after = B.build_system("sa", a1, a0, "2026-11-10")
    assert (tmp_path / "systems" / "sa" / "events.json").read_bytes() == ev_before
    assert before == after


@needs_ne
def test_a_new_reviewed_event_leaves_national_context_alone(tmp_path, monkeypatch):
    """Research ingest and national context are separate concerns (brief §179)."""
    from pipeline import outputs
    monkeypatch.setitem(outputs._target, "root", tmp_path)
    (tmp_path / "x").mkdir()
    # The context builder takes no event input and its source never names one.
    import inspect
    # `restricted` (iteration 20) is a set of system ids by campaign state: it hides the newer national
    # year under the campaign policy and carries no event.
    assert set(inspect.signature(G.build).parameters) == {"world", "admin0", "today", "restricted"}
    src = inspect.getsource(G)
    assert "events.json" not in src and "load_events" not in src and "research_log" not in src


# --- the emitted artifacts ---------------------------------------------------------------------------

@needs_ne
@pytest.mark.parametrize("as_of", ["2022-01-01", "2023-06-30", "2024-02-29", "2026-04-09", "2026-11-10"])
def test_a_country_view_at_any_date_holds_nothing_from_after_it(as_of, tmp_path, monkeypatch):
    """Temporal fuzz: event dates, counts and map placement must agree at any as-of (brief §145)."""
    from pipeline import outputs
    monkeypatch.setitem(outputs._target, "root", tmp_path)
    a1, a0 = B.load_admin1(), B.load_admin0()
    for sid in systems.COUNTRY_SYSTEMS:
        summary = B.build_system(sid, a1, a0, as_of)["event_summary"]
        ev = json.loads((tmp_path / "systems" / sid / "events.json").read_text(encoding="utf-8"))["events"]
        assert all(e["date"][:10] <= as_of for e in ev), sid
        assert summary["recorded_events"] == len(ev), sid
        regions = json.loads((tmp_path / "systems" / sid / "regions.geojson").read_text(encoding="utf-8"))
        placed = sum(f["properties"]["recorded_events"] or 0 for f in regions["features"])
        assert placed == sum(1 for e in ev if e["region_code"]), sid


@needs_payload
def test_the_new_artifacts_are_declared_and_mirrored():
    for name in ("global/energy_context.json", "global/data_quality.json", "global/recent_evidence.json"):
        assert name in artifacts.GLOBAL_PAYLOADS
        assert (WEB / name).read_bytes() == (ROOT / "data" / "processed" / name).read_bytes(), name


@needs_payload
def test_context_rows_are_monitored_only_through_the_registry():
    c = _json("global/energy_context.json")
    owner = {a3: s["id"] for s in systems.SYSTEMS for a3 in s["admin0_a3"]}
    for r in c["countries"]:
        assert r["system_id"] == owner.get(r["a3"]), r["a3"]
    assert sum(1 for r in c["countries"] if r["system_id"] is None) > 150


@needs_payload
def test_taiwan_is_context_and_not_part_of_the_china_system():
    c = {r["a3"]: r for r in _json("global/energy_context.json")["countries"]}
    assert c["TWN"]["system_id"] is None and c["CHN"]["system_id"] == "cn"


@needs_payload
def test_context_rows_carry_no_incident_or_ranking_field_and_no_build_time():
    c = _json("global/energy_context.json")
    keys = set()
    for r in c["countries"]:
        keys |= set(G._walk(r))
    assert not [k for k in keys if any(p in k.lower() for p in G.FORBIDDEN_KEY_PARTS)]
    assert "build_time" not in c and "as_of" not in c


@needs_payload
def test_null_stays_null_in_the_artifact():
    c = _json("global/energy_context.json")
    nulls = sum(1 for r in c["countries"] for v in r["values"].values() if v is None)
    zeros = sum(1 for r in c["countries"] for v in r["values"].values() if v == 0)
    assert nulls > 0 and zeros > 0   # both exist, and they are different things


@needs_payload
def test_every_map_metric_has_a_unit_label_and_one_year():
    c = _json("global/energy_context.json")
    assert isinstance(c["comparison_year"], int)
    for m in c["map_metrics"]:
        assert c["metrics"][m]["unit"] and c["metrics"][m]["label"], m
    assert c["source"]["release"] and c["source"]["retrieved"] and c["source"]["attribution"]


@needs_payload
def test_the_selection_rule_is_stable_on_the_latest_release():
    """The rule, not the membership, is the durable decision. This reports drift rather than
    changing anything (brief §157)."""
    c = _json("global/energy_context.json")
    rows = sorted((r for r in c["countries"] if r["a3"] != "RUS"), key=lambda r: -(r["values"]["total_production"] or 0))
    assert {r["a3"] for r in rows[:5]} == {"CHN", "USA", "SAU", "CAN", "IND"}


@needs_payload
def test_the_manifest_gained_no_figure_per_country():
    m = _json("global/manifest.json")
    for s in m["systems"]:
        assert "total_production" not in json.dumps(s)
    states = m["corpus"]["research_lane_states"]
    assert sum(states.values()) == m["corpus"]["research_lanes"]


@needs_payload
def test_data_quality_holds_no_disruption_count_per_country():
    d = _json("global/data_quality.json")
    keys = {k.lower() for k in G._walk(d["systems"])}
    assert not [k for k in keys if any(p in k for p in ("record", "event", "episode", "count", "rank", "score"))], keys
    # A research finding is prose that can carry a tally; it stays on the country page.
    assert "finding" not in keys
    assert [s["name"] for s in d["systems"]] == sorted(s["name"] for s in d["systems"])
    assert set(G._walk(d["recovery_by_class"])).isdisjoint({"system_id", "country"})


@needs_payload
def test_recovery_statistics_respect_the_sample_rule():
    for r in _json("global/data_quality.json")["recovery_by_class"]["rows"]:
        if r["n"] < 3:
            assert "cases_days" in r and "median_days" not in r and "range_days" not in r
        elif r["n"] < 5:
            assert "range_days" in r and "median_days" not in r
        else:
            assert "median_days" in r


@needs_payload
def test_recent_evidence_is_chronological_safe_and_unranked():
    d = _json("global/recent_evidence.json")
    dates = [e["last_date"] for e in d["episodes"]]
    assert dates == sorted(dates, reverse=True)
    keys = set(G._walk(d["episodes"]))
    assert not keys & {"severity", "rank", "score", "impact", "lat", "lon", "latitude", "longitude", "coordinates",
                       "facility_name", "capacity_affected"}
    assert {e["system_id"] for e in d["episodes"]} <= set(systems.COUNTRY_SYSTEMS)


@needs_payload
def test_a_campaign_record_shows_no_effect_in_the_recent_list():
    d = _json("global/recent_evidence.json")
    ev = {e["event_id"]: e for e in _json("systems/sa/events.json")["events"]}
    withheld = {eid for eid, e in ev.items() if e.get("publication")}
    assert withheld
    shown = 0
    for ep in d["episodes"]:
        if ep["system_id"] != "sa":
            continue
        # A campaign-covered row carries a row key, not the episode id (iteration 20), so the
        # record is found by its date within the country.
        pool = [e for e in ev.values() if e["episode_id"] == ep["episode_id"]] or list(ev.values())
        for m in ep["members"]:
            # The expected state comes from the record, not from the feed's own flag.
            source = next(e for e in pool if e["date"] == m["date"])
            must = source["event_id"] in withheld
            assert bool(m["withheld"]) == must, ep["episode_id"]
            if must:
                shown += 1
                assert m["effect"] is None, ep["episode_id"]
    assert shown > 0


@needs_payload
@pytest.mark.parametrize("sid", systems.COUNTRY_SYSTEMS)
def test_recovery_coverage_adds_up_and_names_no_facility(sid):
    p = _json(f"systems/{sid}/system.json")
    rc = p["recovery_coverage"]
    total = sum(rc[k] for k in ("observed", "estimate", "other_statement", "researched_no_public_evidence",
                                "not_researched", "withheld_active_campaign"))
    assert total == p["event_summary"]["recorded_events"]
    assert set(rc["unresearched_by_class"]) <= set(p["taxonomy"]["asset_classes"])
    # Fixed keys: a facility could only enter through a field that is not on this list.
    assert set(rc) == {"observed", "estimate", "other_statement", "researched_no_public_evidence", "not_researched",
                       "withheld_active_campaign", "unresearched_by_class", "policy"}
    assert "modelled" not in json.dumps(rc).replace("Nothing is modelled", "")


@needs_payload
def test_no_estimate_is_counted_as_observed():
    for sid in systems.COUNTRY_SYSTEMS:
        events = _json(f"systems/{sid}/events.json")["events"]
        est = sum(1 for e in events if e["recovery"]["kind"] == "estimate")
        assert _json(f"systems/{sid}/system.json")["recovery_coverage"]["estimate"] == est, sid


@needs_payload
def test_every_record_reviewed_in_this_pass_was_blind_reviewed():
    for sid in systems.COUNTRY_SYSTEMS:
        for e in _json(f"systems/{sid}/events.json")["events"]:
            if e["review"]["reviewed_at"] >= "2026-11-10":
                assert e["review"]["review_status"] == "blind_reviewed", e["event_id"]
                assert set(e["review"]["roles"].values()) <= {"accept", "accept_with_correction"}, e["event_id"]


@needs_payload
def test_a_month_precision_record_keeps_its_precision_in_the_feed():
    events = {sid: _json(f"systems/{sid}/events.json")["events"] for sid in systems.COUNTRY_SYSTEMS}
    for ep in _json("global/recent_evidence.json")["episodes"]:
        pool = ([e for e in events[ep["system_id"]] if e["episode_id"] == ep["episode_id"]]
                or events[ep["system_id"]])   # a row key since iteration 20: found by date
        for m in ep["members"]:
            assert m["date_precision"] == next(e for e in pool if e["date"] == m["date"])["date_precision"], ep["episode_id"]


@needs_payload
@pytest.mark.parametrize("sid", systems.COUNTRY_SYSTEMS)
def test_citation_quality_carries_no_address_and_is_inside_one_country(sid):
    cq = _json(f"systems/{sid}/system.json")["citation_quality"]
    assert "http" not in json.dumps(cq)
    assert cq["with_publication_date"] <= cq["citations"]
    assert "citation_quality" not in json.dumps(_json("global/manifest.json"))
    assert "citation_quality" not in json.dumps(_json("global/data_quality.json"))


@pytest.mark.parametrize("phrase", [
    "repair work began", "https://x.example/refinery-back-online", "https://x.example/still-shut",
    "https://x.example/running-at-70", "re-started", "\u0627\u0633\u062a\u0623\u0646\u0641\u062a \u0627\u0644\u0639\u0645\u0644",
    "https://x.example/%D8%A7%D8%B3%D8%AA%D8%A6%D9%86%D8%A7%D9%81",
])
def test_status_wording_reads_addresses_and_forms_a_status_check_used_to_miss(phrase):
    assert B.status_wording(phrase), phrase


QUEUE = ROOT / "data" / "candidates"


@needs_payload
@pytest.mark.skipif(not (QUEUE / "us.json").exists(), reason="the local queue is not in CI")
def test_no_unpublished_record_is_named_in_any_served_string():
    """Iteration 18 red team: a held record's name reached the payload through research-log prose."""
    served = "\n".join(p.read_text(encoding="utf-8") for p in WEB.rglob("*.json") if p.stat().st_size < 3_000_000).lower()
    published, names, ids = set(), set(), set()
    for sid in systems.COUNTRY_SYSTEMS:
        for e in _json(f"systems/{sid}/events.json")["events"]:
            published.add(e["event_id"])
            names.add((e.get("facility_name") or "").lower())
    leaked = []
    for sid in systems.COUNTRY_SYSTEMS:
        if not (QUEUE / f"{sid}.json").exists():      # onboarded, nothing researched yet
            continue
        for r in json.loads((QUEUE / f"{sid}.json").read_text(encoding="utf-8")):
            cid = r.get("candidate_id") or ""
            # The whole id, not a prefix of a published one: two lanes named one event
            # 'x-power-cuts' and 'x-power-cuts-generation-shortfall' (iteration 19).
            if (cid and cid not in published and len(cid) > 12 and cid in served
                    and re.search(r"(?<![\w-])" + re.escape(cid.lower()) + r"(?![\w-])", served)):
                leaked.append(cid)
    assert not leaked, leaked[:10]


@needs_payload
def test_a_research_log_says_counts_and_process_never_held_material():
    for sid in systems.COUNTRY_SYSTEMS:
        passes = _json(f"systems/{sid}/system.json")["research_log"]["passes"]
        newest = passes[-1] if passes else {}
        for lane in newest.get("lanes") or []:
            for field in ("limitation", "finding"):
                assert not re.search(r"\bheld\b|\.md\b", lane.get(field) or "", re.I), (sid, lane["lane"], field)


@needs_payload
def test_source_families_are_a_set_and_not_a_score():
    for sid in systems.COUNTRY_SYSTEMS:
        sf = _json(f"systems/{sid}/system.json")["source_families"]
        assert sorted(sf["present"]) == sorted(sf["labels"])
        assert not any(isinstance(v, (int, float)) for v in sf.values())


# --- campaign and copy ---------------------------------------------------------------------------

def test_arabic_status_wording_is_caught_on_a_campaign_record():
    for phrase in ("استئناف الإنتاج", "إعادة تشغيل", "إصلاح"):
        assert B.STATUS_WORDING.search(phrase), phrase


@pytest.mark.repo_hygiene
def test_copy_does_not_overclaim_coverage():
    bad = re.compile(r"complete coverage|fully covered|exhaustive|all disruptions|every disruption", re.I)
    for f in (ROOT / "web" / "src" / "global").glob("*.tsx"):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            # A lint directive names a rule; it is not copy a reader sees.
            if "eslint-disable" in line:
                continue
            assert not bad.search(line), (f.name, i, line.strip())


@pytest.mark.repo_hygiene
def test_the_frontend_holds_no_country_list_for_the_context_layer():
    src = (ROOT / "web" / "src" / "global" / "context.ts").read_text(encoding="utf-8")
    assert not re.search(r'"(CHN|USA|SAU|CAN|IND|AUS)"', src)


@pytest.mark.repo_hygiene
def test_a_context_country_can_never_open_a_dossier():
    """A dossier is reached only with a system id from the registry; a context row has none."""
    src = (ROOT / "web" / "src" / "global" / "WorldContext.tsx").read_text(encoding="utf-8")
    calls = re.findall(r"[^\n;{]*\bnavigate\([^)]*\)", src)
    assert calls
    for c in calls:
        if "import" in c:
            continue
        assert re.search(r"if \((r\.system_id|sid)\) navigate\((r\.system_id|sid)\)|navigate\(row\.system_id as string\)", c), c
    assert "events.json" not in src


@pytest.mark.repo_hygiene
def test_no_view_offers_a_severity_order():
    src = (ROOT / "web" / "src" / "global" / "GlobalPanels.tsx").read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert not re.search(r"severity|\.sort\(\(a, b\) => \(?b\.(records|effect)", code)
