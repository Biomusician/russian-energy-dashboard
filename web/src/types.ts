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
  /** What the source claims the true count is ("at least 16 times"), and how many of those
   *  carried an extractable date. The gap between them is a stated undercount. */
  unenumerated_series_total?: number;
  series_events_extracted?: number;
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
  capacity_bcm_y?: number | null;
  capacity_basis?: string | null;
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
  /** §13 granular description of what the source proves (flow_rerouted, unit_restarted,
   *  station_rebuilt…). Distinct from recovery_status, the scoring bucket. */
  recovery_kind?: string | null;
  /** §15 evidence family: facility_reconstitution | unit_restart | service_restoration |
   *  flow_rerouting | estimate. Only facility_reconstitution means the equipment itself returned. */
  evidence_family?: string | null;
  /** §31 lightweight source-quality tier (major_wire, government, national_regional…). */
  source_quality?: string | null;
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
  min_sector_median_episodes?: number;
  /** POOLED median across all classes — mixed-infrastructure evidence, never the headline. */
  median_observed_restoration_days: number | null;
  median_meaningful: boolean;
  median_is_mixed_infrastructure?: boolean;
  observed_restoration_episodes: number;
  observed_restoration_values: number[];
  /** §15: episode count per evidence family (service_restoration vs unit_restart vs
   *  facility_reconstitution vs flow_rerouting vs estimate). */
  evidence_family_counts?: Record<string, number>;
  /** Per-class medians that individually clear the per-class gate (may be empty). */
  sector_medians?: Record<string, number>;
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
    observed_restoration_values?: number[];
    partial_restart_episodes?: number;
    median_observed_restoration_days: number | null;
  }>;
  note: string;
}

/** One dated restoration observation (iteration 8). The COMPLETE log lives here, not in
 *  live_disruptions — that array only carries facilities still carrying disruption weight and is
 *  truncated, so fully-recovered facilities are absent from it by construction. */
export interface RecoveryEvent {
  incident_id: string;
  episode_id: string;
  asset_id: string;
  asset_name: string | null;
  asset_class: string | null;
  sector: string | null;
  region_code: string | null;
  incident_date: string;
  /** The date the restoration evidence attaches to — what a trailing window filters on. */
  evidence_date: string;
  evidence_date_kind: "observed_restoration" | "partial_restart";
  recovery_status: string | null;
  recovery_kind?: string | null;
  evidence_family?: string | null;
  scoring_evidence_kind: EvidenceKind;
  observed_days: number | null;
  /** True iff this row is one of recovery_stats.observed_restoration_episodes (a measured
   *  duration). Evidence can be real and dated without yielding a usable duration. */
  counts_toward_observed_episodes: boolean;
  what_source_establishes?: string | null;
  source_quality?: string | null;
  sources: { url: string }[];
}

/** Source-coverage metrics for the CONTEXT pipeline network (iteration 9). Describes how
 *  completely the network is sourced — topology completeness and geometry completeness are
 *  deliberately separate numbers. Never a disruption measure; never enters ESDI. */
export interface NetworkCoverageClass {
  routes: number;
  /** Sum of every route's length. DOUBLE-COUNTS by design where a system relation and its
   *  constituent strings are both modelled — that is a correct hierarchy, not a duplicate. Use
   *  `distinct_network_km` for "how much pipe is there"; use this only for "how much did the
   *  routes total", which is a different question. */
  total_length_km: number;
  /** Union of the underlying ways: each kilometre counted once regardless of how many routes
   *  claim it. This is the honest answer to network extent. */
  distinct_network_km?: number;
  detailed_geometry_km?: number;
  generalized_geometry_km?: number;
  unresolved_gap_count?: number;
  canonical_entities?: number;
  by_entity_level?: Record<string, number>;
  single_component_routes: number;
  multi_component_routes: number;
  total_components: number;
  largest_route_components: number;
  routes_overlapping_analytic: number;
  geometry_source: Record<string, number>;
  route_quality: Record<string, number>;
  substance_basis: Record<string, number>;
}

