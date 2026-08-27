# Iteration 3 review — regional intensity, transmission, recovery quality, economic context, map polish

Follows [ITERATION_2_REVIEW.md](ITERATION_2_REVIEW.md). The theme of this pass was
**credibility and interpretability over feature count** — making the existing measures
more defensible, better separated by evidence type, and easier to read. Read the
limitations at the end before quoting any number.

---

## Headline numbers (current build)

| Measure | Value |
|---|---|
| ESDI (Russia + Belarus) | **15.86** |
| Sector exposure | refining 29.66 · **electric generation 0.07** · **transmission 11.92** · oil logistics 9.49 · gas 0 · coal 0 |
| Events (episodes) | **132** |
| Refinery denominator | **35 refineries / 280.6 MTPA** = **85.0%** of the ~330 MTPA national estimate (gap 49.4) |
| Generation denominator | **219,992 MW** installed (AOI total) |
| Recovery evidence | **6 records → 3 distinct observed episodes**, 3 full reconstitutions, 1 partial restart |
| Unresolved impairments | **40** |
| Regions | 80 (29 carry researched population) |
| Coverage | 132 enumerated / 305 reported (43%) |
| Tests | **77 pass**; deterministic rebuild confirmed |

---

## 1. Recovery median gate (§2)

The "typical recovery" claim is now gated on **≥5 distinct recovery *episodes*, not
records**. With only **3** observed episodes today (6 records deduplicated by
`episode_id`), the ribbon shows **"6 / 3 — records / episodes"** and the honest label
**"< 5 episodes — no median"**. The word *typical* never appears below threshold, and the
Recovery tab shows the individual episodes rather than a smoothed curve over too few
points. A test (`test_median_gate…`) enforces the threshold.

## 2. Episode model — one multi-day incident is one episode (§3)

Multi-day strikes previously double-counted. The date parser now groups dates into
**episodes**: a hyphen range (`9–10 June 2026`) is **one** episode; discrete listed dates
(`22–23 and 25 May`) are **separate** episodes. Each emitted incident carries
`episode_id`, `event_date_start`, `event_date_end`. Recovery attaches to the episode it
resolves, so a single incident can no longer generate two recovery records (the Kuibyshev
72/73-day duplicate is gone). Reproducible, not special-cased — verified by
`test_multi_day_one_episode` and the grouped-parse unit tests.

## 3. Electric power split into generation + transmission (§5)

The old single "electric power" sector conflated two incommensurable things and is
**gone**. There are now two sectors with **different measurement bases**:

- **Electric generation** — capacity basis (MW at disrupted plants), same family as
  refining. Currently 0.07: generation has barely been struck.
- **Transmission** — an **event-burden** measure, **never "% offline"**. A voltage-weighted
  count of disrupted substations/lines is scored against a documented **saturation constant
  of 8 weighted concurrent events = 100**. Network inventory (1,455 substations, 5,066
  lines) is **context, not a denominator** — we never invent a capacity we cannot source.
  Currently 11.92, driven mostly by the recent Taman 500 kV strike.

The UI labels them separately everywhere (ribbon, Effects proxy bars, rankings). Tests
enforce the split and the event-burden basis.

## 4. Refinery reconciliation — an honest lower bound (§7)

`refinery_reconciliation` is emitted and shown: **tracked 280.6 / national ~330 MTPA =
85.0% coverage, gap 49.4**. The gap is explained (chiefly mini-refineries and
gas-condensate plants not individually inventoried), and refining exposure is explicitly
a **lower bound** measured against tracked capacity. We did **not** pad toward 330 by
counting unlike facilities — a test asserts coverage stays below 100% and equals the true
tracked/national ratio.

## 5. Rankings — contribution vs intensity, and a transparent burden table (§8, §9)

The single "Most affected regions" ranking that silently mixed concepts is replaced by
**eight explicit, switchable metrics**:

1. **Contribution to National Exposure** (national denominator — the old ranking, now
   honestly named)
2. **Regional Disruption Intensity** (regional denominator)
3. Unresolved disruptions
4. Reconstitution backlog (days)
5. Recent activity (90 days)
6. Cumulative events
7. Recurrence (events / facility)
8. Data coverage / confidence

**Regional intensity** scores each region's disruption against its **own** base, and only
for sectors that *have* a regional denominator (generation MW, transmission saturation).
Refining and oil-logistics have no regional base, so they are listed as **missing —
never scored as zero**. "Unknown" and "not applicable" stay distinct from "zero" (a test
enforces this: a refinery-heavy region flags refining as a missing regional denominator
rather than reporting zero intensity).

**Active Burden** is a **transparent sortable table**, not another composite score:
columns are Region · Unresolved · Oldest (d) · Median age (d) · Backlog (d) · Sectors.
The reader sorts and reads the components directly.

## 6. Three-layer Effects (§10, §11, §12)

