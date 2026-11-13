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
  /** Iteration 19. Names in the country's own script, for search. */
  aliases?: string[];
  regional_groups?: string[];
  maturity?: "monitored" | "research_preview";
  /** Recovery status is withheld here while an attack campaign is active, recent or uncertain. */
  campaign_restricted?: boolean;
  /** Iteration 21. Newest review date of the country's published records; null = no qualifying
   *  record yet. Absent in older builds and for the theatre. A date, never a count. */
  record_reviewed?: string | null;
}

/** A named set of systems: navigation and filtering only, never a scored unit. */
export interface ManifestGroup {
  label: string;
  kind: "geographic" | "membership";
  note: string;
  /** Present when the group has its own overview page at `?group=<slug>`. */
  slug: string | null;
  context: string | null;
  members: string[];
}

/** Totals for the country systems together (iteration 17). Never one figure per country. */
export interface CorpusTotals {
  countries: number;
  records: number;
  episodes: number;
  independently_reviewed: number;
  blind_reviewed: number;
  registry_sources: number;
  records_with_observed_recovery: number;
  records_with_recovery_estimate_only: number;
  records_reported_fully_back: number;
  research_lanes_complete: number;
  research_lane_states?: Record<string, number>;
  research_lanes: number;
  note: string;
}

export interface Manifest {
  schema_version: number;
  build_time: string;
  corpus?: CorpusTotals;
  selection: { rule: string; source: string; source_url: string; caveat: string; regional_rule?: string };
  groups?: Record<string, ManifestGroup>;
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
    /** Iteration 19: how precisely events are placed here, and why. Admin-1 is a maximum. */
    precision_policy?: { kinetic?: "country" | "admin1"; other?: "country" | "admin1"; no_event_units?: string[]; reason: string };
  };
  maturity?: "monitored" | "research_preview";
  campaign_state?: { state: string; checked: string; basis: string; limitation?: string } | null;
  aliases?: string[];
  regional_groups?: string[];
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
  recovery_coverage?: RecoveryCoverage;
  source_families?: { present: string[]; labels: Record<string, string>; note: string };
  citation_quality?: CitationQuality;
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
    /** Iteration 18: lane counts by reader-facing state. Never collapsed into a percentage. */
    lane_states?: Record<string, number>;
    first_systematic_pass?: string | null;
    research_cadence_days: number;
    next_due: string | null;
    note: string;
  };
  stale_policies: Record<string, { days: number; rationale: string }>;
  review_summary: { blind_reviewed?: number; dual_reviewed: number; legacy_single_review: number; note: string };
  publication_policy: {
    withheld_records: number;
    campaigns: { campaign_id: string; name: string; status: string; status_checked: string;
                 status_basis: string; policy_applied: boolean }[];
    release_rule: { id: string; status: string; text: string; release_after_end_days: number } | null;
  };
  episode_bases: Record<string, string>;
  /** Citations of the published events, described inside this country only (iteration 17). */
  source_health?: SourceHealth;
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

/** Counts only. "not_recorded" is not "not_opened". Never compared across countries. */
export interface SourceHealth {
  events: number;
  citations: number;
  publishers: number;
  by_role: Record<string, number>;
  by_language: Record<string, number>;
  opened: { opened: number; not_opened: number; not_recorded: number };
  dated: number;
  single_source_events: number;
  single_origin_events?: number;
  discovery_only_events?: number;
  origin_rule?: string;
  events_with_first_party_source: number;
  first_party_roles: string[];
  first_party_excludes?: string;
  note: string;
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
  lanes?: ResearchLane[];
  outcome: Record<string, number>;
  // Present only under the campaign policy, where the outcome carries the published count alone.
  under_review?: boolean;
}

/** A lane of a systematic pass. Passes before iteration 18 carry `status`; since then `execution`
 *  (what the analyst did) and `source_window` (what the publisher has made available). */
export interface ResearchLane {
  lane: string;
  source_family?: string;
  status?: "complete" | "partial";
  reason?: string;
  covered_through?: string | null;
  universe_kind?: string;
  execution?: string;
  source_window?: string;
  languages_required?: string[];
  languages_executed?: string[];
  queries_declared?: number | null;
  queries_run?: number | null;
  items_enumerated?: number | null;
  items_in_universe?: number | null;
  limitation?: string | null;
  finding?: string | null;
  carried_forward?: boolean;
  /** Set when the pass's own search allowance ran out in this lane; the lane is then never complete. */
  stopped_by?: "search_limit" | null;
}