export type NetworkCoverage = Record<string, NetworkCoverageClass>;

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
  tracked_refineries?: number;
  coverage_pct: number;
  gap_mtpa: number;
  excluded_non_fuels?: string[];
  /** Iteration 7 (§6): denominator-completeness metadata. DENOMINATOR completeness, distinct
   *  from event coverage. */
  reference_nameplate_mtpa?: number;
  reference_range_mtpa?: [number, number];
  reference_crude_nameplate_mtpa?: number;
  reference_year?: number;
  reference_definition?: string;
  denominator_coverage_pct?: number;
  denominator_coverage_basis?: string;
  facility_count?: number;
  excluded_facility_count?: number;
  excluded_condensate_splitters?: string[];
  gap_decomposition?: {
    excluded_condensate_splitters_mtpa: number;
    conservative_basis_understatement_mtpa: number;
    missing_crude_refineries_mtpa: number;
  };
  /** Canonical refinery linkage completeness (iteration 6, §9) — identity/linkage, NOT
   *  disruption coverage. */
  canonical_linkage?: {
    denominator_refineries: number;
    struck_refineries: number;
    mtpa_struck: number;
    pct_denominator_mtpa_struck: number;
    incidents_unresolved_to_registry: string[];
    note: string;
  };
  note: string;
}

export interface Coverage {
  reported_total_strikes: number;
  /** Iteration 6: now the OIL-SECTOR strike count (matches the oil benchmark universe), not
   *  all energy events. See numerator_definition + total_events_all_sectors. */
  enumerated_in_this_dataset: number;
  coverage_ratio: number;
  total_events_all_sectors?: number;
  numerator_definition?: string;
  by_period: { period: string; strikes: number; cumulative: number }[];
  source_url: string;
  note: string;
}

/** Per-sector coverage matrix (iteration 6, §5). EVENT / ASSET-INVENTORY / RECOVERY-EVIDENCE
 *  coverage are kept as separate concepts; only the oil sectors carry a defensible event
 *  benchmark, others get an honest descriptive state, never a fabricated percentage. */
export interface CoverageMatrixEntry {
  event_count: number;
  discovery_sources: string;
  has_event_benchmark: boolean;
  asset_inventory_count: number;
  /** RECOVERY-EVIDENCE coverage: any recovery evidence (observed + partial restarts). */
  recovery_episodes: number;
  recovery_observed_episodes?: number;
  disrupted_facilities: number;
  event_coverage_state: string;
  last_audit: string;
}

/** Experimental gas-processing exposure (iteration 6, §18). A WITHIN-CENSUS share, never a
 *  national figure, and deliberately excluded from the headline ESDI. */
/** A single source-backed observed consequence of a strike (iteration 6, §25-28). Every
 *  effect carries an evidence tag; region population is never an effect here. */
export type EffectEvidence = "observed" | "estimated" | "modelled" | "unknown";
export interface StrategicEffect {
  effect_type: string;
  evidence_kind: EffectEvidence;
  source_quality?: string | null;
  value_numeric: number | null;
  value_unit: string | null;
  currency: string | null;
  cost_year: string | null;
  as_of_date: string | null;
  value_text: string | null;
  source_url: string | null;
}
export interface StrategicEffects {
  national: StrategicEffect[];
  by_incident: Record<string, StrategicEffect[]>;
}

