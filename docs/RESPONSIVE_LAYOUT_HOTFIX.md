# Responsive layout hotfix — map-first scaling

**Not an iteration.** Layout only. No analytical value changed: ESDI, the event corpus,
denominators, recovery, pipeline geometry, the canonical registry, GEM and ENTSOG are untouched,
and no processed-data rebuild was required.

## Reproduction

Measured against **production**, default load, real DOM bounding rectangles — not screenshots.

| Viewport | map | **map area** | ribbon | timeline | filters | dossier |
|---|---|---:|---:|---:|---:|---:|
| 2560×1440 | 1738×1212 | 57.1 % | 115 | 111 | 320 | 500 |
| 1920×1080 | 1178×852 | 48.4 % | 115 | 111 | 300 | 440 |
| 1600×900 | 906×661 | 41.6 % | 126 | 111 | 292 | 400 |
| 1536×864 | 842×624 | 39.6 % | 127 | 111 | 292 | 400 |
| 1440×900 | 746×646 | 37.2 % | 141 | 111 | 292 | 400 |
| 1366×768 | 672×514 | 32.9 % | 141 | 111 | 292 | 400 |
| **1280×720** | **1039×241** | **27.2 %** | **186** | 111 | 240 | 1039 |
| 1024×768 | 939×252 | 30.1 % | 215 | 111 | 240 | 939 |

**The demo failure reproduces at 1280×720** — a 1920×1080 monitor at 150 % OS scaling. The map
was 241 px tall and occupied 27.2 % of the screen. 1536×864 (125 % scaling) and 1366×768 are the
other realistic failure points.

## Root cause

Four causes, three anticipated and one not.

**1 · Fixed rails that grew on large screens.** `292px | map | 400px`, widening to `300/440` above
1800 px and `320/500` above 2400 px. Extra screen was being spent on the rails.

**2 · The `max-width: 1340px` rule stacked the dossier under the map** in a `1.35fr : 1fr` split.
At 1280×720 that split ~430 px of leftover height into a 241 px map and a ~190 px dossier. The
comment said the dossier "collapses under the map rather than squeezing it"; it squeezed it
harder than the docked column had.

**3 · `min-width: 1180px` + `overflow-x: auto`.** Below 1180 px the page became a horizontally
scrolling desktop. In practice content was clipped rather than reachable — at 1024×768 the scope
note was cut off at the right edge.

**4 · The ribbon wrapped, and this was the largest single cause.** `min-height: 92px` was a floor,
not a ceiling: `.ribbon-brand` and the metric cells carry their own `min-width`s, so below about
1500 px the flex row wrapped to a second line. Measured **115 px at 1920 → 141 at 1366 → 186 at
1280 → 215 at 1024**. It consumed *more* vertical space than the timeline and grew precisely when
space was scarcest. Nothing in the brief predicted this; it only showed up in measurement.

## The new architecture

Three modes on `<html data-layout>`, classified by **width and height** in `useLayoutMode.ts`:

| Mode | Layout | Trigger |
|---|---|---|
| `wide` | `filters │ MAP │ dossier` | ≥ 1560 × 760 |
| `compact` | `filters │ MAP` + dossier drawer | < 1560 **or** < 760 |
| `narrow` | `MAP` + both as drawers | < 1120 **or** < 560 |

Plus an orthogonal `data-chrome` axis (`compact` at viewport height ≤ 900) that shrinks the
ribbon and timeline, and a user-invoked `data-mapfocus`.

**Why a hook rather than pure media queries.** The mode depends on height, and it drives React
behaviour (docked vs overlay, and whether MapLibre needs a resize) rather than only paint.
Deriving it twice — once in CSS, once in JS — is how the two quietly disagree.

**Why these thresholds.** Each is the point at which the next-heavier mode would push the map
under its area target, computed from the measured chrome costs, not chosen for roundness. Rails
are `clamp(212px, 14vw, 264px)` and `clamp(300px, 19vw, 380px)` — they scale with the viewport
and are **capped**, so a 2560 px screen gives its extra pixels to the map instead of the rails.

## Result

