# Data schema

All emitted files are UTF-8 JSON in `data/processed/`, mirrored to `web/public/data/`.
TypeScript mirrors of these shapes live in [`web/src/types.ts`](../web/src/types.ts), so
a schema change surfaces as a type error rather than as `undefined` at runtime.

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
  "denominators": { "refining_mtpa": 247.0, "electric_power_mw": 179662 },
  "incident_total": 127,
  "incidents_with_quantified_capacity": 0,        // shown in the UI, not hidden
  "live_disruptions": [ { "asset_id", "name", "disruption_weight", "event_count", "latest" } ],
  "regions": { "RU-LEN": { /* RegionSnapshot */ } },
  "not_modelled": { "industrial_impact": "reason", ... },
  "coverage": {
    "reported_total_strikes": 305,
    "enumerated_in_this_dataset": 127,
    "coverage_ratio": 0.416,
    "by_period": [ { "period": "3rd", "strikes": 92, "cumulative": 108 } ]
  },
  "parser_warnings": ["…: source row has 6 cells, expected 7; capacity not read"]
}
```

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
