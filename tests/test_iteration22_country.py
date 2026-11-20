"""Iteration 22, country pages: the overview, the two new tabs, confidence on event cards and the
image export, executed as shipped.

The shipped TypeScript is bundled from web/src with esbuild and run in Node, the way
tests/test_iteration21_testarch.py does it, so the mutation campaign (scripts/mutation_campaign.py,
ITER22_COUNTRY_MUTATIONS) breaks the code a reader's browser runs.

What is pinned here is what must never regress quietly:
- the overview of a country under attack-campaign safeguards never states or implies how many
  records are held, or whether any are;
- a country with no published record says so honestly: no zero, and "no record is not no
  disruption";
- the impact layer is a separate corpus: it never changes the published-record count shown for the
  country, on the page or in an exported image, and its tab says so before it lists anything;
- an abstracted (attack or sabotage) impact record shows no place, on the page or in the export;
- an event with no evidence confidence shows no chip, never a default category;
- the regional-context tab exists only for the members of the manifest's group;
- an IT failure is not a cyber record.

Systems are the served payloads. Impact records are the pipeline's synthetic fixture, built here
through the pipeline's own builder: every one of them is invented.

The browser-level proof (first screen, each tab, a deep link, phones, the keyboard, a real PNG) is
in web/e2e/country22.e2e.ts; the wider unit tests are in web/src/global/countryPage22.test.tsx.
"""
import copy
import json
import re

import pytest

from pipeline import global_impacts as GI
from tests.test_iteration21_testarch import WEB, needs_bundler, needs_payload, run_ts

OVERVIEW = {"ov": "global/countryOverview.ts", "ob": "global/OverviewBlock.tsx", "lc": "global/laneCoverage.ts"}
TABS = {"ct": "global/countryTabs.ts"}
CARD = {"ec": "global/EventCard.tsx", "ev": "global/evidence.ts"}
IMPACT = {"cm": "global/countryImpactModel.ts", "ci": "global/CountryImpacts.tsx", "vocab": "global/impacts/vocab.ts",
          "rf": "global/recordFilters.ts"}
EXPORT = {"ce": "global/countryExport.ts", "cs": "global/countryScale.ts", "cm": "global/countryImpactModel.ts"}

TEXT_JS = """
const text = (html) => html.replace(/<[^>]+>/g, " ").replace(/&amp;/g, "&").replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/\\s+/g, " ").trim();
"""
SEEDED = {"candidates": 4817, "held": 3929, "rejected": 5743, "accepted": 6151}
SECRET = "SENTINELPLACE"
GULF = {"id": "gulf_littoral", "label": "Gulf littoral", "slug": "gulf"}


def _read(rel):
    return json.loads((WEB / rel).read_text(encoding="utf-8"))


def _manifest():
    return _read("global/manifest.json")


def _systems():
    return {s["id"]: _read(f"systems/{s['id']}/system.json") for s in _manifest()["systems"] if s["kind"] == "country"}


def _events(sid):
    return _read(f"systems/{sid}/events.json")["events"]


def _restricted(sys):
    """The Python reading of laneCoverage.isCampaignRestricted: any one signal is enough."""
    passes = (sys.get("research_log") or {}).get("passes") or []
    state = (sys.get("campaign_state") or {}).get("state")
    return (any("under_review" in p for p in passes)
            or any(c.get("policy_applied") for c in (sys.get("publication_policy") or {}).get("campaigns") or [])
            or (state is not None and state != "NO_ACTIVE_CAMPAIGN"))


@pytest.fixture(scope="module")
def impacts():
    """The synthetic fixture as the build serves it."""
    ctx = GI.load_context(link_states=json.loads((GI.FIXTURE_DIR / "link_health.json").read_text(encoding="utf-8"))["link_states"])
    return GI.build_payloads(*GI.load_curated(GI.FIXTURE_DIR), ctx, "2026-11-19")[GI.IMPACTS_OUT]


def _in_system(payload, sid):
    """Every fixture record moved into one system, so a country has a list worth testing."""
    out = copy.deepcopy(payload)
    for r in out["records"] + out["attempts"]:
        r["system_id"] = sid
    return out


