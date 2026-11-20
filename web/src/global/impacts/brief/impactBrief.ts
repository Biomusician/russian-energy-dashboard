/** The text of an impact brief (iteration 22): the Gulf group's, and any one country's.
 *
 *  A brief is an image that is forwarded without the page around it, so everything the page says to
 *  stop a misreading has to be in the image, and nothing the page withholds may reach it.
 *
 *  HOW THE SECOND HALF IS KEPT. The compositor is handed a `BriefRecord`, not a record. A
 *  `BriefRecord` has four fields: the reported cause, whether the record is an IT failure, the
 *  services with a documented effect, and the evidence-confidence category. It has no place, no
 *  region, no summary, no source, no actor and no country, so a withheld place cannot be drawn: it
 *  never arrives. The Gulf brief's tally is made from those four fields alone, which is also why
 *  it cannot carry a per-country figure.
 *
 *  EVIDENCE CONFIDENCE is a category in words, from the served method. A record the build did not
 *  assess is "Not assessed", its own bucket, never the lowest category. No score is drawn: not as
 *  a number out of a hundred and not as a percentage, because it is neither a probability nor a grade.
 *
 *  No React and no DOM here: the Python tests and vitest read these lines exactly as they ship, and
 *  `drawImpactBrief.ts` only places them.
 */
import { IT_OUTAGE, NOT_ASSESSED as NOT_ASSESSED_ID, NOT_ASSESSED_LABEL, confidenceLabel } from "../model";
import { CONFIDENCE_IS_NOT } from "../../countryCopy";
import { latestCounts, latestEntries } from "../latestOfType";

/** The fields of a served impact record a brief reads. Structural, so the served type satisfies it. */
export interface BriefSourceRecord {
  cause_family: string;
  cyber_mechanism?: string | null;
  civilian_service_impact?: readonly { service: string }[] | null;
  /** `category` null (with the build's reason) is a record that was not assessed. */
  evidence_confidence?: { category?: string | null; label?: string | null } | null;
}

/** Everything a brief knows about one record. See the header: this narrowness is the safeguard. */
export interface BriefRecord {
  cause: string;
  itFailure: boolean;
  services: string[];
  /** The served category and its served label; null when the build did not assess the record. */
  confidence: { id: string; label: string } | null;
}

export function briefRecords(records: readonly BriefSourceRecord[]): BriefRecord[] {
  return records.map((r) => ({
    cause: r.cause_family,
    // The shared rule (model.ts, methodology §4): digitally triggered without malice. Never "cyber".
    itFailure: r.cause_family !== "cyber" && r.cyber_mechanism === IT_OUTAGE,
    services: [...new Set((r.civilian_service_impact ?? []).map((x) => x.service))],
    confidence: r.evidence_confidence?.category
      ? { id: r.evidence_confidence.category, label: confidenceLabel(r.evidence_confidence) }
      : null,
  }));
}

