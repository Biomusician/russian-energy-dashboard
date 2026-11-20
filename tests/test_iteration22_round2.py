"""Iteration 22, release closure round 2: the invariants the lead's rulings R4, R5, R8, R10 and R11 added.

Each rule is shown with one synthetic fixture record (tests/fixtures/impacts22) changed in one way,
and, where the rule is about what is served, against the served payload itself.

  R4  the record-level origin_count never counts a lead-added citation, an actor's own claim or a
      discovery aid, so the inspector's line cannot contradict the confidence component beside it.
  R5  review.ai_check is served only where it is known ("passed", on a record with reported AI
      involvement); "not_applicable" stamped on every other record is refused.
  R8  an abstracted record's short or redirecting citation address (?p=, /node/, a shortener...) is
      refused unless the link check reached it at that same address.
  R10 one served shape for "affected, no figure": {"value": "unknown", ...}; null is not applicable.
  R11 a served research note carries no figure from a source (a price, a percentage, a volume).
"""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

from pipeline import evidence_confidence as EC, global_impacts as G

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "impacts22"
WORLD = ROOT / "data" / "processed" / "global" / "world.geojson"
SERVED = ROOT / "data" / "processed" / "global" / "impacts.json"
UNIT_NAMES = {"ir": ["khuzestan", "tehran", "bushehr"], "iq": ["basrah", "al basrah", "kurdistan"],
              "sa": ["eastern province"], "ae": ["abu dhabi"], "bh": [], "kw": [], "om": [], "qa": []}
FRA = "imp-2025-03-05-fra-electricity-synthetic-grid-ransomware"
USA = "imp-2026-02-14-usa-fuel_supply-synthetic-payment-outage"
UKR = "imp-2025-10-08-ukr-electricity-attack-3fa91c"
POL = "imp-2024-11-18-pol-telecom-synthetic-network-outage"


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ctx(link_states=None):
    states = _json(FIXTURE / "link_health.json")["link_states"]
    states.update(link_states or {})
    return G.load_context(WORLD, unit_names=copy.deepcopy(UNIT_NAMES), link_states=states)


def rec(impact_id):
    return copy.deepcopy(next(r for r in _json(FIXTURE / "events.json")["records"] if r["impact_id"] == impact_id))


def problems(record, link_states=None):
    return G.one_record_problems(record, ctx(link_states))


def refused(record, text, link_states=None):
    got = problems(record, link_states)
    assert any(text in p for p in got), f"expected a refusal containing {text!r}, got {got}"


def _script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- R4: origin_count -------------------------------------------------------------------------------

def _src(ref, url, role="media", publisher=None, **extra):
    return {"ref": ref, "url": url, "publisher": publisher or url.split("/")[2], "date": "2025-03-05",
            "language": "en", "source_role": role, "medium": "web", "social": None,
            "supports": ["occurrence", "effect"], "opened": True, **extra}


def test_origin_count_leaves_out_lead_added_citations_own_claims_and_discovery_aids():
    a = _src("s1", "https://one.example/synthetic/a")
    b = _src("s2", "https://two.example/synthetic/b")
    base = EC.served_origin_count([a, b])
    assert base == 2
    lead = _src("s3", "https://three.example/synthetic/c", added_by="lead", opened=False)
    claim = _src("s4", "https://group.example/synthetic/d", role="actor_self_claim", publisher="Example Group")
    aggregator = _src("s5", "https://four.example/synthetic/e", role="aggregator")
    wiki = _src("s6", "https://en.wikipedia.org/wiki/Synthetic")
    assert EC.served_origin_count([a, b, lead, claim, aggregator, wiki]) == base
    # The plain grouping would have counted the lead-added citation, the claim and the aggregator.
    assert EC.independent_origins([a, b, lead, claim, aggregator, wiki]) > base
    # A press report that relays a claim still reports the event: it is counted, as the confidence
    # component counts it.
    relay = _src("s7", "https://five.example/synthetic/f", attribution_basis="actor_self_claim")
    assert EC.served_origin_count([a, b, relay]) == 3


def test_a_lead_added_citation_never_raises_the_served_count_or_contradicts_the_component():
    r = rec(FRA)
    served_before = G.serve_record(r, ctx())
    added = _src("s9", "https://newpublisher.example/synthetic/later", role="operator", added_by="lead", opened=False)
    r["sources"].append(added)
    served = G.serve_record(r, ctx())
    assert served["origin_count"] == served_before["origin_count"]
    assert served["origin_count"] >= served["evidence_confidence"]["components"]["origins"]["count"]


