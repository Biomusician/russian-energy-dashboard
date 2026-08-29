import type { Bundle } from "../types";
import { fmtDate, titleCase } from "../data";

/** In-app methodology. The brief asks for methodology to be visible in the product,
 *  not only in a repository file someone has to go find. Anything that would change
 *  how a number should be read belongs here. */
export default function Methodology({ bundle, onClose }: { bundle: Bundle; onClose: () => void }) {
  const s = bundle.snapshot;
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Methodology and caveats"
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, background: "rgba(3,5,7,0.78)",
        zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center", padding: 28,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--bg-panel)", border: "1px solid var(--line)", borderRadius: 4,
          maxWidth: 760, width: "100%", maxHeight: "100%", overflowY: "auto",
        }}
      >
        <div className="section-head">
          <h2 style={{ fontSize: 14 }}>Methodology &amp; caveats</h2>
          <button className="ghost" onClick={onClose}>close</button>
        </div>

        <div style={{ padding: "14px 18px", lineHeight: 1.65, fontSize: 12.5, color: "var(--text-dim)" }}>
          <H>What the index measures</H>
          <p>
            The Energy System Disruption Exposure Index answers one question: <em>what
            share of the tracked installed base sits at facilities disrupted recently
            enough to still be plausibly impaired</em>, weighted by evidence strength,
            cause, and time elapsed.
          </p>
          <p style={{ color: "var(--amber)" }}>
            It is not a measurement of lost throughput or lost generation. Open
            reporting almost never states how much capacity a given event removed, and
            nothing here fills that gap with an estimate. Of {s.incident_total} events
            in the dataset, {s.incidents_with_quantified_capacity} carry a quantified
            capacity effect.
          </p>

          <H>How a score is built</H>
          <p>
            Each event contributes <code>confidence × cause × 0.5^(days ÷ half-life)</code>,
            where the half-life is set by the recovery evidence (below). Per facility the
            single strongest live contribution wins rather than the sum, so a site hit
            four times cannot exceed being fully disrupted. Facility contributions are
            then weighted by that facility's share of the national capacity base for its
            sector, and sectors are combined using published weights.
          </p>

          <H>Recovery / reconstitution</H>
          <p>
            The decay half-life is evidence-driven, in priority order:{" "}
            <strong style={{ color: "var(--green)" }}>observed</strong> (a source reported
            how long restoration actually took) &gt;{" "}
            <strong style={{ color: "var(--amber)" }}>estimated</strong> (a source gave a
            reconstitution window) &gt;{" "}
            <strong style={{ color: "var(--text-dim)" }}>modelled</strong> (neither exists,
            so a generic per-sector assumption is used). The kind is carried on every
            number and shown in the Recovery tab, so an observed restart never looks like a
            guess. Confirmed reconstitution collapses a facility's contribution.
          </p>
          <p>
            The modelled fallback horizons are the weakest input — assumptions about how
            quickly each asset class returns to service, not measurements. All of them, and
            every other weight, live in <code>methodology/scoring.json</code>.
          </p>

          <H>Denominators</H>
          <ul>
            <li>Refining: {s.denominators.refining_mtpa} MTPA across the tracked national refinery inventory.</li>
            <li>Electric generation: {s.denominators.electric_generation_mw.toLocaleString("en-GB")} MW installed in the area of interest (a capacity share).</li>
            <li>Transmission: an event/recovery-burden measure against a saturation of {s.denominators.transmission_saturation_events} weighted concurrent facility-events — never a capacity-offline claim.</li>
            <li>Oil logistics uses the refining base as a proxy; it has no published throughput denominator.</li>
            {s.sectors_uncovered.length > 0 && (
              <li style={{ color: "var(--amber)" }}>
                No capacity base for: {s.sectors_uncovered.map(titleCase).join(", ")}. These
                sectors are excluded from the composite and their weights redistributed,
                rather than counted as zero.
              </li>
            )}
          </ul>

          {s.refinery_reconciliation?.reference_nameplate_mtpa && (() => {
            const r = s.refinery_reconciliation!;
            return (
              <p style={{ fontSize: 10.5, color: "var(--text-faint)" }}>
                <b>Refining denominator completeness:</b> {r.tracked_mtpa} MTPA tracked ≈{" "}
                {r.denominator_coverage_pct}% of a crude-fuels nameplate reference (~
                {r.reference_crude_nameplate_mtpa} MTPA; full Russian nameplate{" "}
                {r.reference_nameplate_mtpa} MTPA, range {r.reference_range_mtpa?.[0]}–
                {r.reference_range_mtpa?.[1]}, {r.reference_year}). <b>No major crude refinery is
                missing</b>: the gap is ~{r.gap_decomposition?.excluded_condensate_splitters_mtpa} MTPA
                of gas-condensate splitters (Surgut, Ust-Luga, Astrakhan) excluded like Tobolsk, plus ~
                {r.gap_decomposition?.conservative_basis_understatement_mtpa} MTPA because the tracked
                figures use one consistent source ~10-15% below current nameplate — so reported
                refining shares are conservative <i>upper</i> bounds. This is denominator
                completeness, NOT event coverage.
              </p>
            );
          })()}

          {s.refinery_reconciliation?.canonical_linkage && (
            <p style={{ fontSize: 10.5, color: "var(--text-faint)" }}>
              Refineries resolve to a canonical registry (stable id + aliases), so the
              denominator and incidents share one identity. Petrochemical complexes
              (Tobolsk/ZapSibNeftekhim) are excluded from the fuels-refining base.{" "}
              <b>Canonical linkage {s.refinery_reconciliation.canonical_linkage.struck_refineries}/
              {s.refinery_reconciliation.canonical_linkage.denominator_refineries} refineries
              struck = {s.refinery_reconciliation.canonical_linkage.pct_denominator_mtpa_struck}% of
              denominator capacity</b> — this is identity/linkage completeness, not disruption coverage.
            </p>
          )}

          {s.esdi_all_sectors != null && (
            <p style={{ color: "var(--amber)" }}>
              The headline ESDI ({s.esdi.toFixed(1)}) renormalises the covered sectors. Counting
              the uncovered gas &amp; coal sectors as present-at-zero instead gives{" "}
              {s.esdi_all_sectors.toFixed(1)} — so excluding them lifts the headline by{" "}
              {(s.esdi - s.esdi_all_sectors).toFixed(1)}. Gas is not unmeasured: it carries
              documented strikes that score zero for want of a defensible denominator.
            </p>
          )}
          {s.experimental_indices?.gas_processing && (() => {
            const g = s.experimental_indices!.gas_processing!;
            return (
              <>
                <H>Gas processing — experimental (not in the headline)</H>
                <p>
                  Gas is uncovered in the headline ESDI because no defensible national
                  denominator exists. As a separate, <b style={{ color: "var(--amber)" }}>experimental</b>{" "}
                  measure only, disrupted gas-processing capacity is compared against a{" "}
                  bottom-up census of {g.census_plants} publicly-sourced plants totalling{" "}
                  {g.census_bcm_y} bcm/y raw gas. {g.struck_plants} of them carry a live
                  disruption, giving a <b>within-census exposure of{" "}
                  {g.within_census_exposure_pct != null ? `${g.within_census_exposure_pct}%` : "—"}</b>.
                </p>
                <p style={{ color: "var(--amber)", fontSize: 11 }}>
                  This is <b>not</b> national gas-processing exposure. The census is a
                  non-exhaustive sample — Russia processes far more gas than {g.census_bcm_y}{" "}
                  bcm/y — so the ratio overstates the national picture and is deliberately kept
                  out of the headline ESDI pending an independent red-team.{" "}
                  {g.uncertain_bcm_y > 0 && `${g.uncertain_bcm_y} bcm/y of the census is flagged uncertain; `}
                  {g.aggregate_bcm_y > 0 && `${g.aggregate_bcm_y} bcm/y is multi-plant aggregate. `}
                  Capacities are structured bcm/y fields, never parsed from prose at scoring time.
                </p>
                {g.struck.length > 0 && (
                  <p style={{ fontSize: 10.5, color: "var(--text-faint)" }}>
                    Live-disrupted plants:{" "}
                    {g.struck.map((p) => `${p.name} (${p.bcm_y} bcm/y × ${p.disruption_weight})`).join(", ")}.
                  </p>
                )}
              </>
            );
          })()}
          {s.transmission_concentration && s.transmission_concentration.top.length > 0 && (
            <p style={{ color: "var(--text-faint)" }}>
              Transmission is theatre-concentrated, not a national-grid measure: the top
              contributor is {s.transmission_concentration.top[0].name} (
              {s.transmission_concentration.top[0].pct}% of the sector), and occupied Crimea is{" "}
              {s.transmission_concentration.occupied_share_pct}% of it — so read "transmission"
              as the Kerch power bridge plus Crimea substations, not the wider Russian grid.
            </p>
          )}
          {s.transmission_sensitivity && (() => {
            const t = s.transmission_sensitivity!;
            return (
              <>
                <p style={{ color: "var(--text-faint)", fontSize: 11 }}>
                  <b>Transmission sensitivity.</b> The value is an event-burden against a chosen
                  saturation constant ({t.saturation_constant}), spread over just{" "}
                  {t.distinct_affected_regions} region(s) / {t.distinct_facilities} facilities
                  {t.top_region_share_pct != null && <> (top theatre {t.top_region_share_pct}%)</>}.
                  It moves sharply with that constant:{" "}
                  {t.saturation_sweep.map((r) => `sat ${r.saturation}→${r.sector_value}`).join(", ")}.
                  Published as a sensitivity, not a tuning knob — the formula is unchanged.
                </p>
                <p style={{ color: "var(--text-faint)", fontSize: 10.5, fontStyle: "italic" }}>
                  Red-team verdict: {t.red_team_verdict}
                </p>
              </>
            );
          })()}

          <H>Coverage</H>
          {s.coverage && (
            <p>
              <b>Oil-strike benchmark coverage ≈ {Math.round(s.coverage.coverage_ratio * 100)}%</b>:{" "}
              {s.coverage.enumerated_in_this_dataset} enumerated oil-sector strikes vs the{" "}
              {s.coverage.reported_total_strikes} reported strikes on Russian oil facilities. The
              numerator and denominator are the same oil-strike universe — earlier iterations
              divided <i>all</i> energy events ({s.coverage.total_events_all_sectors} across all
              sectors) by this oil-only benchmark, which overstated coverage; that is corrected.
              Other sectors have no known-total benchmark and are shown as unbenchmarked, never a
              fabricated percentage.
            </p>
          )}
          {s.coverage_matrix && (
            <table className="cov-matrix" style={{ width: "100%", fontSize: 11, borderCollapse: "collapse", marginTop: 6 }}>
              <thead><tr style={{ color: "var(--text-faint)", textAlign: "left" }}>
                <th>Sector</th><th>Events</th><th>Assets</th><th>Recov.</th><th>Event coverage</th>
              </tr></thead>
              <tbody>
                {Object.entries(s.coverage_matrix).map(([sec, m]) => (
                  <tr key={sec} style={{ borderTop: "1px solid var(--line)" }}>
                    <td>{titleCase(sec)}</td>
                    <td>{m.event_count}</td>
                    <td>{m.asset_inventory_count}</td>
                    <td>{m.recovery_episodes}</td>
                    <td style={{ color: m.has_event_benchmark ? "var(--text)" : "var(--text-faint)" }}>
                      {m.has_event_benchmark ? "oil-strike benchmark" : m.event_coverage_state}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p style={{ fontSize: 10.5, color: "var(--text-faint)", marginTop: 4 }}>
            Three distinct concepts, never merged: <b>event coverage</b> (only the oil sectors have a
            defensible benchmark), <b>asset-inventory coverage</b>, and <b>recovery-evidence coverage</b>.
          </p>
          {s.coverage && (
            <p style={{ fontSize: 10.5, color: "var(--text-faint)" }}>
              Events not individually enumerated in open structured sources are absent, and the
              index is correspondingly conservative.
            </p>
          )}

          <H>Attribution</H>
          <p>
            Attribution is reported, never asserted. Events drawn from strike reporting
            carry <code>attribution_confidence = probable</code>, reflecting media
            reporting of responsibility rather than independent confirmation.
          </p>

          <H>Scope boundary</H>
          <p>
            This models publicly reported damage to energy infrastructure, aggregated to
            administrative region. It holds no current unit positions, no readiness
            state, no vulnerability or gap assessment, and no ranking of undamaged
            assets. Range-to-target data present in one upstream source is deliberately
            not ingested.
          </p>

          <H>Not modelled</H>
          <ul>
            {Object.entries(s.not_modelled).map(([k, v]) => (
              <li key={k}><strong style={{ color: "var(--text)" }}>{titleCase(k)}</strong> — {v}</li>
            ))}
          </ul>

          <H>Assumptions worth knowing</H>
          <ul>
            <li>Monitored area: Belarus, the six western Russian federal districts, the Siberian Federal District, and occupied Crimea. The headline <strong style={{ color: "var(--text)" }}>Monitored-Area ESDI</strong> covers all of these. The Far Eastern district is defined but not yet enabled.</li>
            <li>Crimea is internationally recognised as Ukraine and is under Russian occupation. It is shown as a separate unit with distinct styling and status, and it now contributes to the index through the sectors where it has qualifying events and a compatible denominator (transmission, oil logistics) — never labelled a Russian region. Inclusion in the index is an analytic choice, not a statement about sovereignty. The other occupied Ukrainian oblasts remain excluded.</li>
            <li>Transmission lines and pipelines are assigned to the region containing their midpoint, and are counted, never scored.</li>
            <li>Month-precision dates are anchored to the first of the month for decay arithmetic; the precision is preserved and shown.</li>
          </ul>

          {s.parser_warnings.length > 0 && (
            <>
              <H>Parser warnings from this build</H>
              <ul>
                {s.parser_warnings.map((w, i) => <li key={i} style={{ color: "var(--amber)" }}>{w}</li>)}
              </ul>
            </>
          )}

          <H>Sources</H>
          <ul>
            <li>Natural Earth 10m admin-1 boundaries — public domain</li>
            <li>WRI Global Power Plant Database v1.3 — CC BY 4.0</li>
            <li>OpenStreetMap via Overpass — ODbL</li>
            <li>English Wikipedia, “Deep strike campaign”, “List of oil refineries”, “2025–2026 Russian fuel crisis” — CC BY-SA 4.0</li>
            <li>Curated incident file — per-row source URLs, shown on each event</li>
          </ul>

          <p style={{ color: "var(--text-faint)", marginTop: 18, lineHeight: 1.5 }}>
            Data as at {fmtDate(s.as_of)}; the dataset is rebuilt daily (last build{" "}
            {fmtDate(s.build_time.slice(0, 10))}). Sources refresh at their own cadence,
            not all daily — strike reporting continuously, the power-plant and grid
            inventories rarely, CREA economic figures monthly (each shown with its own
            reporting month), and curated incidents when a sourced update is added.
          </p>
        </div>
      </div>
    </div>
  );
}

function H({ children }: { children: React.ReactNode }) {
  return (
    <div className="eyebrow" style={{ marginTop: 18, marginBottom: 5, color: "var(--accent)" }}>
      {children}
    </div>
  );
}
