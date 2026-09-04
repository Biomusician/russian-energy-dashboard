# Iteration 12 backlog

Work deliberately **not** done in iteration 11. Nothing here was forgotten, and nothing here is
blocking: each item was considered during the release gate and set aside with a reason.

---

## Deferred features (cut from iteration 11 by decision, not by time)

### Command palette
A single keyboard-driven entry point for every view, metric, region and panel.

**Why deferred.** Iteration 11 was already a large release, and a palette adds interaction
surface without closing an analytical gap. It also overlaps the existing search box, so shipping
it late would have meant two half-answers to "how do I get to a thing".

**Where it would go.** The ribbon already enumerates every panel, and `urlState.ts` already names
every addressable piece of state — a palette is mostly a view over those two, not new state.

### Saved named workspaces
Naming a configuration — metric, date, filters, camera, comparison — and returning to it.

**Why deferred.** This one is genuinely stateful: it needs persistence, naming, collision rules
and a migration story for when the state shape changes. Deep links already carry a shareable
configuration, which covers most of the need without any of that.

**Prerequisite.** Iteration 11 added state that deep links do NOT yet carry (see below). Fix
that first, or saved workspaces will silently save less than the reader sees.

### Clipboard image copy
Copying an export straight to the clipboard rather than downloading it.

**Why deferred.** Shipped as a `SHOULD`, not a `MUST`. `copyBlobToClipboard()` exists in
`web/src/mapExport.ts` and works, but browser support is uneven and permission-gated, and no
caller uses it. Wiring it needs a fallback path and a way to tell the reader which happened.

### Multi-page Analyst Report
A long-form print product: map, decomposition, ledger, quality and lifecycle across several
pages.

**Why deferred.** Explicitly optional in the P8 brief. The one-page **Map Brief** ships and
covers the common case; a multi-page report is a document-design project, not a print stylesheet.

---

## Accepted limitations carried forward

These are known, deliberate, and documented rather than fixed.

### Deep links drop iteration-11 state
`encodeDeepLink` carries the older `cmp` region tray but not the two-date comparison, the open
recovery episode, or Briefing Mode. A shared link silently reproduces less than the sender saw.
Adding state to the URL during a release freeze risked backward compatibility for no analytical
gain, so it waits. Backward compatibility for existing links is verified and must be preserved.

### Rankings can include a zero-valued affected region
A region with a recorded incident but a currently-zero metric value can appear in a ranking at
0.00. Every ranked region has genuinely been affected — undamaged infrastructure is never ranked
— but a reader could misread the zero as "measured, nothing wrong". The regional zero taxonomy
now explains exactly that distinction in the Inspector; surfacing the same note inline in the
ranking row is the fix.

### `dashboard_first_seen_build` is built but inert
`lifecycle.build()` accepts a first-seen map derived from the build ledger and renders it
correctly when present, but nothing constructs one from git history, so all 26 episodes report
no first-seen date. The UI hides the line rather than guessing — the honest behaviour — but the
pathway is currently unused. Wiring it needs a ledger walk over more than one transition.

### Incident-level `first_seen` / `last_verified` are dead data
`data/curated/incidents.csv` carries curator-entered `first_seen` and `last_verified` columns
that reach `incidents.json` and are read by nothing. All rows share one bulk-stamped date, so
they describe a stamping event rather than per-incident knowledge. They must not be surfaced as
temporal facts without being re-derived — and they share a name with the lifecycle concept,
which is a trap worth removing.

### `http_source_metadata` retrieval basis is never produced
Nothing reads HTTP response metadata, so the only retrieval basis that would legitimately count
as a publisher signal is never emitted. The enum keeps the distinction because it is real; the
empty branch is the honest state, not an oversight.

### Interactive frame-rate impact is unmeasured
See the performance section of [ITERATION_11_REVIEW.md](ITERATION_11_REVIEW.md). The preview
environment used for verification suspends `requestAnimationFrame`, so map-ready time, pan/zoom
and resize responsiveness could not be measured. Recorded as unmeasured rather than estimated.
