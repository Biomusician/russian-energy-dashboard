"""Iteration 22 release closure: four frontend rules, executed.

vitest (web/src/global/impacts/closure22.test.tsx) and Playwright (web/e2e/closure22.e2e.ts) prove
these where a reader meets them. The mutation campaign sees neither, so the rules are pinned here
by RUNNING the shipped TypeScript (the esbuild harness of tests/test_iteration21_testarch.py):

- an actor's own claim of responsibility (`attribution.self_claims`) is shown apart, as
  "Self-claim (unverified)": never inside the competing attributions, never as the attribution;
- a null `first_published` ("pending its first release") is never rendered as a date;
- several regional-context statements of one type sharing the newest date are all the latest,
  and the copy speaks of them in the plural; none is picked over the others;
- the Gulf page's placement copy keeps three rules apart: attacks at country level (always so in
  the impact layer), the admin1 system's own-page rule, and first-level region at most otherwise.

Every record and statement here is invented.
"""
import re

from tests.test_iteration21_testarch import needs_bundler, run_ts

CLAIM = "SYNTHETIC Group Z said on its own channel that it carried out the incident."
SELF_CLAIM = {"actor": "SYNTHETIC Group Z", "actor_type": "hacktivist", "statement": CLAIM, "source_refs": ["s9"]}
BAD_DATE = re.compile(r"\bnull\b|Invalid Date|1970|NaN|undefined")


def _attribution(**over):
    a = {"status": "ASSESSED", "actor": "SYNTHETIC Group A", "actor_type": "state_linked", "basis": ["government"],
         "as_of": "2026-05-01", "statement": "A government assessed SYNTHETIC Group A as responsible.", "competing": [],
         "source_refs": ["s1"], "confidence": "MODERATE", "self_claims": [SELF_CLAIM]}
    a.update(over)
    return a


def _record(**over):
    r = {
        "impact_id": "imp-2023-02-01-zzz-telecom-synthetic", "record_kind": "disruption", "date": "2023-02-01",
        "date_precision": "day", "date_end": None, "country_a3": "ZZZ", "countries_a3": None, "countries": None,
        "country_name": "Synthetica", "system_id": None, "admin1": None, "geographic_precision": "country",
        "domain": "civilian_service", "sector": "telecom", "technology": None, "cause_family": "cyber",
        "contributing_factors": [], "cyber_mechanism": "ddos", "summary": "SYNTHETIC outage of a telecom service.",
        "effect": "Service unavailable.", "effect_specificity": "described", "inclusion_basis": None,
        "civilian_service_impact": [], "attribution": _attribution(),
        "ai_involvement": {"status": "NONE_REPORTED", "relation": None, "role": None, "as_of": None, "statement": None, "source_refs": []},
        "dispute": None,
        "sources": [{"ref": "s1", "url": "https://example.org/a", "publisher": "Agency A", "date": "2023-02-02", "language": "en",
                     "source_role": "government", "medium": "web", "social": None, "supports": ["occurrence", "attribution"]}],
        "episode_id": None, "episode_basis": None, "publication_policy": "standard", "first_published": None,
        "evidence_confidence": None, "origin_count": None,
    }
    r.update(over)
    return r


def _entry(id_, type_, as_of, latest):
    return {"id": id_, "date": as_of, "as_of": as_of, "context_type": type_, "claim": f"SYNTHETIC statement {id_}.", "metric": None,
            "sources": [{"ref": "s1", "url": "https://example.org/c", "publisher": f"Agency {id_}", "source_role": "government",
                         "medium": "web", "supports": ["occurrence"]}], "is_latest_of_type": latest}


def _context(entries, latest_by_type=None):
    c = {"schema_version": 1, "as_of": "2026-11-19", "context_id": "synthetic", "label": "Synthetic context",
         "statement": "Dated statements.", "not_built": "Nothing else.", "latest_note": "n", "empty_reason": None,
         "context_types": [{"id": "shipping_status", "label": "Shipping, in aggregate"}, {"id": "reserve_action", "label": "Reserve action"}],
         "vocabularies": {}, "entries": entries}
    if latest_by_type is not None:
        c["latest_by_type"] = latest_by_type
    return c


TIED = [_entry("a", "shipping_status", "2026-09-20", True), _entry("b", "shipping_status", "2026-09-20", True),
        _entry("c", "shipping_status", "2026-03-01", False), _entry("d", "reserve_action", "2026-04-15", True)]
SERVED_MAP = {"shipping_status": ["a", "b"], "reserve_action": ["d"]}


