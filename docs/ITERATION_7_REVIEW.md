# Iteration 7 review — denominator closure, recovery coherence, transmission validity, gas decision

Follows [ITERATION_6_REVIEW.md](ITERATION_6_REVIEW.md). Theme: **an analytic-integrity pass, not a
feature pass.** Close the important denominator gaps, make recovery state internally coherent, and
decide which proxies deserve to stay in the headline. The headline did not move (real-date ESDI
**18.17**, frozen 2026-08-28 **18.49** — unchanged); what changed is how defensible each number is.

Live headline numbers are generated — see [CURRENT_STATE.md](CURRENT_STATE.md). This review records
the reasoning; it does not re-quote changing numbers.

## Baseline (iteration 6 tip)

| | Value |
|---|---|
| Git SHA | `c6a682f` (iteration 6 merge) |
| ESDI | 18.17 real-date / 18.49 frozen 2026-08-28 |
| Coverage | 144 / 305 = 47.2% oil-strike benchmark |
| Recovery | 7 observed episodes, 20 records |
| Refining | 34 denominator refineries / 273.8 MTPA |
| Gas | experimental, 26.8% of a 91.56 bcm/y 12-plant census |
| Transmission | 20.88 at saturation 8 |
| Tests | ~141 python cases |

## Semantic audit (§1-2)

A residual stale comment in `build_index.py` still claimed "Crimea … contributes to its own
regional exposure but never to the national composite" — **false** (Crimea is `esdi_included=True`
and is ~45% of transmission). Fixed, plus two more (`config.context_units`, `regionmatch`). Added a
**lint test** (`test_no_source_text_claims_crimea_is_out_of_the_composite`) that scans code + current-
state docs (not historical reviews) and fails on any "Crimea/occupied never enters the composite"
phrasing — this class of bug has now shipped twice and is guarded.

Terminology (§2): the whole-area views were mislabelled "National" though the area is Belarus +
Russian regions + occupied Crimea → relabelled "Monitored area". Conversely the refining/generation
CAPACITY denominators are Russia-only → the Methodology now says "Russian national capacity base".
No schema-breaking rename; internal `national` variables kept where harmless.

## Refining denominator (§3-7)

Iteration 6 solved refinery *identity*; iteration 7 addressed *completeness*. An independent
open-source census (triangulated: Carnegie Oct-2025 + Reuters/industry) found:
- **Reference: ~327 MTPA nameplate** (range 320-330), Russia-only, includes gas-condensate splitters
  and mini-refineries. (2024 THROUGHPUT was ~267 MTPA — not capacity; a common conflation.)
- **No major crude refinery is missing.** Every top-tier Russian refinery maps to the tracked 34.
- The ~53 MTPA gap to 327 = **~24 MTPA gas-condensate splitters** (Surgut CSP 12, Novatek Ust-Luga 9,
  Astrakhan line ~3) that make motor fuels from condensate not crude — excluded by the same rule as
  Tobolsk — plus **~29 MTPA** because the tracked figures use one consistent public source (~10-15%
  below current nameplate).

**Decision: keep the one consistent basis, do not revalue.** Swapping to a mixed nameplate basis
(some plants single-sourced) would risk cherry-picking and introduce errors; the honest move is to
DISCLOSE. No capacity changed → ESDI unchanged. Emitted denominator-completeness **metadata** (§6),
structurally distinct from event coverage: reference nameplate 327, like-for-like crude reference
~303, `denominator_coverage_pct` 90.4% against the crude reference (NOT a naive 273.8/327 universe
mismatch), a gap decomposition (24 condensate + 29 basis + 0 missing), and the plain statement that
refining struck-shares are therefore **conservative UPPER bounds**. Belarus (Mozyr/Naftan) confirmed
outside. A future pass could revalue uniformly to a full-nameplate basis.

## Recovery semantics (§9-15)

The iteration-6 wart was that `incident.status` (damage) and the recovery record could contradict
(Unecha). Iteration 7 separates **three orthogonal concepts** so they cannot contradict silently:
- **A. Damage severity** (`recovery.damage_severity` from `incident.status`) — initial hit severity,
  applied ALWAYS and independently of recovery.
