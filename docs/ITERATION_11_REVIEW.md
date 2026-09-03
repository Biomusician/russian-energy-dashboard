# Iteration 11 — explainability, change attribution, and briefable views

Working notes for the iteration. Phases P1–P8; P9 and P10 outstanding.

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

### Performance

- Export at 1920×1080: **1227 ms** end to end, including creating the temporary map, loading the
  style, rendering and encoding.
- The same export at 2400×1350 (before the pixel-size fix) took 13776 ms — but both figures are
  inflated by the harness, which only advances animation frames when a screenshot forces a paint.
  Real-browser latency will be materially lower and is **not** claimed here.
- Persistent interactive cost: **zero by construction**. Nothing about the main map changed.

### Limitations

- Interactive frame-rate impact of the rejected architecture is unmeasured (see above).
- Clipboard copy is not implemented; download ships first, as `SHOULD` rather than `MUST`.
- The Analyst Report multi-page layout is not implemented.
- Export latency figures are harness-inflated and should be re-measured in a real browser.

---

## Outstanding release blocker

The build ledger reports invalid lineage: the daily refresh moved `origin/main` to a commit that
is not an ancestor of this feature branch, so the baseline is not a predecessor of this build. The
ledger correctly refuses to emit a delta. This is resolved at integration by fetching, rebasing
onto the true current main, regenerating the payload and the ledger against the real production
ancestor, verifying `lineage_valid = true`, and rerunning the affected tests — **not** by relaxing
the ancestry check.