# ---------------- the overview ----------------

OVERVIEW_JS = TEXT_JS + """
const render = (sys, impacts, regional) => text(renderToStaticMarkup(React.createElement(ob.CountryOverview,
  { sys, impacts, regional, onTab: () => undefined })));
"""


@needs_bundler
@needs_payload
def test_country_overview_never_states_or_implies_a_held_count(tmp_path_factory):
    """Under the campaign safeguards the overview is the same whatever a research pass logged: no
    count of candidates or held records, and not even whether any exist."""
    systems = {sid: s for sid, s in _systems().items() if _restricted(s)}
    assert systems, "no served system is under the campaign safeguards"
    variants = {}
    for sid, s in systems.items():
        variants[sid] = [s]
        for under_review in (True, False, None):
            v = copy.deepcopy(s)
            for p in v["research_log"]["passes"]:
                p["outcome"] = dict(SEEDED)
                p.pop("under_review", None)
                if under_review is not None:
                    p["under_review"] = under_review
            if not v["research_log"]["passes"]:
                v["research_log"]["passes"] = [{"date": "2026-11-01", "by": "x", "kind": "systematic", "outcome": dict(SEEDED),
                                               **({} if under_review is None else {"under_review": under_review})}]
            variants[sid].append(v)
    out = run_ts(tmp_path_factory, OVERVIEW, OVERVIEW_JS + """
      const res = {};
      for (const [sid, list] of Object.entries(input.variants)) {
        res[sid] = list.map((s) => ({ restricted: lc.isCampaignRestricted(s), text: render(s, { state: "not_loaded" }, input.gulf) }));
      }
      return res;""", {"variants": variants, "gulf": GULF})
    for sid, rows in out.items():
        texts = {r["text"] for r in rows}
        assert len(texts) == 1, f"{sid}: the overview changes with what the research log holds"
        t = rows[0]["text"]
        assert all(r["restricted"] for r in rows), sid
        assert not re.search(r"4817|3929|5743|6151", t), sid
        assert "whether, or how many, records are in review" in t, sid
        assert not re.search(r"\d+\s+(candidate|held|records? (are |is )?(held|in review|under review))", t, re.I), sid
        assert "remain under review" not in t, sid


@needs_bundler
@needs_payload
def test_country_overview_of_an_empty_country_says_why_and_prints_no_zero(tmp_path_factory):
    systems = {sid: s for sid, s in _systems().items() if s["event_summary"]["recorded_events"] == 0}
    assert systems, "no served system has an empty record"
    out = run_ts(tmp_path_factory, OVERVIEW, OVERVIEW_JS + """
      return Object.fromEntries(Object.entries(input.systems).map(([sid, s]) => [sid, {
        text: render(s, { state: "not_loaded" }, null), model: ov.countryOverview(s, { state: "not_loaded" }, null) }]));""",
                 {"systems": systems})
    for sid, r in out.items():
        t = r["text"]
        assert "What this page can tell you" in t, sid
        assert r["model"]["published"].startswith("No energy-disruption record is published for "), sid
        assert "the inclusion rule is strict" in r["model"]["publishedNote"], sid
        assert "No record is not no disruption." in t, sid
        assert not re.search(r"\d", t), f"{sid}: a number on a page with no record: {t}"
        assert not re.search(r"no disruptions|nothing happened", t, re.I), sid
        assert ("attack-campaign safeguards apply" in t) == _restricted(systems[sid]), sid
        # The three parts, in order.
        assert t.index("Published here") < t.index("Also on this page") < t.index("Not published, and why"), sid