export interface GasProcessingIndex {
  experimental: boolean;
  in_headline_esdi: boolean;
  graduation_decision?: string;
  graduation_reasons?: string[];
  census_plants: number;
  census_bcm_y: number;
  struck_plants: number;
  disrupted_bcm_y_weighted: number;
  within_census_exposure_pct: number | null;
  uncertain_bcm_y: number;
  aggregate_bcm_y: number;
  struck: { asset_id: string; name: string | null; bcm_y: number; disruption_weight: number }[];
  caveat: string;
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
  /** §27: sensitivity under the explicitly-FALSE assumption that uncovered gas+coal are zero —
   *  NOT a second valid ESDI. Prefer this clearly-named field. */
  uncovered_zero_assumption_sensitivity?: number;
  /** @deprecated §27 alias of uncovered_zero_assumption_sensitivity (kept for N-1 payloads). */
  esdi_all_sectors?: number;
  /** Model E (§23): the headline if transmission were removed from the composite. */
  esdi_excluding_transmission?: number | null;
  esdi_renormalization_note?: string;
  transmission_concentration?: {
    top: { name: string; region_code: string | null; pct: number }[];
    occupied_share_pct: number;
    note: string;
  };
  /** Transmission audit alternatives (iteration 6, §21-23) — a sensitivity, not a tuning knob. */
  transmission_sensitivity?: {
    saturation_constant: number;
    raw_burden: number;
    saturation_sweep: { saturation: number; sector_value: number }[];
    distinct_affected_regions: number;
    distinct_facilities: number;
    top_region_share_pct: number | null;
    per_region_saturated: { region_code: string | null; burden: number; saturated_value: number }[];
    /** §23 alternative formulations (A current, B per-region, C breadth/intensity, D distinct
     *  facilities, E ESDI if removed). */
    alternative_models?: {
      A_current_global_saturation: number;
      B_per_region_saturation_breadth_aware: number;
      C_breadth_affected_regions: number;
      C_intensity_max_region_pct: number;
      D_distinct_facility_burden: number;
      E_esdi_if_transmission_removed?: number | null;
      note: string;
    };
    note: string;
    red_team_verdict: string;
  };
  sectors: Record<string, number>;
  sectors_covered: string[];
  sectors_uncovered: string[];
  heating_season: boolean;
  denominators: { refining_mtpa: number; electric_generation_mw: number; transmission_saturation_events: number };
  /** Census vintage per denominator. A capacity base without its date reads as current when it is not. */
  denominator_basis?: Record<string, {
    source: string;
    census_vintage: string;
    source_frozen?: string;
    known_bias?: string;
    audit?: string;
  }>;
  incident_total: number;
  incidents_with_quantified_capacity: number;
  assessed_degradation: AssessedDegradation;
  recovery_stats: RecoveryStats;
  coverage_detail: CoverageDetail;
  live_disruptions: LiveDisruption[];
  /** Machine-generated decomposition of the headline and each sector (iteration 11).
   *  Optional: an N-1 payload from a lagging CDN edge predates it, and the Inspector says so
   *  rather than the app breaking. */
  explanations?: Explanations;
  /** Complete dated recovery-evidence log. Optional: an N-1 payload served by a lagging CDN
   *  edge during a deploy predates it, and the UI degrades to "no evidence" rather than break. */
  recovery_events?: RecoveryEvent[];
  /** Context-network source coverage (iteration 9). Optional for the same deploy-window reason. */
  network_coverage?: NetworkCoverage;
  regions: Record<string, RegionSnapshot>;
  not_modelled: Record<string, string>;
  coverage: Coverage | null;
  coverage_matrix?: Record<string, CoverageMatrixEntry>;
  experimental_indices?: { gas_processing: GasProcessingIndex | null };
  strategic_effects?: StrategicEffects;
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
  /** Build-to-build change ledger (iteration 11). Small and needed for the ribbon's delta
   *  chip on first paint, so it loads with the bundle rather than lazily. Null when the
   *  payload predates it — the UI then says the comparison is unavailable rather than
   *  showing a delta of zero, which would claim a quiet build that was never compared. */
  buildChanges: BuildChanges | null;
  /** Result of the schema compatibility check performed at load time. Optional context
   *  layers (rivers, pipeline networks) are lazy-loaded via loadContextLayer(), not held
   *  on the bundle (§16). */
  schema: SchemaCheck;
}

// --- canonical pipeline registry (iteration 10) -------------------------------------------
// Identity, source mappings, temporal status and geometry completeness for one pipeline
// entity. Kept separate from the route GeoJSON because that is component-level: a fragmented
// route has up to 125 components, and repeating the registry on each would be absurd.

/** One source record mapped to a canonical entity. Many-to-many in both directions. */
export interface PipelineSourceMapping {
  source_system: string;
  source_id: string;
  /** `represents` one-to-one · `aggregates` source covers several of ours · `part_of` inverse. */
  relationship: string;
  confidence: string;
  evidence: string | null;
  /** The source's own name, preserved verbatim so a judgement can be revisited. */
  source_native: string | null;
}

/** A status assertion valid over an interval. Three KINDS are tracked separately, because a
 *  pipe can be physically intact, operationally available, and carrying zero commercial flow
 *  all at once — collapsing them into one "status" loses exactly the distinction that matters. */
export interface PipelineStatusRecord {
  status_kind: "physical" | "operational" | "commercial_flow" | string;
  status_value: string;
  valid_from: string | null;
  valid_to: string | null;
  observed_at: string | null;
  source_url: string | null;
  source_date: string | null;
  source_tier: string | null;
  note: string | null;
}