- **B/C. Recovery** — the record sets the decay half-life and, for a credible full reconstitution,
  caps the tail.

`_weight_at` now applies damage severity orthogonally instead of only when the recovery kind is
"modelled". This makes adding a recovery record **structurally monotonic**: partial restart scores
exactly like no record; full ≤ substantial ≤ partial; stronger recovery never raises the score. The
iteration-6 status-coupling bug is now impossible, not patched. **Property tests** sweep statuses ×
classes × ages to prove it. `'repaired'` is no longer a damage state — the 3 incidents that held a
recovery state in the damage field were migrated (all weight-0 at the frozen date, so the headline is
unchanged; rostov/kursk historical curves become more accurate). Frozen ESDI unchanged at 18.49.

**Evidence families (§15)**: recovery is now grouped into `facility_reconstitution` | `unit_restart`
| `service_restoration` | `flow_rerouting` | `estimate`, surfaced in a Recovery-tab block — only
facility_reconstitution means the struck equipment itself returned. Current mix: service_restoration
12, unit_restart 7, facility_reconstitution 2, flow_rerouting 1, estimate 3.

## Recovery evidence (§13-14)

Corpus grown 20 → 25 records, 7 → 9 observed episodes. 4 new sourced episodes (Orenburg GPP 3-day
staged line restart; Kursk NPP 7-day output restoration; Balashovskaya + Oryol service re-
energisation). **electric_generation gets its first two observed episodes** (Kursk 7d, Rostov 1d).
Key honest finding: **transmission/substations still have ZERO physical-reconstitution durations** —
every substation source gives only emergency supply re-energisation around a still-damaged node;
oil terminals have none either. Reported as service-restoration evidence, never dressed as facility
repair. Refining kept its per-class median (47d, n≥3); no other class yet qualifies.

## Gas processing (§16-20)