@needs_bundler
@needs_payload
def test_country_impact_records_never_change_the_published_record_count(tmp_path_factory):
    """The impact corpus is separate: whatever it holds, the sentence that states the country's
    published records is unchanged, and its own count stays beside the words that say so."""
    systems = _systems()
    out = run_ts(tmp_path_factory, OVERVIEW, OVERVIEW_JS + """
      return Object.fromEntries(Object.entries(input.systems).map(([sid, s]) => {
        const without = ov.countryOverview(s, { state: "not_loaded" }, null);
        const withThem = ov.countryOverview(s, { state: "ready", records: 987, attempts: 3, latestResearch: null }, null);
        return [sid, { without, withThem, text: render(s, { state: "ready", records: 987, attempts: 3, latestResearch: null }, null) }];
      }));""", {"systems": systems})
    for sid, r in out.items():
        n = systems[sid]["event_summary"]["recorded_events"]
        assert r["withThem"]["published"] == r["without"]["published"], sid
        assert r["withThem"]["publishedNote"] == r["without"]["publishedNote"], sid
        assert "987" not in r["withThem"]["published"], sid
        if n > 0:
            assert r["withThem"]["published"].startswith(f"{n} reviewed energy-disruption record"), sid
        line = next(k["line"] for k in r["withThem"]["known"] if k["tab"] == "impacts")
        assert line == "987 reviewed impact records and 3 documented attempts, in a separate, non-scored corpus.", sid
        if n > 0:
            assert str(n + 987) not in r["text"] and str(n + 990) not in r["text"], f"{sid}: the two corpora were added up"
        else:
            # The page with no record still says so: the impact corpus does not fill the gap.
            assert r["withThem"]["published"].startswith("No energy-disruption record is published for "), sid


# ---------------- tabs ----------------

@needs_bundler
@needs_payload
def test_country_regional_tab_exists_only_for_members_of_the_manifest_group(tmp_path_factory):
    m = _manifest()
    ids = [s["id"] for s in m["systems"] if s["kind"] == "country"]
    out = run_ts(tmp_path_factory, TABS, """
      const res = {};
      for (const id of input.ids) {
        const g = ct.regionalGroupFor(input.manifest, id);
        res[id] = { group: g ? g.id : null, tabs: ct.tabsFor(g), shown: ct.resolveTab("regional", ct.tabsFor(g)) };
      }
      // A group the system belongs to that carries no regional context gives no regional tab.
      const plain = ct.regionalGroupFor({ groups: { x: { label: "X", kind: "geographic", note: "", slug: "x", context: "global/x.json", members: [input.ids[0]] } } }, input.ids[0]);
      return { res, plain, noGroups: ct.regionalGroupFor({}, input.ids[0]), href: ct.tabHref("ir", "impacts"),
               kept: ct.withTab("sys=us&r=US-TX&f.cause=technical,unknown", "impacts"), dropped: ct.withTab("sys=us&tab=impacts", "events"),
               bad: ct.tabFromSearch("?sys=us&tab=__proto__") };""", {"manifest": m, "ids": ids})
    group = next(g for g in m["groups"].values() if g.get("slug") == "gulf")
    for sid, r in out["res"].items():
        member = sid in group["members"]
        assert ("regional" in r["tabs"]) == member, sid
        assert r["shown"] == ("regional" if member else "events"), sid
        assert r["tabs"][0] == "events" and r["tabs"][1] == "impacts", sid
    assert any("regional" in r["tabs"] for r in out["res"].values())
    assert any("regional" not in r["tabs"] for r in out["res"].values())
    assert out["noGroups"] is None and out["plain"] is None
    assert out["href"] == "?sys=ir&tab=impacts"
    assert out["kept"] == "sys=us&r=US-TX&f.cause=technical,unknown&tab=impacts"
    assert out["dropped"] == "sys=us"
    assert out["bad"] is None


# ---------------- evidence confidence on an event card ----------------

CONF = {"category": "HIGH", "label": "High", "score": 84, "disputed": False,
        "components": {"directness": {"tier": "direct", "points": 40}, "origins": {"count": 2, "points": 16, "basis": "publishers"},
                       "effect": {"specificity": "described", "points": 8}, "opened": {"points": 10},
                       "contemporaneous": {"points": 10}},
        "reasons": ["Direct authoritative statement", "2 publishers cited; their origins are not yet reviewed"]}

CARD_JS = TEXT_JS + """
const bundle = { system: input.system, events: input.events, episodes: [], regions: { type: "FeatureCollection", features: [] } };
const card = (e) => text(renderToStaticMarkup(React.createElement("ul", null, React.createElement(ec.EventCard, { e, bundle }))));
const inspector = (e) => text(renderToStaticMarkup(React.createElement(ec.EvidenceInspector, { id: "x", e, bundle, onClose: () => undefined })));
"""