/** One sourced connection assertion, attached to both canonical ends where both exist.
 *  A connection can be KNOWN without being DRAWABLE — that is the whole reason nodes carry
 *  `geography_precision` and are allowed to have none. */
export interface PipelineConnection {
  relation: string;
  other: string;
  other_id: string | null;
  direction: "from" | "to";
  node_id: string | null;
  node_name: string | null;
  node_type: string | null;
  node_country: string | null;
  /** `none` here means the connection point has no public coordinate and nothing is drawn. */
  node_geography_precision: string | null;
  node_sources: { source_system: string; source_id: string; point_eic: string | null }[];
  substance: string | null;
  source_quality: string | null;
  source_url: string | null;
  linkage: string | null;
  linkage_reason: string | null;
  note: string | null;
}

/** An alias with provenance. A project nickname must point at an artifact that attests it;
 *  native names, romanisations, translations and abbreviations evidence themselves. */
export interface PipelineAlias {
  alias: string;
  alias_type: string;
  language: string | null;
  source_url: string | null;
  source_date: string | null;
  note: string | null;
}

export interface PipelineEntity {
  canonical_pipeline_id: string;
  canonical_name: string;
  aliases: string[];
  commodity: string;
  subtype: string | null;
  entity_level: string;
  parent_id: string | null;
  child_ids: string[];
  operator: string | null;
  owner: string | null;
  countries: string[];
  start_area: string | null;
  end_area: string | null;
  note: string | null;
  curated: boolean;
  sources: PipelineSourceMapping[];
  status: PipelineStatusRecord[];
  connections: PipelineConnection[];
  alias_records: PipelineAlias[];
  /** Segment-weighted. `unresolved_gap_count` is a COUNT: the missing length is deliberately
   *  never estimated, because the straight line between two components is not the pipe. */
  geometry: {
    detailed_geometry_km: number;
    generalized_geometry_km: number;
    unresolved_gap_count: number;
    routes: number;
  } | null;
}

export interface PipelineNode {
  canonical_node_id: string;
  node_name: string;
  node_type: string;
  country: string | null;
  /** Only `coordinate` precision may carry lon/lat. A topology-only node stays undrawable. */
  geography_precision: string;
  lon?: number | null;
  lat?: number | null;
}

export interface PipelineRegistry {
  entities: Record<string, PipelineEntity>;
  nodes: Record<string, PipelineNode>;
  generated_note: string;
}

/* ---------------------------------------------------------------------------
 * Explanations (iteration 11 §2-§6)
 *
 * These mirror pipeline/explain.py exactly. Nothing here is derived in the frontend: the
 * decomposition is computed beside the arithmetic it describes, and the client renders it.
 * Adding a computed field to this file would be the first step towards a second scoring model.
 * ------------------------------------------------------------------------- */

/** How a sector turns a disrupted facility into sector points. Not cosmetic: a capacity share
 *  and an event-burden count mean different things, and conflating them is what makes a reader
 *  believe transmission measures percent-of-grid-offline. */
export type Mechanism = "capacity_share" | "event_burden" | "unscored";

export interface SectorContribution {
  sector: string;
  mechanism: Mechanism;
  included: boolean;
  /** The sector's own value, 0-100, as displayed. */
  sector_value: number;
  raw_sector_value: number;
  nominal_weight: number;
  /** Weight after redistributing the weight of sectors with no denominator. */
  effective_weight: number;
  raw_effective_weight: number;
  /** What this sector adds to the headline, in the headline's own units. */
  index_points: number;
  /** The same figure before display rounding. The authoritative identity is built from these. */
  raw_index_points: number;
  excluded_reason: string | null;
}

