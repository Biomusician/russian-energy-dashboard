# Sources and provenance

All sources are public, open, and redistributable under the licences below. Nothing
here scrapes a commercial database or reproduces a proprietary dataset.

---

## Attribution (required in any redistribution)

> Boundaries: **Natural Earth** (public domain).
> Grid and pipelines: © **OpenStreetMap** contributors, ODbL.
> Generation: **WRI Global Power Plant Database** v1.3, CC BY 4.0.
> Events and refinery capacities: **English Wikipedia**, CC BY-SA 4.0.

This string is rendered in the map's attribution control on every page load.

---

## 1. Natural Earth — administrative boundaries

- **URL:** `raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson`
- **Licence:** Public domain
- **Refresh:** 30-day cache

Chosen over GADM, which is more accurate but whose licence forbids commercial
redistribution — that restriction would propagate into the deployed site.

**Two defects worked around:**

1. The `region` property (federal district) is stale. It predates the 2010 creation of
   the North Caucasian Federal District and files the entire Southern FD under "Volga".
   It is not used; the mapping is carried in `pipeline/config.py`.
2. The `iso_3166_2` codes for Moscow city and Moscow Oblast are swapped relative to the
   official standard. The join key is therefore the region *name*, and canonical codes
   are assigned by us.

Natural Earth assigns Crimea and Sevastopol to Russia by geometry. The pipeline draws
Crimea instead as a **separately-identified occupied unit** (internationally Ukraine,
distinct dashed styling, `analytic_scope: "occupied"`) that, since iteration 4,
contributes to the Monitored-Area ESDI through the sectors where it has qualifying events
and a compatible denominator. It is never coloured as a Russian region. The other four
annexed oblasts remain excluded. Because Natural Earth files Crimea inside the Russian
polygon and Russia is excluded from the context-country layer, Crimea is never painted as
ordinary Russian context either.

Enclave geometry is correct — Moscow city, St Petersburg, Minsk city, Nenets AO,
Khanty-Mansi and Yamalo-Nenets are all properly holed out of their surrounding regions,
verified by point-in-polygon tests during the build.

---

## 2. WRI Global Power Plant Database v1.3

- **URL:** `raw.githubusercontent.com/wri/global-power-plant-database/master/output_database/global_power_plant_database.csv`
- **Licence:** CC BY 4.0
- **Coverage used:** 569 RUS + BLR plants → **432 inside the AOI**, 179,662 MW
- **⚠ FROZEN, AND IT HAS NO STATUS FIELD.** The file's last data commit is **2022-01-26** and it
  touched AUS/IND/USA/GBR only, so the Russian records are older still (`year_of_capacity_data`
  is empty for 552 of 569 rows). WRI states the database is "not currently maintained". The
  `datasets.wri.org` "last updated" date is CMS churn, not data. The pipeline is also pinned to
  `output_database/`, which WRI's README describes as the *bleeding-edge* branch rather than the
  vetted v1.3.0 release — immaterial while the file is frozen, but worth knowing.
- **⚠ KNOWN DEFECT, NOT YET CORRECTED (iteration 9 finding).** Because there is no status column,
  the AOI denominator carries plants that have since retired. Cross-checking GEM's August 2026
  Global Integrated Power Tracker against this file for RU+BY: GEM reports **22,831 MW retired in
  Russia** that WRI cannot distinguish from operating capacity, and the coal fleet reconciles as
  GEM-operating 37,278 + GEM-retired 10,839 ≈ WRI 46,072 MW. Wind is the starkest gap — WRI 42 MW
  against GEM 2,605 MW. This is a **generation-denominator correctness problem**, so it is
  recorded here and in `POWER_SOURCE_RECONCILIATION.md` rather than silently fixed: changing the
  denominator moves every historical ESDI value and requires a frozen replay plus an independent
  methodology red-team (iteration 9 brief §30).

Carries capacity in MW, primary fuel, commissioning year, owner, and a per-plant source
URL — none of which OSM's `power=plant` provides reliably. Each plant record retains
its upstream `url` field as provenance.

Spot-checked against known facilities: Balakovo/Saratov, Kola/Murmansk, Kursk/Kursk,
Leningrad/Leningrad, Rostov/Rostov, Kalinin/Tver, Novovoronezh/Voronezh,
Beloyarsk/Sverdlovsk all resolve to the correct oblast.

---

## 3. OpenStreetMap via Overpass

- **Endpoint:** `overpass-api.de/api/interpreter`
- **Licence:** ODbL — attribution and share-alike required
- **Refresh:** 30-day cache, 10 s pause between queries, retry with backoff on HTTP 429
- **Bounding box:** extended east to 120°E / north to 78°N in iteration 1 to cover the
  Siberian Federal District (Irkutsk reaches ~119°E; Taymyr ~78°N).

| Layer | Selector | In AOI (incl. Siberia) |
|---|---|---|
| Substations | `power=substation` + voltage ≥ 220 kV | 1,425 |
| Transmission | `power=line` + voltage ≥ 330 kV | 5,046 |
| Gas pipelines | `man_made=pipeline` + `substance=gas` + named | 2,572 |
| Oil pipelines | `man_made=pipeline` + `substance~oil` + named | 205 |

