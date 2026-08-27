# Iteration 1 review — Siberia, rankings, reconstitution

Follows [MVP_REVIEW.md](MVP_REVIEW.md). Read the limitations before quoting a number.

---

## 1. What changed

**Geography — AOI locked and extended.**
- The ambiguous "west of the division" phrasing is retired. The AOI is now explicitly
  **Belarus + six western Russian federal districts + the Siberian Federal District** —
  **79 regions** (was 69). The abbreviation "SFD" is gone from code, config, docs and
  UI, enforced by a test.
- The **Far Eastern Federal District** is defined in `FE_REGIONS` but not enabled;
  adding `"Far Eastern"` to `AOI_FEDERAL_DISTRICTS` turns it on with no other change.
- Buryatia and Zabaykalsky Krai are treated as Far Eastern (2018 transfer), overriding
  Natural Earth's stale metadata.
- OSM bbox extended east to 120°E / north to 78°N. Substations 2,524 → 3,536; total
  point assets ~1,924.
- **Omsk — Russia's largest refinery — is now in scope.** Refining exposure rose from
  31 to **34**, and ESDI from 15.4 to **16.7**, entirely from real data coming into
  the AOI rather than any model change.

**Recovery / reconstitution framework — replaces the flat repair half-life.**
- Decay is now evidence-driven: **observed > estimated > modelled**, with the kind
  carried on every number. Half-lives were re-expressed as per-sector reconstitution
  horizons so the index stays continuous with the MVP.
- Confirmed reconstitution collapses a facility's contribution to the residual.
- `data/curated/recovery.csv` holds facility-level recovery evidence, source-required.
  Seeded with **3 real cases**: Kuibyshev (observed ~72-day restoration, resolved),
  Omsk and Moscow Refinery (estimated windows from cited industry sources).
- Snapshot emits per-facility recovery state, reconstitution statistics (medians with
  sample sizes), impairment age, and unresolved counts.

**Four analytic concepts, cleanly separated** in data and UI: disruption **exposure**,
assessed **degradation** (quantified only), **recovery**, and **confidence/coverage**.

**Right panel is now a 7-tab analytical console:** Overview, Rankings, Recent,
Recovery, Effects, Costs, Sources. The central map stays primary.

**Coverage analytics:** categorical event counts by year / sector / district / cause —
no fabricated confidence intervals.

**Cost/economic scaffolding:** schema fields and a Costs tab, honestly near-empty, with
[COST_SOURCES.md](COST_SOURCES.md) documenting candidate open sources.

**UI polish:** observed/estimated/modelled visual language (green solid / amber half /
muted dashed), recovery headline metrics in the ribbon, gas+coal consolidated into one
"Unquantified" cell, label contrast lifted to WCAG AA.

---

## 2. What works

- Pipeline runs end to end, deterministically, stdlib-only, in ~35 s warm. A new test
  asserts byte-for-byte determinism for a fixed as-of.
- **51 tests pass** (was 32). New: Siberian inclusion, Far Eastern exclusion, no-SFD,
  observed-vs-estimated recovery, provenance on recovery records, rankings-only-
  affected-regions, unknown-not-zero, determinism, encoding.
- Frontend typecheck and production build clean; **zero console errors** on a fresh
  load with all seven tabs exercised.
- The recovery framework demonstrably distinguishes evidence kinds: 1 observed, 2
  estimated, 32 modelled, and the observed case (Kuibyshev) correctly collapses to the
  residual once restored.

---

## 3. New source coverage

| Layer | Change |
|---|---|
| Admin regions | +10 Siberian subjects (79 total) |
| OSM substations / lines | Re-fetched over the wider bbox; +~1,000 substations |
| Recovery evidence | New `data/curated/recovery.csv`, 3 sourced facility records |
| Cost sources | Documented (CREA, KSE, Rosstat, Ember…), none ingested yet |

**Siberian event coverage is thin: exactly 1 enumerated event (Omsk).** This is honest,
not a bug — Siberia was struck for the first time in July 2026, and the structured
strike table reflects that. The region is now *ready* to accumulate events as reporting
grows, and the infrastructure base (plants, grid) is fully populated.

---

## 4. Repair / reconstitution: observations vs models

| Facility | Kind | Basis |
|---|---|---|
| Kuibyshev refinery | **Observed** | Reuters industry sources: repairs 1 Jul → resumed 21 Aug 2026 (~72 d) |
| Omsk refinery | **Estimated** | Reuters industry source: "at least half a year" |
| Moscow Refinery | **Estimated** | Industry sources (Wikipedia strike table): ≥6 months offline |
| 32 other live facilities | **Modelled** | Generic per-sector reconstitution horizon (assumption) |

