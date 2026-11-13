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

<!-- SECTIONS 3-16 from integration and red-team handoffs -->

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
