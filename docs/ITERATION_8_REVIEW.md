# Iteration 8 review — infrastructure symbology, trend views & analyst-workflow UX

A **feature / UX** iteration. Goal (§0): make the dashboard faster to read, easier to navigate,
and more useful for daily analysis, **without diluting its evidence discipline**. It is a
visualisation, navigation, derived-comparison and presentation pass only — no change to what the
data means or how it is scored.

## Governing constraint held (§1)

The frozen-reference ESDI is **unchanged at 18.49** (as-of 2026-08-28, 175 incidents). Nothing in
this iteration alters sector weights, transmission saturation, the gas decision, recovery/refinery
scoring, or the incident corpus. The whole pass is frontend plus two cosmetic label strings in the
doc generator.

- Committed data was pinned to the frozen reference (`--as-of 2026-08-28`) as the iteration
  baseline (commit `2cdef32`). The repo's tip had drifted to the real-date build (18.17, as-of
  2026-08-29); the two figures are the documented pair (`docs/HANDOFF.md`), not a scoring change —
  identical inputs, different build date. All 155 pipeline tests (determinism + CURRENT_STATE sync)
  pass against the pinned build.
- End check: `snapshot.esdi == 18.49`, `as_of == 2026-08-28`, `incident_total == 175`. Pipeline
  suite green.

## What shipped

### Infrastructure icon system (§2-§12, MUST-SHIP)

The undifferentiated `asset-dots` overlay is replaced by a coherent icon vocabulary. **One
registry (`src/icons.ts`) drives three surfaces** — the map, the left-rail filter rows, and the
map-marker legend — so they cannot drift. Grammar, one channel per meaning: **SHAPE** = function,
**COLOUR** = existing `CLASS_COLOR` identity, **dashed FRAME** = administrative-region placement.
Disruption/activity is never baked into the glyph; it stays on the region shading and halo.

- Icons are rasterised **locally** (inline SVG → data-URI → canvas → `addImage`) and registered
  after the style loads, so no glyph service, sprite sheet, or network request is introduced — the
  zero-third-party-request invariant is preserved (verified against the production bundle).
- Declutter is deterministic via `symbol-sort-key` (class → capacity/voltage → struck →
  region-precision) with `icon-allow-overlap:false`; it is **display** decluttering, never a
  target-value rank. Verified 208 icons placed at Moscow z7.2, sparse at the home view.
- Precision markers: point assets carry a solid glyph; the 35 region-centroid assets carry the
  dashed frame and say so. Verified both card variants — a point asset ("Ногинск", 500 kV) reads
  "Public-coordinate infrastructure point"; a centroid asset ("Orsk Refinery") reads
  "Administrative-region placement — not a facility location."
- Hover card (§9) and click (§10): public attributes only — capacity/voltage/fuel/operator/status/
  source — and **never a coordinate, distance, range, or route**. Clicking selects the asset,
  opens its containing-region dossier, and shows a "Selected infrastructure" sub-card; the card
  also reports whether the asset is named in disruption reporting (identity, not a location). The
  scope boundary is enforced in one shared component (`AssetDetail.tsx`) so map and dossier cannot
  diverge.

### Trend surfaces (§13-§16, MUST-SHIP) — all opt-in, default view unchanged

- **Change in ESDI choropleth (§14-15):** two surfaces difference each region's own ESDI series
  over the trailing 30 / 90 days. A **diverging** ramp (`ESDI_DELTA_STOPS`) — blue fell, red rose,
  slate ~unchanged — shares no hue with the sequential exposure ramp, and the legend relabels to
  "Change in ESDI" and states it is a modelled index delta, not observed damage. Verified the
  feature-state deltas match the pipeline series exactly (Leningrad −2.8, Rostov +1.21, Tatarstan
  −1.09, Omsk −0.69 over 30 days).
- **Recent-activity halos (§16):** a window control (cumulative / 30d / 90d) sizes the halos to
  events *recorded* in the window, ending at the scrubber. Copy calls it "activity", never
  impairment or damage. Verified 30d narrows the halo set 73 → 12 regions with correct counts.
- **"What changed" digest (§13, §23):** a dossier tab with a 7/30/90-day picker, scoped to the
  selected region or the whole area, showing **three deliberately separate** measures — new events,
  new restoration evidence, ESDI change — because they answer different questions and never sum.
  Verified across windows (7d → 1 event/−1.31; 30d → 4/−4.78; 90d → 53/+4.08).

### Navigation & sharing (§17-§22, MUST + SHOULD + STRETCH)

