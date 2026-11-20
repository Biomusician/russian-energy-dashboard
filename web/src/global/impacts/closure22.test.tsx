import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it } from "vitest";
import { AttributionLine } from "./AttributionLine";
import { ContextTimeline, asOfText } from "./ContextTimeline";
import { ImpactCard } from "./ImpactCard";
import { ImpactInspector } from "./ImpactInspector";
import { anyTie, latestCounts, latestEntries } from "./latestOfType";
import { isHistoricalAddition, notEstablished, selfClaimsOf } from "./model";
import { forgetVocabularies, registerMethod, registerVocabularies } from "./vocab";
import { briefRecords, briefStatements, statementsNote, MAX_BRIEF_STATEMENTS, type BriefSourceEntry } from "./brief/impactBrief";
import { compactLead, latestOfEachType } from "../CountryRegional";
import { impactOrder } from "../countryImpactModel";
import { groupByMonth } from "./atlasModel";
import { IMPACT_COLUMNS, IMPACT_FIELDS, impactRecordsCsv, impactRow } from "../recordCsv";
import { impactItemText, isFirstPublishedDay } from "../whatsNewText";
import { attackPlacementText, precisionRulesText } from "../groupPrecision";
import type { Attribution, ConfidenceMethod, ContextEntry, ImpactRecord, ImpactsPayload, RegionalContext } from "./types";

/** Iteration-22 release closure, in the components (synthetic records throughout; every record and
 *  every statement here is invented):
 *  1. an actor's own claim of responsibility is shown apart, as "Self-claim (unverified)", never as
 *     a competing attribution, never as the attribution itself;
 *  2. a null first_published ("pending its first release") never renders as a date;
 *  3. several statements of one context type sharing the newest date are all the latest, and the
 *     copy is plural for them;
 *  4. the Gulf page's precision copy distinguishes its three rules.
 */

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

const CLAIM = "SYNTHETIC Group Z said on its own channel that it carried out the incident.";
const claim = { actor: "SYNTHETIC Group Z", actor_type: "hacktivist", statement: CLAIM, source_refs: ["s9"] };

function attribution(over: Partial<Attribution> = {}): Attribution {
  return {
    status: "ASSESSED", actor: "SYNTHETIC Group A", actor_type: "state_linked", basis: ["government"], as_of: "2026-05-01",
    statement: "A government assessed SYNTHETIC Group A as responsible.", competing: [], source_refs: ["s1"], confidence: "MODERATE",
    self_claims: [claim], ...over,
  };
}

function record(over: Partial<ImpactRecord> = {}): ImpactRecord {
  const base = payload.records.find((r) => r.cause_family === "cyber" && r.publication_policy === "standard") ?? payload.records[0];
  return {
    ...base, impact_id: "imp-2026-05-01-zzz-telecom-synthetic", attribution: attribution(),
    sources: [...base.sources, { ...base.sources[0], ref: "s9", publisher: "SYNTHETIC Group Z channel", source_role: "actor_self_claim", medium: "social", supports: ["attribution"] }],
    ...over,
  } as ImpactRecord;
}