The Effects tab now separates three layers with **visibly distinct badges**, so a proxy
never carries the authority of a measurement:

- **OBSERVED EFFECT** (green) — directly reported consequences only (quantified capacity
  events, currently-impaired facility count). Deliberately sparse; never padded.
- **STRUCTURAL EXPOSURE / CONTEXT** (accent) — region **population** ("potentially
  exposed", explicitly *not* "actually affected"), installed generation, tracked
  substations/lines, heating season.
- **ANALYTIC PROXY** (amber) — model-derived sector exposure, labelled as such, framed as
  the strategic war-sustainment channel (fuel supply / export revenue), never tactical.

**Observed economic context (CREA)** is a fourth, clearly *observed* block: Russian
fossil-fuel export revenue, monthly (6 points Jan–Jun 2026), each with reporting month,
snapshot date, source URL and revision status. It is labelled **observed economic
context** and carries an explicit caveat that it is **not attributed to strikes**. This is
a deterministic snapshot CSV of cited monthly CREA figures — **no API was fabricated and
no rendered-chart internals were scraped**, per the brief.

## 7. Costs → Repair burden (§13)

The Costs tab is renamed **"Repair burden"** and made useful **without inventing dollar
values**. It leads with the **reconstitution burden** — facilities still impaired, summed
remaining reconstitution days, partial vs full reconstitutions — which is directly
observed. Monetary fields remain structurally present but honestly empty; the
reconstitution burden stands in as the defensible cost signal.

## 8. Evidence coverage matrix (§21)

The Sources tab gains an **evidence coverage matrix**: per sector, counts of event /
recovery / cost evidence. Its purpose is to separate **"little data"** from **"low
disruption"** — a faint cell reads as coverage, not effect. (e.g. refining 84 events / 6
recovery / 0 cost; transmission 6 / 0 / 0.)

## 9. Map declutter + third camera preset (§14–16)

- **Scale-dependent asset density:** individual asset dots fade in above a minimum zoom
  with an opacity interpolation, so the low-zoom view is not a wall of dots. No online
  clustering, no tiles.
- **Scale-dependent labels:** country/sea labels use deterministic per-feature minzoom
  priorities with a greedy de-overlap pass — no overlapping label clusters.
- **Third camera preset "Current activity":** fits the administrative regions with
  unresolved disruption (admin geography only, no coordinates). It is omitted if the
  framing would be unstable (region span > 95°).

## 10. Tab strip (§17)

The seven-tab strip could not fit one readable row in the 400–500px rail, so it **wraps to
two rows** rather than clip or hide tabs behind a scroll. Verified by DOM geometry at
**1366 / 1920 / 2560** widths: **no clipping, all seven tabs visible, active tab
accent-highlighted** (text + underline). The "Costs" tab is relabelled "Repair burden".

## 11. Ribbon hierarchy (§18)

Ribbon order is ESDI → unresolved impairments → observed recovery (records / episodes) →
reconstitution episodes → sector exposure → coverage. The median is shown **only when
eligible**; today it is suppressed with the honest "< 5 episodes — no median".

## 12. Recent — repeated-strike indicator (§19)

Recent events show a **"struck ×N"** badge when a facility has more than one recorded
disruption event (from per-asset event counts), distinguishing a repeatedly-targeted site
from a one-off. Live examples: struck ×9, ×3, ×2.

---

## Limitations (read before quoting)

- **The recovery median is intentionally absent.** With 3 distinct observed episodes we
  are below the 5-episode gate. This is a *feature*: we would rather say "not enough
  episodes" than publish a two-point "typical".
- **Transmission exposure is an event-burden proxy, not capacity loss.** The saturation
  constant (8) is a documented modelling choice, not a measured network limit. It is
  designed to produce a bounded, comparable signal, and is labelled a proxy in the UI.
- **Refining coverage is 85% and framed as a lower bound.** The 15% gap is real and
  disclosed; exposure percentages are against tracked capacity.
- **CREA economic context is observed correlation, never causation.** Export revenue moves
  for many reasons this data cannot separate; the UI says so.
- **Population is structural exposure only** — "potentially exposed", never a claim that a
  number of people were affected.
- **Visual QA was done through the DOM, not pixels.** The Browser pane is not composited
  in this headless environment, so raster screenshots time out. Instead, every tab, the
  tab-strip geometry at three widths, the three-layer badges, the evidence matrix, the
  burden table, and the repeated-strike badges were verified by reading the live rendered
  DOM and computed layout on the running dev server. The MapLibre canvas **does**
  initialise with a live WebGL2 context (1178×852) in the in-app browser — the
  "WebGL won't render headlessly" caveat from earlier iterations applies only to the
  external headless-Edge screenshot path, not to functional correctness.
- **Scope unchanged.** No coordinates, no tactical locations, no current unit state; Crimea
  remains the single documented context exception. All scope tests still pass.
