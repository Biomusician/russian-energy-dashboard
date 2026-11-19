import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it } from "vitest";
import { AiLine } from "./AiLine";
import { AttributionLine } from "./AttributionLine";
import { ConfidenceBreakdown, ConfidenceChip } from "./ConfidenceChip";
import { CONTEXT_CAVEAT, ContextTimeline } from "./ContextTimeline";
import { ImpactCard } from "./ImpactCard";
import { ImpactInspector } from "./ImpactInspector";
import { confidenceMalformed, confidenceMethodProblems, impactsFor, impactsProblems, regionalContextProblems } from "./load";
import {
  NOT_ASSESSED, attempts, attributionConfidenceLabel, claimSupport, confidenceBucket, confidenceLabel, disruptions, isCyber,
  isHistoricalAddition, isItFailure, notEstablished, originsText, placeText, serviceLine,
} from "./model";
import { forgetVocabularies, labelOf, registerMethod, registerVocabularies } from "./vocab";
import type { ConfidenceMethod, EvidenceConfidence, ImpactRecord, ImpactsPayload, RegionalContext } from "./types";

/** The shared impact components against the served shapes (iteration 22).
 *
 *  The fixture is the pipeline's own synthetic corpus as it is served (web/e2e/fixtures/impacts22,
 *  kept equal to `python -m pipeline.global_impacts --fixture` by a pytest), so these tests read
 *  the same shapes the site does. Every record in it is invented.
 */

