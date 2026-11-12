# Iraq — first systematic research pass (iteration 19)

**Part A, the search plan, was written on 2026-11-11 before any search of this pass was run.**
It was written by the source-audit lane from `IQ_SOURCE_AUDIT.md`, which tested every endpoint
named below with one ordinary request and ran no incident search.

**Safety first.** This pass records publicly reported, historical disruption, aggregated to
governorate at most. Kinetic and sabotage events are reported in Iraq inside the window, and
whether a campaign is recorded as active for this system is decided in
`data/curated/systems/conflict_campaigns.json`, not here. **Until that is decided, every kinetic or
sabotage candidate is handled under the strict rule:** occurrence, date and date precision, broad
infrastructure class, country and (if safe) governorate, and the effect reported within 7 days.
The pass does **not** collect restart, current operating rate, repair progress, remaining capacity,
current outage or current facility condition, even where public, in any field. It does not collect
coordinates, distances, attack method, defences, or which facility is the largest of its kind.
**Nothing about export routes, alternative-route capacity, port or terminal dependence, vessel
movements, pipeline routes, grid topology or the status of a named line or interconnector is read
or written down.** National export totals are context only.

| | |
|---|---|
| Window | 2022-01-01 to 2026-11-11 |
| Geography | the 18 governorates Natural Earth draws; Halabja is placed in As-Sulaymaniyah and the record says so; disputed internal territories are placed by the governorate Natural Earth draws and are not otherwise resolved |
| Rule | `inclusion_threshold.json` version `2026-10-30.1`, unchanged |
| Languages | Arabic and English mandatory for IQ2, IQ3 and IQ5; Arabic for IQ1; Kurdish (Sorani) and English for IQ4 |
| Declared queries | 50 in total (IQ1 2, IQ2 10, IQ3 15, IQ4 13, IQ5 10) |

## Part A — plan (written before searching)

### A.1 Lanes

`Y` stands for each year 2022, 2023, 2024, 2025 and 2026 in turn.

| Lane | Universe kind | Languages | Universe | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|---|---|
| IQ1 | report archive | ar (+en) | SOMO monthly export and product statistics, read **only** for an official attribution of a material change to a disruption. A change with no stated cause yields context, never an incident. Breakdowns below the national total are not read | somooil.gov.iq: `/ar/researches`, `/ar/reports`, `/ar/exports/chart`, `/ar/news` (ids to 127). Reachable, but report listings and article bodies were not rendered to an ordinary request; the chart page shows a national monthly total | 2 fallback queries, run only if enumeration fails: `شركة تسويق النفط سومو إيضاح سبب انخفاض الصادرات النفطية`; `SOMO statement Iraq crude exports fell because` | 2, 7 |
| IQ2 | declared query set | ar+en | Ministry of Oil releases and state oil company statements, as carried by agencies. The ministry's own site is behind a security check, so this is a query set, not an archive | oil.gov.iq, boc.oil.gov.iq, mrc.oil.gov.iq, nrc.oil.gov.iq, nocoil.gov.iq (all: security-check page, not read); ina.iq (HTTP 403, not read); **src.gov.iq `news.aspx` and `news-detail.aspx?id=N` (reachable, dated; enumerate first)** | for each Y: `وزارة النفط العراقية بيان توقف الإنتاج حريق Y`; `Iraq oil ministry statement production halted fire Y` | 1, 2, 3, 7 |
| IQ3 | declared query set | ar+en | Electricity: Ministry of Electricity statements on dated losses of supply, classified under A.3 into fuel shortage, grid failure, technical outage, load-shedding policy and kinetic disruption, which are never merged | moelc.gov.iq (security-check page, not read); ina.iq (HTTP 403, not read); via search, then the article pages | for each Y: `وزارة الكهرباء العراقية انطفاء تام المنظومة الوطنية Y`; `وزارة الكهرباء العراقية فقدان ميغاواط توقف إمدادات الغاز Y`; `Iraq electricity ministry nationwide blackout grid megawatts lost gas supply Y` | 4, 5 |
| IQ4 | declared query set | ku+en (+ar) | Kurdistan Region official sources: the regional Ministry of Natural Resources and Ministry of Electricity, and APIKUR (industry association) statements on member production, as carried by media. Statements on commercial terms and export arrangements are not read | gov.krd, moel.gov.krd (HTTP 403, not read); APIKUR's own site (not reached); rudaw.net/sorani, kurdistan24.net/ckb, shafaq.com/ku (reachable) | for each Y: `وەزارەتی کارەبای هەرێمی کوردستان کەمبوونەوەی بەرهەمهێنانی کارەبا Y`; `Kurdistan Region electricity ministry power generation megawatts lost gas supply halted Y`. Once each: `وەزارەتی سامانە سروشتییەکان ڕاگەیەندراو وەستانی بەرهەمهێنان`; `وزارة الثروات الطبيعية إقليم كوردستان بيان توقف الإنتاج`; `APIKUR statement member companies production suspended` | 1, 4, 5, 7 |
| IQ5 | declared query set | ar+en | Media corroboration: Shafaq News, Rudaw, Kurdistan24, Reuters, AP, S&P Global. A translation or syndicated copy is not a second source | shafaq.com `/en/Economy?page=N` and `/ar/اقتصـاد?page=N` (paged, dated); kurdistan24.net `/en/list/category/36/Economy?page=N` (paged, undated); rudaw.net (articles readable, listings not rendered); reuters.com and apnews.com (refused by the fetch tool); spglobal.com (HTTP 403); iraqoilreport.com (paywall, headlines only) | for each Y: `حريق مصفى أو حقل نفطي في العراق توقف الإنتاج Y`; `Iraq refinery oilfield fire attack production halted Y` | 1-7 |