def test_served_origin_count_is_never_below_its_confidence_component():
    doc = _json(SERVED)
    for r in doc["records"] + doc["attempts"]:
        assert r["origin_count"] >= r["evidence_confidence"]["components"]["origins"]["count"], r["impact_id"]
        lead = [s for s in r["sources"] if s.get("added_by") == "lead"]
        if lead:
            rest = [s for s in r["sources"] if s.get("added_by") != "lead"]
            assert r["origin_count"] == EC.served_origin_count(rest, r["attribution"]), r["impact_id"]


# --- R5: review.ai_check ----------------------------------------------------------------------------

def test_ai_check_is_passed_where_ai_is_reported_and_absent_elsewhere():
    r = rec(FRA)
    assert "ai_check" not in r["review"] and not [p for p in problems(r) if "ai_check" in p]
    r["review"]["ai_check"] = "not_applicable"
    refused(r, "review.ai_check")
    r["review"]["ai_check"] = "passed"
    refused(r, "review.ai_check")
    r = rec(USA)
    assert r["review"]["ai_check"] == "passed" and not [p for p in problems(r) if "ai_check" in p]
    del r["review"]["ai_check"]
    refused(r, "review.ai_check")


def test_the_import_writes_no_ai_check_where_none_is_recorded():
    I = _script("import_impacts")
    r = rec(FRA)
    verdicts = {role: {"verdict": "accept"} for role in I.ROLE_ORDER}
    assert "ai_check" not in I.review_block(r, verdicts, "2026-11-19", I.ROLE_ORDER)
    r = rec(USA)
    assert I.review_block(r, verdicts, "2026-11-19", I.ROLE_ORDER)["ai_check"] == "passed"


def test_no_served_record_carries_a_mechanical_ai_check():
    doc = _json(SERVED)
    for r in doc["records"] + doc["attempts"]:
        ai = r["ai_involvement"]["status"] != "NONE_REPORTED"
        assert r["review"].get("ai_check") == ("passed" if ai else None), r["impact_id"]


# --- R8: short or redirecting addresses on abstracted records ----------------------------------------

@pytest.mark.parametrize("url", [
    "https://synthetic-news.example/?p=12345",
    "https://synthetic-news.example/node/753886",
    "https://synthetic-news.example/article-3034103.html",
    "https://bit.ly/synthetic",
    "https://synthetic-news.example/story/amp/",
])
def test_an_abstracted_record_refuses_an_unresolved_short_address(url):
    r = rec(UKR)
    assert r["publication_policy"] == G.ABSTRACTED and not problems(r)
    r["sources"][0]["url"] = url
    refused(r, "short or redirecting form")
    # Reached at that same address by the link check: it stands.
    assert not [p for p in problems(r, {url: "reachable"}) if "short or redirecting" in p]
    # Redirected, blocked or dead: still refused.
    for state in ("redirected", "blocked", "dead"):
        refused(r, "short or redirecting form", {url: state})


def test_a_standard_record_and_a_plain_numeric_address_are_not_caught():
    r = rec(FRA)
    r["sources"][0]["url"] = "https://synthetic-news.example/?p=12345"
    assert not [p for p in problems(r) if "short or redirecting" in p]
    r = rec(UKR)
    r["sources"][0]["url"] = "https://synthetic-news.example/stories/3416422/"
    assert not [p for p in problems(r) if "short or redirecting" in p]


def test_no_served_abstracted_record_cites_an_unresolved_short_address():
    doc = _json(SERVED)
    states = G.load_context().get("link_states")
    for r in doc["records"] + doc["attempts"]:
        if r["publication_policy"] == G.ABSTRACTED:
            for s in r["sources"]:
                assert not G.alias_unresolved(s["url"], {"link_states": states}), (r["impact_id"], s["ref"])


# --- R10: one shape for "affected, no figure" --------------------------------------------------------

@pytest.mark.parametrize("given, want", [
    ("unknown", {"value": "unknown", "unit": None, "qualifier": None, "source_says": None}),
    ({"value": "unknown", "unit": None}, {"value": "unknown", "unit": None, "qualifier": None, "source_says": None}),
    ({"value": None, "unit": None, "qualifier": None, "source_says": "no figure"},
     {"value": "unknown", "unit": None, "qualifier": None, "source_says": "no figure"}),
    ({"value": None, "unit": "unknown", "qualifier": None, "source_says": "no figure"},
     {"value": "unknown", "unit": None, "qualifier": None, "source_says": "no figure"}),
    ({"value": None, "unit": "homes", "qualifier": None, "source_says": "thousands of homes"},
     {"value": "unknown", "unit": "homes", "qualifier": None, "source_says": "thousands of homes"}),
    ({"value": "not_researched", "unit": None, "qualifier": None, "source_says": "x"},
     {"value": "not_researched", "unit": None, "qualifier": None, "source_says": "x"}),
])
def test_every_spelling_of_no_figure_becomes_the_one_canonical_form(given, want):
    assert G.canonical_affected(given) == want
    assert G.canonical_affected(G.canonical_affected(given)) == want


