# Oman — index readiness

Written 2026-11-11 by the Oman source-audit lane (iteration 19, Wave A). Companion to
[OM_SOURCE_AUDIT.md](OM_SOURCE_AUDIT.md), which carries the evidence and addresses for every source
named here. **Nothing here changes a published number, and no score is activated.** Incident
coverage is assessed from the nature of the sources, not from incident research, which is Wave B.

Readiness vocabulary:

- **READY** — denominator exists on one stated basis, dated, complete enough to score against.
- **EXPERIMENTAL** — usable with disclosed caveats; publish as a labelled sensitivity, not headline.
- **INCOMPLETE** — a credible path exists, but a required input is not yet acquired or reconciled.
- **UNSUITABLE** — should not be built, for data reasons, scope-boundary reasons, or both.
- **NOT APPLICABLE** — the sector does not exist in the country's energy system (a sourced zero,
  not a gap). Distinct from **UNKNOWN** (exists, unmeasured) and **NOT YET RESEARCHED**.

This document deliberately lists no facility with a capacity. Where a list exists, it says so and
says where.

---

## Bottom line

**CONTEXT_ONLY** today, for every sector that exists. Coal is **NOT_APPLICABLE**.

- No sector has an index-grade denominator in hand. Two have a credible path: electric generation
  (the single buyer publishes the contracted plants every year) and refining (a small number of
  plants under two operators, whose annual reports were not read this session).
- The national statistics are good and openly licensed, but they are national. The one regional
  table found, electricity production, uses eight groupings that merge five of the eleven
  governorates and leave one without a row.
- The event side is the binding limit. The regulator, the ministry and the news agency could not
  be read by ordinary access, the exchange exposes no disclosure history, and company reports
  carry no outage record. A coverage ratio cannot be computed.

**Minimum work before any Omani sector could be called EXPERIMENTAL:**

1. Read the OQ group annual report (the 2025 PDF exceeds the fetch limit; a person can open it)
   and the OQ8 report, and establish whether together they give every refinery on one stated
   basis and vintage.
2. Build a dated plant census from Nama PWP's annual reports, placed into governorates by name,
   never by coordinate in any emitted file; reconcile its total against NCSI's national
   production.
3. Have a person open apsr.om and establish what the regulator publishes about interruptions.
4. Obtain the owner decisions in `GLOBAL_METHODOLOGY.md` §8. The ESDI's weights, decay and
   transmission measure do not transfer.

---

## 1. Refining — **INCOMPLETE**

| Item | Finding |
|---|---|
| Inventory | Not read. Refining is carried out by OQ Refineries and Petroleum Industries and by the OQ8 joint venture. A per-refinery list is expected in the OQ group annual report (2021-2025 editions listed at `oq.com/en/investors/financial-statements-and-reports`; the 2025 PDF exceeds 10 MB and was not fetched) and in OQ8's own reports (`oq8.om`, not fetched). **Completeness is not established** |
| Capacity | Not read this session from any primary source. EIA's country brief is dated 2019 and is rejected for figures |
| Output (not capacity) | NCSI Table 10 publishes monthly national output, domestic sales and exports by product, stated to represent all refineries; source Ministry of Energy and Minerals. One company release gives crude refined in 2025 by OQ RPI as a company total |
| Basis | Unknown until the annual reports are read. One operator is a joint venture, so the gross-versus-equity question recorded for Saudi Arabia (`SA_SOURCE_AUDIT.md` §3) will arise here and must be settled the same way: gross physical capacity, numerator and denominator from the same row |
| Vintage / status | Not established |

**Granularity caveat:** the number of plants is small, so each is a large fraction of the base and a
sector series would move in steps. That is a reason for caution about scoring at all, and a reason
never to show a per-facility table.

**Achievable incident coverage:** unknown. Company publications read this session report no
unplanned shutdown. Expect coverage only of events large enough for a ministry or company
statement or a wire report.

**Restoration evidence:** not assessed. For any kinetic or sabotage event dated 2026 it is not
collected at all: the Omani campaign is recorded as `uncertain`, which is treated as active.

---

## 2. Electric generation — **INCOMPLETE**

| Item | Finding |
|---|---|
| Inventory | **A list exists.** Nama PWP's Annual Report 2025 carries a purchase figure for each contracted plant, and its 7-Year Statements describe contracted resources; listing at `omanpwp.om/annual-report` and `/7-year-statement-electricity`, editions back to at least 2020. Not copied here |
| Capacity | Contracted capacity per plant is expected in earlier 7-Year Statement issues **(not verified this session**; Issue 20 gives system totals in figures only). National demand: main system peak 7,863 MW and Dhofar system peak 850 MW in 2025 |
| Basis | Contracted (single-buyer) resources. Excludes captive and auto-generation: NCSI notes that net production includes autogenerators and rented diesel units that do not appear in gross production, and that gas for power includes plants belonging to oil and gas companies |
| National total | Gross production 50,973.5 GWh, net 49,532.4 GWh, 2025 (NCSI Table 21, source APSR, provisional) |
| Regional basis | NCSI: eight groupings, not the eleven governorates. Nama PWP: three power systems, and bulk supply for nine governorates of the main system |
| Vintage | Annual; 2025 read |
| Status / retirement | Not stated in the documents read; would have to be inferred by comparing editions |
| WRI GPPD | 12 Omani rows, 6,011 MW, newest stated commissioning year 2008: rejected |

**Path:** dated census from Nama PWP editions 2020-2025 → governorate by name → reconcile to NCSI
national production, disclosing the captive-generation gap. Until then INCOMPLETE.

