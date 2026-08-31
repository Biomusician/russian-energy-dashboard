# Pipeline & infrastructure source audit

Every source evaluated for iteration 9, with what it can and cannot do, and — the part that
decides adoption — **what its licence actually says**. Verified against primary pages during the
iteration. Where a claim could not be verified at the source it is marked **UNVERIFIED** rather
than guessed: a wrong licence claim is worse than an admitted gap.

The governing rule (§28): *publicly downloadable is not the same as freely redistributable.*

## Matrix

| Source | Coverage | Geometry | Topology | Capacity / flow | Status | Cadence | Licence | Machine access | Auth | Adopt? | Role |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **OSM via Overpass — route relations** | Eurasia; 478 pipeline route relations, 9,024 member ways | **Traced centrelines** | Relation membership = route identity | no | tags only | continuous | ODbL | yes, 21.7 MB / ~30 s | none | **ADOPTED — primary** | Route geometry + identity |
| **OSM via Overpass — named ways** | same corridor | traced | none (name grouping only) | no | tags only | continuous | ODbL | yes | none | **ADOPTED — secondary** | Routes with no relation |
| Geofabrik OSM PBF extracts | same data | same | same | no | — | daily | ODbL | yes, multi-GB | none | **REJECTED** | Cost without benefit — see below |
| **GEM GGIT** (gas pipelines) | global; Nov 2025 release | GeoJSON/GeoPackage/shapefile, **with `RouteAccuracy`** | project grouping | length, diameter, capacity | 8-value vocabulary | ~2×/yr | **CC BY 4.0 (verified verbatim)** | **form-gated**, no API | name/email/org/use statement | **ADOPT — manual acquisition** | Route quality, canonical identity, gap fill |
| **GEM GOIT** (oil/NGL pipelines) | global; June 2026 release | GeoJSON/GeoPackage (**not** xlsx) | project grouping | as above | as above | ~2×/yr | **CC BY 4.0** | form-gated | as above | **ADOPT — manual acquisition** | as above |
| GEM public CDN map GeoJSON | global | full routes | project id | capacity | status | per release | CC BY 4.0 (by extension) | yes, ~200 MB/file | none | **NOT USED** | Lacks `RouteAccuracy` — see below |
| GEM `goit-ggit-pipeline-routes` GitHub repo | 4,397 gas + 2,095 liquid route files | full routes | ProjectID | no | no | per release | **NO LICENSE FILE** | yes | none | **NOT USED** | Licence ambiguity |
| **ENTSOG Transparency Platform API** | EU + neighbours: 1,184 interconnections, 788 points, 552 operators, 48 zones | **none** (`tpMapX/Y` are schematic, NOT lat/lon) | **operator ↔ point ↔ balancing zone, EIC-coded** | technical/available capacity, physical flow | validFrom/validTo | continuous | Use + dated attribution; **redistribution unaddressed** | yes, JSON/CSV/XLSX | **none** | **ADOPT — derived only** | European topology validation |
| ENTSOG/GIE System Capacity Map (XLSX) | 245 cross-border/IZ/LNG rows | none | same model + capacity | technical physical capacity GWh/d | editioned | annual | entsog.eu terms (restrictive) | yes, direct XLSX | none | **Cross-check only** | Independent check on the API |
| ENTSOG System Development Map | historic | visual only | — | — | discontinued | — | entsog.eu terms | PDF only | none | **REJECTED** | Superseded, no dataset |
| **GIE Storage Database** | 332 European UGS facilities | **none** | no | working gas TWh, injection/withdrawal GWh/d, storage type | operational/construction/planned | ~2×/yr | gie.eu terms (restrictive); AGSI grant may not reach it | yes, direct XLSX | none | **DEFER to inventory pass** | Underground storage context |
| **GIE LNG Database** | 80 European terminals | **none** | no | send-out, storage, ship class | as above | ~2×/yr | as above | yes, direct XLSX | none | **DEFER to inventory pass** | LNG reconciliation |
| GIE AGSI / ALSI API | daily storage & LNG inventory | none | no | daily fill, net withdrawal | live | daily | **"used or repackaged in any way you see fit"** + attribution | yes | **API KEY REQUIRED** | **REJECTED** | Best licence here, but a key breaks "rebuildable by anyone" |
| Gazprom project pages | Russian gas systems | schematic maps only | **named junctions, endpoints** | length, capacity | operator-stated | irregular | © operator, not licensed for reuse | no (unreachable from CI) | none | **Reference only** | Topology assertions, cited not copied |
| Transneft / CPC / operator pages | Russian oil systems | schematic only | named junctions | length, capacity | operator-stated | irregular | © operator | partial (cpc.ru reachable) | none | **Reference only** | Topology assertions |
| National TSOs (GAZ-SYSTEM, Eustream, Bulgartransgaz, BOTAŞ, MOL) | border points | none | **border-crossing points** | capacity | **authoritative on status** | irregular | © operator | partial | none | **Reference only** | Border topology + status |
| U.S. EIA country analysis | Russia energy overview | none | corridor-level | aggregate | analytic | irregular | US Gov, public domain | yes | none | **Reference only** | Corroboration |
| WRI Global Power Plant Database | 569 RU+BY plants | point coords | — | MW, fuel | **NO STATUS FIELD** | **frozen 2022-01-26** | CC BY 4.0 | yes, direct CSV | none | **DEMOTE — see §23 finding** | Legacy cross-check |
| GEM power trackers (GIPT/GCPT/GOGPT/GNPT) | RU + BY, unit-level | point coords + precision flag | — | MW, status, owner | 8-value vocabulary | rolling | CC BY 4.0 | form-gated | as above | **Recommend, next iteration** | Generation inventory |
| GEM Global Coal Mine Tracker | Aug 2026; RU 453 Mtpa operating | point coords | — | production Mtpa, ownership chain | status vocabulary | annual | CC BY 4.0 | form-gated | as above | **Recommend** | New coal-mine inventory |
| GEM Global Coal Terminals Tracker | **Dec 2024** (page claims Jan 2026 — wrong) | point coords | — | nameplate Mtpa | status | stalled | CC BY 4.0 | form-gated | as above | **Recommend w/ vintage warning** | Coal terminals |
| NASA FIRMS (VIIRS/MODIS) | global thermal anomalies | detections | — | FRP/brightness | NRT ≤3 h | continuous | NASA open / CC0 | yes | **free key required** | **DEFER — see §25 finding** | Incident corroboration only |
| Copernicus Data Space (Sentinel) | global imagery | full EO | — | — | 5-day | continuous | Free, full and open | search yes, **download needs OAuth2** | yes | **REJECTED this iteration** | Damage assessment = out of scope |
| Kpler / Vortexa / Wood Mackenzie / S&P / commercial AIS | — | — | — | — | — | — | proprietary | — | paid | **REJECTED** | Cannot be a hidden dependency (§27) |

