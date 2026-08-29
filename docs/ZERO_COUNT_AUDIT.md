# Zero-count audit (iteration 4)

Every taxonomy/filter dimension the UI can expose, audited against the corpus. The rule
(§28 of the iteration brief): **zero is a question before it is an answer** — first try to
improve truthful coverage from public sources, then hide only what stays genuinely zero.
Visibility is data-driven off `snapshot.facet_counts` (whole-corpus counts); a category
that becomes non-zero in a future rebuild reappears on its own, no frontend edit.

Classification vocabulary: **DATA GAP** (real, not ingested) · **PARSER GAP** · **CLASSIFICATION
GAP** · **TRUE/PLAUSIBLE ABSENCE** · **OUT OF SCOPE** · **NOT YET RESEARCHED** · **NO
DEFENSIBLE EVIDENCE**.

Counts below are corpus-wide as of the iteration-4 build (134 events).

## Infrastructure / asset classes

Visibility = assets + network lines + incidents > 0.

| Class | assets | lines | incidents | baseline | action taken | final | UI | classification |
|---|--:|--:|--:|--:|---|--:|---|---|
| Thermal PP | 334 | – | 2 | shown | — | 336 | shown | — |
| Nuclear PP | 9 | – | 1 | shown | — | 10 | shown | — |
| Hydro | 92 | – | 0 | shown | — | 92 | shown | layer only |
| Other gen | 64 | – | 0 | shown | — | 64 | shown | layer only |
| Oil refinery | 0 | – | 84 | shown | — (inventory in `refinery_inventory.json`) | 84 | shown | incident-driven |
| Oil terminal | 0 | – | 33 | shown | — | 33 | shown | — |
| **Gas processing** | **0→2** | 0 | **0→2** | **ZERO** | **Ingested Orenburg + Astrakhan GPP (cited assets) and two documented drone strikes** | **4** | **now shown** | **DATA GAP, resolved** |
| **LNG terminal** | **0→5** | 0 | 0 | **ZERO** | **Ingested 5 AOI LNG terminals (cited assets, admin precision)** | **5** | **now shown** | **DATA GAP, resolved** |
| Oil pipeline | 0 | 205 | 4 | shown | — | 209 | shown | — |
| Gas pipeline | 0 | 2575 | 2 | shown | — | 2577 | shown | — |
| Major substation | 1449 | – | 6 | shown | — | 1455 | shown | — |
| Transmission line | 0 | 5066 | 0 | shown | — | 5066 | shown | layer only |
| **Coal mine** | **0→7** | 0 | 0 | **ZERO** | **Ingested 7 AOI mines (Kuzbass, Krasnoyarsk, Irkutsk, Komi/Vorkuta, Novosibirsk), cited, admin precision** | 7 | **now shown** | **DATA GAP, resolved (iter 5)** |
| **Coal terminal** | **0→6** | 0 | 0 | **ZERO** | **Ingested 6 coal export terminals (Ust-Luga/Rosterminalugol, Lavna, Murmansk, Taman, Tuapse, Azov)** | 6 | **now shown** | **DATA GAP, resolved (iter 5)** |
| **Coal (sector)** | — | — | **0** | **ZERO** | No kinetic/sabotage coal disruption exists in the AOI (the port strikes were oil/gas); inventory ≠ disruption, so the coal SECTOR stays unsupported | 0 | n/a | **correct zero** |
| **Major interconnector** | **0** | **0** | **0** | **ZERO** | HVDC/cross-border links are tagged `power=line` in OSM and already counted under transmission_line; no separate inventory | 0 | **hidden** | **CLASSIFICATION GAP** |

**Sources investigated (infrastructure):** Global Energy Monitor gem.wiki terminal pages;
Wikipedia *Liquefied natural gas industry in Russia*; AKM / Gazprom references for Astrakhan
GPP capacity; Wikipedia *Orenburg gas field*. LNG classification warning (§11) applied: the
Ust-Luga **gas-condensate** complex is not counted as LNG; the Ust-Luga **Baltic LNG** plant
is a distinct facility and is the one ingested. A test enforces "no condensate/fractionation
facility classed as LNG".

## Disruption causes

Visibility = incidents > 0.

