# Iteration 11 — explainability, change attribution, and briefable views

Working notes for the iteration. Phases P1–P8 shipped, P9 deferred to iteration 12 (see [ITERATION_12_BACKLOG.md](ITERATION_12_BACKLOG.md)), P10 below.

---

## P8 — Briefing and export

### The benchmark, and what could not be measured

`preserveDrawingBuffer` was benchmarked before choosing an architecture, as required. Two of the
requested measurement classes turned out to be impossible in the available environment, and that
is reported here rather than filled in with plausible numbers.

**Measurable (synchronous WebGL, no animation frames needed):**

| Canvas | `preserveDrawingBuffer` | Context creation (median of 5) | `readPixels` 1px | `toDataURL` |
|---|---|---|---|---|
| 1920×1080 | false | 5.5 ms | 2.9 ms | 13.9 ms |
| 1920×1080 | **true** | 4.5 ms | 0.9 ms | 14.0 ms |
| 2560×1440 | false | 4.0 ms | 4.2 ms | 23.5 ms |
| 2560×1440 | **true** | 4.2 ms | 0.5 ms | 17.6 ms |
| 1280×720 | false | 3.9 ms | 1.1 ms | 4.6 ms |
| 1280×720 | **true** | 3.7 ms | 0.5 ms | 4.0 ms |

Creating a context costs ~4 ms whether or not the flag is set. Reading one back is *faster* with
it. The whole on-demand capture path is therefore tens of milliseconds.

**Not measurable here, and not guessed at.** Map-ready time, pan/zoom responsiveness and resize
responsiveness are all frame-bound, and the preview pane in which this work was verified
**suspends `requestAnimationFrame` entirely**. Two direct probes confirmed it: a rAF loop failed
to complete a single 800 ms sample in 45 s, and a counter advanced from 0 to 5 only when a
screenshot forced a paint. No Chrome extension was connected to provide a real browser, and
adding a headless-browser toolchain was out of scope. So the interactive-performance half of the
comparison is **unmeasured**, and is recorded as unmeasured.

### Architecture chosen: export-only render path

The main map keeps its existing configuration. Export builds a temporary MapLibre instance with
`preserveDrawingBuffer` enabled, copies the live style and camera into it, captures, and destroys
it.

The reasoning does not depend on the unmeasured half. A temporary context costs ~4 ms to create
and ~14–18 ms to read back — a cost paid only when someone exports. Setting the flag on the
persistent map would trade that for a cost paid in *every* session forever, in exchange for
nothing a user can see. Since the on-demand path is provably cheap, there is no reason to accept
any persistent cost, whatever its size turns out to be.

Two implementation details that would each have produced a silently blank image:

- This MapLibre version moved the flag to `canvasContextAttributes: { preserveDrawingBuffer }`.
  The old top-level spelling type-errors here, but in plain JS it would have been ignored without
  complaint.
- The temporary container is positioned off-screen, not `display: none`. An undisplayed container
  gives MapLibre no size to adopt and the capture returns empty.

### Never a blank or half-painted file

The exporter waits for `idle`, then samples five points of the rendered canvas and refuses to
produce a blob if they are all identical — a uniform frame is what a premature capture looks
like. Failures surface as a message naming the likely cause (usually a context layer still
loading). The temporary map is removed in a `finally`, so it is cleaned up on success, on
failure, and on a throw. Verified: `leftover: 0` off-screen containers after both a successful
export and the map-not-ready path, and the main map still interactive afterwards.

### Sizes and sharpness

`Current viewport`, `1920×1080`, `2560×1440`. A **named size means exactly those pixels**; the
viewport option keeps the device pixel ratio so it matches what the reader sees, clamped to 2×.

This was a real defect found in browser testing: requesting 1920×1080 on a 1.25 DPR screen
produced a **2400×1350** file. Sharper, but not the size someone building a slide asked for. The
rule now lives in `exportPixelSize()` and is unit-tested.

### Briefing Mode

A product state on top of Map Focus, not screenshot CSS. It strips chrome *and* adds framing:
title, metric label, metric value, as-of date, analytical date where it differs, comparison
summary, selection label, caveat, scope note, Crimea note, source footer. It stays interactive,
and exiting restores the exact panel state the reader had before entering.

Measured with Briefing Mode active — it *increases* map area rather than competing with it:

| Viewport | Layout | Map | Map area | Grid rows | H-overflow |
|---|---|---|---|---|---|
| 1920×1080 | wide | 1920×933 | 0.864 | 3 | 0 |
| 1536×864 | compact | 1536×706 | 0.817 | 3 | 0 |
| 1366×768 | compact | 1366×610 | 0.794 | 3 | 0 |
| 1280×720 | compact | 1280×549 | 0.762 | 3 | 0 |
| 1024×768 | narrow | 1024×597 | 0.777 | 3 | 0 |

