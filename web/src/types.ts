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
  asset_id: string;
  asset_name: string | null;
  asset_class: string | null;
  region_code: string | null;
  date: string;
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
  centroid: [number, number];
  bbox: [number, number, number, number];
}

export interface Asset {
  asset_id: string;
  name: string | null;
  asset_class: string;
  region_code: string;
  capacity_mw?: number | null;
  fuel?: string | null;
  voltage_kv?: number | null;
  owner?: string | null;
  operator?: string | null;
  lon: number;
  lat: number;
  source: string;
  source_url: string | null;
}

export interface RegionEffects {
  generation_margin: number | null;
  fuel_production: number | null;
  logistics: number | null;
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
  esdi: number;
  sectors: Record<string, number>;
  incident_count: number;
  struck_facility_count: number;
  live_disruption_count: number;
  unresolved_count: number;
  installed_mw: number;
  effects: RegionEffects;
}

export type EvidenceKind = "observed" | "estimated" | "modelled";

export interface RecoveryState {
  recovery_evidence_kind: EvidenceKind;
  reconstitution_horizon_days: number;
  resolved: boolean;
  impairment_age_days: number | null;
  observed_restoration_days: number | null;
  reconstitution_observed_days: number | null;
  estimate_days: {
    lower: number | null;
    central: number | null;
    upper: number | null;
    basis: string | null;
    method: string | null;
    confidence: string | null;
  } | null;
  reconstitution_level: string | null;
  partial_operations_resumed_at: string | null;
  reconstituted_at: string | null;
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
  recovery: RecoveryState;
}

export interface RecoveryStats {
  unresolved_count: number;
  resolved_count: number;
  median_observed_restoration_days: number | null;
  observed_restoration_sample: number;
  median_impairment_age_days: number | null;
  impairment_age_sample: number;
  evidence_kind_counts: Record<string, number>;
  by_sector: Record<string, {
    disrupted_facilities: number;
    unresolved: number;
    observed_restoration_sample: number;
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

export interface Snapshot {
  as_of: string;
  build_time: string;
  esdi: number;
  sectors: Record<string, number>;
  sectors_covered: string[];
  sectors_uncovered: string[];
  heating_season: boolean;
  denominators: { refining_mtpa: number; electric_power_mw: number };
  incident_total: number;
  incidents_with_quantified_capacity: number;
  assessed_degradation: AssessedDegradation;
  recovery_stats: RecoveryStats;
  coverage_detail: CoverageDetail;
  live_disruptions: LiveDisruption[];
  regions: Record<string, RegionSnapshot>;
  not_modelled: Record<string, string>;
  coverage: Coverage | null;
  parser_warnings: string[];
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
}
