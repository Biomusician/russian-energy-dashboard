"""Iteration 22: the Gulf overview's evidence sections and the impact briefs, executed.

The browser tier (web/e2e/gulfimpacts.e2e.ts) and vitest (web/src/global/impacts/brief/) prove these
rules where a reader meets them. The mutation campaign has neither, so the rules that matter most
are pinned here by RUNNING the shipped TypeScript (the esbuild harness of
tests/test_iteration21_testarch.py): the sections render through react-dom/server and the briefs
draw into a canvas that records its text, so a test reads what a page or a forwarded image says.

What is held:
- no Gulf section and no brief carries a per-country count of impact records, and nothing is
  ordered by a figure;
- the regional context is dated statements with their sources and no status flag, and narrowing it
  never turns an older statement into the latest;
- the briefs' caveat lines are drawn, each one;
- a brief is handed a cause, an IT-failure flag, services and a confidence category, so what a
  record withholds cannot be drawn;
- evidence confidence is a category in words: a record that was not assessed is its own bucket,
  never the lowest one, no score is drawn, and a provisional method is said to be provisional;
- cause labels come from the served taxonomy; an IT failure is never counted as cyber;
- only the context section speaks of the strait.

The records are made here, in the served shape (web/src/global/impacts/types.ts), with the
vocabularies read from methodology/impact_taxonomy.json and the members from the built gulf.json.
Every record is invented.
"""
import copy
import json
import re
from pathlib import Path

import pytest

from tests.test_iteration21_testarch import needs_bundler, run_ts

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web" / "public" / "data"
needs_gulf = pytest.mark.skipif(not (WEB / "global" / "gulf.json").exists(), reason="no built payload")

MODS = {
    "gs": "global/groupSections.ts",
    "gi": "global/groupImpacts.ts",
    "sec": "global/GroupImpactSections.tsx",
    "bi": "global/impacts/brief/briefInputs.ts",
    "ib": "global/impacts/brief/impactBrief.ts",
    "db": "global/impacts/brief/drawImpactBrief.ts",
    "vocab": "global/impacts/vocab.ts",
}

STRAIT = re.compile(r"hormuz|strait|tanker|choke ?point|shipping|bypass", re.I)
NEVER = re.compile(r"tanker|vessel|\bships?\b|bypass|choke ?point|\broutes?\b|\bdepend\w*", re.I)
STATUS = re.compile(r"\b(is|are|remains?|now|currently|status:)\s+(open|closed|shut|blocked)\b", re.I)
SECRETS = ("Secretville", "Hidden Works", "example.test/hidden", "Example Group", "XX-99")
IT_OUTAGE = "it_outage_affecting_operations"


def _gulf():
    return json.loads((WEB / "global" / "gulf.json").read_text(encoding="utf-8"))


def _taxonomy():
    return json.loads((ROOT / "methodology" / "impact_taxonomy.json").read_text(encoding="utf-8"))


def _vocabularies():
    t = _taxonomy()
    v = {k: t[k] for k in ("cause_families", "sectors", "cyber_mechanisms", "domains", "source_roles", "media", "claims",
                           "attribution_statuses", "actor_types", "attribution_bases", "ai_statuses", "record_kinds",
                           "absence_words", "effect_specificity", "geographic_scopes", "publication_policies", "link_states",
                           "affected_qualifiers", "context_types") if k in t}
    # A cause family the taxonomy is about to gain: the page and the briefs must label it from data.
    if not any(c["id"] == "authority_order" for c in v["cause_families"]):
        v["cause_families"] = v["cause_families"] + [{"id": "authority_order", "label": "Ordered by an authority", "malicious": False,
                                                      "definition": "A service restricted by order of an authority."}]
    v.setdefault("digital_categories", [{"id": "cyber", "label": "Cyber", "definition": "A cyberattack."},
                                        {"id": "it_failure", "label": "IT failure", "definition": "Digitally triggered without malice."}])
    return v


def _confidence(category="HIGH", label="High"):
    return {"category": category, "label": label, "score": 84, "disputed": False,
            "components": {"directness": {"tier": "direct", "points": 40}, "origins": {"count": 2, "points": 16, "basis": "reviewed"},
                           "effect": {"specificity": "described", "points": 8}, "opened": {"points": 10}, "contemporaneous": {"points": 10}},
            "reasons": ["Direct authoritative statement"]}


