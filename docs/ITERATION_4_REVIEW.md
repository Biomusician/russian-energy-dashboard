# Iteration 4 review — Crimea in the index, zero-count audit, LNG/gas coverage

Follows [ITERATION_3_REVIEW.md](ITERATION_3_REVIEW.md). Two principal objectives: bring
**Crimea into the headline index** (while preserving its status and separate treatment),
and run a **systematic zero-count audit** of every taxonomy/filter dimension — researching
apparent gaps before hiding dead controls. Read the limitations before quoting a number.

## Headline

| | Value |
|---|---|
| Baseline ESDI (Crimea excluded) | **15.6** local / 15.34 production |
| **New Monitored-Area ESDI (Crimea included)** | **16.3** |
| Crimea contribution | **≈ +0.7**, almost entirely transmission |
| Why it changed | Crimea's **two recent (Jul 2026) substation strikes** enter the sparse, event-burden transmission sector (11.6 → 17.6). Its two oil-terminal events (2023/24) are largely decayed, so oil logistics barely moves. Sector weights were **not** retuned. |
| Events | 132 → **134** (+2 documented gas-processing strikes) |
| Tests | 82 → **90 pass** |

## Crimea (§1–§5)

**Before:** `esdi_included: false`, `analytic_scope: "context"` — tracked but excluded from
the composite. **After:** `esdi_included: true`, `analytic_scope: "occupied"` — contributes
to the headline index.

- **Methodology, not a bare boolean.** Crimea enters **only** the sectors where it has
  qualifying events and a compatible denominator: **transmission** (event-burden vs the
  national saturation constant — its substations/lines join the *context* counts, never a
  denominator) and **oil logistics** (events vs the proxy denominator, like every region).
  It is **excluded from refining and electric generation** — no inventoried base, no
  qualifying events — rather than parked against an incompatible denominator to move a
  number. `UNKNOWN ≠ ZERO` held.
- **Historical series.** Inclusion recomputes the whole timeline, not just the latest point;
  a test asserts Crimea's transmission series is populated across history.
- **Status preserved (§4).** Distinct dashed-violet map treatment, the sovereignty/occupation
  banner, and an "occupied"/"UA" tag remain — driven now by `analytic_scope`, decoupled from
  index inclusion. Crimea is **never** the Russian choropleth and never labelled a Russian
  region. The headline is renamed **"Monitored-Area ESDI"** (scope: *Belarus + monitored
  Russian regions + Crimea*), so inclusion reads as an analytic choice, not a sovereignty
  claim. The other four annexed oblasts stay fully excluded.
- **Safety unchanged.** No Crimea incident coordinates; admin-region precision only; a test
  enforces both.

## Zero-count audit (§6–§17)

Full detail in [ZERO_COUNT_AUDIT.md](ZERO_COUNT_AUDIT.md). Mechanism: the pipeline emits
`snapshot.facet_counts` (whole-corpus counts, kinds kept separate — assets vs lines vs
incidents), and the left-rail toggles derive **visibility** from those corpus totals, never
the moving timeline/filter slice. A newly-nonzero category reappears automatically after a
rebuild, with no frontend edit (the filter state already holds every taxonomy key).

**Resolved data gaps (now shown):**
- **LNG terminal** (was 0): 5 AOI terminals ingested — Yamal, Arctic LNG 2, Portovaya,
  Cryogas-Vysotsk, Baltic/Ust-Luga — as cited curated assets at admin-region precision.
- **Gas processing** (was 0): Orenburg + Astrakhan GPPs ingested as cited assets, **plus two
  documented drone strikes** (Orenburg 24 Jun 2026, General-Staff-confirmed; Astrakhan 3 Feb
  2025, governor-confirmed) that were entirely absent — a genuine data gap in both inventory
  and events.

**Stayed zero, hidden (with reason):** coal (data gap, deferred — facilities identified),
interconnector (already inside transmission_line), sabotage (qualifying events exist but on
partisan-claim sourcing below our floor), cyber (no demonstrated physical effect),
maintenance (out of scope), unknown (no genuinely unattributed events), unverified (curation
floors at "possible").