export interface HeadlineExplanation {
  value: number;
  /** The composite before display rounding. `round(raw_value, 2) === value`, exactly. */
  raw_value: number;
  as_of: string;
  covered: string[];
  uncovered: string[];
  nominal_weights: Record<string, number>;
  effective_weights: Record<string, number>;
  contributions: SectorContribution[];
  sum_of_contributions: number;
  raw_sum_of_contributions: number;
  /** What the visible two-decimal column adds up to — a different number from the rounded
   *  total whenever the individual roundings do not cancel. */
  display_sum_of_contributions: number;
  display_rounding_residual: number;
  /** Present only when the residual is non-zero, naming it as rounding. */
  rounding_note: string | null;
  /** The authoritative identities. Exact; neither carries a tolerance. */
  reconciles_raw: boolean;
  reconciles_published: boolean;
  /** @deprecated same meaning as reconciles_raw. */
  reconciles: boolean;
  renormalisation_note: string;
  decay: { form: string; half_life_source: string; note: string };
  sensitivities: {
    zero_assumption?: number | null;
    all_sectors?: number | null;
    excluding_transmission?: number | null;
    renormalisation_note?: string | null;
  };
}

/** The factors that produced one facility's impairment multiplier, from the same function that
 *  produced the score. A reader must be able to see WHY, not just the final number. */
export interface ImpairmentTrace {
  confidence_weight: number;
  cause_weight: number;
  damage_severity: number;
  initial_impairment: number;
  days_elapsed: number;
  half_life_days: number;
  half_life_kind: string;
  decay_factor: number;
  reconstitution_cap_applied: boolean;
  form: string;
}

export interface ContributingFacility {
  asset_id: string;
  name: string | null;
  asset_class: string | null;
  region_code: string | null;
  driving_incident_id: string | null;
  mechanism: Mechanism;
  /** How damaged, how well attested, how long ago. */
  impairment_weight: number;
  /** This facility's addition to the sector value, in sector percentage points. */
  sector_points: number;
  raw_sector_points: number;
  /** capacity_share mechanism only. */
  capacity_share_pct?: number;
  capacity_basis?: string;
  capacity_value?: number | null;
  /** event_burden mechanism only — NOT a capacity share, and deliberately not named like one. */
  event_burden_units?: number;
  voltage_kv?: number | null;
  burden_note?: string;
  impairment_trace?: ImpairmentTrace;
  recovery_status: string | null;
  evidence_kind: string | null;
  evidence_family: string | null;
}

export interface SectorExplanation {
  sector: string;
  basis: "capacity_mtpa" | "capacity_mw" | "event_burden" | "uncovered";
  mechanism: Mechanism;
  value: number;
  raw_value: number;
  zero_basis: ZeroBasis;
  zero_note: string | null;
  contributing: ContributingFacility[];
  contributing_count: number;
  sum_of_contributions: number;
  raw_sum_of_contributions: number;
  limitations: string[];
  denominator: {
    value: number;
    unit: string;
    source: string | null;
    vintage: string | null;
    known_bias?: string | null;
    facility_count?: number | null;
    completeness_pct?: number | null;
  } | null;
  /** Transmission only — it is an event-burden proxy, never a share of grid offline. */
  proxy_warning?: string;
  raw_burden?: number;
  saturation_sweep?: { saturation: number; sector_value: number }[];
  concentration?: Snapshot["transmission_concentration"];
  ex_transmission_composite?: number | null;
}

export interface Explanations {
  headline: HeadlineExplanation;
  sectors: Record<string, SectorExplanation>;
}

/** The four ways a published 0.00 can arise. They are different facts, and collapsing them is
 *  how UNKNOWN silently becomes ZERO. Null when the figure is not actually zero. */
export type ZeroBasis =
  | "NO_RECORDED_IMPAIRMENT"
  | "IMPAIRMENT_ONLY_IN_UNCOVERED_SECTOR"
  | "COVERED_SECTOR_SIGNAL_ROUNDS_TO_ZERO"
  | "NOT_APPLICABLE"
  | null;

export interface RegionExplanation {
  code: string;
  name: string | null;
  value: number;
  /** Published before rounding. A region reading 0.00 with a positive raw value has a real
   *  signal below display resolution, not an absence. */
  raw_value: number;
  contributions: {
    sector: string; mechanism: Mechanism; sector_value: number; raw_sector_value: number;
    effective_weight: number; index_points: number; raw_index_points: number;
  }[];
  sum_of_contributions: number;
  raw_sum_of_contributions: number;
  display_sum_of_contributions: number;
  display_rounding_residual: number;
  reconciles_raw: boolean;
  reconciles: boolean;
  zero_basis: ZeroBasis;
  unscored_sectors: string[];
  zero_note: string | null;
}