def _record(member, n, **over):
    r = {
        "impact_id": f"imp-2026-0{n}-01-{member['a3'].lower()}-electricity-synthetic-{n}", "record_kind": "disruption",
        "date": f"2026-0{n}-01", "date_precision": "day", "date_end": None,
        "country_a3": member["a3"], "country_name": member["name"], "system_id": member["system_id"],
        "admin1": None, "geographic_precision": "country", "domain": "energy", "sector": "electricity", "technology": None,
        "cause_family": "industrial_technical", "contributing_factors": [], "cyber_mechanism": None,
        "summary": "SYNTHETIC. A fault interrupted supply.", "effect": "SYNTHETIC. Supply was interrupted.", "effect_specificity": "described",
        "inclusion_basis": 2,
        "civilian_service_impact": [{"service": "electricity", "geographic_scope": "national",
                                     "affected": {"value": 120000, "unit": "customers", "qualifier": "about", "source_says": "about 120,000 customers"},
                                     "duration_text": "about four hours", "source_refs": ["s1"]}],
        "attribution": {"status": "NOT_APPLICABLE", "actor": None, "actor_type": None, "basis": [], "as_of": None, "statement": None,
                        "competing": [], "source_refs": [], "confidence": None},
        "ai_involvement": {"status": "NONE_REPORTED", "relation": None, "role": None, "as_of": None, "statement": None, "source_refs": []},
        "dispute": None,
        "sources": [{"ref": "s1", "url": "https://operator.example/synthetic", "publisher": "Example Operator", "date": f"2026-0{n}-01",
                     "language": "en", "source_role": "operator", "medium": "web", "social": None, "supports": ["occurrence", "effect"],
                     "opened": True, "derived_claim": "Synthetic.", "link_check": "unchecked"}],
        "episode_id": None, "episode_basis": None, "publication_policy": "standard", "first_published": "2026-11-19",
        "evidence_confidence": _confidence(), "origin_count": 2,
    }
    r.update(over)
    return r


def _payload(members):
    """Seven invented records on the group's members, newest first: an IT failure, three cyber
    records (two on one member), an attack published for its country only whose record carries
    everything a brief must not repeat, a record the build did not assess, and one ordered by an
    authority."""
    m = members
    cyber = {"cause_family": "cyber", "cyber_mechanism": "ransomware", "domain": "civilian_service",
             "attribution": {"status": "ATTRIBUTED", "actor": "Example Group", "actor_type": "criminal", "basis": ["government"],
                             "as_of": "2026-07-01", "statement": "A government attributed this to Example Group.", "competing": [],
                             "source_refs": ["s1"], "confidence": "MODERATE"}}
    water = [{"service": "water", "geographic_scope": "regional", "affected": "unknown", "duration_text": "two days", "source_refs": ["s1"]}]
    telecom = [{"service": "telecom", "geographic_scope": "national",
                "affected": {"value": 2000000, "unit": "subscribers", "qualifier": "about", "source_says": "about 2 million subscribers"},
                "duration_text": "most of a day", "source_refs": ["s1"]}]
    records = [
        _record(m[0], 7, cause_family="industrial_technical", cyber_mechanism=IT_OUTAGE, sector="transport", domain="civilian_service",
                civilian_service_impact=[{"service": "transport", "geographic_scope": "regional", "affected": None,
                                          "duration_text": "six hours", "source_refs": ["s1"]}]),
        _record(m[1], 6, sector="water", civilian_service_impact=water, **cyber),
        _record(m[1], 5, sector="telecom", civilian_service_impact=telecom, **cyber),
        _record(m[2], 4, cause_family="kinetic", publication_policy="country_abstracted",
                admin1={"code": "XX-99", "name": "Secretville"}, summary="SYNTHETIC. An attack was reported in the country.",
                sources=[{"ref": "s1", "url": "https://example.test/hidden-works-terminal", "publisher": "Example Wire", "date": "2026-04-01",
                          "language": "en", "source_role": "wire", "medium": "web", "social": None, "supports": ["occurrence", "effect"],
                          "opened": True, "title_en": "Hidden Works terminal hit", "title_original": "Hidden Works terminal hit",
                          "derived_claim": "Synthetic.", "link_check": "unchecked"}]),
        _record(m[3], 3, sector="telecom", civilian_service_impact=telecom, **cyber),
        _record(m[4], 2, cause_family="natural_hazard",
                evidence_confidence={"category": None, "label": None, "score": None, "reason": "No primary source is attached yet."}),
        _record(m[5], 1, cause_family="authority_order", evidence_confidence=_confidence("PRELIMINARY", "Preliminary")),
    ]
    return {
        "schema_version": 1, "as_of": "2026-11-19", "scope_statement": "Reviewed, publicly reported disruptions.",
        "caveats": ["This is not a census."], "empty_reason": None, "attempts_label": "ATTEMPT — NO REPORTED SERVICE DISRUPTION",
        "vocabularies": _vocabularies(),
        "research": {"window": {"start": "2022-01-01", "end": "present"}, "status": "expanding corpus",
                     "source_families": [{"family": "Synthetic operator statements", "method": "Written by hand.", "window": "2022 to 2026",
                                          "status": "synthetic", "limitation": "Every record here is invented."}],
                     "latest_research_date": "2026-11-19", "limitations": ["Official sites in two countries could not be read."]},
        "countries": sorted(({"a3": x["a3"], "name": x["name"], "system_id": x["system_id"]} for x in m[:6]), key=lambda c: c["name"]),
        "records": records, "attempts": [],
    }


