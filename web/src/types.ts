/** Shapes emitted by the Python pipeline. Kept in one file so a schema change in
 *  data/processed/ surfaces here as a type error rather than as undefined at runtime. */

export type Confidence = "confirmed" | "probable" | "possible" | "unverified";
export type Status = "active" | "degraded" | "repaired" | "unknown";

export interface Source {
  url: string;
  title: string | null;
  publisher: string | null;
  date?: string | null;
  source_type?: string | null;
}

export interface Incident {
  incident_id: string;
  episode_id?: string;
  asset_id: string;
  asset_name: string | null;
  asset_class: string | null;
  region_code: string | null;
  date: string;
  date_start?: string | null;
  date_end?: string | null;
  date_precision: "day" | "month";
  cause: string;
  attribution: string;
  attribution_confidence: string;
  confidence: Confidence;
  status?: Status;
  sources: Source[];
  origin: string;
  notes?: string | null;
  conflicting_reports?: boolean;
  part_of_unenumerated_series?: boolean;
  capacity_affected_mw?: number | null;
  capacity_affected_mtpa?: number | null;
  capacity_affected_pct?: number | null;
  repair_cost_reported_usd_m?: number | null;
  repair_cost_estimate_low_usd_m?: number | null;
  repair_cost_estimate_high_usd_m?: number | null;
  cost_basis?: string | null;
  _district?: string | null;
}

export interface RegionMeta {
  code: string;
  name: string;
  district: string;
  country: string;
  esdi_included: boolean;
  analytic_scope?: string;
  sovereignty?: string;
  de_facto_control?: string;
  status_note?: string;
  centroid: [number, number];
  bbox: [number, number, number, number];
}

export interface Asset {
  asset_id: string;
  name: string | null;
  asset_class: string;
  region_code: string;
  capacity_mw?: number | null;
  capacity_mtpa?: number | null;
  fuel?: string | null;
  voltage_kv?: number | null;
  owner?: string | null;
  operator?: string | null;
  status?: string | null;
  /** "region" for curated assets placed at their region centroid (admin-level), absent for
   *  automated point assets carrying their source's own public coordinate. */
  precision?: string | null;
  lon: number;
  lat: number;
  source: string;
  source_url: string | null;
  note?: string | null;
}

export interface RegionEffects {
  generation_margin: number | null;
  fuel_production: number | null;
  logistics: number | null;
  transmission_burden: number | null;
  heating_season_exposure: number | null;
  repair_burden: number | null;
  recurrence: number | null;
  [key: string]: number | null;
}

export interface RegionSnapshot {
  code: string;
  name: string;
  district: string;
  country: string;
  esdi_included: boolean;
  analytic_scope: string;
  sovereignty: string | null;
  de_facto_control: string | null;
  status_note: string | null;
  esdi: number;
  sectors: Record<string, number>;
  incident_count: number;
  struck_facility_count: number;
  live_disruption_count: number;
  unresolved_count: number;
  oldest_unresolved_days: number;
  median_unresolved_age_days: number | null;
  reconstitution_backlog_days: number;
  affected_sectors: string[];
  installed_mw: number;
  tracked_substations: number;
  tracked_transmission_lines: number;
  population_millions: number | null;
  regional_intensity?: RegionalIntensity;
  effects: RegionEffects;
}

export interface RegionalIntensity {
  composite: number | null;
  sectors: Record<string, number | null>;
  covered_sectors: string[];
  missing_sectors: string[];
}

export type EvidenceKind = "observed" | "estimated" | "modelled";
export type RecoveryStatus =
  | "impaired" | "partial_restart" | "substantially_restored" | "fully_reconstituted" | "unknown";

export interface RecoveryState {
  incident_id: string | null;
  recovery_status: RecoveryStatus;
  scoring_evidence_kind: EvidenceKind;
  reconstitution_horizon_days: number;
  resolved: boolean;
  impairment_age_days: number | null;
  observed_days: number | null;
  observed_date: string | null;
  partial_operations_resumed_at: string | null;
  partial_or_full: string | null;
  estimate_days: {
    lower: number | null;
    central: number | null;
    upper: number | null;
    basis: string | null;
    method: string | null;
    confidence: string | null;
    used_for_scoring: boolean;
  } | null;
  estimate_used_for_scoring: boolean;
  what_source_establishes: string | null;
  source_confidence: string | null;
  recovery_sources: { url: string }[];
}

export interface LiveDisruption {
  asset_id: string;
  name: string | null;
  asset_class: string | null;
  sector: string | null;
  region_code: string | null;
  disruption_weight: number;
  event_count: number;
  latest: string;
  driving_incident_id: string | null;
  recovery: RecoveryState;
}