def test_null_and_a_figure_are_left_alone():
    assert G.canonical_affected(None) is None
    fig = {"value": 5, "unit": "homes", "qualifier": "exact", "source_says": "5 homes"}
    assert G.canonical_affected(fig) == fig


def test_the_gate_refuses_the_other_spellings_in_curated_input():
    r = rec(POL)
    c = r["civilian_service_impact"][0]
    assert c["affected"]["value"] == "unknown" and not [p for p in problems(r) if "affected" in p]
    c["affected"] = "unknown"
    refused(r, "never a bare word")
    c["affected"] = {"value": None, "unit": None, "qualifier": None, "source_says": "no figure"}
    refused(r, "affected.value is null")
    c["affected"] = {"value": "unknown", "unit": "unknown", "qualifier": None, "source_says": "no figure"}
    refused(r, "affected.unit 'unknown'")
    c["affected"] = None
    assert not [p for p in problems(r) if "affected" in p]


def test_every_served_affected_is_null_a_figure_or_the_canonical_object():
    doc = _json(SERVED)
    for r in doc["records"]:
        for c in r["civilian_service_impact"]:
            a = c["affected"]
            assert a is None or (isinstance(a, dict) and a.get("value") is not None and a.get("unit") not in G.ABSENCE), \
                r["impact_id"]
            assert G.canonical_affected(a) == a, r["impact_id"]


# --- R11: no figure from a source in a research note -------------------------------------------------

def _log(limitation):
    log = copy.deepcopy(_json(FIXTURE / "research_log.json"))
    fam = copy.deepcopy(log["source_families"][0]) if log.get("source_families") else {
        "lane": "europe", "scope": "impacts", "research_pass": "i22-europe", "family": "Synthetic family",
        "method": "2 searches", "window": "2022 to 2026", "status": "partial", "limitation": ""}
    fam["limitation"] = limitation
    log["source_families"] = [fam]
    return log


@pytest.mark.parametrize("text", [
    "The April move was read but not filed (both benchmarks fell towards $95).",
    "An article on reserve releases (17.5 million barrels) was read but not filed.",
    "A report of a 20% fall was read but not filed.",
    "A lead about 40,000 households was opened.",
])
def test_a_research_note_with_a_figure_from_a_source_is_refused(text):
    assert any("a figure from a source" in p for p in G.log_problems(_log(text)))


def test_a_research_note_may_count_its_own_searches_and_pages():
    assert not [p for p in G.log_problems(_log("3 searches and 2 direct fetches; 4 pages returned 403."))
                if "a figure from a source" in p]


def test_the_served_research_notes_carry_no_figure_from_a_source():
    for name in ("impacts.json", "regional_context.json"):
        doc = _json(SERVED.parent / name)
        for f in doc["research"]["source_families"]:
            for k in ("family", "method", "window", "status", "limitation"):
                assert not G.LOG_FIGURE.search(str(f.get(k) or "")), (name, f.get("family"), k)


def test_the_build_serves_the_canonical_form_whatever_the_curated_spelling():
    r = rec(POL)
    r["civilian_service_impact"][0]["affected"] = {"value": None, "unit": "unknown", "qualifier": None,
                                                   "source_says": "no figure"}
    served = G.serve_record(r, ctx())
    assert served["civilian_service_impact"][0]["affected"] == {"value": "unknown", "unit": None, "qualifier": None,
                                                                "source_says": "no figure"}


def test_the_import_writes_the_canonical_form():
    I = _script("import_impacts")
    r = rec(POL)
    r["civilian_service_impact"][0]["affected"] = "unknown"
    notes = []
    I.normalise(r, notes)
    assert r["civilian_service_impact"][0]["affected"] == {"value": "unknown", "unit": None, "qualifier": None,
                                                           "source_says": None}
    assert any("canonical form" in n for n in notes)
    # null (not applicable) is left for a reviewer or the lead to change, never rewritten here.
    r["civilian_service_impact"][0]["affected"] = None
    I.normalise(r, notes)
    assert r["civilian_service_impact"][0]["affected"] is None