@needs_bundler
@needs_payload
def test_country_confidence_chip_is_absent_when_the_field_is_absent(tmp_path_factory):
    """A payload without evidence_confidence renders as before. Absent is never a category, and a
    half-formed value is treated as absent."""
    sid = next(s for s, v in _systems().items() if v["event_summary"]["recorded_events"] > 0 and not _restricted(v))
    system = _systems()[sid]
    base = dict(_events(sid)[0])
    base.pop("evidence_confidence", None)
    variants = {
        "absent": base,
        "null": {**base, "evidence_confidence": None},
        "no_components": {**base, "evidence_confidence": {"category": "HIGH", "label": "High"}},
        "no_category": {**base, "evidence_confidence": {**CONF, "category": ""}},
        "served": {**base, "evidence_confidence": CONF},
    }
    out = run_ts(tmp_path_factory, CARD, CARD_JS + """
      return Object.fromEntries(Object.entries(input.variants).map(([k, e]) => [k, { card: card(e), inspector: inspector(e), value: ev.eventConfidence(e) }]));""",
                 {"system": system, "events": [base], "variants": variants})
    for k in ("absent", "null", "no_components", "no_category"):
        assert out[k]["value"] is None, k
        assert "Evidence confidence" not in out[k]["card"], f"{k}: a chip was drawn for a record with no confidence"
        assert "How strong the evidence is" not in out[k]["inspector"], k
        assert "not computed" not in out[k]["card"], k
    assert "Evidence confidence: High" in out["served"]["card"]
    insp = out["served"]["inspector"]
    assert "How strong the evidence is" in insp
    # The served reasons, as served: nothing about origins is composed on the page.
    for reason in CONF["reasons"]:
        assert reason in insp
    # The sentence about what confidence is not is on screen before the method file is.
    assert "It is not a probability, not a measure of severity" in insp


NOT_ASSESSED_REASON = "Cited through a discovery aid only; a primary source is not yet attached."
SUMMARY_JS = """
const cfilters = cf.countryFilters(input.system, input.events, ev.confidenceOptions(input.system, input.events));
const conf = cfilters.defs.find((d) => d.id === "conf");
const pick = (v) => rf.applyFilters(input.events, cfilters.defs, rf.toggleChoice(rf.NO_FILTERS, "conf", v), "2026-11-19").map((e) => e.event_id);
"""


