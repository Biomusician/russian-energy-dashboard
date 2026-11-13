"""Iteration 21 safety red team: what the new surfaces made easier to infer, and the gates that close it.

Four paths, each found by reading only the public app and the committed files:

1. Opaque ids. An abstracted attack record's id ended in sha1(queue id)[:4], or kept a lane's own
   "-attack-2". Queue ids name the facility about four times in ten, so a reader with a list of a
   country's plants could hash guesses at the published date and class; and "-attack-2" says a
   sibling candidate exists. Record anchors (#ev-<id>) put the id in every shared link.
2. The committed link-health file. It is written from the records as they stood at the check; a
   record withdrawn or held afterwards would leave its citation's address and its count there.
3. What's new announced "published records were re-reviewed" for a campaign system, the one
   review change its own rule hides record by record.
4. A campaign system's stated research gap said how many records were held and what they were.
"""
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

import pytest

from pipeline import build_systems as B
from pipeline import diff_builds, systems, whats_new as W

ROOT = Path(__file__).resolve().parent.parent
CURATED = ROOT / "data" / "curated" / "systems"
GULF = ("ae", "bh", "iq", "ir", "kw", "om", "qa", "sa")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


# --- 1. opaque ids ---------------------------------------------------------------------------------

KW = {"geography": {"precision_policy": {"kinetic": "country", "reason": "r"}}}


def _attack(eid):
    return {"event_id": eid, "date": "2026-03-12", "date_precision": "day", "asset_class": "refinery",
            "cause": "kinetic_strike", "geography_precision": "country", "region_code": None,
            "regions_affected": [], "facility_name": None, "facility_name_local": None, "operator": None,
            "summary": "A refinery was reported attacked.", "effect": None, "threshold_basis": "Clause 1.",
            "sources": [{"url": "https://example.org/a/123456", "publisher": "P"}]}


def test_an_opaque_id_cannot_be_matched_by_hashing_guessed_facility_names():
    imp = _load("import_candidates")
    r = {"candidate_id": "kw-2026-03-12-example-refinery-strike", "date": "2026-03-12", "asset_class": "refinery"}
    oid = imp.opaque_id("kw", r, key=b"one key")
    token = oid.rsplit("-attack-", 1)[1]
    assert re.fullmatch(B.OPAQUE_TOKEN, token), oid
    # The old token was the unkeyed hash: anyone could recompute it from a guessed queue id.
    assert not token.startswith(hashlib.sha1(r["candidate_id"].encode("utf-8")).hexdigest()[:4])
    assert imp.opaque_id("kw", r, key=b"one key") == oid, "stable for the life of the record"
    assert imp.opaque_id("kw", r, key=b"another key") != oid, "the token depends on the secret"


@pytest.mark.parametrize("lane_id", ["kw-2026-03-12-refinery-attack-1", "kw-2026-03-12-refinery-attack-2",
                                     "kw-2026-03-12-refinery-attack-dup20"])
def test_a_lanes_own_numbering_never_becomes_the_published_id(lane_id):
    imp = _load("import_candidates")
    r = {"candidate_id": lane_id, "date": "2026-03-12", "asset_class": "refinery"}
    oid = imp.opaque_id("kw", r, key=b"k")
    assert oid != lane_id and re.fullmatch(B.OPAQUE_TOKEN, oid.rsplit("-attack-", 1)[1])


@pytest.mark.parametrize("token", ["1", "2", "dup20", "a1b2", "3f9a2cd"])
def test_the_build_refuses_an_attack_id_whose_token_is_not_the_keyed_hash(token):
    probs = B.precision_problems("kw", KW, [_attack(f"kw-2026-03-12-refinery-attack-{token}")])
    assert any("keyed hash" in p or "opaque id" in p for p in probs), (token, probs)
    assert B.precision_problems("kw", KW, [_attack("kw-2026-03-12-refinery-attack-3f9a2c")]) == []


def test_the_opaque_id_key_is_local_and_never_committed():
    imp = _load("import_candidates")
    rel = imp.OPAQUE_KEY.relative_to(ROOT).as_posix()
    assert rel.startswith("data/candidates/")
    r = subprocess.run(["git", "check-ignore", "-q", rel], cwd=ROOT)
    assert r.returncode == 0, f"{rel} is not ignored by git"
    tracked = subprocess.run(["git", "ls-files", "data/candidates"], cwd=ROOT, capture_output=True, text=True).stdout
    assert "opaque_id.key" not in tracked


def test_every_published_attack_id_under_a_country_rule_has_the_keyed_token():
    seen = 0
    for sid in systems.COUNTRY_SYSTEMS:
        doc = _json(CURATED / sid / "system.json")
        if ((doc.get("geography") or {}).get("precision_policy") or {}).get("kinetic") != "country":
            continue
        seen += 1
        for e in _json(CURATED / sid / "events.json")["events"]:
            if e["cause"] in B.KINETIC_CAUSES:
                assert re.fullmatch(B.OPAQUE_TOKEN, e["event_id"].rsplit("-attack-", 1)[-1]), e["event_id"]
    assert seen == 7


# --- 2. the committed link-health file -------------------------------------------------------------

def _published():
    return {sid: (None, _json(CURATED / sid / "events.json")["events"], None) for sid in systems.COUNTRY_SYSTEMS}


def test_the_committed_link_health_file_names_only_published_citations():
    health = _json(CURATED / "source_link_health.json")
    assert health["link_states"], "no link states to check"
    assert B.link_health_problems(health, _published()) == []