**Voltage filtering is essential.** Unfiltered, `power=substation` returns 157,771
features across the AOI bounding box, essentially all local distribution and
analytically meaningless at region level. 220 kV is the transmission/distribution
boundary in the Russian grid.

**OSM is deliberately NOT used for refineries, LNG, gas processing or oil terminals.**
Tag probing (`pipeline/osm_probe.py`, kept in the repo for exactly this reason) found:

| Selector | Result |
|---|---|
| `industrial=oil_refinery` | **0** features across the whole AOI |
| `industrial~refinery\|oil` | 3,834 — overwhelmingly oilfield industrial zones, not refineries |
| `industrial=lng` | **0** |
| `man_made=storage_tank` + oil content | 6,512 — individual tanks, too granular |

Re-run the probe if a layer looks thin and you suspect tagging has moved.

---

## 4. English Wikipedia

Licence CC BY-SA 4.0. Accessed through the MediaWiki API (`action=parse&prop=wikitext`)
and parsed from wikitext, not scraped HTML.

### 4a. *Deep strike campaign* — events

Section: "List of oil industry facilities in Russia hit by Ukrainian strikes".
Two sortable tables → **39 facilities, 123 events, 137 citations** to Reuters, the Kyiv
Independent, The Moscow Times, Ukrainska Pravda, Kyiv Post, NV, Al Jazeera, Militarnyi
and others. Per-event citations are attributed by comma-fragment proximity, so each
date keeps the reference that follows it.

**The "Distance (km)" column is deliberately not read.** It gives range from
Ukrainian-controlled territory to each facility. It describes reach rather than damage,
adds nothing to a degradation assessment, and is the one field in the table with clear
operational-planning value. A test fails the build if any range-to-target field appears
in emitted data.

**Parser caveats:**

- The tables use `rowspan` to group facilities under one port. Without expansion, every
  continuation row shifts a column left and mis-assigns its region. Handled, with a
  test.
- `<ref>` blocks containing multi-line `{{cite web}}` templates must be lifted out
  before cell splitting, or one citation becomes a dozen phantom cells. Handled, with a
  test. This also fixed a real bug where citation dates were being harvested as strike
  dates.
- One source row (Novorossiysk Fuel Oil Terminal) is genuinely malformed — 6 cells
  where 7 are expected. It is flagged in `parser_warnings` and its capacity is not
  read, rather than being mis-aligned silently.

### 4b. *List of oil refineries* — refining denominator

Sections "Russia in Europe" and "Russia in Asia", parsed and merged with a sourced curated
supplement (`data/curated/refineries_supplement.csv`). The distinction matters and is kept
mechanically consistent (live counts in [CURRENT_STATE.md](CURRENT_STATE.md)):

