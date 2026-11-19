/** The regional overview's impact evidence, worked out apart from the view (iteration 22).
 *
 *  Pure functions over the served impact layer, so the Python tests run them in Node as they ship.
 *
 *  WHAT IS DELIBERATELY ABSENT. Nothing here groups, counts or orders records by country. The
 *  records of the group's members are one list in the served order (event date, newest first); the
 *  filters are date, cause, sector and evidence confidence, and there is no country filter, because
 *  a filter's option counts would be a per-country tally of an attack campaign set side by side.
 *  Services are listed in the vocabulary's order, never by how many records name them.
 */
import { impactsFor } from "./impacts/load";
import {
  NOT_ASSESSED, NOT_ASSESSED_LABEL, confidenceBucket, confidenceLabel, endDay, impactDateText, isCyber, isItFailure, placeText, serviceLine, startDay,
  type ServiceLine,
} from "./impacts/model";
import type { ContextEntry, ImpactRecord, ImpactsPayload, RegionalContext, VocabEntry } from "./impacts/types";
import { optionsPresent, type FilterDef, type FilterOption } from "./recordFilters";

/** The group's disruptions: every record of a member system, in the served order. */
export function groupRecords(payload: ImpactsPayload, members: readonly string[]): ImpactRecord[] {
  return impactsFor(payload, { systemIds: members });
}

/** Documented attempts with no reported service disruption, for the same members. Listed apart
 *  under their own label and never counted with the disruptions. */
export function groupAttempts(payload: ImpactsPayload, members: readonly string[]): ImpactRecord[] {
  return (payload.attempts ?? []).filter((r) => (r.system_id != null && members.includes(r.system_id))
    || (r.countries ?? []).some((c) => c.system_id != null && members.includes(c.system_id)));
}

export const IT_FAILURE = "it_failure";

const options = (v: readonly VocabEntry[] | undefined): FilterOption[] => (v ?? []).map((e) => ({ value: String(e.id), label: e.label }));

export interface GroupFilters {
  defs: FilterDef<ImpactRecord>[];
  /** In place of a filter that has one possible value: what that value is. */
  fixed: string[];
}

/** The filters over the group's records. A filter appears only when it could narrow the list. */
export function groupImpactFilters(records: readonly ImpactRecord[], vocab: ImpactsPayload["vocabularies"]): GroupFilters {
  const defs: FilterDef<ImpactRecord>[] = [
    { kind: "date", id: "date", label: "Date", start: startDay, end: endDay },
  ];
  const fixed: string[] = [];
  const add = (id: string, label: string, all: FilterOption[], values: (r: ImpactRecord) => string[], one: (o: FilterOption) => string) => {
    const present = optionsPresent(all, records, values);
    if (present.length > 1) defs.push({ kind: "choice", id, label, options: present, values });
    else if (present.length === 1) fixed.push(one(present[0]));
  };
  // An IT failure keeps its cause family and is also its own choice. It is never under "Cyber":
  // cyber means a malicious act through computer systems (methodology §4).
  const itLabel = (vocab.digital_categories ?? []).find((d) => d.id === IT_FAILURE)?.label ?? "IT failure";
  add("cause", "Cause", [...options(vocab.cause_families), { value: IT_FAILURE, label: `${itLabel} (not an attack)` }],
    (r) => (isItFailure(r) ? [r.cause_family, IT_FAILURE] : [r.cause_family]),
    (o) => `All records have one reported cause: ${o.label}.`);
  add("sector", "Service or sector", options(vocab.sectors), (r) => [r.sector],
    (o) => `All records concern one sector: ${o.label}.`);
  // The categories these records carry, by their served labels in name order, then "Not assessed":
  // its own choice, last, and never folded into the lowest category.
  const categories: FilterOption[] = [];
  for (const r of records) {
    const c = r.evidence_confidence;
    if (c && c.category && !categories.some((o) => o.value === c.category)) categories.push({ value: c.category, label: confidenceLabel(c) });
  }
  categories.sort((a, b) => a.label.localeCompare(b.label, "en"));
  categories.push({ value: NOT_ASSESSED, label: NOT_ASSESSED_LABEL });
  add("confidence", "Evidence confidence", categories, (r) => [confidenceBucket(r.evidence_confidence)],
    (o) => `All records have one evidence confidence: ${o.label}.`);
  return { defs, fixed };
}

type Confidence = { category?: string | null; label?: string | null; reason?: string | null } | null | undefined;

