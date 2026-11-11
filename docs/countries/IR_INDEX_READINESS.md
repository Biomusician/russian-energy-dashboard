# Iran — index readiness

Written 2026-11-11 by the Iran source-audit lane (iteration 19, Wave A). Companion to
[IR_SOURCE_AUDIT.md](IR_SOURCE_AUDIT.md), which carries the evidence and addresses for every source
named here. **No score is activated and nothing here changes a published number.** Incident
coverage is assessed from the nature of the sources, not from incident research, which is a
separate lane.

This document lists no facility and no facility capacity. Where a list exists, it says that a list
exists and where.

Readiness vocabulary, as in `SA_INDEX_READINESS.md`:

- **READY** — denominator exists on one stated basis, dated, complete enough to score against.
- **EXPERIMENTAL** — usable with disclosed caveats.
- **INCOMPLETE** — a credible path exists, but a required input is not acquired or reconciled.
- **UNSUITABLE** — should not be built, for data reasons, scope reasons, or both.
- **NOT_APPLICABLE** — the sector does not exist in the country (a sourced zero, not a gap).

Distinct from all of these: **unknown** (exists, unmeasured) and **not yet researched**.

---

## Bottom line

**CONTEXT_ONLY in every sector.** No Iranian sector has an index-grade denominator that could be
read this session, and the methodology decisions a country score needs
(`docs/GLOBAL_METHODOLOGY.md` §8) are not made. Two further reasons apply to Iran specifically:

1. **Access.** The bodies that hold the inventories (Tavanir, the refining company's current
   statistics, the gas company, the statistics office) could not be opened on 2026-11-11. That is
   an access limitation on this date. It does not show that the inventories do not exist.
2. **Campaign.** Iran is handled under the active-campaign rule. A facility-by-facility capacity
   table for a country whose facilities are being attacked would serve no analytic purpose while
   nothing is scored, and it is not built.

| Sector | Complete national inventory? | Capacity available? | Verdict |
|---|---|---|---|
| refining | not read; a national total only | national total, EIA estimate, early 2024 | **INCOMPLETE** |
| electric_generation | a 2015-vintage list only (WRI) | national total not read on a page | **INCOMPLETE** |
| transmission | none | none | **UNSUITABLE** |
| oil_logistics | none sought | none | **UNSUITABLE** |
| gas | not read | national production and consumption only | **INCOMPLETE** |
| coal | not yet researched | none | **INCOMPLETE** |

---

## 1. Refining — **INCOMPLETE**

| Item | Finding |
|---|---|
| Inventory | No official per-refinery table was read. NIORDC's site was reachable, but its statistical yearbooks stop at 1396-97 (about 2018-19) and are consumption statistics. SHANA and the ministry could not be opened. OPEC's bulletin is believed to carry member refinery capacity by location (**not verified**: HTTP 402). EIA's brief has **no** refinery table |
| National capacity | crude distillation "an estimated 2.1 million b/d", plus condensate splitter capacity 0.6 million b/d, at the beginning of 2024 (EIA, updated 2024-10-10) |
| Basis | EIA estimate. Crude distillation and condensate splitting are different quantities and Iranian official statements often add them (search results from SHANA quote combined figures near 2.2 to 2.4 million b/d in different years, **titles only, pages not opened**). Any denominator must state which it is |
| Vintage | early 2024, one point |
| Status, retirement | not available |
| Ownership | mixed state and privatised companies (**not verified this session**), so there is no single-publisher table of the Saudi kind |

**Path, if ever wanted:** a person reads the OPEC bulletin and NIORDC's current statistics in a
browser, reconciles crude-only against crude-plus-condensate, and builds a dated census at
province level. Not before the campaign ends and the methodology decisions are made.

**Incident coverage to expect:** partial for fires and explosions that domestic agencies report;
poor for unit-level technical outages; contested for attacks. No benchmark list exists, so a
coverage ratio cannot be computed and must read "unknown".

## 2. Electric generation — **INCOMPLETE**

| Item | Finding |
|---|---|
| Inventory | Tavanir is believed to publish detailed annual statistics (**not verified**: name did not resolve). The only list read is WRI GPPD v1.3 in the local cache: 107 plants, 61,362 MW, 75 rows credited to Tavanir, newest commissioning year 2015. GEM GIPT not acquired |
| National capacity | **not read on any page this session.** A search summary attributes about 94,600 MW to Tavanir's chief in spring 1404 (2025); the pages behind it did not load. EIA gives no installed figure, only that "available capacity was less than 78% of installed capacity" in 2023 |
| Generation | 360.7 TWh net in 2022: gas 85.2%, petroleum 8.1%, hydro 4.4%, nuclear 1.7%, other renewables 0.4% (EIA Table 1) |
| Basis | installed against available capacity differ widely here, by EIA's own statement. A denominator on installed capacity would overstate what the system can deliver in a normal summer |
| Status, retirement | none in WRI |