@needs_bundler
@needs_payload
def test_country_a_record_that_was_not_assessed_is_its_own_state_never_a_category(tmp_path_factory):
    """`category: null` with a reason is "Not assessed": on the card, in the inspector, and as its
    own bucket in the filter and the per-country summary. Never "Preliminary", never absent."""
    sid = next(s for s, v in _systems().items() if v["event_summary"]["recorded_events"] >= 5 and not _restricted(v))
    system = dict(_systems()[sid])
    system["evidence_confidence_summary"] = {"by_category": {"HIGH": 0, "MODERATE": 0, "LIMITED": 0, "PRELIMINARY": 0, "DISPUTED": 0}}
    base = [{k: v for k, v in e.items() if k != "evidence_confidence"} for e in _events(sid)[:5]]
    events = [
        {**base[0], "evidence_confidence": CONF},
        {**base[1], "evidence_confidence": {**CONF, "category": "PRELIMINARY", "label": "Preliminary"}},
        {**base[2], "evidence_confidence": {"category": None, "reason": NOT_ASSESSED_REASON}},
        {**base[3], "evidence_confidence": {"category": None, "reason": NOT_ASSESSED_REASON}},
        base[4],
    ]
    mods = {**CARD, "cf": "global/countryFilters.ts", "rf": "global/recordFilters.ts", "cs": "global/ConfidenceSummary.tsx"}
    out = run_ts(tmp_path_factory, mods, CARD_JS + SUMMARY_JS + """
      const na = input.events[2];
      return { card: card(na), inspector: inspector(na), noReason: card({ ...na, evidence_confidence: { category: null } }),
               options: conf.options, notAssessed: pick("NOT_ASSESSED"), preliminary: pick("PRELIMINARY"),
               counts: ev.confidenceCounts(input.system, input.events),
               summary: text(renderToStaticMarkup(React.createElement(cs.ConfidenceSummary, { bundle }))),
               empty: renderToStaticMarkup(React.createElement(cs.ConfidenceSummary, { bundle: { ...bundle, events: [input.events[4]] } })) };""",
                 {"system": system, "events": events})
    named = re.compile(r"Evidence confidence: (Preliminary|Limited|Moderate|High|Disputed)")
    for t in (out["card"], out["inspector"], out["noReason"]):
        assert "Evidence confidence: Not assessed" in t
        assert not named.search(t), "a record that was not assessed was shown under a category"
        assert not re.search(r"/\s?100|\d\s?%", t.split("What this report does not establish")[0].split("How strong the evidence is")[-1])
    assert NOT_ASSESSED_REASON in out["card"] and NOT_ASSESSED_REASON in out["inspector"]
    assert "Not assessed is not a low category" in out["inspector"]
    assert "It is not a probability, not a measure of severity" in out["inspector"]
    # Its own choice, last, selecting exactly the records that were not assessed.
    assert out["options"] == [{"value": "HIGH", "label": "High"}, {"value": "PRELIMINARY", "label": "Preliminary"},
                              {"value": "NOT_ASSESSED", "label": "Not assessed"}]
    assert out["notAssessed"] == [events[2]["event_id"], events[3]["event_id"]]
    assert out["preliminary"] == [events[1]["event_id"]]
    # Its own line in the summary, which stays inside the country with its sentence.
    assert out["counts"] == [{"value": "HIGH", "label": "High", "n": 1}, {"value": "PRELIMINARY", "label": "Preliminary", "n": 1},
                             {"value": "NOT_ASSESSED", "label": "Not assessed", "n": 2}]
    s = out["summary"]
    assert "High: 1" in s and "Preliminary: 1" in s and "Not assessed: 2" in s
    assert "describes the citations these records carry" in s and "not comparable across countries" in s
    assert not re.search(r"/\s?100|\d\s?%", s)
    assert out["empty"] == "", "a summary was drawn for records that carry no confidence"


@needs_bundler
@needs_payload
def test_country_campaign_covered_records_gain_the_chip_and_nothing_else(tmp_path_factory):
    """A campaign-covered record shows the chip like any other. Its card still shows no headline and
    no later status."""
    covered = [(sid, e) for sid in _systems() for e in _events(sid) if e.get("publication")]
    if not covered:
        pytest.skip("no campaign-covered record is served")
    sid, e = covered[0]
    out = run_ts(tmp_path_factory, CARD, CARD_JS + """
      const e = input.events[0];
      return { without: card(e), with: card({ ...e, evidence_confidence: input.conf }) };""",
                 {"system": _systems()[sid], "events": [{k: v for k, v in e.items() if k != "evidence_confidence"}], "conf": CONF})
    assert "Evidence confidence: High" in out["with"]
    # Only the chip and its disclosure are added.
    assert out["with"].replace("Evidence confidence: High Why? Evidence confidence: High", "").split() == out["without"].split()


# ---------------- the impact tab ----------------

IMPACT_JS = TEXT_JS + """
vocab.registerVocabularies(input.payload.vocabularies);
const render = (records, attempts) => text(renderToStaticMarkup(React.createElement(ci.CountryImpacts,
  { sys: input.system, impacts: { state: "ready", payload: input.payload, records, attempts }, today: "2026-11-19" })));
"""


