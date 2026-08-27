# Data schema

All emitted files are UTF-8 JSON in `data/processed/`, mirrored to `web/public/data/`.
TypeScript mirrors of these shapes live in [`web/src/types.ts`](../web/src/types.ts), so
a schema change surfaces as a type error rather than as `undefined` at runtime.

> **Iteration 1 additions** (detailed below): `data/curated/recovery.csv`; the
> `recovery`, `recovery_stats`, `assessed_degradation` and `coverage_detail` blocks in
> `snapshot.json`; per-region `unresolved_count`; and cost fields on incidents. The
> four analytic concepts — exposure, assessed degradation, recovery, confidence/coverage
> — are kept structurally distinct.

---

## Input: `data/curated/recovery.csv` (iteration 1)

**Iteration 2: keyed by `incident_id`, not facility.** Each disruption has its own
recovery trajectory; recovery of one strike never resolves a later one. **A row with no
`source_urls` is skipped** (provenance is mandatory for a recovery claim). Legacy
facility-keyed rows still load for backward compatibility.

| Column | Meaning |
|---|---|
| `incident_id` | The specific incident this recovery applies to (e.g. `omsk-refinery:2026-07-06`) |
| `recovery_status` | `impaired` / `partial_restart` / `substantially_restored` / `fully_reconstituted` / `unknown` |
| `source_confidence` | `high` / `medium` / `low` — decides whether the evidence overrides the model |
| `observed_date` | Date the status was reached (for observed) |
| `observed_days` | **Observed** days from disruption to that status |
| `partial_operations_resumed_at` | Date partial operations resumed (partial restart) |
| `partial_or_full` | `partial` / `full` — what the source actually establishes |
| `est_lower_days` / `est_central_days` / `est_upper_days` | **Estimated** reconstitution window |
| `estimate_basis` / `estimate_method` | Provenance of the estimate |
| `what_source_establishes` | Free text: exactly what the source supports, and by whom |
| `source_types`, `source_urls` | `\|`-separated. **Required.** |

**Evidence precedence (rule-based).** observed full/substantial reconstitution
(conf ≥ medium) → credible sourced estimate (≥ medium) → modelled fallback. A
**partial restart** updates state and records the date but is display-only for scoring;
a **low-confidence estimate** is shown but does not drive the decay curve. The
`scoring_evidence_kind` (observed / estimated / modelled) is emitted on every live
disruption so the UI never renders a guess like a report. See
`methodology/scoring.json` → `recovery_precedence`.

---

## Input: `data/curated/refineries_supplement.csv` (iteration 2)

Sourced additions to the national refinery denominator that the automated *List of oil
refineries* parse omits. De-duplicated by canonical name against the base list.

| Column | Meaning |
|---|---|
| `name`, `region_code`, `capacity_mtpa`, `operator` | Refinery identity and capacity |
| `source_url`, `source_date` | Provenance |
| `inclusion_reason` | Why it was added and why it is not a double-count |

---

## Input: `data/curated/incidents.csv`

The analyst-maintained extension point. Everything the automated parsers cannot reach
goes here — non-kinetic causes, electricity and gas events, anything reported only in
prose. **A row with no `source_urls` is skipped with a warning, not ingested.**

