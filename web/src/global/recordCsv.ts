/** Safe CSV export of the published records a reader is looking at (iteration 22).
 *
 *  WHAT IS EXPORTED. The public, published records currently shown: the caller passes the list on
 *  screen after its filters. Nothing else is read, so a record that is held in review, which is
 *  never served, cannot be exported.
 *
 *  HOW IT STAYS SAFE. A file leaves the page and travels without its caveats, so it is stricter than
 *  the page:
 *  - A fixed allow-list of columns per record kind. Each cell is built from a named field; a record
 *    is never dumped, so a field the build adds later is not exported until it is added here.
 *  - Never a coordinate, never a reviewer's reasoning or any other internal review field.
 *  - A record published under attack-campaign safeguards, or abstracted to the country, exports no
 *    place, facility, operator, source headline or later status. Those cells are EMPTY and
 *    `publication_note` says why. A record that keeps the older convention of naming its facility
 *    in its own text exports no text, id or citation either: its date, class and cause only.
 *  - RFC 4180 quoting; a cell that a spreadsheet would run as a formula is prefixed with an
 *    apostrophe; a UTF-8 byte-order mark so Excel reads Arabic and Persian.
 *
 *  The CSV is clean data and nothing else. What the columns mean, the build date, the filters in
 *  force and the limits of the corpus travel in a second file, the README, offered beside it.
 *
 *  Pure: type imports and two import-free vocabulary modules only, so the Python tests run this file
 *  in Node as it ships.
 */
import type { CountryEvent, CountrySystem } from "./manifest";
import { eventPlacement, headlinesAllowed, isOpaqueAttackId, placementKind } from "./evidence";
import { PLACEMENT_LABEL } from "./placement";

// ---- the CSV itself -----------------------------------------------------------------------------

export const CSV_BOM = "﻿";

/** One cell. A value starting with = + - @ (or a tab or carriage return, which a spreadsheet strips
 *  before looking) would be run as a formula by Excel, LibreOffice and Sheets: an apostrophe makes
 *  it text. Then RFC 4180: quote when the value holds a comma, a quote or a line break. */
