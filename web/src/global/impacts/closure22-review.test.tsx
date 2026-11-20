import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it } from "vitest";
import { AttributionLine } from "./AttributionLine";
import { ConfidenceBreakdown } from "./ConfidenceChip";
import { ContextTimeline } from "./ContextTimeline";
import { ImpactCard } from "./ImpactCard";
import { monitoredTag } from "./ImpactAtlas";
import { atlasFilterDefs, atlasPresets, presetCount, presetEmptyText } from "./atlasModel";
import { disruptions, isMaliciousCause, notEstablished } from "./model";
import { forgetVocabularies, registerMethod, registerVocabularies } from "./vocab";
import { TAB_LABEL } from "../countryTabs";
import { IMPACT_INCLUSION_LINE } from "../countryOverview";
import { impactFiles } from "../countryImpactModel";
import { ZERO_RECORD_IMPACT_NOTE, impactTabHref } from "../homeModel";
import { GLOSSARY, glossaryEntry } from "../glossary";
import { IMPACT_COLUMNS, IMPACT_FIELDS, SCORE_NOTE, readmeText } from "../recordCsv";
import { readinessLabel } from "../manifest";
import { causeDefinition } from "../GroupImpactSections";
import type { ConfidenceMethod, ImpactRecord, ImpactsPayload, RegionalContext } from "./types";

/** The first-time-user review's findings (iteration-22 closure), one block each. Every record is
 *  the pipeline's synthetic fixture or invented here. */