| Column | Type | Notes |
|---|---|---|
| `incident_id` | string | Unique. Convention: `cur-YYYY-MM-DD-slug` |
| `date` | ISO date | `YYYY-MM-DD` or `YYYY-MM` for month precision |
| `date_end` | ISO date | Optional, for events with duration |
| `date_precision` | `day` \| `month` | Must match `date`'s shape |
| `scope` | `asset` \| `region` \| `national` | What the record describes |
| `region_code` | string | Canonical code, e.g. `RU-LEN`. Null for national-scope |
| `asset_id` | string | Stable slug; groups repeat events at one facility |
| `linked_asset_id` | string | Optional. A `wri-*` or `osm-*` id from `assets.json`. When set, that asset's **full capacity** becomes the exposure base |
| `asset_name` | string | Display name |
| `asset_class` | enum | See asset classes below |
| `cause` | enum | `kinetic_strike` \| `sabotage` \| `cyber` \| `technical` \| `sanctions` \| `maintenance` \| `unknown` |
| `attribution` | string | `none` \| `reported_ukrainian_strike` \| … |
| `attribution_confidence` | enum | `not_applicable` \| `possible` \| `probable` \| `confirmed` |
| `status` | enum | `active` \| `degraded` \| `repaired` \| `unknown` |
| `confidence` | enum | `confirmed` \| `probable` \| `possible` \| `unverified` — occurrence, not attribution |
| `capacity_affected_mw` | float | Only if a source states it. Leave blank otherwise |
| `capacity_affected_mtpa` | float | As above |
| `capacity_affected_pct` | float | As above |
| `repair_cost_reported_usd_m` | float | **Reported** repair cost (a source stated it). Leave blank otherwise |
| `repair_cost_estimate_low_usd_m` / `_high_usd_m` | float | **Estimated** repair-cost range from an external analyst |
| `cost_basis` | string | Who estimated/reported the cost and how |
| `first_seen` | ISO date | When this record entered the dataset |
| `last_verified` | ISO date | When a human last checked it |
| `conflicting_reports` | `true` \| `false` | Sources disagree on a material fact |
| `notes` | string | Free text. Record *why* a judgement was made |
| `source_types` | `\|`-separated | `news_agency`, `news_outlet`, `government_statement`, `encyclopaedia`, … |
| `source_urls` | `\|`-separated | **Required.** At least one |

### Three distinct absences

The schema distinguishes them and the UI must preserve the distinction:

- **`null` / blank** — not known, or not yet researched.
- **`0`** — measured and genuinely zero.
- **`not modelled`** — no data source exists for this category in the MVP. Emitted
  explicitly in `snapshot.not_modelled` with a reason.

---

## Output: `snapshot.json`

Current state, plus the honesty metadata.

```jsonc
{
  "as_of": "2026-08-26",
  "build_time": "2026-08-26T21:41:03+00:00",
  "esdi": 15.35,
  "sectors": { "refining": 31.02, "electric_power": 0.0, ... },
  "sectors_covered":   ["refining", "electric_power", "oil_logistics"],
  "sectors_uncovered": ["gas", "coal"],          // no capacity base; excluded from composite
  "heating_season": false,
  "denominators": { "refining_mtpa": 280.6, "electric_power_mw": 179662 },
  "incident_total": 128,
  "incidents_with_quantified_capacity": 0,        // shown in the UI, not hidden

  // Concept 2 — assessed degradation, kept separate from exposure (quantified only)
  "assessed_degradation": { "quantified_incident_count": 0, "total_incident_count": 128,
                            "quantified_mw": 0, "quantified_mtpa": 0, "note": "…" },

  // Concept 3 — reconstitution statistics (medians, always with sample size)
  "recovery_stats": {
    "unresolved_count": 34, "resolved_count": 1,
    "median_observed_restoration_days": 72, "observed_restoration_sample": 1,
    "median_impairment_age_days": 51, "impairment_age_sample": 33,
    "evidence_kind_counts": { "observed": 1, "estimated": 2, "modelled": 32 },
    "by_sector": { "refining": { "disrupted_facilities", "unresolved",
                                 "observed_restoration_sample",
                                 "median_observed_restoration_days" } },
    "note": "…"
  },

  // Concept 4 — categorical coverage. No fabricated confidence interval.
  "coverage_detail": { "by_year", "by_sector", "by_district", "by_cause", "note" },

  // Each live disruption now carries a `recovery` object (see below)
  "live_disruptions": [ { "asset_id", "name", "asset_class", "sector", "region_code",
                          "disruption_weight", "event_count", "latest",
                          "recovery": { /* RecoveryState */ } } ],
  "regions": { "RU-LEN": { /* RegionSnapshot */ } },
  "not_modelled": { "industrial_impact": "reason", ... },
  "coverage": {
    "reported_total_strikes": 305,
    "enumerated_in_this_dataset": 128,
    "coverage_ratio": 0.42,
    "by_period": [ { "period": "3rd", "strikes": 92, "cumulative": 108 } ]
  },
  "parser_warnings": ["…: source row has 6 cells, expected 7; capacity not read"]
}
```

### `RecoveryState` (per live disruption)

