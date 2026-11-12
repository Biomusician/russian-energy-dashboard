# Gulf architecture (iteration 19)

How seven Gulf country systems, a regional overview and three group facts were added without a
new kind of system, a new index or a country list in the frontend. Read with
`GLOBAL_ARCHITECTURE.md` (the system model this extends), `GULF_ENERGY_CONTEXT.md` (what the
overview shows) and `GLOBAL_METHODOLOGY.md` (what may be computed and compared).

## One paragraph

Iran, Iraq, Kuwait, Bahrain, Qatar, the United Arab Emirates and Oman are ordinary **country
systems**: same files, same build, same review gate as Canada or India, no score. Saudi Arabia was
already one and is unchanged. A **group** is a named set of system ids in the registry: the Gulf
littoral (geography), the GCC and OPEC (memberships). A group has no payload directory, no index
and no figure of its own. The one group with a page, the Gulf, is fed by one generated context
file. Three things are new and apply to every country, not only the Gulf: a **campaign
classification** per system that fails closed, a **precision policy** per system under which
admin-1 is a maximum, and **calendar and numeral handling** for sources that do not write
Gregorian dates in Latin digits.

## What was added, by file

| File | What it holds |
|---|---|
| `pipeline/systems.py` | the seven new `SYSTEMS` entries with own-script `aliases`; `GROUPS`; `groups_of`; `GULF_SELECTION` |
| `pipeline/calendars.py` | digit normalisation, `parse_number`, Solar Hijri and Hijri conversion, `normalize_date` |
| `pipeline/gulf_context.py` | builds `global/gulf.json`; refuses forbidden fields; no analytic module imports it |
| `pipeline/build_systems.py` | `campaign_problems`, `precision_problems`, Persian status wording, Iran's code table, the manifest's `groups` |
| `data/curated/systems/conflict_campaigns.json` | `system_states` for all eight Gulf systems; a campaign entry for each restricted one |
| `data/curated/systems/<cc>/` | `system.json` (with `geography.precision_policy` and `maturity`), `profile.json`, `events.json`, `episodes.json`, `research_log.json` |
| `scripts/onboard_system.py` | turns a reviewed source-audit draft into a curated system with an empty record |
| `scripts/import_candidates.py` | the gate: date re-computation, country-level downgrade, opaque ids, original-language titles |
| `web/src/global/GroupView.tsx`, `groupExport.ts` | the regional overview and its PNG brief |
| `docs/countries/<CC>_SOURCE_AUDIT.md`, `_INDEX_READINESS.md`, `_SYSTEMATIC_SWEEP.md` | per-country audit, readiness and the committed search plan |

## Groups

```python
GROUPS = {
    "gulf_littoral": {"kind": "geographic", "slug": "gulf", "context": "global/gulf.json", "members": (...8...)},
    "gcc":           {"kind": "membership", "members": (...6...)},
    "opec":          {"kind": "membership", "members": (...4...), "as_of": "2026-11-11", "former_members": {...}},
}
```

- The manifest emits `groups` (label, kind, note, slug, context, members in the registry's
  alphabetical order) and each system's `regional_groups`. The frontend reads those; it has no
  list of Gulf countries.
- A group with a `slug` and a `context` file has a page at `?group=<slug>`. A membership has
  neither: it is a filter on the home page and inside the Gulf overview.
- No group has an index, a headline, a count or any rankable figure. Tests hold the manifest's
  group entries to exactly six keys.

## Campaign classification (fails closed)

`conflict_campaigns.json` → `system_states[<id>]` is one of `ACTIVE_KINETIC_CAMPAIGN`,
`RECENT_ENDED_CAMPAIGN`, `NO_ACTIVE_CAMPAIGN`, `UNCERTAIN`, each with a dated basis.

- Every Gulf system must have one. A missing one fails the build.
- `UNCERTAIN` restricts exactly as active does. A restricting state with no campaign entry that
  applies the policy fails the build.
- What withholds is a campaign's `policy_applied`, not its `status`. An active or uncertain
  campaign cannot switch it off; an ended one keeps it until `release_after_end_days` have passed.
- A covered record publishes that the event occurred, its date, class, place at the precision the
  system allows, and the effect reported at the time. Its recovery block is the withheld marker,
  it has no end date, and a citation whose address or headline states restart or repair is not
  published (English, Arabic and, since this iteration, Persian wording).

States on 2026-11-11: Iran, Iraq and Saudi Arabia active; Bahrain, Kuwait, Oman, Qatar and the UAE
uncertain. Iran's rule starts at June 2025 and Iraq's at 2022, because sites struck earlier were
reported struck again: an old record's recovery would be a current target's status.

## Precision policy (admin-1 is a maximum)

`system.json` → `geography.precision_policy`:

```json
{"kinetic": "country" | "admin1", "other": "country" | "admin1", "no_event_units": ["..."], "reason": "..."}
```