/** The record's evidence confidence in words, for a compact line: the served label, or "not
 *  assessed" with the build's own reason. A record that was not assessed is its own state (the
 *  shared model's NOT_ASSESSED bucket); it is not the lowest category and is never worded as one. */
export function confidenceWord(r: { evidence_confidence?: Confidence }): string {
  const c = r.evidence_confidence;
  if (c?.category) return confidenceLabel(c);
  return c?.reason ? `${NOT_ASSESSED_LABEL.toLowerCase()} (${c.reason.replace(/\.$/, "")})` : NOT_ASSESSED_LABEL.toLowerCase();
}

// ---- a link to one record -------------------------------------------------------------------------

const ANCHOR = "impact-";

/** The id of a record's card on the page, and so the fragment that links to it. */
export function impactAnchor(impactId: string): string {
  return `${ANCHOR}${impactId}`;
}

/** The record a fragment names, or null. */
export function recordFromAnchor(hash: string): string | null {
  let h = hash.startsWith("#") ? hash.slice(1) : hash;
  try { h = decodeURIComponent(h); } catch { /* not a record link */ }
  return h.startsWith(ANCHOR) && h.length > ANCHOR.length ? h.slice(ANCHOR.length) : null;
}

/** What a record's cause is called beside a service line: one word for cyber, one for an IT
 *  failure, otherwise the served cause label. */
export function causeWord(r: ImpactRecord, causeLabels: readonly VocabEntry[] | undefined, itLabel = "IT failure"): string {
  if (isItFailure(r)) return `${itLabel} (not an attack)`;
  return (causeLabels ?? []).find((c) => c.id === r.cause_family)?.label ?? r.cause_family.replace(/_/g, " ");
}

export interface ServiceRow {
  key: string;
  /** The date as the sources give it, and the place at the precision the record publishes. */
  when: string;
  place: string;
  cause: string;
  /** The effect in the source's own unit and words; nothing converted. */
  line: ServiceLine;
}

export interface ServiceGroup { service: string; label: string; rows: ServiceRow[] }

/** Documented effects on civilian services, grouped by the service named, in the vocabulary's
 *  order. Inside a group the rows keep the served date order. A record that names two services is
 *  in both groups; that is why no total is made across groups. */
export function serviceGroups(records: readonly ImpactRecord[], vocab: ImpactsPayload["vocabularies"]): ServiceGroup[] {
  const itLabel = (vocab.digital_categories ?? []).find((d) => d.id === IT_FAILURE)?.label ?? "IT failure";
  const by = new Map<string, ServiceRow[]>();
  for (const r of records) {
    r.civilian_service_impact.forEach((s, i) => {
      const rows = by.get(s.service) ?? [];
      rows.push({ key: `${r.impact_id}:${i}`, when: impactDateText(r), place: placeText(r), cause: causeWord(r, vocab.cause_families, itLabel), line: serviceLine(s) });
      by.set(s.service, rows);
    });
  }
  const sectors = vocab.sectors ?? [];
  const known = sectors.filter((v) => by.has(String(v.id))).map((v) => ({ service: String(v.id), label: v.label, rows: by.get(String(v.id))! }));
  const unknown = [...by.keys()].filter((k) => !sectors.some((v) => String(v.id) === k))
    .map((k) => ({ service: k, label: k.replace(/_/g, " "), rows: by.get(k)! }));
  return [...known, ...unknown];
}

/** Cyber records and IT failures, apart: an IT failure is not an attack and is never listed as one. */
export function digitalSplit(records: readonly ImpactRecord[]): { cyber: ImpactRecord[]; itFailures: ImpactRecord[] } {
  return { cyber: records.filter(isCyber), itFailures: records.filter(isItFailure) };
}

// ---- regional context ---------------------------------------------------------------------------

/** The kinds of statement the context actually holds, in the served order. */
export function contextTypesPresent(ctx: RegionalContext): VocabEntry[] {
  return ctx.context_types.filter((t) => ctx.entries.some((e) => e.context_type === String(t.id)));
}

/** The context narrowed to the chosen kinds of statement; none chosen means all. Each entry is
 *  passed through untouched: its date, its sources and whether it is the newest of its kind are the
 *  build's, and a filter must not turn an older statement into the latest one. */
export function filterContext(ctx: RegionalContext, types: readonly string[]): RegionalContext {
  if (types.length === 0) return ctx;
  const entries: ContextEntry[] = ctx.entries.filter((e) => types.includes(e.context_type));
  return { ...ctx, entries };
}