describe("self-claims are provenance, shown apart", () => {
  it("an assessed attribution keeps its actor; the claim is a separate 'Self-claim (unverified)' line", () => {
    const out = render(<AttributionLine a={attribution()} />);
    expect(out).toContain("SYNTHETIC Group A (state-linked)");
    expect(out).toContain(`Self-claim (unverified): ${CLAIM}`);
    expect(out).toContain("not a competing attribution");
    expect(out).not.toMatch(/Competing attributions/);
    // The attribution itself is still the assessed one: the claimant is not its actor.
    expect(out.indexOf("SYNTHETIC Group A")).toBeLessThan(out.indexOf("Self-claim"));
    expect(out).not.toMatch(/Attribution: [^·]*SYNTHETIC Group Z/);
  });

  it("under a disputed attribution the claim is never inside the competing list", () => {
    const a = attribution({
      status: "DISPUTED", actor: null, actor_type: null, confidence: "DISPUTED",
      competing: [{ actor: "SYNTHETIC Group B", actor_type: "criminal", basis: ["cybersecurity_firm"], statement: null, source_refs: ["s2"] },
                  { actor: "SYNTHETIC Group C", actor_type: "state", basis: ["government"], statement: null, source_refs: ["s3"] }],
    });
    const html = renderToStaticMarkup(<AttributionLine a={a} />);
    const competing = /<ul class="attr-competing">([\s\S]*?)<\/ul>/.exec(html)![1];
    expect(competing.match(/<li/g)).toHaveLength(2);
    expect(competing).not.toContain("Group Z");
    expect(competing).not.toContain("Self-claim");
    expect(text(html)).toContain(`Self-claim (unverified): ${CLAIM}`);
  });

  it("beside an unknown attribution, and on its own where there is nothing to attribute", () => {
    const unknown = render(<AttributionLine a={attribution({ status: "UNKNOWN", actor: null, confidence: "NOT_ESTABLISHED" })} />);
    expect(unknown).toContain("unknown (not established)");
    expect(unknown).toContain("Self-claim (unverified)");
    expect(unknown).not.toMatch(/confidence:/);
    const na = render(<AttributionLine a={attribution({ status: "NOT_APPLICABLE", actor: null, confidence: null })} />);
    expect(na).toBe(`Self-claim (unverified): ${CLAIM} An actor's own claim of responsibility, recorded as provenance. It is not an attribution, not a competing attribution, and it does not change the attribution or its confidence.`);
    expect(renderToStaticMarkup(<AttributionLine a={attribution({ status: "NOT_APPLICABLE", self_claims: [] })} />)).toBe("");
  });

  it("an absent, null or malformed list is no claims, and a claim with no statement says who claimed it", () => {
    for (const self_claims of [undefined, null, "x", [null], [{ actor: null, actor_type: null, statement: null, source_refs: [] }]]) {
      const a = attribution({ self_claims: self_claims as unknown as Attribution["self_claims"] });
      expect(selfClaimsOf(a)).toEqual([]);
      expect(render(<AttributionLine a={a} />)).not.toContain("Self-claim");
    }
    const bare = render(<AttributionLine a={attribution({ self_claims: [{ ...claim, statement: null }] })} />);
    expect(bare).toContain("Self-claim (unverified): SYNTHETIC Group Z (hacktivist) claimed responsibility.");
  });

  it("does not change the confidence shown", () => {
    const withClaim = render(<AttributionLine a={attribution()} />);
    const without = render(<AttributionLine a={attribution({ self_claims: [] })} />);
    expect(withClaim).toContain("confidence: Moderate");
    expect(without).toContain("confidence: Moderate");
  });

  it("the card and the evidence inspector show it, with its source, under its own heading", () => {
    const r = record();
    expect(render(<ImpactCard record={r} />)).toContain(`Self-claim (unverified): ${CLAIM}`);
    const insp = render(<ImpactInspector record={r} />);
    expect(insp).toContain("Self-claims of responsibility (unverified)");
    expect(insp).toContain(`Self-claim (unverified): ${CLAIM} Cited: SYNTHETIC Group Z channel.`);
    expect(insp).toContain("A self-claim is not corroboration");
  });

  it("notEstablished says a claim is a claim once, and not twice under a CLAIMED status", () => {
    expect(notEstablished(record()).filter((l) => /claimed responsibility/.test(l))).toHaveLength(1);
    const claimed = record({ attribution: attribution({ status: "CLAIMED", actor: "SYNTHETIC Group Z", basis: ["actor_self_claim"], confidence: "CLAIM_ONLY" }) });
    expect(notEstablished(claimed).filter((l) => /claimed responsibility/.test(l))).toHaveLength(1);
    expect(notEstablished(record({ attribution: attribution({ self_claims: [] }) })).some((l) => /self-claim/i.test(l))).toBe(false);
  });

  it("the CSV has no competing column, so no self-claims column, and no cell carries the claim", () => {
    expect(IMPACT_COLUMNS.some((c) => /competing/.test(c))).toBe(false);
    expect(IMPACT_COLUMNS.some((c) => /self_claim/.test(c))).toBe(false);
    const row = impactRow(record());
    // The claimant's channel is still cited as a source; the claim itself is in no column.
    expect(Object.entries(row).filter(([k, v]) => k !== "citations" && v.includes("Group Z"))).toEqual([]);
    expect(Object.values(row).some((v) => v.includes(CLAIM))).toBe(false);
    expect(row.attribution_actor).toBe("SYNTHETIC Group A");
  });

  it("a brief is never handed an attribution, so a claim cannot be drawn", () => {
    for (const r of briefRecords([record()])) expect(JSON.stringify(r)).not.toContain("Group Z");
  });
});

