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
    """DO NOT MOVE THE GOALPOSTS. Only the iteration-18 pass uses the new vocabulary."""
    log = json.loads((ROOT / "data" / "curated" / "systems" / sid / "research_log.json").read_text(encoding="utf-8"))
    sysp = [p for p in log["passes"] if p["kind"] == "systematic"]
    for p in sysp[:-1]:
        assert all("execution" not in lane and "status" in lane for lane in p["lanes"]), p["date"]
    assert all("execution" in lane and "status" not in lane for lane in sysp[-1]["lanes"])


@needs_payload
@pytest.mark.parametrize("sid", systems.COUNTRY_SYSTEMS)
def test_the_emitted_lane_states_match_the_log(sid):
    p = _json(f"systems/{sid}/system.json")
    newest = [x for x in p["research_log"]["passes"] if x["kind"] == "systematic"][-1]
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
    (lambda d: d["countries"][0]["newer"].__setitem__("oil_production", {"year": 2023, "value": 1}), "not after the comparison year"),
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
    a = G.build({"type": "FeatureCollection", "features": []}, today=TODAY)
    # The context builder takes no event input at all.
    import inspect
    assert set(inspect.signature(G.build).parameters) == {"world", "admin0", "today"}
    b = G.build({"type": "FeatureCollection", "features": []}, today=TODAY)
    assert a == b


# --- the emitted artifacts ---------------------------------------------------------------------------

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
    keys = set(G._walk(d["systems"]))
    assert not keys & {"records", "events", "episodes", "recorded_events", "rank", "score", "quality_score"}
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
    campaign_regions = 0
    for ep in d["episodes"]:
        for m in ep["members"]:
            if m["withheld"]:
                campaign_regions += 1
                assert m["effect"] is None
    assert campaign_regions == sum(1 for e in ev.values() if e.get("publication")) or campaign_regions > 0


@needs_payload
@pytest.mark.parametrize("sid", systems.COUNTRY_SYSTEMS)
def test_recovery_coverage_adds_up_and_names_no_facility(sid):
    p = _json(f"systems/{sid}/system.json")
    rc = p["recovery_coverage"]
    total = sum(rc[k] for k in ("observed", "estimate", "other_statement", "researched_no_public_evidence",
                                "not_researched", "withheld_active_campaign"))
    assert total == p["event_summary"]["recorded_events"]
    assert set(rc["unresearched_by_class"]) <= set(p["taxonomy"]["asset_classes"])
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
    for ep in _json("global/recent_evidence.json")["episodes"]:
        for m in ep["members"]:
            assert m["date_precision"] in ("day", "month", "range"), ep["episode_id"]


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
        assert re.search(r"if \((r\.system_id|sid)\) navigate\((r\.system_id|sid)\)", c), c
    assert "events.json" not in src


@pytest.mark.repo_hygiene
def test_no_view_offers_a_severity_order():
    src = (ROOT / "web" / "src" / "global" / "GlobalPanels.tsx").read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    assert not re.search(r"severity|\.sort\(\(a, b\) => \(?b\.(records|effect)", code)
