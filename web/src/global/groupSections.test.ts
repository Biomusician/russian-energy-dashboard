import { describe, expect, it } from "vitest";
import {
  IT_FAILURE, confidenceWord, contextTypesPresent, digitalSplit, filterContext, groupAttempts, groupImpactFilters, groupRecords,
  impactAnchor, recordFromAnchor, serviceGroups,
} from "./groupImpacts";
import { SECTIONS, sectionFrom, tellLines, withSection, type TellFacts } from "./groupSections";
import { contextDescribes } from "./impacts/brief/briefInputs";
import type { ImpactRecord, ImpactsPayload, RegionalContext } from "./impacts/types";

/** The regional overview's sections and its impact model (iteration 22). Made records in the served
 *  shape: the rules here are about what the page may group, count and order, not about any country. */

const VOCAB = {
  cause_families: [
    { id: "kinetic", label: "Kinetic attack" }, { id: "cyber", label: "Cyber" },
    { id: "authority_order", label: "Ordered by an authority" },
    { id: "industrial_technical", label: "Industrial or technical failure" }, { id: "natural_hazard", label: "Natural hazard" },
  ],
  sectors: [{ id: "electricity", label: "Electricity" }, { id: "water", label: "Water" }, { id: "telecom", label: "Telecommunications" }],
  digital_categories: [{ id: "cyber", label: "Cyber" }, { id: "it_failure", label: "IT failure" }],
};

const conf = (category: string | null, label: string | null, reason?: string) => ({
  category, label, score: category ? 60 : null, disputed: false, reason,
  components: { directness: { tier: "direct", points: 40 }, origins: { count: 1, points: 0 }, effect: { specificity: null, points: 0 },
                opened: { points: 10 }, contemporaneous: { points: 10 } },
  reasons: [],
});

function rec(id: string, system: string | null, over: Partial<ImpactRecord> = {}): ImpactRecord {
  return {
    impact_id: id, record_kind: "disruption", date: "2026-03-01", date_precision: "day", date_end: null,
    country_a3: "AAA", country_name: `Country ${system}`, system_id: system, admin1: null, geographic_precision: "country",
    domain: "energy", sector: "electricity", technology: null, cause_family: "natural_hazard", contributing_factors: [], cyber_mechanism: null,
    summary: "s", effect: null, effect_specificity: null, inclusion_basis: 2, civilian_service_impact: [],
    attribution: { status: "NOT_APPLICABLE", actor: null, actor_type: null, basis: [], as_of: null, statement: null, competing: [], source_refs: [], confidence: null },
    ai_involvement: { status: "NONE_REPORTED", relation: null, role: null, as_of: null, statement: null, source_refs: [] },
    dispute: null, sources: [], episode_id: null, episode_basis: null, publication_policy: "standard", first_published: null,
    evidence_confidence: conf("HIGH", "High") as ImpactRecord["evidence_confidence"], origin_count: 1, ...over,
  };
}

const service = (s: string) => ({ service: s, geographic_scope: "national", affected: null, duration_text: null, source_refs: [] });

const RECORDS = [
  rec("a", "x", { date: "2026-05-01", cause_family: "cyber", cyber_mechanism: "ransomware", sector: "telecom", civilian_service_impact: [service("telecom")] }),
  rec("b", "y", { date: "2026-04-01", cause_family: "industrial_technical", cyber_mechanism: "it_outage_affecting_operations", sector: "water",
                  civilian_service_impact: [service("water"), service("telecom")] }),
  rec("c", "y", { date: "2026-03-01", cause_family: "authority_order", civilian_service_impact: [service("telecom")],
                  evidence_confidence: conf(null, null, "No primary source is attached yet.") as ImpactRecord["evidence_confidence"] }),
  rec("d", "z", { date: "2026-02-01", cause_family: "kinetic", publication_policy: "country_abstracted", civilian_service_impact: [service("electricity")],
                  evidence_confidence: conf("PRELIMINARY", "Preliminary") as ImpactRecord["evidence_confidence"] }),
  rec("e", null, { date: "2026-01-01" }),
  rec("f", "x", { record_kind: "attempt_no_service_impact" }),
];
const PAYLOAD = { vocabularies: VOCAB, records: RECORDS, attempts: [rec("g", "y", { record_kind: "attempt_no_service_impact" }), rec("h", "q", { record_kind: "attempt_no_service_impact" })] } as unknown as ImpactsPayload;
const MEMBERS = ["x", "y", "z"];

