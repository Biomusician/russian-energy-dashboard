# Energy Disruption Monitor — project instructions

Project-level rules. These override `~/.claude/CLAUDE.md` where they conflict.

## What this is

An open-source-only dashboard tracking publicly reported degradation of energy
infrastructure in western Russia and Belarus, aggregated to administrative region,
2022–present. It is a **research and monitoring instrument whose main product is
calibrated honesty about what is and is not known**, with a good map attached.

Read [docs/METHODOLOGY.md](docs/METHODOLOGY.md) before changing anything that produces a
number.

## SCOPE BOUNDARY — never relaxed

This models **publicly reported disruption to energy infrastructure, aggregated to
administrative region**. It is not, and must never become, a targeting or operational
tracking tool.

Never build or populate: current unit positions; readiness or force status; ammunition
or fuel state; vulnerability or defensive-gap assessment; target prioritisation or
ranking of undamaged assets; strike planning; ingress/egress routing; range-to-target
data; or building-level coordinates for sensitive facilities.

Specific consequences already implemented — do not undo them:

- The upstream Wikipedia strike table publishes a **"Distance (km)" column** giving
  range from Ukrainian-controlled territory. The parser deliberately does not read it.
- **Incident records never carry coordinates.** Events are region-scoped.
- `tests/test_pipeline.py` fails the build if a range-to-target field or an incident
  coordinate appears in emitted data. **Do not defeat these tests.**
- Occupied Ukrainian territory is excluded from the region set, with a test.

Sources are public, open and unclassified, always.

## The rule that governs every design decision

**Never present an estimate as an observation.** If the data does not support a number,
emit `null` and make the UI say why.

This is the project's whole point and it has already shaped the architecture:

- The index measures **exposure**, not capacity loss, because open reporting does not
  support a loss figure. Do not "improve" it into a loss estimate.
- Sectors with no capacity denominator are **excluded from the composite and the weights
  renormalised** — never counted as zero. Zero would mean "measured, nothing wrong".
- Effect categories that cannot be derived render as **"not modelled" with a reason**,
  never as a blank row and never as a plausible-looking guess.
- Where a source says a facility was hit "at least 16 times" without listing dates, only
  the extractable dates become events. The remainder is recorded as a known undercount.
- The dashboard states its own **coverage ratio** and **quantified-capacity ratio** in
  the top ribbon, at the same visual weight as the headline index.

Distinguish three absences and keep them distinct: **unknown**, **not applicable**, and
**not yet researched**.

## Data is reproducible from source

`data/curated/` is the truth. `data/processed/` is a build artifact — committed only
because Vercel builds the frontend alone and has no Python. **Never hand-edit processed
JSON**; fix the curated source or the pipeline and rebuild.

`data/raw/` is gitignored: large, regenerable, third-party licensed.

Every scoring parameter lives in `methodology/scoring.json`. Never hardcode a weight,
half-life or sector definition into Python or a component.

## Architecture decisions already made

Do not re-litigate without a good reason:

- **Stdlib-only ETL.** No pandas, geopandas, shapely, requests. Point-in-polygon,
  Douglas–Peucker and wikitext parsing are each a few dozen readable lines. The
  scheduled GitHub Action needs no toolchain and cannot break on a wheel.
- **No database.** ~1,600 assets and ~130 events. Static JSON is the backend.
- **No basemap.** The choropleth is the map. Zero external network requests at runtime,
  no API key, no tile bill. This also rules out MapLibre symbol layers, which need an
  external glyph endpoint — region names go in the hover card and dossier.
- **Taxonomy is data.** Asset classes, sectors and causes come from `taxonomy.json`. The
  frontend never hardcodes them.

## This machine

Windows 11. PowerShell primary, Git Bash available — different syntax, don't mix. Paths
contain spaces; quote them.

| Thing | Path | Notes |
|---|---|---|
| Python | `.venv\Scripts\python.exe` | 3.13. **Never** bare `python` — three are on PATH |
| Node | `scripts\node.cmd` | v24, portable, not on PATH, gitignored |
| npm | `scripts\npm.cmd` | 11.17 |
| Dev server | `cd web && ..\scripts\npm.cmd run dev` | port 5178 |

### Encoding — this bites silently

Python's preferred encoding here is **cp1252**, not UTF-8, and this dataset is full of
Cyrillic. Every file read/write **must** pass `encoding="utf-8"` explicitly or content is
corrupted with no error raised. There is a test enforcing it. When printing diagnostics
to the console, set `PYTHONIOENCODING=utf-8` first.

## Working style

- Boring, flat, readable. Plain functions over classes. Comments explain *why*.
- Run `python -m pytest` and exercise the actual dashboard before claiming anything
  works. A passing suite is not proof the feature works.
- When a source is malformed, **flag it into `parser_warnings`** — never guess at column
  alignment. There is precedent: one strike-table row is genuinely broken and is handled
  this way.
- Keep [docs/MVP_REVIEW.md](docs/MVP_REVIEW.md) honest. It is the document a reader
  should trust most.
