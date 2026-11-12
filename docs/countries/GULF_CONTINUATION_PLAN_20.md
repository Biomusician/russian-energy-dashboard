# Gulf continuation plan (iteration 20)

Committed before any iteration-20 search. It continues the iteration-19 pass; it does not
replace it. The iteration-19 pass stays in each research log as it was written.

## Rules of the continuation

- **No new declared query.** Every query below was declared in Part A of the iteration-19 plan
  (`docs/countries/<CC>_SYSTEMATIC_SWEEP.md`, `SA_LANE_PASS_19.md`) and was not run. A query a
  researcher needs that is not declared is logged as `queries_added` with its reason, and a lane
  is never called complete on the strength of an added query.
- **Order of work in each lane:** enumerate reachable archives and listings by direct fetch;
  run the declared queries that are not about attacks, required language first; then the
  declared queries about attack occurrence, only within the attack allowance below; then
  evidence for held non-conflict candidates (local list). Historical non-conflict events
  (2022-2025) come before recent conflict reporting.
- **Search allowance.** One limit of 200 web searches is shared by the whole iteration. Each
  researcher has the cap below. Direct fetches of an archive do not count against it.
- **Blocked is blocked.** A source that refused access in iteration 19 is tried once more by an
  ordinary fetch; if it refuses again it is recorded and left. No workaround.
- **Campaign rules are unchanged.** Attack records: occurrence, date, broad class, country, the
  effect reported at the time. Nothing about later status is collected.

## Allowances

| System | Declared queries not run (non-attack / attack) | Cap (non-attack + attack) |
|---|---|---|
| Bahrain | 13 / 2 | 13 + 1 |
| Iran | 27 / 6 | 27 + 4 |
| Iraq | 23 / 3 | 23 + 3 |
| Kuwait | 9 / 6 | 9 + 2 |
| Oman | 20 / 0 | 20 + 0 |
| Qatar | 11 / 7 | 11 + 3 |
| Saudi Arabia | 8 / 12 | 8 + 6 |
| United Arab Emirates | 21 / 3 | 21 + 2 |

Iteration-19 state, per lane, and what this pass is to do. Alphabetical by system.

## Bahrain (plan: `docs/countries/BH_SYSTEMATIC_SWEEP.md`)

### BH1: Hydrocarbons: Bapco Energies group press releases and ministry statements carried by the state news agency

- Iteration 19: partial, source window `inaccessible`, stopped by the search allowance; queries 0 of 5; items listed or read 8; languages run English of Arabic, English; 4 endpoints refused or unreadable.
- This pass: run the lane in Arabic; run the 5 declared queries listed below; enumerate the archive further where it is reachable; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `بابكو مصفاة حريق توقف وحدة بيان`
  - `بابكو للغاز بناغاز حادث توقف الإنتاج`
  - `البحرين استهداف منشأة نفطية بيان رسمي` (attack occurrence: attack allowance only)
  - `Bapco Refining fire unit shutdown statement`
  - `Bahrain oil gas facility attack official statement` (attack occurrence: attack allowance only)

### BH2: Electricity: Electricity and Water Authority statements

- Iteration 19: partial, source window `rolling_archive_gap`, stopped by the search allowance; queries 0 of 4; items listed or read 148; languages run Arabic, English of Arabic, English; 0 endpoints refused or unreadable.
- This pass: run the 4 declared queries listed below; enumerate the archive further where it is reachable.
- Declared, not run in iteration 19:
  - `هيئة الكهرباء والماء انقطاع التيار الكهربائي بيان`
  - `هيئة الكهرباء والماء خلل فني محطة إنتاج الكهرباء انقطاع`
  - `EWA Bahrain power outage statement`
  - `Bahrain blackout Electricity and Water Authority generation fault`

### BH3: Arabic and English media by year, via search

- Iteration 19: partial, source window `no_census_exists`, stopped by the search allowance; queries 9 of 15; languages run Arabic of Arabic, English; 2 endpoints refused or unreadable.
- This pass: run the lane in English; run the 6 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `البحرين انقطاع الكهرباء 2026`
  - `Bahrain refinery gas plant power outage incident 2022`
  - `Bahrain refinery gas plant power outage incident 2023`
  - `Bahrain refinery gas plant power outage incident 2024`
  - `Bahrain refinery gas plant power outage incident 2025`
  - `Bahrain refinery gas plant power outage incident 2026`