| System | Attacks and sabotage | Other events | Why |
|---|---|---|---|
| Bahrain | country | country | about 780 square kilometres; the map source draws governorates abolished in 2014 |
| Iran | country | province | strikes are being reported now |
| Iraq | country | governorate | changed after the research wave: where most attacks were reported, a governorate and a class name one facility |
| Kuwait | country | governorate | facilities sit in two or three governorates |
| Oman | country | governorate | each coastal governorate holds one port-industrial area |
| Qatar | country | municipality | two industrial cities hold most of the system |
| United Arab Emirates | country | emirate | five small emirates; publishing some and not others would show which |
| Saudi Arabia | region | region | unchanged; no policy block, existing records untouched |

Under `kinetic: "country"` a record has no region, no facility name, no operator, and an id of the
form `<cc>-<date>-<class>-attack-<n>` that names nothing. The import gate does the downgrade, so no
later step has to remember to; the build refuses a record that escaped it; and a record whose
summary or effect names its facility is held. A citation whose address names the place, the
operator or the method is not published, nor is a short link. **Residual, stated:** the page
behind a published citation is a public news report and names the place. The record does not
repeat it; the link is still a link.

The UAE's two areas that Natural Earth labels "Neutral Zone" are drawn and listed in
`no_event_units`: no record is ever placed there. Iran's and the UAE's disputed islands are never
an analytic unit of either system; the ruling text is sovereignty-neutral and follows the Crimea
and China precedents (Natural Earth's line of actual control, stated as an analytic choice).

## Iran's province codes

Natural Earth carries the ISO 3166-2:IR numbering from before November 2020. All but two codes
mean a different province today, and Alborz shares Tehran's. Units are moved to the current codes
by name (`NAME_CODE_FIXES`); a unit the table misses fails the build instead of keeping its old
code, which would be another province's.

## Calendars, numerals, original titles

- `pipeline/calendars.py` converts Solar Hijri dates exactly and Hijri dates by the tabular
  calendar, which can differ by a day from an observed date; the `conversion_basis` says so.
- A year outside 1900-2100 is refused as Gregorian. `1404` is never a Gregorian year.
- `parse_number` reads Persian and Arabic digits and separators and returns nothing for an
  ambiguous string such as `1,5`.
- A record converted from another calendar keeps `source_date_text`, `date_calendar` and
  `conversion_basis`. The import gate recomputes the conversion and holds a mismatch.
- A non-English citation keeps `title_original` and an English gloss `title_en`, shown with the
  right text direction. Titles are dropped for campaign-covered records: a headline is where a
  publisher puts the status.

## Maturity

`system.json` → `maturity` is `monitored` or `research_preview`. All seven new systems are
previews: one overnight pass, most official sites unreadable from here, a search allowance that
ran out. The label is on the card, the country page and the regional brief. An empty record reads
"No qualifying records in the current reviewed corpus", never "0 disruptions".

## What the daily refresh does with all this

Nothing new. The scheduled job rebuilds payloads from curated files. It does not research, does
not re-check campaign status, and does not fetch any Gulf source. `campaign_problems` runs in
every build, so a stale or contradictory register stops the refresh rather than publishing.

## What was not built, by design

No Gulf index, no ranking, no facility layer, no route or strait or shipping view, no dependence
or importance measure, no export-route or bypass analysis, no interconnector status, no nuclear
fuel-cycle or site status, no economic-impact model. `docs/GULF_ENERGY_CONTEXT.md` lists what the
overview may and may not hold; the tests in `tests/test_iteration19.py` hold it there.

## Changes after the release reviews

Five independent reviews read the release candidate (safety, methodology and sources, geography,
test architecture, and a first-time reader). The record fields held. What they found was in text
that sits around the records and that no gate read. Each is now a rule with a test:

- **Campaign bases** (`conflict_campaigns.json`) say only that attacks are reported. Status
  sources are a publisher and a date. `build_systems.campaign_text_problems` stops the build
  otherwise.
- **Research-log notes** are fixed sentences (`write_gulf_pass.LANE_NOTES`), chosen by what the
  researcher's note mentions. The note itself is never published. Two word-list filters had each
  let paraphrase through.
- **`review_edits.json`** keeps only the final text for systems under the campaign policy
  (`apply_reviews.py --collapse`, run by every apply).
- **The gate** refuses a short link as the citation of a record published without its place, reads
  addresses against every name a unit goes by (`geography.display_names`, `unit_aliases`), shows a
  headline with its gloss or not at all, and imports an iteration-19 record only with three
  confirmations.
- **Units where no record can be placed** serve `records_placed: false` and no count.
- **The regional list** places a campaign-covered record at country level and carries row keys.
- **An attack record published for the country is its own episode.**
- **Display names.** Natural Earth's file carries a former name for one governorate and unusual
  spellings for others. `geography.display_names` gives the name shown; the code never changes,
  and a ruling says what the map file calls it.
- **The overview map** keeps a monitored country's sizeable detached parts, which simplification
  used to drop.

`docs/ITERATION_19_REVIEW.md` §24 lists what the reviews found that was not changed, and why.
