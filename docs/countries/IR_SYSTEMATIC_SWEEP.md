# Iran — first systematic research pass (iteration 19)

**Part A, the search plan, was written on 2026-11-11 before any search of this pass was run.** The
three searches used by the source audit were about the province count, whether a search engine
indexes SHANA, and national generating capacity; none was a declared query below. Iran has had no
research of any kind in this project. Its reporting environment is `conflict_restricted`
(`IR_SOURCE_AUDIT.md` §3). **This pass is not expected to complete**: most Iranian sites could not
be opened on the day the plan was written, so the lanes run on a search engine's partial index.

**Safety first.** Iran is handled under the active-campaign rule of
`docs/CURRENT_EVENT_PUBLICATION_POLICY.md`. This pass collects that an event occurred, its date and
date precision, the broad infrastructure class, and the effect reported at the time (within 7
days). For kinetic and sabotage events it records the country, not the province, unless the lead
says otherwise. It does **not** collect restart, repair, current operating rate, remaining
capacity or current outage status, in any field, in either language, even where public. It does
not collect coordinates, distances, routes, weapon or attack-method detail, defences, which
facility is said to matter most, dependencies between facilities, tanker or shipping material,
pipeline routes, grid topology, or anything about the nuclear fuel cycle or nuclear sites. A page
whose title or address states later status is not opened and not cited.

| | |
|---|---|
| Window | 2022-01-01 to 2026-11-11 |
| Geography | the 31 provinces; Abu Musa and the Greater and Lesser Tunbs are never a unit (audit §1.2) |
| Rule | `inclusion_threshold.json` version `2026-10-30.1`, unchanged |
| Languages | Persian for IR1 to IR4, English for IR5, both for IR6. A lane run in fewer than its required languages is partial |
| Declared queries | 59 (cap 60) |

## Part A — plan (written before searching)

### A.1 Lanes

`Y` is a year token. In a Persian query it is a Solar Hijri year written in Persian digits, one
query for each of ۱۴۰۰، ۱۴۰۱، ۱۴۰۲، ۱۴۰۳، ۱۴۰۴، ۱۴۰۵ (table A.2). In an English query it is a
Gregorian year, one query for each of 2022, 2023, 2024, 2025, 2026.

| Lane | Universe kind | Languages | Universe | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|---|---|
| IR1 | declared query set | fa | Oil and gas, official: Ministry of Petroleum statements and SHANA items on upstream, gas processing and gas transmission; NIOC and NIGC statements | shana.ir (connection closed on 2026-11-11; indexed by search, article form `shana.ir/news/<id>/...`); mop.ir and nioc.ir (bot check); nigc.ir (certificate error). No listing can be enumerated: search only, restricted to these domains first | for each Persian Y: `شانا آتش‌سوزی انفجار پالایشگاه گاز توقف تولید Y`; `شرکت ملی گاز حادثه خط لوله انتقال قطع گاز Y` (12) | 1, 3, 7 |
| IR2 | declared query set | fa | Refining and processing: NIORDC news and notices; SHANA refining items | niordc.ir `/fa-IR/Portal/5121` (read: page 1 of 71, 20 items; later pages need a script postback and are not enumerable) and `/fa-IR/Portal/5120`; otherwise search | for each Persian Y: `آتش‌سوزی پالایشگاه نفت توقف تولید Y` (6) | 1 |
| IR3 | declared query set | fa | Electricity, official: Ministry of Energy, Tavanir and grid-operator statements. Four kinds kept apart (A.3): chronic shortfall, planned load management, discrete grid events, attack-related outages | moe.gov.ir, paven.ir, tavanir.org.ir, igmc.ir (none resolved on 2026-11-11). No listing can be enumerated: search only | for each Persian Y: `توانیر خاموشی گسترده حادثه شبکه سراسری برق Y`; `جدول خاموشی نوبتی ناترازی برق Y` (12) | 4, 5 |
| IR4 | declared query set | fa | Persian-language media: IRNA, ISNA, Mehr, Tasnim, Fars, and Persian-language outlets outside Iran (Radio Farda, Iran International) for corroboration only | tasnimnews.ir `/fa/service/80/` (read: newest 20 items, then a script "show more") and `/fa/archive`; radiofarda.com `/iran-economy` (read); the other agencies through search (irna.ir, isna.ir: script shell; mehrnews.com: connection closed; farsnews.ir: did not resolve) | for each Persian Y: `نیروگاه از مدار خارج شد قطع برق استان Y` (6); once each: `انفجار معدن زغال‌سنگ توقف تولید`; `ترکیدگی خط لوله انتقال گاز قطع گاز استان` (2) | 1, 3, 4, 5, 6 |
| IR5 | declared query set | en | International corroboration: Reuters, AP, AFP, S&P Global; EIA brief (read in the audit, national context only); OPEC monthly report read only for a production change the report itself attributes to a disruption | via search (reuters.com, apnews.com, afp.com refused by the fetch tool; spglobal.com HTTP 403); iranintl.com/en (read); opec.org (HTTP 402: needs a person, no workaround) | for each Gregorian Y: `Iran refinery gas plant fire explosion production halted Y`; `Iran nationwide power outage rolling blackouts Y` (10) | 1-7 |
| IR6 | declared query set | fa+en | Kinetic and sabotage events, **occurrence only**: that it occurred, date, class, effect reported at the time. Never restart, repair or current status. Country precision | via search; every candidate needs a source published within 7 days of the event whose title and address carry no status wording | for each Gregorian Y: `Iran energy facility attack sabotage Y` (5); for each Persian Y: `حمله خرابکاری تأسیسات نفت گاز برق ایران Y` (6) | 1, 2, 3, 4, 5, 7 |

