# Global geography — sources, licences, disputed territory, size budget

Status: **research and recommendation, 2026-10-30.** No pipeline code has been changed. This
document decides where the geometry for the five-country extension (China, United States,
Saudi Arabia, Canada, India) comes from, under what licence, how heavy it is, and how disputed
territory is handled. It feeds item 1 of the onboarding gate in
[GLOBAL_METHODOLOGY.md §7.2](GLOBAL_METHODOLOGY.md) ("admin-1 geometry and source, plus an
explicit ruling on disputed or occupied territory, in the style of the Crimea rule").

Every number below was measured, not estimated, unless it says otherwise. How it was measured
is in §8.

---

## 0. The short version

| Layer | Recommended source | Licence | Size shipped (raw / gzip) |
|---|---|---|---|
| World countries (always loaded) | Natural Earth **1:110m** admin-0, default edition | Public domain | 174 KB / 54 KB |
| Per-country context frame (lazy) | Natural Earth **1:50m** admin-0, clipped to the country frame (the method the Russia view already uses) | Public domain | 7–27 KB gzip each |
| Admin-1, all five countries (lazy, per country) | Natural Earth **1:10m** `admin_1_states_provinces`, default edition: the file the Russia layer already uses | Public domain | 8–144 KB gzip each (table in §4) |
| Hong Kong, Macau outlines | Natural Earth 1:10m admin-0 (`HKG`, `MAC`), not the 18 Hong Kong district polygons | Public domain | < 1 KB gzip each |
| Disputed-area overlay | Natural Earth 1:10m `admin_0_disputed_areas`, filtered to the 16 relevant features | Public domain | 26 KB / 7 KB |

- **Use one global source, Natural Earth, for every layer.** It is adequate for all five
  countries once the four known defects below are corrected with a curated crosswalk. It is
  public domain, so nothing blocks redistribution from a public repo. It already sits under the
  Russia layer, so borders between countries come from the same linework.
- **GADM is ruled out.** Its licence forbids redistribution without permission, and this repo
  redistributes the processed geometry (§2.3).
- **geoBoundaries is not a drop-in alternative for India or China.** Its India file draws India's
  claimed boundary and its China file draws Taiwan as a Chinese province. Using either would
  take a side on sovereignty (§2.2).
- **Use the default (de facto) edition. Never use a point-of-view edition.** Mark disputed areas
  with a separate neutral overlay. Carry sovereignty, administration and claims as separate fields
  on each affected unit, generalising the Crimea model. Never let geometry alone place an
  incident in a disputed unit (§3).
- **Join on a curated canonical code (ISO 3166-2 where valid).** Never join on Natural Earth's
  `code_hasc` or `postal`: for China they collide with ISO codes and point to *different
  provinces* (§5).
- **One existing bug blocks a US build.** `geo.simplify_geometry` drops any ring that simplifies
  to fewer than 6 points. That deletes **Wyoming and Colorado** at every tolerance tested (§7, risk 1).

---

## 1. Admin-0 (world context)

### 1.1 Licence

Natural Earth is public domain. The terms page says: "All versions of Natural Earth raster +
vector map data found on this website are in the public domain", and "No permission is needed
to use Natural Earth. Crediting the authors is unnecessary."
- <https://www.naturalearthdata.com/about/terms-of-use/>
- The repository carries the same wording: <https://github.com/nvkelso/natural-earth-vector/blob/master/LICENSE.md>

**Version.** The download pages list 5.1.1. The latest GitHub release is
**v5.1.2 (2022-05-13)**. The last commit to `master` was **2022-06-02**, and `master/VERSION`
reads `5.2.0-pre` (GitHub API, checked 2026-10-30). In practice the dataset has been **frozen
since mid-2022**, and §7 lists what that leaves stale. `build_regions.py` and `build_context.py`
fetch from `master`, which is unpinned. Pin them to the `v5.1.2` tag or a commit SHA so that a
future upstream change cannot silently move a border.

### 1.2 Measured sizes

Simplification uses the project's own `geo.simplify_geometry`. The emitted JSON is compact,
carries minimal properties (`code`, `name`, `labelrank`) and is gzipped at level 9.

| Edition | Features | Source vertices | Published GeoJSON | Simplification | Raw | Gzip | Units lost to simplification |
|---|---|---|---|---|---|---|---|
| 110m | 177 | 10,654 | 819 KB | none, 2 dp | 174 KB | 54 KB | 0 |
| 110m | 177 | | | 0.05°, 2 dp | 160 KB | 49 KB | 0 |
| 50m | 242 | 99,613 | 3,011 KB | 0.05°, 2 dp | 440 KB | 142 KB | 23 (Singapore, Bermuda, Jersey…) |
| 50m | 242 | | | 0.1°, 2 dp | 346 KB | 109 KB | 15 (incl. **Bahrain**, Guam) |
| 10m | 258 | 548,471 | 12,976 KB | 0.05°, 2 dp | 1,087 KB | 292 KB | 26 (incl. **KAS/Siachen**) |

### 1.3 Recommendation: 110m for the world, 50m frames per country

- **World view: 110m, unsimplified, 2 decimal places, about 54 KB gzip.** At world zoom it
  is already coarser than a screen pixel and needs no further simplification.
- **Country view: a 50m admin-0 context frame per country,** clipped with the same bounding-box
  filter `build_context.py` uses for Russia, and lazy-loaded with that country's admin-1. Each
  frame is 7–27 KB gzip (§4).

110m alone is not good enough below world zoom. It omits small states (Bahrain, Singapore),
folds Hong Kong into China, and is coarse enough to **move disputed places across borders**:

| Place | 10m default | 50m default | 110m default |
|---|---|---|---|
| Demchok | India | **China** | **China** |
| Tawang (Arunachal) | India | India | **Bhutan** |
| Siachen Glacier | KAS (indeterminate) | KAS | **Pakistan** |
| Hong Kong | HKG | (water/gap) | **China** |

That table is the empirical case for rule D3 in §3: **world geometry is display-only, and no
scale of it may ever be used to assign anything.**

---

## 2. Admin-1 for the five countries

### 2.1 Natural Earth 10m `admin_1_states_provinces`: unit-by-unit audit

Source file: `geojson/ne_10m_admin_1_states_provinces.geojson` from
github.com/nvkelso/natural-earth-vector (`master`, byte-identical to the copy already in
`data/raw/ne_10m_admin_1.geojson`, 40.7 MB). Every feature carries `iso_3166_2`, `adm1_code`,
`ne_id`, `name`, `name_en`, `name_alt`, `name_local`, `name_zh`, `name_zht`, `name_ar`,
`name_fr` and about 30 other name fields, plus `FCLASS_*` worldview fields.

| Country | NE features | Expected | `iso_3166_2` present and well-formed | Verdict |
|---|---|---|---|---|
| **United States** | 51 | 50 states + DC | 51/51 (`US-AK`…`US-WY`, `US-DC`) | **Adequate.** Territories (Puerto Rico, Guam, USVI, American Samoa, N. Marianas, minor outlying islands) are *separate admin-0 units* in NE (`PRI`, `GUM`, …), not part of `USA`. See the scope decision in §7. |
| **Canada** | 13 | 10 provinces + 3 territories | 13/13 | **Adequate.** `code_hasc` for Newfoundland and Labrador is the obsolete `CA.NF`; ignore HASC. |
| **China** | 32 | 31 provincial-level (mainland) + HK + MO | 31/32. The extra feature is **Paracel Islands, `CN-X01~`** (a non-ISO NE placeholder). | **Adequate after corrections.** Hong Kong is a separate admin-0 (`HKG`) with **18 district features** (`HK-X01~`…`HK-X18~`, non-ISO). Macau is admin-0 `MAC`, one feature `MO-M`. Taiwan is admin-0 `TWN` with 21 county-level features (`TW-*`), separate from China. |
| **India** | 36 | 28 states + 8 UTs | 36/36 well-formed, but **4 codes are stale** (below) | **Adequate after corrections.** It **does reflect** the 2019 reorganisation (`IN-JK` typed Union Territory, `IN-LA` Ladakh present) and the 2020 merger (`IN-DH` "Dadra and Nagar Haveli and Daman and Diu"; no `IN-DN`/`IN-DD`). |
| **Saudi Arabia** | 13 | 13 regions | 13/13: `SA-01`…`SA-12`, `SA-14`. ISO has **no SA-13**, so this matches exactly. | **Adequate.** |

**India: stale ISO codes.** ISO 3166-2:IN changed four codes on **2023-11-23**
(<https://en.wikipedia.org/wiki/ISO_3166-2:IN>, changes section). Natural Earth predates the change:

| Unit | NE `iso_3166_2` | Current ISO 3166-2 |
|---|---|---|
| Chhattisgarh | `IN-CT` | `IN-CG` |
| Uttarakhand | `IN-UT` | `IN-UK` |
| Odisha | `IN-OR` | `IN-OD` |
| Telangana | `IN-TG` | `IN-TS` |

Other India defects: `type_en` is wrong for Himachal Pradesh (tagged "Union Territory"; it is a
state) and missing for Gujarat. **Do not derive state/UT category from NE.** Carry it in the
curated crosswalk.

The 2019 and 2020 reorganisations took effect on 31 Oct 2019 and 26 Jan 2020, both before the
project's 2022 start. NE's current India unit set is therefore valid for the whole time window
and needs no date-versioned geometry.

**China: ISO.** ISO 3166-2:CN moved from numeric to letter codes on 2017-11-23
(<https://en.wikipedia.org/wiki/ISO_3166-2:CN>). NE uses the letter codes. ISO 3166-2:CN also
lists `CN-HK`, `CN-MO` and `CN-TW`. NE does not use these, because it models all three as
separate admin-0 units. §3 covers how Taiwan is handled.

**Saudi Arabia: ISO.** <https://en.wikipedia.org/wiki/ISO_3166-2:SA> lists 13 regions,
01–14 with 13 skipped. NE matches exactly.

### 2.2 Alternatives compared

| Source | Licence (verified) | Redistributable from a public repo? | Disqualifiers found |
|---|---|---|---|
| **Natural Earth 10m** | Public domain (§1.1) | **Yes**, no attribution required | Stale India codes; non-ISO pseudo-codes for Paracel, HK districts and Siachen; frozen since 2022. All of these are fixable with a crosswalk. |
| **geoBoundaries gbOpen** (licence is per file; read from the API at `https://www.geoboundaries.org/api/current/gbOpen/<ISO3>/ADM1/`) | USA: Public Domain (source US Census). CAN: **Open Government Licence – Canada 2.0** (StatCan). CHN: "Public Domain" (Wikimedia Commons). IND: **CC BY 2.5 India** (DataMeet). SAU: **ODbL 1.0** (OpenStreetMap). | Yes, but CAN and IND require attribution and SAU is **share-alike**: derived databases must stay ODbL. | **IND (tested):** Aksai Chin and Gilgit fall inside `IN-LA`, and Muzaffarabad (Pakistan-administered) inside `IN-JK`. This is **India's claimed boundary**, so it overlaps Pakistan's and China's polygons. **CHN (tested):** contains "**Taiwan Province**" plus HK and Macau. Every feature's `shapeISO` is just `CHN` (**no ISO 3166-2 codes**), and Guangdong is misnamed "**Guangzhou Province**". Boundary years run 2011–2023. |
| **GADM** | <https://gadm.org/license.html>: "freely available for academic use and other non-commercial use. Redistribution or commercial use is not allowed without prior permission." | **No.** See §2.3. | Licence alone. |
| **US Census cartographic boundary files** (<https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html>) | US federal work, public domain under 17 U.S.C. §105. geoBoundaries records it as Public Domain. **The CB page itself carries no licence statement**, and that could not be checked further in this pass (§8). | Yes | Ships as shapefile, geodatabase or GeoPackage only, **no GeoJSON**. Using it would need a stdlib shapefile reader in the ETL, and its linework would not match the NE context and Canada/Mexico neighbours. 2025 vintage at 1:500k, 1:5M and 1:20M. |
| **Statistics Canada boundary files** | Statistics Canada Open Licence (<https://www.statcan.gc.ca/en/reference/licence>): redistribution, modification and commercial use are allowed. **Attribution is mandatory**: "Adapted from Statistics Canada, *product*, *reference date*. This does not constitute an endorsement by Statistics Canada of this product." | Yes, with the attribution notice | Adds an attribution obligation, and the shapefile has to be converted. Its coastline is far denser than NE's, so it would be the heaviest file in the app. |

**Per-country recommendation: Natural Earth 10m for all five.** The reasons:

1. **Licence.** NE is the only source with no obligations at all. It is also the reason
   `build_regions.py` chose it for Russia.
2. **Consistency.** The China–Russia, US–Canada and India–China borders come from one linework
   that already matches the Russia layer. Mixing Census and StatCan files would make
   neighbouring countries disagree at their shared border.
3. **Neutrality.** NE is the only candidate whose default edition is de facto *and* that ships a
   separate disputed-areas layer to mark claims (§3). geoBoundaries IND and CHN each adopt one
   claimant's view.
4. **Adequacy.** Unit counts are correct for all five countries. The defects are code-level, not
   geometry-level, and a crosswalk fixes them.

Use the national-agency files (Census, StatCan) only if a later need for sub-state precision
justifies them. Admin-1 aggregation does not need them.

### 2.3 Why GADM is out

`data/processed/` is committed to the public GitHub repo and served by Vercel. Both are
**redistribution**. GADM's terms forbid redistribution without prior permission, and the
academic carve-out covers "maps for publishing of academic research articles", not
redistributing the data. Commercial status is irrelevant, because the redistribution clause
alone rules it out. `build_regions.py`'s docstring already reached the same conclusion for Russia.

---

## 3. Disputed and contested territory

### 3.1 What Natural Earth does by default

NE: "Natural Earth Vector draws boundaries of countries according to defacto status. We show who
actually controls the situation on the ground." It also publishes **point-of-view editions**
(`ne_10m_admin_0_countries_<pov>.geojson`). The editions in the repo are: arg, bdg, bra, chn,
deu, egy, esp, fra, gbr, grc, idn, ind, iso, isr, ita, jpn, kor, mar, nep, nld, pak, pol, prt,
pse, rus, sau, swe, tlc, tur, twn, ukr, usa, vnm. Admin-1 has no POV files. Instead it carries
`FCLASS_<pov>` attributes (for example `IN-AR` has `FCLASS_CN = "Unrecognized"`, and `KAS` is
"Unrecognized" from the CN, IN, PK, TW and NP viewpoints). The separate
`ne_10m_admin_0_disputed_areas` layer (99 features) holds each disputed polygon with a note in
the form "Admin. by X; Claimed by Y".

Measured by point-in-polygon, default edition against POV editions:

| Place | Default (de facto) | India POV | China POV | Pakistan POV | US POV | Default admin-1 unit |
|---|---|---|---|---|---|---|
| Srinagar (Indian-administered J&K) | India | India | India | **Pakistan** | India | `IN-JK` |
| Leh (Ladakh) | India | India | India | **Pakistan** | India | `IN-LA` |
| Siachen Glacier | **KAS** (indeterminate) | India | India | Pakistan | (none) | `-99-X06~` (KAS) |
| Aksai Chin | China | **India** | China | China | China | `CN-XJ` |
| Shaksgam Valley | China | **India** | China | China | China | `CN-XJ` |
| Demchok | India | India | **China** | **Pakistan** | **China** | `IN-LA` |
| Muzaffarabad (AJK) | Pakistan | **India** | Pakistan | Pakistan | Pakistan | `PK-JK` |
| Gilgit (G-B) | Pakistan | **India** | Pakistan | Pakistan | Pakistan | `PK-GB` |
| Tawang / Itanagar (Arunachal) | India | India | **China** | India | India | `IN-AR` |
| Junagadh | India | India | India | **Pakistan** | India | `IN-GJ` |
| Taipei | Taiwan | Taiwan | **China** | **China** | Taiwan | `TW-TPE` (admin-0 `TWN`) |
| Simferopol | Russia | **Ukraine** | **Ukraine** | **Ukraine** | **Ukraine** | `UA-43` (filed under `RUS`) |

Each POV edition moves several borders at once, and no two agree. **Choosing any POV edition
would adjudicate sovereignty.** The default edition makes a single statement: who administers the
ground. That is the same evidential basis the project already uses ("observed, not asserted").
The default admin-0 file files Crimea under Russia. The project already handles this by
excluding Russia from the context layer and drawing Crimea only as its own unit
(`build_context.py`). The disputed-areas layer also contains a `RUS` "Crimea" feature, which is
consistent with that treatment.

Admin-0 attribute trap: in the default admin-0 file, **Taiwan's `ISO_A2` is `"CN-TW"`** (its
`ISO_A2_EH` is `"TW"`, `ADM0_A3` is `"TWN"`). Never key country identity on `ISO_A2`. Use `ADM0_A3`.

### 3.2 Which features need a note

The list below comes from sampling each relevant disputed-area polygon on a 60×60 grid and
recording which default admin-1 unit holds each sample. It is complete for the five countries
and their immediate disputes:

| Admin-1 unit | NE disputed polygon(s) over it (share of polygon) | NE note | Needs |
|---|---|---|---|
| `IN-JK` Jammu and Kashmir | "Jammu and Kashmir" (40%) | Admin. by India; claimed by Pakistan | Dispute note. The polygon is the **Indian-administered portion only**. India's legal claim also covers `PK-JK`. |
| `IN-LA` Ladakh | "Jammu and Kashmir" (59%); "Demchok" (100%) | Admin. by India; claimed by Pakistan / by China | Dispute note. India's claim also covers Gilgit-Baltistan, Aksai Chin and Shaksgam, none of which are in this polygon. |
| `IN-AR` Arunachal Pradesh | "Arunachal Pradesh" (97%, with 2% spilling into `IN-AS`) | Admin. by India; claimed by China | Dispute note. China calls it "Zangnan" / South Tibet and claims it as part of Xizang. |
| `IN-HP` Himachal Pradesh | "Samdu Valleys" (100%); "Tirpani Valleys" (7%) | Admin. by India; claimed by China | Minor-sector note |
| `IN-UT` Uttarakhand | "Bara Hotii Valleys" (100%); "Tirpani Valleys" (92%); "Near Om Parvat" (100%) | Admin. by India; claimed by China / by Nepal (Kalapani–Lipulekh) | Minor-sector note |
| `IN-GJ` Gujarat | "Junagadh and Manavadar" (99%) | Admin. by India; claimed by Pakistan | Minor note (claim appears on Pakistan's 2020 political map) |
| `CN-XJ` Xinjiang | "Aksai Chin" (85%); "Shaksam Valley" (100%) | Admin. by China; claimed by India | Dispute note |
| `CN-XZ` Xizang | "Aksai Chin" (14%) | Admin. by China; claimed by India | Dispute note. Also note China's claim to `IN-AR`. |
| `CN-X01~` Paracel Islands | "Paracel Is." | Admin. by China; claimed by Vietnam and Taiwan | Treat as an indeterminate island unit, not a scored province (D5). |
| `-99-X06~` Siachen (admin-0 `KAS`) | "Siachen Glacier" (100%) | Claimed by Pakistan and India | Never scored (D5) |
| Taiwan (admin-0 `TWN`, 21 units) | "Taiwan" | Self-administered; claimed by China | Separate admin-0. Never part of China (D6). |
| Hong Kong (`HKG`), Macau (`MAC`) | none | (Chinese SARs; sovereignty undisputed) | Administration note only (D7) |
| `PK-JK`, `PK-GB` (context only) | "Azad Kashmir", "Gilgit-Baltistan" (100%) | Admin. by Pakistan; claimed by India | Note, if Pakistan context is ever labelled |
| `SA-04` Eastern Province | none | NE attribute note: "Kuwait-SA neutral zone divided, part went to Eastern Province." | **Attribution note, not a dispute.** The former Saudi–Kuwaiti Neutral Zone is partitioned on the map: Khafji tests into `SA-04`, Wafra into `KW-AH`. Oil production there is shared between the two states (background knowledge, not re-verified here), so an incident at Khafji or Wafra affects both countries' output even though the geometry gives it to one. |
| Saudi Arabia, other | "Tiran and Sanafir Is." lies in `EG-JS` (Egypt), not in any Saudi unit | Admin. by Egypt; claimed by Saudi Arabia | No Saudi unit affected. NE predates or does not reflect the 2016 Egypt–Saudi transfer agreement; status not re-verified. The Saudi–Yemen line (2000 Treaty of Jeddah) and Saudi–UAE line have **no disputed polygon in NE**. Note that the Saudi–Yemen border is an active cross-border strike zone, so attribution there must come from text, never from geometry. |
| US, Canada | none in admin-1 | n/a | Machias Seal Island / North Rock, Beaufort Sea, Dixon Entrance and Strait of Juan de Fuca are maritime or islet disputes that **no NE polygon represents**. NE's "Hans Island" feature (admin. by Denmark, claimed by Canada) **is stale**: the island was divided by the 2022 Canada–Denmark agreement, after NE's last commit. It touches no Canadian admin-1 unit. US-administered islets with foreign claims (Navassa, Wake, Swains, Bajo Nuevo, Serranilla) are outside the 50+DC scope. |

### 3.3 Recommended policy

This generalises the Crimea model (`config.SPECIAL_UNITS`, METHODOLOGY §5a) from a one-off into
a schema. The aim is that **the map shows who administers the ground and who claims it, and
never decides between them**.

**D1. Geometry basis.** All geometry comes from Natural Earth's **default (de facto)** editions.
Never use a POV edition, and never mix editions or scales for one boundary. Record
`geometry_basis: "natural_earth_default_de_facto"` in `data_manifest.json` and show it in the
dossier footer. Add a test that fails if any `_<pov>` file is fetched.

**D2. Status fields on every unit.** Every unit gets the same fields. They are null or "none" for
undisputed units, and they live in `regions.json` metadata, not in the geometry file:

| Field | Meaning | Crimea today | `IN-AR` | `CN-XJ` | Siachen |
|---|---|---|---|---|---|
| `sovereignty_recognised` | Majority international recognition, or `"no settled consensus"` | "Ukraine" | "India" (see note on wording) | "China" | "no settled consensus" |
| `administered_by` | De facto administration | "Russia (occupying)" | "India" | "China" | "contested military control (India)" |
| `claimed_by` | Other claimants, as a list | ["Russia"] | ["China"] | ["India"] (Aksai Chin, Shaksgam sub-areas) | ["India", "Pakistan"] |
| `dispute_class` | `none` · `occupied` · `administered_disputed` · `separately_governed_claimed` · `indeterminate` · `special_administrative_region` | `occupied` | `administered_disputed` | `administered_disputed` | `indeterminate` |
| `disputed_share` | `whole` / `part` (which NE disputed polygon) | whole | whole | part | whole |
| `analytic_scope` | `aoi` · `occupied` · `disputed` · `context` · `excluded` (drives styling, as it does for Crimea) | `occupied` | `aoi` | `aoi` | `excluded` |
| `aggregate_included` | Analytic inclusion in the country aggregate. Explicitly *not a statement about sovereignty*. | true | true (owner decision) | true (owner decision) | false |
| `status_note` | Plain-language text for the dossier | (existing) | e.g. "Administered by India. Claimed by China. Inclusion in India's aggregate reflects administration of the grid, not a view on sovereignty." | similar | similar |

`sovereignty_recognised` should not be filled in where reasonable sources disagree. In those
cases "no settled consensus" is the honest value. Kashmir is the clearest case. The
recommendation is that `IN-JK` and `IN-LA` carry
`sovereignty_recognised: "no settled consensus (UN-recognised dispute)"`, with
`administered_by: "India"`.

**D3. Geometry never assigns.** Incidents carry no coordinates (a scope boundary), so text alone
resolves them to a unit. Extend that rule to **every** geometry-based step for these countries:
- An asset point (for example from OSM) that falls inside any disputed-area polygon goes to
  `parser_warnings` and is **not** auto-assigned to a unit by point-in-polygon. A human-reviewed
  alias decides it, or it stays `disputed_unassigned`.
- The scale table in §1.3 is the evidence. Demchok is India at 10m and China at 50m and 110m.
  Geometry-only assignment is an artefact of scale.

**D4. Text resolution gets explicit dispute outcomes.** `regionmatch.resolve` needs a sixth
outcome, `("disputed_unassigned", name)`, for Siachen, Aksai Chin, Shaksgam, the Paracels and
the Spratlys. It also needs explicit alias rows so a claimant's name for a place resolves to the
**administering** unit *with* its dispute flag and is never relabelled. For example, "Zangnan"
or "South Tibet" (藏南) resolves to `IN-AR` and never to `CN-XZ`. "Pakistan-administered
Kashmir", "Azad Kashmir" or "Gilgit-Baltistan" resolve to `out_of_aoi`. "Aksai Chin" resolves to
`disputed_unassigned`, even though its geometry sits in `CN-XJ`. This mirrors the Crimea alias
check, which runs *before* ordinary matching for the same reason.

**D5. Indeterminate units are drawn but never scored.** Siachen (`KAS`) and the Paracel
Islands (`CN-X01~`) render with the neutral disputed style, have `aggregate_included: false`,
and are never ranked. The Paracels must not be scored as a Chinese province.

**D6. Taiwan is never part of China.** It stays the separate admin-0 `TWN` that NE's default
edition draws. It is not one of the five countries and is drawn as context only. ISO 3166-2:CN's
`CN-TW` code is **never** used as an identifier for Taiwan's geometry or events. Add a test that
no unit in China's set intersects `TWN` and that China's aggregate never contains a `TW-*` or
`CN-TW` code. A source reporting an event in Taiwan resolves to `out_of_aoi` until Taiwan is
deliberately onboarded as its own country.

**D7. Hong Kong and Macau** are not disputed. NE models them as separate admin-0 units because
they are administered separately. The recommendation is to show them **inside the China view** as
two provincial-level units, `CN-HK` and `CN-MO` (ISO 3166-2:CN), with
`dispute_class: "special_administrative_region"` and a note that they have their own
grids and regulators. Take their geometry from **NE 10m admin-0** (one outline each, under 1 KB
gzip), not from the 18 Hong Kong district polygons, which would need a polygon union the stdlib
ETL does not have. Whether they count toward China's aggregate is an owner decision.

**D8. Rendering.** The choropleth fills the de facto admin-1 unit. A **disputed-area overlay**
(NE `admin_0_disputed_areas`, the 16 features in §3.2, 7 KB gzip) is drawn above it with a
neutral hatch and **no fill colour from the index**. The style must differ from Crimea's
dashed violet, because "occupied" and "disputed" are different classes. Labels use the neutral
form, for example "Ladakh (administered by India)", and never a claimant's name for the unit.
Admin-1 boundaries inside a disputed area are drawn as NE draws them. The overlay, not the
boundary, carries the claim.

**D9. Aggregate inclusion is the owner's call, stated as analytic.** For
`administered_disputed` units the recommended default is `aggregate_included: true` in the
**administering** country's aggregate. The reasoning: the energy assets there are operated,
dispatched and reported inside that country's system, so they belong to its exposure picture.
This uses the same reasoning as Crimea's iteration-4 inclusion, and it gets the same caveat line
in the UI. The alternative, excluding Kashmir, Ladakh and Arunachal from India's aggregate and
Aksai Chin's host provinces from China's, is defensible too. It must be recorded in
`docs/DECISIONS.md` either way. This is the explicit ruling GLOBAL_METHODOLOGY §7.2 item 1
requires.

---

## 4. Size budget

Admin-1 sizes use the Russia layer's settings: tolerance 0.01°, 3 decimal places, compact JSON,
properties `{code, name, country, special}`, gzip level 9. They use `min_ring_points=4` (the
bug fix in §7, risk 1). With today's `min_ring_points=6`, the US file is 271 KB / 79 KB but is
**missing Wyoming and Colorado**.

**Calibration.** The current `data/processed/regions.geojson` is **432,064 bytes (422 KiB) raw,
138 KB gzip** for 80 regions. Re-running the same method on all 93 RUS+BLR features (which
includes the disabled Far East) gives 606 KB / 192 KB, so the method reproduces the existing
layer.

| Layer (lazy-loaded with the country unless noted) | Units | Tolerance | Raw | Gzip |
|---|---|---|---|---|
| **World admin-0, 110m** (always loaded) | 177 | none, 2 dp | 174 KB | 54 KB |
| Disputed-area overlay (global, 16 features) | 16 | 0.01° | 26 KB | 7 KB |
| **United States** admin-1 | 51 | 0.01° | 279 KB | 81 KB |
| US 50m context frame | 29 countries | 0.05°, 2 dp | 87 KB | 27 KB |
| **Canada** admin-1 | 13 | 0.01° | 467 KB | 144 KB |
| Canada admin-1 (recommended: Arctic archipelago) | 13 | **0.02°** | 296 KB | 93 KB |
| Canada 50m context frame | 4 | 0.05°, 2 dp | 83 KB | 26 KB |
| **China** admin-1 (31 + Paracel) | 32 | 0.01° | 223 KB | 68 KB |
| + Hong Kong, Macau (admin-0 10m outlines) | 2 | 0.01° | 2 KB | 1 KB |
| China 50m context frame | 25 | 0.05°, 2 dp | 77 KB | 25 KB |
| **India** admin-1 | 36 | 0.01° | 136 KB | 42 KB |
| India 50m context frame | 20 | 0.05°, 2 dp | 44 KB | 14 KB |
| **Saudi Arabia** admin-1 | 13 | 0.01° | 29 KB | 8 KB |
| Saudi 50m context frame | 25 | 0.05°, 2 dp | 23 KB | 7 KB |
| *Reference: Russia + Belarus `regions.geojson` today* | *80* | *0.01°* | *422 KB* | *138 KB* |

Tolerance sensitivity (raw / gzip):

| Country | 0.005° | 0.01° | 0.02° | 0.03° |
|---|---|---|---|---|
| USA | 406 / 115 | 271 / 79 | 171 / 51 | 141 / 42 |
| Canada | 686 / 204 | 463 / 142 | 284 / 90 | 210 / 67 |
| China | 335 / 100 | 222 / 68 | 141 / 44 | 107 / 33 |
| India | 201 / 61 | 135 / 42 | 87 / 27 | 66 / 20 (Chandigarh drops) |
| Saudi Arabia | 42 / 12 | 28 / 8 | 19 / 6 | 16 / 5 |

(Measured with `min_ring_points=6`. US figures therefore exclude Wyoming and Colorado.)

**Per-selection payload,** gzip (country admin-1 + context frame, on top of the 54 KB world
layer and the 7 KB overlay): USA about 108 KB, Canada about 119 KB (at 0.02°), China about 94 KB,
India about 56 KB, Saudi Arabia about 15 KB. Every country is below today's Russia layer (138 KB).

Canada at 0.01° is the heaviest single file because of the Arctic archipelago. The
recommendation is 0.02° for Canada, or 0.01° plus dropping islands below an area threshold.

---

## 5. Matching / join keys

### 5.1 Canonical key

**The canonical unit code is ISO 3166-2 where ISO defines one; otherwise it is a
project-assigned code in the same shape** (the precedent is `UA-CR`). It must never be a code
taken blindly from NE. Build a curated crosswalk per country, in the form
`data/curated/admin1_<cc>.csv`: `ne_id`, NE `iso_3166_2`, canonical `code`, display name,
category, dispute fields, and aliases in English, local script, Arabic, Chinese and French. Join
NE to the crosswalk on `ne_id`. The build should fail on any NE feature missing from the
crosswalk and on any crosswalk row with no NE feature, as `build_regions.py` already does for
Russia.

Prefer `ne_id` over joining on NE `name`, which is what Russia uses today. NE's `name` field
mixes transliteration schemes: Saudi `"Al Quassim"` (sic), `` "`Asir" `` with a backtick,
Chinese `"Inner Mongol"`, Canadian `"Québec"`.

Corrections the crosswalk must apply:

| NE value | Canonical | Why |
|---|---|---|
| `IN-CT`, `IN-UT`, `IN-OR`, `IN-TG` | `IN-CG`, `IN-UK`, `IN-OD`, `IN-TS` | ISO change, 2023-11-23 |
| `CN-X01~` Paracel Islands | none (`disputed_unassigned`, D5) | Non-ISO placeholder, disputed |
| `HK-X01~`…`HK-X18~` (18 districts) | `CN-HK` (one unit, admin-0 geometry) | Non-ISO placeholders, wrong level |
| `MO-M` | `CN-MO` | Non-ISO placeholder |
| `-99-X06~` (KAS) | none (`disputed_unassigned`) | Indeterminate |

### 5.2 Fields that must never be used as keys

- **`code_hasc` and `postal` for China collide with ISO and point to different provinces:**

  | Province | ISO (`iso_3166_2`) | NE `code_hasc` |
  |---|---|---|
  | Hebei | `CN-HE` | `CN.HB` |
  | Henan | `CN-HA` | `CN.HE` |
  | Hubei | `CN-HB` | `CN.HU` |
  | Hainan | `CN-HI` | `CN.HA` |
  | Shaanxi | `CN-SN` | `CN.SA` |

  A careless join on the two-letter suffix would put a Henan event in Hebei.
- **`name_en` for the US capital is "Washington"**, the same as the state of Washington. Use
  `name` ("District of Columbia").
- **`ISO_A2` for Taiwan is "CN-TW"** in admin-0 (§3.1).
- Saudi `code_hasc` (`SA.RI`, `SA.SH`, …) bears no relation to the numeric ISO codes.

### 5.3 Free-text names in English, Chinese, Arabic and French

1. **Resolve within a country first.** The same string means different units in different
   countries. The clearest case: NE's Arabic name for Saudi Arabia's **Eastern Province**
   ("المنطقة الشرقية") is *identical* to its Arabic name for Hong Kong's **Eastern District**,
   and NE's `name` for that HK district is also "Eastern". Saudi "Al Jawf" and Yemen "Al Jawf"
   collide in the same way.
2. **`regionmatch._norm` cannot handle non-Latin names as written.** It lowercases and then
   replaces every character outside `[a-z0-9]` with a space. That turns "Québec" into "qu bec",
   and every Chinese or Arabic name into an empty string, which resolves as `unresolved`. A
   global resolver needs Unicode-aware normalisation:
   - NFKD with combining marks stripped, for Latin script (Québec → quebec, Hawaiʻi → hawaii).
   - For Arabic: strip harakat and tatweel; unify alef forms (أ إ آ → ا), ta marbuta (ة → ه) and
     alif maqsura (ى → ي); strip the leading "منطقة" / "المنطقة" region word.
   - For Chinese: strip administrative suffixes (省, 市, 自治区, 特别行政区, and the ethnic
     qualifiers 壮族 / 回族 / 维吾尔); map traditional characters to simplified with
     `name_zht`→`name_zh` pairs from NE. Sources write "广东", "广东省" and "廣東" for the
     same place.
3. **Seed alias tables from NE, then curate.** `name`, `name_en`, `name_alt` (pipe-separated),
   `name_local`, `name_zh`, `name_zht`, `name_ar` and `name_fr` give a solid starting set.
   Examples for Saudi Arabia: `SA-04` ← "Eastern Province", "Eastern Region", "Ash Sharqiyah",
   "Al-Sharqiyah", "المنطقة الشرقية", "Ach-Charqiya", "东部省". Add the energy towns that sources
   name instead of the region, curated as Russia's port aliases are: Abqaiq, Ras Tanura, Jubail,
   Dhahran, Khurais (→ `SA-01`, check), Yanbu (→ `SA-03`), Jazan refinery (→ `SA-09`).
   Many Saudi regions share a name with their capital city (Riyadh, Makkah, Madinah, Tabuk,
   Ha'il, Najran, Jazan); that is harmless because the city sits inside the region.
4. **India's historic names** (Orissa, Uttaranchal, Pondicherry) and Canada's French names
   (Colombie-Britannique, Terre-Neuve-et-Labrador, Territoires du Nord-Ouest) are already in NE
   `name_alt` / `name_fr`. Adopt them as aliases.

---

## 6. What blocks redistribution from a public repo

| Layer / source | Redistribution status |
|---|---|
| Natural Earth (every layer recommended here) | **No obstacle.** Public domain, no attribution needed (the site credit is a courtesy). |
| GADM | **Blocked.** Redistribution needs prior permission. Do not use. |
| geoBoundaries IND (CC BY 2.5 IN) / CAN (OGL-Canada 2.0) | Allowed **with attribution**. Not recommended anyway (§2.2). |
| geoBoundaries SAU (ODbL 1.0, from OSM) | Allowed, but **share-alike**: the derived database must be offered under ODbL. Avoid mixing it into the NE-derived files. |
| Statistics Canada direct | Allowed with the mandatory "Adapted from Statistics Canada…" notice. |
| US Census CB files | Public domain as a US federal work. The CB page itself states nothing. |

---

## 7. Open risks

1. **Bug: `geo.simplify_geometry` deletes Wyoming and Colorado.** Their outlines are near
   rectangles. Douglas–Peucker reduces each to 5 points (4 corners plus the closing point) at
   every tolerance from 0.005° up, and `min_ring_points=6` then drops the ring as a "sliver".
   Utah survives with 7 points. The same rule removes 248 admin-1 features worldwide at 0.01°.
   The behaviour is also **non-monotonic**: Macau vanishes at 0.02° but survives at 0.03°, and
   10m admin-0 keeps *more* units at 0.1° than at 0.05°. A vertex count is the wrong test for
   "too small to see". Fix it with an area threshold (or `min_ring_points=4`, the minimum valid
   ring) before any US build. Add a test that every crosswalk unit survives simplification. The
   same rule drops `KAS` (Siachen) from the China and India 50m context frames at 0.05°, which
   would leave a **hole exactly where a disputed area should be drawn**.
2. **Natural Earth has been frozen since mid-2022.** That leaves the stale India ISO codes,
   Pakistan's FATA (merged into Khyber Pakhtunkhwa in 2018 but still separate in NE), Hans Island
   (settled 2022) and every later administrative change uncaptured. Mitigations: pin the fetch to
   `v5.1.2` or a commit SHA, carry corrections in the crosswalk, and run a yearly check against
   ISO 3166-2 changes.
3. **Antimeridian.** Alaska spans longitude -179.14 to +179.78 (the Aleutians cross 180°). The
   bbox and representative-point code in `build_regions._meta_entry` will produce a globe-wide
   bbox for `US-AK`, and anything that fits the map to it will zoom out to the whole world.
   Chukotka has the same issue once the Far Eastern FD is enabled.
4. **No topology-preserving simplification.** Each polygon is simplified independently, so
   shared borders between neighbouring units drift and leave slivers or overlaps at high zoom. A
   mismatch already exists between the 50m context and 10m admin-1 edges, and it will become
   visible along long straight borders (US–Canada, US states). It is cosmetic, but it should be
   noted in MVP_REVIEW.
5. **Scale-dependent disputed geometry** (§1.3) and slight overlap between the disputed-area
   layer and neighbouring admin-1 units (the Arunachal disputed polygon spills 2% into Assam).
   Both are covered by D3 (geometry never assigns) and D8 (the overlay is display only).
6. **Owner decisions still open:** aggregate inclusion for `administered_disputed` units (D9),
   Hong Kong and Macau in China's aggregate (D7), and **US territories**. Puerto Rico is
   material to an energy-disruption monitor (grid outages), and NE draws it as admin-0 `PRI`.
   Including it would mean a separately identified unit (`US-PR` per ISO 3166-2:US) built from
   admin-0 geometry, like HK and Macau.
7. **Wording of `sovereignty_recognised`.** For Arunachal and Aksai Chin, "majority recognition"
   is a judgement call. The safe option is to fill only `administered_by` and `claimed_by` and
   leave `sovereignty_recognised` as "no settled consensus" wherever there is no UN-level
   instrument (as there is for Crimea, UNGA 68/262).
8. **Unverified in this pass:** a census.gov licence statement, the current status of the
   Tiran/Sanafir transfer, and current Neutral Zone production-sharing arrangements. The web-search
   budget ran out (§8). None of these changes the recommendation.

---

## 8. Method and reproducibility

- **Files measured.** GeoJSON editions from `https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/`:
  `ne_110m_admin_0_countries`, `ne_50m_admin_0_countries`, `ne_10m_admin_0_countries`,
  `ne_10m_admin_0_countries_{ind,chn,pak,usa,twn}`, `ne_10m_admin_0_disputed_areas`,
  `ne_10m_admin_1_states_provinces` and `ne_50m_admin_1_states_provinces`. From geoBoundaries:
  the simplified ADM1 files for IND, CHN and SAU (release commit `9469f09`), plus API metadata
  for all five countries. All downloads went to a session scratch directory. Nothing was written
  to `data/raw/`.
- **Tools.** `.venv\Scripts\python.exe -I`, stdlib only. Simplification and rounding use a
  verbatim copy of `pipeline/geo.py` (`simplify_geometry`, `round_coords`), so the sizes are what
  the pipeline would emit. Point-in-polygon tests use an even-odd ray cast. Dispute-to-unit
  shares come from a 60×60 sample grid over each disputed polygon's bounding box.
- **Licences** were read from the URLs cited in §1.1 and §2.2 on 2026-10-30. geoBoundaries
  licences come from its API metadata (`boundaryLicense`, `licenseSource`). The tool budget for
  web *search* (not fetch) ran out partway through. The Census licence statement could not be
  located directly and is reported as unverified above.
- **Not done.** No pipeline code was changed and no geometry entered the repo. This document is
  the only file written.
