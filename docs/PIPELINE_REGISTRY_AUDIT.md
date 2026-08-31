# Canonical pipeline registry — audit

What the registry contains, what it deliberately does not, and where the judgement calls were.

Reproduce the counts with:

```bash
.venv\Scripts\python.exe -m pipeline.pipeline_registry
```

## Shape

| | |
|---|---:|
| Curated entities | **36** |
| — by level | 2 system · 7 corridor · 24 pipeline · 3 branch |
| — by commodity | 24 gas · 12 oil |
| — with a structural parent | 16 |
| Auto-derived entities (one per unmatched OSM route) | 255 |
| **Total in the emitted payload** | **291** |
| Source mappings (canonical) | 29 — 26 OSM · 3 GEM |
| — relationship | 20 `represents` · 6 `aggregates` · 3 `part_of` |
| — confidence | 20 `exact` · 9 `strong` |
| Entities carrying ≥1 source | 22 |
| Temporal status records | 27 across 15 entities |
| — by kind | 16 commercial flow · 7 physical · 4 operational |
| Canonical nodes | 34 |
| Topology assertions | 54 (46 with a resolved subject, 44 with a resolved node) |
| Review queue | 11 rows — 4 accepted · 3 unresolved · 3 rejected · 1 unmatched |

## The four separations the schema exists to protect

**1 · Identity is not name.** Mapping is many-to-many in both directions and every row carries the
evidence that justified it. `represents` is one-to-one; `aggregates` means the source object covers
several of ours (an OSM superroute, a national network modelled as one relation); `part_of` is the
inverse. Two rows in the canonical map were matched on **shareholders and endpoints, not on name**
— CPC (whose GEM name "Caspian Pipeline" is a substring of two unrelated routes) and Surgut–Polotsk
(which GEM names through an intermediate node).

**2 · Hierarchy is structural, not textual.** `entity_level` and `parent_id` are columns, never
something inferred from a name or a note. This is what makes the double-count question answerable:
`NORTHERN_LIGHTS` is a corridor whose children are the Ukhta–Torzhok strings, OSM models both, and
summing them counts the same pipe twice. See [PIPELINE_GAP_LEDGER.md](PIPELINE_GAP_LEDGER.md).

**3 · Status is temporal and multi-kind.** `physical`, `operational` and `commercial_flow` are
tracked separately over validity intervals. Yamal–Europe is why: the pipe is intact and commercial
transit has been zero since May 2022. A single `status` column would have to publish one of those
and suppress the other. `status_at(records, kind, when)` answers *what was true on date D*.

**4 · Geography is optional.** All **34 nodes carry `geography_precision = none`** and no
coordinates. Torzhok, Sudzha GMS, Mozyr, Velke Kapusany and the rest are real, named, sourced
connection points whose position was never looked up — because nothing needs it. Only
`coordinate` precision may carry lon/lat, and a test enforces it. Geocoding a topology-only
assertion to make it drawable is the failure mode this column exists to prevent.

## Judgement calls, and what they cost

### The alias gaps were closed by curation, not by loosening the matcher

`reconcile_gem.py` compares **normalised full names for equality**. No substring, no fuzzy ratio,
no token overlap. That is deliberate: this iteration already has a scar from substring matching,
where `Ukhta–Torzhok 1` swallowed strings 2 and 3 (review RV-002/RV-003).

The strict matcher initially missed Druzhba, Bukhara–Urals, Baltic Pipeline System 1 and eleven
others, because GEM's name and ours differed by a word. **Fourteen aliases were added to the
registry; the matcher was not relaxed.** Auto-mapping then rose from 31 rows to 66.

That distinction matters. Adding an alias is a human asserting "these two names denote the same
thing", recorded in curated data and reviewable. Widening a matcher is a machine guessing it, once,
everywhere, invisibly.

### What the review queue caught that a name match would not have

| Row | Case | Disposition |
|---|---|---|
| RV-005 | GEM "Caspian Pipeline" = CPC — proven by Tengiz→Novorossiysk-2 endpoints and a shareholder list that is verbatim the consortium | ACCEPTED (`strong`) |
| RV-008 | OSM carries Ukhta–Torzhok **3** as mapped existing geometry; GEM records string 3 as **proposed**, and adds a fourth | **UNRESOLVED** |
| RV-009 | "Yamal Europe 2" is a **cancelled** Belarus→Slovakia project, not the operating Torzhok→Mallnow trunk | **REJECTED** |
| RV-010 | Three OSM relations are named "Nord Stream"; r2006544 has six member ways of which **zero are its own** | **UNRESOLVED** |

RV-008 is the one to read twice. Two sources disagree about whether a pipeline is *built*. The
registry keeps the OSM-derived entity and the row records that GEM disagrees. Nothing was
harmonised. Modelling rule 5 says disagreement survives contact with the model.

RV-010 is a caution about arithmetic evidence: r2006544's 2,448.7 km is within 0.02 % of twice
Nord Stream 1's length, which made "NS1, both lines" look obvious. Way-level membership refuted it
— 4 of its ways are NS1's, 2 are NS2's. A plausible number is not a source.

### 66 GEM mappings are proposed, not canonical

`data/review/gem_source_map_proposal.csv` holds 66 auto-matched rows covering 22 entities. They
are **not** in `data/curated/pipeline_source_map.csv`, which carries only the 3 hand-verified GEM
mappings.

The rule permits `exact` to auto-merge, and these are exact *name* matches. They have not been
promoted because Nord Stream demonstrated that **an exact name match is not an exact identity
match** — three relations share that name and the exact one resolved to an auto-derived entity.
Promotion is a one-pass human review of a 66-row file, and it is the obvious next task. Until then
the honest statement is: *GEM is reconciled and the mapping is inspectable; three mappings are
canonical.*

## What is deliberately absent

- **No geometry from GEM.** 698 of the 1,917 GEM rows for this area carry GEM's own straight-line
  or schematic geometry. `GENERALIZED != MAPPED`: a schematic line must never overwrite a traced
  one, and no precedence rule has been written yet, so none was applied.
- **No unresolved-gap length.** Gap *counts* are reported; gap *lengths* are not, because the
  straight line between two mapped components is not the pipe between them.
- **No coordinates on topology-only nodes.** See above.
- **No capacity or length figures invented to fill a column.** GEM's `--` sentinel maps to `None`,
  never to `0`; "unknown" and "zero" are different states.
- **Nothing from GEM enters ESDI.** Verified structurally: `build_index.py`, `build_assets.py` and
  `run.py` contain no GEM import, and all 1,292 route features carry `scope: context`.

## Known weaknesses

1. **255 auto-derived entities carry a source's raw name as their identity.** They are excluded
   from search for that reason, but they still appear in the route detail panel labelled
   "auto-derived from source". They are a backlog, not a model.
2. **The proposal file is not yet promoted** (above).
3. **Only 15 of 36 curated entities have any temporal status.** The other 21 are silent, which the
   schema represents correctly as *not yet researched* rather than as *nothing happened* — but it
   is still absence.
4. **Node geography is entirely unresolved.** That is correct for now and would need a decision,
   not a script, to change.
5. **`operational` status is thin** — 4 records. Physical and commercial flow carry the weight.