**Achievable incident coverage:** large interruptions are reported by the press with regulator
statements; plant-level trips are not expected to surface. Clause 4 (about 500 MW) and clause 5
(about 100,000 customers) are absolute thresholds in a system whose 2025 peak was under 8,000 MW;
the known weakness recorded in `inclusion_threshold.json` applies with some force here.

**Restoration evidence:** press reports of restoration exist for large interruptions (seen in
search-result titles, not researched).

---

## 3. Transmission — **UNSUITABLE** (as an event-burden sector), context only

| Item | Finding |
|---|---|
| Inventory | None read. OETC's annual-report and publication listings returned no entries |
| Basis / vintage | Not established |

There is neither a regional event stream nor a regional inventory, and assembling a line-level or
station-level picture of a grid from planning documents is outside the scope boundary. The task
instruction for this country is explicit: national totals only, no line-level or constraint data.
Recommend **no Omani transmission sector**. A national total may appear as dated context if an
OETC annual report is ever read.

---

## 4. Oil logistics — **UNSUITABLE**

No public capacity inventory for terminals, storage or crude pipelines was sought or found, and
building one would centre on export routing, which the scope boundary and the Gulf brief both
exclude. National export volume is published monthly (NCSI Table 9) and is context only: export
volume is not commensurable with a refining base, as recorded for Saudi Arabia. Recommend the
sector stay **uncovered** (excluded, never zero), with the page saying why.

---

## 5. Gas — **INCOMPLETE** overall

### 5a. Gas processing — **INCOMPLETE**

- Inventory: none read. Processing is carried out by several operators (PDO, OQ Exploration and
  Production and others); no single national list was found. PDO's report gives company sales-gas
  production, not plant capacities.
- National balance: NCSI Table 9 gives monthly gas supply (associated; non-associated plus
  imports) and its use by four consumer classes. That is a flow, not a capacity.
- Verdict: a denominator would have to be assembled from several company reports on bases not yet
  compared. INCOMPLETE.

### 5b. Gas pipelines — **UNSUITABLE**

The network operator's investor pages sit behind a terms-acceptance gate and were not read. No
capacity inventory; and a pipeline layer would be route information. Recommend no Omani gas
pipeline layer, analytic or context.

### 5c. Gas storage — **NOT YET RESEARCHED**

### 5d. LNG — **INCOMPLETE**, national context available

- Oman LNG's annual reports (2009-2025 listed) give annual production for the complex: 11.98
  million tonnes in 2024. That is a production figure; a capacity figure on a stated basis was not
  read. New LNG projects are reported as under development and are not inventory.
- The inventory is very small, which makes any per-facility presentation unsuitable; LNG belongs
  in the national profile as one dated number.
- Nothing about cargoes, vessels or routes is read.

---

## 6. Coal — **NOT APPLICABLE**

The repository's committed EIA International Energy Statistics extract (bulk release 2026-10-16,
year 2024) gives Oman coal production **0.0 million tonnes** and coal-fired electricity
**0 TWh**, with coal consumption of 0.03 million tonnes. Nama PWP's 7-Year Statement 2026-2032
describes the generation mix as natural gas plus solar and wind and mentions no coal plant. This
is a **sourced zero**: NOT APPLICABLE, not UNKNOWN. The small consumption figure is industrial use
and creates no energy-infrastructure sector to monitor.

---

## 7. Upstream — not a sector in the current taxonomy

Petroleum liquids and natural gas made up almost all of Oman's primary energy production in 2024
(2.146 and 1.59 of 3.742 quadrillion Btu in the repository's committed EIA extract). National oil
production averaged 1,002.0 thousand b/d in 2025 (NCSI, from the ministry), of which one operator reported
705,539 b/d. The taxonomy has no upstream sector. A field-level or station-level inventory is
**not recommended** under the scope boundary. Upstream belongs in the national profile as context
(NCSI monthly production and exports; JODI), and upstream events enter only through clause 7, at
governorate precision at most.

---

## Russia-model assumptions that fail for Oman

| Russia assumption | Omani reality |
|---|---|
| A structured open-source event table supplies events and a coverage benchmark | None identified; **coverage must read "unknown"** |
| Regional electricity facts can be placed into first-level regions | Official production statistics use eight groupings; five governorates are merged and one has no row |
| Natural Earth codes join to ISO codes | Two of eleven do not (OM-BA, OM-SH), and the obvious remapping is wrong for one of them |
| WRI GPPD is an acceptable (if stale) generation denominator | 12 rows, newest 2008: unusable |
| Pipelines reconstructed from OSM route relations | Not inspected, and out of scope for this country in any case |
| `heating_season_months` marks the stress season | Demand peaks in summer **(stated generally by Nama PWP as weather-driven; month not read this session)**; the heating flag is wrong, not merely irrelevant |
| Coal "uncovered" is a temporary gap | Coal is **not applicable** |
| Sector taxonomy covers the main energy activity | Upstream is absent from the taxonomy |
| Absolute thresholds mean roughly the same everywhere | 500 MW is over 6% of the main system's 2025 peak (computed from 7,863 MW); 100,000 customers is set against a registered population of about 5.45 million (NCSI, September 2026) |

---

## Transparency limits, stated once

- The ministry (script-only), the regulator (script-only) and the national news agency (certificate
  error) could not be read by ordinary access on 2026-11-11. Whether a browser reads them was not
  tested and is not assumed.
- The exchange's disclosure history and one listed company's investor pages are not reachable
  without scripts or accepting terms.
- Company reports read this session (Nama PWP, Oman LNG, PDO, one OQ release) contain no dated
  outage record.
- Low reported incident counts for Oman are a property of this environment and must be presented
  as "coverage unknown", never as low disruption.
