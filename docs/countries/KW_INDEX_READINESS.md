# Kuwait — index readiness

Written 2026-11-11 by the Kuwait source-audit lane (iteration 19, Wave A). Companion to
[KW_SOURCE_AUDIT.md](KW_SOURCE_AUDIT.md), which carries the evidence and addresses for every source
named here. **Nothing here changes a published number, and no score is activated.** Incident
coverage is assessed from the nature of the sources, not from incident research, which is a
separate lane.

Readiness vocabulary, as in `SA_INDEX_READINESS.md`:

- **READY** — denominator exists on one stated basis, dated, complete enough to score against.
- **EXPERIMENTAL** — usable with disclosed caveats; a labelled sensitivity, not a headline.
- **INCOMPLETE** — a credible path exists, but a required input is not yet acquired or reconciled.
- **UNSUITABLE** — should not be built, for data reasons, scope-boundary reasons, or both.
- **NOT APPLICABLE** — the sector does not exist in the country's energy system (a sourced zero,
  not a gap). Distinct from **UNKNOWN** (exists, unmeasured) and **NOT YET RESEARCHED**.

This document names no facility and gives no facility capacity. Where a list exists it says so and
says where.

---

## Bottom line

**CONTEXT_ONLY** today, and likely to stay so.

Two things block a score, and they are different in kind. First, **the national denominators that
would be needed were not acquired from a Kuwaiti source**: the ministry's yearbook page offers no
file, the statistics bureau's terms are unread, and the oil companies' report lists are mostly
script-only. Only EIA's national totals were read. Second, and more lasting, **the system has so
few facilities in each class that a sector share would be a facility's status under another name**,
and attack records are held at country level for that reason.

| Sector | Complete national inventory | Capacity available | Basis and vintage | Verdict |
|---|---|---|---|---|
| refining | yes (EIA Table 3) | yes, national total | nameplate, 2023; secondary compilation | **UNSUITABLE** |
| electric_generation | exists in the ministry yearbook; not acquired | national total only (EIA) | installed, 2024 | **INCOMPLETE** |
| transmission | none read | — | — | **UNSUITABLE** |
| oil_logistics | none sought | — | — | **UNSUITABLE** |
| gas | none read | national production, consumption, imports (EIA) | dry gas, 2024 | **UNSUITABLE** to score |
| coal | — | — | EIA: zero production, 2024 | **NOT_APPLICABLE** |

---

## 1. Refining — **UNSUITABLE** (context only)

| Item | Finding |
|---|---|
| Inventory | EIA's Country Analysis Brief (updated 20 July 2023), Table 3, lists the country's refineries. KNPC's annual reports (fiscal years 2011-12 to 2025-26, listing static) describe them; the PDFs were not opened |
| Total capacity | **1,415 thousand b/d**, 2023 (Table 3 total) |
| Basis | nameplate; stream-day or calendar-day not stated; a secondary compilation. The brief's text gives 1.2 million b/d as of May 2023 and expected the higher total in the second half of that year, so the table total includes capacity then still being brought into service |
| Throughput | not read. No national throughput series with clear terms was found |
| Vintage | one EIA vintage (2023), now more than three years old |
| Missing | the operator's own capacity statement on a stated basis; a current vintage; national throughput |

**Why unsuitable.** With very few plants, a refining share takes only a handful of values, and each
one says which plant is affected. That is facility status, which this project does not publish for
a system under a recorded campaign and should not approximate through a ratio at any time. The
national capacity total belongs in the profile as context, with its vintage stated.

## 2. Electric generation — **INCOMPLETE**

| Item | Finding |
|---|---|
| Inventory | the ministry's Statistical Year Book would carry one; its page shows covers for 2017–2019 and no file. Not acquired |
| Total capacity | **19.4 GW** installed, 2024 (EIA, series `INTL.2-7-KWT-MK.A`) |
| Basis | EIA's installed capacity; whether industrial captive generation is included is not yet researched |
| Generation | 92.5 billion kWh net, 2024; 97.8% fossil (EIA) |
| Vintage | 2024 |
| Missing | a national, dated plant inventory on one basis from the ministry; any outage or reliability statistic; peak load and available capacity on the ministry's basis |