/** A key in plain words, for a key no served vocabulary names: "authority_order" reads "Authority order". */
function plain(id: string): string {
  const s = id.replace(/_/g, " ").toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

interface Labelled { id: string; label: string }

/** The served vocabularies a brief labels its tally with. Labels are data, never typed in here. */
export interface BriefVocabularies {
  cause_families: readonly Labelled[];
  sectors: readonly Labelled[];
  digital_categories?: readonly Labelled[];
  /** The served method's categories, in its own order. Without it the categories are listed by name. */
  confidence?: readonly Labelled[];
}

export interface TallyRow { id: string; label: string; n: number }
export interface ImpactTally { total: number; byCause: TallyRow[]; byService: TallyRow[]; byConfidence: TallyRow[] }

const IT_FAILURE = "it_failure";
/** The shared model's bucket for a record the build did not assess. */
export const NOT_ASSESSED = { id: NOT_ASSESSED_ID, label: NOT_ASSESSED_LABEL } as const;

/** Published records by reported cause and by service, in the VOCABULARY's order. Never ordered by
 *  the count: a list sorted by a figure is a ranking of causes. An IT failure is counted apart from
 *  its cause family and never under "cyber" (methodology §4), so the cause rows add up to the total. */
export function tallyImpacts(records: readonly BriefRecord[], vocab: BriefVocabularies): ImpactTally {
  const cause = new Map<string, number>();
  const service = new Map<string, number>();
  for (const r of records) {
    const key = r.itFailure ? IT_FAILURE : r.cause;
    cause.set(key, (cause.get(key) ?? 0) + 1);
    for (const s of r.services) service.set(s, (service.get(s) ?? 0) + 1);
  }
  // Evidence confidence: the served categories in the method's order (by name without it), then
  // "Not assessed" last. Never by count, and "Not assessed" is never merged into a category.
  const assessed = new Map<string, { label: string; n: number }>();
  let notAssessed = 0;
  for (const r of records) {
    if (!r.confidence) { notAssessed += 1; continue; }
    const row = assessed.get(r.confidence.id) ?? { label: r.confidence.label, n: 0 };
    row.n += 1;
    assessed.set(r.confidence.id, row);
  }
  const order = vocab.confidence
    ? [...vocab.confidence.map((c) => c.id).filter((id) => assessed.has(id)), ...[...assessed.keys()].filter((id) => !vocab.confidence!.some((c) => c.id === id))]
    : [...assessed.keys()].sort((a, b) => assessed.get(a)!.label.localeCompare(assessed.get(b)!.label, "en"));
  const byConfidence: TallyRow[] = order.map((id) => ({ id, label: vocab.confidence?.find((c) => c.id === id)?.label ?? assessed.get(id)!.label, n: assessed.get(id)!.n }));
  if (notAssessed > 0) byConfidence.push({ ...NOT_ASSESSED, n: notAssessed });
  const itLabel = vocab.digital_categories?.find((d) => d.id === IT_FAILURE)?.label ?? "IT failure";
  const causeVocab: Labelled[] = [...vocab.cause_families, { id: IT_FAILURE, label: `${itLabel} (not an attack)` }];
  const rows = (vocabulary: readonly Labelled[], counts: Map<string, number>): TallyRow[] => {
    const out = vocabulary.filter((v) => counts.has(v.id)).map((v) => ({ id: v.id, label: v.label, n: counts.get(v.id)! }));
    // A value the vocabulary does not have is still a published record: listed last under its own id.
    for (const [id, n] of counts) if (!vocabulary.some((v) => v.id === id)) out.push({ id, label: plain(id), n });
    return out;
  };
  return { total: records.length, byCause: rows(causeVocab, cause), byService: rows(vocab.sectors, service), byConfidence };
}

// ---- regional context statements ------------------------------------------------------------------

export interface BriefMetric { value: number | null; value_upper?: number | null; qualifier?: string | null; unit: string | null; basis?: string | null }

/** The fields of a served regional-context entry a brief reads. */
export interface BriefSourceEntry {
  id?: string;
  as_of: string;
  context_type: string;
  claim: string;
  metric?: BriefMetric | null;
  sources: readonly { publisher: string | null }[];
  is_latest_of_type?: boolean;
}

/** `ofType`: how many of the type's newest statements the brief carries (more than one when
 *  several share the newest date; all of them are carried, never one picked). */
export interface BriefStatement { asOf: string; type: string; claim: string; figure: string | null; source: string; ofType?: number }

const QUALIFIER_WORDS: Record<string, string> = { about: "about ", at_least: "at least ", at_most: "up to " };

const num = (v: number) => v.toLocaleString("en-GB", { maximumFractionDigits: 2 });

/** A statement's figure in the source's own unit, with what it measures. Nothing is converted.
 *  The same words as the page's timeline (ContextTimeline.metricText), written out here so the
 *  image does not depend on which vocabulary a page happened to load. */
export function metricText(m: BriefMetric): string | null {
  if (m.value == null) return null;
  const value = m.qualifier === "range" && m.value_upper != null
    ? `between ${num(m.value)} and ${num(m.value_upper)}`
    : `${QUALIFIER_WORDS[m.qualifier ?? ""] ?? ""}${num(m.value)}`;
  return `${value}${m.unit ? ` ${m.unit}` : ""}${m.basis ? ` (${m.basis})` : ""}`;
}

export const MAX_BRIEF_STATEMENTS = 5;

/** "19 Nov 2026" from a calendar day, or from a build timestamp, of which only the day is shown. */
function isoDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:T.*)?$/.exec(iso);
  if (!m) return iso;
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${Number(m[3])} ${months[Number(m[2]) - 1] ?? m[2]} ${m[1]}`;
}

/** The newest statements of each type, newest first, at most five. A brief is a snapshot: it carries
 *  the most recent statements on record for a type with their date, never an older one beside them
 *  and never a status. Where several statements of a type share the newest date, all of them are
 *  carried or none: a type that does not fit whole is left out rather than cut to an arbitrary one.
 *  `latestByType` is the served map; without it the latest are read from the entries. */
export function briefStatements(entries: readonly BriefSourceEntry[], typeLabels: readonly Labelled[], latestByType?: unknown): BriefStatement[] {
  const label = (id: string) => typeLabels.find((t) => t.id === id)?.label ?? id;
  const latest = latestEntries(entries, latestByType);
  const counts = latestCounts(entries, latest);
  const seen = new Set<string>();
  const out: BriefStatement[] = [];
  const newestFirst = [...entries].sort((a, b) => (a.as_of < b.as_of ? 1 : a.as_of > b.as_of ? -1 : 0));
  for (const e of newestFirst) {
    if (seen.has(e.context_type)) continue;
    seen.add(e.context_type);
    const group = newestFirst.filter((x) => x.context_type === e.context_type && latest.has(x));
    if (group.length === 0 || out.length + group.length > MAX_BRIEF_STATEMENTS) continue;
    for (const x of group) {
      out.push({
        asOf: x.as_of,
        type: label(x.context_type),
        claim: x.claim,
        figure: x.metric ? metricText(x.metric) : null,
        source: [...new Set(x.sources.map((s) => s.publisher).filter(Boolean))].join("; ") || "source not stated",
        ofType: counts.get(x.context_type) ?? 1,
      });
    }
    if (out.length >= MAX_BRIEF_STATEMENTS) break;
  }
  return out;
}

// ---- the brief ------------------------------------------------------------------------------------

export interface BriefLine { text: string; dim?: boolean; strong?: boolean }
export interface BriefBlock { heading: string; lines: BriefLine[] }
export interface ImpactBrief {
  title: string;
  sub: string;
  /** Two columns of blocks, each read top to bottom. */
  columns: [BriefBlock[], BriefBlock[]];
  /** The band at the foot. Drawn in full on every brief; never wrapped away or shortened. */
  caveats: string[];
}

/** The impact layer as a brief receives it. "unavailable" is a failed download: it is said in
 *  words and is never drawn as "no records", which would be a finding. */
export type BriefImpacts = "unavailable" | {
  records: BriefRecord[];
  vocab: BriefVocabularies;
  /** The research window, when the payload states one. */
  window: { start: string; end: string } | null;
  limitations: string[];
  latestResearch: string | null;
};

export interface BriefConfidence {
  statement: string;
  categories: readonly { label: string; meaning: string }[];
  /** Set when the served method says its categories are provisional: what it says after the word
   *  ("thresholds not calibrated"), or "" when it says no more. The brief then says so in a line. */
  provisional?: string | null;
}

/** "provisional: thresholds not calibrated" -> "thresholds not calibrated"; any other status -> null. */
export function provisionalNote(status: string | null | undefined): string | null {
  const m = /^\s*provisional\b[\s:,;-]*(.*)$/i.exec(status ?? "");
  return m ? m[1].trim() : null;
}

/** The three sentences every Gulf brief ends with. Each is its own line so none can ride on another. */
export const GULF_BRIEF_CAVEATS = [
  "Aggregate regional context only: no facilities, no routes, no vessels.",
  "Event counts are published records in this corpus. They are not comparable across countries, and nothing here ranks a country.",
  "The later status of attacked facilities is not published.",
] as const;

export const COUNTRY_BRIEF_CAVEATS = [
  "Counts are published records inside this country, in this corpus: not a rate, and not comparable with any other country.",
  "No facility, route or vessel, and nothing finer than a first-level region. An attack is published for the country only, without place, operator, method or later status.",
] as const;

const SIGN = "Energy Disruption Monitor · open sources only";

function windowText(w: { start: string; end: string } | null): string | null {
  if (!w) return null;
  return `${isoDate(w.start)} to ${w.end === "present" ? "the present" : isoDate(w.end)}`;
}

function tallyLines(t: ImpactTally): BriefLine[] {
  const out: BriefLine[] = [];
  out.push({ text: "By reported cause (one per record; vocabulary order, not an order of size):", dim: true });
  out.push({ text: t.byCause.map((r) => `${r.label} ${r.n}`).join(" · ") });
  if (t.byService.length) {
    out.push({ text: "By service with a documented effect (a record can name more than one):", dim: true });
    out.push({ text: t.byService.map((r) => `${r.label} ${r.n}`).join(" · ") });
  } else {
    out.push({ text: "No record documents an effect on a named service.", dim: true });
  }
  out.push({ text: "By evidence confidence (the quality of the public evidence: not severity, not a probability):", dim: true });
  out.push({ text: t.byConfidence.map((r) => `${r.label} ${r.n}`).join(" · ") });
  return out;
}

function statementLines(statements: readonly BriefStatement[]): BriefLine[] {
  const out: BriefLine[] = [];
  for (const s of statements) {
    out.push({ text: `As of ${isoDate(s.asOf)} · ${s.type}`, strong: true });
    out.push({ text: s.figure ? `${s.claim} Figure: ${s.figure}.` : s.claim });
    out.push({ text: `Source: ${s.source}`, dim: true });
  }
  return out;
}

/** The line under the Gulf brief's statements. Plural where a type carries more than one newest
 *  statement: "the most recent statement" over two statements would pick one in words. */
export function statementsNote(statements: readonly BriefStatement[]): string {
  const tie = statements.some((s) => (s.ofType ?? 1) > 1);
  const recent = tie
    ? "the most recent on record for its type (where several statements of a type share the newest date, all of them are shown)"
    : "the most recent on record for its type";
  return `Each statement is as of its own date: ${recent}, not a current status. No open or closed status is published. A market movement is not an infrastructure loss.`;
}

function confidenceBlock(c: BriefConfidence | null): BriefBlock {
  return {
    heading: "Evidence confidence",
    lines: c
      ? [{ text: c.statement },
         ...(c.provisional != null ? [{ text: `The categories are provisional${c.provisional ? `: ${c.provisional}` : ""}.`, strong: true }] : []),
         ...c.categories.map((k) => ({ text: `${k.label}: ${k.meaning}`, dim: true })),
         { text: `${NOT_ASSESSED.label}: the build could not assess the record's evidence. It is not the lowest category.`, dim: true }]
      // The sentence that must travel even when the method file did not load.
      : [{ text: CONFIDENCE_IS_NOT }],
  };
}