export interface CitationQuality {
  citations: number;
  with_publication_date: number;
  languages: Record<string, number>;
  event_date_precision: Record<string, number>;
  link_check: { reachable: number; redirected: number; blocked: number; dead: number; error: number } | null;
  link_check_date: string | null;
  link_check_note: string | null;
}

export interface RecoveryCoverage {
  observed: number;
  estimate: number;
  other_statement: number;
  researched_no_public_evidence: number;
  not_researched: number;
  withheld_active_campaign: number;
  unresearched_by_class: Record<string, number>;
  policy: string;
}

export interface RecentEpisode {
  system_id: string;
  country: string;
  episode_id: string;
  episode_name: string | null;
  basis: string;
  records: number;
  first_date: string;
  last_date: string;
  date_precision: string;
  classes: string[];
  causes: string[];
  // effect_on_country_page: the record's system is under the campaign policy, so no list repeats its effect.
  members: { date: string; date_precision: string; region: string; effect: string | null; effect_on_country_page: boolean; withheld: boolean }[];
  more_members: number;
}

export interface RecentEvidence { order: string; scope: string; note: string; episodes: RecentEpisode[] }

/** One member of a regional overview. National figures and research process; no disruption count. */
export interface GroupSystem {
  system_id: string;
  name: string;
  a3: string;
  gcc_member: boolean;
  opec_member: boolean;
  maturity: "monitored" | "research_preview";
  recovery_status_withheld: boolean;
  values: Record<string, number | null>;
  role: string | null;
  last_systematic_pass: string | null;
  lane_states: Record<string, number>;
  languages_required: string[];
  languages_executed: string[];
  reporting_environment: string;
  /** Where the system places an attack record: the country as a whole, or a first-level region. */
  attack_records_placed?: "country" | "admin1";
}

export interface GroupContext {
  group: string;
  label: string;
  note: string;
  statement: string;
  not_built: string;
  /** Every member of the view, by name, in registry (alphabetical) order. */
  member_names?: string[];
  memberships: Record<"gcc" | "opec", { label: string; note: string; members: string[]; member_names?: string[];
                                        as_of?: string | null; basis?: string | null }>;
  order: string;
  sources: Record<string, { name: string; url: string; release: string | null; attribution: string | null }>;
  metrics: Record<string, { label: string; unit: string; definition: string; year: number; source_id: string }>;
  accounting_convention?: string;
  systems: GroupSystem[];
  region: Record<string, { value: number | null; world_share: number | null; reason: string | null }>;
  recent?: RecentEvidence;
}

export interface DataQualityLane {
  lane: string; source_family?: string; execution?: string; source_window?: string; covered_through?: string | null;
  languages_required?: string[]; languages_executed?: string[]; limitation?: string | null; finding?: string | null;
  state: string;
}

