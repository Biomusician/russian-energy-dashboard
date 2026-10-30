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
  sources: { name: string; role: string; licence: string }[];
  research_gaps: string[];
  audit_docs: string[];
  record_reviewed: string | null;
  review_freshness_days: number;
  onboarding_gate: { item: number; label: string; status: "met" | "partial" | "unmet"; note: string }[];
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
  review: { reviewed: string; process: string; threshold_version: string; source_access: string };
}

export interface CountryBundle {
  system: CountrySystem;
  events: CountryEvent[];
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
    getJson<{ events: CountryEvent[] }>(`${entry.root}/events.json`, signal),
    getJson<GeoJSON.FeatureCollection>(`${entry.root}/regions.geojson`, signal),
  ]);
  if (system.system_id !== entry.id) {
    throw new Error(`${entry.root}/system.json describes ${system.system_id}, not ${entry.id}`);
  }
  return { system, events: events.events, regions };
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