def _entry(eid, date, kind, claim, publisher, latest, metric=None):
    return {"id": eid, "date": date, "as_of": date, "context_type": kind, "claim": claim, "metric": metric,
            "sources": [{"ref": "s1", "url": f"https://agency.example/{eid}", "publisher": publisher, "date": date, "language": "en",
                         "source_role": "government", "medium": "report", "social": None, "supports": ["occurrence"], "opened": True,
                         "link_check": "unchecked"}],
            "first_published": "2026-11-19", "age_days": 30, "is_latest_of_type": latest}


def _context():
    v = _vocabularies()
    return {
        "schema_version": 1, "as_of": "2026-11-19", "context_id": "gulf_hormuz", "label": "The Gulf and the Strait of Hormuz",
        "statement": "Dated, sourced statements about the Gulf and the Strait of Hormuz, in aggregate.",
        "not_built": "There is no open or closed flag and no current status: only what a named source said, and when.",
        "latest_note": "The newest statement of its type, as of its date.", "empty_reason": None,
        "context_types": v["context_types"], "vocabularies": {k: v[k] for k in ("source_roles", "media", "link_states", "affected_qualifiers")},
        "research": {"source_families": [{"family": "Synthetic agency statements", "method": "Written by hand.", "status": "synthetic"}],
                     "latest_research_date": "2026-11-19"},
        "entries": [
            _entry("ctx-2026-09-20-a", "2026-09-20", "shipping_status", "SYNTHETIC. Transit traffic through the Strait of Hormuz remained below its usual level.", "Example Maritime Agency", True),
            _entry("ctx-2026-04-15-b", "2026-04-15", "reserve_action", "SYNTHETIC. Members agreed a coordinated release from emergency oil stocks.", "Example Energy Agency", True,
                   {"value": 60, "unit": "million barrels", "basis": "total release announced"}),
            _entry("ctx-2026-03-05-c", "2026-03-05", "shipping_status", "SYNTHETIC. Transit traffic was reported lower than a month earlier.", "Example Statistics Office", False),
        ],
    }


def _method(status=None):
    m = {"version": "2.0", "statement": "Evidence confidence describes the quality of the public evidence for this record. It is not a probability, not a measure of severity.",
         "questions": [], "components": [], "overrides": [], "properties": [],
         "categories": [{"id": "HIGH", "min": 78, "label": "High", "meaning": "Corroborated."},
                        {"id": "MODERATE", "min": 55, "label": "Moderate", "meaning": "One origin."},
                        {"id": "LIMITED", "min": 35, "label": "Limited", "meaning": "Thin."},
                        {"id": "PRELIMINARY", "min": 0, "label": "Preliminary", "meaning": "Unverified."},
                        {"id": "DISPUTED", "label": "Disputed", "meaning": "Sources disagree."}],
         "attribution": {"labels": {}, "meanings": {}}, "labels": {}}
    if status:
        m["status"] = status
    return m


def _input(**over):
    g = _gulf()
    members = g["systems"]
    base = {"gulf": g, "metric": next(iter(g["metrics"])), "members": [s["system_id"] for s in members],
            "payload": _payload(members), "context": _context(), "method": _method()}
    base.update(over)
    return base


