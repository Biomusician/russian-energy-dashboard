/** The global impact layer as it is served (iteration 22; docs/GLOBAL_IMPACT_METHODOLOGY.md §4, §11).
 *
 *  Types only. These follow the three served files (`global/impacts.json`,
 *  `global/regional_context.json`, `global/evidence_confidence.json`), which are the truth where
 *  they and the methodology differ.
 *
 *  An absence is never a zero: a field that may be absent is `null` (not applicable) or one of the
 *  served absence words ("unknown", "not_researched", "withheld", ...), so several fields here are
 *  `X | string | null` on purpose.
 */

/** One entry of a served vocabulary: a key, the words for it and what it means. */
export interface VocabEntry {
  id: string | number;
  label: string;
  definition?: string;
  /** Sectors carry their domain; AI roles carry their relation; cause families say if malicious. */
  domain?: string;
  relation?: string;
  malicious?: boolean | null;
  may_be_sole_evidence?: boolean;
}

/** Vocabularies by name ("sectors", "cause_families", "claims", ...). */
export type Vocabularies = Record<string, VocabEntry[]>;

export interface ImpactSocial {
  platform: string;
  handle: string | null;
  display_name: string | null;
  /** S1 official, S2 recognised journalist or institution, S3 researcher, S4 unknown. */
  account_tier: string;
  /** How the account's identity was established. A platform badge is not identity. */
  identity_basis: string;
  posted_at?: string | null;
}

export interface ImpactSource {
  ref: string;
  url: string;
  publisher: string | null;
  date: string | null;
  language: string | null;
  source_role: string;
  medium: string;
  social: ImpactSocial | null;
  /** Which claims this source supports: occurrence, effect, attribution, ai_involvement. */
  supports: string[];
  opened: boolean | null;
  /** Never present on an abstracted record. */
  title_original?: string | null;
  title_en?: string | null;
  derived_claim?: string | null;
  link_check?: string | null;
}

/** Evidence Confidence v2 (§8.1): a category, an ordinal score that is not a probability, and the
 *  components that produced it. The same shape on impact records and on country events.
 *
 *  `category` is null where the evidence was NOT ASSESSED (for example a record cited only through
 *  a discovery aid, with no primary source attached yet); `reason` then says why. Not assessed is
 *  its own state: it is not the lowest category and it is not zero. */
export interface EvidenceConfidence {
  category: string | null;
  label: string | null;
  score: number | null;
  /** Why there is no category, where there is none. */
  reason?: string | null;
  disputed: boolean;
  components: {
    directness: { tier: string | null; points: number };
    /** `basis` says what was counted: "reviewed" (originating statements established on review)
     *  or "publishers" (distinct publishers cited; whether they relay one statement was not reviewed). */
    origins: { count: number; points: number; basis?: string | null };
    effect: { specificity: string | null; points: number };
    opened: { points: number };
    contemporaneous: { points: number };
  };
  reasons: string[];
}

export interface CompetingAttribution {
  actor: string | null;
  actor_type: string | null;
  basis: string[];
  statement: string | null;
  source_refs: string[];
}

/** An actor's own, unverified claim of responsibility (iteration 22 closure). Provenance only:
 *  never a competing attribution, never the attribution itself, and it never moves a confidence. */
export interface SelfClaim {
  actor: string | null;
  actor_type: string | null;
  statement: string | null;
  source_refs: string[];
}

/** Who is publicly said to be responsible (§6). Never this site's own finding. */
export interface Attribution {
  /** NOT_APPLICABLE, UNKNOWN, CLAIMED, SUSPECTED, ASSESSED, ATTRIBUTED or DISPUTED. */
  status: string;
  actor: string | null;
  actor_type: string | null;
  basis: string[];
  /** The date of the attribution, which may be much later than the event. */
  as_of: string | null;
  statement: string | null;
  /** Credible alternative attributions by a source other than the actor. A self-claim is never one. */
  competing: CompetingAttribution[];
  /** Actors' own claims of responsibility, unverified. Optional: older payloads do not carry it. */
  self_claims?: SelfClaim[] | null;
  source_refs: string[];
  /** HIGH, MODERATE, LOW, CLAIM_ONLY, DISPUTED, NOT_ESTABLISHED; null when not applicable. */
  confidence: string | null;
}

/** Whether a source ties AI to this incident (§7). */
export interface AiInvolvement {
  /** NONE_REPORTED, CLAIMED, SUSPECTED, ASSESSED or CONFIRMED. */
  status: string;
  /** ai_assisted or ai_operational_cause: different things, never merged. */
  relation: string | null;
  role: string | null;
  as_of: string | null;
  statement: string | null;
  source_refs: string[];
}

export interface AffectedFigure {
  value: number | null;
  /** The source's own unit. People are not customers are not households. Never converted. */
  unit: string | null;
  qualifier: string | null;
  source_says: string | null;
}

export interface ServiceImpact {
  service: string;
  geographic_scope: string;
  /** A figure, or an absence word ("unknown", "not_researched", ...), or null (not applicable). */
  affected: AffectedFigure | string | null;
  /** The sources' words, or an absence word, or null. */
  duration_text: string | null;
  source_refs: string[];
}

export interface ImpactCountry {
  a3: string;
  name: string;
  /** The monitored country system this country belongs to, else null. */
  system_id: string | null;
  /** True where the country is part of the Russia, Belarus and Crimea theatre. */
  theatre?: boolean | null;
}