## The decisions that mattered

### Overpass relations, not a PBF extract

The whole pipeline-relation corpus for the Europe–Far East corridor is **21.7 MB and fetches in
about 30 seconds**, plus 2.5 MB of member-way tags. A Geofabrik path would mean multi-GB country
extracts, a compiled parser dependency (pyosmium/libosmium) on a Windows-primary machine that
currently needs no build toolchain, and minutes of CI time — to obtain the same relations. PBF
would only win if we needed the *whole* map; we need one tagged relation type. **Rejected on
cost, not capability.**

### GEM: licence is clean, access is not

The download form's mandatory checkbox links to GEM's licence page, which carries the **verbatim,
unmodified CC BY 4.0 International Public License** with no NonCommercial, NoDerivatives or
ShareAlike rider. CC BY 4.0 §2(a)(1)(A) and §4 permit reproduction and sharing including database
rights, and §2(a)(5)(B) forbids imposing further restrictions downstream — so **raw redistribution
is permitted with attribution**, and the site footer's generic "All Rights Reserved" does not
override the dataset-specific grant.

The obstacle is *access*, not licence: acquisition is a form requiring a name, email, organisation
and a ≥100-character statement of intended use, returning a client-zipped bundle. There is no API
and no stable file URL. Scripting that flow would be circumventing an access control, so it is not
automated.

Two ungated GEM paths exist and were deliberately **not** used:
- the public CDN map GeoJSON (~200 MB per tracker) carries full route geometry but **no
  `RouteAccuracy`, no length, no diameter** — it is a display subset. Without `RouteAccuracy` a
  route's quality cannot be labelled honestly, and labelling everything `generalized` would be as
  wrong as labelling it `mapped`.
- the `goit-ggit-pipeline-routes` GitHub repo has **no LICENSE file**, and at least one route file
  (`gas-pipelines/P0271.geojson`) contains `osm_id`/`tiger:*` tags, i.e. re-imported OSM under a
  share-alike licence. Using it would mean asserting a licence GEM has not stated on that repo.