# Draw the Gulf brief exactly as the page does: served payloads -> gulfBriefInput -> the canvas.
DRAW_GULF_JS = """
const drawGulf = (payload, context, method) => {
  globalThis.__drawn.length = 0;
  db.drawGulfImpactBrief(bi.gulfBriefInput({ ctx: input.gulf, metricId: input.metric, members: input.members,
    payload, regional: context, method, buildDate: "2026-11-19T06:00:00Z" }));
  return globalThis.__drawn.map((d) => d.t);
};
"""

RENDER_JS = """
// React separates adjacent text with an empty comment: removed first, so a sentence reads as written.
const text = (html) => html.replace(/<!-- -->/g, "").replace(/<[^>]+>/g, " ").replace(/&amp;/g, "&").replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/\\s+/g, " ");
vocab.registerVocabularies(input.payload.vocabularies);
vocab.registerVocabularies({ ...input.context.vocabularies, context_types: input.context.context_types });
const el = (C, props) => renderToStaticMarkup(React.createElement(C, props));
const ready = (data) => ({ state: "ready", data });
"""


def _joined(lines):
    return " ".join(lines)


# ---------------- the briefs' caveats ----------------

@needs_bundler
@needs_gulf
def test_iter22_gulf_brief_caveat_lines_are_each_drawn(tmp_path_factory):
    out = run_ts(tmp_path_factory, MODS, DRAW_GULF_JS + """
      return { full: drawGulf(input.payload, input.context, input.method), bare: drawGulf(null, null, null) };
    """, _input())
    for name in ("full", "bare"):
        lines = out[name]
        aggregate = [l for l in lines if "aggregate regional context only" in l.lower()]
        assert len(aggregate) == 1, (name, "the aggregate-context caveat is not drawn")
        for words in ("no facilities", "no routes", "no vessels"):
            assert words in aggregate[0], (name, words)
        assert any("published records in this corpus" in l and "not comparable across countries" in l for l in lines), name
        assert any(re.search(r"later status of attacked facilities is not published", l, re.I) for l in lines), name
        assert "not a probability" in _joined(lines), name
        # The caveat band is the last thing drawn.
        assert "aggregate regional context only" in _joined(lines[-4:]).lower(), name
    assert "Built 19 Nov 2026" in _joined(out["full"]) and "Evidence window 1 Jan 2022 to the present" in _joined(out["full"])


@needs_bundler
@needs_gulf
def test_iter22_gulf_country_brief_says_what_its_counts_are_and_what_is_withheld(tmp_path_factory):
    inp = _input()
    member = inp["gulf"]["systems"][1]
    out = run_ts(tmp_path_factory, MODS, """
      const draw = (system, payload) => {
        globalThis.__drawn.length = 0;
        db.drawCountryImpactBrief(bi.countryBriefInput({ name: input.member.name, a3: input.member.a3, system,
          coverage: "4 of 9 source groups searched.", campaignLine: "Active-campaign safeguards apply.", reportingEnvironment: "restricted",
          national: null, payload, regional: input.context, method: input.method, buildDate: "2026-11-19" }));
        return globalThis.__drawn.map((d) => d.t);
      };
      const sys = (n) => ({ system_id: input.member.system_id, name: input.member.name, reporting_environment: "restricted",
                           event_summary: { recorded_events: n } });
      return { some: draw(sys(3), input.payload), none: draw(sys(0), { ...input.payload, records: [] }) };
    """, {**inp, "member": member})
    some, none = _joined(out["some"]), _joined(out["none"])
    assert f"2 published records inside {member['name']}" in some
    assert "3 published energy disruption records in this country's reviewed record" in some
    for text in (some, none):
        assert "not comparable with any other country" in text
        assert "place, facility, operator, method, headline and any later status" in text
        assert "Active-campaign safeguards apply." in text
        assert re.search(r"As of 20 Sep 2026 · ", text) and "Source: Example Maritime Agency" in text
        assert not any(s in text for s in SECRETS if s != "Example Group") and "Example Group" not in text
    # Meaningful when everything is empty: words about the dataset, never a zero.
    assert f"No published energy disruption record. That describes this dataset, not {member['name']}." in none
    assert f"No published impact record for {member['name']} in the current reviewed corpus" in none
    assert not re.search(r"\b0 (published|records|events)", none)


# ---------------- no per-country figure, nothing withheld ----------------