The export-options panel overlays the map and is dismissible; it never claims a column, and the
grid stays at three rows at every size.

### What every export carries

Metric-specific caveats rather than one disclaimer: the exposure caveat for ESDI, a
change caveat for delta surfaces, the event-burden-proxy caveat wherever transmission is in the
index, a geometry caveat when pipeline networks are shown, and the reconstruction caveat for any
historical view. The Crimea sovereignty note is present whenever Crimea is in scope and is never
dropped to tidy the graphic.

**The build delta is exported only when ledger lineage is provable.** With invalid lineage it is
omitted entirely — "no prior build" is a fact about a git repository, not an analytical finding,
and must not leave the application looking like one.

Filenames are deterministic and describe the view:
`energy-disruption-monitor_2026-09-03_esdi.png`, `..._30d-change.png`, and
`energy-disruption-monitor_2025-08-30_to_2026-09-03.png` for a comparison.

### Print

Print CSS is a deliberate product, not a screenshot of the running UI: interactive controls,
drawers, the inspector and the export controls are removed; the map becomes a fixed block that
does not break across pages; and the dark presentation overlays become readable dark-on-white
text with the caveat still emphasised.

The **Map Brief** (one page, map-centric) ships. The multi-page **Analyst Report** does not — it
was explicitly optional and would have expanded scope without improving the core deliverable.

### Per-view verification (§26)

Each view listed in §26 was driven in the browser and its exported framing read back.

| View | Framing carried | Result |
|---|---|---|
| Headline ESDI | value 16.69, as-of, exposure + transmission caveats, scope, Crimea, sources | pass |
| 30-day delta | change caveat only — the exposure caveat correctly absent | pass |
| Selected region | `Krasnodar Krai · 3.07`, no coordinates | pass |
| Infrastructure-heavy | no pipeline-geometry caveat (points, not networks) | pass |
| Gas/oil context | pipeline-geometry caveat added; exported 1920×1080, 383 KB | pass |
| Date A/B Δ | both dates, both values, +12.35, resolution note, reconstruction caveat | pass |
| Recovery episode | **failed — see below**, then fixed and re-verified | fixed |

**The defect this pass found.** Entering Briefing Mode from the recovery lifecycle explorer
produced a graphic that said nothing whatever about the episode on screen — with a comparison
also open it exported the comparison framing and the comparison filename, and with the comparison
closed it exported the plain headline. A reader would have received a briefing image titled after
something they were not looking at.

The briefing context now carries the selected episode, and states the four things that make a
recovery claim readable: the facility, the disruption date, the **evidence family**, and what was
actually claimed. Family semantics are preserved verbatim from P7 — an estimate never gets a
restoration date (`projected repair horizon, no observed restoration`), and an undated
restoration report is neither "restored" nor "no evidence" (`restoration reported, no date
recorded — on no timeline, drives no scoring change`). A recovery view also earns the
reconstruction caveat at any date, because a trajectory is rebuilt from the current evidence set
whatever the map is showing, plus a family caveat saying the families are distinct claims.

Verified after the fix:
`energy-disruption-monitor_2026-08-11_recovery_orsk-refinery-orsknefteorgsintez.png`,
1920×1080, 382 KB, `leftover: 0`.

`FAMILY_LABEL` moved to `data.ts` so the explorer and the exporter spell the families
identically rather than drifting apart in two files.

### Performance

- Export at 1920×1080: **521 ms** end to end with a warm style — creating the temporary map,
  loading the style, rendering and encoding. Output 382 KB.
- Earlier runs of the same export measured 1227 ms and 11113 ms. The spread is the harness, not
  the code: this pane only advances animation frames when a screenshot forces a paint, so an
  export's wall-clock depends on how often something happens to force one. The 521 ms figure is
  the closest to real and still an upper bound. Real-browser latency is **not** claimed here.
- The 2400×1350 run before the pixel-size fix took 13776 ms, for the same reason.
- Persistent interactive cost: **zero by construction**. Nothing about the main map changed.

### Limitations

- Interactive frame-rate impact of the rejected architecture is unmeasured (see above).
- Clipboard copy is not implemented; download ships first, as `SHOULD` rather than `MUST`.
- The Analyst Report multi-page layout is not implemented.
- Export latency figures are harness-inflated and should be re-measured in a real browser.

---

## P10 — integration, red-team, release

### Integration against a moving main

The refresh bot advanced `origin/main` two commits past this branch's base while iteration 11 was
in flight, which is why the ledger had been correctly refusing to emit a delta.

| | commit | as_of | ESDI |
|---|---|---|---|
| branch base | `441974a` | 2026-09-01 | 17.27 |
| refresh | `24d172c` | 2026-09-02 | 16.98 |
| **origin/main at integration** | **`1362ddb`** | **2026-09-03** | **16.69** |