| Viewport | mode | map | **after** | before | Δ |
|---|---|---|---:|---:|---:|
| 2560×1440 | wide | 1914×1212 | **62.9 %** | 57.1 % | +5.8 |
| 1920×1080 | wide | 1289×852 | **52.9 %** | 48.4 % | +4.5 |
| 1600×900 | wide | 1070×753 | **55.9 %** | 41.6 % | +14.3 |
| 1536×864 | compact | 1320×717 | **71.3 %** | 39.6 % | +31.7 |
| 1440×900 | compact | 1227×753 | **71.3 %** | 37.2 % | +34.1 |
| 1366×768 | compact | 1153×621 | **68.2 %** | 32.9 % | +35.3 |
| **1280×720** | compact | 1067×573 | **66.3 %** | 27.2 % | **+39.1** |
| 1024×768 | narrow | 1024×610 | **79.4 %** | 30.1 % | +49.3 |

Horizontal document overflow is **0 at every viewport**. Ribbon 186 → 99 px; timeline 111 → 46 px
in compact chrome. Every target in the brief is met.

At 1600×900 the chrome compacts at exactly 900 px height — that alone moved the map from 49.1 %
to 55.9 % and let the full three-column desktop survive at that size, which is the better trade
than undocking a rail.

## MapLibre resize

A `ResizeObserver` on the map container, plus a settle-resize keyed to a `layoutSignal` prop that
changes on mode, map-focus and dock/undock transitions. The map is never recreated.

Two deliberate choices:

- **Not gated on the map's `ready` state.** The failure being guarded against is a container that
  is 0×0 at construction; in that state the style never finishes and `ready` never becomes true,
  so an observer waiting for `ready` could never rescue it.
- **Debounced with a timer, not `requestAnimationFrame`.** rAF is suspended in a hidden or
  background tab, so an rAF-scheduled resize would never run for a container that changed while
  the tab was in the background — exactly when a missed resize is most likely. The same reasoning
  applies to the layout classifier, which also observes `document.documentElement` because the
  `resize` event is not fired for every change to the CSS viewport (browser zoom among them).

## Progressive disclosure, not deletion

No analytical content was removed.

- Ribbon metric cells scroll horizontally instead of wrapping; long coverage prose is clamped to
  two lines and keeps its full text.
- The scope note collapses to a 214×34 marker with a "more…" hint, expanding on hover or focus.
  It was 268×218 — 11 % of a 1280×720 map, permanently.
- Camera presets scroll rather than wrap or clip.
- The dossier's seven tabs are one scrollable row instead of three wrapped rows.
- The comparison tray's hard-coded `margin-left: 300px` (tied to the old filters rail width) is
  replaced with clearance relative to the map.

## Accessibility

Drawer toggles are real `<button>`s with `aria-expanded` and `aria-controls`; Map focus uses
`aria-pressed`. Closed drawers are `aria-hidden`. Escape closes the topmost drawer, and a scrim
gives a pointer route out. The drawers are non-modal, so focus is **not** trapped. A polite live
region announces the current mode.

## Verification

- 114 frontend tests (from 96), including the eight measured viewports as regression fixtures and
  four assertions that `checkLayout` still fails the pre-hotfix geometry.
- Verified in-browser at 1280×720: drawer open leaves the map width unchanged at 1067 px; Escape
  closes; Map focus takes the map 1067 → 1280 px and restores on exit; a gas-network filter set
  before entering map focus survives the round trip; the layout mode is not written to the URL.

## Limitations

- **The in-app browser pane suspends `requestAnimationFrame`**, which is MapLibre's render loop,
  so the map canvas does not paint in pane screenshots. Verified this affects unmodified
  production identically, and confirmed the map itself is healthy behind it —
  `isStyleLoaded: true`, 17 layers, canvas correctly sized. Screenshots in this environment are
  evidence of *layout*, not of map rendering; map rendering is verified on the deployed site.
- The pane's viewport emulation fires neither `resize` nor a root `ResizeObserver`, so mode
  changes during live emulated resizes had to be measured with a reload per viewport. Real
  browsers fire both; the app also observes the root element specifically so that zoom-driven
  changes are caught.
- `1024×768` is the narrowest tested viewport. Below ~900 px wide the drawers still work but the
  ribbon's pinned brand and ESDI block start to crowd; genuine phone widths are out of scope.