**Toggles that disappeared:** the four above infra classes' zeros plus sabotage/cyber/
maintenance/unknown causes and the unverified tier — nine dead controls removed. **Toggles
that newly populated:** LNG terminal, Gas processing.

## LNG / gas (§11–§13)

- **Inventory vs disruption kept separate.** LNG assets = 5, LNG disruption events = 0 — a
  valid state, not padded. Gas processing = 2 assets + 2 events.
- **Classification discipline.** The Ust-Luga gas-condensate complex is **not** counted as
  LNG; only the distinct Baltic-LNG plant is. A test enforces "no condensate facility as LNG".
- **Gas denominator (§13): no coherent composite yet.** LNG liquefaction (MTPA), gas-
  processing throughput (bcm/y) and pipeline capacity (bcm/y) are **not** summed into a
  meaningless number. Gas therefore stays **uncovered**: it now carries **4 records but a
  sector score of 0** — the §20 distinction (record count ≠ score), enforced by a test. Gas
  incident/infrastructure controls remain visible; the composite honestly excludes gas.

## Architecture / provenance

- New `data/curated/assets_supplement.csv` + loader places curated infrastructure at its
  region centroid (`precision: "region"`) — never a sourced facility coordinate. `assets.json`
  is now written after the merge so the file and the facet counts agree.
- Every added asset and event carries a public source URL. No synthetic records; no
  confidence moved to fill a bucket; no reclassification for cosmetics.
- Stack unchanged: stdlib ETL → static JSON → Vite/React → GitHub `main` → Vercel, daily
  refresh. LNG/gas infrastructure is an analyst-curated **snapshot** (release-dated), not
  pretended to update daily.

## Production

Deployed to **https://russian-energy-dashboard.vercel.app** (commit `fb79a49`), exercised on
the live URL: headline reads **Monitored-Area ESDI 16.3**; scope line *Belarus, western
Russia & Siberia + occupied Crimea*; Crimea selectable with its **occupied-territory /
in-index** banner and sovereignty status; the **LNG terminal (5)** and **Gas processing (4)**
toggles present while coal, interconnector, sabotage, cyber, maintenance, unknown and
unverified are hidden; all seven tabs render (134 events, 44% coverage); WebGL map canvas
live; all `/data/*` return 200, no 404s; **zero console errors** on a clean load.

**One production-only defect found and fixed.** The first iteration-4 deploy briefly
white-screened: for a few minutes the Vercel edge served the previous `snapshot.json`
(without `facet_counts`) to the newly-deployed bundle, and Filters assumed the field
existed. Fixed by making Filters fall back to computing facet counts from the raw corpus
when `snapshot.facet_counts` is absent (commit `fb79a49`), verified against the production
build with a `facet_counts`-stripped snapshot. Future deploys degrade instead of crashing.

Dataset as-of: the daily rebuild date; the freshness line states per-source cadence.

## Limitations — read before quoting

- **Crimea's transmission bump reflects sparsity, not over-weighting.** Two fresh substation
  strikes are ~40% of the *active* national transmission burden because that sector is thinly
  populated; a richer transmission corpus would shrink Crimea's share. The headline moved only
  +0.7 because transmission is 10% of the composite.
- **Gas-processing strikes are tracked but do not score.** They are real disruptions, but with
  no defensible gas denominator they add 0 to the ESDI — so the index *understates* gas-sector
  disruption. This is deliberate honesty, not a claim that these strikes did not matter.
- **LNG/gas infrastructure coverage is partial.** Five LNG terminals and two GPPs are a floor,
  not a census; coal and smaller gas-processing/LNG facilities remain un-ingested (documented).
- **A hidden toggle is a statement about *our corpus*, not the world.** "Sabotage: hidden"
  means we hold no event that clears our sourcing floor, not that no sabotage occurred.
- **Admin-region precision throughout.** Curated LNG/gas assets sit at region centroids; no
  facility-level geometry, no incident coordinates, no targeting-oriented fields. Scope tests
  cover the whole served payload.