All four merge conflicts were generated payload files; the bot changed no curated source, so the
drift across those days is pure time decay over the same 175 events. Neither side was taken as
analytical truth: the conflicts were cleared and the payload regenerated from the integrated tree.

**The integrated code reproduces all three committed production builds exactly** — 17.27, 16.98
and 16.69 at their own as-of dates. That is the strongest available evidence that iteration 11
changed no scoring, and it is three independent checks rather than one.

### Ledger lineage, proved

| | |
|---|---|
| previous commit | `1362ddb4` — "data: daily refresh 2026-09-03 — ESDI 16.69, 175 events" |
| previous as_of | 2026-09-03 |
| current as_of | 2026-09-03 (at the time of proof) |
| previous fingerprint | **null — not comparable** |
| current fingerprint | `419ef7b7af28e2d1` |
| ESDI | 16.69 to 16.69, delta **0.0** |
| changes | **0**, across all four natures |
| `lineage.valid` | **true**, `previous_is_ancestor: true`, mode `development` |

The zero is the finding. An iteration whose theme was "make every number explainable" should move
no numbers, and against a real production ancestor the ledger now says so instead of refusing to
answer.

Input fingerprints are reported as **not comparable**: the baseline predates the manifest emitter
and publishes nothing to compare against. Absent is not equal, and the ledger says which it is.

**The zero was tested, not assumed.** Re-running the ledger against the older `441974a` ancestor
produces a real transition — 17.27 to 16.69, delta -0.58 — with sector attribution correctly
withheld, because that baseline also predates the explanation emitter and there is nothing to
decompose against. The Inspector states that reason rather than rendering an empty block.

### Red teams

Three independent reviews ran against the integrated branch and generated payload, each asked to
reproduce claims rather than read this document.

| Team | Verdict | Defects | Risks |
|---|---|---|---|
| Analytic / methodology | 1 defect, 1 risk | zero-taxonomy branch unreachable | 0-valued rows in rankings |
| Frontend / UX / accessibility | 4 defects, 2 risks | **PNG carried no framing**; no keyboard exit from Briefing; map-focus desync; Inspector not a real modal | drawer `aria-hidden`; deep links drop new state |
| Data / provenance / temporal | 2 defects, 3 risks | ENTSOG publisher-signal; undercount magnitude never surfaced | two date rules; inert first-seen; dead incident fields |

**Every defect was fixed.** Risks are either fixed or carried as documented limitations in
[ITERATION_12_BACKLOG.md](ITERATION_12_BACKLOG.md).

The analytic team independently reproduced the headline decomposition to float precision
(`16.691103864251095` against a published `16.691103864251097`), confirmed the 0.01 display
residual is published as its own field rather than absorbed into a sector, and confirmed gas and
coal are excluded with weights renormalised to exactly 1.0.

### The two findings that mattered most

**The exported PNG had no caveat.** `runExport` captured the MapLibre canvas and wrote it
straight to a file. Every piece of framing — metric, dates, caveat, scope, Crimea note, sources —
was DOM on top of the map, so it reached the reader's screen and not the image. The file leaving
the application was a bare choropleth of Russia with nothing anywhere saying it measures exposure
rather than damage: precisely the misreading the feature was built to prevent.

It survived P8 because I verified the live overlay, the download filename and the pixel
dimensions, and never opened the file. The instruction for this phase said it in as many words —
inspect the actual PNG, do not infer export quality from the live map — and that is the check I
skipped.

`briefingFrame.ts` now draws the frame into the image with the 2D canvas API: no DOM rasteriser,
no library, no external font. It composes after the blank-canvas check, so a failed capture can
never return as confident-looking text over an empty map. `briefingFrame.test.ts` asserts on what
is actually drawn.

**A region with unscorable damage said nothing was wrong.** `_share` returns 0 for a sector with
no capacity denominator, and the scoring loop drops a facility on `share <= 0` before recording
its sector — so gas and coal impairment never reached the regional fractions and the
`ZERO_UNCOVERED_ONLY` branch was unreachable for all 80 regions. Astrakhan Oblast, carrying a live
gas-processing disruption at weight 0.272, published "Nothing is recorded as impaired" directly
above a panel listing that same live facility.

The scorer now records uncovered-sector impairment in a map kept entirely apart from the
composite. Recorded, not scored — the rebuild confirms ESDI is unchanged to the cent. Three
regions now report unscorable impairment.

The existing test passed throughout, because it fed the classifier a fabricated fraction map the
real pipeline could never produce. That is the general lesson of this gate: **both headline
defects were invisible to a green suite because the tests asserted on the layer just before the
one that mattered.**

### Recovery lifecycle: all 26 episodes