## Iran (plan: `docs/countries/IR_SYSTEMATIC_SWEEP.md`)

### IR1: Oil and gas, official: Ministry of Petroleum statements and its news service, via search

- Iteration 19: partial, source window `inaccessible`, stopped by the search allowance; queries 5 of 12; languages run Persian of Persian; 13 endpoints refused or unreadable.
- This pass: run the 7 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `شانا آتش‌سوزی انفجار پالایشگاه گاز توقف تولید ۱۴۰۰`
  - `شانا آتش‌سوزی انفجار پالایشگاه گاز توقف تولید ۱۴۰۴`
  - `شانا آتش‌سوزی انفجار پالایشگاه گاز توقف تولید ۱۴۰۵`
  - `شرکت ملی گاز حادثه خط لوله انتقال قطع گاز ۱۴۰۰`
  - `شرکت ملی گاز حادثه خط لوله انتقال قطع گاز ۱۴۰۳`
  - `شرکت ملی گاز حادثه خط لوله انتقال قطع گاز ۱۴۰۴`
  - `شرکت ملی گاز حادثه خط لوله انتقال قطع گاز ۱۴۰۵`

### IR2: Refining and processing: the national refining company's news and notices

- Iteration 19: partial, source window `no_census_exists`, stopped by the search allowance; queries 3 of 6; items listed or read 29; languages run Persian of Persian; 6 endpoints refused or unreadable.
- This pass: run the 3 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `آتش‌سوزی پالایشگاه نفت توقف تولید ۱۴۰۰`
  - `آتش‌سوزی پالایشگاه نفت توقف تولید ۱۴۰۴`
  - `آتش‌سوزی پالایشگاه نفت توقف تولید ۱۴۰۵`

### IR3: Electricity, official: Ministry of Energy and grid-operator statements, via search

- Iteration 19: partial, source window `inaccessible`, stopped by the search allowance; queries 6 of 12; languages run Persian of Persian; 4 endpoints refused or unreadable.
- This pass: run the 6 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `توانیر خاموشی گسترده حادثه شبکه سراسری برق ۱۴۰۰`
  - `توانیر خاموشی گسترده حادثه شبکه سراسری برق ۱۴۰۵`
  - `جدول خاموشی نوبتی ناترازی برق ۱۴۰۰`
  - `جدول خاموشی نوبتی ناترازی برق ۱۴۰۱`
  - `جدول خاموشی نوبتی ناترازی برق ۱۴۰۲`
  - `جدول خاموشی نوبتی ناترازی برق ۱۴۰۵`

### IR4: Persian-language media, inside and outside Iran

- Iteration 19: partial, source window `no_census_exists`, stopped by the search allowance; queries 2 of 8; items listed or read 49; languages run Persian of Persian; 2 endpoints refused or unreadable.
- This pass: run the 6 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `نیروگاه از مدار خارج شد قطع برق استان ۱۴۰۰`
  - `نیروگاه از مدار خارج شد قطع برق استان ۱۴۰۱`
  - `نیروگاه از مدار خارج شد قطع برق استان ۱۴۰۲`
  - `نیروگاه از مدار خارج شد قطع برق استان ۱۴۰۵`
  - `انفجار معدن زغال‌سنگ توقف تولید`
  - `ترکیدگی خط لوله انتقال گاز قطع گاز استان`

### IR5: International corroboration, via search

- Iteration 19: partial, source window `no_census_exists`, stopped by the search allowance; queries 5 of 10; languages run English of English; 4 endpoints refused or unreadable.
- This pass: run the 5 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `Iran refinery gas plant fire explosion production halted 2025`
  - `Iran refinery gas plant fire explosion production halted 2026`
  - `Iran nationwide power outage rolling blackouts 2022`
  - `Iran nationwide power outage rolling blackouts 2023`
  - `Iran nationwide power outage rolling blackouts 2026`