Query count: IR1 12, IR2 6, IR3 12, IR4 8, IR5 10, IR6 11. **Total 59.**

The Persian strings use the words Iranian outlets themselves use, because that is what a search
engine matches. They are retrieval strings and not this project's description of any event.

### A.2 Solar Hijri years

| Persian Y | Gregorian span | Note |
|---|---|---|
| ۱۴۰۰ (1400) | 2021-03-21 to 2022-03-20 | only 2022-01-01 to 2022-03-20 is inside the window; discard anything earlier |
| ۱۴۰۱ (1401) | 2022-03-21 to 2023-03-20 | |
| ۱۴۰۲ (1402) | 2023-03-21 to 2024-03-19 | |
| ۱۴۰۳ (1403) | 2024-03-20 to 2025-03-20 | leap year |
| ۱۴۰۴ (1404) | 2025-03-21 to 2026-03-20 | |
| ۱۴۰۵ (1405) | 2026-03-21 to 2027-03-20 | the window ends on 2026-11-11, which is 20 Aban 1405 |

A year such as 1404 is never read as Gregorian. Every record from a Persian source keeps
`source_date_text` as written, `date_calendar: "solar_hijri"`, and a Gregorian `normalized_date`
converted day by day, not by adding 621. Tasnim's Persian article addresses carry the Solar Hijri
date in the path; its English addresses carry the Gregorian date. Sites write the year in Persian
digits (SHANA, NIORDC) or Latin digits (Tasnim). If a Persian-digit query returns nothing, that is
logged; the Latin-digit form is a different query and is not run under this plan.

### A.3 Electricity: four things kept apart (IR3, and any electricity item from IR4 or IR5)

| Kind | What it is | Disposition |
|---|---|---|
| Chronic shortfall (ناترازی) | A standing gap between supply and demand, stated by officials as a figure or a forecast | **Not an event.** Context only. Never a candidate |
| Planned load management | Scheduled rotating outages, published outage tables, ordered closures of offices or industry, announced in advance | A candidate only under the second half of clause 4 (a generation shortfall that forced rotating outages), **held** by default, at most one candidate per season, country precision. How a season of scheduled outages is represented is a decision for the lead (below) |
| Discrete grid event | A dated failure: a plant or part of the grid forced offline, a province-wide or multi-province blackout | A candidate under clause 4 or 5 if the source gives the effect. Province only as the source names it. Cause as the source states it, otherwise `unknown` |
| Attack-related outage | An outage a source attributes to an attack or to sabotage | Moves to IR6 and its rules: occurrence only, country precision, no status |

A forecast, a warning or a planned-outage table is not evidence that an outage happened.

### A.4 Safety

- Occurrence and the effect reported at the time only. Citations published more than 7 days after
  a kinetic or sabotage event, and addresses or titles that announce status, are not recorded.
- Persian status wording is a stop signal in a title or address: `راه‌اندازی مجدد`، `ازسرگیری`،
  `از سر گرفته شد`، `بازگشت به مدار`، `به مدار بازگشت`، `تعمیر`، `ترمیم`، `بازسازی`، `بازیابی`،
  `همچنان متوقف`، `در مدار قرار گرفت`. The build's status check has no Persian patterns yet, so
  until it does this list is applied by the researcher and the reviewer by hand.
- `facility_name` on a kinetic or sabotage record only when the facility's own name is what the
  source reports as hit. No unit, component, tank or line detail.
- NIORDC's listing includes items on post-attack infrastructure condition. They are not opened.
- Wikipedia's war articles are not mined. Tanker, shipping and export-route material is not read.

### A.5 Evidence

- Five domestic agencies repeating one ministry statement are one source. A translation by the
  same agency is not a second source. A wire story carried by many outlets is one source.
