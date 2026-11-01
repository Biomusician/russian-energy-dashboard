/** The global manifest and per-system payloads (iteration 14).
 *
 *  The frontend holds no list of countries. Which systems exist, where their files live and
 *  what their evidence supports all come from `global/manifest.json`, which the pipeline
 *  generates from `pipeline/systems.py`. Adding a country is a pipeline change only.
 */

const BASE = `${import.meta.env.BASE_URL}data`;

export type Readiness = "INDEX_READY" | "EXPERIMENTAL" | "CONTEXT_ONLY" | "INSUFFICIENT_EVIDENCE";
export type SectorState =
  | "SCORED" | "EXPERIMENTAL" | "CONTEXT_ONLY" | "INSUFFICIENT_EVIDENCE"
  | "NOT_APPLICABLE" | "NOT_YET_RESEARCHED";

export interface ManifestSystem {
  id: string;
  name: string;
  kind: "theatre" | "country";
  root: string;
  evidence_readiness: Readiness;
  index: { id: string; name: string } | null;
  headline: { value: number; as_of: string; label: string; meaning: string } | null;
  reporting_environment: string;
  as_of: string;
  bounds?: [number, number, number, number];
  files: string[];
}

export interface Manifest {
  schema_version: number;
  build_time: string;
  selection: { rule: string; source: string; source_url: string; caveat: string };
  comparability_statement: string;
  reporting_environments: Record<string, string>;
  systems: ManifestSystem[];
}

export interface SectorEntry {
  sector: string;
  label: string;
  state: SectorState;
  assessed_readiness: string;
  reason: string;
}

export interface ProfileMetric {
  metric: string;
  value: number | string | null;
  unit?: string;
  year?: number | string;
  source?: string;
  url?: string;
  note?: string;
  basis?: string;
}

export interface CountrySystem {
  system_id: string;
  name: string;
  as_of: string;
  evidence_readiness: Readiness;
  index: null;
  headline: null;
  no_index_reason: string;
  sectors: SectorEntry[];
  reporting_environment: string;
  reporting_environment_text: string;
  reporting_note: string;
  comparability: "none";
  comparability_statement: string;
  geography: {
    unit_label: string;
    units_expected: number;
    note: string;
    source: string;
    bounds: [number, number, number, number];
    view_bounds: [number, number, number, number];
    rulings: { code: string; status: string; note: string }[];
  };
  event_summary: {
    recorded_events: number;
    episodes: number;
    multi_record_episodes: number;
    excluded_after_as_of: number;
    recovery_kinds: Record<string, number>;
    placed_in_a_region: number;
    country_level: number;
    recovery_research: Record<string, number>;
    first_date: string | null;
    last_date: string | null;
    note: string;
  };
  inclusion_threshold: { version: string; rule: string; clauses: Record<string, string> };
  taxonomy: { asset_classes: Record<string, string>; causes: Record<string, string> };
  profile: {
    as_of_note?: string;
    metrics: ProfileMetric[];
    significance?: string[];
    significance_sources?: string[];
  };
  sources: SourceEntry[];
  research_log: { note: string; passes: ResearchPass[] };
  /** The event SEARCH's coverage. Independent of source freshness: never derived from it. */
  research_freshness: {
    last_systematic_pass: string | null;
    coverage_window: [string, string] | null;
    completeness: "complete" | "partial" | "never_systematic";
    /** Iteration 16: whether the newest systematic pass starts at the coverage start, and how
     *  many of its declared lanes ran in full. Optional for older payloads. */
    covers_full_window?: boolean;
    lanes_declared?: number;
    lanes_complete?: number;
    research_cadence_days: number;
    next_due: string | null;
    note: string;
  };
  stale_policies: Record<string, { days: number; rationale: string }>;
  review_summary: { dual_reviewed: number; legacy_single_review: number; note: string };
  publication_policy: {
    withheld_records: number;
    campaigns: { campaign_id: string; name: string; status: string; status_checked: string;
                 status_basis: string; policy_applied: boolean }[];
    release_rule: { id: string; status: string; text: string; release_after_end_days: number } | null;
  };
  episode_bases: Record<string, string>;
  research_gaps: string[];
  audit_docs: string[];
  record_reviewed: string | null;
  review_freshness_days: number;
  onboarding_gate: { item: number | string; label: string; status: "met" | "partial" | "unmet"; note: string }[];
}

/** A registry source. Its stale limit is display policy derived from `stale_policy`; it never
 *  decides whether an event is accepted and never enters a number. */
export interface SourceEntry {
  name: string;
  role: string;
  licence: string;
  last_checked: string | null;
  publication_cadence: string | null;
  stale_policy: string | null;
  stale_after_days: number | null;
  source_release: string | null;
  content_vintage: string | null;
}

export interface ResearchPass {
  date: string;
  by: string;
  kind: "systematic" | "targeted";
  window: [string, string];
  scope: string;
  status: "complete" | "partial";
  status_reason?: string;
  source_families?: string[];
  lanes?: { lane: string; source_family?: string; status: "complete" | "partial"; reason?: string }[];
  outcome: Record<string, number>;
}

/** One named hazard or one explicitly common event. A record no episode names is a singleton. */
export interface Episode {
  episode_id: string;
  name: string | null;
  hazard: string | null;
  basis: string;
  event_ids: string[];
  records: number;
  first_date: string;
  last_date: string;
  region_codes: string[];
  has_country_level_record: boolean;
}