/* ---------------------------------------------------------------------------
 * Build-to-build change ledger (iteration 11 §7-§10). Mirrors pipeline/diff_builds.py.
 * ------------------------------------------------------------------------- */

/** world = something happened · data = the record changed, the world did not ·
 *  decay = nothing changed, time passed · methodology = we changed how we measure. */
export type ChangeNature = "world" | "data" | "time_progression" | "methodology";

/** How a row relates to the world's timeline versus the record's. Evidence arriving today about
 *  a restoration three months ago is not a restoration today. */
export type RecordClass =
  | "current_event"
  | "historical_record_added"
  | "historical_evidence_added"
  | "correction"
  | "withdrawal"
  | "input_change";

/** Provenance of the comparison. The baseline is an immutable commit, never the worktree. */
export interface Lineage {
  source: "git" | "none";
  production_branch: string;
  baseline_ref: string | null;
  previous_commit: string | null;
  previous_commit_subject: string | null;
  previous_commit_date: string | null;
  current_branch: string | null;
  current_commit: string | null;
  worktree_dirty: boolean | null;
  on_production_branch: boolean;
  previous_is_ancestor: boolean;
  valid: boolean;
  mode: "production" | "development" | "backward" | "invalid";
  reason: string | null;
  worktree_payload_differs_from_baseline: boolean | null;
}

export interface BuildChange {
  category: string;
  nature: ChangeNature;
  record_class: RecordClass;
  id: string;
  asset_id: string | null;
  label: string;
  /** When the thing happened in the world. */
  effective_date: string | null;
  /** The build in which the record first carried it. Different concepts. */
  first_seen_as_of: string | null;
  date: string | null;
  detail: string;
  sources?: number;
  fields?: string[];
  urls?: string[];
  rescales_sector?: boolean;
}

export interface SectorAttributionRow {
  sector: string;
  index_points_before: number;
  index_points_after: number;
  delta: number;
  sector_value_before: number;
  sector_value_after: number;
  weight_changed: boolean;
  rescaled: boolean;
}

export interface FacilityAttributionRow {
  sector: string;
  asset_id: string;
  name: string | null;
  sector_points_before: number;
  sector_points_after: number;
  delta: number;
  entered: boolean;
  left: boolean;
  /** False where a cap, a denominator change or a weight change means this row is an account
   *  of where movement sits rather than a decomposition of what caused it. */
  attribution_exact: boolean;
  non_additive_reason: string | null;
}

export interface BuildChanges {
  previous_build: string | null;
  previous_as_of: string | null;
  current_build: string | null;
  current_as_of: string | null;
  esdi_before: number | null;
  esdi_after: number | null;
  esdi_delta: number | null;
  as_of_direction: "forward" | "backward" | "same_date" | null;
  /** No input changed; only the evaluation date moved. Direction-neutral on purpose — a
   *  backwards comparison makes the same mechanism raise the index. */
  time_progression_only: boolean;
  time_progression_note: string | null;
  previous_build_fingerprint: string | null;
  current_build_fingerprint: string | null;
  input_groups_changed: string[];
  input_fingerprints_comparable: boolean;
  lineage: Lineage | null;
  attribution_separable: boolean;
  non_separable_reason: string | null;
  change_count: number;
  by_nature: Record<ChangeNature, number>;
  by_category: Record<string, number>;
  by_record_class: Record<string, number>;
  changes: BuildChange[];
  sector_attribution: {
    rows: SectorAttributionRow[];
    sum_of_sector_deltas: number;
    headline_delta: number;
    exact: boolean;
  } | null;
  facility_attribution: FacilityAttributionRow[];
  rescaled_sectors: string[];
  /** Present only when there was no previous build to compare against. */
  unavailable_reason?: string;
  attribution_note: string | null;
}

/* ---------------------------------------------------------------------------
 * Data quality and source freshness (iteration 11 §5). Mirrors pipeline/data_quality.py.
 *
 * Every statement here is derived at build time. Nothing in the component computes a freshness
 * claim, because a freshness statement written in React is true on the day it is typed and
 * silently false afterwards.
 * ------------------------------------------------------------------------- */

/** Whether the sector is inside the headline composite. INDEPENDENT of how it is measured —
 *  transmission is fully scored in the headline on an event-burden proxy, and a single ladder
 *  that called it "experimental" would read as excluded. */
