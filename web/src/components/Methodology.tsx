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
            <li>Electric power: {s.denominators.electric_power_mw.toLocaleString("en-GB")} MW installed in the area of interest.</li>
            <li>Oil logistics uses the refining base as a proxy; it has no published throughput denominator.</li>
            {s.sectors_uncovered.length > 0 && (
              <li style={{ color: "var(--amber)" }}>
                No capacity base for: {s.sectors_uncovered.map(titleCase).join(", ")}. These
                sectors are excluded from the composite and their weights redistributed,
                rather than counted as zero.
              </li>
            )}
          </ul>

          <H>Coverage</H>
          {s.coverage && (
            <p>
              This dataset enumerates {s.coverage.enumerated_in_this_dataset} region-assigned
              events. The source benchmark reports {s.coverage.reported_total_strikes} strikes
              on Russian oil facilities in total — so coverage is roughly{" "}
              {Math.round(s.coverage.coverage_ratio * 100)}%. Events not individually
              enumerated in open structured sources are absent, and the index is
              correspondingly conservative.
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
            <li>Area of interest: Belarus, the six western Russian federal districts, and the Siberian Federal District (79 regions). The Far Eastern district is defined but not yet enabled.</li>
            <li>Occupied Ukrainian territory is excluded; it is internationally recognised as Ukraine.</li>
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

          <p style={{ color: "var(--text-faint)", marginTop: 18 }}>
            Data as at {fmtDate(s.as_of)} · built {s.build_time}
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
