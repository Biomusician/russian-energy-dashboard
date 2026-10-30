# Global country selection (iteration 14)

## The rule

**The five largest total primary energy producers in the world, excluding Russia.**

"Total" means all primary energy: oil, gas, coal, nuclear and renewables, measured in one
energy unit. It is a statement about the size of the energy system. It is **not** a statement
about how important a country's infrastructure is to anyone, how exposed it is, or how much
disruption happens there. A country's place in this list never appears in the dashboard as a
rank.

Russia is excluded because it is already monitored, as part of the Russia, Belarus & Crimea
theatre. The theatre is not a country and keeps its own shape.

## The evidence

U.S. EIA International Energy Statistics, total primary energy production, 2024, ranked over all
countries the EIA publishes (quadrillion Btu). Read 2026-10-30.

| Country | 2024 production (quad Btu) | In the set |
|---|---:|---|
| China | 130.8 | yes |
| United States | 103.5 | yes |
| *Russia* | *60.3* | *already monitored (theatre)* |
| Saudi Arabia | 26.9 | yes |
| Canada | 22.6 | yes |
| India | 22.3 | yes |
| Indonesia | 20.2 | no — first outside the set |
| Iran | 20.2 | no |
| Australia | 17.8 | no |

The Energy Institute Statistical Review (EI-derived 2024 totals) agrees on the membership of the
five, but puts India about 0.1% ahead of Canada.

**Consequence.** The *set* is stable across both sources. The *order* within it is not:
Canada and India differ by about 1% and swap places between sources and years. The dashboard
therefore never shows an order. Systems are listed alphabetically everywhere, and the registry
(`pipeline/systems.py`) records the rule, the source and this caveat rather than a rank.

The margin to the sixth country is also thin: India (22.3) leads Indonesia and Iran (both 20.2)
by about 10%. A future EIA revision could change the membership. If it does, the rule is the
decision; re-running it is not a methodology change.

## What the selection is not

- **Not a target list.** Selection by production size is the most neutral available criterion
  precisely because it says nothing about any facility. The project's scope boundary applies in
  full to every system: no ranking of undamaged infrastructure, no vulnerability or criticality
  fields, incidents aggregated to first-level regions, never coordinates.
- **Not a claim of comparable data.** Data availability varies enormously across the five
  (`docs/countries/*_SOURCE_AUDIT.md`). COUNTRY DATA AVAILABILITY ≠ COUNTRY ENERGY IMPORTANCE.
- **Not a claim of comparable disruption.** See `GLOBAL_METHODOLOGY.md` §6. Counts reflect
  reporting environments, which range from mandatory regulatory reporting (US) to media only
  (China).

## Wave 2 (ranked, not implemented)

Ranked by the same rule, for a future iteration to take up. Listed with the main obstacle each
would bring, from what the iteration-14 lanes learned about the first five.

| Order | Country | 2024 (quad Btu) | Main obstacle |
|---|---|---:|---|
| 1= | Indonesia | 20.2 | Coal-heavy with an archipelago grid; reporting is regional and largely in Indonesian. |
| 1= | Iran | 20.2 | Conflict-affected reporting; sanctions limit official data; the scope boundary needs particular care. |
| 3 | Australia | 17.8 | Probably the most tractable after the US: mandatory market-operator reporting and open statistics. |
| — | Qatar, Norway, Brazil, UAE, Iraq | not read | Named in the iteration brief. Their 2024 values were **not read** this iteration, so they are not ordered here. Qatar and UAE would be corporate-disclosure environments like Saudi Arabia; Norway mostly context (excellent data, few qualifying events); Brazil needs a drought/supply-shortfall cause the taxonomy lacks; Iraq's Kurdistan Region needs a disputed-administration ruling. |

Only Indonesia, Iran and Australia were read from the EIA table this iteration. Ordering the rest
needs one more read of the same table, not a judgement.
