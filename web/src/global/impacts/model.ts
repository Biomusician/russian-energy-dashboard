/** What an impact record says, worked out once and shown the same everywhere (iteration 22).
 *
 *  Plain functions over a served record: no React and no DOM, so the Python tests run them in Node
 *  exactly as they ship. The rules they hold (docs/GLOBAL_IMPACT_METHODOLOGY.md):
 *  - an attempt is not a disruption and is never in a timeline or a count;
 *  - "cyber" means a malicious cyber cause. A non-malicious IT failure is its own thing;
 *  - unknown attribution is "not established", never a low confidence, and "not applicable" is
 *    said by saying nothing;
 *  - AI involvement is shown only where a source reports it;
 *  - an abstracted (attack or sabotage) record shows the country and nothing finer.
 */
import { fmtDate } from "../../data";
import { isAbstractedImpact } from "../recordCsv";
import { isAbsenceWord, labelOf, lowerLabel, vocabulary } from "./vocab";
import type { AffectedFigure, AiInvolvement, Attribution, ImpactRecord, ImpactSource, ImpactsPayload, SelfClaim, ServiceImpact } from "./types";

export const DISRUPTION = "disruption";
/** The one mechanism a non-malicious, digitally triggered failure carries (§4). */
export const IT_OUTAGE = "it_outage_affecting_operations";

const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;

/** The disruptions of a payload, in the served order. A record of any other kind that reached the
 *  list is left out: only a disruption is ever in a timeline or a count. */
export function disruptions(payload: ImpactsPayload): ImpactRecord[] {
  return payload.records.filter((r) => r.record_kind === DISRUPTION);
}

/** The documented attempts: listed apart, never counted. */
export function attempts(payload: ImpactsPayload): ImpactRecord[] {
  return [...(payload.attempts ?? []), ...payload.records.filter((r) => r.record_kind !== DISRUPTION)];
}

/** A malicious cyber cause. An IT failure (industrial_technical with an IT-outage mechanism) is
 *  not one, and a contributing factor does not make a record cyber. */
export function isCyber(r: ImpactRecord): boolean {
  return r.cause_family === "cyber";
}

/** Digitally triggered without malice: a faulty update, an IT system failure that stopped operations. */
export function isItFailure(r: ImpactRecord): boolean {
  return r.cause_family !== "cyber" && r.cyber_mechanism === IT_OUTAGE;
}

export function aiReported(ai: AiInvolvement | null | undefined): boolean {
  return !!ai && !!ai.status && ai.status !== "NONE_REPORTED";
}

/** Somebody is named: claimed, suspected, assessed, attributed or disputed. Unknown is not. */
export function hasAttribution(a: Attribution | null | undefined): boolean {
  return !!a && a.status !== "NOT_APPLICABLE" && a.status !== "UNKNOWN";
}

export function isAbstracted(r: ImpactRecord): boolean {
  return isAbstractedImpact(r);
}

// ---- evidence confidence -------------------------------------------------------------------------

/** The bucket for a record whose evidence was not assessed (a null category). Its own bucket in
 *  filters and counts: never folded into the lowest category. */
export const NOT_ASSESSED = "NOT_ASSESSED";
export const NOT_ASSESSED_LABEL = "Not assessed";
/** Said where a record carries no confidence at all and so no served reason. */
export const NO_CONFIDENCE_REASON = "No evidence confidence is published for this record.";

interface ConfidenceLike { category?: string | null; label?: string | null }

/** The filter and count bucket of a confidence: its category, or NOT_ASSESSED. */
export function confidenceBucket(c: ConfidenceLike | null | undefined): string {
  return c?.category ?? NOT_ASSESSED;
}

/** The words for a confidence: the served label, or "Not assessed". Never empty. */
export function confidenceLabel(c: ConfidenceLike | null | undefined): string {
  if (!c || c.category == null) return NOT_ASSESSED_LABEL;
  return c.label || c.category.replace(/_/g, " ").toLowerCase().replace(/^./, (ch) => ch.toUpperCase());
}

/** What the origins figure counts, by its served basis. Where only publishers were counted the
 *  line says so: whether they relay one statement was not reviewed, so they are not called
 *  independent. A build with no basis gets the bare number and no claim about what it counts. */
export function originsText(count: number, basis: string | null | undefined): string {
  if (basis === "publishers") return `${count} distinct ${count === 1 ? "publisher" : "publishers"} cited; whether they relay one statement was not reviewed`;
  if (basis === "reviewed") return `${count} originating ${count === 1 ? "statement" : "statements"}, as established on review`;
  return String(count);
}

// ---- dates ---------------------------------------------------------------------------------------

/** The first calendar day the record can refer to: a month-precision date starts on the 1st. */
export function startDay(r: ImpactRecord): string {
  if (ISO_DAY.test(r.date)) return r.date;
  if (/^\d{4}-\d{2}$/.test(r.date)) return `${r.date}-01`;
  return `${r.date.slice(0, 4)}-01-01`;
}