**Why incomplete and not experimental.** The Qatar verdict rests on a utility-published, licensed,
annual capacity table. Kuwait has only a national total from a secondary source. Even with the
yearbook in hand, three obstacles would remain: no outage reporting exists; the list of plants is
short; and attack events resolve to country level. No model for this country's events has been
approved (`GLOBAL_METHODOLOGY.md` §2 and §8.3).

**A note on load shedding.** Reported summer cuts are a generation-adequacy shortfall, stated in
megawatts shed or areas cut. That is a different quantity from plant capacity forced offline. If
such episodes enter the record they do so as events under the inclusion rule; they are not a
measure of capacity lost and must not be divided by installed capacity.

## 3. Transmission — **UNSUITABLE** (context only)

No national line-length or substation aggregate was read. The Russia-model event-burden measure
does not fit a compact single-ministry grid, and no grid detail is collected: no substation, feeder
or line name, and no interconnection flow. The EIA file gives zero electricity imports and exports
for 2024; that was not cross-checked and is not used.

## 4. Oil logistics — **UNSUITABLE**

No inventory is built. It would centre on export terminals and routing, which are out of scope.
National crude exports would be the context figure, and **none is in the profile**: EIA's series
stops at 2018, and the other sources that publish it (OPEC, OAPEC, JODI, the statistics bureau)
have unread or restrictive terms. The gap is stated, not filled with an estimate.

## 5. Gas

### 5a. Production and processing — **UNSUITABLE** to score

National dry gas production (703 Bcf), consumption (998 Bcf) and imports (332 Bcf) for 2024 are
read from EIA and shown as context. Processing is concentrated in very few places, so a share would
again be facility status. No processing inventory was sought.

### 5b. Gas import — **context dimension; UNSUITABLE to score**

EIA's national import series does not separate LNG from pipeline gas. EIA's brief has a
regasification table (Table 4, 2022); it is in effect a facility table and is not copied. No
terminal capacity is recorded.

### 5c. Gas pipelines and storage — **UNSUITABLE / NOT YET RESEARCHED**

No route is collected. Whether gas storage exists was not researched.

## 6. Coal — **NOT APPLICABLE**

EIA records zero coal production for 2024 and no coal in power generation (brief, Table 1, 2021;
bulk file, 2024). A small coal consumption is recorded (about 0.003 quadrillion Btu in 2024); its use is
not stated, and it is not an energy-infrastructure sector here. This is a sourced zero, not a gap.

## 7. Upstream — a note, not a sector

Crude production including lease condensate was 2,584 thousand b/d in 2025, and petroleum and other
liquids 2,805 thousand b/d (EIA). How production in the Partitioned Zone is attributed in those
series is not stated. Upstream is not one of the six sectors and has no denominator here. An
upstream event enters the record only through the inclusion rule's clauses, and offshore or
shared-field events are country level. A change in an annual or monthly production total with no
stated cause is never an event; OPEC+ decisions are not events.

---

## Russia-model assumptions that fail for Kuwait

- **Many facilities per region.** The theatre's shares are meaningful because a region holds many
  assets. Here a class often has one to three members in the whole country.
- **Region as the unit.** Six governorates are drawn, but energy infrastructure sits in two or
  three of them, and attack records are held at country level.
- **Independent, attacker-side and open-source reporting.** The theatre's record draws on several
  kinds of source. Here statements come from one state corporation, one ministry and one agency.
- **A long event series.** Decay and half-life parameters were set against hundreds of events. No
  comparable series exists for Kuwait.

## Transparency limits, stated once

No Kuwaiti body publishes an outage register, forced-outage rates or reliability indices. The
ministry's news archive is static but thin before late 2024. The oil companies' lists and the state
news agency cannot be read by an ordinary request. Every national figure in the profile comes from
EIA, and one of them is from a 2023 document. None of this is evidence about how the system
performed.