export interface ImpactRecord {
  impact_id: string;
  /** "disruption", or "attempt_no_service_impact" (listed apart, never counted). */
  record_kind: string;
  /** ISO day, or "YYYY-MM" at month precision. */
  date: string;
  date_precision: string;
  date_end: string | null;
  /** ISO alpha-3, or "MULTI" with `countries_a3`. */
  country_a3: string;
  countries_a3?: string[] | null;
  countries?: ImpactCountry[] | null;
  country_name: string;
  system_id: string | null;
  theatre?: boolean | null;
  admin1: { code: string; name: string } | null;
  geographic_precision: string;
  domain: string;
  sector: string;
  /** Null outside energy (not applicable); may be an absence word. */
  technology: string | null;
  cause_family: string;
  contributing_factors: string[];
  /** Null unless the cause is cyber, or a non-malicious IT failure (it_outage_affecting_operations). */
  cyber_mechanism: string | null;
  summary: string;
  effect: string | null;
  effect_specificity: string | null;
  inclusion_basis: number | null;
  civilian_service_impact: ServiceImpact[];
  attribution: Attribution;
  ai_involvement: AiInvolvement;
  dispute: { about: string; statement: string; source_refs: string[] } | null;
  sources: ImpactSource[];
  episode_id: string | null;
  episode_basis: string | null;
  /** "standard" or "country_abstracted" (every kinetic or sabotage record). */
  publication_policy: string;
  research_pass?: string | null;
  /** The build date the record was first served. Not the event date, not a source date.
   *  null: not yet served, pending its first release. Never a date to invent or to sort as one. */
  first_published: string | null;
  review?: {
    reviewed_at?: string; review_status?: string; roles?: Record<string, string>;
    ai_check?: string; social_check?: string; disposition?: string | null;
  } | null;
  evidence_confidence: EvidenceConfidence | null;
  origin_count: number | null;
}

export interface ResearchFamily {
  lane?: string;
  research_pass?: string;
  family: string;
  method?: string;
  window?: string;
  status?: string;
  limitation?: string;
}

export interface ImpactResearch {
  window?: { start: string; end: string };
  status?: string;
  source_families: ResearchFamily[];
  latest_research_date: string | null;
  regions_worked?: string[];
  limitations?: string[];
}

export interface ImpactsPayload {
  schema_version: number;
  as_of: string;
  scope_statement: string;
  caveats: string[];
  order?: string;
  field_notes?: Record<string, string>;
  /** Why the corpus is empty, when it is. */
  empty_reason: string | null;
  attempts_label?: string;
  vocabularies: Vocabularies;
  research: ImpactResearch;
  /** Countries with at least one record, alphabetical by name. Never carries a count. */
  countries: ImpactCountry[];
  /** Disruptions, by event date, newest first. */
  records: ImpactRecord[];
  /** Documented attempts with no reported service disruption. Apart, and never counted. */
  attempts: ImpactRecord[];
}

export interface ContextMetric {
  value: number | null;
  value_upper?: number | null;
  unit: string | null;
  qualifier?: string | null;
  /** What the figure measures, in the source's words. */
  basis: string | null;
}

/** One dated, sourced statement of the regional context (§10). Never a status flag. */
export interface ContextEntry {
  id: string;
  date: string;
  as_of: string;
  context_type: string;
  claim: string;
  metric: ContextMetric | null;
  sources: ImpactSource[];
  first_published?: string | null;
  age_days?: number | null;
  /** The newest statement of its type on record. It is still "as of" its date, not a current status. */
  is_latest_of_type: boolean;
}

export interface RegionalContext {
  schema_version: number;
  as_of: string;
  context_id: string;
  /** The registry group these statements describe (iteration 22). */
  group?: string | null;
  label: string;
  statement: string;
  /** What is deliberately not built: no open/closed flag, no vessels, routes or bypass capacity. */
  not_built: string;
  order?: string;
  latest_note?: string;
  /** For each context type, the ids of its newest statements. Several may share the newest
   *  as_of; all of them are the latest. Absent in older payloads: computed from the entries then. */
  latest_by_type?: Record<string, string[]> | null;
  empty_reason: string | null;
  context_types: VocabEntry[];
  vocabularies: Vocabularies;
  research?: ImpactResearch;
  entries: ContextEntry[];
}

export interface ConfidenceComponent {
  id: string;
  label: string;
  max: number;
  meaning?: string;
  tiers?: { id: string; points: number; label: string; meaning: string }[];
}

/** The method of §8 as data: read by the confidence disclosure and the glossary. */
export interface ConfidenceMethod {
  version: string;
  /** Present while the method is provisional, e.g. "provisional: thresholds not calibrated". */
  status?: string | null;
  /** Confidence is evidence quality: not a probability, not severity, not importance. */
  statement: string;
  questions: { id: string; label: string; asks: string }[];
  components: ConfidenceComponent[];
  categories: { id: string; min?: number; label: string; meaning: string }[];
  overrides: string[];
  properties: string[];
  attribution: {
    official_bases?: string[];
    first_party_bases?: string[];
    technical_bases?: string[];
    labels: Record<string, string>;
    meanings: Record<string, string>;
  };
  scope_of_use?: string;
  /** The same vocabularies the impact payload carries, for pages that load only the method. */
  labels: Vocabularies;
  null_means?: string;
}