function limitLines(impacts: BriefImpacts): BriefLine[] {
  if (impacts === "unavailable") return [{ text: "The impact layer's research notes could not be loaded when this brief was made.", dim: true }];
  const out: BriefLine[] = impacts.limitations.slice(0, 4).map((text) => ({ text }));
  out.push({ text: "Not a census: disclosure rules and reporting differ by country, so an absent record is not an absent disruption.", dim: true });
  if (impacts.latestResearch) out.push({ text: `Latest research on the impact layer: ${isoDate(impacts.latestResearch)}.`, dim: true });
  return out;
}

export interface GulfBriefInput {
  /** The group's label and its members' national figures for one metric, as the page shows them. */
  group: { label: string; members: number };
  energy: {
    label: string; unit: string; year: number; source: string;
    /** Alphabetical, as served. A national energy total with its unit: context, never a disruption figure. */
    rows: { name: string; value: string }[];
    total: string | null;
    totalReason: string | null;
  };
  impacts: BriefImpacts;
  /** null: the context file could not be loaded. */
  statements: BriefStatement[] | null;
  confidence: BriefConfidence | null;
  buildDate: string;
}

/** The Gulf impact brief: one page about the group as a whole. */
export function gulfImpactBrief(x: GulfBriefInput): ImpactBrief {
  const impacts = x.impacts;
  const window = impacts === "unavailable" ? null : windowText(impacts.window);
  const evidence: BriefLine[] = [];
  if (impacts === "unavailable") {
    evidence.push({ text: "The impact records could not be loaded when this brief was made. That is a failed download, not a finding." });
  } else if (impacts.records.length === 0) {
    evidence.push({ text: `No published impact record for these ${x.group.members} countries in the current reviewed corpus. That describes this dataset, not the region.` });
  } else {
    const t = tallyImpacts(impacts.records, impacts.vocab);
    evidence.push({ text: `${t.total} published ${t.total === 1 ? "record" : "records"} for the ${x.group.members} countries together${window ? `, ${window}` : ""}.`, strong: true });
    evidence.push(...tallyLines(t));
  }
  evidence.push({ text: "Reviewed records from a separate corpus that is not scored. Published records, not incidents that occurred.", dim: true });

  const context: BriefLine[] = x.statements == null
    ? [{ text: "The regional context statements could not be loaded when this brief was made." }]
    : x.statements.length === 0
      ? [{ text: "No reviewed regional context statement has been published yet." }]
      : statementLines(x.statements);
  context.push({ text: statementsNote(x.statements ?? []), dim: true });

  return {
    title: `${x.group.label}: reported impacts and regional context`,
    sub: `No index or score. Built ${isoDate(x.buildDate)}.${window ? ` Evidence window ${window}.` : ""} Reviewed public reporting only.`,
    columns: [
      [
        {
          heading: `National energy context: ${x.energy.label}, ${x.energy.year}`,
          lines: [
            { text: `${x.energy.unit}. National annual totals, alphabetical. ${x.energy.source}.`, dim: true },
            ...x.energy.rows.map((r) => ({ text: `${r.name}: ${r.value}` })),
            { text: x.energy.total != null ? `All ${x.group.members} together: ${x.energy.total}.` : `Not summed: ${x.energy.totalReason ?? "a member has no figure"}.` },
            { text: "The size of each national energy system, for context. It is not a measure of disruption, importance or exposure.", dim: true },
          ],
        },
        { heading: "Published impact evidence: the group as a whole", lines: evidence },
      ],
      [
        { heading: "Gulf and Strait of Hormuz: dated statements", lines: context },
        confidenceBlock(x.confidence),
        { heading: "Research limits", lines: limitLines(impacts) },
      ],
    ],
    caveats: [...GULF_BRIEF_CAVEATS, SIGN],
  };
}

