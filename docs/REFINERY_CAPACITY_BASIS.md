# The refining capacity basis — a methodology proposal, NOT deployed

Written during iteration 13 (2026-10-16). **Nothing in this document has been applied to the
published index.** It exists because changing it would materially change what the headline
number means, which is a decision for the project owner and not for the session that found it.

For current figures see [CURRENT_STATE.md](CURRENT_STATE.md); the magnitudes below were
measured on the 2026-10-16 build and are recorded here as dated findings, not as live values.

---

## The short version

The refining sector's **numerator and denominator are drawn from different sources**, and for
the same physical plants those sources disagree.

- The **denominator** — 273.8 MTPA across 35 plants — comes from the curated canonical registry
  (`data/curated/refineries_canonical.csv` plus the inventory built by
  `pipeline/fetch_refineries.py`, sourced from Wikipedia's *List of oil refineries*).
- The **numerator** — each struck plant's exposed capacity — comes from the **strike table's own
  "Capacity by MTPA" column** on the *Deep strike campaign* page.

Two consequences follow, pulling in opposite directions. They do not cancel; they are separate
defects that happen to have opposite signs.

---

## 1. The two bases disagree by about 6%, and by 2.3× for one plant

Across the 23 scored refineries that resolve to a registry entry:

| | MTPA |
|---|---|
| summed as the **numerator** scores them | **217.65** |
| the same plants in the **denominator** | **206.00** |
| difference | **+11.65 (+5.7%)** |

**19 of the 23 differ.** The largest:

| plant | scored as | registry says | difference |
|---|---|---|---|
| TANECO | 17.00 | 7.45 | **+9.55** |
| Novoshakhtinsk | 13.00 | 8.57 | +4.43 |
| Omsk | 22.00 | 17.97 | +4.03 |
| Syzran | 9.00 | 5.98 | +3.02 |
| Antipinsky | 6.00 | 8.94 | −2.94 |
| Ufimsky | 3.80 | 6.40 | −2.60 |
| Novo-Ufimsky | 3.80 | 6.08 | −2.28 |

### Why this matters more than the percentage suggests

`refinery_inventory.json`'s reconciliation note currently reassures the reader that

> a **uniform** nameplate revaluation — scaling all tracked plants up together — leaves the
> exposure essentially **invariant** (numerator and denominator scale together).

That argument is sound, **and it only holds if both sides share a basis.** They do not. The note
is defending a property the code does not have, which is the most consequential thing in this
document: a reader is being told the measure is robust to a revaluation it is not actually
robust to.

Structurally, a fully-struck fleet can exceed 100% of its own base.

---

## 2. Two denominator members cannot reach the numerator at all

Moscow and Volgograd are **members of the refining denominator** and are **live**, and they
contribute **exactly zero** to the refining numerator — because their strike-table rows have an
empty capacity cell and `_share()` returns `0.0` when capacity is `None`.

| plant | impairment weight | denominator MTPA | share of base | refining points not counted |
|---|---|---|---|---|
| Moscow refinery | 0.671 | 12.15 | 4.44% | 2.98 |
| Volgograd refinery | 0.092 | 12.41 | 4.53% | 0.42 |
| | | | **total** | **3.40** |

That is **about 1.4 index points**, roughly an eighth of the headline, on the 2026-10-16 build.

An unknown quantity is being scored as if it were zero, inside the index itself. This is the
one thing the project's own governing rule forbids. It was disclosed *qualitatively* — the
regions carry `zero_basis = COVERED_IMPAIRMENT_WITH_NO_CAPACITY_FIGURE`, and
`capacity_measurement_audit` counts the events — but the **magnitude was never stated
anywhere**. As of iteration 13 it is: `snapshot.impairment_not_sized`. The index is unchanged.

---

## Why this was not simply fixed

The obvious repair for (2) is to size Moscow and Volgograd from the registry that already puts
them in the denominator. That is a one-line change and it is **not** obviously right, because
it would put those two plants on a like-for-like basis while nineteen others stay on the strike
table's basis — making the mixture worse, not better, while raising the headline.

So the question is not "should Moscow be sized". It is **which basis the refining sector uses**,
and that is a methodology decision.

---

## The options, with their measured effects

All figures are from the 2026-10-16 build, headline **10.50**.

### A. Status quo — mixed basis (deployed today)

Numerator from the strike table, denominator from the registry. Moscow and Volgograd score zero.

- Headline **10.50**.
- **Against it**: the numerator runs ~5.7% hot; the invariance claim in the inventory note is
  false as written; two large plants are counted in the base and not in the measure.
- **For it**: the strike-table capacity is the figure attached to the event by the source that
  reports the event, so numerator and event share a provenance.

### B. Registry basis throughout — like-for-like

Take every scored plant's capacity from the canonical registry, the same source as the
denominator. Plants not in the registry keep no capacity and remain unsized (correctly — they
are not in the denominator either, so there is no asymmetry).

- Expected direction: the numerator falls ~5.7% on the 23 resolvable plants, while Moscow and
  Volgograd (+3.40 refining points) become countable. **Not yet computed end-to-end** — see
  "What is still unmeasured".
- **For it**: one basis, stated once. The invariance argument becomes true. Nothing is counted
  in a base it cannot appear in.
- **Against it**: the registry's figures are themselves Wikipedia-sourced nameplate, of mixed
  vintage, with no retirement field; TANECO at 7.45 against a scored 17.0 is a 2.3× gap that
  deserves its own source check before either number is trusted.

### C. Registry basis, with the strike table kept as a disclosed alternative

As B, but publish the strike-table-basis value beside it as a sensitivity, the way the
transmission saturation sweep is published.

- **For it**: the reader sees the basis disagreement rather than being asked to trust a choice.
  It is also the pattern this project already uses for its other weakest input.
- **Against it**: a second refining number on the page needs very careful labelling, or it
  becomes exactly the "two plausible-looking values, pick one" problem the project avoids.

### D. Size nothing that the denominator cannot size, and say so

Keep the mixed basis but **exclude** from the denominator any plant the numerator cannot size,
renormalising — the treatment uncovered sectors already get.

- **For it**: internally consistent by construction, and it uses machinery that already exists
  and is already tested.
- **Against it**: it shrinks the denominator to flatter the measure, and it means a plant drops
  out of the base because of a missing cell in one Wikipedia column — which is a data artefact
  driving a methodological boundary.

---

## Recommendation

**C**, with **B** as the fallback if a second published number is judged too confusing.

The decisive consideration is not the 5.7%: it is that the inventory note currently makes a
robustness claim the architecture does not support. Whichever option is chosen, **that note must
be corrected**, and that correction does not require a methodology change and should not wait
for one.

A prerequisite for B or C: **check TANECO against a current public source.** A 2.3× disagreement
on a single plant is more likely a stale or wrong figure on one side than a basis difference,
and it is large enough to move the sector on its own.

---

## What is still unmeasured

Stated plainly rather than implied:

- The **end-to-end headline under option B has not been computed.** The direction is known
  (numerator down ~5.7% on the resolvable plants, +3.40 refining points from Moscow and
  Volgograd) but the two effects interact through the per-facility maximum and the decay, so
  the net has to be run, not estimated. It needs a build with the numerator re-sourced, which
  is the change this document declines to make.
- **Which of the two figures is right, plant by plant**, has not been researched. This document
  establishes that they disagree, not which is correct.
- The registry's own vintage and retirement coverage is a separate open question, tracked
  against the generation denominator in [GENERATION_DENOMINATOR_AUDIT.md](GENERATION_DENOMINATOR_AUDIT.md).

---

## How this was found

Iteration 13, by an independent agent asked to recompute the published index from the curated
inputs and the declared methodology without calling the pipeline's own scoring code. The
reconciliation was otherwise **exact** — every sector value, the composite, the renormalisation,
the ex-transmission identity, the regional decomposition and all 251 timeline steps matched to
machine precision. The basis asymmetry is not an arithmetic error; the arithmetic is right. It
is a question about which number the arithmetic is fed.