describe("a null first_published is pending its first release, never a date", () => {
  const BAD = /\bnull\b|Invalid Date|1970|NaN|undefined/;
  const old = () => record({ date: "2023-02-01", date_end: null, date_precision: "day", first_published: null });

  it("the card says nothing about when it was added, and invents nothing", () => {
    expect(isHistoricalAddition(old())).toBe(false);
    const out = render(<ImpactCard record={old()} />);
    expect(out).not.toContain("Historical record added");
    expect(out).not.toMatch(BAD);
    expect(render(<ImpactInspector record={old()} />)).not.toMatch(BAD);
    // A malformed value is not a date either.
    expect(isHistoricalAddition(record({ first_published: "null" }))).toBe(false);
    expect(isHistoricalAddition(record({ first_published: "" }))).toBe(false);
  });

  it("the CSV cell is empty and its definition says why", () => {
    expect(impactRow(old()).first_published).toBe("");
    expect(impactRecordsCsv([old()])).not.toMatch(BAD);
    expect(IMPACT_FIELDS.first_published).toMatch(/Empty: not yet served, pending its first release/);
  });

  it("What's New gives no first-published date for it", () => {
    const item = { key: "k", impact_id: "imp-x", date: "2023-02-01", date_precision: "day", country: "Oman", sector: "water" };
    for (const first_published of [null, undefined, "null", "", "2026-13"]) {
      const s = impactItemText({ ...item, timing: "backfill", first_published }, "impact_record_added");
      expect(s).not.toContain("first published");
      expect(s).not.toMatch(BAD);
      expect(isFirstPublishedDay(first_published)).toBe(false);
    }
    expect(impactItemText({ ...item, timing: "backfill", first_published: "2026-11-20" }, "impact_record_added")).toContain("first published 20 Nov 2026");
  });

  it("ordering and grouping never read it: the list sorts by event date and does not throw", () => {
    const rs = [record({ impact_id: "b", date: "2024-01-01", first_published: null }), record({ impact_id: "a", date: "2025-01-01", first_published: "2026-11-20" }),
                record({ impact_id: "c", date: "2023-01-01", first_published: null })];
    expect(impactOrder(rs).map((r) => r.impact_id)).toEqual(["a", "b", "c"]);
    expect(groupByMonth(impactOrder(rs)).map((g) => g.year)).toEqual(["2025", "2024", "2023"]);
  });
});