| Cause | baseline | research | final | UI | classification |
|---|--:|---|--:|---|---|
| Kinetic strike | 129 | — | 131 | shown | — |
| Technical accident | 2 | — | 2 | shown | — |
| Sanctions / supply chain | 1 | — | 1 | shown | — |
| **Sabotage** | **0** | Qualifying events exist (e.g. Atesh partisan substation sabotage, Bryansk Oblast; various "mystery fires") but the reporting I found rests on **partisan claims** that sit below this project's ingestion confidence floor. Not ingested pending firmer, non-claim sourcing. | 0 | **hidden** | **PLAUSIBLE ABSENCE / thin sourcing** |
| **Cyber** | **0** | No open report found of a cyberattack causing *demonstrated physical* energy-infrastructure disruption in the AOI. Claimed intrusions without an operational effect do not qualify (§15). | 0 | **hidden** | **NO DEFENSIBLE EVIDENCE** |
| **Scheduled maintenance** | **0** | Deliberately not ingested: routine planned downtime is not a disruption this product tracks. Would qualify only if it materially interacts with an existing disruption/sanctions constraint — no such case curated. | 0 | **hidden** | **OUT OF SCOPE** |
| **Unknown** | **0** | Every curated event so far has an identifiable cause; none has been left genuinely unattributed. Not downgrading known attributions to populate this bucket (§15). | 0 | **hidden** | **PLAUSIBLE ABSENCE** |

## Confidence tiers

Visibility = incidents > 0.

| Tier | count | UI | classification |
|---|--:|---|---|
| Confirmed | 39 | shown | — |
| Probable | 66 | shown | — |
| Possible | 29 | shown | — |
| **Unverified** | **0** | **hidden** | **PLAUSIBLE ABSENCE** — curation floors sourced events at "possible"; nothing is carried at "unverified". Tier kept in the taxonomy for future data. Confidence-assignment logic checked; not collapsing every event into one tier (the three used tiers are well spread: 39/66/29). |

## Other dimensions

- **Recovery state / evidence kind:** emitted in `facet_counts` (recovery_state:
  impaired/substantially_restored; evidence_kind: modelled/estimated/observed). Not exposed
  as left-rail filters, so no visibility decision; populated and non-degenerate.
- **District:** every AOI federal district is represented; no zero-district control.

## What remains genuinely zero (and why it is honest)

`coal`, `interconnector`, `sabotage`, `cyber`, `maintenance`, `unknown`, `unverified` are
hidden. None was hidden to tidy the UI: each is either a documented **deferred data gap**
(coal), a **classification** artefact already counted elsewhere (interconnector), **below
the sourcing floor** (sabotage), **without defensible evidence** (cyber), **out of scope**
(maintenance), or a **plausible true absence** (unknown, unverified). Every one reappears
automatically if a sourced record later lands. No synthetic records were created, no
confidence was moved to fill a bucket, and no facility was reclassified to complete the UI.

---

## Iteration-7 re-audit (§32)

Re-run after the iteration-7 research (new recovery episodes, effects, source-quality). Filter
visibility remains data-driven off `snapshot.facet_counts` (zero keys omitted, so a dead control
is hidden automatically and reappears on its own if a sourced record arrives). Findings:

- **Cause**: kinetic_strike, technical, sanctions are populated. **sabotage / cyber** stay zero —
  a genuine/plausible absence in a drone-strike corpus (maintenance accidents are captured as
  `technical`, e.g. the 2022 Urengoy pipeline explosion). Not a parser or classification gap; not
  populated for cosmetic completeness.
- **Confidence**: confirmed / probable / possible populated; `unverified` stays zero (curated rows
  all carry at least a probable classification).
- **Coal**: inventory exists (mines + terminals) but zero AOI disruption events → correctly
  score-0 and the sector stays uncovered. TRUE ABSENCE.
- **New iteration-7 fields are display-only, not filter dimensions**: effect types (price_move,
  export_interruption, …), recovery `evidence_family`, and `source_quality` are shown where present
  and never create an empty toggle. `evidence_family="unknown"` is not emitted (every record maps
  to a concrete family).

No category was populated for cosmetic completeness; no new dead control was introduced. The
iteration-4 rule holds: **zero is a question before it is an answer.**
