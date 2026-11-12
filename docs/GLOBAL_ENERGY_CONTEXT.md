# Global energy context (iteration 18)

National energy statistics for every country in one source and one year. **Context, not
monitoring.** A country in this layer is not thereby watched for disruptions; the systems
registry (`pipeline/systems.py`) is the only thing that says a country is monitored.

## What it is, and what it is not

| | |
|---|---|
| Unit | Country. Nothing finer exists in this layer and none may be added |
| Source | U.S. EIA International Energy Statistics, bulk file `INTL.zip` |
| Year | One comparison year for every country and every metric; the file states it |
| Used for | The world map's context modes, the context card, the national table, the country page's national block, the PNG exports |
| Never used for | Scoring, weighting, event inclusion, ranking of disruptions, or any statement about a facility |

Hard rules, each tested in `tests/test_iteration18.py`:

- No module that produces an analytic figure may import the context layer.
- The daily build never fetches world data. `scripts/build_global_context.py` is an analyst step;
  the build only validates and copies the committed file. If EIA is unreachable the last valid
  static file keeps serving.
- A country outside the registry carries no incident field, not even zero. Zero incidents would
  say we looked. We did not.
- A missing value is `null` and renders "no data". A zero is the source's own zero. They draw
  differently on the map.
- No value from another year stands in for a missing one. A later value, where EIA has one, is
  held apart under `newer` and labelled with its year.
- Colour ramp is its own sequential scale, unlike the disruption palette: a large producer must not
  look like a damaged one.
- Rows sort by name. The table can be sorted on the reader's own request. Since iteration 20 the world profile lists no "largest producers" at all, alphabetical or not (brief §80: no rank language). No position number is shown. **The sort is an owner question** (`docs/ITERATION_18_REVIEW.md` §15): these are national aggregates, not assets, but a descending sort is a ranking.

## Metrics

Twenty-two series: total primary energy production and consumption, the fuel split of production,
oil (crude and total liquids), natural gas and coal production and consumption, electricity
generation and its fuel split. Exact EIA series ids, unit conversions and definitions are in
`METRICS` in `scripts/build_global_context.py`, and travel with the payload under `metrics`.

**Omitted on purpose: LNG and refining capacity.** EIA has no such series in the bulk file, and no
open national source was verified, so neither is shown. Facility-level datasets exist and are out
of scope for this layer.

**Map uses crude oil, not total liquids.** EIA's total-liquids series includes refinery processing
gain, which credits a refining importer with "production" (validation below).

**Producer or consumer.** A broad label from production against consumption, with a band of 15%
around balance. It compares production with consumption and says nothing about trade, and it is
not a dependence measure.

## Comparison year

The latest year for which EIA covers nearly every country across the map metrics. A newer year with
partial coverage would compare different years silently; `newer` shows those values without
letting them colour the map. Choosing the year is an analyst decision recorded in
`comparison_year_reason`.

## Licensing

| Source | Decision | Basis |
|---|---|---|
| U.S. EIA `INTL.zip` | **Used** | U.S. government work, public domain, credit requested. Attribution is on every surface showing a figure |
| Our World in Data energy dataset | Validation only, **no value committed** | CC BY for OWID's own work, but its fossil columns derive from the Energy Institute, whose terms could not be read |
| Energy Institute Statistical Review | Not committed | Terms page refused automated access; unread terms mean do not commit |
| Ember | Not needed | CC BY 4.0, electricity only |
| World Bank | Not needed | Licence varies by indicator |
| IEA, UN Statistics Division | Not committed | Non-commercial or restricted redistribution |
| Global Energy Monitor | Excluded by scope | Facility-level; an inventory is what this layer must not become |

## Validation (2026-11-10)

Against the Our World in Data file, which draws on other primary compilers, for the comparison year:

- Primary energy consumption: median ratio about 1.02. Most outliers are hydro-heavy countries
  (Norway, Sweden, Switzerland, Austria), explained by the substitution method the two sources use;
  a few (Estonia, Turkmenistan, Kazakhstan) are not and remain unexplained.
- Electricity generation: median ratio about 1.000.
- Gas and coal agree up to the expected energy-content conversion, with a few outliers (Poland,
  Syria and Venezuela on gas). Coal in mass against coal in energy has a legitimate spread.
- Total liquids runs ahead of crude for refining importers. That is the processing-gain effect and
  the reason the map uses crude. The producer-or-consumer oil label still counts all liquids, and the
  card says so.

Internal: the sum of countries is 0.99999 of EIA's world total production.

The five-largest-producer selection rule was re-run on this release and is unchanged. Membership
does not change from this page; see `docs/GLOBAL_COUNTRY_SELECTION.md`.

## Updating it

1. Download `INTL.zip` by hand into `data/raw/global/` (gitignored).
2. `.venv\Scripts\python.exe scripts\build_global_context.py`
3. Read the diff, then `.venv\Scripts\python.exe -m pipeline.run`.
4. Tests fail if a value breaks a plausibility limit, a unit changes, a year is unfinished or a
   forbidden field appears.

EIA updates the file on a rolling basis. A new comparison year is a deliberate change, not a
refresh. Nothing about this layer runs in the daily workflow.

## Known limits

- Some Natural Earth units have no EIA row (Somaliland, Northern Cyprus) and show "no data".
- EIA does not state whether its Ukraine or Russia totals include Crimea. Crimea's hover therefore
  shows Ukraine's national figure, labelled as national.
- The electricity split has no "other" row, so shares can sum below 100%.