@needs_bundler
@needs_gulf
def test_iter22_gulf_brief_has_no_per_country_impact_figure(tmp_path_factory):
    inp = _input()
    names = [s["name"] for s in inp["gulf"]["systems"]]
    one = inp["gulf"]["systems"][0]
    moved = copy.deepcopy(inp["payload"])
    for r in moved["records"]:
        r.update(country_a3=one["a3"], country_name=one["name"], system_id=one["system_id"])
    out = run_ts(tmp_path_factory, MODS, DRAW_GULF_JS + """
      return { spread: drawGulf(input.payload, input.context, input.method), moved: drawGulf(input.moved, input.context, input.method) };
    """, {**inp, "moved": moved})
    assert out["spread"] == out["moved"], "the Gulf brief changes when records move between countries"
    assert any(re.search(r"7 published records for the \d+ countries together", l) for l in out["spread"])
    named = [l for l in out["spread"] if any(n in l for n in names)]
    assert len(named) == len(names), named
    for line in named:
        # A member is named on one line: its national energy figure and its unit, nothing else.
        assert re.fullmatch(r"[A-Z][A-Za-z ]+: (no data|[\d.,]+ [^·]+)", line), line
        assert not re.search(r"\brecords?\b|\bincidents?\b|\battacks?\b|\bevents?\b", line), line


@needs_bundler
@needs_gulf
def test_iter22_gulf_brief_is_handed_four_fields_and_draws_nothing_withheld(tmp_path_factory):
    out = run_ts(tmp_path_factory, MODS, DRAW_GULF_JS + """
      const narrowed = ib.briefRecords(input.payload.records);
      return { keys: [...new Set(narrowed.flatMap((r) => Object.keys(r)))].sort(), narrowed: JSON.stringify(narrowed),
               drawn: drawGulf(input.payload, input.context, input.method) };
    """, _input())
    assert out["keys"] == ["cause", "confidence", "itFailure", "services"]
    for secret in SECRETS:
        assert secret not in out["narrowed"], secret
        assert secret not in _joined(out["drawn"]), secret
    # The score never crosses either: a brief has the category in words.
    assert "score" not in out["narrowed"] and "84" not in out["narrowed"]


# ---------------- regional context in a brief ----------------

@needs_bundler
@needs_gulf
def test_iter22_gulf_brief_context_statements_are_dated_and_sourced(tmp_path_factory):
    inp = _input()
    many = copy.deepcopy(inp["context"])
    kinds = [t["id"] for t in many["context_types"]]
    many["entries"] = [_entry(f"ctx-{i}", f"2026-0{i + 1}-10", k, f"SYNTHETIC statement {i}.", f"Agency {i}", True) for i, k in enumerate(kinds)]
    out = run_ts(tmp_path_factory, MODS, DRAW_GULF_JS + """
      return { few: drawGulf(input.payload, input.context, input.method), many: drawGulf(input.payload, input.many, input.method) };
    """, {**inp, "many": many})
    few = out["few"]
    heads = [l for l in few if l.startswith("As of ")]
    assert heads == ["As of 20 Sep 2026 · Shipping, in aggregate", "As of 15 Apr 2026 · Reserve action"], heads
    for publisher in ("Example Maritime Agency", "Example Energy Agency"):
        assert f"Source: {publisher}" in few
    text = _joined(few)
    # The older statement of a kind is not drawn beside the newer one, and its source is not cited.
    assert "lower than a month earlier" not in text and "Example Statistics Office" not in text
    assert "60 million barrels (total release announced)" in text
    assert "not a current status" in text and "No open or closed status is published" in text
    assert not STATUS.search(text)
    assert not NEVER.search(text.replace("no facilities, no routes, no vessels", "")), NEVER.search(text.replace("no facilities, no routes, no vessels", ""))
    assert len(kinds) > 5, "the taxonomy no longer has more kinds than a brief carries"
    assert len([l for l in out["many"] if l.startswith("As of ")]) == 5
    # The newest five.
    assert [l for l in out["many"] if l.startswith("As of ")][0].startswith(f"As of 10 {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'][len(kinds) - 1]} 2026")


# ---------------- evidence confidence and causes in a brief ----------------

