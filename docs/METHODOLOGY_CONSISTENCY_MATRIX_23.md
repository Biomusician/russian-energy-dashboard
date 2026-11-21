# Iteration 23 — methodology consistency matrix

21 November 2026. One row per concept, one column per layer. It shows where the same concept
is held to the same rule, which test enforces it, and which finding is still open against it.
Finding ids are from `docs/METHODOLOGY_RED_TEAM_23.md` (all red teams were Claude agents, not
outside human reviewers). A cell names a test only if a function of that name exists under `tests/`
at `iteration-23` (through `c09919e`); otherwise it says "(no test)". A named test means the rule has a
guard, not that the guard is complete.

Layers:

- **TH** — the theatre (Russia, Belarus & Crimea), the only system with an index.
- **CS** — the twelve country systems.
- **IL** — the global impact layer (`global/impacts.json`).
- **GC** — the Gulf regional context (`global/regional_context.json`).
- **WN** — What's New and the theatre's change ledger.
- **UI** — the reader-facing pages, Help and exports.

## 1. The matrix

### Occurrence (did it happen?)

| Layer | Rule | Test | Open |
|---|---|---|---|
| TH | Every curated incident is sourced; only extractable dates become events; the remainder is a stated undercount | `test_every_curated_incident_is_sourced`, `test_a_known_undercount_states_its_magnitude_not_merely_its_existence` | XL-16 |
| CS | A reviewed record that meets an inclusion clause, region-scoped and sourced | `test_country_events_are_region_scoped_whitelisted_and_sourced` | C5, T-A6 (records held, c09919e) |
| IL | Every blind role accepted; an unofficial post is never the sole evidence | `test_import_publishes_only_what_every_role_accepted_and_leaves_first_published_pending`, `test_gate_refuses_an_unofficial_post_as_the_sole_evidence_of_occurrence` | XL-07, XL-16 |
| GC | Aggregate, dated, sourced statements, not events; no open/closed flag | `test_context_entries_are_dated_as_of_sourced_and_reviewed`, `test_the_context_artifact_has_no_status_flag_and_no_shelf_life` | XL-01 (fixed) |
| WN | A historical addition is a data change, not a world change | `test_a_historical_event_added_today_is_a_data_change_not_a_world_change` | XL-03 (limitation) |
| UI | No record is not no disruption | `test_help_says_no_record_is_not_no_disruption` | C4, T-B8 |

### Cause

| Layer | Rule | Test | Open |
|---|---|---|---|
| TH | Cause from the taxonomy; cause and confidence reduce weight | `test_confidence_and_cause_reduce_weight` | Technical and sanctions causes handled ad hoc (cross-layer matrix gap; no finding id) |
| CS | Publication policy follows the cause; a named physical cause is left to review | `test_kinetic_country_policy_is_by_cause`, `test_a_named_physical_cause_is_left_to_review` | — |
| IL | Cause family from the vocabulary; an authority order is neither malicious nor cyber; cyber stops at the broad mechanism | `test_authority_order_is_a_cause_that_is_not_malicious_and_not_cyber`, `test_a_lead_patch_cannot_change_an_attacks_cause_or_weaken_an_abstracted_records_policy` | ECI-07 (corrected); ECI-D1 cause provenance (M13) |
| GC | Statements carry no cause | (no test) | — |
| WN | No cause rule of its own | (no test) | — |
| UI | Evidence confidence does not cover the cause, said on the chip | `test_f5_eci08_the_chip_says_provisional_and_that_it_does_not_cover_the_cause` | ECI-08 (filter label) |

### Attribution

| Layer | Rule | Test | Open |
|---|---|---|---|
| TH | Reported, never asserted; the curated label is hand-set, unread by the score, shown as reported | `test_a_curated_confirmed_label_never_reads_as_confirmed`, `test_the_score_does_not_read_attribution_confidence`, `test_no_curated_incident_without_an_attribution_carries_an_attribution_confidence` | C8 (M4); Help glossary "never typed by hand" (C6) |
| CS | No attribution field; cause only | (no test) | — |
| IL | Status and confidence derived from who attributes; a self-claim never exceeds CLAIM_ONLY; a relay is one attribution; ATTRIBUTED needs an official basis | `test_a_self_claim_alone_cannot_exceed_claim_only`, `test_attribution_confidence_by_who_attributes`, `test_g1_to_g8_a_relayed_attribution_is_one_attribution_and_never_a_second`, `test_attributed_without_an_official_basis_is_refused` | T-C1, T-C2, ECI-12 (M10); T-C3, T-C4, T-C5 (latent); T-C7 (M10) |
| GC | Statements carry no attribution | (no test) | — |
| WN | An attribution update is an update, not a new incident | `test_an_attribution_update_is_an_update_to_an_existing_record_not_a_new_incident` | — |
| UI | Unknown attribution is never low confidence; not applicable renders nothing | `test_atlas_unknown_attribution_never_renders_as_low_confidence`, `test_atlas_not_applicable_attribution_renders_nothing` | — |