- **canonical/inventory facilities**: 35 (every refinery the registry knows);
- **excluded non-fuels**: 1 — Tobolsk/ZapSibNeftekhim (a petrochemical NGL cracker, not crude fuels);
- **fuels-refining DENOMINATOR facilities**: 34 (= 35 − 1);
- **denominator MTPA**: 273.8 (the sum of the 34 members only; Tobolsk's 6.85 MTPA is NOT in it).

So "35 refineries" is the inventory, never the denominator — only 34 participate in the 273.8 MTPA
base. Iteration 7 added denominator-completeness metadata: this base covers ~90% of a like-for-like
crude nameplate reference (~303 MTPA); the gap to the full ~327 MTPA nameplate is ~24 MTPA of
excluded gas-condensate splitters plus a ~10-15% conservative-basis understatement, not any missing
refinery (see [ITERATION_7_REVIEW.md](ITERATION_7_REVIEW.md)).

Both sections are included: the index frame is national because Russian fuel markets
are national, and the Europe/Asia split does not match the federal-district AOI anyway
(Antipinsky is in the Ural FD, inside our AOI, but filed under Asia).

Without this, refining exposure would be measured against the set of refineries known
to have been struck — 100% by construction, and meaningless.

**Still a lower bound.** Even after the iteration-2 audit (280.6 MTPA), Russia's full refining base (~330 MTPA) exceeds it; smaller and mini-refineries
are absent. Exposure is therefore against *tracked major refining capacity* and is
labelled as such. Capacities cross-check well against the strike table (Kirishi 17.18 vs
17.5, Kstovo 14.54 vs 15.0).

### 4c. *2025–2026 Russian fuel crisis* — coverage benchmark

A single table of reported strikes on Russian oil facilities by war year: 3, 13, 92,
138, then 59 — **305 cumulative**. Used *only* to state this dataset's own coverage
(127 / 305 ≈ 42%). It is never an input to any score.

### Not used

*Attacks in Russia during the Russo-Ukrainian war* — 298,000 characters, zero
structured tables. Parsing prose into incidents reliably is beyond MVP scope and would
risk fabricated records. This is the largest identified coverage gap.

---

## 5. Curated file — `data/curated/incidents.csv`

Analyst-maintained, now the largest event source (2022–present). Curated events reach the
scored corpus only after passing through the analyst **candidate queue**
(`data/candidate/candidate_incidents.csv`) — proposed → accepted/rejected/hold, each with
a decision reason and mandatory source URLs. A sample of the seed events:

| Event | Date | Cause | Region |
|---|---|---|---|
| Urengoy–Pomary–Uzhhorod pipeline explosion | 2022-12-20 | technical | Chuvashia |
| Rostov NPP turbine shutdown | 2024-07-16 | technical | Rostov |
| Sudzha gas transit halt | 2025-01-01 | sanctions / supply chain | Kursk |
| Kaleykino oil pumping station | 2025-02-23 | kinetic strike | Tatarstan |
| Unecha oil pumping station | 2025-08 | kinetic strike | Bryansk |

Deliberately sparse. It is a **mechanism**, seeded only with events verifiable right
now, not padded to look fuller. A row without a source URL is skipped.

Two honesty notes carried in the data itself:

- Sudzha is a transit-agreement expiry — a commercial and political termination, not a
  sanction. It is filed under `sanctions` because the fixed taxonomy has no
  commercial-constraint class, and the `notes` field says so explicitly.
- Unecha is recorded at **month precision** because no day-level date was established
  across sources, and is flagged `conflicting_reports = true`. The date was not
  inferred.

---

## 6. Curated recovery file — `data/curated/recovery.csv` (iteration 1)

Facility-level recovery evidence, source-required per row. **13 records → 6 distinct
observed episodes** (iteration 5), spanning refining, oil logistics and gas processing, so
the "typical recovery" median is now shown (47 days). A sample:

| Facility | Kind | Evidence |
|---|---|---|
| Kuibyshev refinery | **Observed** | Reuters industry sources: halted 10 Jun 2026, resumed 21 Aug 2026 (~72 d) |
| Omsk refinery | **Estimated** | Reuters industry source: "at least half a year" after CDU-10 damage |
| Moscow Refinery | **Estimated** | Industry sources (via strike table): ≥6 months offline after June 2026 strikes |

The observed vs estimated distinction is structural and drives both the score and the
UI language. Kuibyshev's 28 Aug 2026 re-strike is after the dataset's as-of date and is
not yet reflected — noted in the record's `evidence` field.

Candidate open sources for future repair-cost and economic-effect fields are catalogued
in [COST_SOURCES.md](COST_SOURCES.md).

---

## Provenance guarantees

1. Every incident record carries its source URLs, rendered as clickable links in the UI.
2. Occurrence confidence is derived from how many distinct publishers are cited.
3. Attribution confidence is separate and never exceeds "probable" from strike-table
   sources — reported, not independently confirmed.
4. Events with no captured per-event citation say so in the UI rather than appearing
   equally well-sourced.
5. Parser warnings from each build are surfaced in the in-app methodology panel.
6. The dashboard states its own coverage ratio in the top ribbon.

## 7. Continental pipeline network context — OpenStreetMap (ODbL), iteration 5

`pipeline/build_pipeline_network.py` reconstructs canonical trunk ROUTES from
**OpenStreetMap `type=route` + `route=pipeline` relations via Overpass (ODbL)**, assembling each
route from its member ways before applying any length threshold. These are `scope="context"` —
display-only, never scored. Overlap with the analytic OSM lines is MARKED (`analytic_overlap`),
never removed, because the context toggle is independent of the analytic one in the UI.

Iteration 9 replaced a way-at-a-time extraction that applied a 50 km minimum to each OSM way and
queried four bands with a hole across 56–120°E. That cost 161,899 km of relation-member geometry
and hid the entire West Siberian trunk corridor; see `PIPELINE_GAP_AUDIT.md` for the measurements.
Route geometry is OSM-traced (`route_quality="osm_mapped"`); cadence is monthly at most, not
daily.

**Global Energy Monitor's GGIT (gas, November 2025) and GOIT (oil/NGL, June 2026)** are the
authoritative trackers and remain the cited cross-reference. Their licence is **CC BY 4.0,
verified verbatim, and permits raw redistribution with attribution** — the earlier note in this
file that there is "no stable CI-fetchable URL" was correct about the *authoritative* download
(a per-request form) but is not a licence limitation, and is not true of every GEM path. Two
ungated paths exist and are deliberately NOT used: the public CDN map GeoJSON omits the
`RouteAccuracy` field, so route quality could not be labelled honestly, and the
`goit-ggit-pipeline-routes` GitHub repo carries no LICENSE file and contains re-imported OSM.
See `PIPELINE_SOURCE_AUDIT.md` for the acquisition procedure and the manifest a snapshot must
carry.

## 8. Major rivers — Natural Earth (public domain), iteration 5

`rivers.geojson` from Natural Earth 50m `rivers_lake_centerlines`, emphasis by `scalerank`.
Geographic context only — never scored. Attribution is carried in the map footer.