@needs_bundler
@needs_gulf
def test_iter22_gulf_brief_confidence_is_words_and_not_assessed_is_its_own_bucket(tmp_path_factory):
    out = run_ts(tmp_path_factory, MODS, DRAW_GULF_JS + """
      return { calibrated: drawGulf(input.payload, input.context, input.method),
               provisional: drawGulf(input.payload, input.context, input.provisional),
               // The method file failed to load: the categories are then worded from the records' own labels.
               unloaded: drawGulf(input.payload, input.context, null),
               tally: ib.tallyImpacts(ib.briefRecords(input.payload.records), { cause_families: [], sectors: [],
                 confidence: input.method.categories.map((c) => ({ id: c.id, label: c.label })) }).byConfidence };
    """, {**_input(), "provisional": _method("provisional: thresholds not calibrated")})
    assert out["tally"] == [{"id": "HIGH", "label": "High", "n": 5}, {"id": "PRELIMINARY", "label": "Preliminary", "n": 1},
                            {"id": "NOT_ASSESSED", "label": "Not assessed", "n": 1}]
    for name in ("calibrated", "provisional", "unloaded"):
        lines = out[name]
        assert "High 5 · Preliminary 1 · Not assessed 1" in lines, name
        text = _joined(lines)
        # No score: not out of a hundred, not a percentage. The one percentage is the energy share.
        assert not re.search(r"/ ?100|\bof 100\b|\b84\b", text), name
        assert all("of the world total" in l for l in lines if "%" in l), name
        assert "not a probability" in text, name
    for name in ("calibrated", "provisional"):
        assert "It is not the lowest category" in _joined(out[name]), name
    assert "The categories are provisional: thresholds not calibrated." in out["provisional"]
    assert "provisional" not in _joined(out["calibrated"]).lower()


@needs_bundler
@needs_gulf
def test_iter22_gulf_brief_causes_are_labelled_from_the_taxonomy_in_its_order(tmp_path_factory):
    inp = _input()
    out = run_ts(tmp_path_factory, MODS, DRAW_GULF_JS + """
      const v = input.payload.vocabularies;
      const vocab = { cause_families: v.cause_families.map((c) => ({ id: c.id, label: c.label })),
                      sectors: v.sectors.map((c) => ({ id: c.id, label: c.label })), digital_categories: v.digital_categories };
      return { tally: ib.tallyImpacts(ib.briefRecords(input.payload.records), vocab), drawn: drawGulf(input.payload, input.context, input.method) };
    """, inp)
    families = [c["id"] for c in inp["payload"]["vocabularies"]["cause_families"]]
    by_cause = out["tally"]["byCause"]
    ids = [r["id"] for r in by_cause]
    # Three cyber records and one of each other cause: vocabulary order, so the largest is not first.
    assert {r["id"]: r["n"] for r in by_cause} == {"kinetic": 1, "cyber": 3, "natural_hazard": 1, "authority_order": 1, "it_failure": 1}
    assert ids[:-1] == [f for f in families if f in ids] and ids[-1] == "it_failure", ids
    assert ids[0] != "cyber", "the cause rows are ordered by count"
    # An IT failure keeps out of cyber and out of its own cause family's row, so the rows add up.
    assert sum(r["n"] for r in by_cause) == out["tally"]["total"] == 7
    labels = {r["id"]: r["label"] for r in by_cause}
    assert labels["authority_order"] == "Ordered by an authority" and labels["it_failure"] == "IT failure (not an attack)"
    assert [r["id"] for r in out["tally"]["byService"]] == [s["id"] for s in inp["payload"]["vocabularies"]["sectors"]
                                                           if s["id"] in ("electricity", "water", "telecom", "transport")]
    assert any("Ordered by an authority 1" in l and "Cyber 3" in l for l in out["drawn"])


# ---------------- the page's sections ----------------