So of ~35 currently-disrupted facilities, **1 has an observed recovery time and 2 have
sourced estimates; the rest use the modelled fallback.** The dashboard says so plainly
in the Recovery tab's evidence-mix bar and every per-facility chip.

---

## 5. Limitations

**These do not go away by adding data:**
- The index still measures **exposure, not loss** (0 of 128 events carry a quantified
  capacity effect). Unchanged by design.
- Regional scores remain **contributions to the national total**, not regional
  intensities (see METHODOLOGY §4).
- The refining denominator (247 MTPA) is still low, so refining-exposure percentages
  are inflated.

**These are data gaps:**
- **Observed recovery n = 1.** The median-observed-restoration headline is a
  median-of-one and is labelled as such. It becomes meaningful only with more curated
  observed cases.
- **Siberian events n = 1.** Coverage there is nascent.
- **Electric power still ≈ 0** and **gas/coal have no denominator.** Unchanged.
- **Costs tab is essentially empty** — per-facility repair costs are rarely public.
- Four regional-effect categories remain "not modelled".

**Technical debt:**
- Recovery evidence attaches per *facility*, not per *incident*. For a facility hit
  repeatedly this applies the latest recovery assessment to all its incidents — correct
  for "current state", coarse for historical reconstruction.
- The strategic/war-sustainment indicators in the Effects tab are still a **refining/
  logistics-exposure proxy**, not observed revenue. COST_SOURCES.md names the fix
  (CREA data).
- Line-to-region assignment by midpoint unchanged (fine; lines are counted, not scored).
- No frontend automated test; verified manually + structurally.

**Weak assumptions, ranked:**
1. **Modelled reconstitution horizons** — still the largest lever where no evidence
   exists. Now at least visibly flagged as modelled per facility.
2. Sector weights (unvalidated judgement).
3. Cause weights (maintenance 0.15, sanctions 0.6).
4. Oil-logistics proxy denominator.

---

## 6. Methodological concerns worth surfacing

- **Median-of-one restoration.** Statistically meaningless alone; shown only with its
  n=1. Do not headline it until the sample grows. Consider suppressing the ribbon figure
  below some minimum n (e.g. n<3) — a deliberate choice not yet made.
- **Recovery half-life from a single reported duration.** One observed reconstitution
  sets that facility's whole decay curve. Reasonable, but a single misreported restart
  date moves one facility's score. Confidence on the recovery record is not yet used to
  discount it.
- **Coverage remains categorical.** Siberian coverage of "1 event" cannot distinguish
  "little disruption" from "little reporting". Stated, not resolved.

---

## 7. Verification performed

- 51 Python tests pass, including determinism and all scope guarantees.
- `tsc --noEmit` clean; production build clean.
- Dashboard exercised in-browser: all seven tabs render with content and **zero console
  errors**; region selection (incl. Omsk) drives Overview/Effects; rankings click
  focuses a region; recovery chips show observed/estimated/modelled distinctly.
- Recovery arithmetic unit-tested (observed overrides modelled; confirmed reconstitution
  caps at residual; impairment age; provenance enforcement).

**Not verified: pixel-level visual appearance.** Screenshots remain unavailable in this
environment (the preview pane does not composite frames here), so layout was confirmed
structurally — computed grid, panel dimensions, no horizontal overflow, tab content
lengths — not by eye. **Look at it before showing anyone.**

---

## 8. Recommended next iteration

1. **Ingest CREA export-revenue + refinery-throughput data** → replace the proxy
   strategic indicators with observed, dated national figures. Highest value available.
2. **Grow the observed-recovery corpus** — curate restart dates for the major struck
   refineries (Reuters/Moscow Times report many). Lifts the median off n=1.
3. **Complete the national refinery inventory with regions** → fixes the low denominator
   and enables true regional refining intensity.
4. **Curated electricity-event path** so the electric-power sub-index becomes real.
5. **Per-incident recovery** (not just per-facility) for accurate historical curves.
6. **Minimum-sample gating** on median headlines (suppress below n=3).
7. Frontend smoke test.

---

## 9. Decisions needed from you

1. **Enable the Far Eastern FD?** It is one line away. Left off because its event
   coverage is near-zero today; turning it on adds empty map area. Your call.
2. **Suppress median-observed-restoration below a minimum n?** Currently shows n=1
   honestly; some readers may still over-read it.
3. **How much recovery curation effort is available?** The framework is built; its value
   scales directly with hand-curated observed restart dates.
4. **Should the strategic/war-sustainment tab wait for CREA data**, or is the current
   refining-exposure proxy (clearly labelled) acceptable in the interim?
5. **Belarus** still participates in the index with zero events — score it or show it as
   context only? (Carried over from the MVP.)