export interface CountryBriefInput {
  name: string;
  buildDate: string;
  /** One national figure with its year and source, or null when the context layer has none. */
  national: { label: string; value: string; year: number; source: string } | null;
  /** The country system's own reviewed energy record; null when the country is not a monitored system. */
  system: {
    energyEvents: number;
    reportingEnvironment: string;
    /** One line on how far the search got, from the country's research log. */
    coverage: string | null;
    /** The campaign caveat the country page carries, or null where none applies. */
    campaignLine: string | null;
  } | null;
  /** Impact records INSIDE this country. */
  impacts: BriefImpacts;
  /** Regional context, only for a system in the group the context describes. */
  regional: { label: string; statements: BriefStatement[] } | null;
  confidence: BriefConfidence | null;
}

const inSentence = (name: string) => (/^United /.test(name) ? `the ${name}` : name);

/** A country's impact brief. Meaningful when every count is zero: an empty record is a statement
 *  about this dataset, and the brief says so in those words. */
export function countryImpactBrief(x: CountryBriefInput): ImpactBrief {
  const where = inSentence(x.name);
  const impacts = x.impacts;
  const window = impacts === "unavailable" ? null : windowText(impacts.window);

  const energy: BriefLine[] = [];
  if (!x.system) {
    energy.push({ text: `${x.name} is not a monitored system on this site: its energy disruptions have not been searched systematically, so there is no country record, and none is implied.` });
  } else if (x.system.energyEvents === 0) {
    energy.push({ text: `No published energy disruption record. That describes this dataset, not ${where}.`, strong: true });
    energy.push({ text: `Reporting environment: ${x.system.reportingEnvironment}.`, dim: true });
  } else {
    energy.push({ text: `${x.system.energyEvents} published energy disruption ${x.system.energyEvents === 1 ? "record" : "records"} in this country's reviewed record (reporting: ${x.system.reportingEnvironment}).`, strong: true });
    energy.push({ text: "What was reported and found, not a rate of disruption.", dim: true });
  }

  const evidence: BriefLine[] = [];
  if (impacts === "unavailable") {
    evidence.push({ text: "The impact records could not be loaded when this brief was made. That is a failed download, not a finding." });
  } else if (impacts.records.length === 0) {
    evidence.push({ text: `No published impact record for ${where} in the current reviewed corpus. That describes this dataset, not ${where}.` });
  } else {
    const t = tallyImpacts(impacts.records, impacts.vocab);
    evidence.push({ text: `${t.total} published ${t.total === 1 ? "record" : "records"} inside ${where}${window ? `, ${window}` : ""}.`, strong: true });
    evidence.push(...tallyLines(t));
  }
  evidence.push({ text: "Reviewed records from a separate corpus that is not scored: they enter no index and not the country's energy record above.", dim: true });

  const right: BriefBlock[] = [];
  if (x.regional) {
    const lines = x.regional.statements.length ? statementLines(x.regional.statements) : [{ text: "No reviewed regional context statement has been published yet." }];
    lines.push({ text: "Regional statements in aggregate, each as of its own date; none is a current status, and none is part of this country's record.", dim: true });
    right.push({ heading: `Regional context: ${x.regional.label}`, lines });
  }
  right.push(confidenceBlock(x.confidence));
  right.push({
    heading: "Research coverage",
    lines: [
      ...(x.system?.coverage ? [{ text: x.system.coverage }] : []),
      ...(!x.system ? [{ text: "No systematic research pass: this country appears through the impact layer only." }] : []),
      ...limitLines(impacts),
    ],
  });
  right.push({
    heading: "What is withheld",
    lines: [
      { text: "For an attack or sabotage record: the place, facility, operator, method, headline and any later status. For every record: coordinates and anything finer than a first-level region." },
      ...(x.system?.campaignLine ? [{ text: x.system.campaignLine }] : []),
    ],
  });

  return {
    title: `${x.name}: reported impact evidence`,
    sub: `No index or score. Built ${isoDate(x.buildDate)}.${window ? ` Evidence window ${window}.` : ""} Reviewed public reporting only.`,
    columns: [
      [
        {
          heading: "National energy context",
          lines: x.national
            ? [{ text: `${x.national.label}: ${x.national.value} (${x.national.year}, ${x.national.source}).` },
               { text: "The size of the national energy system, for context. It is not a measure of disruption, importance or exposure.", dim: true }]
            : [{ text: "No national figure in the context layer for this country. That is a missing figure, not a zero." }],
        },
        { heading: "Country system: reviewed energy record", lines: energy },
        { heading: "Reviewed impact evidence, inside this country", lines: evidence },
      ],
      right,
    ],
    caveats: [...COUNTRY_BRIEF_CAVEATS, SIGN],
  };
}

/** Every line of a brief, in reading order: what a test (or a screen reader's alternative) reads. */
export function briefText(b: ImpactBrief): string[] {
  return [b.title, b.sub,
    ...b.columns.flatMap((col) => col.flatMap((blk) => [blk.heading, ...blk.lines.map((l) => l.text)])),
    ...b.caveats];
}