### IR6: Attack and sabotage events: occurrence, date, class and effect at the time only

- Iteration 19: partial, source window `no_census_exists`, stopped by the search allowance; queries 5 of 11; languages run English, Persian of English, Persian; 8 endpoints refused or unreadable.
- This pass: run the 6 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `حمله خرابکاری تأسیسات نفت گاز برق ایران ۱۴۰۰` (attack occurrence: attack allowance only)
  - `حمله خرابکاری تأسیسات نفت گاز برق ایران ۱۴۰۱` (attack occurrence: attack allowance only)
  - `حمله خرابکاری تأسیسات نفت گاز برق ایران ۱۴۰۳` (attack occurrence: attack allowance only)
  - `Iran energy facility attack sabotage 2022` (attack occurrence: attack allowance only)
  - `Iran energy facility attack sabotage 2023` (attack occurrence: attack allowance only)
  - `Iran energy facility attack sabotage 2024` (attack occurrence: attack allowance only)

## Iraq (plan: `docs/countries/IQ_SYSTEMATIC_SWEEP.md`)

### IQ1: SOMO monthly statistics, read only for a change the publisher attributes to a disruption

- Iteration 19: partial, source window `inaccessible`, stopped by the search allowance; queries 1 of 2; items listed or read 7; languages run Arabic of Arabic; 3 endpoints refused or unreadable.
- This pass: run the 1 declared queries listed below; enumerate the archive further where it is reachable; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `SOMO statement Iraq crude exports fell because`

### IQ2: Ministry of Oil and state oil company statements, as carried by agencies

- Iteration 19: partial, source window `no_census_exists`, stopped by the search allowance; queries 6 of 10; items listed or read 21; languages run Arabic of Arabic, English; 7 endpoints refused or unreadable.
- This pass: run the lane in English; run the 4 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `Iraq oil ministry statement production halted fire 2023`
  - `Iraq oil ministry statement production halted fire 2024`
  - `Iraq oil ministry statement production halted fire 2025`
  - `Iraq oil ministry statement production halted fire 2026`

### IQ3: Ministry of Electricity statements on dated losses of supply

- Iteration 19: partial, source window `inaccessible`, stopped by the search allowance; queries 7 of 15; languages run Arabic of Arabic, English; 5 endpoints refused or unreadable.
- This pass: run the lane in English; run the 8 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `وزارة الكهرباء العراقية فقدان ميغاواط توقف إمدادات الغاز 2022`
  - `وزارة الكهرباء العراقية فقدان ميغاواط توقف إمدادات الغاز 2024`
  - `وزارة الكهرباء العراقية فقدان ميغاواط توقف إمدادات الغاز 2026`
  - `Iraq electricity ministry nationwide blackout grid megawatts lost gas supply 2022`
  - `Iraq electricity ministry nationwide blackout grid megawatts lost gas supply 2023`
  - `Iraq electricity ministry nationwide blackout grid megawatts lost gas supply 2024`
  - `Iraq electricity ministry nationwide blackout grid megawatts lost gas supply 2025`
  - `Iraq electricity ministry nationwide blackout grid megawatts lost gas supply 2026`

### IQ4: Kurdistan Region official sources and industry-association statements, as carried by media

- Iteration 19: partial, source window `no_census_exists`, stopped by the search allowance; queries 5 of 13; languages run English, Kurdish (Sorani) of English, Kurdish (Sorani); 3 endpoints refused or unreadable.
- This pass: run the 8 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `Kurdistan Region electricity ministry power generation megawatts lost gas supply halted 2024`
  - `وەزارەتی کارەبای هەرێمی کوردستان کەمبوونەوەی بەرهەمهێنانی کارەبا 2025`
  - `Kurdistan Region electricity ministry power generation megawatts lost gas supply halted 2025`
  - `وەزارەتی کارەبای هەرێمی کوردستان کەمبوونەوەی بەرهەمهێنانی کارەبا 2026`
  - `Kurdistan Region electricity ministry power generation megawatts lost gas supply halted 2026`
  - `وەزارەتی سامانە سروشتییەکان ڕاگەیەندراو وەستانی بەرهەمهێنان`
  - `وزارة الثروات الطبيعية إقليم كوردستان بيان توقف الإنتاج`
  - `APIKUR statement member companies production suspended`