### A.2 Safety

Event occurrence and the effect reported at the time only. No restart, recovery, operating-rate,
repair or dependency content is recorded for a kinetic or sabotage candidate, even in the local
queue's published fields; `recovery` stays `NOT_YET_RESEARCHED`, `date_end` null, and
`geography_precision` is `country` unless the lead says governorate is safe. A citation published
more than 7 days after such an event, or whose address or title states facility status, stays in
the local queue. `facility_name` is filled only when the facility's own name is what the source
reports as affected.

A cut in imported gas or electricity is recorded as a national supply effect. The line,
interconnector or route it arrived by is not written down. SOMO's and EIA's breakdowns below the
national total are not opened for this pass.

### A.3 Electricity classification (IQ3 and IQ4)

Every electricity candidate carries exactly one class at the start of `threshold_basis`:

| Class tag | Meaning | Disposition rule |
|---|---|---|
| `[fuel_shortage]` | generation lost because gas or fuel supply fell | candidate if the source gives a date, a cause and a size (megawatts or governorates); `cause` is `unknown` unless the source states why supply fell |
| `[grid_failure]` | system-wide or multi-governorate collapse of the network | candidate under clause 5 if an operator emergency or a stated scale is reported; `asset_class` `system_wide` |
| `[technical_outage]` | plant or unit fault, fire or trip | candidate under clause 4 only with a stated size of about 500 MW or more and a stated effect |
| `[load_shedding_policy]` | scheduled supply hours, seasonal rationing | **always `out_of_scope`**: background, not an event |
| `[kinetic]` | attack or sabotage | A.2 applies in full |

Megawatts are never converted to customers. A candidate that states neither a customer count, an
emergency declaration nor a megawatt figure is **held**. A statement that mixes two classes (for
example a fuel cut followed by a network collapse) becomes two candidates only if the source dates
both; otherwise one, with the class the source gives as the cause.

### A.4 Dates and languages

Official Iraqi statements are dated in the Gregorian calendar, with Arabic month names in the
Levantine form (كانون الثاني, شباط, آذار …) or the Egyptian form (يناير, فبراير …). A Hijri date
shown alongside is kept in `source_date_text` with `date_calendar` `hijri`; a year such as 1447 is
never read as Gregorian. Kurdish text keeps its original title in Sorani script with language code
`ku` and an English gloss in a separate field.

### A.5 Budget, resilience, review