### Confidence

| Layer | Rule | Test | Open |
|---|---|---|---|
| TH | Evidence Confidence v1 multiplier, pinned; no analytic module reads v2 or the impact layer | `test_the_theatres_confidence_multiplier_is_byte_for_byte_unchanged`, `test_no_analytic_module_imports_the_impact_layer_or_the_confidence_module`, `test_low_confidence_estimate_does_not_drive_scoring` | ESDI-09, C7, C8 (M4) |
| CS | v2, origins not reviewed, so capped at Moderate; reproducible from public fields | `test_a_record_whose_origins_were_not_reviewed_cannot_be_high`, `test_every_served_country_record_carries_a_confidence_that_its_own_public_fields_reproduce` | C3, ECI-13 (M6); XL-14 |
| IL | v2 `2.0-draft`, provisional; High rests on two counted origins; categories follow the published thresholds | `test_high_confidence_always_rests_on_two_counted_origins`, `test_categories_follow_the_published_thresholds`, `test_f5_the_served_status_says_the_first_calibration_was_run_and_did_not_pass` | ECI-01 (corrected; two need a reviewer), ECI-10 (M15); ECI-02 to -05, -09, -11 (M13) |
| GC | Statements carry no confidence | (no test) | — |
| WN | No confidence figure in a cross-country file | `test_no_confidence_figure_reaches_the_manifest_or_any_cross_country_file` (whether it scans `whats_new.json` was not checked) | — |
| UI | Words, never a score; provisional status beside each category; no total in "Why?"; no country distributions side by side | `test_atlas_confidence_is_words_with_the_served_caveat`, `test_eci15_f2_no_total_and_the_two_origin_counts_say_what_they_count`, `test_f14_no_comparison_view_reads_a_countrys_confidence_distribution` | ECI-08 (filter label); CSV still exports the ordinal score (§5.3 of the report) |

### Geography and precision

| Layer | Rule | Test | Open |
|---|---|---|---|
| TH | Administrative region only; no incident coordinates; no range field; Crimea a separate occupied unit | `test_no_coordinates_on_incident_records`, `test_emitted_data_carries_no_out_of_scope_fields`, `test_crimea_is_a_separate_occupied_unit_others_excluded` | ESDI-06 (node identity, not verified) |
| CS | Admin-1 is a maximum set by `precision_policy`; campaign systems carry no region; Gulf attack records are the country's | `test_a_precision_policy_must_give_its_reason`, `test_f10_no_record_of_a_campaign_restricted_country_system_carries_a_region`, `test_an_abstracted_record_in_a_campaign_system_names_no_region_in_a_citation_address` | Saudi Option B (standing owner decision; disclosed per XL-08) |
| IL | Kinetic and sabotage records country-abstracted with a keyed id; `admin1` must belong to the country | `test_gate_refuses_a_region_on_an_abstracted_record`, `test_an_attack_record_is_abstracted_and_given_a_keyed_id`, `test_f11_the_gate_refuses_a_region_of_another_country` | XL-16 (M12) |
| GC | No vessel, route, position or port dependence; only this file carries strait wording | `test_context_gate_refuses_vessel_route_port_dependence_and_naval_wording`, `test_regional_context_is_the_only_served_file_with_strait_wording` | — |
| WN | A withdrawn record is listed by date, region and class, never by id; a campaign system's hidden fields never surface | `test_a_withdrawn_record_outside_a_campaign_is_listed_by_date_region_and_class_never_by_id`, `test_whats_new_a_campaign_systems_hidden_fields_never_surface_as_a_wording_change` | — |
| UI | An abstracted record shows no place; Crimea is never described as Russian; Compare discloses a page finer than one region | `test_atlas_abstracted_record_shows_no_place_and_no_headline`, `test_crimea_is_never_described_as_russian`, `test_xl08_compare_discloses_a_country_page_finer_than_one_region_at_most` | XL-16 (Atlas shades Crimea for a country-level Ukrainian record) |