export interface RecoveryStats {
  unresolved_count: number;
  resolved_count: number;
  min_median_episodes: number;
  median_observed_restoration_days: number | null;
  median_meaningful: boolean;
  observed_restoration_episodes: number;
  observed_restoration_values: number[];
  median_impairment_age_days: number | null;
  impairment_age_sample: number;
  partial_restart_episodes: number;
  full_reconstitution_episodes: number;
  estimate_episodes: number;
  recovery_record_count: number;
  evidence_kind_counts: Record<string, number>;
  by_sector: Record<string, {
    disrupted_facilities: number;
    unresolved: number;
    observed_restoration_episodes: number;
    median_observed_restoration_days: number | null;
  }>;
  note: string;
}

export interface AssessedDegradation {
  quantified_incident_count: number;
  total_incident_count: number;
  quantified_mw: number;
  quantified_mtpa: number;
  note: string;
}

export interface CoverageDetail {
  by_year: Record<string, number>;
  by_sector: Record<string, number>;
  by_cause: Record<string, number>;
  by_district: Record<string, number>;
  evidence_matrix: Record<string, { events: number; recovery: number; cost: number }>;
  note: string;
}

export interface EconomicSnapshotPoint {
  reporting_month: string;
  snapshot_date: string;
  value: number | null;
  units: string;
  source_url: string | null;
  revision_status: string | null;
}

export interface EconomicContext {
  provider: string;
  cadence: string;
  kind: string;
  caveat: string;
  metrics: Record<string, EconomicSnapshotPoint[]>;
}

export interface RefineryReconciliation {
  national_public_estimate_mtpa: number;
  national_estimate_source: string;
  tracked_mtpa: number;
  coverage_pct: number;
  gap_mtpa: number;
  note: string;
}

export interface Coverage {
  reported_total_strikes: number;
  enumerated_in_this_dataset: number;
  coverage_ratio: number;
  by_period: { period: string; strikes: number; cumulative: number }[];
  source_url: string;
  note: string;
}

export interface SchemaCheck {
  dataVersion: number;
  appVersion: number;
  ok: boolean;
  mode: "exact" | "back" | "forward" | "unsupported";
}

export interface Snapshot {
  as_of: string;
  build_time: string;
  esdi: number;
  sectors: Record<string, number>;
  sectors_covered: string[];
  sectors_uncovered: string[];
  heating_season: boolean;
  denominators: { refining_mtpa: number; electric_generation_mw: number; transmission_saturation_events: number };
  incident_total: number;
  incidents_with_quantified_capacity: number;
  assessed_degradation: AssessedDegradation;
  recovery_stats: RecoveryStats;
  coverage_detail: CoverageDetail;
  live_disruptions: LiveDisruption[];
  regions: Record<string, RegionSnapshot>;
  not_modelled: Record<string, string>;
  coverage: Coverage | null;
  economic_context: EconomicContext | null;
  refinery_reconciliation: RefineryReconciliation | null;
  facet_counts: FacetCounts;
  parser_warnings: string[];
  /** Data-contract version (iteration 5). Absent in pre-iteration-5 payloads -> treated as 1. */
  schema_version?: number;
}

/** Full-corpus counts per UI dimension (iteration 4). Counters omit zero keys, so a key's
 *  presence with a positive count is what a data-driven "show this toggle" rule checks.
 *  Kinds are separate on purpose: a class can have assets but no incidents, or vice versa. */
export interface FacetCounts {
  asset_class: Record<string, number>;
  line_class: Record<string, number>;
  /** Continental context trunk routes, kept SEPARATE from analytic line_class so a
   *  continent of context pipelines can never imply thousands of disruption records (§15). */
  context_route_class?: Record<string, number>;
  incident_asset_class: Record<string, number>;
  sector: Record<string, number>;
  cause: Record<string, number>;
  confidence: Record<string, number>;
  recovery_state: Record<string, number>;
  evidence_kind: Record<string, number>;
}

export interface NationalSeries {
  dates: string[];
  esdi: number[];
  sectors: Record<string, number[]>;
}

export interface RegionalSeries {
  dates: string[];
  regions: Record<string, { esdi: number[]; sectors: Record<string, number[]> }>;
}

export interface Taxonomy {
  asset_classes: Record<string, string>;
  sectors: Record<string, string>;
  causes: Record<string, string>;
  analytic_concepts: Record<string, string>;
  evidence_kinds: string[];
  window_start: string;
}

export interface Bundle {
  snapshot: Snapshot;
  national: NationalSeries;
  regional: RegionalSeries;
  incidents: Incident[];
  regions: RegionMeta[];
  assets: Asset[];
  taxonomy: Taxonomy;
  regionsGeo: GeoJSON.FeatureCollection;
  linesGeo: GeoJSON.FeatureCollection;
  contextLand: GeoJSON.FeatureCollection;
  contextBorders: GeoJSON.FeatureCollection;
  ocean: GeoJSON.FeatureCollection;
  /** Result of the schema compatibility check performed at load time. Optional context
   *  layers (rivers, pipeline networks) are lazy-loaded via loadContextLayer(), not held
   *  on the bundle (§16). */
  schema: SchemaCheck;
}