export type IndexParticipation = "scored" | "not_scored";

/** What kind of measurement the sector rests on. Orthogonal to participation. */
export type MethodologyBasis =
  | "capacity_based"
  | "proxy_capacity_base"
  | "event_burden_proxy"
  | "experimental_census"
  | "uncovered";

export interface SectorQuality {
  sector: string;
  index_participation: IndexParticipation;
  methodology_basis: MethodologyBasis;
  basis_explanation: string;
  experimental_index: {
    in_headline_esdi: boolean | null;
    graduation_decision: string | null;
    graduation_reasons: string[];
    census_plants: number | null;
  } | null;
  mechanism: Mechanism | null;
  value: number | null;
  denominator_value: number | null;
  denominator_unit: string | null;
  denominator_source: string | null;
  denominator_vintage: string | null;
  known_bias: string | null;
  limitations: string[];
  proxy_warning?: string;
}

export type Freshness = {
  status: "current" | "ageing" | "stale" | "frozen" | "undated";
  age_days: number | null;
  note: string;
};

/** Whether this source can be cited as a dated publication — three situations a single boolean
 *  would flatten into one. Only `release_expected_but_absent` is a finding. */
export type Citability =
  | "citable_release"
  | "snapshot_of_a_live_source"
  | "internal_versioned_by_repo"
  | "release_expected_but_absent";

export interface SourceRecord {
  source_id: string;
  name: string;
  publisher: string;
  role: string;
  applies_to: { sectors: string[]; asset_classes: string[] };
  url: string | null;
  licence: string | null;
  release_identifier: string | null;
  release_expectation: string;
  has_release_identifier: boolean;
  citability: Citability;
  /** What the data describes — distinct from when it was published or fetched. */
  content_vintage: string | null;
  retrieved_at: string | null;
  /** Closed vocabulary: a cache mtime is OUR filesystem's opinion and must never read as
   *  publisher freshness. On a fresh clone it says today for a file never downloaded. */
  retrieval_basis: "fetch_manifest" | "http_source_metadata" | "local_cache_mtime"
    | "repo_commit_timestamp" | "unknown";
  retrieval_basis_label: string;
  retrieval_is_publisher_signal: boolean;
  /** A missing release id is a finding only where the publisher issues relevant releases. */
  release_gap_matters: boolean;
  release_gap_note: string | null;
  frozen_at: string | null;
  freshness: Freshness;
  limitations: string[];
}

export interface CannotTellYou {
  question: string;
  answer: string;
  basis: string;
}

export interface DataQuality {
  as_of: string;
  build_time: string | null;
  build_date_is_not_a_source_date: string;
  sector_states: SectorQuality[];
  sources: SourceRecord[];
  sources_by_freshness: Record<string, number>;
  sources_without_release_identifier: string[];
  release_gaps: { source_id: string; name: string; note: string | null }[];
  citability_note: string;
  capacity_measurement_audit: {
    total_events: number;
    applicable_events: number;
    measured_of_applicable: number;
    buckets: Record<string, number>;
    by_asset_class: Record<string, Record<string, number>>;
    definition: string;
  } | null;
  cannot_tell_you: CannotTellYou[];
}

/* ---------------------------------------------------------------------------
 * Historical-state comparison (iteration 11 P6). Mirrors pipeline/history.py.
 *
 * This series answers "what does TODAY'S dataset and model estimate for date A", never "what
 * did the dashboard say on date A". No archive of past builds exists. The distinction ships in
 * `semantics` so the UI renders the pipeline's own words rather than paraphrasing them.
 * ------------------------------------------------------------------------- */

export interface HistorySemantics {
  kind: "historical_state_comparison";
  headline: string;
  what_this_answers: string;
  what_this_does_not_answer: string;
  controlling_dates: { concept: string; field: string; rule: string }[];
  delta_convention: string;
  series_resolution_note: string;
}

export interface HistorySeries {
  dates: string[];
  step_days: number | null;
  covered: string[];
  effective_weights: Record<string, number>;
  esdi: number[];
  raw_esdi: number[];
  index_points: Record<string, number[]>;
  raw_index_points: Record<string, number[]>;
  sector_values: Record<string, number[]>;
  contributing_facilities: number[];
  /** Which facilities were contributing at each step. Identity, not a count:
   *  "which stopped contributing between A and B" cannot be answered by a number. */
  contributing_asset_ids: string[][];
  incidents_to_date: number[];
  recovery_evidence_to_date: number[];
  reconstitutions_to_date: number[];
  semantics: HistorySemantics;
}