### Recovery and current status

| Layer | Rule | Test | Open |
|---|---|---|---|
| TH | Observed > estimated > modelled, kind always stated; a partial restart is not reconstitution; model counts said as model counts | `test_observed_recovery_overrides_modelled_decay`, `test_recovery_evidence_always_says_what_kind_it_is`, `test_partial_restart_is_not_full_reconstitution`, `test_the_ribbon_counts_say_what_they_count` | ESDI-01 (M1); ESDI-02 remainder |
| CS | Campaign systems withhold restart, repair and status; an end date on an active-campaign record fails the build | `test_every_restricted_gulf_system_says_recovery_status_is_withheld`, `test_an_end_date_on_an_active_campaign_record_fails_the_build` | F12 (M11; the one record held) |
| IL | Unknown end is null; abstracted records carry no end date, no duration and no citation more than seven days after the event | `test_an_empty_or_unknown_end_date_is_written_as_null`, `test_csv_an_abstracted_impact_record_exports_no_end_date`, `test_an_abstracted_record_states_no_duration`, `test_xl15_an_abstracted_record_carries_no_late_citation` | — |
| GC | The latest statement is not the current status; no status flag; `as_of` on or before `date` (gated) | `test_help_says_the_latest_gulf_statement_is_not_the_current_status`, `test_atlas_context_timeline_keeps_its_caveat_and_has_no_status_flag`, `test_xl01_a_context_entry_cannot_describe_a_day_after_it_was_made` | — |
| WN | A recovery change alone on a campaign record changes nothing visible | `test_a_recovery_change_alone_on_a_campaign_record_changes_nothing_visible` | — |
| UI | Modelled recovery kept apart from observed; an older context statement says where its newer one is drawn | `test_help_keeps_modelled_recovery_apart_from_observed`, `test_xl01_a_historical_statement_points_where_its_newer_statement_is_drawn` | — |

### First published and history

| Layer | Rule | Test | Open |
|---|---|---|---|
| TH | First seen is the first served build; a past-date build is a reconstruction and says so | `test_first_seen_is_the_first_served_build_and_never_a_fabricated_date`, `test_a_past_date_build_is_labelled_a_reconstruction_at_the_call_site`, `test_a_reconstructed_payload_says_so_on_the_ribbon` | XL-11 (latent), XL-13 |
| CS | `first_published` kept, `last_revised` added; past dates reconstruct country systems | `test_a_changed_record_keeps_first_published_and_gains_last_revised`, `test_a_historical_as_of_build_reconstructs_country_systems_instead_of_failing` | XL-09, XL-10 |
| IL | `first_published` required, pending until import | `test_gate_requires_first_published_and_a_well_formed_id`, `test_import_publishes_only_what_every_role_accepted_and_leaves_first_published_pending` | XL-09, XL-10 |
| GC | Every entry dated and as-of, `as_of` never after `date` | `test_context_entries_are_dated_as_of_sourced_and_reviewed`, `test_xl01_a_context_entry_cannot_describe_a_day_after_it_was_made` | XL-10 |
| WN | Three backfill rules, documented side by side; a month is historical only when wholly before; impact backfill reads the observed end; a first release keeps the context sentence | `test_only_a_record_dated_before_the_previous_build_is_called_historical`, `test_xl04_a_month_is_historical_only_when_the_whole_month_is_before`, `test_xl05_the_panel_and_the_card_call_the_same_records_historical`, `test_xl02_a_first_release_keeps_the_context_sentence` | XL-03 (limitation); IA-15 (payload at head in development mode) |
| UI | A null `first_published` is never a date; the dashboard never "learned" of an event; a reconstruction is not what was published | `test_closure22_null_first_published_is_never_rendered_as_a_date`, `test_no_reader_text_says_the_dashboard_learned_of_an_event`, `test_help_keeps_a_reconstruction_apart_from_what_was_published` | XL-13 |

### Inclusion