export interface CountryEvent {
  event_id: string;
  date: string;
  date_precision: string;
  date_end: string | null;
  region_code: string | null;
  region_name: string | null;
  geography_precision: "admin1" | "country";
  regions_affected: string[];
  facility_name: string | null;
  facility_name_local: string | null;
  operator: string | null;
  asset_class: string;
  cause: string;
  summary: string;
  effect: string | null;
  inclusion_basis: string;
  criterion_met: number | null;
  threshold_basis: string | null;
  capacity_affected: { value: number | null; unit?: string; source_says?: string } | null;
  sources: { url: string; publisher?: string; date?: string; language?: string;
             source_role?: string; opened?: boolean | null }[];
  recovery: { research_status: string; kind: string | null; date: string | null;
              evidence: string | null; url: string | null };
  review: {
    reviewed_at: string;
    review_status: "dual_reviewed" | "legacy_single_review";
    primary_review_complete: boolean;
    independent_review_complete: boolean;
    reviewer_count: number;
    disposition: "confirmed" | "corrected" | null;
    source_count: number;
    sources_opened_by_reviewer: number | null;
    process: string;
    threshold_version: string;
    source_access: string;
  };
  episode_id: string;
  hazard_name: string | null;
  /** Set when an active campaign's publication rule withholds part of this record. */
  publication: { rule: string; campaign_id: string; withheld: string[]; note: string } | null;
}

export interface CountryBundle {
  system: CountrySystem;
  events: CountryEvent[];
  episodes: Episode[];
  regions: GeoJSON.FeatureCollection;
}

let manifestPromise: Promise<Manifest> | null = null;

/** The manifest, fetched once per page. A failure is not cached: the next call retries. */
export function loadManifest(): Promise<Manifest> {
  if (!manifestPromise) {
    manifestPromise = fetch(`${BASE}/global/manifest.json`, { cache: "no-cache" })
      .then((r) => {
        if (!r.ok) throw new Error(`manifest: HTTP ${r.status}`);
        return r.json() as Promise<Manifest>;
      })
      .catch((err) => {
        manifestPromise = null;
        throw err;
      });
  }
  return manifestPromise;
}

async function getJson<T>(path: string, signal: AbortSignal): Promise<T> {
  const r = await fetch(`${BASE}/${path}`, { signal, cache: "no-cache" });
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json() as Promise<T>;
}

/** One country's three files. Aborting `signal` abandons the load, so a slow response for the
 *  country the reader just left can never land on the one they moved to. */
export async function loadCountry(entry: ManifestSystem, signal: AbortSignal): Promise<CountryBundle> {
  const [system, events, regions] = await Promise.all([
    getJson<CountrySystem>(`${entry.root}/system.json`, signal),
    getJson<{ events: CountryEvent[]; episodes?: Episode[] }>(`${entry.root}/events.json`, signal),
    getJson<GeoJSON.FeatureCollection>(`${entry.root}/regions.geojson`, signal),
  ]);
  if (system.system_id !== entry.id) {
    throw new Error(`${entry.root}/system.json describes ${system.system_id}, not ${entry.id}`);
  }
  return { system, events: events.events, episodes: events.episodes ?? [], regions };
}

export async function loadWorld(signal: AbortSignal): Promise<GeoJSON.FeatureCollection> {
  return getJson<GeoJSON.FeatureCollection>("global/world.geojson", signal);
}

// ---- display vocabulary ---------------------------------------------------------------------

export const READINESS_LABEL: Record<Readiness, string> = {
  INDEX_READY: "Index published",
  EXPERIMENTAL: "Experimental",
  CONTEXT_ONLY: "Context and reported events only",
  INSUFFICIENT_EVIDENCE: "Insufficient evidence",
};

export const SECTOR_STATE_LABEL: Record<SectorState, string> = {
  SCORED: "Scored",
  EXPERIMENTAL: "Experimental",
  CONTEXT_ONLY: "Tracked, not scored",
  INSUFFICIENT_EVIDENCE: "Unknown",
  NOT_APPLICABLE: "Not applicable",
  NOT_YET_RESEARCHED: "Not yet researched",
};

export const ENVIRONMENT_LABEL: Record<string, string> = {
  mandatory_regulatory: "Mandatory regulatory reporting",
  mixed_regulatory: "Mixed regulatory and press reporting",
  corporate_disclosure: "Corporate and ministry disclosure",
  media_only: "Media and company statements only",
  conflict_restricted: "Wartime-restricted reporting",
};

export const RECOVERY_LABEL: Record<string, string> = {
  EVIDENCE_FOUND: "Recovery evidence found",
  RESEARCHED_NO_PUBLIC_EVIDENCE: "Researched — no public recovery evidence",
  NOT_YET_RESEARCHED: "Recovery not yet researched",
  WITHHELD_ACTIVE_CAMPAIGN: "Facility status not published while the attack campaign is active",
};

export const REVIEW_STATUS_LABEL: Record<string, string> = {
  dual_reviewed: "Independently reviewed",
  legacy_single_review: "Single review (published before independent review was required)",
};

export const RESEARCH_COMPLETENESS_LABEL: Record<string, string> = {
  complete: "Systematic search complete",
  partial: "Systematic search partial",
  never_systematic: "Targeted searches only, no systematic search yet",
};

/** What KIND of recovery evidence was found. Different claims, never one "recovered". */
export const RECOVERY_KIND_LABEL: Record<string, string> = {
  full_restart: "Full restart reported",
  partial_restart: "Partial restart only",
  service_restored: "Service restored (physical repair not implied)",
  partial_restoration: "Partial restoration only — no completion found",
  estimate: "Estimate only — not an observed restoration",
  supply_unaffected_statement: "Supply-continuity statement — not a facility restart",
  no_supply_lost: "No supply was lost — nothing to restore",
};

export function labelFor(map: Record<string, string>, key: string): string {
  return Object.prototype.hasOwnProperty.call(map, key) ? map[key] : key.replace(/_/g, " ");
}