Validated programmatically, not sampled. All 26 pass: milestone chronology with undated
milestones sorting last; no episode carrying coordinates; trajectory weights in range; evidence
status never collapsed into the scoring kind; the estimate family never carrying a measured
duration; undated restoration claims never becoming a duration and always carrying their note.

Every n<3 group withholds median and quartiles and states its own sample size as the reason. The
three class-by-family groups reaching n>=3 recompute exactly from raw values:

| Group | n | values | median |
|---|---|---|---|
| oil_terminal x service_restoration | 3 | 3, 4, 4 | 4 |
| refinery x unit_restart | 3 | 7, 22, 72 | 22 |
| substation x service_restoration | 3 | 0, 0, 0 | 0 |
| *(pooled)* service_restoration | 12 | 0-18 | 2.0 |
| *(pooled)* unit_restart | 6 | 2-205 | 14.5 |

### "What this dashboard cannot tell you"

All 8 items generated from conditions that currently hold; none is stale prose. Proved by fixture:
closing the gas/coal gap, giving transmission a denominator and resolving every impairment makes
three items disappear, while the scope-boundary item correctly persists — it is a permanent limit,
not a data gap.

The capacity statement uses **164 applicable / 11 with no modelled capacity dimension**, not the
175-event corpus; 164 + 11 = 175, and the corpus figure appears nowhere in the sentence.

### Export QA

| View | Verified how | Result |
|---|---|---|
| Headline ESDI | **real export, PNG opened and read** | frame complete |
| Date A/B delta | **real export, PNG opened and read** | both dates, +12.07, resolution note, reconstruction caveat |
| Gas/oil context | real export | pipeline geometry caveat present |
| Recovery episode | real export + compositor render read | family and outcome present |
| Selected region | framing verified in-app; compositor unit-tested | no coordinates |
| 30-day delta | framing verified in-app; compositor unit-tested | change caveat only |
| Crimea in scope | present in every export above | note never dropped |

Resource audit: temporary containers, canvases and WebGL contexts return to baseline after every
export. `leftover: 0` was observed after success, after the map-not-ready path, and after a real
20-second idle timeout — which surfaced a clear message and wrote **no file**.

Export latency is not claimed. Observed values ranged 3.6-11.3 s in an environment that only
advances animation frames when a screenshot forces one; a warm-style run measured 521 ms. Real
browser latency will be materially lower and is not asserted here.

### Responsive regression

Measured at the pinned viewports, with the layout observer driven manually because the preview
pane does not fire it on its own.

| Viewport | Mode | Map area (dashboard) | Map area (briefing) | Grid rows | H-overflow | Console errors |
|---|---|---|---|---|---|---|
| 1920x1080 | wide | 0.522 | **0.864** | 3 | 0 | 0 |
| 1536x864 | compact | 0.702 | 0.817 | 3 | 0 | 0 |
| 1366x768 | compact | 0.670 | 0.794 | 3 | 0 | 0 |
| 1280x720 | compact | 0.636 | 0.762 | 3 | 0 | 0 |
| 1024x768 | narrow | 0.777 | 0.777 | 3 | 0 | 0 |

Data Quality, Methodology, Date A/B and the Recovery Explorer were opened at each size: all
revealed, no horizontal overflow, no console errors. Briefing figures at 1536/1366/1280 are the
P8 measurements, unchanged by P10.

### Performance

| | before iteration 11 | after |
|---|---|---|
| app chunk | 347,159 B | 426,228 B (+22.8%) |
| MapLibre chunk | 1,053,009 B | unchanged |
| committed payload | — | 2.30 MB across 16 files |

The largest new payloads are lazy: `recovery_lifecycle.json` (107 KB) and `history_series.json`
(78 KB) load only when their panel is opened; `explanations_regional.json` (91 KB) loads with the
Inspector. No new runtime network dependency: a full scan of the frontend finds no external URL
other than an SVG XML namespace string.

### What could not be verified here

Stated rather than estimated:

- **Interactive frame-rate impact** of the rejected `preserveDrawingBuffer` architecture. The
  preview pane suspends `requestAnimationFrame`; measured directly, a rAF loop failed to complete
  one 800 ms sample in 45 s.
- **Browser print output.** Print CSS is written and the excluded selectors are verified in
  source, but no print preview could be rendered in this environment. The one-page Map Brief is
  **unverified visually** and should be checked by eye before being relied on.
- **Export latency** in a real browser, as above.

---

## Release blocker: resolved

The ledger had been reporting invalid lineage because the daily refresh moved `origin/main` to a
commit that was not an ancestor of this branch. That was correct behaviour, and it was resolved
the intended way — by integrating, regenerating, and proving ancestry — **not** by relaxing the
ancestry check, which is unchanged.

`lineage.valid = true`, `previous_is_ancestor = true`, baseline `1362ddb4`. See the lineage
table above.