- **Deep-link state (§20-22, MUST):** the whole analyst view — surface, activity window, timeline
  DATE, selected region, layer toggles, filter subsets, comparison set, and camera — lives in the
  URL. Only non-default values are written (clean default URL); a malformed link degrades to
  defaults. Verified a rich link round-trips every field including the camera frame.
- **ESDI-trajectory sparklines (§18-19, SHOULD):** an inline SVG trajectory at the top of the
  monitored-area and per-region Overview, drawn only up to the scrubber, with the current point,
  90-day change, and peak-to-date.
- **Region comparison tray (§17, SHOULD):** pin up to three regions and read ESDI, trajectory,
  90-day change, events, unresolved, and top sector side by side; part of the shareable link.
- **Region / facility search (§21, STRETCH):** substring search over public names only; picking a
  region fits its bbox, an asset centres its public point (zoom capped so a centroid is never
  framed as a precise fix). Never indexes or reveals a coordinate.

### Wording (§28)

Doc-generator labels: "ESDI, gas+coal counted at zero" → "Uncovered-sector zero-assumption
sensitivity"; observed-restoration episodes "(national)" → "(monitored area)". Regenerated from the
frozen snapshot; ESDI unchanged; sync test green.

### Defects fixed in passing

- `asset-symbols` `minzoom` lowered 3.4 → 2, so infrastructure is visible at the Full-AOI home view
  (declutter keeps the wide view sparse); previously the home view showed no icons at all.
- `rivers` `line-opacity` nested `["zoom"]` inside a `case`, which MapLibre rejects — the layer was
  silently dropped and its toggle errored. Reformulated as a top-level zoom interpolate with the
  per-feature reveal gate in the stop outputs (pre-existing iteration-5 defect).

## Scope discipline (§24, invariants preserved)

No prospective-target ranking, no vulnerability score, no distance-to-event, no criticality
ranking of intact assets, no coordinate/range/route in any card. The verbal invariants hold in the
UI copy: **region-centroid placement ≠ facility coordinate**, **map visibility ≠ analytic
inclusion**, **unknown ≠ zero**, **activity ≠ impairment**, **ESDI delta ≠ observed physical
damage**, **Crimea's analytic inclusion ≠ a sovereignty statement**.

## Tests

- Frontend (vitest): **33 pass** (10 → 33). New coverage: `addDays` (month/year/leap boundaries +
  empty-date guard), `fmtDelta` (signs), the full `urlState` encode/decode round-trip (clean
  default, subset filters, layer departures, camera, compare cap, malformed inputs), and the
  `esdiDeltaColor` diverging ramp.
- Pipeline (pytest): **155 pass**, unchanged, including determinism and CURRENT_STATE sync.
- `tsc -b` clean; production `vite build` clean.

## Production

- `vite build` succeeds. App chunk 314 kB (97 kB gzip); the 1 MB chunk is maplibre itself
  (unchanged). Zero-third-party-request invariant verified against the built bundle: the only
  external strings are a maplibre GitHub-issue link and the SVG XML namespace — neither is fetched.

## Limitations (aggressive)

- **Headless verification friction.** The in-app browser pane pauses MapLibre's render loop when
  hidden, so map-camera and symbol-placement checks required forcing a paint. All map assertions in
  this review were taken from a fronted, style-loaded map; interaction was exercised via synthetic
  canvas events to avoid the front-on-click resize shift. The behaviour is a test-harness artifact,
  not a product bug (a real user's pane is always visible).
- **`window.__map` dev hook.** `MapPanel` exposes the map on `window.__map` under
  `import.meta.env.DEV`. It is dead-code-eliminated from the production build (verified: `DEV` is
  false in prod) and never ships, but it remains in source as a debugging affordance.
- **Frozen-date fragility (pre-existing).** `--as-of` defaults to `date.today()`, so the "frozen"
  reference only stays 18.49 as long as the committed build is not regenerated real-date. This
  iteration pins it explicitly; a future pass may want a committed frozen-date config so the
  reference cannot drift by accident. Out of scope here (would touch the pipeline).
- **Restoration-evidence dating.** "What changed" and the new-restoration count key off
  `recovery.observed_date` on `live_disruptions`; an episode without an observed date is not counted
  as a restoration in the window (correctly — absence of evidence is not restoration), but the tab
  says so rather than implying completeness.
- **Comparison tray overlap.** The tray floats at the bottom-centre of the map and can lightly
  overlap the corner legend on a narrow map column; it is dismissible and only appears with ≥2 pins.