describe("sections", () => {
  it("each has its own address; the overview's is the page's own", () => {
    expect(SECTIONS.map((s) => s.id)).toEqual(["overview", "energy", "systems", "impacts", "services", "context", "coverage"]);
    expect(withSection("?group=gulf", "context")).toBe("?group=gulf&section=context");
    expect(withSection("?group=gulf&section=context&f.cause=cyber", "impacts")).toBe("?group=gulf&f.cause=cyber&section=impacts");
    expect(withSection("?group=gulf&section=context", "overview")).toBe("?group=gulf");
    expect(withSection("", null)).toBe("");
  });

  it("an address names a section or none: an unknown name is never a guess", () => {
    expect(sectionFrom("?group=gulf&section=coverage")?.id).toBe("coverage");
    expect(sectionFrom("?group=gulf&section=Coverage")?.id).toBe("coverage");
    expect(sectionFrom("?group=gulf&section=constructor")).toBeNull();
    expect(sectionFrom("?group=gulf&section=%E0%A4%A")).toBeNull();
    expect(sectionFrom("?group=gulf")).toBeNull();
  });

  it("the eight lines each point at a section, and say a failed download apart from an empty corpus", () => {
    const facts = (impacts: TellFacts["impacts"], context: TellFacts["context"]): TellFacts =>
      ({ label: "Gulf littoral", members: 8, metrics: ["Crude oil production"], impacts, context });
    const ids = SECTIONS.map((s) => s.id);
    for (const i of ["loading", "unavailable", "empty", "some"] as const) {
      const lines = tellLines(facts(i, "some"));
      expect(lines).toHaveLength(8);
      for (const l of lines) expect(ids).toContain(l.section);
    }
    const evidence = (i: TellFacts["impacts"]) => tellLines(facts(i, "some")).find((l) => l.id === "evidence")!.answer;
    expect(evidence("empty")).toMatch(/describes the corpus and not the region/);
    expect(evidence("unavailable")).toMatch(/Could not be loaded/);
    expect(evidence("unavailable")).not.toMatch(/No impact record/);
    expect(new Set(["loading", "unavailable", "empty", "some"].map((i) => evidence(i as TellFacts["impacts"]))).size).toBe(4);
  });
});

