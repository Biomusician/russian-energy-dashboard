# MVP review

Written at the end of the first build, 26 August 2026. Read the limitations section
before quoting any number from this dashboard.

---

## 1. What works

**The pipeline.** `python -m pipeline.run` goes from five public sources to a deployed
dataset in about 35 seconds on a warm cache, deterministically, with no dependencies
beyond the Python standard library. It degrades rather than breaks: a source outage
falls back to the cached copy with a warning.

**The data is real.**

| Layer | Count | Source |
|---|---|---|
| Administrative regions | 69 | Natural Earth |
| Power plants | 432 (179,662 MW) | WRI GPPD |
| Major substations (≥220 kV) | 1,173 | OpenStreetMap |
| Transmission lines (≥330 kV) | 4,913 | OpenStreetMap |
| Gas / oil pipelines | 2,553 / 178 | OpenStreetMap |
| Struck facilities | 39 | Wikipedia strike tables |
| Events (2022–2026) | 128, 127 region-assigned | Wikipedia + curated |
| Citations | 137 | Reuters, Kyiv Independent, Moscow Times, Pravda, … |
| National refinery inventory | 30 (247.0 MTPA) | Wikipedia |

Nothing is synthetic. No placeholder rows exist anywhere in the dataset.

**The index behaves correctly under inspection.** Near zero through 2022 (which matches
the source benchmark's 3 strikes in war year one), rising through 2024–25, peaking at
26.5 on 11 July 2026, standing at 15.4 today. The Rostov NPP turbine event registers in
the electric-power sub-index in July 2024 and decays out — visible only when you scrub
back to it.

**Provenance survives to the UI.** Every event row renders its citations as clickable
links. Occurrence confidence is derived from how many distinct publishers are cited;
attribution confidence is a separate field that never exceeds "probable".

**The honesty machinery is load-bearing, not decorative.** The ribbon shows coverage
(127/305) and the quantified-capacity ratio (0/127) at the same visual weight as the
headline index. Unmeasurable sectors show "n/a — no capacity base" rather than a
misleading 0. Unmodelled effect categories render as "not modelled" with reasons.
Parser warnings from each build surface in the methodology panel.

**Scope discipline is tested, not just promised.** `tests/test_pipeline.py` fails the
build if a range-to-target field or an incident coordinate appears in emitted data, or
if occupied Ukrainian territory enters the region set. 32 tests pass.

**The frontend is genuinely dependency-light.** 71 KB gzipped of app code, MapLibre in
a separately-cached chunk, no basemap, no API key, no external network requests at
runtime.

---

## 2. What is incomplete

**Coverage is ~42%.** 127 enumerated events against a reported 305. The missing events
are reported only in prose. The main Wikipedia article on attacks in Russia is 298,000
characters with zero structured tables; parsing it was judged too likely to fabricate
records for an MVP.

**Electric power scores 0.0 today** and has essentially no history. Not a bug — we have
one power-generation event in the dataset. Strikes on Russian *generation* are far less
reported in structured form than strikes on refining, and grid events are mostly absent
from open structured sources.

**Gas and coal have no capacity base at all** and are excluded from the composite. The
pipeline layers are drawn on the map but score nothing, because OSM pipeline segments
carry no throughput figure.

**Four of the nine requested regional effect categories are not modelled** — industrial
impact, civilian electricity reliability, military-industrial implications,
cross-region dependencies. They are displayed as "not modelled" with reasons rather
than estimated.

**No conflicting-source resolution UI.** The `conflicting_reports` flag exists in the
schema, is set on one event, and renders as a tag — but there is no view that shows the
competing claims side by side.

**Curated file has five rows.** It is a working mechanism, not a populated dataset.

---

## 3. Limitations that will not go away by adding data

**The index measures exposure, not loss.** No amount of extra events changes this. Only
sources that quantify capacity effects would, and they are rare. Anyone reading ESDI as
"31% of refining is offline" is misreading it; the correct reading is "31% of tracked
refining capacity sits at facilities disrupted recently enough to still be plausibly
impaired".

**The refining denominator is low.** 247 MTPA across 30 refineries understates Russia's
true refining base, so refining exposure percentages are *higher* than they would be
against a complete inventory. Directionally the trend is sound; the absolute level is
inflated by an unknown factor, plausibly 20–30%.

**Regional scores are contributions to the national total, not regional intensities.**
"Leningrad Oblast 3.3" means Leningrad accounts for 3.3 points of national exposure, not
that Leningrad is 3.3% disrupted. This is the right choice given the data (see
METHODOLOGY §4) but it is not the intuitive reading, and the UI could state it more
loudly.

---

## 4. Weak assumptions, ranked by how much they matter

1. **Repair half-lives** (14–120 days by class). Pure assumption, no evidence base, and
   the single largest lever on every score. Halving the refinery half-life roughly
   halves refining exposure at any date. **Fix this first.**
2. **Sector weights** (refining 0.35, electric 0.30, oil logistics 0.20, gas 0.10, coal
   0.05). A judgement about systemic importance. Defensible, unvalidated.
3. **Area of interest** was the six western federal districts plus Belarus. (Iteration
   1 resolved the original phrasing ambiguity and locked the AOI explicitly, adding the
   Siberian Federal District; see docs/ITERATION_1_REVIEW.md.)
4. **Cause weights**, particularly maintenance at 0.15 and sanctions at 0.6. Sanctions
   effects are cumulative and slow; a single decaying event models them badly.
5. **Oil logistics uses the refining base as a proxy denominator.** Terminals and
   pipelines move more than domestic refinery feedstock, so this is imprecise in a
   direction that is hard to characterise.
6. **Confidence derived from citation count.** Two citations to outlets that both
   syndicated one wire report is not two independent confirmations, but it scores as
   "confirmed".

---

## 5. Data gaps worth filling, in order of value

1. **Electricity and grid events.** The largest hole. Would make the electric-power
   sub-index real. Likely sources: SO UPS (System Operator) disruption notices,
   regional utility statements, Russian regional press.
2. **A complete refinery inventory with regions.** Fixes the low denominator and enables
   genuine regional refining intensity.
3. **Refinery repair durations.** Would replace the worst assumption in the model with
   evidence. Reuters and Bloomberg report restart dates for major refineries.
4. **Prose-reported strike events (2022–23).** Closes most of the coverage gap. Needs
   careful extraction with a human in the loop.
5. **Gas and coal throughput baselines.** Would bring two sectors into the composite.
6. **Quantified capacity effects.** Even a handful would let the dashboard show a
   measured-loss figure alongside exposure.

---

## 6. Technical debt

- `pipeline/osm_probe.py` is a one-off kept in the repo as documentation for the tag
  choices. It is not part of the build and is not tested.
- Line-to-region assignment by midpoint is crude. Acceptable because lines are counted
  and never scored, but it would need real clipping before any per-region line metric.
- `build_index.py` recomputes every facility's weight at every one of 244 timesteps.
  Fine at this scale (~1 s); would need memoising at 10× the events.
- No end-to-end frontend test. Verified manually through the browser (region selection,
  filters, timeline, tallies) but nothing guards against regression.
- The `scope` column in the curated CSV is parsed but not yet used to distinguish
  national-scope from region-scope events in the UI.
- Node is vendored at `tools/node/` (106 MB, gitignored) copied from a sibling project
  rather than installed by a setup script of its own.

---

## 7. Questions for you

1. **Area-of-interest scope.** (Resolved in iteration 1: the AOI is now explicitly
   Belarus + six western districts + the Siberian Federal District.)
2. **Should Belarus be scored, or only shown?** It currently participates fully in the
   index, but it has had no recorded events, so it contributes nothing and sits on the
   map as empty area. Treating it as context-only might read better.
3. **Is exposure the right headline?** The alternative is to lead with the event count
   and recency, and demote the composite index. Exposure is more analytically useful
   but harder to explain in one line.
4. **How much curation effort is available?** The gap between 42% and ~90% coverage is
   human hours reading prose reporting, not engineering. If nobody will do that, the
   architecture should lean harder on the structured sources it can automate.
5. **Do you want asset-level detail visible at all?** Struck facilities are currently
   named in the dossier (they are named in public reporting) but never mapped to
   coordinates. That line could move in either direction.

---

## 8. Decisions to make next

| Decision | Options | Recommendation |
|---|---|---|
| Repair half-lives | Keep as assumptions · research real durations · make them user-adjustable in the UI | Research the top 10 refineries; make the rest adjustable |
| Coverage strategy | Accept 42% · manual curation · LLM-assisted prose extraction with human review | LLM-assisted extraction **with** mandatory human sign-off before a row enters the curated file |
| Regional framing | Keep contributions-to-national · add regional intensity where a denominator exists | Add intensity for electric power, where WRI gives a real denominator |
| Gas/coal | Leave uncovered · find throughput baselines | Leave uncovered until a real baseline exists — an empty sector is honest |
| Refresh cadence | Daily · weekly | Daily, as built. Upstream Wikipedia tables update within hours of events |

---

## 9. Next iteration — suggested order

1. Replace refinery repair half-lives with researched values; document each.
2. Build a complete Russian refinery inventory with region assignment.
3. Add an electricity-event ingestion path, even if it starts curated.
4. Add a conflicting-sources view for events flagged `conflicting_reports`.
5. Make scoring parameters adjustable in the UI, so a reader can test the model's
   sensitivity to the assumptions it rests on.
6. Add a frontend smoke test.

---

## 10. Verification performed

- 32 Python tests pass, covering date parsing, wikitext rowspan and ref handling,
  region resolution, index arithmetic, UTF-8 enforcement, and the scope boundary.
- `tsc --noEmit` clean; production build succeeds.
- Dashboard exercised in-browser: region selection updates the dossier and the timeline
  series; filters recompute tallies; the choropleth, legend, hover card and scrubber
  all respond; source links resolve to real articles.
- Region assignment spot-checked against known city coordinates and all nine nuclear
  plants.
- Enclave geometry verified (Moscow/Moscow Oblast, St Petersburg/Leningrad,
  Minsk/Minsk Region, Khanty-Mansi and Yamalo-Nenets/Tyumen, Nenets/Arkhangelsk) — no
  double assignment.
- Barrel-to-tonne conversion cross-checked against Omsk's published capacity.

**Not verified:** visual appearance. Screenshots were unavailable in this environment,
so the layout was confirmed structurally (computed grid areas, panel dimensions at
1280 px and 1920 px, no horizontal overflow) rather than by eye. **Look at it before
showing it to anyone.**