At most 50 searches for this country, as declared above; enumeration by direct request comes first
and costs none. Each lane writes its log after every source family. Refused access (402, 403,
security-check pages, login walls, script-only listings) is recorded and never worked around.
Every lane-accepted record goes through blind three-role review (`REVIEW_GOVERNANCE.md` §7) and
confirmation before import.

## Part B — execution (written after the pass, 2026-11-11)

**This pass did not finish.** 0 of 5 lanes ran as far as declared; 5 were stopped by the shared limit of 200 web searches per turn, which was not worked around. Each lane states below what did not run. A blocked source (HTTP 402 or 403, login wall, script-only page) was recorded as blocked and left.

| Lane | Execution | Source window | Covered through | Queries | Items read | Languages required | Languages run |
|---|---|---|---|---|---|---|---|
| IQ1 | partial; stopped by search limit | inaccessible | not reached | 1 of 2 | 7 | ar | ar |
| IQ2 | partial; stopped by search limit | no_census_exists | not reached | 6 of 10 | 21 | ar, en | ar |
| IQ3 | partial; stopped by search limit | inaccessible | not reached | 7 of 15 | - | ar, en | ar |
| IQ4 | partial; stopped by search limit | no_census_exists | 2026-11-11 | 5 of 13 | - | en, ku | en, ku |
| IQ5 | partial; stopped by search limit | no_census_exists | 2026-11-11 | 5 of 10 | - | ar, en | ar, en |

Candidates 69: accepted after blind review 10, rejected 15, duplicate 1, held 38, out of scope 5. Published records in this system after the pass: 10.

**Result.** Published: two national-grid collapses and four fuel-supply shortfalls with a ministry-stated size, three production shut-ins at a stated volume, and one attack record at country level. Held: three attack records whose every citation names the place in its address; a fourth referred to the owner with them, because the safety reviewer judged that the set reads as a tally on one site and that the megawatt effect is itself an identifier; non-attack records at or about a site that has attack records (owner); a blackout whose reported cause may include sabotage (owner); two shortfalls whose stated reason is a supplier's maintenance (owner); one attack record with a named shutdown and no volume. The Kurdish-language and media lanes ran about half their declared queries.

**Review.** Every published record was reviewed blind by three independent roles (evidence, safety, taxonomy), reconciled, and confirmed by all three on the text the import gate publishes. A hold from any role held the record.

### Limitations, per lane

- **IQ1**: The monthly report archive and every news body are script-rendered, so no report was read and the archive was not enumerated. One of two fallback queries ran; the English one was left unrun to keep the cap for IQ2.
- **IQ2**: Six of ten declared queries ran: Arabic for all five years, English for 2022 only, so English is partial. Official sites stayed unread, so every record is a media copy of a statement or of unnamed officials. One Arabic business outlet that recurred in the results refused every request.
- **IQ3**: Seven of fifteen declared queries ran and none in English, so this lane is partial and its silence proves nothing. The gas-loss string did not run for 2022, 2024 or 2026; the 2022 and 2024 blackout searches returned no dated collapse, which is a search result, not a finding that none occurred. Station fires and unit faults with a stated loss were not found by these strings and remain not yet researched. Official pages could not be read, so every record rests on media copies of ministry statements, and six of the ten accepted records have one opened source.
- **IQ4**: Official regional sites refuse automated reading, so every statement was read as carried by media, mostly in English; Sorani text was read for four items. Five of 13 declared queries ran (2022, 2023 and the Sorani string for 2024) before the cap; the 2025 and 2026 strings and the three once-only strings did not run, so 2025-2026 rests on one outlet's tag listings, which are an editor's selection, not an archive. A tag or a year with no item is not evidence of no event.
- **IQ5**: Shafaq's section listings run to more than a thousand pages each and were read only at page 1; discovery was through tag listings, which are incomplete, and the Arabic listing was not paged. Kurdistan24's Economy listing exposes 5 undated pages (about 80 recent items). Five of 10 declared queries ran (2022, 2023 and the Arabic string for 2024). Reuters and AP were read only in syndicated copies. Federal-Iraq events were recorded only where met in passing; lanes IQ2 and IQ3 own them.