const FIX = new URL("../../../e2e/fixtures/impacts22/global/", import.meta.url);
const read = <T,>(name: string): T => JSON.parse(readFileSync(fileURLToPath(new URL(name, FIX)), "utf-8")) as T;
const payload = read<ImpactsPayload>("impacts.json");
const context = read<RegionalContext>("regional_context.json");
const method = read<ConfidenceMethod>("evidence_confidence.json");
const text = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/&amp;/g, "&").replace(/&#x27;/g, "'").replace(/&quot;/g, "\"").replace(/\s+/g, " ").trim();
const render = (el: React.ReactElement) => text(renderToStaticMarkup(el));

beforeAll(() => {
  forgetVocabularies();
  registerVocabularies(payload.vocabularies);
  registerVocabularies({ context_types: context.context_types });
  registerMethod(method);
});

describe("C1: a country card with no qualifying record points to its impact records tab", () => {
  it("links the tab by address and states no count", () => {
    expect(impactTabHref("ir")).toBe("?sys=ir&tab=impacts");
    expect(impactTabHref("a b")).toBe("?sys=a%20b&tab=impacts");
    expect(Object.values(ZERO_RECORD_IMPACT_NOTE).join("")).not.toMatch(/\d/);
    expect(ZERO_RECORD_IMPACT_NOTE.after).toMatch(/non-scored/);
  });
});

describe("C2: the country tab is named for what it holds", () => {
  it("is 'Impact records (not scored)' and says why an event can be there and not in the country's record", () => {
    expect(TAB_LABEL.impacts).toBe("Impact records (not scored)");
    expect(IMPACT_INCLUSION_LINE).toContain("own inclusion rule");
    expect(IMPACT_INCLUSION_LINE).toContain("so an event can appear here and not there");
    expect(IMPACT_INCLUSION_LINE).toContain("never enter a score");
    const files = impactFiles("ir", "Iran", [], 0, [], payload, "2026-11-19");
    expect(files.readme).toContain(IMPACT_INCLUSION_LINE);
  });
});

describe("C3: monitored systems are tagged in words; impact-record countries are defined", () => {
  it("tags a country system and the theatre, and nothing else", () => {
    expect(monitoredTag({ system_id: "ir", theatre: null })).toBe("monitored system");
    expect(monitoredTag({ system_id: null, theatre: true })).toBe("monitored theatre");
    expect(monitoredTag({ system_id: null, theatre: null })).toBeNull();
  });

  it("the glossary defines an impact-record country, alphabetically placed, and placement lists its four words", () => {
    const e = glossaryEntry("impact-record-country")!;
    expect(e.term).toBe("Impact-record country");
    expect(e.detail).toMatch(/no index/);
    expect(e.detail).toMatch(/no implied complete set of records/);
    const placement = glossaryEntry("placement")!;
    expect(placement.plain).toContain("four placements: National; Several regions; One region; National, under safeguards.");
    const at = GLOSSARY.findIndex((g) => g.id === "impact-record-country");
    expect(GLOSSARY[at - 1].id).toBe("impact-atlas");
  });
});

describe("C4: the evidence score is ordinal and nothing is ranked by it", () => {
  it("the breakdown says so without speaking of a percentage or a hundred", () => {
    const r = payload.records.find((x) => x.evidence_confidence?.score != null)!;
    const out = render(<ConfidenceBreakdown value={r.evidence_confidence!} method={method} />);
    expect(out).toContain("ordinal score, not a probability and not a share of a maximum");
    expect(out).toContain("records are never ranked by them");
    expect(out).not.toMatch(/\/\s*100|of 100|\d\s*%|percent/i);
  });

  it("the CSV puts the score beside its category and its README says it is ordinal, never to rank by", () => {
    expect(IMPACT_COLUMNS.indexOf("evidence_confidence_score")).toBe(IMPACT_COLUMNS.indexOf("evidence_confidence") + 1);
    expect(IMPACT_FIELDS.evidence_confidence_score).toMatch(/never rank or sort records by it/);
    const readme = readmeText({ title: "t", csvName: "x.csv", scope: "s", buildDate: "2026-11-19", downloaded: "2026-11-19", shown: 0, total: 0,
                                filters: [], limitations: [], columns: IMPACT_COLUMNS, fields: IMPACT_FIELDS });
    expect(readme).toContain(SCORE_NOTE);
    expect(SCORE_NOTE).toMatch(/must not be ranked or sorted by it/);
    const other = readmeText({ title: "t", csvName: "x.csv", scope: "s", buildDate: "2026-11-19", downloaded: "2026-11-19", shown: 0, total: 0,
                               filters: [], limitations: [], columns: ["event_id"], fields: { event_id: "id" } });
    expect(other).not.toContain(SCORE_NOTE);
  });
});

describe("C5: a context card leads with its 'as of' date", () => {
  it("'As of' comes first; the statement's own date follows only where it differs", () => {
    const html = renderToStaticMarkup(<ContextTimeline ctx={context} />);
    const heads = [...html.matchAll(/<div class="ctx-head">(.*?)<\/div>/g)].map((m) => text(m[1]));
    expect(heads.length).toBe(context.entries.length);
    for (const h of heads) expect(h).toMatch(/^As of \d{1,2} [A-Z][a-z]{2} \d{4}/);
    const differs = context.entries.find((e) => e.date !== e.as_of)!;
    expect(heads.some((h) => h.includes("statement dated"))).toBe(!!differs);
  });
});

describe("C6: a preset that leads to nothing says so", () => {
  it("each chip has its count, and an empty AI preset explains itself", () => {
    const defs = atlasFilterDefs(payload, method);
    const records = disruptions(payload);
    const presets = atlasPresets(payload);
    const ai = presets.find((p) => p.id === "ai")!;
    const aiRecords = records.filter((r) => r.ai_involvement.status !== "NONE_REPORTED").length;
    expect(presetCount(ai, defs, records, "2026-11-19")).toBe(aiRecords);
    expect(presetCount(ai, defs, records.filter((r) => r.ai_involvement.status === "NONE_REPORTED"), "2026-11-19")).toBe(0);
    expect(presetCount(presets.find((p) => p.id === "cyber")!, defs, records, "2026-11-19")).toBe(records.filter((r) => r.cause_family === "cyber").length);
    // A preset whose filter is not on the page counts nothing, rather than every record.
    expect(presetCount({ ...ai, choices: { nosuch: ["x"] } }, defs, records, "2026-11-19")).toBe(0);
    expect(presetEmptyText(ai)).toMatch(/^No reviewed record currently reports AI involvement/);
  });
});

describe("C7: no 'malicious or possibly malicious' over a cause that is not malicious", () => {
  const unknownCause = () => payload.records.find((r) => r.cause_family === "unknown" && r.attribution.status === "UNKNOWN")
    ?? ({ ...payload.records[0], cause_family: "unknown", contributing_factors: [], attribution: { ...payload.records[0].attribution, status: "UNKNOWN", self_claims: [] } } as ImpactRecord);

  it("reads the served malicious flag", () => {
    expect(isMaliciousCause({ cause_family: "cyber", contributing_factors: [] })).toBe(true);
    expect(isMaliciousCause({ cause_family: "kinetic", contributing_factors: [] })).toBe(true);
    expect(isMaliciousCause({ cause_family: "unknown", contributing_factors: [] })).toBe(false);
    expect(isMaliciousCause({ cause_family: "industrial_technical", contributing_factors: ["sabotage"] })).toBe(true);
  });

  it("an unknown-cause record says there is no attribution question; a cyber one keeps 'not established'", () => {
    const r = unknownCause();
    const card = render(<ImpactCard record={r} />);
    expect(card).toContain("Attribution: no attribution question");
    expect(card).not.toMatch(/malicious or possibly malicious/i);
    expect(notEstablished(r)[0]).toMatch(/^Whether the cause was malicious at all/);
    const cyber = payload.records.find((x) => x.cause_family === "cyber" && x.attribution.status === "UNKNOWN")!;
    expect(render(<ImpactCard record={cyber} />)).toContain("unknown (not established)");
    // Without the cause, the line is as it was.
    expect(render(<AttributionLine a={r.attribution} />)).toContain("unknown (not established)");
  });
});

describe("C9: nits", () => {
  it("the readiness badge never implies events a system does not have", () => {
    expect(readinessLabel("CONTEXT_ONLY", 0)).toBe("No index; no qualifying records yet");
    expect(readinessLabel("CONTEXT_ONLY", 3)).toBe("Reported events, no index");
    expect(readinessLabel("INDEX_READY", 0)).toBe("Index published");
  });

  it("a malicious cause's definition says it is malicious, once", () => {
    expect(causeDefinition({ definition: "A disruption caused through computer systems or networks.", malicious: true }))
      .toBe("A disruption caused through computer systems or networks. Malicious: an attack, not an accident or a failure.");
    expect(causeDefinition({ definition: "A kinetic attack on a site.", malicious: true })).toBe("A kinetic attack on a site.");
    expect(causeDefinition({ definition: "A storm.", malicious: false })).toBe("A storm.");
  });
});
