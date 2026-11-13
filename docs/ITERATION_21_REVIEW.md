# Iteration 21 review: from instrument to product

<!-- status: in-progress -->

Iteration 21 added no country, no score and no new kind of data. It turned the dashboard into a
product people can use: one first screen that says what the site is and what to open next, search,
navigation that always leads home, a safe comparison workspace, a research-coverage explorer, a
per-record evidence inspector, a "what's new" panel, a redesigned Gulf overview and Russia theatre
header, error containment per view and per panel, and a mobile and accessibility pass. Live figures
are in [CURRENT_STATE.md](CURRENT_STATE.md), which the build regenerates; none is re-quoted here
except where a figure is the point of a finding.

**The short version.**

<!-- LEAD: fill at release -->

---

## 0. Baseline

| | |
|---|---|
| Start commit | `51eb9c6` (iteration-20 release) locally; origin/main at `5b68a82` (the daily refresh of 12 November), fast-forwarded |
| First commits of the iteration | `3713096` (export caveats found by iteration-20 production QA) and `94620d4` (iteration-20 review §28) |
| Systems | 13: the Russia theatre (index) and 12 country systems (no score), unchanged |
| Mutation campaign at start | 234 mutants |
| First-time-user baseline | production, before any change (§2) |

## 1. Product strategy

The site's job is unchanged: calibrated honesty about what is and is not known, with a good map. The
iteration-20 product did that job for a reader who already knew how to read it. A first-time reader
met thirteen near-identical cards, the only indexed system tenth in alphabetical order, internal
vocabulary, hover-only definitions and no way home.

The strategy was therefore to make the existing honesty legible, not to add claims:

- **Answer "what should I open next?" on the first screen**, without ordering anything by a figure.
  The theatre leads because it is a different kind of system (the only one with an index), the
  countries follow in alphabetical order.
- **Make every distinction visible where it is used**: research coverage versus source health,
  observed versus modelled, unknown versus not applicable versus not yet researched, no index versus
  zero, "no qualifying record" versus "no disruption".
- **Let readers do analyst tasks**: compare systems on the dimensions that mean the same thing
  everywhere, inspect one record's evidence, cite it with a stable link, export a self-explaining
  image.
- **Keep every safety rule on every new surface.** Each new view was built under the campaign policy
  and then attacked by a safety red team (§24).

Eight features were built in parallel in separate checkouts and integrated deliberately (§27), then
six red teams and fix passes ran against the integrated tree.

## 2. User research and baseline usability

A first-time-user pass ran against production before any change: 20 tasks a new reader should be
able to do, each scored OBVIOUS, FINDABLE, NOT STATED or MISLEADING.

| Result | Tasks |
|---|---|
| Obvious | 6 |
| Findable | 12 |
| Not stated | 1 — "what should I click next?" |
| Misleading | 1 — the theatre's Recent tab |

The misleading one was the most serious finding of the iteration. The Recent tab printed a modelled
"Impaired · impaired 33 d · modelled horizon ~100 d" chip beside "Current facility status withheld
during active campaign", and the reader concluded that the site shows facility status. It does not:
the chip was the index's own decay model, rendered per facility. It is fixed (§9).

The other findings, routed to the feature that owned the surface:

1. The flagship was buried and nothing said what to do next (§3).
2. The headline read 6.7 on cards and 6.69 in the explanation, with no scale (§9).
3. Internal vocabulary reached readers: iteration numbers, file names, "search allowance", Saudi
   Arabia's "open decision" (§7, §8).
4. The theatre ribbon was cramped and scrolled sideways; per-sector cells were zero pixels wide (§9).
5. The theatre on a phone: truncated selector, clipped headline, legend over the attribution (§9, §13).
6. Clicking a dossier tab at 1440 px slid the whole app 400 px left (§9).
7. A black screen while loading; the world map captured the mouse wheel (§3, §15).
8. No way home, three names for the theatre, a stale tab title (§4, §9).
9. Definitions only on hover, which a touch screen does not have; a zero-record country carried the
   badge "Reported events, no index"; Bahrain offered a region filter that could filter nothing (§3, §7).