### IQ5: Media corroboration: Iraqi, Kurdish and international outlets

- Iteration 19: partial, source window `no_census_exists`, stopped by the search allowance; queries 5 of 10; languages run Arabic, English of Arabic, English; 6 endpoints refused or unreadable.
- This pass: run the 5 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `Iraq refinery oilfield fire attack production halted 2024` (attack occurrence: attack allowance only)
  - `حريق مصفى أو حقل نفطي في العراق توقف الإنتاج 2025`
  - `Iraq refinery oilfield fire attack production halted 2025` (attack occurrence: attack allowance only)
  - `حريق مصفى أو حقل نفطي في العراق توقف الإنتاج 2026`
  - `Iraq refinery oilfield fire attack production halted 2026` (attack occurrence: attack allowance only)

## Kuwait (plan: `docs/countries/KW_SYSTEMATIC_SWEEP.md`)

### KW1: Oil sector operators and ministry: statements and the national refining company's annual reports

- Iteration 19: partial, source window `rolling_archive_gap`; queries 2 of 2; items listed or read 4; languages run Arabic, English of Arabic, English; 7 endpoints refused or unreadable.
- This pass: enumerate the archive further where it is reachable; try each refused endpoint once by ordinary fetch.

### KW2: Electricity: the ministry's news archive, Arabic and English

- Iteration 19: partial, source window `rolling_archive_gap`, stopped by the search allowance; queries 2 of 4; items listed or read 655; languages run Arabic, English of Arabic, English; 0 endpoints refused or unreadable.
- This pass: run the 2 declared queries listed below; enumerate the archive further where it is reachable.
- Declared, not run in iteration 19:
  - `Kuwait Ministry of Electricity statement power outage`
  - `Kuwait programmed power cuts load shedding megawatts`

### KW3: Official statements as carried by the state news agency, via search

- Iteration 19: partial, source window `no_census_exists`, stopped by the search allowance; queries 2 of 4; languages run Arabic of Arabic, English; 1 endpoints refused or unreadable.
- This pass: run the lane in English; run the 2 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `KUNA statement fire oil facility Kuwait`
  - `KUNA electricity ministry power outage areas statement`

### KW4: Arabic and English media by year, via search

- Iteration 19: partial, source window `no_census_exists`, stopped by the search allowance; queries 9 of 20; languages run Arabic of Arabic, English; 6 endpoints refused or unreadable.
- This pass: run the lane in English; run the 11 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `Kuwait refinery OR oil facility fire shutdown 2026`
  - `Kuwait energy facility attack reported 2026` (attack occurrence: attack allowance only)
  - `Kuwait refinery OR oil facility fire shutdown 2025`
  - `Kuwait energy facility attack reported 2025` (attack occurrence: attack allowance only)
  - `Kuwait refinery OR oil facility fire shutdown 2024`
  - `Kuwait energy facility attack reported 2024` (attack occurrence: attack allowance only)
  - `Kuwait refinery OR oil facility fire shutdown 2023`
  - `Kuwait energy facility attack reported 2023` (attack occurrence: attack allowance only)
  - `Kuwait refinery OR oil facility fire shutdown 2022`
  - `استهداف منشآت الطاقة في الكويت 2022` (attack occurrence: attack allowance only)
  - `Kuwait energy facility attack reported 2022` (attack occurrence: attack allowance only)

## Oman (plan: `docs/countries/OM_SYSTEMATIC_SWEEP.md`)

### OM1: Ministry of Energy and Minerals statements and the national statistical bulletin, read for disruption-attributed changes

- Iteration 19: partial, source window `current_through_end_date`, stopped by the search allowance; queries 0 of 2; items listed or read 4; languages run Arabic, English of Arabic, English; 2 endpoints refused or unreadable.
- This pass: run the 2 declared queries listed below; enumerate the archive further where it is reachable; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `وزارة الطاقة والمعادن بيان توقف الإنتاج`
  - `Oman Ministry of Energy and Minerals statement production disruption`