def test_a_withdrawn_records_citation_left_in_the_link_health_file_fails_the_build():
    health = _json(CURATED / "source_link_health.json")
    pub = _published()
    sa = next(e for e in pub["sa"][1] if e.get("cause") == "kinetic_strike")
    gone = {**pub, "sa": (None, [e for e in pub["sa"][1] if e is not sa], None)}
    probs = B.link_health_problems(health, gone)
    url = sa["sources"][0]["url"]
    assert any(url in p and "link_states" in p for p in probs), probs
    assert any("by_system: sa counts" in p for p in probs), probs


def test_a_link_health_entry_for_an_unpublished_address_fails_the_build():
    health = copy.deepcopy(_json(CURATED / "source_link_health.json"))
    health["page_stated_dates"]["https://example.org/held-record"] = "2026-03-01"
    health["final_addresses"]["https://example.org/?p=1"] = "https://example.org/kw-refinery-strike"
    health["link_states"][next(iter(health["link_states"]))] = "reachable: Example refinery restarted"
    probs = B.link_health_problems(health, _published())
    assert any("page_stated_dates" in p for p in probs)
    assert any("final_addresses" in p for p in probs)
    assert any("not a bare state" in p for p in probs)


def test_the_build_runs_the_link_health_gate():
    src = (ROOT / "pipeline" / "build_systems.py").read_text(encoding="utf-8")
    body = src[src.index("def build(theatre_snapshot):"):]
    assert "link_health_problems(read_json(LINK_HEALTH)" in body


# --- 3. What's new and re-review under the campaign rule --------------------------------------------

def _state(sid, campaign, reviewed, events):
    s = {"system_id": sid, "as_of": "2026-11-11", "campaign_state": campaign,
         "publication_policy": {"withheld_records": 0, "campaigns": [], "release_rule": {"id": "A"}},
         "research_log": {"passes": []}, "research_freshness": {}, "sectors": [], "sources": [],
         "research_gaps": [], "citation_quality": {}, "geography": {}, "profile": {}, "record_reviewed": reviewed}
    return {"systems": {sid: {"system": s, "events": {"as_of": "2026-11-11", "events": events, "episodes": []}}},
            "energy_context": {}}


def _ev(eid, reviewed, covered):
    return {"event_id": eid, "date": "2026-03-02", "date_precision": "day", "region_code": None, "region_name": None,
            "geography_precision": "country", "regions_affected": [], "asset_class": "refinery",
            "cause": "kinetic_strike", "summary": "s", "sources": [{"url": "https://example.org/a"}],
            "recovery": {"research_status": "WITHHELD_ACTIVE_CAMPAIGN", "kind": None, "date": None},
            "review": {"reviewed_at": reviewed},
            "publication": {"rule": "r", "campaign_id": "c", "withheld": ["recovery"], "note": "n"} if covered else None}


QUIET = diff_builds.diff(*[{"as_of": "2026-11-12", "esdi": 7.0, "build_time": "x", "build_inputs": {"groups": {}}}] * 2,
                         [], [], [], [])
CMP = {"previous_as_of": "2026-11-11", "current_as_of": "2026-11-12", "mode": "production", "basis": "b"}


def test_a_re_review_of_a_campaign_record_is_not_announced_for_the_system():
    prev = _state("kw", {"state": "ACTIVE_KINETIC_CAMPAIGN"}, "2026-11-01", [_ev("kw-x", "2026-11-01", True)])
    curr = copy.deepcopy(prev)
    curr["systems"]["kw"]["system"]["record_reviewed"] = "2026-11-12"
    curr["systems"]["kw"]["events"]["events"][0]["review"]["reviewed_at"] = "2026-11-12"
    d = W.derive(prev, curr, QUIET, CMP)
    assert "re-reviewed" not in json.dumps(d["systems"]) and "12 Nov 2026" not in json.dumps(d["systems"])
    assert not any(r["system_id"] == "kw" for r in d["systems"]), "a re-review alone shows nothing, not even build-only"


def test_a_re_review_outside_a_campaign_is_still_announced():
    prev = _state("us", None, "2026-11-01", [_ev("us-x", "2026-11-01", False)])
    curr = copy.deepcopy(prev)
    curr["systems"]["us"]["system"]["record_reviewed"] = "2026-11-12"
    d = W.derive(prev, curr, QUIET, CMP)
    assert "re-reviewed" in json.dumps(d["systems"])


# --- 4. held-record wording in a campaign system's research prose ------------------------------------

def test_no_campaign_system_states_a_held_record_in_its_gaps_or_research_prose():
    states = B.load_campaigns().get("system_states") or {}
    checked = 0
    for sid in GULF:
        assert (states.get(sid) or {}).get("state") in B.RESTRICTING_STATES, sid
        doc, log = _json(CURATED / sid / "system.json"), _json(CURATED / sid / "research_log.json")
        assert B.held_wording_problems(doc, log) == [], sid
        checked += 1
    assert checked == 8


def test_a_held_count_in_a_campaign_systems_gap_fails_the_build():
    doc = {"research_gaps": ["Non-conflict incidents remain thin: one 2024 power outage is held rather than converted."]}
    log = {"passes": [{"date": "2026-11-12", "status_reason": "2 candidates remain", "lanes": [
        {"lane": "X1", "finding": "One record is on hold pending review."}]}]}
    probs = B.held_wording_problems(doc, log)
    assert len(probs) == 3, probs
    assert B.held_wording_problems({"research_gaps": ["Reporting gives residents, not customers."]}, {"passes": []}) == []


def test_the_build_applies_the_held_wording_gate_to_campaign_systems_only():
    src = (ROOT / "pipeline" / "build_systems.py").read_text(encoding="utf-8")
    body = src[src.index("def build_system("):src.index("def build_world(")]
    i = body.index("held_wording_problems(doc, research_log)")
    assert "RESTRICTING_STATES" in body[i - 200:i]
