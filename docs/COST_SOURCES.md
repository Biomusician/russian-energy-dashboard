# Cost & economic-effect sources — research architecture

Iteration 1 built the **schema and UI foundation** for repair cost and economic
effects, and deliberately left the values null. This document records the candidate
open sources so a later iteration can populate them from evidence rather than guesses.

The guiding rule is unchanged: **reported, externally-estimated and modelled figures
stay structurally distinct, and nothing is invented to fill a slot.**

---

## 1. Repair cost (per facility)

The hard truth: **per-facility repair costs are rarely public.** Russian operators do
not publish them, and where a figure exists it is almost always an analyst estimate in
news copy, not a reported cost. So this field will stay sparse, and the schema treats
that as normal (`repair_cost_reported_usd_m` vs `repair_cost_estimate_low/high_usd_m`
with a `cost_basis` string).

| Source | What it offers | Access / licence | Usability |
|---|---|---|---|
| Reuters / Bloomberg energy desks | Occasional analyst repair-cost estimates in strike coverage | Headlines public; full articles paywalled | Manual, per-incident, cite the estimate and its author |
| Kyiv School of Economics (KSE Institute) | Structured war-economy analysis; methodology is public | Reports open (PDF) | Estimates, not reported costs; good for method, cite explicitly |
| S&P Global Commodity Insights (Platts) | Refinery outage and capacity notes | Mostly paywalled | Low for open use |
| Company disclosures (Rosneft, Gazprom Neft, Lukoil, Transneft) | Capex / impairment lines in filings | Public but coarse, Russian-language, annual | Cannot attribute to a single strike; low granularity |

**Recommendation:** treat repair cost as an occasional, manually-curated, estimate-only
field. Do not build an automated ingester for it — the source density does not justify
one, and automation would pressure toward fabrication.

---

## 2. Export / revenue effects (the strongest open channel)

This is where open data is genuinely good, and where the "war-sustainment" effects tab
should eventually draw real numbers rather than the current refining-exposure proxy.

| Source | What it offers | Access / licence | Usability |
|---|---|---|---|
| **CREA — Centre for Research on Energy and Clean Air** | Monthly Russian fossil-fuel export volumes and revenue, by commodity and destination; a monthly refinery-outage / crude-throughput tracker | Open, published as data and charts; attribution expected | **High.** The single best open source for revenue effects. Machine-readable exports exist. |
| **IEA Oil Market Report** | Russian crude and product export and refining throughput | Summary public, full report subscription | Medium; use public summaries |
| Russian Ministry of Finance | Federal oil & gas budget revenue (monthly) | Public, Russian-language | Medium; a national macro denominator for revenue pressure |
| Rosstat | Industrial production, refining output indices | Public, Russian-language, lagged | Medium; supports "industrial impact" and "refining utilization" |

**Recommendation:** a later iteration should ingest **CREA's monthly export-revenue and
refinery-throughput series** and use it to replace the proxy strategic indicators with
observed national figures — clearly dated and cited. This is the highest-value data
addition available.

---

## 3. Electricity / population effects

| Source | What it offers | Access / licence | Usability |
|---|---|---|---|
| **Ember** | Open European/global electricity generation and demand data | Open, CC BY 4.0 | High for structural context; thin on Russian outage events |
| SO UPS (System Operator of the Unified Power System) | Russian grid operational notices | Public, Russian-language | Medium; disruption notices, not customer-minutes-lost |
| ENTSO-E | Cross-border flows (relevant to interconnectors) | Open | Low for internal Russia |
| Regional utility statements / local press | Outage duration, affected consumers | Ad hoc, Russian-language | Manual curation only |

There is **no open source for Russian customer-minutes-lost or outage duration at
scale**, which is why `civilian_electricity_reliability` stays "not modelled". Do not
proxy it with something weaker and call it measured.

---

## 4. What to build next, in order

1. **Ingest CREA monthly export-revenue + throughput** → real observed national
   revenue-pressure and refining-utilization series (replaces the proxy).
2. **Curated repair-cost estimates**, estimate-only, per notable incident, each citing
   its analyst source.
3. **Rosstat refining-output index** as a national throughput sanity check against the
   exposure index.
4. Leave electricity-reliability and per-facility reported cost null until a real
   source exists. An honest gap beats a fabricated number.

Every one of these must land in the data as `observed` / `estimated` / `modelled` with
provenance, exactly like the recovery framework.