describe("several statements of one type can share the newest date", () => {
  const entry = (id: string, type: string, asOf: string, latest?: boolean): ContextEntry => ({
    id, date: asOf, as_of: asOf, context_type: type, claim: `SYNTHETIC statement ${id}.`, metric: null,
    sources: [{ ref: "s1", url: "https://example.org/a", publisher: `Agency ${id}`, date: asOf, language: "en", source_role: "government", medium: "web", supports: ["occurrence"] }],
    ...(latest === undefined ? {} : { is_latest_of_type: latest }),
  } as ContextEntry);
  const tied = [entry("a", "shipping_status", "2026-09-20", true), entry("b", "shipping_status", "2026-09-20", true),
                entry("c", "shipping_status", "2026-03-01", false), entry("d", "reserve_action", "2026-04-15", true)];
  const served = { ...context, latest_note: "n", entries: tied, latest_by_type: { shipping_status: ["a", "b"], reserve_action: ["d"] } };

  it("the served map is used as it is; without it, the flags and their ties; without flags, the newest date", () => {
    expect([...latestEntries(tied, served.latest_by_type)].map((e) => e.id).sort()).toEqual(["a", "b", "d"]);
    // An older payload that flagged only one of two tied statements: neither is picked over the other.
    const legacy = [entry("a", "shipping_status", "2026-09-20", true), entry("b", "shipping_status", "2026-09-20", false), entry("c", "shipping_status", "2026-03-01", false)];
    expect([...latestEntries(legacy)].map((e) => e.id).sort()).toEqual(["a", "b"]);
    const unflagged = [entry("a", "t", "2026-09-20"), entry("b", "t", "2026-09-20"), entry("c", "t", "2026-01-01")];
    expect([...latestEntries(unflagged)].map((e) => e.id).sort()).toEqual(["a", "b"]);
    // A malformed map is ignored rather than trusted.
    expect([...latestEntries(tied, { shipping_status: "a" })].map((e) => e.id).sort()).toEqual(["a", "b", "d"]);
    const counts = latestCounts(tied, latestEntries(tied, served.latest_by_type));
    expect(counts.get("shipping_status")).toBe(2);
    expect(anyTie(counts)).toBe(true);
  });

  it("the timeline marks both tied statements and speaks of them in the plural", () => {
    const out = render(<ContextTimeline ctx={served} />);
    expect(out.match(/one of the 2 most recent shipping, in aggregate statements on record/gi)).toHaveLength(2);
    expect(out).not.toMatch(/the most recent shipping, in aggregate statement on record/i);
    expect(out).toMatch(/the most recent reserve action statement on record/i);
    expect(out.match(/Historical statement, as of/g)).toHaveLength(1);
    expect(out).toContain("where several share the newest date, every one of them is marked");
    // Without a tie the copy stays singular.
    const single = render(<ContextTimeline ctx={{ ...served, entries: [tied[0], tied[2], tied[3]], latest_by_type: { shipping_status: ["a"], reserve_action: ["d"] } }} />);
    expect(single).toMatch(/the most recent shipping, in aggregate statement on record/i);
    expect(single).not.toMatch(/statements on record/);
    expect(asOfText(tied[0], 0)).toMatch(/^Historical statement/);
  });

  it("the country tab's compact view keeps both and says so", () => {
    const compact = latestOfEachType(served);
    expect(compact.entries.map((e) => e.id)).toEqual(["a", "b", "d"]);
    expect(compactLead(compact, 1)).toBe("The newest statements of each kind (where several share the newest date, all are shown); 1 earlier statement is on the full timeline.");
    const single = latestOfEachType({ ...served, latest_by_type: { shipping_status: ["a"], reserve_action: ["d"] } });
    expect(compactLead(single, 2)).toBe("The newest statement of each kind; 2 earlier statements are on the full timeline.");
  });

  it("a brief carries every tied statement or none of its type, and its note is plural", () => {
    const labels = [{ id: "shipping_status", label: "Shipping, in aggregate" }, { id: "reserve_action", label: "Reserve action" }];
    const s = briefStatements(tied as BriefSourceEntry[], labels, served.latest_by_type);
    expect(s.map((x) => x.claim)).toEqual(["SYNTHETIC statement a.", "SYNTHETIC statement b.", "SYNTHETIC statement d."]);
    expect(statementsNote(s)).toContain("where several statements of a type share the newest date, all of them are shown");
    expect(statementsNote(s.slice(2))).not.toContain("several");
    // Four single types first, then a tied pair that would overflow five: the pair is left out whole.
    const many = [...["p", "q", "r", "s"].map((t, i) => entry(t, t, `2026-10-0${i + 1}`)), entry("x", "u", "2026-09-01"), entry("y", "u", "2026-09-01")];
    const cut = briefStatements(many as BriefSourceEntry[], []);
    expect(cut.length).toBeLessThanOrEqual(MAX_BRIEF_STATEMENTS);
    expect(cut.some((x) => x.claim.includes(" x.")) === cut.some((x) => x.claim.includes(" y."))).toBe(true);
  });
});

describe("the Gulf page's three placement rules", () => {
  it("a card says which rule applies, and what holds for the other records", () => {
    expect(attackPlacementText("country")).toMatch(/^Attacks and sabotage are recorded for the country as a whole/);
    expect(attackPlacementText("country")).toContain("Other eligible records: first-level region at most.");
    const admin1 = attackPlacementText("admin1");
    expect(admin1).toContain("by first-level region");
    expect(admin1).toContain("on this country's own page");
    expect(admin1).toContain("In the impact records on this page they are country level");
  });

  it("the page's paragraph names the exception from the served field and says the impact layer is always country level", () => {
    const systems = [{ name: "Bahrain", attack_records_placed: "country" as const }, { name: "Saudi Arabia", attack_records_placed: "admin1" as const }];
    const p = precisionRulesText(systems);
    expect(p.lead).toBe("Countries are recorded under two rules.");
    expect(p.body).toContain("In the impact records on this page that holds for every country, always.");
    expect(p.body).toContain("Saudi Arabia places its own attack records by first-level region");
    expect(p.body).toContain("Records that are not attacks are placed by first-level region at most");
    const none = precisionRulesText([{ name: "Bahrain", attack_records_placed: "country" }]);
    expect(none.lead).not.toContain("two rules");
    expect(none.body).not.toMatch(/places its own attack records/);
  });
});