- A claim by a party to the conflict is recorded as a claim, with who made it.
- A record resting only on an outlet outside Iran (Iran International, Radio Farda) is held until
  an independent source is found.
- A source found by search and not opened is `opened: false`. On 2026-11-11 that will be most
  Iranian sources.
- A production or export decline with no stated cause is not an event. Sanctions, quotas, price
  moves and planned maintenance are not events.

### A.6 Budget, resilience, review

Lane order IR6, IR1, IR2, IR3, IR4, IR5, so that the lane with the strictest handling is done by
one researcher with a fresh allowance. The output file is written after each lane. A query refused
by the shared search limit is logged as not run, never substituted. Blind three-role review before
import (`REVIEW_GOVERNANCE.md`); every Iranian record is read end to end by the safety reviewer.

### A.7 For the lead to decide before Wave B

1. Province codes: **decided before Wave B.** The system uses the current ISO 3166-2 codes
   (`IR-00` to `IR-30`, audit §1.1, right-hand column), not the numbering Natural Earth carries.
   Every candidate carries `admin1_name` beside `admin1_code`.
2. Whether a season of scheduled rotating outages is one held candidate, an episode, or context
   only (A.3).
3. Whether `conflict_restricted` stands for the whole window (audit §3).
4. Persian patterns for the status check before any import (A.4).

## Part B — execution (written after the pass, 2026-11-11)

**This pass did not finish.** 0 of 6 lanes ran as far as declared; 6 were stopped by the shared limit of 200 web searches per turn, which was not worked around. Each lane states below what did not run. A blocked source (HTTP 402 or 403, login wall, script-only page) was recorded as blocked and left.

| Lane | Execution | Source window | Covered through | Queries | Items read | Languages required | Languages run |
|---|---|---|---|---|---|---|---|
| IR1 | partial; stopped by search limit | inaccessible | not reached | 5 of 12 | - | fa | fa |
| IR2 | partial; stopped by search limit | no_census_exists | not reached | 3 of 6 | 29 | fa | fa |
| IR3 | partial; stopped by search limit | inaccessible | not reached | 6 of 12 | - | fa | fa |
| IR4 | partial; stopped by search limit | no_census_exists | not reached | 2 of 8 | 49 | fa | fa |
| IR5 | partial; stopped by search limit | no_census_exists | 2025-07-05 | 5 of 10 | - | en | en |
| IR6 | partial; stopped by search limit | no_census_exists | 2026-07-14 | 5 of 11 | - | en, fa | en, fa |

Candidates 35: accepted after blind review 0, rejected 11, duplicate 0, held 23, out of scope 1. Published records in this system after the pass: 0.

**Result.** No record is published. Two reached review. A 2024 sabotage record is with the owner: no opened source says the line was shut, which is what clause 3 asks. A 2025 attack record is held: the evidence reviewer rests it on a figure for one plant, which the safety reviewer removes as identifying, and the two could not be reconciled. Most Persian-language official archives were unreachable or script-only. Seasonal load shedding is held for the owner question on scheduled outages. No nuclear site appears in any record or citation.

**Review.** Every published record was reviewed blind by three independent roles (evidence, safety, taxonomy), reconciled, and confirmed by all three on the text the import gate publishes. A hold from any role held the record.

### Limitations, per lane

- **IR1**: Five of twelve declared queries ran, and the search engine did not honour the year token: every string returned the same few 2023-2026 events whatever year was asked. No official site could be opened, so nothing official was read. No winter gas shortfall was returned by any query run; that is a gap in this pass, not a finding that none was reported.
- **IR2**: Three of six declared queries ran. Every media page with a refinery fire refused access, so no refinery record could be verified and none is proposed for acceptance.
- **IR3**: No official electricity site could be opened, so nothing was enumerated and no official statement was read on its own page: every Tavanir or ministry statement here is as relayed by Radio Farda or Iran International. Six of twelve declared queries ran; four of those six were restricted to the three hosts that can be opened, which is narrower than the declared query, and the search engine did not separate results by Solar Hijri year (the 1401 and 1402 runs returned mostly 1403 to 1405 items). 2022, 2023 and the first half of 2024 are in effect not searched.
- **IR4**: The listings that can be read show only the newest days, so the archive for 2022 to 2025 was not enumerated. Two of eight declared queries ran, both restricted to the three hosts that can be opened; the coal-mine and gas-pipeline queries and the 1400, 1401, 1402 and 1405 years did not run. Domestic agencies other than Tasnim were not retried after the audit's refusals.
- **IR5**: Half the declared queries ran. The wire services cannot be opened directly, so their stories were read where another outlet carried them. Iran International's English home page was read as the only listing available and holds only the newest items;
- **IR6**: Five of eleven declared queries ran. Iranian agency pages could not be opened, so every Iranian account is read through a wire or a foreign outlet.