/** The last calendar day the record can refer to. A month-precision record spans its month. */
export function endDay(r: ImpactRecord): string {
  if (r.date_end && ISO_DAY.test(r.date_end)) return r.date_end;
  if (ISO_DAY.test(r.date)) return r.date;
  if (/^\d{4}-\d{2}$/.test(r.date)) {
    const [y, m] = r.date.split("-").map(Number);
    return `${r.date}-${String(new Date(Date.UTC(y, m, 0)).getUTCDate()).padStart(2, "0")}`;
  }
  return `${r.date.slice(0, 4)}-12-31`;
}

/** The date as the sources give it: a month-precision date is shown as a month, never as a day. */
export function impactDateText(r: ImpactRecord): string {
  const start = r.date_precision === "month" ? fmtDate(r.date.slice(0, 7)) : r.date_precision === "year" ? r.date.slice(0, 4) : fmtDate(r.date);
  return r.date_end && ISO_DAY.test(r.date_end) && r.date_end !== r.date ? `${start} – ${fmtDate(r.date_end)}` : start;
}

function daysBetween(from: string, to: string): number {
  return Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86400000);
}

/** The event predates its first publication here by more than 30 days: the card says the record
 *  was added later, so later knowledge is never read as contemporaneous. */
export function isHistoricalAddition(r: ImpactRecord): boolean {
  if (!r.first_published || !ISO_DAY.test(r.first_published)) return false;
  return daysBetween(endDay(r), r.first_published) > 30;
}

/** "2026-05" -> "May 2026", for the timeline's month headings. */
export function monthHeading(ym: string): string {
  const names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const [y, m] = ym.split("-");
  return `${names[Number(m) - 1] ?? m} ${y}`;
}

// ---- place ---------------------------------------------------------------------------------------

/** Where the record is placed, in words. An abstracted record is its country and nothing finer,
 *  whatever the record carries. */
export function placeText(r: ImpactRecord): string {
  if (r.country_a3 === "MULTI" && r.countries && r.countries.length > 0) return r.countries.map((c) => c.name).join(", ");
  if (!isAbstracted(r) && r.admin1?.name) return `${r.admin1.name}, ${r.country_name}`;
  return r.country_name;
}

/** Every country code the record belongs to (a multi-country record has several). */
export function countryCodes(r: ImpactRecord): string[] {
  return r.country_a3 === "MULTI" ? [...(r.countries_a3 ?? [])] : [r.country_a3];
}

// ---- civilian-service impact ---------------------------------------------------------------------

export interface ServiceLine { service: string; scope: string; affected: string | null; unitNote: string | null; duration: string | null }

function affectedText(a: AffectedFigure | string | null): { text: string | null; unitNote: string | null } {
  if (a == null) return { text: null, unitNote: null };
  if (typeof a === "string") return { text: isAbsenceWord(a) ? lowerLabel("absence_words", a) : a, unitNote: null };
  // The source's own words carry its own unit and its own qualifier. Nothing is recomputed.
  const text = a.source_says ?? (a.value != null ? `${a.value.toLocaleString("en-GB")}${a.unit ? ` ${a.unit}` : ""}` : null);
  return { text, unitNote: a.value != null && a.unit ? `the source counts ${a.unit}` : null };
}

/** One civilian-service impact as the card shows it. The figure keeps the source's own unit. */
export function serviceLine(s: ServiceImpact): ServiceLine {
  const { text, unitNote } = affectedText(s.affected);
  const d = s.duration_text;
  return {
    service: labelOf("sectors", s.service),
    scope: labelOf("geographic_scopes", s.geographic_scope),
    affected: text,
    unitNote,
    duration: d == null ? null : isAbsenceWord(d) ? lowerLabel("absence_words", d) : d,
  };
}

// ---- attribution and AI, in words ---------------------------------------------------------------

/** "a government and a cyber security firm", from the served basis labels. */
export function basisText(basis: readonly string[] | null | undefined): string {
  const words = (basis ?? []).map((b) => lowerLabel("attribution_bases", b));
  if (words.length <= 1) return words[0] ?? "";
  return `${words.slice(0, -1).join(", ")} and ${words[words.length - 1]}`;
}

/** The label for an attribution confidence. UNKNOWN attribution has none to show: its confidence
 *  key is NOT_ESTABLISHED, which is not a point on the low-to-high scale. */
export function attributionConfidenceLabel(a: Attribution, labels: Record<string, string> | null | undefined): string | null {
  if (!a.confidence || a.status === "UNKNOWN" || a.status === "NOT_APPLICABLE" || a.confidence === "NOT_ESTABLISHED") return null;
  const served = labels && Object.prototype.hasOwnProperty.call(labels, a.confidence) ? labels[a.confidence] : null;
  return served ?? a.confidence.replace(/_/g, " ").toLowerCase().replace(/^./, (c) => c.toUpperCase());
}

// ---- the evidence chain --------------------------------------------------------------------------

export interface ClaimSupport { claim: string; label: string; sources: ImpactSource[] }

/** For each claim the record's sources support, which sources support it, in the served order of
 *  claims: so a reader sees an operator's notice under "that it happened" and a cyber firm's report
 *  under "attribution", not one undifferentiated list of links. */