Census verified: all 12 GPPs genuine; only Minnibaevo corrected (0.45 → 0.8 bcm/y, Tatneft actual
throughput). **No missing in-AOI plant** (Amur GPP 42 bcm/y is Far East, out of AOI; Surgut/Novy
Urengoy/Purovsky are condensate stabilisation — different function). **No matched external
denominator** (Gazprom's 110 bcm is operator-scope + multi-district incl. out-of-AOI Amur).

**Decision (§19): stays EXPERIMENTAL, out of the headline.** It cannot graduate because (a) no
matched denominator and (b) the census mixes design nameplate (Orenburg 45, Astrakhan 12 — actual
much lower) with actual throughput, so it is not like-for-like. Recorded as `graduation_decision` +
`graduation_reasons`. The caveat forbids ever summing gas processing + LNG + gas pipelines into one
"Gas" super-score (§20). Within-census exposure 27.0% (census 91.91 bcm/y).

## LNG (§21)

Lower priority. Only operating liquefaction would belong in a liquefaction denominator; FSRU import/
regasification is a different function. No qualifying disruption incident exists (Novatek Ust-Luga is
a gas-condensate/LNG complex, tracked as gas_processing, not liquefaction) — inventory ≠ disruption,
which is fine. No LNG denominator built.

## Transmission (§22-26)

The least physically-grounded covered sector: an event-burden against an arbitrary saturation
constant (~4× sensitivity), theatre-concentrated, occupied Crimea ~45%. Five formulations were
computed on the frozen data and given to an **independent red-team**: A (current) 21.35, B (per-
region breadth-aware) 20.21, C (breadth 3 / intensity 11.6), D (distinct-facility) 62.5, E (remove →
ESDI 18.10, i.e. transmission adds +0.39).

**Verdict: keep Model A in the composite, relabel, do not amputate.** A is the only formulation that
jointly honours recency, evidence, damage severity and voltage class, is structurally immune to
repeat-strike double-counting (a node's strongest live trajectory wins, never the sum), and fits the
service-only recovery evidence we actually have. B's breadth-awareness is dormant at current
magnitudes; D (62.5) is the single most misleading number; C is kept as a supporting display; E buys
only +0.39 of "purity" while discarding real signal and is the option most exposed to the appearance
of tuning Crimea away. The honest fix is **labelling not surgery**: the sector is relabelled
"**Transmission burden**" everywhere (never "% offline"), the ex-transmission counterfactual (18.10)
is published, and the concentration/sweep/alternatives are all disclosed. Crimea's inclusion is
untouched (its 44.7% share is a consequence of the fixed analytic choice, not tuned).

## Uncovered-sector sensitivity (§27)

`esdi_all_sectors` was too easy to misread as a second valid ESDI. Renamed to
`uncovered_zero_assumption_sensitivity` — a sensitivity under the explicitly-FALSE assumption that
gas & coal are zero, not a measurement. Old field kept as a deprecated N-1 alias; UI relabelled
"uncovered-sectors-zero sensitivity". Unknown stays unknown.

## Effects (§28-31)

Corpus 15 → 26 (8 macro + 18 per-incident across 15 incidents). New: Kirishi ×2, Ryazan ×2,
Novokuibyshevsk, Novoshakhtinsk, Kerch TPP outage (a proxy "half the peninsula" claim, explicitly
NOT a consumer count), and macro datapoints (17% refining disrupted Aug-2025; diesel export ban +
collapse to 80k bbl/d; AI-95 record price). Added a lightweight **source_quality** tier (§31) for
triage/provenance — separate from evidence_kind and occurrence confidence, not a hidden score. No
repair-cost dollar figure was found, so none is stored. Macro figures carry their own date/period and
are never asserted to be caused by specific dashboard incidents.

## Zero-count audit (§32)

Re-run. Filter visibility is data-driven off `facet_counts` (zero keys omitted → dead controls hidden
automatically). Current zeros — sabotage, cyber, dedicated maintenance — are genuine absences in a
drone-strike corpus (maintenance accidents are captured as `technical`; coal has inventory but no AOI
disruption). No category was populated for cosmetic completeness; no new dead control was introduced
(new effect types and recovery families are display fields, not filter dimensions).

## ESDI — frozen decomposition ledger (2026-08-28)

Every material change was measured at the frozen date; the residual is zero.

```
baseline (iteration 6)                              18.49
+ semantic-comment / lint / terminology            +0.00  (comments + labels)
+ recovery state refactor + repaired migration     +0.00  (neutral; property-tested)
+ 4 new recovery observations                      +0.00  (gas unscored; kursk closes fast)
+ refining denominator metadata                    +0.00  (no capacity revalued)
+ gas Minnibaevo correction + caveats              +0.00  (gas out of headline)
+ transmission alternatives + relabel              +0.00  (formula unchanged)
+ uncovered-zero rename                             +0.00  (same value, new name)
+ effects + source_quality                         +0.00  (observational)
= final                                            18.49
```
Iteration 7 is **scoring-neutral by construction** — it improved defensibility, not the number.

## Independent final red-team

<!-- FINAL RED-TEAM: filled from the independent adversarial review before deploy. -->

## Production

<!-- deploy SHA, live verification — filled at Phase K. -->

## Limitations (aggressive)

1. **The refining base is still a conservative single-source vintage** ~10-15% below nameplate — a
   real bias that inflates refining struck-shares; disclosed, not corrected. A uniform nameplate
   revaluation is deferred.
2. **Transmission is still an arbitrary-constant proxy** (4× sensitivity), retained on labelling +
   disclosure rather than a physically-grounded measure; ~45% is occupied Crimea by analytic choice.
3. **Gas processing has no defensible denominator** and mixes design/actual — a sample, not a rate.
4. **Recovery is still thin (n=9 observed)**; transmission/oil-terminals have no physical-
   reconstitution durations at all — only service restoration.
5. **The recovery decay horizons remain modelled assumptions** for every class without observed
   episodes.
6. **Candidate discovery stays manual** (no reachable no-key feed found — see §30 in the code).
