# Taxonomy options (iteration 20)

Iteration 19's researchers held candidates because no asset class or cause fitted. No label is
added in this iteration: a category is worth adding only if it solves a problem that recurs across
systems, never to rescue one record. This document sets out each proposal and a recommendation for
the owner (`OWNER_DECISION_MATRIX_20.md`, D-02 and D-19).

The vocabulary today: 15 asset classes in `pipeline/config.py` (`ASSET_CLASSES`) plus `system_wide`
and `upstream_production` (`TAXONOMY_EXTENSIONS`); causes in `DISRUPTION_CAUSES` plus
`natural_hazard` and `labour`.

## Asset classes

| Proposal | Definition | Examples seen | Overlap with existing terms | Evidence threshold | Cross-country | Safety effect | Corpus change | Recommendation |
|---|---|---|---|---|---|---|---|---|
| Fuel depot | storage and distribution of refined products, not at a refinery or terminal | Iraq, Kuwait | `oil_terminal` is labelled "Oil terminal / storage" and already covers storage | the clauses, not the class, are the gap: no clause covers a depot unless it is an import or export terminal (clause 2) | common everywhere | a depot class beside a campaign invites a target list of storage sites | none | **Do not add.** Classify as `oil_terminal` where a source calls it a terminal and clause 2 is met; otherwise it does not qualify. |
| Petrochemical plant | a plant whose output is chemicals, not fuel or power | Saudi Arabia, United States | none | — | common | none | none | **Do not add.** Outside the product: energy supply, not chemical output. Record only the energy effect (a refinery unit, a power outage) when one is stated. |
| Power-and-water plant | a cogeneration plant producing electricity and desalinated water | every GCC state | `power_plant_thermal` fits truthfully: it is a thermal power plant | as for any plant: about 500 MW offline with a reported electricity effect, or rotating outages | the six GCC states | none beyond any power plant | the held candidates become reviewable | **Do not add.** Classify by its electricity role as `power_plant_thermal` when a source reports an electricity effect; a water-only effect is outside the product. This answers the recurring question without a new label. |
| Gas-to-liquids plant | converts natural gas to liquid fuels | Qatar | `gas_processing` is the nearest truthful class | clause 1 | one or two sites in the monitored systems | where the class is one site in a country, the single-site rule applies | none | **Do not add.** Use `gas_processing` where clause 1 is met; the single-site rule applies. |

## Causes

| Proposal | Definition | Examples seen | Overlap | Evidence threshold | Cross-country | Safety effect | Corpus change | Recommendation |
|---|---|---|---|---|---|---|---|---|
| Precautionary shutdown during hostilities | an operator stops a plant pre-emptively, with no reported damage | Gulf 2026 | it is an operator's decision: the "policy decisions" exclusion | — | Gulf | recording pre-emptive stops beside attack records maps which sites operators fear for | none | **Do not add.** Excluded as a decision with no physical effect; where damage is reported, the cause is the attack. |
| Protest or blockade by people who are not the workforce | access to a site or route blocked by protesters | Iraq (recurring), Canada and the United States (pipeline protests), India | `labour` covers the workforce only | a stated shutdown or shut-in caused by the blockade | at least four systems | low: public, non-kinetic, already widely reported | one Iraq hold becomes reviewable | **Add `civil_blockade`** ("Protest or blockade by non-workforce actors"). The one proposal that recurs across systems and has no truthful existing label. |
| Demand above available generation | load exceeds what is available | Kuwait, Iraq, Iran | a cause of programmed cuts, which clause 4 handles through its "generation shortfall" limb | — | Gulf | none | none | **Do not add.** It is the clause-4 question (D-17), not a cause; such records use `unknown` with the stated shortfall in the summary, as fuel-supply shortfalls already do. |

## If approved

`civil_blockade` is one entry in `TAXONOMY_EXTENSIONS["causes"]`; the import gate then accepts it,
held candidates tagged [TAXONOMY] with a blockade cause go to blind review, and nothing published
changes. Until then those candidates stay held.