export interface DataQuality {
  note: string;
  context_vintage: { source: string; url: string; release: string; retrieved: string; comparison_year: number;
                     update_cadence: string; countries: number; note: string };
  systems: { system_id: string; name: string; reporting_environment: string; last_systematic_pass: string | null;
             first_systematic_pass: string | null; lane_states: Record<string, number>; lanes: DataQualityLane[];
             source_families: Record<string, string>;
             sources_checked: { name: string; last_checked: string | null; stale_after_days: number | null }[] }[];
  recovery_by_class: { note: string; rows: { class: string; class_label: string; kind: string; n: number;
                                             cases_days?: number[]; range_days?: [number, number]; median_days?: number }[] };
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
  // Iteration 20: a figure carries its uncertainty. `value` is null for a bound, a range or a
  // disputed figure; `measure` says whether it is an amount affected or the facility's size.
  // Nothing sums these figures.
  capacity_affected: {
    value: number | null;
    value_min: number | null;
    value_max: number | null;
    qualifier: "exact" | "about" | "at_least" | "at_most" | "range" | "component_only" | "disputed";
    measure: "affected" | "facility_size" | "other";
    unit: string;
    source_says: string;
  } | null;
  sources: { url: string; publisher?: string; date?: string; language?: string;
             source_role?: string; opened?: boolean | null;
             /** A non-English source's own headline and an English gloss (iteration 19). */
             title_original?: string; title_en?: string;
             /** The page's state at the last automated link check (iteration 21); absent if never checked. */
             link_check?: "reachable" | "redirected" | "blocked" | "dead" | "error" }[];
  /** Present when the source dated the event in another calendar: what it wrote, and how it was converted. */
  source_date_text?: string;
  date_calendar?: "gregorian" | "solar_hijri" | "hijri";
  conversion_basis?: string;
  recovery: { research_status: string; kind: string | null; date: string | null;
              evidence: string | null; url: string | null };
  review: {
    reviewed_at: string;
    review_status: "blind_reviewed" | "dual_reviewed" | "legacy_single_review";
    /** Blind three-role review (iteration 17): each role's verdict, never its reasoning. */
    roles?: { evidence: string; safety: string; taxonomy: string };
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

// ---- loading: one request per file per page (iteration 21) ----------------------------------
//
// Every view and panel asks for what it needs and the same file is never fetched twice in a page:
// the home, the Gulf overview and the switcher in every header all want the manifest, and a reader
// going home -> Gulf -> home used to download the 430 KB world map three times. A failure is NOT
// kept, so the next caller retries; a validated result is kept for the life of the page, which is
// right for files that change only when the site is rebuilt.
//
// No abort signal reaches the shared request. A view that is left simply ignores the answer (each
// view checks that it is still the one on screen), and the finished download is then ready if the
// reader comes back.

const loads = new Map<string, Promise<unknown>>();

export function once<T>(key: string, load: () => Promise<T>): Promise<T> {
  const held = loads.get(key) as Promise<T> | undefined;
  if (held) return held;
  const p = load();
  loads.set(key, p);
  p.catch(() => { if (loads.get(key) === p) loads.delete(key); });
  return p;
}

/** Test seam: forget every held request. */
export function forgetLoads() {
  loads.clear();
}

async function getJson<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}/${path}`, { cache: "no-cache" });
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json() as Promise<T>;
}

/** The manifest, fetched once per page. A malformed one is refused here, so every view fails as
 *  "the system list is unavailable" instead of throwing while it renders. */
export function loadManifest(): Promise<Manifest> {
  return once("global/manifest.json", async () => {
    const m = await getJson<Manifest>("global/manifest.json");
    const bad = manifestProblems(m);
    if (bad.length) throw new Error(`manifest malformed (${bad.join(", ")})`);
    return sanitizeManifest(m);
  });
}

/** One country's three files, validated, fetched once per page. */
export function loadCountry(entry: ManifestSystem): Promise<CountryBundle> {
  return once(`country:${entry.id}`, async () => {
    const [system, events, regions] = await Promise.all([
      getJson<CountrySystem>(`${entry.root}/system.json`),
      getJson<{ events: CountryEvent[]; episodes?: Episode[] }>(`${entry.root}/events.json`),
      getJson<GeoJSON.FeatureCollection>(`${entry.root}/regions.geojson`),
    ]);
    if (system.system_id !== entry.id) {
      throw new Error(`${entry.root}/system.json describes ${system.system_id}, not ${entry.id}`);
    }
    const bad = shapeProblems(system, events, regions);
    if (bad.length) throw new Error(`${entry.root}: malformed payload (${bad.join(", ")})`);
    return { system, events: events.events, episodes: events.episodes ?? [], regions };
  });
}

/** Start loading a country before the reader opens it: on an explicit hover or focus of a link to
 *  it, never for every system at once. Silent: the view's own load reports any failure, and a
 *  failed prefetch is not kept, so the view retries. */
export function prefetchCountry(id: string): void {
  loadManifest()
    .then((m) => {
      const e = m.systems.find((s) => s.id === id && s.kind === "country");
      return e ? loadCountry(e) : undefined;
    })
    .catch(() => undefined);
}

/** One country's system.json alone (iteration 21), for a view that describes a system without its
 *  events or map. Refused on the same terms as a full load. */
export function loadCountrySystem(entry: ManifestSystem): Promise<CountrySystem> {
  // Validated inside once(): a refused file rejects, and a rejection is never kept, so it is retried.
  return once(`system:${entry.id}`, async () => {
    const system = await getJson<CountrySystem>(`${entry.root}/system.json`);
    if (system.system_id !== entry.id) {
      throw new Error(`${entry.root}/system.json describes ${system.system_id}, not ${entry.id}`);
    }
    const bad = shapeProblems(system, { events: [] });
    if (bad.length) throw new Error(`${entry.root}: malformed payload (${bad.join(", ")})`);
    return system;
  });
}

/** The parts of a country payload the view reads without a guard. A malformed one is refused at
 *  load, so it fails as "this system could not be loaded" and the others stay usable, instead
 *  of throwing during render and taking the whole dashboard down (iteration 17, §65). */
export function shapeProblems(system: unknown, events: unknown, regions?: unknown): string[] {
  const s = (system ?? {}) as Record<string, unknown>;
  const e = (events ?? {}) as Record<string, unknown>;
  const obj = (x: unknown) => typeof x === "object" && x !== null && !Array.isArray(x);
  const out: string[] = [];
  for (const k of ["sectors", "sources", "research_gaps", "onboarding_gate", "audit_docs"]) {
    if (!Array.isArray(s[k])) out.push(`${k} is not a list`);
  }
  for (const k of ["event_summary", "review_summary", "publication_policy", "research_freshness",
                   "geography", "profile", "taxonomy", "stale_policies", "inclusion_threshold",
                   "episode_bases"]) {
    if (!obj(s[k])) out.push(`${k} is missing`);
  }
  // Nested fields the view also reads unguarded (iteration 17, test-architecture red team).
  if (obj(s.geography) && !Array.isArray((s.geography as Record<string, unknown>).rulings ?? [])) {
    out.push("geography.rulings is not a list");
  }
  if (obj(s.event_summary) && !obj((s.event_summary as Record<string, unknown>).recovery_kinds)) {
    out.push("event_summary.recovery_kinds is missing");
  }
  if (Array.isArray(e.events) && (e.events as unknown[]).some((x) => !obj(x) || !obj((x as Record<string, unknown>).review)
      || !Array.isArray((x as Record<string, unknown>).sources) || !obj((x as Record<string, unknown>).recovery))) {
    out.push("an event lacks its review, sources or recovery");
  }
  if (regions !== undefined && !(obj(regions) && Array.isArray((regions as Record<string, unknown>).features))) {
    out.push("regions.features is not a list");
  }
  // Optional, but read unguarded when present (iteration 20, §122: found by a corrupt-file test).
  const sh = s.source_health as Record<string, unknown> | undefined;
  if (sh !== undefined && sh !== null && !(obj(sh) && obj(sh.opened) && obj(sh.by_role) && obj(sh.by_language))) {
    out.push("source_health is malformed");
  }
  const log = s.research_log as Record<string, unknown> | undefined;
  if (!obj(log) || !Array.isArray(log!.passes)) out.push("research_log.passes is not a list");
  // The research coverage explorer reads each pass's date, kind and window, and each lane's id,
  // without a guard (iteration 21). Lists inside a lane are guarded where they are read.
  else if ((log!.passes as unknown[]).some((p) => {
    const q = p as Record<string, unknown>;
    return !obj(p) || typeof q.date !== "string" || typeof q.kind !== "string" || !Array.isArray(q.window)
      || (q.lanes !== undefined && !(Array.isArray(q.lanes)
        && (q.lanes as unknown[]).every((l) => obj(l) && typeof (l as Record<string, unknown>).lane === "string")));
  })) out.push("a research pass lacks its date, kind or window, or has a lane without an id");
  if (!Array.isArray(e.events)) out.push("events is not a list");
  // Iteration 21: the rest of what the page reads without a guard, found by reading every
  // `.map`/`Object.entries` in the country view and its export.
  const field = (block: unknown, key: string) => (obj(block) ? (block as Record<string, unknown>)[key] : undefined);
  if (typeof s.evidence_readiness !== "string") out.push("evidence_readiness is missing");
  if (obj(s.profile) && !Array.isArray(field(s.profile, "metrics"))) out.push("profile.metrics is not a list");
  if (obj(s.inclusion_threshold) && !obj(field(s.inclusion_threshold, "clauses"))) out.push("inclusion_threshold.clauses is missing");
  const box = (b: unknown) => Array.isArray(b) && b.length === 4 && b.every((x) => typeof x === "number" && Number.isFinite(x));
  if (obj(s.geography) && !box(field(s.geography, "view_bounds")) && !box(field(s.geography, "bounds"))) {
    out.push("geography.bounds is not a box");
  }
  if (obj(log) && Array.isArray(log!.passes) && (log!.passes as unknown[]).some((p) => !obj(p) || !obj((p as Record<string, unknown>).outcome))) {
    out.push("a research pass lacks its outcome");
  }
  // Optional blocks, read unguarded inside when present.
  const optional: [string, string[]][] = [
    ["source_families", ["labels"]],
    ["citation_quality", ["languages", "event_date_precision"]],
    ["recovery_coverage", ["unresearched_by_class"]],
  ];
  for (const [k, inner] of optional) {
    const b = s[k];
    if (b !== undefined && b !== null && !(obj(b) && inner.every((i) => obj(field(b, i))))) out.push(`${k} is malformed`);
  }
  if (regions !== undefined && obj(regions) && Array.isArray((regions as Record<string, unknown>).features)
      && ((regions as Record<string, unknown>).features as unknown[]).some((f) => !obj(f))) {
    out.push("a region feature is not an object");
  }
  return out;
}

/** The parts of the manifest every view reads without a guard. A required part missing refuses the
 *  manifest; an optional part that is malformed is dropped by `sanitizeManifest` instead, so a bad
 *  corpus total costs one panel, not the system list (iteration 21). */
export function manifestProblems(x: unknown): string[] {
  const m = (x ?? {}) as Record<string, unknown>;
  const obj = (v: unknown) => typeof v === "object" && v !== null && !Array.isArray(v);
  const out: string[] = [];
  if (!Array.isArray(m.systems) || m.systems.length === 0) {
    out.push("systems is not a list");
  } else if ((m.systems as unknown[]).some((s) => {
    const r = s as Record<string, unknown>;
    return !obj(s) || typeof r.id !== "string" || typeof r.name !== "string" || typeof r.root !== "string"
      || (r.kind !== "theatre" && r.kind !== "country") || typeof r.evidence_readiness !== "string"
      || typeof r.reporting_environment !== "string";
  })) {
    out.push("a system lacks its id, name, kind, root, readiness or reporting environment");
  }
  const sel = m.selection as Record<string, unknown> | undefined;
  if (!obj(sel) || typeof sel!.rule !== "string" || typeof sel!.source_url !== "string") out.push("selection is missing");
  if (!obj(m.reporting_environments)) out.push("reporting_environments is missing");
  return out;
}

/** Drop optional manifest parts that would throw where they are read. Never invents a value. */
export function sanitizeManifest(m: Manifest): Manifest {
  const obj = (v: unknown) => typeof v === "object" && v !== null && !Array.isArray(v);
  const strings = (v: unknown) => Array.isArray(v) && v.every((s) => typeof s === "string");
  const box = (b: unknown) => Array.isArray(b) && b.length === 4 && b.every((x) => typeof x === "number" && Number.isFinite(x));
  const out: Manifest = { ...m };
  if (out.corpus !== undefined && !obj(out.corpus)) delete out.corpus;
  if (out.groups !== undefined) {
    const kept: Record<string, ManifestGroup> = {};
    if (obj(out.groups)) {
      for (const [id, g] of Object.entries(out.groups)) {
        if (obj(g) && typeof g.label === "string" && strings(g.members)) kept[id] = g;
      }
    }
    out.groups = kept;
  }
  out.systems = m.systems.map((s) => {
    const t: ManifestSystem = { ...s };
    if (t.aliases !== undefined && !strings(t.aliases)) delete t.aliases;
    if (t.regional_groups !== undefined && !strings(t.regional_groups)) delete t.regional_groups;
    if (t.bounds !== undefined && !box(t.bounds)) delete t.bounds;
    if (t.headline !== null && t.headline !== undefined && !(obj(t.headline) && typeof t.headline.value === "number")) t.headline = null;
    return t;
  });
  return out;
}

/** The parts of a regional context file the overview reads without a guard (iteration 21). */
export function groupContextProblems(x: unknown): string[] {
  const c = (x ?? {}) as Record<string, unknown>;
  const obj = (v: unknown) => typeof v === "object" && v !== null && !Array.isArray(v);
  const out: string[] = [];
  if (!obj(c.metrics) || Object.keys(c.metrics as object).length === 0
      || Object.values(c.metrics as object).some((m) => !obj(m) || typeof (m as Record<string, unknown>).label !== "string")) {
    out.push("metrics is missing");
  }
  if (!Array.isArray(c.systems) || (c.systems as unknown[]).some((s) => {
    const r = s as Record<string, unknown>;
    return !obj(s) || typeof r.system_id !== "string" || typeof r.a3 !== "string" || !obj(r.values)
      || !obj(r.lane_states) || !Array.isArray(r.languages_required) || !Array.isArray(r.languages_executed);
  })) {
    out.push("a system lacks its id, values, lane states or languages");
  }
  const ms = c.memberships as Record<string, unknown> | undefined;
  if (!obj(ms) || !obj(ms!.gcc) || !obj(ms!.opec)) out.push("memberships is missing");
  if (!obj(c.region) || (obj(c.metrics) && Object.keys(c.metrics as object).some((k) => !obj((c.region as Record<string, unknown>)?.[k])))) {
    out.push("region totals are missing");
  }
  if (!obj(c.sources)) out.push("sources is missing");
  if (c.member_names !== undefined && !Array.isArray(c.member_names)) out.push("member_names is not a list");
  const rec = c.recent as Record<string, unknown> | undefined;
  if (rec !== undefined && rec !== null && !(obj(rec) && recentProblems(rec).length === 0)) out.push("recent is malformed");
  return out;
}

/** The recent-evidence list, on the home and inside a regional context (iteration 21). */
export function recentProblems(x: unknown): string[] {
  const r = (x ?? {}) as Record<string, unknown>;
  const obj = (v: unknown) => typeof v === "object" && v !== null && !Array.isArray(v);
  if (!Array.isArray(r.episodes)) return ["episodes is not a list"];
  const bad = (r.episodes as unknown[]).some((e) => {
    const ep = e as Record<string, unknown>;
    return !obj(e) || typeof ep.system_id !== "string" || typeof ep.first_date !== "string"
      || !Array.isArray(ep.classes) || !Array.isArray(ep.causes) || !Array.isArray(ep.members)
      || (ep.members as unknown[]).some((m) => !obj(m));
  });
  return bad ? ["an episode lacks its date, classes, causes or members"] : [];
}

/** The data-quality summary on the home (iteration 21). */
export function dataQualityProblems(x: unknown): string[] {
  const d = (x ?? {}) as Record<string, unknown>;
  const obj = (v: unknown) => typeof v === "object" && v !== null && !Array.isArray(v);
  const out: string[] = [];
  if (!obj(d.context_vintage)) out.push("context_vintage is missing");
  if (!Array.isArray(d.systems) || (d.systems as unknown[]).some((s) => {
    const r = s as Record<string, unknown>;
    return !obj(s) || !Array.isArray(r.lanes) || !Array.isArray(r.sources_checked) || !obj(r.lane_states) || !obj(r.source_families)
      || (r.lanes as unknown[]).some((l) => !obj(l));
  })) {
    out.push("a system lacks its lanes, sources or states");
  }
  const rb = d.recovery_by_class as Record<string, unknown> | undefined;
  if (!obj(rb) || !Array.isArray(rb!.rows)) out.push("recovery_by_class.rows is not a list");
  return out;
}

/** Map polygons (the world, or a country's regions): a feature list of objects. Anything else is
 *  refused before MapLibre sees it. */
export function geometryProblems(x: unknown): string[] {
  const fc = (x ?? {}) as Record<string, unknown>;
  if (!Array.isArray(fc.features)) return ["features is not a list"];
  return (fc.features as unknown[]).some((f) => typeof f !== "object" || f === null) ? ["a feature is not an object"] : [];
}

/** Fetch a file once, refusing it if `problems` finds anything: a refused file fails like a missing
 *  one, as "could not be loaded", and never reaches a component half-formed. */
function validated<T>(path: string, problems: (x: unknown) => string[]): Promise<T> {
  return once(path, async () => {
    const x = await getJson<T>(path);
    const bad = problems(x);
    if (bad.length) throw new Error(`${path}: malformed (${bad.join(", ")})`);
    return x;
  });
}

export function loadRecentEvidence(): Promise<RecentEvidence> {
  return validated<RecentEvidence>("global/recent_evidence.json", recentProblems);
}

/** A regional overview's context file, named by the manifest (`groups.<id>.context`). */
export function loadGroupContext(path: string): Promise<GroupContext> {
  return validated<GroupContext>(path, groupContextProblems);
}

/** The group a `?group=` slug names, or null. Own keys only: a slug is reader input. */
export function groupBySlug(m: Manifest, slug: string): { id: string; group: ManifestGroup } | null {
  for (const [id, g] of Object.entries(m.groups ?? {})) {
    if (g.slug && g.slug === slug && g.context) return { id, group: g };
  }
  return null;
}

export function loadDataQuality(): Promise<DataQuality> {
  return validated<DataQuality>("global/data_quality.json", dataQualityProblems);
}

export function loadWorld(): Promise<GeoJSON.FeatureCollection> {
  return validated<GeoJSON.FeatureCollection>("global/world.geojson", geometryProblems);
}

// ---- display vocabulary ---------------------------------------------------------------------

export const READINESS_LABEL: Record<Readiness, string> = {
  INDEX_READY: "Index published",
  EXPERIMENTAL: "Experimental",
  CONTEXT_ONLY: "Reported events, no index",
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
  blind_reviewed: "Blind reviewed by three independent reviewers",
  dual_reviewed: "Independently reviewed",
  legacy_single_review: "Single review (published before independent review was required)",
};

export const RESEARCH_COMPLETENESS_LABEL: Record<string, string> = {
  complete: "Every declared source group searched",
  partial: "Systematic search under way",
  never_systematic: "Targeted searches only, no systematic search yet",
};

/** What a lane's two dimensions mean to a reader. Computed by the build; never typed per lane. */
export const LANE_STATE_LABEL: Record<string, string> = {
  universe_searched: "All listed sources searched",
  current_through_latest_release: "Searched through the publisher's latest release",
  declared_query_set_run: "Planned searches run (not exhaustive)",
  partially_searched: "Partly searched",
  blocked_by_source: "Blocked by the source",
  stopped_by_search_limit: "Stopped when the search allowance ran out",
  not_started: "Not started",
  legacy: "Logged under the earlier format",
};

export const LANE_EXECUTION_LABEL: Record<string, string> = {
  not_started: "Not started",
  partial: "Partly executed",
  declared_search_complete: "Every declared query run",
  enumerated_complete: "Published items enumerated (see limitation)",
};

export const LANE_WINDOW_LABEL: Record<string, string> = {
  current_through_end_date: "Source current through the window",
  publisher_not_yet_released: "Publisher has not released the rest",
  inaccessible: "Source refused or could not be read",
  no_census_exists: "No census exists for this class",
  rolling_archive_gap: "Publisher keeps only a recent window",
  unknown: "Not determined",
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

export const CAMPAIGN_STATE_LABEL: Record<string, string> = {
  ACTIVE_KINETIC_CAMPAIGN: "Attacks on energy facilities are being reported now",
  RECENT_ENDED_CAMPAIGN: "An attack campaign ended recently",
  UNCERTAIN: "Attacks were reported this year and no end has been reported",
  NO_ACTIVE_CAMPAIGN: "No attack campaign is recorded",
};

export const CALENDAR_LABEL: Record<string, string> = {
  solar_hijri: "Solar Hijri calendar",
  hijri: "Hijri calendar",
  gregorian: "Gregorian calendar",
};

// Whole primary subtags, not two-letter prefixes: "ckb".slice(0, 2) is "ck" (iteration 20, geography
// red team). "ku" stays right to left because this dataset uses it for Sorani in Arabic script; a
// script subtag overrides the language either way ("ku-Latn" is Kurmanji in Latin letters).
const RTL = new Set(["ar", "fa", "ku", "ckb", "ur", "he", "ug", "ps", "sd", "dv", "yi", "syr"]);
/** Text direction for a language code, so an Arabic or Persian headline is not laid out backwards. */
export function dirFor(lang: string | undefined): "rtl" | "ltr" {
  const parts = (lang ?? "").toLowerCase().split(/[-_]/);
  if (parts.includes("arab") || parts.includes("hebr") || parts.includes("thaa") || parts.includes("syrc")) return "rtl";
  if (parts.includes("latn") || parts.includes("cyrl")) return "ltr";
  return RTL.has(parts[0]) ? "rtl" : "ltr";
}

/** Language names for reader copy (iteration 20, §66). The codes stay in the data. */
export const LANGUAGE_LABEL: Record<string, string> = {
  ar: "Arabic", en: "English", fa: "Persian", ku: "Kurdish (Sorani)", ckb: "Kurdish (Sorani)", fr: "French",
  zh: "Chinese", hi: "Hindi", ru: "Russian", uk: "Ukrainian", es: "Spanish", de: "German",
  "not recorded": "not recorded",
};

/** "Arabic, English" from ["ar", "en"]; an unknown code is shown as it is, never dropped. */
export function languageNames(codes: Iterable<string>): string {
  return [...codes].map((c) => LANGUAGE_LABEL[c] ?? c).join(", ");
}

export function labelFor(map: Record<string, string>, key: string): string {
  return Object.prototype.hasOwnProperty.call(map, key) ? map[key] : key.replace(/_/g, " ");
}

// ---- what's new in the data (iteration 21) -----------------------------------------------------

/** One record as the panel shows it: never an id, an effect, a cause or a facility. */
export interface WhatsNewItem {
  key: string;
  date: string | null;
  date_precision: string;
  region: string;
  class: string;
  fields?: string[];
  recovery_kind?: string;
  evidence_date?: string | null;
}

export interface WhatsNewChange {
  category: string;
  notes: string[];
  items?: WhatsNewItem[];
  more?: boolean;
  event_dates?: [string, string] | null;
  all_predate_previous_build?: boolean;
  /** A campaign system's withdrawn or held records: one sentence, nothing countable. */
  aggregated?: boolean;
}

export interface WhatsNewSystem {
  system_id: string;
  name: string;
  kind: string;
  changes: WhatsNewChange[];
  index?: { label: string; before: number | null; after: number | null; separable: boolean };
  unavailable?: string;
}

export interface WhatsNew {
  schema_version: number;
  available: boolean;
  unavailable_reason: string | null;
  comparison: { previous_as_of: string | null; current_as_of: string | null; mode: string;
                basis: string | null; note?: string };
  categories: { id: string; label: string; meaning: string }[];
  order: string;
  note: string;
  global: WhatsNewChange[];
  systems: WhatsNewSystem[];
  unchanged: { system_id: string; name: string }[];
}

/** The parts of the panel's file the component reads without a guard. A malformed file is refused
 *  at load, so the panel says it could not be loaded instead of throwing during render. */
export function whatsNewShapeProblems(d: unknown): string[] {
  const obj = (x: unknown): x is Record<string, unknown> => typeof x === "object" && x !== null && !Array.isArray(x);
  const strs = (x: unknown) => Array.isArray(x) && x.every((s) => typeof s === "string");
  if (!obj(d)) return ["not an object"];
  const out: string[] = [];
  if (typeof d.available !== "boolean") out.push("available is not a boolean");
  if (!obj(d.comparison)) out.push("comparison is missing");
  if (!Array.isArray(d.categories) || !d.categories.every((c) => obj(c) && typeof c.id === "string"
      && typeof c.label === "string" && typeof c.meaning === "string")) out.push("categories is malformed");
  if (!Array.isArray(d.unchanged) || !d.unchanged.every((u) => obj(u) && typeof u.system_id === "string"
      && typeof u.name === "string")) out.push("unchanged is malformed");
  const known = new Set(Array.isArray(d.categories) ? d.categories.map((c) => (obj(c) ? c.id : null)) : []);
  const change = (c: unknown) => obj(c) && typeof c.category === "string" && known.has(c.category) && strs(c.notes)
    && (c.items === undefined || (Array.isArray(c.items) && c.items.every((it) => obj(it)
        && typeof it.key === "string" && typeof it.region === "string" && typeof it.class === "string"
        && (it.fields === undefined || strs(it.fields)))))
    && (c.event_dates === undefined || c.event_dates === null || strs(c.event_dates));
  if (!Array.isArray(d.global) || !d.global.every(change)) out.push("global is malformed");
  if (!Array.isArray(d.systems) || !d.systems.every((s) => obj(s) && typeof s.system_id === "string"
      && typeof s.name === "string" && Array.isArray(s.changes) && s.changes.every(change))) {
    out.push("systems is malformed");
  }
  return out;
}

export function loadWhatsNew(): Promise<WhatsNew> {
  // Validated inside once(): a refused file rejects, is not kept, and is asked for again.
  return once("global/whats_new.json", async () => {
    const d = await getJson<unknown>("global/whats_new.json");
    const bad = whatsNewShapeProblems(d);
    if (bad.length) throw new Error(`global/whats_new.json: malformed (${bad.join(", ")})`);
    return d as WhatsNew;
  });
}
