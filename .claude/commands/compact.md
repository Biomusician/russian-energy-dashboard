---
description: Compact this conversation, keeping the invariants that make the Energy Disruption Monitor safe and honest
argument-hint: "[optional: anything extra this compaction must preserve]"
---

Compact the conversation so far. Extra instructions from Jonathan (may be empty): $ARGUMENTS

This project is a **research and monitoring instrument whose product is calibrated honesty
about what is and is not known.** A summary that keeps the numbers but drops the rules that
govern them is worse than no summary, because the next session will act confidently on a
model it no longer understands the limits of.

## Never drop these, even if unmentioned for a long stretch

**The scope boundary.** Publicly reported disruption to energy infrastructure, aggregated to
administrative region. Never unit positions, readiness, fuel or ammunition state, vulnerability
or defensive-gap assessment, target prioritisation, ranking of undamaged assets, strike
planning, ingress/egress routing, range-to-target, or building-level coordinates. Incidents
carry no coordinates. The upstream Wikipedia "Distance (km)" column is deliberately not parsed.
Tests enforce all of this and must never be defeated or weakened to make something pass.
Sources are public, open and unclassified, always.

**The governing rule: never present an estimate as an observation.** If the data does not
support a number, emit `null` and make the UI say why. The index measures *exposure*, not
capacity loss. Recovery evidence is ranked observed > estimated > modelled and the `kind`
travels with every number. Exposure, assessed degradation, recovery and confidence stay
structurally distinct. Sectors without a capacity denominator are excluded and the weights
renormalised — never counted as zero, because zero means "measured, nothing wrong". Keep
**unknown**, **not applicable** and **not yet researched** distinct.

**Crimea.** A separately identified occupied unit, internationally Ukrainian,
`analytic_scope: "occupied"`, `esdi_included: true`. It contributes to the Monitored-Area index
and is never labelled a Russian region. The other four annexed oblasts stay excluded.

**This machine.** `.venv\Scripts\python.exe` — never bare `python`, three are on PATH. Every
file read/write passes `encoding="utf-8"` (the default here is cp1252 and the data is Cyrillic);
`PYTHONIOENCODING=utf-8` before printing diagnostics. Node is `scripts\npm.cmd`. Dev server runs
on port 5178. Paths contain spaces — quote them.

**Repo mechanics.** `data/curated/` is truth; `data/processed/` is a build artifact committed
only because Vercel has no Python — never hand-edit it, fix the source and rebuild. Every
scoring parameter lives in `methodology/scoring.json`. A `dataset-refresh[bot]` pushes to
`origin/main` daily: expect artifact conflicts on any branch, resolve them by **regenerating**
rather than choosing a side, and if the bot moves main again mid-release, re-integrate rather
than race it. Build-ledger lineage requires real git ancestry; the ancestry check is never
relaxed to make a delta appear.

## Keep, compressed

- Which iteration and phase is in flight, what shipped, what was explicitly deferred and why.
- Decisions and their **rationale** — the reasoning is the part worth carrying, not the verdict.
- Defects found and how they were fixed, especially any where a green test suite hid a real
  failure. Those are the ones that recur.
- Open limitations and anything recorded as *unverified* — never let an unverified claim get
  summarised into a verified one.
- Harness quirks that cost real time: the preview pane can suspend `requestAnimationFrame`
  (screenshots force frames) and may not fire its ResizeObserver (dispatch `resize` manually);
  `window.__map` exists only in dev builds; complex bash heredocs fail here, so write Python
  patch scripts with the Write tool and execute them; oversized browser results are saved to a
  file and should be decoded from there rather than pulled through context.

## Drop aggressively

Tool-call mechanics, file listings, failed attempts that were superseded, exploratory reads that
led nowhere, and narration of routine commands. Superseded numbers should go entirely — keeping
both an old and a new ESDI invites the next session to cite the wrong one.

## State is re-derived, not remembered

Do not carry current branch, test totals, ESDI values or deployment status forward as fact.
Record instead *how to establish them*: `git status`, `git log --oneline -15`,
`python -m pytest`, `cd web && ..\scripts\npm.cmd run test`, and reading
`docs/ITERATION_11_REVIEW.md` and `docs/HANDOFF.md`. Where the summary and the repo disagree,
the repo wins.

## Carry the verification standard forward

Written is never done. Run the tests **and** exercise the actual feature against the artifact
that ships — the exported file, the deployed page, the emitted payload — not the layer just
before it. This project has twice shipped a defect that a fully green suite could not see,
because the tests asserted on the object feeding the thing that mattered rather than the thing
itself. If something could not be verified, the summary must say so in those words.