export function csvCell(value: string): string {
  let s = value;
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** A CSV document: byte-order mark, header, one line per row, CRLF line ends. Only the listed
 *  columns are written, whatever else a row object carries. */
export function toCsv(columns: readonly string[], rows: readonly Record<string, string>[]): string {
  const lines = [columns.map(csvCell).join(",")];
  for (const row of rows) {
    lines.push(columns.map((c) => csvCell(Object.prototype.hasOwnProperty.call(row, c) ? row[c] : "")).join(","));
  }
  return `${CSV_BOM}${lines.join("\r\n")}\r\n`;
}

const text = (v: unknown): string => (v == null ? "" : String(v));
const list = (v: unknown): string => (Array.isArray(v) ? v.map(text).filter(Boolean).join("; ") : "");

interface Citation { url?: string; publisher?: string | null; date?: string | null }

function host(url: string): string {
  const m = /^[a-z][a-z0-9+.-]*:\/\/([^/?#]+)/i.exec(url);
  return m ? m[1] : url;
}

/** Publisher, date and address of each citation, in one cell. Never a headline: a headline can name
 *  what a record withholds, and has its own column, which is emptied where it must be. */
export function citationsCell(sources: readonly Citation[] | null | undefined): string {
  return (sources ?? []).filter((s) => s && s.url).map((s) => {
    const url = text(s.url);
    const date = s.date ? `, ${s.date}` : "";
    return `${s.publisher || host(url)}${date}, ${url}`;
  }).join(" | ");
}

// ---- country-system events ----------------------------------------------------------------------

export const COUNTRY_EVENT_COLUMNS = [
  "record_id", "system_id", "country", "date", "date_precision", "date_end",
  "placement", "region_code", "region_name", "regions_affected", "facility", "operator",
  "asset_class", "asset_class_label", "cause", "cause_label", "summary", "reported_effect",
  "recovery_research_status", "recovery_kind", "recovery_date",
  "evidence_confidence", "review_status", "citations", "source_headlines", "publication_note",
] as const;

export const COUNTRY_EVENT_FIELDS: Record<(typeof COUNTRY_EVENT_COLUMNS)[number], string> = {
  record_id: "The record's stable id on this site. Empty where the id itself would name a facility.",
  system_id: "The monitored country system the record belongs to.",
  country: "The country system's name.",
  date: "The day the event began (ISO 8601, YYYY-MM-DD), or the month (YYYY-MM) where only the month is known. See date_precision.",
  date_precision: "day or month: how precisely the sources date the event.",
  date_end: "The last day of the event, where the sources give one.",
  placement: "How precisely the record is placed: one region, several regions, national, or national under safeguards.",
  region_code: "First-level region code (ISO 3166-2 style), for a record placed in one region. Never finer than a first-level region.",
  region_name: "That region's name.",
  regions_affected: "First-level region codes a record that is not placed in one region says it reached.",
  facility: "The facility's name, where the record publishes one.",
  operator: "The operator's name, where the record publishes one.",
  asset_class: "Kind of infrastructure (taxonomy key).",
  asset_class_label: "Kind of infrastructure, in words.",
  cause: "Reported cause (taxonomy key).",
  cause_label: "Reported cause, in words.",
  summary: "What was reported, in one or two sentences.",
  reported_effect: "The effect the sources reported at the time.",
  recovery_research_status: "EVIDENCE_FOUND, RESEARCHED_NO_PUBLIC_EVIDENCE or NOT_YET_RESEARCHED. These are three different states: not researched is not the same as nothing found.",
  recovery_kind: "What kind of return the evidence describes (an estimate is not an observed restoration).",
  recovery_date: "The date of that return, where the evidence gives one.",
  evidence_confidence: "Evidence confidence category, where the build publishes one: the quality of the public evidence, not a probability, a severity or an importance.",
  review_status: "How the record was reviewed before publication.",
  citations: "Each cited source as publisher, date, address; sources separated by \" | \".",
  source_headlines: "Original-language headlines of the cited sources, where the record may show them.",
  publication_note: "Why cells of this row are empty, where a publication rule withholds them.",
};

export type CountryEventRow = Record<(typeof COUNTRY_EVENT_COLUMNS)[number], string>;

/** What the file says in place of the cells it empties. */
export const SAFEGUARD_CSV_NOTE = "Published under attack-campaign safeguards: region, facility, operator, source headlines and later status are not exported.";
export const LEGACY_CSV_NOTE = "This record's own text, id and source addresses name its facility, so they are not exported either; the record is listed with its date, kind of infrastructure and cause only.";

/** A record the campaign rule covers, or an attack record kept at the country level. */
export function isRestrictedEvent(e: CountryEvent, sys: CountrySystem): boolean {
  return !!e.publication || placementKind(e, sys) === "country_attack";
}

export function countryEventRow(e: CountryEvent, sys: CountrySystem): CountryEventRow {
  const restricted = isRestrictedEvent(e, sys);
  // The newer convention gives such a record an opaque id and text the build has already checked
  // for places, operators and status. The older one (a facility named in the id, the summary and
  // the citation addresses) is exported as the cross-country lists show it: no text at all.
  const abstracted = isOpaqueAttackId(e, sys.system_id);
  const bare = restricted && !abstracted;
  const open = !restricted;
  const confidence = (e as { evidence_confidence?: { category?: string; label?: string } | null }).evidence_confidence;
  return {
    record_id: bare ? "" : text(e.event_id),
    system_id: text(sys.system_id),
    country: text(sys.name),
    date: text(e.date),
    date_precision: text(e.date_precision),
    date_end: text(e.date_end),
    placement: restricted ? PLACEMENT_LABEL.national_safeguarded : PLACEMENT_LABEL[eventPlacement(e, sys)],
    region_code: open ? text(e.region_code) : "",
    region_name: open ? text(e.region_name) : "",
    regions_affected: open ? list(e.regions_affected) : "",
    facility: open ? text(e.facility_name) : "",
    operator: open ? text(e.operator) : "",
    asset_class: text(e.asset_class),
    asset_class_label: label(sys.taxonomy.asset_classes, e.asset_class),
    cause: text(e.cause),
    cause_label: label(sys.taxonomy.causes, e.cause),
    summary: bare ? "" : text(e.summary),
    reported_effect: bare ? "" : text(e.effect),
    recovery_research_status: open ? text(e.recovery?.research_status) : "",
    recovery_kind: open ? text(e.recovery?.kind) : "",
    recovery_date: open ? text(e.recovery?.date) : "",
    evidence_confidence: text(confidence?.label ?? confidence?.category),
    review_status: text(e.review?.review_status),
    citations: bare ? "" : citationsCell(e.sources),
    source_headlines: open && headlinesAllowed(e, sys)
      ? (e.sources ?? []).map((s) => text(s.title_original)).filter(Boolean).join(" | ") : "",
    publication_note: restricted
      ? [SAFEGUARD_CSV_NOTE, bare ? LEGACY_CSV_NOTE : "", text(e.publication?.note)].filter(Boolean).join(" ")
      : "",
  };
}

function label(map: Record<string, string> | undefined, key: string): string {
  return map && Object.prototype.hasOwnProperty.call(map, key) ? map[key] : text(key).replace(/_/g, " ");
}

/** The CSV of the events shown, in the order shown. */
export function countryEventsCsv(shown: readonly CountryEvent[], sys: CountrySystem): string {
  return toCsv(COUNTRY_EVENT_COLUMNS, shown.map((e) => countryEventRow(e, sys)));
}

// ---- global impact records (docs/GLOBAL_IMPACT_METHODOLOGY.md §4, §11) --------------------------

/** The served impact record, as far as the export reads it. Every field is optional here: the file
 *  is built from whatever the payload carries and never fails on an absent one. */
export interface ImpactRecordForCsv {
  impact_id?: string;
  record_kind?: string;
  date?: string;
  date_precision?: string;
  date_end?: string | null;
  country_a3?: string;
  countries_a3?: string[] | null;
  country_name?: string | null;
  admin1?: { code?: string; name?: string } | null;
  geographic_precision?: string;
  domain?: string;
  sector?: string;
  technology?: string | null;
  cause_family?: string;
  contributing_factors?: string[] | null;
  cyber_mechanism?: string | null;
  summary?: string;
  effect?: string | null;
  effect_specificity?: string | null;
  civilian_service_impact?: {
    service?: string; geographic_scope?: string; duration_text?: string | null;
    affected?: { source_says?: string | null; unit?: string | null } | string | null;
  }[] | null;
  attribution?: {
    status?: string; actor?: string | null; actor_type?: string | null; basis?: string[] | null;
    as_of?: string | null; statement?: string | null; confidence?: string | { category?: string } | null;
  } | null;
  ai_involvement?: { status?: string; relation?: string | null; role?: string | null; as_of?: string | null } | null;
  evidence_confidence?: { category?: string | null; label?: string | null; score?: number | null } | null;
  origin_count?: number | null;
  sources?: (Citation & { title_original?: string | null })[] | null;
  publication_policy?: string;
  first_published?: string | null;
}

export const IMPACT_COLUMNS = [
  "impact_id", "record_kind", "date", "date_precision", "date_end",
  "country_a3", "countries_a3", "country", "admin1_code", "admin1_name", "geographic_precision",
  "domain", "sector", "technology", "cause_family", "contributing_factors", "cyber_mechanism",
  "summary", "effect", "effect_specificity", "civilian_service_impact",
  "attribution_status", "attribution_actor", "attribution_actor_type", "attribution_basis",
  "attribution_as_of", "attribution_statement", "attribution_confidence",
  "ai_involvement_status", "ai_involvement_relation", "ai_involvement_role", "ai_involvement_as_of",
  "evidence_confidence", "evidence_confidence_score", "originating_statements",
  "citations", "source_headlines", "first_published", "publication_note",
] as const;

export const IMPACT_FIELDS: Record<(typeof IMPACT_COLUMNS)[number], string> = {
  impact_id: "The record's stable id in the impact corpus.",
  record_kind: "disruption, or attempt_no_service_impact (an attempt with no reported service disruption; never counted with disruptions).",
  date: "The day the disruption began (ISO 8601), or a coarser date where only that is known. See date_precision.",
  date_precision: "How precisely the sources date the disruption (day or month).",
  date_end: "The last day of the disruption, where the sources give one.",
  country_a3: "ISO 3166-1 alpha-3 country code, or MULTI.",
  countries_a3: "The countries of a multi-country record.",
  country: "The country's name.",
  admin1_code: "First-level region code, where the record is placed in one. Never finer than a first-level region.",
  admin1_name: "That region's name.",
  geographic_precision: "country, admin1 or multi_country.",
  domain: "energy or civilian_service.",
  sector: "Sector (taxonomy key).",
  technology: "Energy technology (taxonomy key). Empty outside energy: not applicable.",
  cause_family: "Primary cause family (taxonomy key).",
  contributing_factors: "Other cause families a source says contributed.",
  cyber_mechanism: "Broad cyber mechanism, where the cause is cyber. Empty otherwise: not applicable. Never how access was gained.",
  summary: "What happened, to what service, where (country or region).",
  effect: "The effect the sources report, in neutral words.",
  effect_specificity: "quantified, described or vague.",
  civilian_service_impact: "Each affected service with its scope, the figure in the source's own unit and words, and the reported duration. Units are never converted.",
  attribution_status: "NOT_APPLICABLE, UNKNOWN, CLAIMED, SUSPECTED, ASSESSED, ATTRIBUTED or DISPUTED. Who is publicly said to be responsible, never this site's own finding.",
  attribution_actor: "The actor named by the attributing source.",
  attribution_actor_type: "The source's description of the actor's type.",
  attribution_basis: "Who attributes: government, law enforcement, the victim or operator, a cybersecurity firm, a researcher, a media investigation, or the actor's own claim.",
  attribution_as_of: "The date of the attribution, which may be much later than the event.",
  attribution_statement: "The attribution in words: who attributed the incident to whom.",
  attribution_confidence: "HIGH, MODERATE, LOW, CLAIM_ONLY, DISPUTED or NOT_ESTABLISHED. Computed from the attribution sources.",
  ai_involvement_status: "NONE_REPORTED, CLAIMED, SUSPECTED, ASSESSED or CONFIRMED: how firmly a source ties AI to this incident.",
  ai_involvement_relation: "ai_assisted (an attacker used AI tooling) or ai_operational_cause (an AI system in operations failed). Different things.",
  ai_involvement_role: "The role the source describes.",
  ai_involvement_as_of: "The date of that statement.",
  evidence_confidence: "Evidence confidence category: the quality of the public evidence that it happened and of the reported effect. Not a probability, a severity or an importance.",
  evidence_confidence_score: "The ordinal score behind the category (0 to 100). Not a probability.",
  originating_statements: "How many distinct originating statements support the record. Republications count once.",
  citations: "Each cited source as publisher, date, address; sources separated by \" | \".",
  source_headlines: "Original-language headlines of the cited sources, where the record may show them.",
  first_published: "The build date on which the record was first served here: not the event's date and not the source's.",
  publication_note: "Why cells of this row are empty, where a publication rule withholds them.",
};

export type ImpactRow = Record<(typeof IMPACT_COLUMNS)[number], string>;

export const ABSTRACTED_CSV_NOTE = "Published at country level under the abstraction rule for attacks and sabotage: no region, facility, operator, source headline or later status is published or exported.";

const ABSTRACT_CAUSES: readonly string[] = ["kinetic", "sabotage"];

/** Abstracted by its own policy field, or by its cause: every kinetic or sabotage record is
 *  country-abstracted everywhere (§4), so the export treats one as abstracted even if the policy
 *  field were missing. The most conservative reading wins. */
export function isAbstractedImpact(r: ImpactRecordForCsv): boolean {
  return r.publication_policy === "country_abstracted" || ABSTRACT_CAUSES.includes(text(r.cause_family))
    || (r.contributing_factors ?? []).some((c) => ABSTRACT_CAUSES.includes(c));
}

function serviceImpactCell(r: ImpactRecordForCsv): string {
  return (r.civilian_service_impact ?? []).map((s) => {
    const affected = typeof s.affected === "string" ? s.affected : text(s.affected?.source_says);
    return [text(s.service), text(s.geographic_scope), affected, text(s.duration_text)].filter(Boolean).join(", ");
  }).filter(Boolean).join(" | ");
}

export function impactRow(r: ImpactRecordForCsv): ImpactRow {
  const abstracted = isAbstractedImpact(r);
  const a = r.attribution ?? {};
  const ai = r.ai_involvement ?? {};
  const conf = typeof a.confidence === "string" ? a.confidence : text(a.confidence?.category);
  return {
    impact_id: text(r.impact_id),
    record_kind: text(r.record_kind),
    date: text(r.date),
    date_precision: text(r.date_precision),
    date_end: text(r.date_end),
    country_a3: text(r.country_a3),
    countries_a3: list(r.countries_a3),
    country: text(r.country_name),
    admin1_code: abstracted ? "" : text(r.admin1?.code),
    admin1_name: abstracted ? "" : text(r.admin1?.name),
    geographic_precision: abstracted && r.geographic_precision === "admin1" ? "country" : text(r.geographic_precision),
    domain: text(r.domain),
    sector: text(r.sector),
    technology: text(r.technology),
    cause_family: text(r.cause_family),
    contributing_factors: list(r.contributing_factors),
    cyber_mechanism: text(r.cyber_mechanism),
    summary: text(r.summary),
    effect: text(r.effect),
    effect_specificity: text(r.effect_specificity),
    civilian_service_impact: serviceImpactCell(r),
    attribution_status: text(a.status),
    attribution_actor: text(a.actor),
    attribution_actor_type: text(a.actor_type),
    attribution_basis: list(a.basis),
    attribution_as_of: text(a.as_of),
    attribution_statement: text(a.statement),
    attribution_confidence: conf,
    ai_involvement_status: text(ai.status),
    ai_involvement_relation: text(ai.relation),
    ai_involvement_role: text(ai.role),
    ai_involvement_as_of: text(ai.as_of),
    evidence_confidence: text(r.evidence_confidence?.label ?? r.evidence_confidence?.category),
    evidence_confidence_score: text(r.evidence_confidence?.score),
    originating_statements: text(r.origin_count),
    citations: citationsCell(r.sources),
    source_headlines: abstracted ? "" : (r.sources ?? []).map((s) => text(s.title_original)).filter(Boolean).join(" | "),
    first_published: text(r.first_published),
    publication_note: abstracted ? ABSTRACTED_CSV_NOTE : "",
  };
}

/** The CSV of the impact records shown, in the order shown. */
export function impactRecordsCsv(shown: readonly ImpactRecordForCsv[]): string {
  return toCsv(IMPACT_COLUMNS, shown.map(impactRow));
}

// ---- the README that travels with the file ------------------------------------------------------

export const CORPUS_CAVEAT = "These are the published records in this corpus, not a census of everything that happened. "
  + "Counts are not comparable across countries: disclosure rules, reporting and research coverage differ.";

export const CSV_CONVENTIONS = [
  "UTF-8 with a byte-order mark, comma separated, quoted per RFC 4180, CRLF line ends.",
  "An empty cell means the record does not publish that value: it was not reported, it does not apply, or a publication rule withholds it (see publication_note). An empty cell is never a zero.",
  "A cell that begins with = + - or @ is prefixed with an apostrophe so a spreadsheet shows it as text instead of running it as a formula.",
  "No coordinates, and nothing finer than a first-level region, are published or exported.",
];

export interface ReadmeInput {
  /** What the file holds, e.g. "Reported events: United States". */
  title: string;
  csvName: string;
  /** The system or scope id the filename carries. */
  scope: string;
  buildDate: string;
  /** The reader's day the file was made on. */
  downloaded: string;
  shown: number;
  total: number;
  /** One line per active filter (describeFilters), and any region the list was narrowed to. */
  filters: readonly string[];
  /** Limits specific to this list: the system's comparability statement, safeguards in force. */
  limitations: readonly string[];
  columns: readonly string[];
  fields: Record<string, string>;
}

/** "About this file": plain text, one fact per line, so it can be read anywhere. */
export function readmeText(i: ReadmeInput): string {
  const hidden = i.total - i.shown;
  const lines = [
    "Energy Disruption Monitor: about this file",
    "",
    `File: ${i.csvName}`,
    `Contents: ${i.title}`,
    `Scope: ${i.scope}`,
    `Site build date: ${i.buildDate}`,
    `File made on: ${i.downloaded}`,
    `Records in this file: ${i.shown} of ${i.total} published records in this list`,
    "",
    "Filters in force when the file was made",
    ...(i.filters.length > 0
      ? [...i.filters.map((f) => `- ${f}`), `- These filters leave out ${hidden} of the ${i.total} published records in this list.`]
      : ["- None: every published record in this list is in the file."]),
    "",
    "What this file is, and is not",
    `- ${CORPUS_CAVEAT}`,
    "- Each row is a publicly reported record that met the inclusion rule and passed review. Records still in review are not published and are not in this file.",
    "- A record is not a measure of severity, and nothing here ranks a country, a region or a facility.",
    ...i.limitations.filter(Boolean).map((l) => `- ${l}`),
    "",
    "Format",
    ...CSV_CONVENTIONS.map((c) => `- ${c}`),
    "",
    "Columns",
    ...i.columns.map((c) => `- ${c}: ${i.fields[c] ?? ""}`),
    "",
  ];
  return lines.join("\r\n");
}

/** Lower-case letters, digits and hyphens only: a scope from an address never shapes a filename. */
function slug(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "records";
}

/** `edm-<scope>-<kind>-<build date>.csv`: the system and the build travel in the name. */
export function csvFilename(scope: string, kind: string, buildDate: string): string {
  return `edm-${slug(scope)}-${slug(kind)}-${slug(buildDate)}.csv`;
}

export function readmeFilename(csvName: string): string {
  return `${csvName.replace(/\.csv$/, "")}-README.txt`;
}