@needs_bundler
@needs_payload
def test_country_an_abstracted_impact_record_renders_no_place(tmp_path_factory, impacts):
    """An attack or sabotage record is its country and nothing finer, on the country page and in
    the exported image, even if a payload carried a region or a headline."""
    payload = _in_system(impacts, "ir")
    kinetic = [r for r in payload["records"] if r["publication_policy"] == "country_abstracted"]
    assert kinetic, "the fixture has no abstracted record"
    for r in kinetic:
        r["admin1"] = {"code": "XX-01", "name": SECRET}
        for s in r["sources"]:
            s["title_original"] = s["title_en"] = SECRET
    # The cause alone abstracts too: a kinetic record whose policy field was lost.
    lost = copy.deepcopy(kinetic[0])
    lost["impact_id"] += "-b"
    lost["publication_policy"] = "standard"
    payload["records"].append(lost)
    out = run_ts(tmp_path_factory, IMPACT, IMPACT_JS + """
      const { records, attempts } = cm.countryImpacts(input.payload, "ir");
      const abstracted = records.filter((r) => r.admin1 && r.admin1.name === input.secret);
      return { n: abstracted.length, page: render(records, attempts), rows: abstracted.map((r) => cm.impactExportRow(input.payload, r)),
               summary: cm.impactExportSummary("Iran", abstracted, [], input.payload) };""",
                 {"payload": payload, "system": _systems()["ir"], "secret": SECRET})
    assert out["n"] == len(kinetic) + 1
    assert SECRET not in out["page"], "an abstracted record's region reached the country page"
    assert "place withheld" in out["page"]
    for row in out["rows"]:
        assert SECRET not in row
        assert row.endswith("country level, place withheld")
    assert SECRET not in json.dumps(out["summary"])


@needs_bundler
@needs_payload
def test_country_impact_tab_says_it_is_a_separate_corpus_and_never_counts_an_attempt(tmp_path_factory, impacts):
    payload = _in_system(impacts, "ir")
    out = run_ts(tmp_path_factory, IMPACT, IMPACT_JS + """
      const { records, attempts } = cm.countryImpacts(input.payload, "ir");
      const none = cm.countryImpacts(input.payload, "zz");
      const states = ["not_loaded", "loading", "failed"].map((state) => text(renderToStaticMarkup(React.createElement(ci.CountryImpacts,
        { sys: input.system, impacts: { state }, today: "2026-11-19" }))));
      return { records: records.map((r) => r.record_kind), attempts: attempts.map((r) => r.record_kind), page: render(records, attempts),
               empty: render([], []), none, states, presence: ci.impactPresence({ state: "ready", payload: input.payload, records, attempts }) };""",
                 {"payload": payload, "system": _systems()["ir"]})
    n, a = len(payload["records"]), len(payload["attempts"])
    assert a > 0, "the fixture has no attempt"
    assert out["records"] == ["disruption"] * n
    assert len(out["attempts"]) == a and "disruption" not in out["attempts"]
    assert out["presence"]["records"] == n and out["presence"]["attempts"] == a
    assert f"Showing {n} of {n} reviewed impact records" in out["page"]
    for t in [out["page"], out["empty"], *out["states"]]:
        assert "separate, non-scored corpus" in t and "enter no count or index" in t
    assert "No reviewed impact record is published for Iran yet. That describes this corpus, not Iran." in out["empty"]
    assert "The impact research last ran on" in out["empty"]
    assert not re.search(r"\b0 (reviewed|impact|records)", out["empty"])
    assert out["none"] == {"records": [], "attempts": []}


@needs_bundler
@needs_payload
def test_country_impact_filters_keep_an_it_failure_out_of_cyber(tmp_path_factory, impacts):
    """"Cyber" is a malicious cyber cause only. A digitally triggered failure without malice is a
    technical record with its own label and its own filter."""
    payload = _in_system(impacts, "ir")
    victim = next(r for r in payload["records"] if r["cause_family"] == "industrial_technical")
    victim["cyber_mechanism"] = "it_outage_affecting_operations"
    out = run_ts(tmp_path_factory, IMPACT, IMPACT_JS + """
      const { records } = cm.countryImpacts(input.payload, "ir");
      const defs = cm.impactFilters(input.payload, records);
      const pick = (id, value) => rf.applyFilters(records, defs, rf.toggleChoice(rf.NO_FILTERS, id, value), "2026-11-19").map((r) => r.impact_id);
      return { ids: defs.map((d) => d.id), cyber: pick("cause", "cyber"), it: pick("it", "it_failure"),
               counts: cm.causeCounts(input.payload, records), row: cm.impactExportRow(input.payload, records.find((r) => r.impact_id === input.victim)),
               summary: cm.impactExportSummary("Iran", records, [], input.payload).lines };""",
                 {"payload": payload, "system": _systems()["ir"], "victim": victim["impact_id"]})
    assert out["ids"] == ["cause", "it", "sector", "tech", "attr", "ai", "conf"]
    cyber = {r["impact_id"] for r in payload["records"] if r["cause_family"] == "cyber"}
    assert set(out["cyber"]) == cyber and victim["impact_id"] not in out["cyber"]
    assert out["it"] == [victim["impact_id"]]
    assert "(it failure)" in out["row"]
    assert sum(c["n"] for c in out["counts"]) == len(payload["records"])
    assert next(c["n"] for c in out["counts"] if c["id"] == "cyber") == len(cyber)
    order = [e["id"] for e in payload["vocabularies"]["cause_families"]]
    assert [c["id"] for c in out["counts"]] == [i for i in order if any(c["id"] == i for c in out["counts"])]
    assert any("1 is an IT failure" in line and "not a cyberattack" in line for line in out["summary"])