10. A monolithic methodology with a broken sentence (§9).
11. Feeds padded with one identical safeguard line per record; the Gulf map opened grey and read as
    broken (§3, §8).

The pass was repeated on the final build (§22).

## 3. Global home

The first screen now answers "what is this and what do I open next?" without ordering anything by a
figure.

- **First screen:** product name, a one-line purpose, the search box and three actions (Explore the
  Gulf littoral, Compare systems, Russia, Belarus & Crimea). A fourth action, "Search systems", was
  removed after the second first-time-user pass: the search box above it already searches. The
  comparability note stays visible in a compact form.
- **Start here:** six points and "What to open next". It can be dismissed; the choice is kept in
  browser storage behind a try/catch, so a private window or blocked storage still renders it. It
  does not take focus on a first visit (§14).
- **The indexed system leads** in its own entry, "the only one with a score", with what the score
  means and the sentence "Built for this area alone. No country below has an index". It leads
  because it is a different kind of system, not because of its value. Country cards follow in
  manifest (alphabetical) order and are never re-sorted.
- **Cards:** "No index" in words, neutral shape-coded tags (research preview, Gulf littoral,
  publication safeguards) that open by tap or click rather than hover, the date the newest published
  record was reviewed or "No qualifying records yet", the last systematic research pass and the
  reporting environment. The amber readiness badge, which read as a warning, is gone. Ages are
  computed on the reader's calendar, so a UTC build date no longer reads as tomorrow.
- **Recent published evidence:** date, country link, class, cause and placement; no effect text.
  Consecutive campaign-covered rows of one country fold into one line with no count. One line says
  "Newest is not worst, and a country with no item here is not a quiet country", and the list now
  says how it is sorted (latest date of an episode).
- **Data quality** became separate plain questions: when the site was rebuilt, when sources were
  re-checked, how complete research is, observed versus modelled, what is withheld, whether
  countries can be compared, how old the national context is.
- **Pipeline:** manifest country entries carry `record_reviewed` (a date, or null when there is no
  record).

## 4. Navigation and search

- **One header per page.** Every global view (home, country, Gulf, Compare) has one site bar: the
  product name linking home, a breadcrumb built from the manifest groups (Home › Gulf littoral ›
  Iran), search, What's new, How to read this, How this works, Glossary, Copy view link and the
  system picker; the page title follows it. Integration had produced two stacked headers on
  country, Gulf and Compare pages, about 240 px on a phone before any content; the design red team
  caught it and it was consolidated. The theatre keeps its own bar (§9), which carries the same
  breadcrumb, picker and a Compare link.
- **Phone:** at 600 px or less a "Menu" toggle folds the secondary tools; search and the picker stay
  visible. The country bar fell from five rows to about three and is tested to stay under 22% of an
  844 px screen.
- **What's new** is in the site bar. On home it scrolls to the panel and focuses its heading; from
  another view it goes home as a new history entry.
- **Back and forward work:** every move is a history entry; `document.title` is set per route.
- **Search** is one ARIA 1.2 combobox with no dependency, focused by `/`. Matching ignores case,
  diacritics, Arabic and Persian letter variants, tatweel and direction marks, so Iran is found as
  ایران, ايران, Iran or iran; displayed text is never altered. It indexes systems, aliases, groups,
  views and glossary concepts. Theatre region names (one 17 kB file) are fetched on first focus;
  Crimea is labelled "Occupied unit, internationally Ukrainian". A country's regions are added once
  its page has loaded.
- **Glossary:** a native modal dialog with "How this works" in six steps and the terms the site uses,
  including the research-coverage states and the placement words, each read from the module that
  renders them so the glossary cannot drift from the page. `?help=glossary` opens it.

## 5. Safe compare workspace

`?compare=us,ca,sa` sets two to four monitored systems side by side, only on dimensions that mean the
same thing in every system. The URL is the only state; Back leaves the view.

- **Common basis:** what the system is, record as-of date, index ("No index" in words; the theatre
  reads "Has its own index, not comparable" and its value never appears), research maturity, latest
  systematic pass, source-group states (one count per state, zeros kept, never a percentage),
  campaign safeguards, most precise placement.