@needs_bundler
def test_closure22_self_claim_is_never_a_competing_attribution_or_the_attribution(tmp_path_factory):
    disputed = _attribution(status="DISPUTED", actor=None, actor_type=None, confidence="DISPUTED", competing=[
        {"actor": "SYNTHETIC Group B", "actor_type": "criminal", "basis": ["cybersecurity_firm"], "statement": None, "source_refs": ["s2"]},
        {"actor": "SYNTHETIC Group C", "actor_type": "state", "basis": ["government"], "statement": None, "source_refs": ["s3"]}])
    out = run_ts(tmp_path_factory, {"al": "global/impacts/AttributionLine.tsx", "m": "global/impacts/model.ts"}, """
      const r = (a) => renderToStaticMarkup(React.createElement(al.AttributionLine, { a }));
      return { assessed: r(input.assessed), disputed: r(input.disputed), unknown: r(input.unknown), none: r(input.none),
               notEst: m.notEstablished(input.record) };
    """, {"assessed": _attribution(), "disputed": disputed, "unknown": _attribution(status="UNKNOWN", actor=None, confidence="NOT_ESTABLISHED"),
          "none": _attribution(self_claims=[]), "record": _record()})
    competing = re.search(r'<ul class="attr-competing">(.*?)</ul>', out["disputed"], re.S).group(1)
    assert competing.count("<li") == 2
    assert "Group Z" not in competing and "Self-claim" not in competing
    for html in (out["assessed"], out["disputed"], out["unknown"]):
        assert f"Self-claim (unverified):</span> {CLAIM}" in html, html
    # The attribution's own line, before its statement, names the assessed actor and never the claimant.
    head = out["assessed"].split('<div class="attr-statement">')[0]
    assert "SYNTHETIC Group A" in head and "Group Z" not in head
    assert "Self-claim" not in out["none"]
    assert sum("claimed responsibility" in line for line in out["notEst"]) == 1


@needs_bundler
def test_closure22_null_first_published_is_never_rendered_as_a_date(tmp_path_factory):
    item = {"key": "k", "impact_id": "imp-x", "date": "2023-02-01", "date_precision": "day", "country": "Synthetica", "sector": "water"}
    out = run_ts(tmp_path_factory, {"card": "global/impacts/ImpactCard.tsx", "wn": "global/whatsNewText.ts", "csv": "global/recordCsv.ts"}, """
      return {
        card: renderToStaticMarkup(React.createElement(card.ImpactCard, { record: input.record })),
        items: [null, "null", ""].map((first_published) => wn.impactItemText({ ...input.item, timing: "backfill", first_published }, "impact_record_added")),
        dated: wn.impactItemText({ ...input.item, timing: "backfill", first_published: "2026-11-20" }, "impact_record_added"),
        cell: csv.impactRow(input.record).first_published,
      };
    """, {"record": _record(first_published=None), "item": item})
    assert "Historical record added" not in out["card"]
    assert not BAD_DATE.search(re.sub(r"<[^>]+>", " ", out["card"]))
    for s in out["items"]:
        assert "first published" not in s and not BAD_DATE.search(s), s
    assert out["dated"].endswith("first published 20 Nov 2026")
    assert out["cell"] == ""


@needs_bundler
def test_closure22_tied_latest_statements_are_all_kept_and_plural(tmp_path_factory):
    legacy = [dict(TIED[0]), dict(TIED[1], is_latest_of_type=False), dict(TIED[2])]
    out = run_ts(tmp_path_factory, {"tl": "global/impacts/ContextTimeline.tsx", "cr": "global/CountryRegional.tsx",
                                    "lt": "global/impacts/latestOfType.ts", "ib": "global/impacts/brief/impactBrief.ts"}, """
      const compact = cr.latestOfEachType(input.served);
      const statements = ib.briefStatements(input.served.entries, input.served.context_types, input.served.latest_by_type);
      return {
        timeline: renderToStaticMarkup(React.createElement(tl.ContextTimeline, { ctx: input.served })),
        compact: compact.entries.map((e) => e.id), lead: cr.compactLead(compact, 1),
        legacy: [...lt.latestEntries(input.legacy)].map((e) => e.id).sort(),
        brief: statements.map((s) => s.claim), note: ib.statementsNote(statements),
      };
    """, {"served": _context(TIED, SERVED_MAP), "legacy": legacy})
    timeline = re.sub(r"<[^>]+>", " ", out["timeline"])
    assert len(re.findall(r"one of the 2 most recent shipping[^.]* statements on record", timeline)) == 2, timeline
    assert not re.search(r"the most recent shipping[^.]* statement on record", timeline)
    assert "every one of them is marked" in timeline
    assert out["compact"] == ["a", "b", "d"]
    assert out["lead"].startswith("The newest statements of each kind (where several share the newest date, all are shown)")
    assert out["legacy"] == ["a", "b"]
    assert out["brief"] == ["SYNTHETIC statement a.", "SYNTHETIC statement b.", "SYNTHETIC statement d."]
    assert "share the newest date, all of them are shown" in out["note"]


@needs_bundler
def test_closure22_gulf_placement_rules_stay_distinct(tmp_path_factory):
    out = run_ts(tmp_path_factory, {"gp": "global/groupPrecision.ts"}, """
      return { country: gp.attackPlacementText("country"), admin1: gp.attackPlacementText("admin1"),
               rules: gp.precisionRulesText(input.systems) };
    """, {"systems": [{"name": "Bahrain", "attack_records_placed": "country"}, {"name": "Saudi Arabia", "attack_records_placed": "admin1"}]})
    assert out["country"].startswith("Attacks and sabotage are recorded for the country as a whole")
    assert "first-level region at most" in out["country"]
    assert "on this country's own page" in out["admin1"] and "In the impact records on this page they are country level" in out["admin1"]
    body = out["rules"]["body"]
    assert "In the impact records on this page that holds for every country, always." in body
    assert "Saudi Arabia places its own attack records by first-level region" in body
    assert "Records that are not attacks are placed by first-level region at most" in body