/** A comparison endpoint. Both dates are kept because the series is weekly and a requested day
 *  is resolved backwards to a series point — presenting the requested date alone would pass a
 *  weekly point off as a daily observation. */
export interface ResolvedPoint {
  requested_date: string;
  resolved_series_date: string;
  step: number;
  exact: boolean;
}

/* ---------------------------------------------------------------------------
 * Recovery lifecycle (iteration 11 P7). Mirrors pipeline/lifecycle.py.
 *
 * The evidence families are load-bearing and stay distinct: service restored is not facility
 * rebuilt, and flow rerouted is not a repair at all.
 * ------------------------------------------------------------------------- */

export type EvidenceFamily =
  | "service_restoration" | "unit_restart" | "facility_reconstitution"
  | "flow_rerouting" | "estimate";

export interface Milestone {
  stage: string;
  date: string | null;
  date_precision: string | null;
  /** Whether the MILESTONE was reported — not how the decay behind it is scored. */
  status: "observed" | "estimated" | "modelled";
  /** How this evidence drives the decay. A sourced milestone can still leave a modelled
   *  half-life, and conflating the two labels real reports as guesses. */
  drives_scoring_as?: string;
  evidence_family: EvidenceFamily | null;
  recovery_kind?: string | null;
  what_source_establishes?: string | null;
  /** Estimate milestones are deliberately UNDATED: a projected horizon is not an event that
   *  happened on a day, and dating it would make it look observed. */
  estimate_days?: { lower: number | null; central: number | null; upper: number | null };
  estimate_method?: string | null;
  meaning: string;
}

export interface LifecycleSource {
  url: string;
  published: string | null;
  published_basis: "sourced" | "unavailable";
}

export interface LifecycleEpisode {
  episode_id: string;
  incident_id: string;
  asset_id: string;
  asset_name: string | null;
  asset_class: string | null;
  sector: string | null;
  region_code: string | null;
  incident_date: string;
  cause: string | null;
  confidence: string | null;
  status: string | null;
  recovery_status: string | null;
  evidence_family: EvidenceFamily | null;
  /** A source says the facility was restored but records no date, so it appears on no timeline
   *  and drives no scoring change. Neither "restored" nor "no evidence" describes that. */
  undated_restoration_claim: boolean;
  undated_restoration_note: string | null;
  scoring_evidence_kind: string;
  milestones: Milestone[];
  /** Stages with no evidence either way. Never rendered as pending or complete. */
  stages_unknown: string[];
  duration_days: number | null;
  duration_start: string | null;
  duration_end: string | null;
  initial_impairment: number | null;
  half_life_days: number | null;
  half_life_kind: string | null;
  /** The MODELLED disruption weight the index consumed — not measured repair progress. */
  trajectory: { date: string; weight: number }[];
  sources: LifecycleSource[];
  publication_date_available: boolean;
  /** Only ever populated from a build ledger with provable lineage, and it means "first present
   *  in this dashboard" — never "when the report was published" or "when anyone learned it". */
  first_seen: { build_date: string; commit: string } | null;
}

export interface DurationSummary {
  asset_class: string;
  evidence_family: string;
  duration_start: string;
  duration_end: string | null;
  mixed_endpoints: boolean;
  n: number;
  sufficient: boolean;
  reason?: string;
  values: number[];
  median?: number;
  min?: number;
  max?: number;
  q1?: number;
  q3?: number;
}

export interface LifecyclePayload {
  temporal_model: {
    concepts: { field: string; label: string; available: boolean; note: string }[];
    warning: string;
  };
  reconstruction_caveat: string;
  layer_labels: { observed: string; model: string };
  stage_order: string[];
  stage_meaning: Record<string, string>;
  episode_count: number;
  episodes_by_family: Record<string, number>;
  episodes_with_publication_date: number;
  episodes_with_first_seen: number;
  episodes: LifecycleEpisode[];
  distributions: {
    min_sample: number;
    by_class_family: Record<string, DurationSummary>;
    by_family: Record<string, DurationSummary>;
    note: string;
  };
}