**Adopted procedure** (`data/vendor/gem/`): an analyst completes the form once per release,
records SHA-256 of every file, commits the attribute table plus a Russia-scoped derived GeoJSON,
and records release label, acquisition date, citation string and licence in a manifest. CI
verifies checksums and rebuilds deterministically; it may poll GEM's public bucket listing to
detect a newer release and **fail loudly asking a human to refresh**, but never fetches the gated
file itself. `RouteAccuracy` maps onto route quality as
`high → gem_traced`, `medium|low → gem_generalized`, `very low (straight line/schematic)|no route
→ topology_only or excluded`.

### ENTSOG proves operator topology, not pipeline topology

This is the finding that reshaped the ENTSOG plan. The API is genuinely excellent — key-free,
CORS-open, EIC-coded, explicitly blessing automated access (T&C Art. 5.7) — but **there is no
pipeline entity anywhere in its model**. Mallnow returns:

```
GASCADE Gastransport (DE) [DE THE BZ] <--> Mallnow ITP-00096 <--> GAZ-SYSTEM (PL) [TGPS (YAMAL)]
infrastructureLabel: "Transmission"        <- generic, not a pipeline name
```

The string "YAMAL" appears only inside a Polish *balancing zone* label, which is an accident of
zone naming, not a general capability — there is no equivalent handle for Nord Stream, TurkStream
or Brotherhood. So ENTSOG can support `OPERATOR_A connects_to OPERATOR_B at POINT_X` and must
never be forced into `PIPELINE_A connects at POINT_X`. Any pipeline↔point mapping is **our own
sourced editorial claim**, not ENTSOG data — exactly the trap §14 warned against.

Second trap: `tpMapX`/`tpMapY` are **schematic layout coordinates**, not geography. Mallnow
returns (−7.12, −1.58) against a real position near 52.3°N 14.5°E. They must never be treated as
lat/lon.

Licence: the Transparency Platform T&C permit use and require the attribution
`ENTSOG TP [DD-MM-YYYY] https://transparency.entsog.eu/` including the extraction date, but are
**silent on redistribution** — and the separate entsog.eu website terms are much stricter.
Treated as **derived-only**.

### Russian operator sources: topology yes, geometry never

Operator and TSO publications yielded **54 machine-usable connection assertions**, each a named
point with a source URL (recorded in `data/curated/pipeline_topology.csv`). They are evidence
class E/F in the connection hierarchy: they can establish that two systems meet at Sosnogorskaya
CS or that Druzhba splits at Mozyr, but they **cannot supply a route** — a schematic operator map
is schematic topology, and tracing a line from prose would be inventing geometry.

Three cautions came out of that research and are worth carrying:
- **GEM's wiki status fields are stale.** It reports Ukraine transit as operating in August 2026;
  transit through Sudzha stopped 1 January 2025 and Eustream confirms the Veľké Kapušany halt.
  Where a tracker and a TSO disagree about status, the TSO wins.
- **Status must be modelled separately from existence.** Yamal–Europe and the Brotherhood corridor
  are physically intact and carrying zero contracted transit. A schema that collapses those two
  facts gets both wrong.
- **Names mislead.** Ukhta–Torzhok terminates at Novogryazovetskaya/Gryazovets, not Torzhok. CPC's
  Novorossiysk terminal (Yuzhnaya Ozereyevka) is a separate node from Transneft's Sheskharis.

### Why several good sources were still not adopted now

- **GIE Storage/LNG**: right fields, direct download, no key — but **no coordinates at all**, so
  they are an inventory pass (a new context asset class) rather than anything the network layer
  can consume. Deferred deliberately, not rejected.
- **AGSI/ALSI**: the most permissive licence in this whole audit, and rejected anyway, because a
  personal API key is incompatible with "rebuildable by anyone from public sources". An
  optional-key feature that degrades gracefully would be the honest way to add it later.
- **Copernicus/Sentinel**: legally and technically available. Rejected on scope: Sentinel-2 SWIR
  and Sentinel-1 change detection do not corroborate reporting, they **assess damage** — an
  original imagery-derived judgement about the physical state of a named installation, which is
  precisely what the scope boundary excludes.
- **NASA FIRMS**: licence is open (NASA CC0) and would even permit republishing raw detections.
  Deferred anyway, because corroborating "refinery X burned on date D" requires querying a
  bounding box around refinery X — reintroducing the facility-precision geometry this project
  deliberately does not hold — and because a scheduled sweep over a facility list would be a
  strike-detection pipeline whatever the output column is called. If it is ever built it must be
  analyst-invoked per incident, restricted to incidents already in the curated corpus with a
  source URL, and must persist no coordinates.