@needs_bundler
@needs_gulf
def test_iter22_gulf_sections_never_emit_a_per_country_count(tmp_path_factory):
    inp = _input()
    names = [s["name"] for s in inp["gulf"]["systems"]]
    out = run_ts(tmp_path_factory, MODS, RENDER_JS + """
      const records = gi.groupRecords(input.payload, input.members);
      const f = gi.groupImpactFilters(records, input.payload.vocabularies);
      return {
        n: records.length, order: records.map((r) => r.date),
        filters: f.defs.map((d) => ({ id: d.id, options: d.kind === "choice" ? d.options.map((o) => o.label) : [] })),
        impacts: text(el(sec.ReportedImpacts, { impacts: ready(input.payload), members: input.members, memberCount: input.members.length })),
        services: text(el(sec.ServicesSection, { impacts: ready(input.payload), members: input.members })),
        coverage: text(el(sec.CoverageSection, { impacts: ready(input.payload), systems: input.gulf.systems })),
      };
    """, inp)
    assert out["n"] == 7 and out["order"] == sorted(out["order"], reverse=True)
    # The filters are date, cause, sector and confidence. No filter's options are countries: an
    # option's count would be a tally per country.
    assert [f["id"] for f in out["filters"]] == ["date", "cause", "sector", "confidence"]
    for f in out["filters"]:
        assert not set(f["options"]) & set(names), f
    confidence = next(f for f in out["filters"] if f["id"] == "confidence")["options"]
    assert confidence[-1] == "Not assessed" and "Preliminary" in confidence
    cause = next(f for f in out["filters"] if f["id"] == "cause")["options"]
    assert "Ordered by an authority" in cause and "IT failure (not an attack)" in cause
    assert "Showing 7 of 7 published impact records" in out["impacts"]
    assert "separate corpus that is not scored" in out["impacts"]
    for section in ("impacts", "services", "coverage"):
        text = out[section]
        for name in names:
            assert not re.search(rf"{name}[^.]{{0,24}}\b\d+ (records?|incidents?|attacks?|events?)\b", text, re.I), (section, name)
            assert not re.search(rf"\b\d+ (records?|incidents?|attacks?|events?) (in|for|on|against) {name}", text, re.I), (section, name)
        assert not re.search(r"\bmost (affected|attacked|targeted)\b|\bhardest[- ]hit\b|\branked\b", text, re.I), section
        assert not STRAIT.search(text), (section, STRAIT.search(text))
    # The attack record is its country and nothing finer, on the page as in the brief.
    for secret in ("Secretville", "Hidden Works", "XX-99"):
        assert secret not in out["impacts"] and secret not in out["services"], secret
    assert "place withheld" in out["impacts"]
    # The record the build did not assess says so in words; it is not shown as the lowest category.
    assert "Not assessed" in out["impacts"]


@needs_bundler
@needs_gulf
def test_iter22_gulf_services_follow_the_vocabulary_and_keep_cyber_and_it_failures_apart(tmp_path_factory):
    inp = _input()
    out = run_ts(tmp_path_factory, MODS, RENDER_JS + """
      const records = gi.groupRecords(input.payload, input.members);
      const groups = gi.serviceGroups(records, input.payload.vocabularies);
      const split = gi.digitalSplit(records);
      return { groups: groups.map((g) => ({ service: g.service, rows: g.rows.map((r) => r.when) })),
               cyber: split.cyber.map((r) => r.impact_id), it: split.itFailures.map((r) => r.impact_id),
               html: text(el(sec.ServicesSection, { impacts: ready(input.payload), members: input.members })) };
    """, inp)
    sectors = [s["id"] for s in inp["payload"]["vocabularies"]["sectors"]]
    got = [g["service"] for g in out["groups"]]
    assert got == [s for s in sectors if s in got] and set(got) == {"electricity", "water", "telecom", "transport"}
    sizes = {g["service"]: len(g["rows"]) for g in out["groups"]}
    # Telecom has two lines and water one, and electricity (three) still comes first: the vocabulary's
    # order, not the counts.
    assert sizes == {"electricity": 3, "water": 1, "telecom": 2, "transport": 1}
    assert got.index("water") < got.index("telecom")
    records = inp["payload"]["records"]
    assert out["cyber"] == [r["impact_id"] for r in records if r["cause_family"] == "cyber"]
    assert out["it"] == [records[0]["impact_id"]] and records[0]["impact_id"] not in out["cyber"]
    html = out["html"]
    assert "the source counts subscribers; not converted" in html and "the source counts customers; not converted" in html
    assert "never listed as cyber" in html and "There is no summary by actor" in html
    assert "attributed by a government" in html, "attribution is shown as who attributes"
    # Every cause in the taxonomy is explained from the taxonomy, the new one included.
    for c in inp["payload"]["vocabularies"]["cause_families"]:
        assert c["label"] in html and c["definition"] in html, c["id"]
    # Three cyber records and one IT failure, each in brief with a link to its full record.
    assert html.count("Full record and sources") == 4
    assert html.index("Cyber records") < html.index("IT failures (not attacks)")