export function claimSupport(r: ImpactRecord, claimOrder: readonly string[]): ClaimSupport[] {
  const seen = new Set<string>();
  for (const s of r.sources) for (const c of s.supports) seen.add(c);
  const order = [...claimOrder.filter((c) => seen.has(c)), ...[...seen].filter((c) => !claimOrder.includes(c))];
  return order.map((claim) => ({ claim, label: labelOf("claims", claim), sources: r.sources.filter((s) => s.supports.includes(claim)) }));
}

/** "Operator, web page" or "Operator, social media post": who is speaking and through what. */
export function sourceKind(s: ImpactSource): string {
  return `${labelOf("source_roles", s.source_role)}, ${lowerLabel("media", s.medium)}`;
}

const MALICIOUS_FALLBACK: readonly string[] = ["kinetic", "cyber", "sabotage"];

/** Whether the record's reported cause, or a contributing factor, is a malicious kind of cause
 *  (iteration 22 closure). Read from the served cause vocabulary's `malicious` flag; where the
 *  vocabulary has not loaded, kinetic, cyber and sabotage. "unknown" and "civil disruption" are not
 *  established as malicious, so they are not. */
export function isMaliciousCause(r: Pick<ImpactRecord, "cause_family" | "contributing_factors">): boolean {
  const served = vocabulary("cause_families");
  const malicious = (id: string) => {
    const e = served.find((x) => String(x.id) === id) as { malicious?: boolean | null } | undefined;
    return e && typeof e.malicious === "boolean" ? e.malicious : MALICIOUS_FALLBACK.includes(id);
  };
  return [r.cause_family, ...(r.contributing_factors ?? [])].some(malicious);
}

/** The actors' own claims of responsibility on an attribution, as served. A malformed or absent
 *  list is no claims; an entry with neither an actor nor a statement says nothing and is dropped. */
export function selfClaimsOf(a: Attribution | null | undefined): SelfClaim[] {
  const list = a && Array.isArray(a.self_claims) ? a.self_claims : [];
  return list.filter((c): c is SelfClaim => !!c && typeof c === "object" && (!!c.statement || !!c.actor));
}

/** The sentence a self-claim is shown as, after "Self-claim (unverified):". The served statement
 *  when there is one; otherwise who claimed it, in words that say it is a claim. */
export function selfClaimText(c: SelfClaim): string {
  if (c.statement) return c.statement;
  const type = c.actor_type ? ` (${lowerLabel("actor_types", c.actor_type)})` : "";
  return `${c.actor ?? "An actor"}${type} claimed responsibility.`;
}

/** Said once under the self-claims, wherever they are shown. */
export const SELF_CLAIM_NOTE = "An actor's own claim of responsibility, recorded as provenance. "
  + "It is not an attribution, not a competing attribution, and it does not change the attribution or its confidence.";

/** What the evidence for this record does not establish. Derived from the record's own fields. */
export function notEstablished(r: ImpactRecord): string[] {
  const out: string[] = [];
  const a = r.attribution;
  if (a.status === "UNKNOWN" && !isMaliciousCause(r)) out.push("Whether the cause was malicious at all. The reported cause is not established as malicious, so there is no attribution question to answer yet.");
  else if (a.status === "UNKNOWN") out.push("Who was responsible. No credible public attribution was found; that is not the same as a low-confidence attribution.");
  else if (a.status === "CLAIMED") out.push("That the actor who claimed responsibility carried it out. A claim is not corroboration.");
  else if (a.status === "SUSPECTED") out.push("Who was responsible. A source names a likely actor without a firm attribution.");
  else if (a.status === "ASSESSED") out.push("A formal government or law-enforcement attribution. One body's assessment is reported, with its date.");
  else if (a.status === "DISPUTED") out.push("Which attribution is right. Credible sources disagree and this site does not choose between them.");
  // A self-claim beside another status: the claim is recorded, and it is still only a claim.
  if (a.status !== "CLAIMED" && selfClaimsOf(a).length > 0) {
    out.push("That an actor who claimed responsibility carried it out. A self-claim is not corroboration and is not counted as an attribution.");
  }
  if (!aiReported(r.ai_involvement)) out.push("Whether AI played any part. No source ties AI to this incident, which is not a finding that none was involved.");
  else {
    if (r.ai_involvement.status !== "CONFIRMED") out.push(`That AI was involved. It is ${lowerLabel("ai_statuses", r.ai_involvement.status)}, not confirmed.`);
    if (r.ai_involvement.relation === "ai_assisted") out.push("That AI caused the disruption. The source describes AI assisting an attacker, which is a different thing.");
  }
  if (r.effect_specificity !== "quantified") out.push("A figure for the effect. No cited source quantifies it.");
  if (r.dispute) out.push(`${labelOf("dispute_about", r.dispute.about)}: credible sources disagree, and this site does not choose.`);
  if (isAbstracted(r)) out.push("Where in the country it happened, what was affected there, or its later state. These are not published for an attack or sabotage record.");
  out.push("How severe or important the disruption was. Evidence confidence describes the evidence, not the event.");
  out.push("The state of the service today. The record describes what was reported at the time.");
  return out;
}