const FIX = new URL("../../../e2e/fixtures/impacts22/global/", import.meta.url);
const read = <T,>(name: string): T => JSON.parse(readFileSync(fileURLToPath(new URL(name, FIX)), "utf-8")) as T;
const payload = read<ImpactsPayload>("impacts.json");
const context = read<RegionalContext>("regional_context.json");
const method = read<ConfidenceMethod>("evidence_confidence.json");
const text = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/&amp;/g, "&").replace(/&#x27;/g, "'").replace(/&quot;/g, "\"").replace(/\s+/g, " ").trim();
const render = (el: React.ReactElement) => text(renderToStaticMarkup(el));
const one = (pick: (r: ImpactRecord) => boolean): ImpactRecord => {
  const r = payload.records.find(pick);
  if (!r) throw new Error("the fixture has no such record");
  return r;
};

/** Evidence that was not assessed, as the build serves it: a null category and the reason. */
const NOT_ASSESSED_VALUE = {
  category: null, label: null, score: null, disputed: false,
  reason: "Cited through a discovery aid only; a primary source is not yet attached.",
} as unknown as EvidenceConfidence;

beforeAll(() => {
  forgetVocabularies();
  registerVocabularies(payload.vocabularies);
  registerVocabularies({ context_types: context.context_types });
  registerMethod(method);
});

describe("served shapes", () => {
  it("the three fixture files pass the shape checks the loaders apply", () => {
    expect(impactsProblems(payload)).toEqual([]);
    expect(regionalContextProblems(context)).toEqual([]);
    expect(confidenceMethodProblems(method)).toEqual([]);
  });

  it("a malformed corpus is refused, naming the fault", () => {
    expect(impactsProblems({ ...payload, records: "x" })).toContain("records is not a list");
    expect(impactsProblems({ ...payload, records: [{ ...payload.records[0], attribution: null }] })).toContain("a record has no attribution status");
    expect(impactsProblems(null)).toEqual(["not an object"]);
  });
});

describe("impactsFor", () => {
  it("returns one country's records in the served order, and a multi-country record for each of its countries", () => {
    const esp = impactsFor(payload, { a3: "ESP" });
    expect(esp.map((r) => r.country_a3).sort()).toEqual(["ESP", "MULTI"]);
    expect(esp.map((r) => r.impact_id)).toEqual(payload.records.filter((r) => esp.includes(r)).map((r) => r.impact_id));
    expect(impactsFor(payload, { a3: "prt" }).map((r) => r.country_a3)).toEqual(["MULTI"]);
  });

  it("returns the records of a set of systems, and nothing for no selection", () => {
    expect(impactsFor(payload, { systemIds: ["us", "ir"] }).map((r) => r.system_id).sort()).toEqual(["ir", "us"]);
    expect(impactsFor(payload, { systemIds: ["zz"] })).toEqual([]);
    expect(impactsFor(payload, {})).toEqual([]);
  });

  it("never returns an attempt, even one filed among the records", () => {
    const stray = { ...payload.attempts[0], country_a3: "ESP" };
    const mixed = { ...payload, records: [stray, ...payload.records] };
    expect(impactsFor(mixed, { a3: "ESP" }).some((r) => r.record_kind !== "disruption")).toBe(false);
    expect(disruptions(mixed)).toHaveLength(payload.records.length);
    expect(attempts(mixed)).toHaveLength(payload.attempts.length + 1);
  });
});

describe("ConfidenceChip", () => {
  it("says the category in words and offers the reasons", () => {
    const r = one((x) => x.evidence_confidence?.category === "HIGH");
    const out = render(<ConfidenceChip value={r.evidence_confidence} />);
    expect(out).toContain("Evidence confidence: High");
    expect(out).toContain("Why?");
  });

  it("an absent confidence is 'Not assessed', never the lowest category and never an empty chip", () => {
    const out = render(<ConfidenceChip value={null} />);
    expect(out).toContain("Evidence confidence: Not assessed");
    expect(out).toContain("No evidence confidence is published for this record");
    expect(out).not.toMatch(/Preliminary|Limited/);
  });

  it("a null category with a reason is a neutral 'Not assessed' chip that shows the served reason", () => {
    const out = render(<ConfidenceChip value={NOT_ASSESSED_VALUE} />);
    expect(out).toContain("Evidence confidence: Not assessed");
    expect(out).toContain(NOT_ASSESSED_VALUE.reason!);
    expect(out).not.toMatch(/Preliminary|Limited|Why\?/);
    expect(renderToStaticMarkup(<ConfidenceChip value={NOT_ASSESSED_VALUE} />)).not.toMatch(/conf-(preliminary|limited|high|moderate)/);
    expect(confidenceLabel(NOT_ASSESSED_VALUE)).toBe("Not assessed");
    expect(confidenceBucket(NOT_ASSESSED_VALUE)).toBe(NOT_ASSESSED);
    expect(confidenceBucket(null)).toBe(NOT_ASSESSED);
  });

  it("a null category must come with its reason: a bare null is refused at load", () => {
    expect(confidenceMalformed(NOT_ASSESSED_VALUE)).toBe(false);
    expect(confidenceMalformed({ ...NOT_ASSESSED_VALUE, reason: null })).toBe(true);
    expect(confidenceMalformed({ ...NOT_ASSESSED_VALUE, reason: "  " })).toBe(true);
    const rec = { ...payload.records[0], evidence_confidence: NOT_ASSESSED_VALUE };
    expect(impactsProblems({ ...payload, records: [rec] })).toEqual([]);
    expect(impactsProblems({ ...payload, records: [{ ...rec, evidence_confidence: { category: null } }] })).toContain("a record's evidence confidence is malformed");
  });

  it("a card and an inspector for a not-assessed record say so, with the reason", () => {
    const rec: ImpactRecord = { ...payload.records[0], evidence_confidence: NOT_ASSESSED_VALUE };
    expect(render(<ImpactCard record={rec} />)).toContain(`Evidence confidence: Not assessed ${NOT_ASSESSED_VALUE.reason}`);
    const inspector = render(<ImpactInspector record={rec} />);
    expect(inspector).toContain("Evidence confidence: Not assessed");
    expect(inspector).toContain(NOT_ASSESSED_VALUE.reason!);
    expect(inspector).not.toMatch(/Preliminary/);
  });

  it("the points are points: never out of a hundred, never a percentage", () => {
    for (const r of payload.records) {
      const out = render(<ConfidenceBreakdown value={r.evidence_confidence!} method={method} />);
      expect(out).not.toMatch(/\/\s*100|of 100|\d\s*%|percent/i);
      expect(out).toContain(`${r.evidence_confidence!.score} points : ordinal score, not a probability`);
    }
  });

  it("origins are worded by their served basis, and publishers are never called originating statements", () => {
    expect(originsText(3, "publishers")).toBe("3 distinct publishers cited; whether they relay one statement was not reviewed");
    expect(originsText(1, "publishers")).toBe("1 distinct publisher cited; whether they relay one statement was not reviewed");
    expect(originsText(2, "reviewed")).toMatch(/^2 originating statements, as established on review$/);
    expect(originsText(2, undefined)).toBe("2");
    const base = one((x) => x.evidence_confidence?.category === "HIGH");
    const withBasis = (basis: string): ImpactRecord => ({
      ...base, evidence_confidence: { ...base.evidence_confidence!, components: { ...base.evidence_confidence!.components,
        origins: { ...base.evidence_confidence!.components.origins, basis } } },
    });
    const publishers = render(<ImpactInspector record={withBasis("publishers")} />);
    expect(publishers).toContain("distinct publishers cited; whether they relay one statement was not reviewed");
    // Only served text (the method's own component label, a served reason) may say "originating".
    const served = [...method.components.flatMap((c) => [c.label, c.meaning ?? ""]), ...method.categories.map((c) => c.meaning), ...base.evidence_confidence!.reasons].filter(Boolean);
    let own = publishers;
    for (const s of served) own = own.split(s).join("");
    expect(own).not.toMatch(/originating statement/i);
    expect(render(<ImpactInspector record={withBasis("reviewed")} />)).toContain("as established on review");
  });

  it("no component composes 'independent originating statements': that phrase is the served method's to use", () => {
    const servedLabel = method.components.find((c) => c.id === "origins")!.label;
    for (const r of payload.records) {
      let out = render(<ImpactCard record={r} />) + render(<ImpactInspector record={r} />);
      for (const s of [servedLabel, ...method.categories.map((c) => c.meaning), ...(r.evidence_confidence?.reasons ?? [])]) out = out.split(s).join("");
      expect(out).not.toMatch(/independent originating statements/i);
    }
  });

  it("shows the method's status while it is provisional, and nothing when it is not", () => {
    const r = one((x) => x.evidence_confidence?.category === "MODERATE");
    const provisional = { ...method, status: "provisional: thresholds not calibrated" };
    expect(render(<ConfidenceBreakdown value={r.evidence_confidence!} method={provisional} />)).toContain("Method status: provisional: thresholds not calibrated.");
    expect(render(<ConfidenceBreakdown value={r.evidence_confidence!} method={{ ...method, status: null }} />)).not.toContain("Method status");
  });

  it("the breakdown lists reasons and components, calls the score ordinal and quotes the served sentence", () => {
    const r = one((x) => x.evidence_confidence?.category === "MODERATE");
    const out = render(<ConfidenceBreakdown value={r.evidence_confidence!} method={method} />);
    for (const reason of r.evidence_confidence!.reasons) expect(out).toContain(reason);
    for (const c of method.components) expect(out).toContain(c.label);
    expect(out).toContain(`${r.evidence_confidence!.score} points : ordinal score, not a probability`);
    expect(out).toContain(method.statement);
  });

  it("a disputed record says that disputed overrides the score", () => {
    const r = one((x) => x.evidence_confidence?.category === "DISPUTED");
    expect(render(<ConfidenceBreakdown value={r.evidence_confidence!} method={method} />)).toContain("Disputed overrides the score");
  });
});

describe("AttributionLine: three absences, three renderings", () => {
  it("not applicable renders nothing at all", () => {
    const r = one((x) => x.attribution.status === "NOT_APPLICABLE");
    expect(renderToStaticMarkup(<AttributionLine a={r.attribution} />)).toBe("");
  });

  it("unknown is 'not established' and never a confidence level", () => {
    const r = one((x) => x.attribution.status === "UNKNOWN");
    const out = render(<AttributionLine a={r.attribution} />);
    expect(out).toContain("Attribution: unknown (not established)");
    expect(out).not.toMatch(/confidence: /i);
    expect(out).not.toMatch(/\bconfidence: low\b/i);
    expect(attributionConfidenceLabel(r.attribution, method.attribution.labels)).toBeNull();
  });

  it("an assessed attribution reads status, actor (type), attributed by, as of, confidence", () => {
    const r = one((x) => x.attribution.status === "ASSESSED");
    const out = render(<AttributionLine a={r.attribution} />);
    expect(out).toContain("Attribution: assessed · Example Group B (state-linked) · attributed by the affected operator · as of 2 Dec 2024 · confidence: Moderate");
    expect(out).toContain(r.attribution.statement!);
  });

  it("a claim is the actor's own, is called claim only, and is said not to be corroboration", () => {
    const r = one((x) => x.attribution.status === "CLAIMED");
    const out = render(<AttributionLine a={r.attribution} />);
    expect(out).toContain("claimed by the actor itself");
    expect(out).toContain("confidence: Claim only");
    expect(out).not.toContain("attributed by");
  });

  it("a disputed attribution lists every competing attribution in 'X attributed this to Y' form and does not choose", () => {
    const r = one((x) => x.attribution.status === "DISPUTED");
    const out = render(<AttributionLine a={r.attribution} />);
    expect(out).toContain("A government attributed this to Example Group E (state-linked).");
    expect(out).toContain("A cyber security firm attributed this to Example Group F (criminal).");
    expect(out).toContain("does not choose");
  });

  it("no attribution copy says an actor attacked", () => {
    for (const r of payload.records) {
      expect(render(<AttributionLine a={r.attribution} />)).not.toMatch(/\battacked\b/i);
    }
  });
});

describe("AiLine", () => {
  it("renders nothing when no source reports AI, including on an ordinary cyber record", () => {
    const cyber = payload.records.filter((r) => isCyber(r) && r.ai_involvement.status === "NONE_REPORTED");
    expect(cyber.length).toBeGreaterThan(0);
    for (const r of cyber) expect(renderToStaticMarkup(<AiLine ai={r.ai_involvement} />)).toBe("");
    expect(renderToStaticMarkup(<AiLine ai={null} />)).toBe("");
  });

  it("AI-assisted is said not to be AI-caused", () => {
    const r = one((x) => x.ai_involvement.relation === "ai_assisted");
    const out = render(<AiLine ai={r.ai_involvement} />);
    expect(out).toContain("AI involvement: suspected");
    expect(out).toContain("AI-assisted (not AI-caused)");
    expect(out).toContain(r.ai_involvement.statement!);
  });

  it("an AI system that failed in operations is 'AI as operational cause', a different thing", () => {
    const r = one((x) => x.ai_involvement.relation === "ai_operational_cause");
    const out = render(<AiLine ai={r.ai_involvement} />);
    expect(out).toContain("AI involvement: confirmed");
    expect(out).toContain("AI as operational cause");
    expect(out).not.toContain("not AI-caused");
  });
});

describe("ImpactCard", () => {
  it("shows date, country, the taxonomy chips from served labels, summary and effect", () => {
    const r = one((x) => x.cyber_mechanism === "ransomware");
    const out = render(<ImpactCard record={r} />);
    expect(out).toContain(r.country_name);
    expect(out).toContain(labelOf("sectors", r.sector));
    expect(out).toContain("Cause: cyber");
    expect(out).toContain("Mechanism: ransomware");
    expect(out).toContain(r.summary);
    expect(out).toContain(r.effect!);
    expect(out).toContain(`Sources (${r.sources.length})`);
  });

  it("an ordinary cyber record carries no AI line", () => {
    const r = one((x) => isCyber(x) && x.ai_involvement.status === "NONE_REPORTED");
    expect(render(<ImpactCard record={r} />)).not.toContain("AI involvement");
  });

  it("an IT failure is labelled as one and is not cyber", () => {
    // Built from a served record: the ruling (methodology §4) is newer than the fixture corpus.
    const base = one((x) => x.cause_family === "industrial_technical");
    const r: ImpactRecord = { ...base, cyber_mechanism: "it_outage_affecting_operations" };
    expect(isItFailure(r)).toBe(true);
    expect(isCyber(r)).toBe(false);
    // The same mechanism under a malicious cyber cause is a cyber record, not an IT failure.
    expect(isItFailure({ ...r, cause_family: "cyber" })).toBe(false);
    const out = render(<ImpactCard record={r} />);
    expect(out).toContain("IT failure: IT outage affecting operations");
    expect(out).not.toContain("Attribution:");
  });

  it("a region is shown when one is published", () => {
    const r = one((x) => !!x.admin1 && x.publication_policy === "standard");
    expect(render(<ImpactCard record={r} />)).toContain(`${r.admin1!.name}, ${r.country_name}`);
  });

  it("an abstracted record shows no place, even if one reached the record, and says the place is withheld", () => {
    const r = one((x) => x.publication_policy === "country_abstracted");
    const leaked = { ...r, admin1: { code: "UA-99", name: "Leakedregion" }, geographic_precision: "admin1" };
    expect(placeText(leaked)).toBe(r.country_name);
    const out = render(<ImpactCard record={leaked} />);
    expect(out).not.toContain("Leakedregion");
    expect(out).toContain("Published under safeguards: place withheld");
  });

  it("a kinetic record is treated as abstracted even without the policy field", () => {
    const r = one((x) => x.cause_family === "kinetic");
    const leaked = { ...r, publication_policy: "standard", admin1: { code: "UA-99", name: "Leakedregion" } };
    expect(render(<ImpactCard record={leaked} />)).not.toContain("Leakedregion");
  });

  it("the figure keeps the source's own unit and words", () => {
    const r = one((x) => x.civilian_service_impact.some((s) => typeof s.affected === "object" && s.affected?.unit === "stations"));
    const out = render(<ImpactCard record={r} />);
    expect(out).toContain("affected: about 300 stations");
    expect(out).toContain("the source counts stations; not converted");
  });

  it("an unknown figure is said as unknown, and a not-yet-researched duration as that", () => {
    const line = serviceLine({ service: "water", geographic_scope: "local", affected: "unknown", duration_text: "not_researched", source_refs: [] });
    expect(line.affected).toBe("unknown");
    expect(line.duration).toBe("not yet researched");
    expect(serviceLine({ service: "water", geographic_scope: "local", affected: null, duration_text: null, source_refs: [] }).affected).toBeNull();
  });

  it("says when a record was added long after its event, and not otherwise", () => {
    const old = one((x) => x.date < "2026-01-01");
    expect(isHistoricalAddition(old)).toBe(true);
    expect(render(<ImpactCard record={old} />)).toContain("Historical record added");
    const fresh = { ...old, date: "2026-11-01", date_end: null, date_precision: "day", first_published: "2026-11-19" };
    expect(isHistoricalAddition(fresh)).toBe(false);
    expect(render(<ImpactCard record={fresh} />)).not.toContain("Historical record added");
  });

  it("a month-precision date is shown as a month", () => {
    const r = one((x) => x.date_precision === "month");
    expect(render(<ImpactCard record={r} />)).toMatch(/(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) 20\d\d/);
  });

  it("an attempt is labelled as an attempt, in the served words", () => {
    const out = render(<ImpactCard record={payload.attempts[0]} />);
    expect(out).toContain(payload.attempts_label!);
  });
});

describe("ImpactInspector", () => {
  it("lists which sources support which claim, as a chain", () => {
    const r = one((x) => x.attribution.status === "ATTRIBUTED");
    const chain = claimSupport(r, payload.vocabularies.claims.map((c) => String(c.id)));
    expect(chain.map((c) => c.claim)).toEqual(["occurrence", "effect", "attribution"]);
    const out = render(<ImpactInspector record={r} />);
    expect(out).toContain("What each claim rests on");
    expect(out).toContain("Attribution:");
    for (const s of r.sources) expect(out).toContain(s.publisher!);
    expect(out).toMatch(/Supports: that it happened; the effect\./);
    expect(out).toMatch(/Supports: attribution\./);
  });

  it("a social source shows platform, account, tier and how identity was established", () => {
    const r = one((x) => x.sources.some((s) => s.social?.account_tier === "S1"));
    const s = r.sources.find((x) => x.social)!;
    const out = render(<ImpactInspector record={r} />);
    expect(out).toContain(s.social!.platform);
    expect(out).toContain(s.social!.handle!);
    expect(out).toContain("Account tier S1: official account");
    expect(out).toContain(s.social!.identity_basis);
  });

  it("an abstracted record shows no source headline", () => {
    const r = one((x) => x.publication_policy === "country_abstracted");
    const leaked = { ...r, sources: r.sources.map((s) => ({ ...s, title_original: "Leakedheadline names a place" })) };
    const out = render(<ImpactInspector record={leaked} />);
    expect(out).not.toContain("Leakedheadline");
    expect(out).toContain("Source headlines are not shown");
  });

  it("says what the evidence does not establish, from the record's own fields", () => {
    const unknown = notEstablished(one((x) => x.attribution.status === "UNKNOWN" && x.ai_involvement.status === "NONE_REPORTED"));
    expect(unknown.join(" ")).toContain("not the same as a low-confidence attribution");
    expect(unknown.join(" ")).toContain("No source ties AI to this incident");
    const assisted = notEstablished(one((x) => x.ai_involvement.relation === "ai_assisted"));
    expect(assisted.join(" ")).toContain("That AI caused the disruption");
    const natural = notEstablished(one((x) => x.attribution.status === "NOT_APPLICABLE"));
    expect(natural.join(" ")).not.toContain("Who was responsible");
  });
});

describe("ContextTimeline", () => {
  const out = render(<ContextTimeline ctx={context} />);

  it("always carries the fixed caveat and the served limits", () => {
    expect(out).toContain(CONTEXT_CAVEAT);
    expect(CONTEXT_CAVEAT).toMatch(/No vessels, routes or bypass capacity are collected/);
    expect(out).toContain(context.not_built);
    const empty = render(<ContextTimeline ctx={{ ...context, entries: [] }} />);
    expect(empty).toContain(CONTEXT_CAVEAT);
  });

  it("lists statements newest first, whatever order the file is in", () => {
    const shuffled = render(<ContextTimeline ctx={{ ...context, entries: [...context.entries].reverse() }} />);
    const dates = context.entries.map((e) => e.date).sort().reverse();
    let at = -1;
    for (const e of [...context.entries].sort((a, b) => (a.date < b.date ? 1 : -1))) {
      const i = shuffled.indexOf(e.claim);
      expect(i).toBeGreaterThan(at);
      at = i;
    }
    expect(dates[0]).toBe(context.entries[0].date);
  });

  it("marks the newest of each type 'as of' and older ones 'historical statement', and never a status flag", () => {
    const older = context.entries.filter((e) => !e.is_latest_of_type);
    expect(older.length).toBeGreaterThan(0);
    expect(out.match(/Historical statement, as of/g)).toHaveLength(older.length);
    expect(out.match(/Not a current status/g)!.length).toBeGreaterThanOrEqual(context.entries.length - older.length);
    expect(out).not.toMatch(/\b(status|strait|shipping)( is|:)? (open|closed)\b/i);
  });

  it("shows a figure with its unit and what it measures", () => {
    const e = context.entries.find((x) => x.metric && x.metric.unit === "mb/d")!;
    expect(out).toContain(`${e.metric!.value} mb/d`);
    expect(out).toContain(e.metric!.basis!);
  });
});