# ---------------- the exported image ----------------

EXPORT_JS = """
const scale = cs.scaleFor([0, 1, 2, 3]);
const draw = (sys, summary) => {
  globalThis.__drawn = [];
  ce.composeCountryFrame({ width: 1600, height: 900 }, sys, scale, null, summary);
  return globalThis.__drawn.map((d) => d.t);
};
"""


@needs_bundler
@needs_payload
def test_country_image_carries_the_research_preview_caveat_where_the_page_shows_it(tmp_path_factory):
    systems = _systems()
    out = run_ts(tmp_path_factory, EXPORT, EXPORT_JS + """
      return Object.fromEntries(Object.entries(input.systems).map(([sid, s]) => [sid, draw(s, null)]));""", {"systems": systems})
    assert any(s.get("maturity") == "research_preview" for s in systems.values())
    for sid, drawn in out.items():
        preview = systems[sid].get("maturity") == "research_preview"
        lines = [t for t in drawn if t.startswith("A research preview is ")]
        assert bool(lines) == preview, sid
        if preview:
            assert "not evidence that no disruption occurred" in lines[0], sid
        # The existing caveats are still drawn.
        assert any("not comparable across countries" in t for t in drawn), sid
        assert any(t.startswith("Active-campaign safeguards apply") for t in drawn) == (
            (systems[sid].get("campaign_state") or {}).get("state") not in (None, "NO_ACTIVE_CAMPAIGN")), sid


@needs_bundler
@needs_payload
def test_country_image_from_the_impact_tab_draws_the_summary_and_leaves_the_published_count_alone(tmp_path_factory, impacts):
    payload = _in_system(impacts, "ir")
    for r in payload["records"]:
        if r["publication_policy"] == "country_abstracted":
            r["admin1"] = {"code": "XX-01", "name": SECRET}
    systems = _systems()
    out = run_ts(tmp_path_factory, EXPORT, EXPORT_JS + """
      const { records, attempts } = cm.countryImpacts(input.payload, "ir");
      const summary = cm.impactExportSummary("Iran", records, attempts, input.payload, "STATEMENT FROM THE METHOD.");
      return Object.fromEntries(Object.entries(input.systems).map(([sid, s]) => [sid, { plain: draw(s, null), withSummary: draw(s, summary) }]));""",
                 {"systems": systems, "payload": payload})
    n = len(payload["records"])
    for sid, r in out.items():
        added = " ".join(t for t in r["withSummary"] if t not in r["plain"])
        # Every line the page's own image drew is still drawn, unchanged: the count line among them.
        assert [t for t in r["withSummary"] if t in r["plain"]] == r["plain"], sid
        count_line = next(t for t in r["plain"] if t.startswith("No index."))
        assert count_line in r["withSummary"], sid
        assert "separate, non-scored" in added and "enter no count or index" in added, sid
        assert f"{n} reviewed impact records for Iran, by cause family" in added.replace("  ", " "), sid
        assert "STATEMENT FROM THE METHOD." in added, sid
        assert "not comparable across" in added, sid
        assert SECRET not in " ".join(r["withSummary"]), sid
        assert "place withheld" in added, sid