### OM2: OQ group and PDO annual and sustainability reports and company releases

- Iteration 19: partial, source window `current_through_end_date`, stopped by the search allowance; queries 0 of 2; items listed or read 5; languages run English of Arabic, English; 12 endpoints refused or unreadable.
- This pass: run the lane in Arabic; run the 2 declared queries listed below; enumerate the archive further where it is reachable; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `OQ PDO Oman unplanned shutdown production halted`
  - `أوكيو تنمية نفط عمان توقف الإنتاج حريق`

### OM3: Oman LNG annual reports, read for material interruptions of production

- Iteration 19: partial, source window `current_through_end_date`, stopped by the search allowance; queries 0 of 2; items listed or read 2; languages run English of Arabic, English; 3 endpoints refused or unreadable.
- This pass: run the lane in Arabic; run the 2 declared queries listed below; enumerate the archive further where it is reachable; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `Oman LNG plant production halted`
  - `الشركة العمانية للغاز الطبيعي المسال توقف الإنتاج`

### OM4: Power: procurement company reports and the regulator's findings on major interruptions

- Iteration 19: partial, source window `current_through_end_date`, stopped by the search allowance; queries 3 of 4; items listed or read 5; languages run Arabic, English of Arabic, English; 7 endpoints refused or unreadable.
- This pass: run the 1 declared queries listed below; enumerate the archive further where it is reachable; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `Oman cyclone electricity customers without power`

### OM5: Arabic and English media by year, via search

- Iteration 19: partial, source window `no_census_exists`, stopped by the search allowance; queries 7 of 20; items listed or read 64; languages run Arabic of Arabic, English; 6 endpoints refused or unreadable.
- This pass: run the lane in English; run the 13 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `حريق مصفاة محطة غاز سلطنة عمان 2023`
  - `حريق مصفاة محطة غاز سلطنة عمان 2024`
  - `حريق مصفاة محطة غاز سلطنة عمان 2025`
  - `Oman power outage 2022`
  - `Oman power outage 2023`
  - `Oman power outage 2024`
  - `Oman power outage 2025`
  - `Oman power outage 2026`
  - `Oman refinery gas plant fire shutdown 2022`
  - `Oman refinery gas plant fire shutdown 2023`
  - `Oman refinery gas plant fire shutdown 2024`
  - `Oman refinery gas plant fire shutdown 2025`
  - `Oman refinery gas plant fire shutdown 2026`

## Qatar (plan: `docs/countries/QA_SYSTEMATIC_SWEEP.md`)

### QA1: QatarEnergy and QatarEnergy LNG: the LNG company's news archive and operator statements

- Iteration 19: partial, source window `current_through_end_date`, stopped by the search allowance; queries 2 of 4; items listed or read 45; languages run Arabic, English of Arabic, English; 6 endpoints refused or unreadable.
- This pass: run the 2 declared queries listed below; enumerate the archive further where it is reachable; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `قطر للطاقة تعلن حالة القوة القاهرة`
  - `QatarEnergy declares force majeure`

### QA2: Electricity and water: utility and ministry statements carried by the state news agency

- Iteration 19: partial, source window `no_census_exists`, stopped by the search allowance; queries 3 of 6; items listed or read 107; languages run Arabic, English of Arabic, English; 1 endpoints refused or unreadable.
- This pass: run the 3 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `Qatar blackout KAHRAMAA widespread power cut`
  - `كهرماء بيان انقطاع المياه محطة تحلية`
  - `KAHRAMAA statement water supply interruption desalination plant`

### QA3: Arabic and English media by year, via search

