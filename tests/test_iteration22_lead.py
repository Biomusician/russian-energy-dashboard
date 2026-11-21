"""Iteration 22, integration rules that sit between the agents' modules.

Each test here pins a decision made when the impact layer, the confidence model and the pages were
joined: who tells the confidence model that a record's sources were reviewed for independence, what
the Gulf page's standing sentence says now that one section may carry strait wording, and that the
impact corpus as served holds to the owner's rules (no record that a country system holds, no AI
claim without a source, nothing kinetic outside the abstracted form).
"""
import json
from pathlib import Path

import pytest

from pipeline import evidence_confidence as EC

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

needs_payload = pytest.mark.skipif(not (PROCESSED / "global" / "impacts.json").exists(),
                                   reason="impact payload not built")


def _json(rel):
    return json.loads((PROCESSED / rel).read_text(encoding="utf-8"))


def _records():
    doc = _json("global/impacts.json")
    return doc["records"] + doc["attempts"]


@needs_payload
def test_an_impact_record_reviewed_for_origins_is_counted_as_reviewed():
    """The source-and-attribution reviewer sets shared origins on relays, so an impact record's
    origin count is a reviewed count. The build has to SAY so to the model, or every record is held
    at Moderate for a reason that is not true of it (which is what happened at integration)."""
    recs = _records()
    reviewed = [r for r in recs if r["review"]["roles"].get("attribution_source") in ("accept", "accept_with_correction")]
    assert reviewed, "no reviewed impact record to check"
    for r in reviewed:
        ec = r["evidence_confidence"]
        assert ec["components"]["origins"]["basis"] == "reviewed", r["impact_id"]
        assert ec.get("cap") != "origins_not_reviewed", r["impact_id"]


@needs_payload
def test_high_confidence_always_rests_on_two_counted_origins():
    """High is never earned by one originating statement, however many links carry it."""
    for r in _records():
        ec = r["evidence_confidence"]
        if ec["category"] == "HIGH":
            assert ec["components"]["origins"]["count"] >= 2, r["impact_id"]


def test_the_impact_build_passes_the_review_block_to_the_confidence_model():
    """Unit form of the first test, so it holds without a payload."""
    sources = [
        {"ref": "s1", "url": "https://operator.example/statement", "publisher": "Example Operator", "date": "2025-03-05",
         "source_role": "operator", "medium": "web", "supports": ["occurrence", "effect"], "opened": True},
        {"ref": "s2", "url": "https://wire.example/story", "publisher": "Example Wire", "date": "2025-03-05",
         "source_role": "wire", "medium": "web", "supports": ["occurrence", "effect"], "opened": True},
    ]
    review = {"roles": {"evidence": "accept", "attribution_source": "accept", "safety": "accept"}}
    with_review = EC.assess(sources, "2025-03-05", None, "quantified", None, review=review)
    without = EC.assess(sources, "2025-03-05", None, "quantified", None)
    assert with_review["components"]["origins"]["basis"] == "reviewed" and with_review["category"] == "HIGH"
    assert without["components"]["origins"]["basis"] == "publishers" and without["category"] == "MODERATE"
    src = (ROOT / "pipeline" / "global_impacts.py").read_text(encoding="utf-8")
    assert 'review=r.get("review")' in src


@needs_payload
def test_no_impact_record_claims_ai_involvement_without_a_source_for_it():
    for r in _records():
        ai = r["ai_involvement"]
        if ai["status"] != "NONE_REPORTED":
            refs = set(ai.get("source_refs") or [])
            assert refs and refs <= {s["ref"] for s in r["sources"]}, r["impact_id"]
            assert any("ai_involvement" in (s.get("supports") or []) for s in r["sources"] if s["ref"] in refs), r["impact_id"]


@needs_payload
def test_every_kinetic_or_sabotage_impact_record_is_country_abstracted_as_served():
    for r in _records():
        if r["cause_family"] in ("kinetic", "sabotage"):
            assert r["publication_policy"] == "country_abstracted", r["impact_id"]
            assert r.get("admin1") is None and r["geographic_precision"] in ("country", "multi_country"), r["impact_id"]
            assert all(not s.get("title_original") and not s.get("title_en") for s in r["sources"]), r["impact_id"]


