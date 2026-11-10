# Saudi Arabia — research pass (iteration 18)

**Part A, the search plan, was written on 2026-11-10 before any search of this pass was run.**
Lanes and order are those of `SA_SYSTEMATIC_SWEEP.md`. Inclusion rule version `2026-10-30.1`,
unchanged. Window 2022-01-01 to 2026-11-10. Coverage vocabulary as in `US_LANE_PASS_18.md`.

**Safety first.** An attack campaign is recorded as active (`conflict_campaigns.json`). This pass
collects event occurrence, the effect reported at the time and the admin-1 historical record. It
does **not** collect restart, current operating rate, repair progress, remaining capacity, current
outage or current facility condition, even where public, in any field.

## Part A — plan (written before searching)

### A.1 Lanes

| Lane | Universe kind | Languages | Universe | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|---|---|
| SA1 | report archive | ar+en | Ministry of Energy statements as carried by SPA | spa.gov.sa; moenergy.gov.sa public search or index pages by ordinary access | for each year Y in 2022-2026: `وزارة الطاقة مصدر مسؤول استهداف Y`; `Saudi energy ministry statement attack facility Y` | 1, 2, 3, 7 |
| SA2 | report archive | ar+en | Aramco annual reports 2022-2025; investor disclosures for incident occurrence. Tadawul refusal is a documented limitation | aramco.com annual reports; saudiexchange.sa by ordinary access | `Aramco Tadawul announcement incident`; `أرامكو إعلان تداول حادث` | 1, 7 |
| SA3 | report archive | ar+en | GASTAT and JODI production releases, read only for disruption-attributed commentary. A numeric series with no attribution yields context, never an incident | stats.gov.sa; jodidata.org | none; enumeration only | 7 |
| SA4 | report archive | en | OPEC Monthly Oil Market Report: production changes attributed to a disruption | opec.org archive, official downloadable monthly PDFs by ordinary access | none; enumeration only | 7 |
| SA5 | declared query set | ar+en | International and regional reporting | via search; Arabic query for each English family | for each year Y in 2022-2026: `Saudi refinery fire shut Y`; `Saudi Aramco facility attack Y`; `Saudi power outage Y`; and `حريق مصفاة السعودية Y`; `انقطاع الكهرباء السعودية Y` | 1-7 |

### A.2 Safety

Citations published more than 7 days after a covered event, and addresses that announce status, stay
in the local queue. Every published Saudi record is read end to end by a safety reviewer in this pass.

### A.3 Budget, resilience, review

As `US_LANE_PASS_18.md` A.3.
