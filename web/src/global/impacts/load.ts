/** Loading the impact layer's three files (iteration 22).
 *
 *  One request per file per page, through the request cache every other payload uses
 *  (manifest.ts): a failed or malformed file is not kept, so the next caller retries, and a
 *  malformed one fails as "could not be loaded" instead of reaching a component half-formed.
 *
 *  Nothing here runs at import. The home page imports none of this, and no file is requested
 *  until a view that shows impact records asks for it.
 */
import { once, validated } from "../manifest";
import { registerMethod, registerVocabularies } from "./vocab";
import type { ConfidenceMethod, ImpactRecord, ImpactsPayload, RegionalContext } from "./types";

export const IMPACTS_PATH = "global/impacts.json";
export const REGIONAL_CONTEXT_PATH = "global/regional_context.json";
export const CONFIDENCE_METHOD_PATH = "global/evidence_confidence.json";

const isObj = (x: unknown): x is Record<string, unknown> => typeof x === "object" && x !== null && !Array.isArray(x);
const isStr = (x: unknown): x is string => typeof x === "string";

/** What the components read without checking. One line per kind of fault, not per record. */
function recordProblems(r: unknown): string | null {
  if (!isObj(r)) return "a record is not an object";
  if (!isStr(r.impact_id) || !isStr(r.date) || !isStr(r.country_a3) || !isStr(r.record_kind)) return "a record lacks its id, date, country or kind";
  if (!isStr(r.summary) || !isStr(r.cause_family) || !isStr(r.sector) || !isStr(r.domain)) return "a record lacks its summary, cause, sector or domain";
  if (!isObj(r.attribution) || !isStr(r.attribution.status)) return "a record has no attribution status";
  if (!isObj(r.ai_involvement) || !isStr(r.ai_involvement.status)) return "a record has no AI-involvement status";
  if (!Array.isArray(r.sources) || r.sources.some((s) => !isObj(s) || !isStr(s.url) || !Array.isArray(s.supports))) return "a record's sources are malformed";
  if (!Array.isArray(r.civilian_service_impact)) return "a record's service impacts are not a list";
  if (r.evidence_confidence != null && (!isObj(r.evidence_confidence) || !isStr(r.evidence_confidence.category)
      || !isObj(r.evidence_confidence.components) || !Array.isArray(r.evidence_confidence.reasons))) return "a record's evidence confidence is malformed";
  return null;
}

export function impactsProblems(x: unknown): string[] {
  if (!isObj(x)) return ["not an object"];
  const out: string[] = [];
  if (!isStr(x.scope_statement)) out.push("no scope statement");
  if (!Array.isArray(x.caveats)) out.push("caveats is not a list");
  if (!isObj(x.vocabularies)) out.push("no vocabularies");
  if (!isObj(x.research)) out.push("no research summary");
  if (!Array.isArray(x.countries)) out.push("countries is not a list");
  for (const key of ["records", "attempts"]) {
    const list = x[key];
    if (!Array.isArray(list)) { out.push(`${key} is not a list`); continue; }
    const bad = new Set(list.map(recordProblems).filter(isStr));
    out.push(...bad);
  }
  return out;
}

export function regionalContextProblems(x: unknown): string[] {
  if (!isObj(x)) return ["not an object"];
  const out: string[] = [];
  if (!isStr(x.label) || !isStr(x.statement) || !isStr(x.not_built)) out.push("no label, statement or limits");
  if (!Array.isArray(x.context_types)) out.push("context_types is not a list");
  if (!Array.isArray(x.entries)) out.push("entries is not a list");
  else if (x.entries.some((e) => !isObj(e) || !isStr(e.id) || !isStr(e.date) || !isStr(e.as_of) || !isStr(e.claim)
      || !isStr(e.context_type) || !Array.isArray(e.sources))) out.push("an entry is malformed");
  return out;
}

export function confidenceMethodProblems(x: unknown): string[] {
  if (!isObj(x)) return ["not an object"];
  const out: string[] = [];
  if (!isStr(x.statement)) out.push("no statement");
  if (!Array.isArray(x.components) || x.components.some((c) => !isObj(c) || !isStr(c.id) || !isStr(c.label))) out.push("components malformed");
  if (!Array.isArray(x.categories)) out.push("categories is not a list");
  if (!isObj(x.attribution) || !isObj(x.attribution.labels) || !isObj(x.attribution.meanings)) out.push("attribution labels missing");
  return out;
}

/** The impact corpus. Its vocabularies are registered for every impact component on the page. */
export function loadImpacts(): Promise<ImpactsPayload> {
  return once("impacts:payload", async () => {
    const p = await validated<ImpactsPayload>(IMPACTS_PATH, impactsProblems);
    registerVocabularies(p.vocabularies);
    return p;
  });
}

/** The Gulf and Strait of Hormuz context timeline. */
export function loadRegionalContext(): Promise<RegionalContext> {
  return once("impacts:context", async () => {
    const c = await validated<RegionalContext>(REGIONAL_CONTEXT_PATH, regionalContextProblems);
    registerVocabularies({ ...c.vocabularies, context_types: c.context_types });
    return c;
  });
}

/** The Evidence Confidence method, as data: what the "Why?" disclosure and the glossary read. */
export function loadConfidenceMethod(): Promise<ConfidenceMethod> {
  return once("impacts:method", async () => {
    const m = await validated<ConfidenceMethod>(CONFIDENCE_METHOD_PATH, confidenceMethodProblems);
    registerMethod(m);
    return m;
  });
}

/** The disruptions of one country (`a3`) or of a set of monitored systems, in the served order
 *  (event date, newest first). A multi-country record belongs to each of its countries. Attempts
 *  are never returned: they are not disruptions and are listed apart (`payload.attempts`). */
export function impactsFor(payload: ImpactsPayload, by: { a3?: string; systemIds?: readonly string[] }): ImpactRecord[] {
  const a3 = by.a3?.toUpperCase();
  const systems = by.systemIds ?? [];
  if (!a3 && systems.length === 0) return [];
  return payload.records.filter((r) => {
    if (r.record_kind !== "disruption") return false;
    if (a3 && (r.country_a3 === a3 || (r.countries_a3 ?? []).includes(a3))) return true;
    if (systems.length === 0) return false;
    if (r.system_id && systems.includes(r.system_id)) return true;
    return (r.countries ?? []).some((c) => c.system_id != null && systems.includes(c.system_id));
  });
}