@needs_payload
def test_no_gulf_or_iran_impact_record_carries_a_region():
    # Read from the curated register, not a list typed here (iteration 23, F10): a system that comes
    # under the campaign policy is covered the day its state is recorded.
    from pipeline import build_systems as B, systems as S
    states = B.load_campaigns().get("system_states") or {}
    campaign = {a3 for s in S.SYSTEMS if s["kind"] == "country"
                and (states.get(s["id"]) or {}).get("state") in B.RESTRICTING_STATES for a3 in s["admin0_a3"]}
    assert campaign, "no campaign-restricted country system is recorded: retire this guard deliberately"
    for r in _records():
        a3 = r["country_a3"]
        if (set(a3) if isinstance(a3, list) else {a3}) & campaign:
            assert r.get("admin1") is None, r["impact_id"]


def test_the_import_has_no_override_for_a_held_country_record():
    """Owner brief §216: an event held from a country system cannot appear in the impact layer
    because the layer has a different schema. The import may only be told a match is a different
    event; the earlier allow-list is gone and must not come back."""
    src = (ROOT / "scripts" / "import_impacts.py").read_text(encoding="utf-8")
    assert "reconcile_distinct.json" in src
    assert 'read_json(queue / "reconcile_allow.json")' not in src
    assert "allowed by the lead's override" not in src


@needs_payload
def test_the_gulf_views_standing_sentence_points_at_the_separate_regional_context():
    """`global/gulf.json` still holds no strait or shipping material. Its sentence used to say "this
    view has no ... strait ... information", which stopped being true of the PAGE when the regional
    context section was added; it now speaks for the figures and names the separate artifact."""
    from pipeline import gulf_context
    said = _json("global/gulf.json")["not_built"]
    assert said.startswith("These regional figures carry no route, strait, shipping or tanker information")
    assert "published separately as regional context and enter none of these figures" in said
    assert "This view has no" not in said
    assert "hormuz" in gulf_context.FORBIDDEN_KEY_PARTS and "strait" in gulf_context.FORBIDDEN_KEY_PARTS


@needs_payload
def test_regional_context_is_the_only_served_file_with_strait_wording():
    """The narrowed rule, as bytes: strait wording appears in `global/regional_context.json` (and in
    the impact payload's own statement of what it does not hold), and in no country system's events."""
    for path in sorted((PROCESSED / "systems").glob("*/events.json")):
        text = path.read_text(encoding="utf-8").lower()
        assert "hormuz" not in text and "strait of" not in text, path
    gulf = json.dumps({k: v for k, v in _json("global/gulf.json").items() if k not in ("recent", "not_built")}).lower()
    assert "hormuz" not in gulf and "strait" not in gulf
    for r in _records():
        text = json.dumps({k: r.get(k) for k in ("summary", "effect", "impact_id")}).lower()
        assert "hormuz" not in text and "strait of" not in text, r["impact_id"]
    ctx = _json("global/regional_context.json")
    assert any("hormuz" in json.dumps(e).lower() for e in ctx["entries"])
    # And what the context itself may never say, as served.
    served = json.dumps(ctx["entries"]).lower()
    for word in ("tanker", "bypass", "chokepoint", "choke point", "alternate route", "alternative route"):
        assert word not in served, word


@needs_payload
def test_regional_context_names_its_group_and_the_manifest_names_its_file():
    """The registry pairs the group and the file once; both served files carry the pairing, so no
    page pairs them by hand (iteration 22 integration: three frontend constants removed)."""
    ctx = _json("global/regional_context.json")
    manifest = _json("global/manifest.json")
    group = ctx["group"]
    assert group and manifest["groups"][group]["regional_context"] == "global/regional_context.json"
    assert [g for g, d in manifest["groups"].items() if d.get("regional_context")] == [group]
    src = " ".join((ROOT / "web" / "src" / "global" / f).read_text(encoding="utf-8")
                    for f in ("countryTabs.ts", "searchIndex.ts", "impacts/brief/briefInputs.ts"))
    assert '"gulf_littoral"' not in src and 'SLUG = "gulf"' not in src
