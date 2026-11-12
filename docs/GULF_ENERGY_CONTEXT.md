# Gulf energy context

What the Gulf overview (`?group=gulf`, `global/gulf.json`) shows, where each figure comes from,
and what was deliberately left out. Written in iteration 19.

**A regional energy picture, not a target set.** Every figure on the overview is a country's
annual national total. Nothing on it describes a facility, a route, a strait, a ship, or how much
any country depends on anything.

## The eight systems and three different groupings

| | Gulf littoral | GCC | OPEC (today) |
|---|---|---|---|
| Bahrain | yes | member | not a member |
| Iran | yes | not a member | member |
| Iraq | yes | not a member | member |
| Kuwait | yes | member | member |
| Oman | yes | member | not a member |
| Qatar | yes | member | not a member |
| Saudi Arabia | yes | member | member |
| United Arab Emirates | yes | member | not a member since 2026-05-01 |

These are three facts, kept in three fields (`pipeline/systems.py`, `GROUPS`). "Gulf" is geography.
"GCC" is never used as shorthand for the eight: Iran and Iraq are not members.

**OPEC membership is today's.** The UAE government announced on 2026-04-28 that it would leave OPEC
and OPEC+ with effect from 2026-05-01 (reported by the Associated Press and Khaleej Times). In
iteration 19 OPEC's own member page returned HTTP 402. In iteration 20 one ordinary visit read it:
it still lists the UAE among twelve members and mentions no withdrawal, while OPEC's own
1 November 2026 release on market stability names the other seven countries of the earlier
voluntary-cut group and not the UAE. The list follows the member's announcement, and the overview
says that the organisation's page disagrees. The annual figures shown are for 2024, a year in which the UAE was a member. The brief
for this iteration listed the UAE as a member; the published membership follows the world.

## What is shown

Four columns, all from one source and one year (the same national context layer the world map
uses, `docs/GLOBAL_ENERGY_CONTEXT.md`):

| Metric | Source | Year |
|---|---|---|
| Total primary energy production | U.S. EIA International Energy Statistics, bulk file | the context layer's comparison year |
| Crude oil production (including lease condensate) | same | same |
| Dry natural gas production | same | same |
| Net electricity generation | same | same |

Below the table: the sum for the eight and its share of the world total, **only where all eight
report a value**. A sum over seven would look like the region's figure and be smaller than it, so
it is refused with the reason (`_region` in `pipeline/gulf_context.py`).

The map colours the eight countries by the chosen metric in five classes of magnitude within the
group. Colour is a national energy figure; the legend says a larger figure is not a more important
country. Countries are listed alphabetically everywhere, never by any figure.

Each country card also carries, as process facts and never as counts of disruption: whether its
research is a preview, whether recovery status is being withheld under the campaign rule (a flag,
never a number of records), its reporting environment, its latest research pass, lane states, and
which languages its plan required against which were run.

## What was looked for and not adopted

The regional source assessment of 2026-11-11 looked for refining capacity, LNG exports and crude
exports on a common basis for all eight. None is published here.

| Metric | Why it is absent |
|---|---|
| Refining capacity | No source with readable terms that allow reuse. The EIA bulk file has no refining-capacity series. OPEC (HTTP 402) and the Energy Institute (HTTP 403) refused access, so their terms are unread. OAPEC prints "All rights reserved" and covers six of the eight. |
| LNG exports | The EIA bulk file has no LNG series; its gas export series adds pipeline and LNG together, and showing that under an LNG label would present one thing as another. GECF's terms page is placeholder text. |
| Crude exports | The EIA series exists for all eight but ends in 2018. A 2018 figure beside a 2024 layer would be read as current. Omitted. |

| Source | Verdict | Reason |
|---|---|---|
| U.S. EIA International Energy Statistics | adopted | U.S. government work, public domain; one file, all eight |
| OPEC Annual Statistical Bulletin | blocked | HTTP 402 on every host tried; terms unread |
| JODI Oil and Gas | validation only | data free to download, site terms reserve all rights; redistribution not granted |
| Energy Institute Statistical Review | blocked | HTTP 403; terms unread |
| GECF Annual Statistical Bulletin | not adopted | terms page is placeholder text; PDF not readable by ordinary access |
| IRENA statistics portal | blocked | HTTP 403 on the portal (a country profile PDF was readable and is cited in Bahrain's own profile) |
| GCC-Stat | not adopted for the common table | terms allow reuse with attribution, but it covers six of the eight and its energy report draws on OPEC, OAPEC, GECF and IRENA, whose terms travel with their figures |
| GCC Interconnection Authority | not adopted | terms forbid reproduction without written consent; nothing line-level, constraint or topology was read |
| OAPEC (to become the Arab Energy Organization) | validation only | "All rights reserved"; six of the eight |

A blocked source was not worked around. A metric with no committable common source is left out,
not estimated, and not filled from a second source for some countries: two sources never share a
column.

Each country's own page carries a profile from that country's audited sources (for example
Qatar's and Bahrain's open-data portals, Oman's statistical bulletin). Those rows have different
sources, years and bases, are labelled row by row, and are never placed side by side across
countries.

## What this view will never hold

Enforced by `FORBIDDEN_KEY_PARTS` in `pipeline/gulf_context.py` and by `tests/test_iteration19.py`:

- a facility, a facility count, or a share attributed to a facility;
- a route, a strait, a pipeline corridor, a port or terminal dependence, an alternative or bypass
  route or its capacity;
- tanker, vessel or shipping information of any kind;
- a ranking, score, importance, criticality, vulnerability or severity field;
- a count of incidents or of withheld records per country;
- any field that combines two metrics into a derived indicator;
- current or post-attack operating status of anything.

No analytic module imports `pipeline/gulf_context.py`. Context never enters a number.

## Update path

The four columns move when the national context layer is refreshed
(`scripts/build_global_context.py`, a manual step that reads EIA's bulk file). The daily refresh
does not touch them and does not research anything. Membership is curated in `pipeline/systems.py`
with an `as_of` date; re-check it when a country is researched.