describe("the group's impact records", () => {
  it("are the members' disruptions in the served order; attempts are apart", () => {
    expect(groupRecords(PAYLOAD, MEMBERS).map((r) => r.impact_id)).toEqual(["a", "b", "c", "d"]);
    expect(groupAttempts(PAYLOAD, MEMBERS).map((r) => r.impact_id)).toEqual(["g"]);
    expect(groupRecords(PAYLOAD, [])).toEqual([]);
  });

  it("filters are date, cause, sector and confidence: there is no country filter", () => {
    const { defs } = groupImpactFilters(groupRecords(PAYLOAD, MEMBERS), VOCAB as unknown as ImpactsPayload["vocabularies"]);
    expect(defs.map((d) => d.id)).toEqual(["date", "cause", "sector", "confidence"]);
    const options = (id: string) => { const d = defs.find((x) => x.id === id)!; return d.kind === "choice" ? d.options.map((o) => o.label) : []; };
    // The taxonomy's order and labels, the new family included; an IT failure is its own choice.
    expect(options("cause")).toEqual(["Kinetic attack", "Cyber", "Ordered by an authority", "Industrial or technical failure", "IT failure (not an attack)"]);
    // Not assessed is its own choice, last, and is not Preliminary.
    expect(options("confidence")).toEqual(["High", "Preliminary", "Not assessed"]);
    const cause = defs.find((d) => d.id === "cause")!;
    const values = (r: ImpactRecord) => (cause.kind === "choice" ? cause.values(r) : []);
    expect(values(RECORDS[1])).toEqual(["industrial_technical", IT_FAILURE]);
    expect(values(RECORDS[0])).toEqual(["cyber"]);
    const confidence = defs.find((d) => d.id === "confidence")!;
    expect(confidence.kind === "choice" ? confidence.values(RECORDS[2]) : []).toEqual(["NOT_ASSESSED"]);
  });

  it("a filter with one possible value is a sentence instead", () => {
    const { defs, fixed } = groupImpactFilters([RECORDS[0]], VOCAB as unknown as ImpactsPayload["vocabularies"]);
    expect(defs.map((d) => d.id)).toEqual(["date"]);
    expect(fixed).toEqual(["All records have one reported cause: Cyber.", "All records concern one sector: Telecommunications.", "All records have one evidence confidence: High."]);
  });

  it("services follow the vocabulary's order, not the number of records; an IT failure is not cyber", () => {
    const groups = serviceGroups(groupRecords(PAYLOAD, MEMBERS), VOCAB as unknown as ImpactsPayload["vocabularies"]);
    expect(groups.map((g) => [g.service, g.rows.length])).toEqual([["electricity", 1], ["water", 1], ["telecom", 3]]);
    expect(groups[2].rows.map((r) => r.cause)).toEqual(["Cyber", "IT failure (not an attack)", "Ordered by an authority"]);
    // The attack record is its country and nothing finer.
    expect(groups[0].rows[0].place).toBe("Country z");
    const split = digitalSplit(groupRecords(PAYLOAD, MEMBERS));
    expect(split.cyber.map((r) => r.impact_id)).toEqual(["a"]);
    expect(split.itFailures.map((r) => r.impact_id)).toEqual(["b"]);
  });

  it("evidence confidence in words: the served label, or not assessed with the build's reason", () => {
    expect(confidenceWord(RECORDS[0])).toBe("High");
    expect(confidenceWord(RECORDS[2])).toBe("not assessed (No primary source is attached yet)");
    expect(confidenceWord({ evidence_confidence: null })).toBe("not assessed");
    expect(confidenceWord(RECORDS[2])).not.toMatch(/preliminary/i);
  });

  it("a record's link round-trips, and only a record link is read as one", () => {
    expect(impactAnchor("imp-2026-01-01-aaa-water-x")).toBe("impact-imp-2026-01-01-aaa-water-x");
    expect(recordFromAnchor("#impact-imp-2026-01-01-aaa-water-x")).toBe("imp-2026-01-01-aaa-water-x");
    expect(recordFromAnchor("#group-notes")).toBeNull();
    expect(recordFromAnchor("#impact-")).toBeNull();
    expect(recordFromAnchor("")).toBeNull();
  });
});

describe("the regional context", () => {
  const entry = (id: string, type: string, latest: boolean) => ({ id, date: "2026-01-01", as_of: "2026-01-01", context_type: type, claim: "c", metric: null,
    sources: [{ ref: "s1", url: "https://a.example", publisher: "A" }], is_latest_of_type: latest });
  const ctx = { context_id: "gulf_hormuz", context_types: [{ id: "shipping_status", label: "Shipping" }, { id: "aggregate_trade", label: "Trade" }, { id: "market_response", label: "Market" }],
                entries: [entry("1", "shipping_status", true), entry("2", "market_response", true), entry("3", "shipping_status", false)] } as unknown as RegionalContext;

  it("offers the kinds it holds, and narrowing passes each statement through untouched", () => {
    expect(contextTypesPresent(ctx).map((t) => t.id)).toEqual(["shipping_status", "market_response"]);
    expect(filterContext(ctx, [])).toBe(ctx);
    const shipping = filterContext(ctx, ["shipping_status"]);
    expect(shipping.entries).toEqual([ctx.entries[0], ctx.entries[2]]);
    expect(shipping.entries.map((e) => e.is_latest_of_type)).toEqual([true, false]);
  });

  it("belongs to the group it describes and to no other", () => {
    // The served file names its group; nothing else pairs them.
    expect(contextDescribes({ ...ctx, group: "gulf_littoral" }, "gulf_littoral")).toBe(true);
    expect(contextDescribes({ ...ctx, group: "gulf_littoral" }, "gcc")).toBe(false);
    expect(contextDescribes({ context_id: "constructor" }, "gulf_littoral")).toBe(false);
    // A file that names no group describes none: its id alone is never read as a group.
    expect(contextDescribes({ context_id: "gulf_hormuz" }, "gulf_littoral")).toBe(false);
    expect(contextDescribes({ context_id: "gulf_hormuz", group: "opec" }, "opec")).toBe(true);
    expect(contextDescribes({ context_id: "gulf_hormuz", group: "opec" }, "gulf_littoral")).toBe(false);
  });
});
