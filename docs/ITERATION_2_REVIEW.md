# Iteration 2 review — Crimea, context geography, incident-level recovery

Follows [ITERATION_1_REVIEW.md](ITERATION_1_REVIEW.md). Read the limitations before
quoting any number.

---

## Geography

**Crimea — a narrow, documented exception to the occupied-territory exclusion.**
- Added as a **separately identified context unit** (`UA-CR`), never as a Russian
  federal subject. Geometry is the union of Natural Earth's Crimea (UA-43) + Sevastopol
  (UA-40) features. Metadata carries `sovereignty` ("Internationally recognised as
  Ukraine"), `de_facto_control` ("Russian-occupied since 2014"), `analytic_scope`
  ("context"), and `esdi_included: false`.
- **Excluded from the Russia+Belarus ESDI denominator and composite** — enforced in
  `build_index` and by a test. Its own regional exposure is computed and shown, but it
  never feeds the national index.
- Participates in Recent, timeline, Recovery, Sources, coverage and filters.
- **Political/status representation:** the map does not adjudicate sovereignty by colour
  or polygon membership. Crimea gets a distinct **dashed-violet outline + neutral slate
  fill** (never the Russian choropleth), and the hover card, legend and scope note all
  state its status in words. The other four annexed oblasts (Donetsk, Luhansk,
  Zaporizhzhia, Kherson) remain fully excluded, resolved as `excluded_occupied`.

**Context countries added** (Natural Earth 50m admin-0), display-only: Ukraine,
Romania, Moldova, Poland, Lithuania, Latvia, Estonia, Finland, Norway, Georgia,
Kazakhstan, Turkey, China, Mongolia, Azerbaijan, plus Sweden, Bulgaria, Slovakia,
Hungary, Armenia and the Central Asian states — **25 countries**. No infrastructure is
ingested for them and nothing there is scored (a test enforces the context files carry
only display metadata).

**Black Sea implementation:** Natural Earth 50m ocean fill (a distinct dark blue-grey)
so the sea reads as water, with an italic `BLACK SEA` HTML label (plus Caspian, Baltic,
Barents). Country and sea labels are HTML overlays positioned via `map.project()` — **no
glyph endpoint, no tiles, zero external runtime dependency preserved.**

**Camera:** two presets — **Full AOI** and **West / Black Sea**.

**Far Eastern FD: structurally supported, analytically disabled** pending sufficient
event/coverage justification. Unchanged from iteration 1; a test keeps it off.

---

## Dataset

| | Iteration 1 | Iteration 2 |
|---|---|---|
| Regions | 79 | **80** (+ Crimea context unit) |
| Events | 128 | **133** |
| Crimea events | 0 | **1** (Feodosia oil terminal, 7 Oct 2024, confirmed) |
| Electricity events | 0 curated | **3** (Bryansk 750 kV & 110 kV, Kursk 110 kV) |
| Refinery inventory | 30 / 247.0 MTPA | **35 / 280.6 MTPA** |

**Refinery denominator audit (task 8).** Added five sourced majors the automated
Wikipedia-list parse omitted, de-duplicated by canonical name:

| Added | MTPA | Region | Source |
|---|---|---|---|
| Moscow Refinery (Kapotnya) | 12.15 | Moscow | Wikipedia / ~245 kb/d |
| Ilsky | 6.6 | Krasnodar | Deep strike table (Moscow Times DB) |
| Slavyansk ECO | 5.2 | Krasnodar | Deep strike table |
| TAIF-NK | 8.5 | Tatarstan | Deep strike table (distinct from TANECO) |
| Mari El (Mariysky) | 1.2 | Mari El | abarrelfull / conservative |

- **Old denominator:** 247.0 MTPA (30 refineries).
- **New denominator:** 280.6 MTPA (35 refineries, +33.6).
- **Effect:** refining exposure 34.3 → **30.2**; ESDI 16.7 → **14.7**. This is an honest
  downward correction from a more complete denominator — not a re-tune of the model. The
  inventory is still a **lower bound** (mini-refineries and some mid-size plants remain
  absent; the true national total is ~330 MTPA). Provenance and inclusion reasons are in
  `data/curated/refineries_supplement.csv`.

---

## Recovery — the core methodological change

**Recovery moved from facility-level to incident-level.** Each disruption has its own
trajectory; recovery of one strike never resolves a later one. A facility hit repeatedly
shows the strongest still-live incident, not a state smeared backwards through time. The
timeline benefits directly.

**States:** `impaired`, `partial_restart`, `substantially_restored`,
`fully_reconstituted`, `unknown`. **A partial restart ("operations resumed") is recorded
and shown but never treated as full reconstitution and never invents a restored-capacity
percentage.**

**Rule-based evidence precedence** (task 6), in `methodology/scoring.json`:
observed full/substantial reconstitution (confidence ≥ medium) → credible sourced
estimate (≥ medium) → modelled fallback. **A low-confidence estimate is displayed but
does not drive the ESDI decay curve** (Moscow Refinery is the live example, marked "low
conf, not scored"). Confidence changes *whether* evidence overrides the model, not by an
arbitrary multiplier.

**Corpus counts (all sourced):**

| | Iteration 1 | Iteration 2 |
|---|---|---|
| Observed restorations (n) | 1 | **4** (22, 72, 73, 98 days) |
| Full reconstitutions | 0 | **1** (Tuapse, ~98 d) |
| Partial restarts | 0 | **1** (Ryazan, 18 d) |
| Estimates | 2 | **2** (Omsk medium-drives, Moscow low-display-only) |
| Records linked per incident | 0 (facility-level) | **7 incident-level** |

The median observed restoration (72.5 d) now **un-suppresses** because n ≥ 3; below that
the ribbon shows a raw case count, never a "median". (The 72/73 pair is the same 9–10
June Kuibyshev strike, split into two dated incident rows by the source table — a minor
double-count in the sample, noted.)

---

## ESDI

- **Previous (iter 1): 16.7. Current: 14.7.**
- **What changed it, decomposed:**
  - **Denominator audit** is the dominant cause: refining base 247 → 280.6 MTPA lowered
    refining exposure 34.3 → 30.2 and the composite with it. (~−2 points.)
  - **Incident-level recovery + observed corpus** shifted Kuibyshev and others onto
    faster observed decay, trimming a little more.
  - **Methodology:** the flat status-multiplier gave way to rule-based precedence.
  - **Data:** +5 events (Crimea excluded from the composite, so it did not raise ESDI).
- **Denominator effect on sub-indexes:** refining and oil-logistics (which uses the
  refining base as a proxy) both dropped proportionally; electric power unchanged (≈0).

---

## Effects / strategic-economic (CREA)

**No CREA data was ingested this iteration**, by design. Investigation found CREA
publishes monthly public tracker/report products but **no documented stable
machine-readable public endpoint** suitable for reproducible automated ingestion, and
CREA revises historical figures as shipment data is verified. Per the brief, we did not
reverse-engineer a fragile private API to claim automation. [COST_SOURCES.md](COST_SOURCES.md)
records CREA (and KSE, Rosstat, Ember) as candidates with their cadence and access
constraints; the recommended path is deterministic ingestion of published monthly
snapshots in a later iteration.

**The strategic/war-sustainment indicators remain a refining/logistics-exposure proxy,
clearly labelled as a proxy** and visually distinct from observed economic data (there
is none yet). Population and industrial effects remain structural context only, with
`not modelled` shown for what open data cannot support.

---

## Costs

Schema supports `reported` / `estimated (low/high)` / `basis`; modelled cost is never
auto-generated. Current coverage: **0 reported repair costs, 0 external estimates** in
the dataset — per-facility repair costs are essentially never public (see
COST_SOURCES.md). The Costs tab reports this honestly rather than inventing figures.

---

## UI

**Changes:** context geography + Black Sea + labels; Crimea dashed-violet treatment and
status banner; two camera presets; recovery UI rebuilt for incident-level
observed/estimated/modelled with partial-restart and low-confidence handling; ribbon
median gating; National/Region toggle on Recent; context tags in Rankings/Recent;
severity-0 and border contrast lifted so the analytic surface stays dominant over the
new context geography.

**Visual QA performed.** This iteration the environment yielded **real screenshots**
(headless Edge at 1500–1920 px). Verified visually: the ribbon (new recovery metrics),
all seven tabs (Overview, Rankings, Recent, Recovery, Effects, Costs, Sources), the
legend with the Crimea entry, the scope note, the context-country and sea labels, and
the timeline. Screenshots inspected at 1920×1080 and 1500×1000.

**Screenshot availability / known limitation.** The **WebGL map canvas itself could not
be pixel-verified**: headless Edge on this machine renders no WebGL (with or without
`--disable-gpu`, ANGLE/D3D11, or SwiftShader), and the in-app browser pane is not
displayed so it does not composite frames. The map's **HTML label overlays projected to
the correct geographic positions** in headless (Norway top-left, Kazakhstan centre,
Mongolia/China right, Black Sea bottom-centre), which confirms the map loads, the
projection works and the AOI is framed correctly — but the choropleth fills, Crimea
outline and event markers on the GL canvas were verified by code/spec and data, not by
eye. **Look at the map in a real browser before showing anyone.**

**Known visual defects:** none observed in the HTML chrome. The map's on-canvas
appearance is unverified (above).

---

## Limitations (specific)

- **Median observed restoration rests on n=4, with one duplicated strike (72/73).**
  Real distinct observed reconstitutions: 3 (Kuibyshev, Saratov, Tuapse). Still thin.
- **Electric-power exposure is ≈0** in current scoring: the 3 curated substation events
  predate the fast substation reconstitution horizon and have decayed out, and
  substations carry transmission throughput, not generation MW. The events enrich
  Recent/coverage/history but the electric sub-index is not yet meaningful — stated, not
  forced.
- **Refining denominator still a lower bound** (~281 vs true ~330 MTPA); refining
  exposure percentages remain somewhat inflated, though less than before.
- **Crimea coverage is n=1.** One well-documented event; the treatment is complete but
  the corpus is nascent.
- **Strategic economic indicators are still a proxy** (no CREA yet).
- **Costs tab is empty** of dollar figures (no public per-facility costs).
- **Regional scores remain contributions to the national total**, not regional
  intensities (unchanged; see METHODOLOGY §4).
- **The WebGL map canvas is visually unverified** in this environment (above).
- Recovery evidence attaches to a specific incident, but a source-table day-range strike
  can appear as two adjacent incidents; recovery must then be recorded on both.

---

## Decisions needed from you

1. **Crimea depth.** The treatment is complete with one event. Curate more Crimea events
   (Feodosia repeat strikes, other depots), or leave it as a demonstrated capability?
2. **Electricity sub-index.** Substation events don't move a generation-MW index. Either
   (a) accept electric stays ≈0 until generation-plant strikes with MW arrive, or (b)
   introduce a separate transmission-disruption sub-measure. Which?
3. **CREA ingestion.** Worth building deterministic monthly-snapshot ingestion next, to
   replace the strategic proxy with observed export-revenue data?
4. **Refinery denominator.** Push toward the full ~330 MTPA (adds many mini-refineries,
   more curation), or hold at the audited 281 MTPA lower bound with the caveat shown?
5. **Median gating threshold.** n≥3 is the current gate; raise it (e.g. n≥5) before
   calling any restoration time "typical"?

---

## Verification performed

- **64 Python tests pass**, including: Crimea permitted-context / others-excluded,
  Crimea excluded from the ESDI denominator, Far-Eastern disabled, no-SFD,
  no-coordinates, no-range-to-target, incident-level recovery, partial-restart ≠ full
  reconstitution, evidence precedence, low-confidence-estimate handling, median
  suppression below n=3, provenance requirements, determinism, encoding, and a
  **frontend data-contract smoke test** (the practical substitute for a browser test on
  this machine).
- Deterministic pipeline rebuild verified (fixed as-of reproduces the index).
- `tsc --noEmit` clean; production build clean.
- Dashboard exercised: all seven tabs screenshot-verified; live console clean.
- Recovery arithmetic unit-tested against the precedence rules.