- Iteration 19: partial, source window `no_census_exists`, stopped by the search allowance; queries 7 of 20; items listed or read 192; languages run Arabic of Arabic, English; 4 endpoints refused or unreadable.
- This pass: run the lane in English; run the 13 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `استهداف منشآت الطاقة في قطر 2025` (attack occurrence: attack allowance only)
  - `قطر حريق منشأة نفطية أو غازية 2026`
  - `استهداف منشآت الطاقة في قطر 2026` (attack occurrence: attack allowance only)
  - `Qatar gas plant OR refinery fire shutdown 2022`
  - `Qatar energy facility attack reported 2022` (attack occurrence: attack allowance only)
  - `Qatar gas plant OR refinery fire shutdown 2023`
  - `Qatar energy facility attack reported 2023` (attack occurrence: attack allowance only)
  - `Qatar gas plant OR refinery fire shutdown 2024`
  - `Qatar energy facility attack reported 2024` (attack occurrence: attack allowance only)
  - `Qatar gas plant OR refinery fire shutdown 2025`
  - `Qatar energy facility attack reported 2025` (attack occurrence: attack allowance only)
  - `Qatar gas plant OR refinery fire shutdown 2026`
  - `Qatar energy facility attack reported 2026` (attack occurrence: attack allowance only)

## Saudi Arabia (plan: `docs/countries/SA_LANE_PASS_19.md`)

### SA1: Ministry of Energy statements as carried by SPA (spa.gov.sa; moenergy.gov.sa), reached through Saudi outlets republishing them

- Iteration 19: not_started, source window `inaccessible`, stopped by the search allowance; queries 0 of 10; languages run none of Arabic, English; 2 endpoints refused or unreadable.
- This pass: run the lane in Arabic, English; run the 10 declared queries listed below; enumerate the archive further where it is reachable; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `وزارة الطاقة مصدر مسؤول استهداف 2026` (attack occurrence: attack allowance only)
  - `Saudi energy ministry statement attack facility 2026` (attack occurrence: attack allowance only)
  - `وزارة الطاقة مصدر مسؤول استهداف 2025` (attack occurrence: attack allowance only)
  - `Saudi energy ministry statement attack facility 2025` (attack occurrence: attack allowance only)
  - `وزارة الطاقة مصدر مسؤول استهداف 2024` (attack occurrence: attack allowance only)
  - `Saudi energy ministry statement attack facility 2024` (attack occurrence: attack allowance only)
  - `وزارة الطاقة مصدر مسؤول استهداف 2023` (attack occurrence: attack allowance only)
  - `Saudi energy ministry statement attack facility 2023` (attack occurrence: attack allowance only)
  - `وزارة الطاقة مصدر مسؤول استهداف 2022` (attack occurrence: attack allowance only)
  - `Saudi energy ministry statement attack facility 2022` (attack occurrence: attack allowance only)

### SA2: Saudi Aramco disclosures: Tadawul announcements; aramco.com news and annual-report incident statements

- Iteration 19: partial, source window `current_through_end_date`, stopped by the search allowance; queries 0 of 2; items listed or read 4; languages run Arabic of Arabic, English; 4 endpoints refused or unreadable.
- This pass: run the lane in English; run the 2 declared queries listed below; enumerate the archive further where it is reachable; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `Aramco Tadawul announcement incident`
  - `أرامكو إعلان تداول حادث`

### SA3: GASTAT and JODI production releases (production effects explicitly attributed to a disruption)

- Iteration 19: partial, source window `rolling_archive_gap`; queries 0 of 0; items listed or read 24; languages run Arabic, English of Arabic, English; 2 endpoints refused or unreadable.
- This pass: enumerate the archive further where it is reachable; try each refused endpoint once by ordinary fetch.

### SA4: OPEC Monthly Oil Market Report archive

- Iteration 19: not_started, source window `inaccessible`; queries 0 of 0; languages run none of English; 1 endpoints refused or unreadable.
- This pass: run the lane in English; enumerate the archive further where it is reachable; try each refused endpoint once by ordinary fetch.

### SA5: International and regional reporting (Reuters, Bloomberg, AP, S&P Global, Argus, as carried by open outlets), via search