**The chronic shortfall is the central difficulty, not a detail.** EIA reports that peak summer
demand exceeded supply by 12 GW in 2023 and that the gap has recurred each summer since 2020; gas
shortage in winter pushes thermal plants onto liquid fuels. A system in standing deficit has no
clean "undisrupted" baseline. Scheduled load management is not an event in the sense the other
country systems use, and treating each day of it as an event would swamp everything else. See
lane IR3 in `IR_SYSTEMATIC_SWEEP.md`.

**Incident coverage to expect:** officials discuss the shortage freely, so rotating-outage seasons
are well reported at national level. Discrete plant or grid failures are reported unevenly, by
province. Customer counts are rarely given, so clause 5's threshold will often be unprovable and
the item held.

## 3. Transmission — **UNSUITABLE**

No regional inventory and no regional event stream was found, and a map of grid topology is outside
what this expansion may collect. Electricity is organised by regional electric companies that do
not follow the 31 provinces one-to-one (**not verified this session**). Recommend no Iranian
transmission sector; national aggregates may appear as dated context if a readable source is found.

## 4. Oil logistics — **UNSUITABLE**

No inventory was sought. Terminals, storage and crude pipelines for an exporter are export-route
material, which the brief excludes outright, as is all tanker and shipping material. The sector
stays uncovered (excluded, never zero), with the page saying it is not modelled for Iran and why.
Clause 2 and clause 3 events can still be recorded as events, at country precision under the
campaign rule.

## 5. Gas — split

Natural gas was 55.7% of Iran's primary energy production in 2022 and 67.6% of its primary energy
consumption (EIA Table 1). It is the main fuel of the power system (85.2% of generation). A sector
set that left gas as an afterthought would misdescribe this country.

### 5a. Gas processing — **INCOMPLETE**

No per-plant census was read. EIA carries a table of named projects only, which is not an inventory
and was not transcribed. The gas company's statistics could not be opened. National aggregates:
dry production 9.4 Tcf and consumption 8.9 Tcf in 2023 (EIA).

### 5b. Gas pipelines — **UNSUITABLE**

Route detail is out of scope. No layer, analytic or context.

### 5c. Gas storage — **not yet researched**

### 5d. LNG — **not yet researched**

No source read this session states whether Iran has an operating LNG terminal. EIA reports gas
exports of 515 Bcf in 2023 without stating the mode on the lines read. Do not record NOT_APPLICABLE
until a source says so.

## 6. Coal — **INCOMPLETE** (inventory not yet researched)

EIA Table 1 shows coal at under 0.1 quads: 0.3% of primary energy production and 0.4% of
consumption in 2022, with no coal-fired generation listed ("--"). That is small but **not zero**,
so the sector exists and NOT_APPLICABLE would be wrong. The cached OWID series shows well under
1 TWh of coal generation a year, which disagrees with EIA's "--" at the margin; neither figure
supports a sector of any size. No mine inventory was looked for: the bodies that would hold one
were outside this audit's source list. Clause 6 events (a mine event that materially cut supply)
can be recorded; nothing can be normalised.

## 7. Upstream — a note, not a sector

Petroleum and other liquids were 43.4% of primary energy production in 2022. The only upstream
figures read are national: 4.0 million b/d of liquids in 2023, of which almost 2.9 million b/d
crude (EIA). A search result title from SHANA quotes a national crude production capacity for
Mehr 1405; the page was not opened and the figure is not used. A field-level inventory is not
recommended. Clause 7 events can be recorded at country precision.

---

## Russia-model assumptions that fail for Iran

| Russia assumption | Iranian reality |
|---|---|
| A structured open-source strike table supplies events and a coverage benchmark | None identified. Coverage must read "unknown" |
| An undisrupted baseline exists between events | The power and gas systems run a standing seasonal deficit (EIA). Shortfall is the baseline |
| `heating_season_months` marks the stress season | Two stress seasons: summer for electricity, winter for gas |
| Sources date events in the Gregorian calendar | Solar Hijri, in Persian and Latin digits |
| Regions join by ISO code as Natural Earth carries it | Natural Earth's Iranian codes predate the 2020 renumbering and one is duplicated (audit §1.1); the units are moved to the current codes by name |
| WRI is an acceptable if stale generation list | Newest Iranian row is 2015; about a third short of the quoted national total |
| Recovery evidence accumulates and is published after a delay | Under the country campaign rule no facility status is collected at all |
| Attribution confidence can lean on publisher count | Domestic agencies repeat one official account; each party to the conflict makes claims about the other |
| National monthly series give independent context | No JODI submission since July 2018; international figures are third-party estimates |

## Transparency limits, stated once

- Most Iranian official and agency sites could not be read from this machine on 2026-11-11. The
  cause is not established.
- OPEC, IEA, the Energy Institute and S&P Global refused scripted access; GECF's bulletin exceeded
  the fetch size limit. Their figures are cited by a person or not at all.
- National generating capacity was not read on any page this session and is absent from the
  profile draft for that reason.
- Low or high reported counts for Iran are a property of this environment and must be presented as
  "coverage unknown".