| Layer | Rule | Test | Open |
|---|---|---|---|
| TH | No threshold by design: every publicly reported strike in the area of interest | (no test; by design) | — |
| CS | Clauses in `inclusion_threshold.json`; the served rule text matches the build | `test_ta8_the_served_rule_text_matches_what_the_build_does` | T-A1 to T-A5, C13 (M7); T-A6, C5 (records held) |
| IL | Bases 1–6; a candidate matching a held country record is refused, per event | `test_a_candidate_matching_a_record_held_from_a_country_system_is_refused`, `test_a_held_territory_event_cannot_return_through_the_impact_layer` | XL-07, T-B7 (M8); T-B1, T-B4, T-B5, T-B6, T-B9 (M9); T-B2 (gated: `test_tb2_basis_four_needs_a_national_or_regional_scope`), T-B3 (corrected); C11 (`date_end` not reconciled) |
| GC | Only the aggregate statement types allowed | `test_context_gate_allows_the_aggregate_words`, `test_context_gate_refuses_vessel_route_port_dependence_and_naval_wording` | — |
| WN | A threshold version change is one rule change, never a country improving | `test_a_threshold_version_change_is_one_rule_change_never_a_country_improving` | — |
| UI | The grid sentence says which limb the record met | `test_ta7_the_grid_clause_says_which_limb_the_record_met` | T-A7 remainder (exclusions not shown), T-B1 (inspector shows the whole basis definition) |

### Source independence

| Layer | Rule | Test | Open |
|---|---|---|---|
| TH | v1 counts distinct hosts, not origins | (no test) | ESDI-09; EVIDENCE_CONFIDENCE_V2 §8 condition 7 notes v1 fails it |
| CS | Corroboration by origin, not by URL; origins beside citations; the rule says it can overstate independence | `test_corroboration_is_counted_by_origin_not_by_url`, `test_every_served_source_health_counts_origins_beside_citations`, `test_f3_the_served_origin_rule_says_it_can_overstate_independence` | IMPL-D1 (three implementations) |
| IL | A relay never adds an origin; wire copies are one report; an aggregator is never an origin; wire names match whole | `test_b1_to_b4_a_relay_never_adds_an_origin`, `test_case_01_five_syndicated_copies_of_one_wire_report_are_one_report`, `test_an_aggregator_or_a_discovery_aid_is_never_an_origin`, `test_eci14_wire_matching_reads_whole_names` | ECI-01 (corrected; no gate check), ECI-09, ECI-11 (M13) |
| GC | Statements are sourced; origin independence untested | (no test) | Cross-layer matrix gap (no finding id) |
| WN | Not applicable | (no test) | — |
| UI | Origins worded by their basis; the two origin counts say what each counts; reviewers disclosed as sessions of one model | `test_atlas_origins_are_worded_by_their_served_basis`, `test_eci15_f2_no_total_and_the_two_origin_counts_say_what_they_count`, `test_f4_every_review_label_says_the_reviewers_were_one_model` | XL-14 (per-chip basis) |

### Ranking and comparison

| Layer | Rule | Test | Open |
|---|---|---|---|
| TH | Rankings cover affected regions only | `test_rankings_cover_only_affected_regions` | — |
| CS | No rankable figure in the manifest; systems in the manifest's order | `test_the_manifest_carries_no_figure_a_reader_could_rank_countries_by`, `test_the_panel_keeps_the_manifest_order` | C2 (M5), F15 (M14) |
| IL | Atlas counts never per country | `test_atlas_counts_are_never_per_country` | C4; CSV ordinal score (sort warning only) |
| GC | No Gulf index, no count per country | `test_a_new_gulf_system_has_no_index_and_no_zero`, `test_regional_context_changes_are_sentences_with_no_counts` | — |
| WN | Order by name, however much each system changed | `test_whats_new_order_is_by_name_however_much_each_system_changed` | — |
| UI | Compare rows declared and none a count; columns never sorted; the home never sorts its systems | `test_compare_rows_are_declared_and_none_is_a_count`, `test_compare_never_sorts_its_columns`, `test_the_home_never_sorts_its_systems_and_has_no_picker_or_start_here` | C2 (maturity under a common-basis row), F16 (M14) |

### Null versus zero (and the three absences)