- Iteration 19: partial, source window `no_census_exists`, stopped by the search allowance; queries 7 of 15; languages run Arabic, English of Arabic, English; 6 endpoints refused or unreadable.
- This pass: run the 8 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `Saudi refinery fire shut 2025`
  - `Saudi Aramco facility attack 2025` (attack occurrence: attack allowance only)
  - `Saudi power outage 2025`
  - `حريق مصفاة السعودية 2024`
  - `انقطاع الكهرباء السعودية 2024`
  - `Saudi refinery fire shut 2024`
  - `Saudi Aramco facility attack 2024` (attack occurrence: attack allowance only)
  - `Saudi power outage 2024`

## United Arab Emirates (plan: `docs/countries/AE_SYSTEMATIC_SWEEP.md`)

### AE1: National statements: Ministry of Energy and Infrastructure and federal statements as carried by the state news agency, via search

- Iteration 19: partial, source window `inaccessible`, stopped by the search allowance; queries 1 of 10; languages run Arabic of Arabic, English; 2 endpoints refused or unreadable.
- This pass: run the lane in English; run the 9 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `وام وزارة الطاقة والبنية التحتية بيان انقطاع إمدادات الطاقة 2022`
  - `وام وزارة الطاقة والبنية التحتية بيان انقطاع إمدادات الطاقة 2023`
  - `وام وزارة الطاقة والبنية التحتية بيان انقطاع إمدادات الطاقة 2024`
  - `وام وزارة الطاقة والبنية التحتية بيان انقطاع إمدادات الطاقة 2025`
  - `WAM UAE Ministry of Energy and Infrastructure statement energy supply disruption 2022`
  - `WAM UAE Ministry of Energy and Infrastructure statement energy supply disruption 2023`
  - `WAM UAE Ministry of Energy and Infrastructure statement energy supply disruption 2024`
  - `WAM UAE Ministry of Energy and Infrastructure statement energy supply disruption 2025`
  - `WAM UAE Ministry of Energy and Infrastructure statement energy supply disruption 2026`

### AE2: ADNOC group annual and integrated reports, read for incident occurrence

- Iteration 19: partial, source window `publisher_not_yet_released`, stopped by the search allowance; queries 1 of 4; items listed or read 73; languages run Arabic, English of Arabic, English; 5 endpoints refused or unreadable.
- This pass: run the 3 declared queries listed below; enumerate the archive further where it is reachable; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `ADNOC fire explosion refinery gas plant shutdown force majeure`
  - `ADNOC Gas ADX disclosure incident production halted`
  - `أدنوك للغاز إفصاح سوق أبوظبي للأوراق المالية حادث قوة قاهرة`

### AE3: Electricity utilities and regulators: media releases and news listings

- Iteration 19: partial, source window `rolling_archive_gap`, stopped by the search allowance; queries 2 of 4; items listed or read 269; languages run Arabic, English of Arabic, English; 7 endpoints refused or unreadable.
- This pass: run the 2 declared queries listed below; enumerate the archive further where it is reachable; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `UAE power outage DEWA SEWA EWEC Etihad Water and Electricity statement customers affected`
  - `انقطاع التيار الكهربائي الإمارات هيئة كهرباء ومياه بيان المتأثرين`

### AE4: Arabic and English media by year, via search

- Iteration 19: partial, source window `no_census_exists`, stopped by the search allowance; queries 8 of 18; languages run Arabic, English of Arabic, English; 10 endpoints refused or unreadable.
- This pass: run the 10 declared queries listed below; try each refused endpoint once by ordinary fetch.
- Declared, not run in iteration 19:
  - `الإمارات حريق مصفاة محطة كهرباء انقطاع توقف 2022`
  - `الإمارات حريق مصفاة محطة كهرباء انقطاع توقف 2026`
  - `UAE refinery gas plant power station fire outage shutdown 2022`
  - `UAE refinery gas plant power station fire outage shutdown 2023`
  - `UAE refinery gas plant power station fire outage shutdown 2024`
  - `UAE refinery gas plant power station fire outage shutdown 2025`
  - `UAE refinery gas plant power station fire outage shutdown 2026`
  - `Abu Dhabi attack fuel facility 17 January 2022` (attack occurrence: attack allowance only)
  - `UAE energy facility attack April 2026` (attack occurrence: attack allowance only)
  - `UAE energy facility attack May 2026` (attack occurrence: attack allowance only)