```jsonc
{
  "recovery_evidence_kind": "observed",   // observed | estimated | modelled — the key field
  "reconstitution_horizon_days": 46,
  "resolved": true,
  "impairment_age_days": null,            // null once resolved
  "observed_restoration_days": 72,        // present only for observed
  "reconstitution_observed_days": 72,
  "estimate_days": null,                  // { lower, central, upper, basis, method, confidence } for estimated
  "reconstitution_level": "substantial",
  "partial_operations_resumed_at": "2026-08-21",
  "reconstituted_at": "2026-08-21",
  "recovery_sources": [ { "url": "…" } ]
}
```

`recovery_evidence_kind` is the one field the UI must always honour: **observed** and
**estimated** and **modelled** are rendered in visibly different language, and a
`modelled` record never carries an `observed_*` day count.

`parser_warnings` is surfaced in the in-app methodology panel. A malformed upstream row
becomes a visible warning, never a silently misaligned record.

### `RegionSnapshot`

```jsonc
{
  "code": "RU-LEN", "name": "Leningrad Oblast",
  "district": "Northwestern", "country": "RU",
  "esdi": 3.31,
  "sectors": { "refining": 6.9, ... },
  "incident_count": 22,
  "struck_facility_count": 5,
  "live_disruption_count": 5,
  "unresolved_count": 5,               // facilities impaired with no reported restoration
  "installed_mw": 7915,
  "effects": {
    "generation_margin": 0.0,          // % of region's own installed MW
    "fuel_production": 3.38,           // % of NATIONAL refining base impaired here
    "logistics": 0.90,
    "heating_season_exposure": 0.0,
    "repair_burden": 5,
    "recurrence": 4.40,
    "industrial_impact": null,         // not modelled — see snapshot.not_modelled
    "civilian_electricity_reliability": null,
    "military_industrial": null,
    "cross_region_dependencies": null
  }
}
```

---

## Output: `incidents.json`

One record per event. **Never carries coordinates** — events are region-scoped, and a
lat/lon on an event record would be exactly the asset-level precision this MVP rules
out. There is a test.

```jsonc
{
  "incident_id": "kirishi-refinery-kinef:2026-07-09",
  "asset_id": "kirishi-refinery-kinef",
  "asset_name": "Kirishi Refinery (Kinef)",
  "asset_class": "refinery",
  "region_code": "RU-LEN",
  "date": "2026-07-09",
  "date_precision": "day",
  "cause": "kinetic_strike",
  "attribution": "reported_ukrainian_strike",
  "attribution_confidence": "probable",
  "confidence": "confirmed",           // occurrence: 2+ independent outlets cited
  "status": "unknown",
  "origin": "wikipedia_strike_table",  // or "curated"
  "sources": [ { "url", "title", "publisher", "date" } ],
  "part_of_unenumerated_series": false // true = the real count exceeds what is plotted
}
```

**Occurrence confidence** is derived from citation count: 2+ distinct publisher hosts →
`confirmed`, 1 → `probable`, 0 → `possible`. **Attribution confidence** is separate and
never exceeds `probable` from strike-table sources.

---

## Output: time series

`index_national.json` and `index_regional.json` share a date axis; values are parallel
arrays rather than objects, which roughly halves the payload.

```jsonc
// index_national.json
{ "dates": ["2022-01-01", ...], "esdi": [0.0, ...], "sectors": { "refining": [0.0, ...] } }

// index_regional.json
{ "dates": [...], "regions": { "RU-LEN": { "esdi": [...], "sectors": {...} } } }
```

244 weekly steps from 2022-01-01. Weekly, not daily: decay half-lives are measured in
weeks, so daily resolution would quadruple the payload without changing any visible
conclusion.

---

## Output: `assets.json`, geometry

`assets.json` — point infrastructure with real published coordinates (WRI plants, OSM
substations). `regions.geojson` — simplified display boundaries, ~1 km tolerance.
`assets_lines.geojson` — transmission and pipeline lines, region-assigned by midpoint.
`taxonomy.json` — asset classes, sectors and causes, so the frontend never hardcodes
them.

---

## Asset classes

`power_plant_thermal` · `power_plant_nuclear` · `power_plant_hydro` ·
`power_plant_other` · `refinery` · `oil_terminal` · `gas_processing` · `lng_terminal` ·
`pipeline_oil` · `pipeline_gas` · `substation` · `transmission_line` · `coal` ·
`interconnector`

Sector rollup is defined by `SECTOR_OF_CLASS` in `pipeline/config.py`. A class absent
from that map is displayed but not scored.