| Layer | Rule | Test | Open |
|---|---|---|---|
| TH | A percentage of nothing is null; uncovered sectors null, excluded and renormalised; a zero region and an uncovered region stay distinct | `test_a_percentage_of_nothing_is_null`, `test_uncovered_sectors_and_missing_denominators_are_null_in_every_served_file`, `test_a_zero_region_and_an_uncovered_only_region_stay_distinguishable` | ESDI-08 (zero-scoring oil-logistics nodes not disclosed) |
| CS | No index is not a zero; an empty page says what the absence means | `test_every_country_page_says_no_index_is_not_a_zero`, `test_an_empty_country_page_says_what_the_absence_means_and_never_prints_a_zero` | — |
| IL | An absence is never written as zero or empty | `test_gate_refuses_an_absence_written_as_zero_or_as_an_empty_string`, `test_every_served_affected_is_null_a_figure_or_the_canonical_object` | — |
| GC | A missing national figure is null and the sum is refused | `test_a_gulf_null_is_null_and_the_sum_is_refused_when_one_is_missing` | — |
| WN | Unknown is never shown as unchanged | `test_whats_new_panel_never_shows_unknown_as_unchanged_or_nothing_changed` | — |
| UI | No "0 MW" for a missing figure; no index is words; Help says no index is not zero | `test_no_capacity_figure_never_reads_as_zero_megawatts`, `test_compare_no_index_is_words_never_zero`, `test_help_says_no_index_is_not_zero` | — |

## 2. Gaps

1. **Occurrence across corpora is not reconciled.** Theatre incidents and impact records can describe
   one event without either knowing (XL-16). Country systems reconcile against the impact layer per
   event, on start date ±1 day, and ignore `date_end` (XL-07, C11).
2. **No-widening is per event, not per rule.** A class a country system holds for an owner decision
   can still appear through the impact layer when the country pass stopped early (XL-07, T-B7; M8).
3. **Cause has no common provenance field.** The theatre treats technical and sanctions causes ad
   hoc; the impact layer shows a cause beside a confidence that does not cover it, and the Atlas
   filter label still reads as if it did (ECI-08). A record-level `cause_basis` is proposed, never as
   a scoring input (ECI-D1).
4. **Attribution means different things by layer.** The theatre's label is hand-set (now shown as
   reported). The impact layer's is derived, but the status does not record the instrument's
   formality (T-C1). Three latent gate gaps remain (T-C3 to T-C5). The Help glossary's "never typed
   by hand" is unscoped (C6).
5. **Confidence: three methods, one word.** Theatre v1 (pinned), country v2 capped at Moderate, impact
   v2 provisional. The country summary is near-constant (C3, ECI-13); the chip does not show which
   origin basis it used (XL-14); context and What's New carry none, and only partly by test.
6. **Geography.** The Atlas presence fill shades Crimea for any country-level Ukrainian record
   (XL-16). Saudi Option B is disclosed, not harmonised (standing owner decision).
7. **Recovery and current status.** Observed-only `date_end` holds in the impact layer but not in
   country systems (F12; the one record that showed it is held). Abstracted impact records now carry
   no duration and no late citation (XL-15), and the context gate refuses `as_of` after `date`
   (XL-01, H-M11), all since `a624ec7`.
8. **First published and history.** `first_published` is hand-stamped and not reconciled with the
   production history (XL-09). History doctrine and reconstruction metadata are theatre-only (XL-10).
   "First seen" has four meanings (XL-13). Presumed lineage is dropped (XL-11). Three backfill rules
   are documented, not unified (XL-03). The committed `whats_new.json` at `446a818` is in development
   mode (IA-15).
9. **Inclusion.** The theatre has no threshold by design. Country procedural limbs outrank severity
   (T-A1 to T-A5, C13). Impact bases 1, 2 and 6 drift (T-B1, T-B4, T-B9). Exclusions and known
   weaknesses are not shown on country pages (T-A7 remainder).
10. **Source independence.** The theatre counts hosts (v1). Country origins are grouped by a separate
    implementation from the impact layer and the card (IMPL-D1). Context origin independence is
    untested. Declared relays are not gate-checked (ECI-01).
11. **Ranking and comparison.** The maturity flag sits under Compare's common basis (C2). The CSV
    exports an ordinal score that the page no longer totals (§5.3 of the report). The Atlas map can
    make monitored systems look less disrupted (C4, T-B8).
12. **Null versus zero.** Closed in the theatre's served files by F8. One remaining disclosure gap:
    oil-logistics nodes that score zero for lack of a capacity figure (ESDI-08).
13. **Cells with no test.** TH source independence; CS attribution; GC cause, attribution,
    confidence and source independence; WN cause and source independence; TH inclusion (by design).
    Most are "not applicable" by construction. TH source independence and GC origin independence are
    real gaps.
14. **Found while drafting, not a red-team finding.** The repository CLAUDE.md says replacing the
    theatre multiplier needs "the seven conditions" in EVIDENCE_CONFIDENCE_V2; that section lists
    eight.