@needs_bundler
@needs_gulf
def test_iter22_gulf_context_section_is_dated_statements_with_sources_and_no_status_flag(tmp_path_factory):
    inp = _input()
    out = run_ts(tmp_path_factory, MODS, RENDER_JS + """
      const shipping = gi.filterContext(input.context, ["shipping_status"]);
      return {
        ready: text(el(sec.ContextSection, { regional: ready(input.context), groupId: "gulf_littoral" })),
        other: text(el(sec.ContextSection, { regional: ready(input.context), groupId: "gcc" })),
        failed: text(el(sec.ContextSection, { regional: { state: "failed" }, groupId: "gulf_littoral" })),
        narrowed: shipping.entries.map((e) => [e.id, e.is_latest_of_type, e.sources.length, e.date]),
        all: gi.filterContext(input.context, []).entries.length,
        kinds: gi.contextTypesPresent(input.context).map((t) => t.id),
      };
    """, inp)
    ready = out["ready"]
    for date, publisher in (("20 Sep 2026", "Example Maritime Agency"), ("15 Apr 2026", "Example Energy Agency"), ("5 Mar 2026", "Example Statistics Office")):
        assert date in ready and publisher in ready, (date, publisher)
    assert "As of 20 Sep 2026" in ready and "Historical statement, as of 5 Mar 2026" in ready
    assert "Showing 3 of 3 dated statements" in ready and "No single status is given" in ready
    assert not STATUS.search(ready), STATUS.search(ready)
    # Narrowing passes each statement through whole: the older one stays historical, with its source.
    assert out["narrowed"] == [["ctx-2026-09-20-a", True, 1, "2026-09-20"], ["ctx-2026-03-05-c", False, 1, "2026-03-05"]]
    assert out["all"] == 3 and out["kinds"] == ["shipping_status", "reserve_action"]
    # The fixed block says what is not collected and why, whether or not the file loaded.
    for name in ("ready", "failed", "other"):
        text = out[name]
        assert "Why there is no tanker map" in text, name
        assert "aggregate, dated, sourced statements only" in text, name
        assert "does not collect vessel positions, routes, bypass capacity or which facility depends on the strait" in text, name
        assert "those serve operations, not understanding" in text, name
        assert "enters no index and no country's record" in text and "A price movement is not an infrastructure loss" in text, name
    assert "could not be loaded" in out["failed"] and "Example Maritime Agency" not in out["failed"]
    assert "No regional context is published for this group" in out["other"] and "Example Maritime Agency" not in out["other"]


@needs_bundler
def test_iter22_gulf_sections_have_addresses_and_only_the_context_section_names_the_strait(tmp_path_factory):
    out = run_ts(tmp_path_factory, MODS, """
      const facts = (impacts, context) => ({ label: "Gulf littoral", members: 8, metrics: ["Crude oil production"], impacts, context });
      const states = ["loading", "unavailable", "empty", "some"];
      return {
        sections: gs.SECTIONS,
        from: ["?group=gulf&section=context", "?section=IMPACTS&group=gulf", "?group=gulf&section=tankers", "?group=gulf", "?group=gulf&section="]
          .map((s) => gs.sectionFrom(s)?.id ?? null),
        withSection: [gs.withSection("?group=gulf&f.cause=cyber", "context"), gs.withSection("?group=gulf&section=impacts&f.cause=cyber", "coverage"),
                      gs.withSection("?group=gulf&section=impacts", "overview"), gs.withSection("?group=gulf&section=impacts", null)],
        tell: states.flatMap((i) => states.map((c) => gs.tellLines(facts(i, c)))),
      };
    """)
    ids = [s["id"] for s in out["sections"]]
    assert ids == ["overview", "energy", "systems", "impacts", "services", "context", "coverage"]
    assert len({s["anchor"] for s in out["sections"]}) == len(ids)
    # A name the page does not have is no section at all, never a guess.
    assert out["from"] == ["context", "impacts", None, None, None]
    assert out["withSection"] == ["?group=gulf&f.cause=cyber&section=context", "?group=gulf&f.cause=cyber&section=coverage",
                                  "?group=gulf", "?group=gulf"]
    for s in out["sections"]:
        if s["id"] != "context":
            assert not STRAIT.search(s["label"]), s
    for lines in out["tell"]:
        assert len(lines) == 8 and all(l["section"] in ids for l in lines)
        for l in lines:
            # The overview is outside the context section, so no line of it speaks of the strait.
            assert not STRAIT.search(l["question"] + " " + l["answer"]), l
            assert not re.search(r"\bmost (affected|attacked|important)\b|\branked\b", l["answer"], re.I), l
    empty = out["tell"][2 * 4 + 3]   # impacts empty, context some
    assert any("describes the corpus and not the region" in l["answer"] for l in empty)
    failed = out["tell"][1 * 4 + 1]
    assert sum("Could not be loaded" in l["answer"] for l in failed) == 3