- **National context:** the four energy-context figures with unit, year and definition; "no data" is
  distinct from a reported zero, and the theatre reads "No single national figure".
- **Within each system only:** reporting environment, how records are sourced, source check dates,
  under a heading that says it is not a comparison.
- **Never shown:** event, attack or held counts, severity, any ranking or sort. "Not on this basis",
  "no data" and "could not be loaded" are three different cells.
- Only the chosen systems' `system.json` files are fetched, never their event lists, and a
  malformed file affects only its own column. MapLibre is no longer downloaded on this route (§15).
- **Export:** a 1600×900 PNG carrying the title, systems, build date, context year and source, the
  research-coverage states, the no-index meaning, "Not comparable: event counts" and, added by the
  analyst red team, the caveat that a larger national figure does not mean a more important country.
- Entry points: the country header, the home actions, and the theatre's Tools menu.

## 6. Research coverage UX

The country "Research coverage" tab now answers "how well has this country actually been searched?"
in plain words.

- One card per source group (the research plans call them lanes): source family, how it is searched
  with search and item counts, languages required versus run with missing ones named, search window,
  covered-through date, what the source allows, the limitation, and a folded note of what the search
  learned. An overview table jumps to each card.
- States are text plus a distinct shape, all one neutral colour, and never a percentage.
- **One vocabulary everywhere.** The first-time-user pass found one fact described three ways ("not
  exhaustive", "finished", "declared complete"); Compare had a five-bucket map whose "declared
  complete" bucket merged three different build states, and that went into the PNG. All surfaces
  (country header, tab, home, Gulf cards, Compare and its PNG, the empty-corpus page, the glossary)
  now read one module that uses the build's eight lane states and matches the build's rule for rule:
  "Every published item read", "Searched through the publisher's latest release", "Planned searches
  run (not exhaustive)", "Partly searched", "Source unavailable", "Stopped at this site's search
  limit", "Not started", "Logged in an earlier format". A typical line reads "6 source groups: 5 with
  planned searches run (not exhaustive) · 1 with the source unavailable."
- Research coverage and source health are separate headed blocks, with one line saying neither
  implies the other.
- **Campaign systems** never show an outcome count, even if a served log carried one; "under review"
  appears only where the build says so, and in the past tense for older passes.
- When a country has no published record, the tab says there is no recovery research and no citation
  to describe, instead of listing zeros.
- A real gap surfaced in the data: the Saudi OPEC-archive lane requires English and ran in none. It
  shows "Not run in: English".

## 7. Country pages

- **Event cards:** date, class and cause tags, title, summary, then labelled rows for effect,
  placement, recovery and review. On campaign records the recovery row is "Later status" and reads
  as withheld. The evidence block says "N cited pages · M originating statements" and says plainly
  when a record rests only on Wikipedia or an aggregator; the origin rule is mirrored in the browser
  and checked record by record against the build's own count.
- **Evidence Inspector** (§11).
- **Record links:** "Link to this record" on every card that has a stable anchor, `?sys=<id>#ev-<id>`.
  Following one opens the full list, scrolls to the record and marks it. A campaign record gets an
  anchor only if its id is the build's opaque form, so Saudi Arabia's campaign records, whose ids
  name facilities, get none.
- **Empty corpus** (Bahrain, Iran, Oman, Qatar, UAE): leads with "No qualifying records in the current
  reviewed corpus — this is not evidence that no disruption occurred", then what was searched, how
  the country reports, national context, sources, safeguards and what remains incomplete. No zeros,
  no held counts, and the map shrinks instead of filling the first screen with an empty country.
- **Why no score:** a plain paragraph, then "No score is not a score of zero", then what the page
  shows instead; technical detail is folded. File names and "open decision" wording are gone.
- **Filters:** a region filter that could filter nothing is replaced by one line saying why; a Year or
  Type filter with one option says so instead. The selects are styled like the rest of the site.
- **One placement vocabulary**, from one module: National; Several regions; One region; National,
  under safeguards. It replaced five labels for "not placed in one region". On aggregating surfaces a
  safeguarded row keeps an opaque list position, now written "list entry 15" rather than a raw key.
- **Saudi Arabia's older convention** is stated plainly: its older records name facility and region;
  the newer Gulf pages record an attack for the country as a whole. Its data and convention are
  unchanged (owner rows D-11/D-33, §29).

## 8. Gulf overview

- **First screen:** purpose, a caveat line visible at every width ("National context only · not
  comparable between countries · no index or score"), the controls on the map's top edge, the map,
  and beside it the chosen figure's facts and the member list.
- **Neutral default:** the map opens uncoloured but with members distinctly filled and outlined, and
  says "Geography only — choose a national figure to colour the map". The first pass read the grey
  map as broken.
- **Members** are listed in name order beside the map. Pointing or focusing highlights the member;
  Enter or a tap selects it and zooms to its box; a selection panel offers Open, Zoom to, Show all and
  Clear, so nothing is hover-only.
- **Legend:** in-view, filtered-out, other and selected each have their own swatch; zero and no-data
  get their own when they occur.
- **Feed:** a campaign country's consecutive covered rows fold into one line with no count, and a
  line explains why a record reads "National" here while its country page may say more. A fold
  regression found during integration (rows that merely carried a list key were folded as campaign
  records, mislabelling Kuwait's grid faults) was caught in the browser and fixed; the fold now reads
  only the members' withheld flag, and tests pin it on both served lists.
- **Brief export bug fixed:** the export copied the live style and camera, so a selection highlight
  and the reader's zoom would have gone into the brief. It now always frames the whole group and
  drops selection and hover layers.

## 9. Russia theatre UX

No score, weight or meaning changed. The work was to make the existing figures readable.

- **The misleading status chip is gone.** A withheld row shows only "Status withheld", which expands
  to its meaning. Rows with released, dated evidence keep that status without the modelled chip,
  impairment age or horizon.
- **Top bar:** Home › Russia, Belarus & Crimea breadcrumb (one name, also used in the tab title and the
  dossier), system picker, a view switch (Analyze · Map focus · Briefing & export) derived from
  existing state, and tools folded behind "Tools" below 1280 px, including "Compare systems".
- **Headline:** one decimal everywhere a level is shown (ribbon, briefing, Inspector, methodology,
  What's new); changes keep two. A scale line states what the number is, from METHODOLOGY §1, shared
  by the ribbon and the methodology panel. "Why this number?" opens the Inspector, or the historical
  breakdown when the timeline is scrubbed. The peak to date is shown.
- **A live but tiny value no longer reads "0.0".** Electric generation (0.03) and some regions showed
  "0.0", which means "measured, nothing disrupted". They now show "<0.1"; an exact zero stays "0.0"
  and a missing value stays "—".
- **"Why this number?" said coal had documented unscored events; it has none.** The text now uses the
  build's own count and says a zero is not evidence none occurred.
- **Sector cells were zero pixels wide at every width**; they are visible, each with its basis
  (capacity share or event-burden proxy). Both coverage ratios sit beside the headline at the same
  size at every width.
- **Tab bug at 1440 px:** the closed dossier drawer made the root scrollable, so focusing into it slid
  the app about 400 px left. Fixed with `overflow: clip` and hidden closed drawers.
- **Text defects fixed:** "a oil terminal", a spliced methodology sentence, three names for the
  theatre, developer wording in the build ledger, raw ISO dates.
- **Phone:** stacked header within its height cap, compact legend with "All keys", attribution behind
  its own button, presets on one row.

<!-- LEAD: theatre status wording pass (wave 3) -->

## 10. Maps

- The shared map component (home, country, Gulf) has HTML zoom and reset buttons of at least 44 px,
  credits as text under the map rather than an icon over it, an optional empty-state note, a "Same
  data as a table" link and a highlight layer. No basemap, tiles, glyphs or symbol layers were added.
- The home world map no longer captures the mouse wheel: the page scrolls, and zoom needs Ctrl or ⌘
  with the wheel, the buttons, or a click into the map.
- A country map with no record placed in a region shrinks to a smaller fixed height instead of
  dominating the first screen.
- The theatre's controls on the map are 44 px; its header controls stay 24 px (§14, §29).

## 11. Evidence and provenance

- **Evidence Inspector** per record: a button with `aria-expanded` whose content renders only while
  open. It answers in plain words why the record is included (with the rule version and clause in a
  folded "Technical detail"), where each report came from (role, language, date, whether opened,
  whether the link still loaded), how many originating statements there are, what the record does
  not establish, and the review verdicts. Campaign records show no headline, capacity figure or later
  status, enforced in code.
- **Per-citation link state:** each served citation carries `link_check` from the last automated visit
  (§18). The safety red team added a build gate so the curated file can never name an unpublished
  address (§24).
- **Original headlines** sit on their own line with language and direction set, separate from the
  English gloss.

## 12. Briefing and exports

- **Theatre briefing on screen** no longer draws presets, drawer toggles and a duplicate scope note
  under its frame; the legend moves out of the way and controls sit on the map. The exported PNG is
  unchanged.
- **Country PNG:** found broken for countries whose live map is a short strip (the UAE export failed
  with "the rendered map came back blank"), because it copied the live camera into a 1600×900 frame.
  It now frames the country's own bounds with padding for the text panels. The frame text formats
  dates and names countries grammatically.
- **Gulf brief** always frames the whole group, without selection or hover (§8).
- **Compare PNG** (§5) carries the same research-coverage lines as the page.

## 13. Mobile

Driven with Playwright at 390×844, 768×1024, 1440×900 and 720×450 at device scale 2 (the 200% zoom
case) before any source was read.

- Country pages put the navigation below the whole event list on a phone, because phone CSS reordered
  the page. Reordering now happens only inside the page's `<main>`, so the header stays first and the
  map still starts above 430 px.
- At 200% zoom the theatre map was squeezed to about 190 px under its legend; at heights of 520 px or
  less the page now scrolls vertically and the map keeps at least 340 px.
- Compare was 290 px wider than the screen; fixed. No view scrolls sideways at 390 or 720 px.
- Touch targets: 44 px minimum on primary controls at 600 px or less or on a coarse pointer, 24 px on
  inline disclosures; the theatre header is the documented exception (§29).
- The phone site-bar menu (§4); the theatre's weighting clause moves to screen-reader text on phones
  so its header stays inside its height cap.

## 14. Accessibility

- One `h1` and one `main` per view; heading levels never skip; tables captioned.
- Escape closes every disclosure, the evidence inspector, the theatre's methodology dialog (which
  now takes focus and traps Tab), the tools menu (focus returns to its toggle) and any open native
  `<details>`, except inside the glossary dialog, which keeps its native behaviour.
- No two controls share an accessible name where they do different things: 119 buttons named
  "Evidence inspector" now carry the record's title and date as hidden text, and the same was done
  for Compare's definition toggles, the glossary, the theatre filters and the Gulf member buttons.
  Citation links keep their publisher names: their purpose is set by the card around them (WCAG
  2.4.4), and repeating hidden text on hundreds of links would add noise. A lead decision (§29).
- Reading order reaches the header before the theatre's drawer toggles; Start here does not steal
  focus on a first visit.
- One shared `prefers-reduced-motion` rule; more specific transitions had been overriding the old one.
- Focus rings on the theatre's region search.

## 15. Performance

Measured with a reusable tool (`web/scripts/measure-routes.mjs`: cold cache, requests, bytes, time to
map idle, maps created, long tasks, layout shift), five runs per route, before and after.

- **Home layout shift fell from 0.86 to under 0.001.** The manifest and the national context each
  inserted content above the map; home now waits for both before drawing its body, and the map draws
  into a fixed box.
- **One request per file per page.** A shared request cache covers the manifest, country bundles, the
  world map, group context, recent evidence, data quality and the theatre bundle. Before, home → Gulf
  → home downloaded the 428 kB world map three times. A failed request is never kept, so the next
  caller retries.
- **Prefetch:** a route's data starts with its code download; hovering or focusing a card fetches only
  that system.
- **Country pages** no longer fetch the national-context file (164 kB) until a tab or export needs it.
- **The world map is a lazy chunk**, so MapLibre (1.05 MB) is off the home page's critical path.
- **The release red team found three regressions on the integrated build** and fixed them: Compare
  downloaded MapLibre (its transfer fell from 462 kB to 183 kB); opening a country page after Compare
  fetched its `system.json` twice; searching on home and then opening the theatre fetched the region
  file twice. Playwright now asserts each.
- Not changed: the theatre still loads about 3.4 MB because its map uses all of it at load. Splitting
  the 2.4 MB line file is a candidate for a later iteration.

## 16. Error containment

- **A failure stays where it happened.** A view boundary wraps each route, keyed per route so a
  failure does not carry over; its fallback keeps the system picker and offers a way home, a reload
  and a clean link. Panel boundaries wrap each home panel, each Gulf section and each country tab.
- **Validation at load** for every file a view iterates over: manifest, group context, recent
  evidence, data quality, world geometry, What's new and the country fields that had none. A
  malformed optional part is dropped, never invented; a malformed required part refuses the file.
- Tested in the browser: missing and malformed country files, malformed Gulf context with the theatre
  untouched, garbage coordinates in one region, a wrong-type leaf caught by its panel, a country code
  chunk that returns 404.

## 17. Gulf research continuation

The iteration-20 continuation left seven lanes stopped by the shared search allowance (AE4, BH1, IR6,
KW4, QA3, SA1, SA5) and one Saudi archive lane (SA4) unworked. All eight ran in this pass, under the
same plan and inclusion rule, with no candidate threshold lowered.

- **Ran their remaining declared queries:** AE4, BH1, IR6, KW4, QA3 and SA5 (declared search
  complete), SA1 (every declared query run; partial because the archive endpoints refuse an automated
  reader, which is a statement about the source).
- **SA4** (the OPEC report archive) was limited to the period before the campaign, so that no current
  status of an attacked facility was researched. The archive refused access; the lane reads "source
  unavailable", and its required English-language pass is shown as not run.
- **No candidate met the inclusion rule.** The curated corpus is unchanged; the review queue
  re-imports byte-identical.
- The research log records the pass for the six systems worked (`EDM_PASS=21`). A lane worked in this
  pass replaces its iteration-20 entry; a lane not worked is carried forward and marked so.
  Campaign systems publish no outcome counts, only whether review continues.

After the pass no Gulf lane is stopped by the search allowance. Lane states per Gulf system:

| System | Declared search complete | Partly searched | Source unavailable | Last systematic pass |
|---|---|---|---|---|
| Bahrain | 1 | 1 | 1 | 12 Nov 2026 |
| Iran | 5 | 0 | 1 | 12 Nov 2026 |
| Iraq | 3 | 0 | 2 | 11 Nov 2026 |
| Kuwait | 2 | 2 | 0 | 12 Nov 2026 |
| Oman | 1 | 4 | 0 | 11 Nov 2026 |
| Qatar | 2 | 1 | 0 | 12 Nov 2026 |
| Saudi Arabia | 1 | 3 | 1 | 12 Nov 2026 |
| UAE | 1 | 2 | 1 | 12 Nov 2026 |

## 18. Link health

`scripts/check_source_links.py` made one automated visit to each cited page on 12 November: 299
cited addresses, 277 reachable, 1 redirected, 9 blocked, 4 dead, 8 errors (the PHMSA report generator
returning server errors). Every dead link was already dead in the iteration-20 run; none is new. The
check now covers fewer addresses than in iteration 20 (349) because the records held in iteration 20
are no longer cited.

**New this iteration: per-citation state.** Each served citation now carries the state of its last
check (`link_check`), and the evidence inspector says, per citation, whether it still loaded. The
curated file gains `link_states`, keyed by address. Before it was merged, every address in it was
checked against the served payloads: all are cited by published records, and held records never
enter the curated corpus, so the file names no unpublished citation.

**Not a signal: "content changed".** The checker compares a page's hash with the previous run's. On
this run nearly every page reported a change, because news pages rotate advertising and related
links. The flag stays local and is not used as evidence that an article was edited.

<!-- SECTIONS 19-31 at release -->
