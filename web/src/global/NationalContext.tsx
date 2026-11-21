import { useMemo, useState } from "react";
import {
  ELEC_FUELS, ROLE_LABEL, UNIT_SHORT, fmtValue, mixShares, type ContextRow, type EnergyContext,
} from "./context";
import { fmtDate } from "../data";
import { navigate } from "./router";

/** National energy figures (iteration 18; moved out of the world map in iteration 23 so the home
 *  page, the selection card and the country pages can show them without the map library). Context,
 *  never monitoring: one source, one year, national only. */

// The label carries the definition's qualifier ("incl. lease condensate", "dry", "net"), and the
// full definition is the hover text: a bare "Crude oil" invited comparison with crude-only figures.
function Figure({ label, value, title }: { label: string; value: string; title?: string }) {
  return <div className="ctx-fig" title={title}><span className="dim">{label}</span><span className="mono">{value}</span></div>;
}

export function NationalFigures({ row, ctx }: { row: ContextRow; ctx: EnergyContext }) {
  const m = ctx.metrics;
  const v = row.values;
  const shares = mixShares(row);
  const elecTotal = v.electricity_generation;
  const roles = Object.entries(row.roles.by_commodity).filter(([, r]) => r);
  return (
    <>
      <div className="ctx-figs">
        <Figure label={`Energy production, ${ctx.comparison_year}`} title={m.total_production.definition} value={fmtValue(v.total_production, m.total_production.unit)} />
        <Figure label={`Energy consumption, ${ctx.comparison_year}`} title={m.total_consumption.definition} value={fmtValue(v.total_consumption, m.total_consumption.unit)} />
        <Figure label={`${m.crude_production.label}, ${ctx.comparison_year}`} title={m.crude_production.definition} value={fmtValue(v.crude_production, m.crude_production.unit)} />
        <Figure label={`${m.gas_production.label.replace(/ production$/, "")}, ${ctx.comparison_year}`} title={m.gas_production.definition} value={fmtValue(v.gas_production, m.gas_production.unit)} />
        <Figure label={`Coal, ${ctx.comparison_year}`} title={m.coal_production.definition} value={fmtValue(v.coal_production, m.coal_production.unit)} />
        <Figure label={`${m.electricity_generation.label}, ${ctx.comparison_year}`} title={m.electricity_generation.definition} value={fmtValue(elecTotal, m.electricity_generation.unit)} />
      </div>
      {row.scope_note && <p className="small dim">{row.scope_note}</p>}
      {shares.length > 0 && (
        <div>
          <div className="eyebrow">Production mix</div>
          <div className="mix-bar" role="img"
            aria-label={shares.map((s) => `${s.label} ${Math.round(s.share * 100)}%`).join(", ")}>
            {shares.map((s) => <span key={s.id} style={{ width: `${s.share * 100}%`, background: s.color }} />)}
          </div>
          <div className="small dim">{shares.map((s) => `${s.label} ${Math.round(s.share * 100)}%`).join(" · ")}</div>
          {ctx.accounting_convention && <div className="small dim">{ctx.accounting_convention}</div>}
        </div>
      )}
      {elecTotal != null && elecTotal > 0 && (
        <div className="small dim">Electricity by source: {ELEC_FUELS
          .map(([id, label]) => [label, (v[id] ?? 0) / elecTotal] as const)
          .filter(([, s]) => s >= 0.01)
          .map(([label, s]) => `${label} ${Math.round(s * 100)}%`).join(" · ")}</div>
      )}
      {row.roles.overall && (
        <div className="small">{ROLE_LABEL[row.roles.overall]}
          {roles.length > 0 && <span className="dim"> ({roles.map(([k, r]) => `${k}: ${String(r).replace("net_", "").replace("about_", "")}`).join(", ")}; oil here counts all liquids, including refinery gain)</span>}
        </div>
      )}
    </>
  );
}

export function SourceLine({ ctx }: { ctx: EnergyContext }) {
  return (
    <div className="small dim">
      {ctx.comparison_year} figures. Source: <a href={ctx.source.url} target="_blank" rel="noreferrer">{ctx.source.name}</a>,
      release of {fmtDate(ctx.source.release)}.
    </div>
  );
}

/** The status column (iteration 23, H-10): a country with published impact records but no system is
 *  an impact-record country, not "context only". `impactRecords`: the manifest's presence codes. */
export function nationalStatus(r: Pick<ContextRow, "a3" | "name" | "system_id">, partly: Set<string>, impactRecords: Set<string>,
                               systemNames: Record<string, string>): string {
  if (partly.has(r.a3)) return "Partly monitored";
  if (r.system_id) return systemNames[r.system_id] && systemNames[r.system_id] !== r.name ? `Monitored, in the ${systemNames[r.system_id]} system` : "Monitored";
  return impactRecords.has(r.a3) ? "Impact records, not monitored" : "Context only";
}

export function NationalTable({ ctx, partly, impactRecords, onContext, systemNames }: { ctx: EnergyContext; partly: Set<string>; impactRecords: Set<string>; onContext: (a3: string) => void; systemNames: Record<string, string> }) {
  const [sort, setSort] = useState<string | null>(null);
  const cols = ctx.map_metrics;
  const rows = useMemo(() => {
    if (!sort) return ctx.countries;
    // Sorting is the reader's own request. The default order is alphabetical, and nulls stay last.
    return [...ctx.countries].sort((a, b) => (b.values[sort] ?? -1) - (a.values[sort] ?? -1));
  }, [ctx, sort]);
  return (
    <div className="table-scroll">
      <p className="small dim">One source, one year ({ctx.comparison_year}). Alphabetical by default; choose a column to
        sort by that national figure. "No data" is not zero. Energy production says nothing about disruption or importance.</p>
      <table className="sector-table national-table">
        <caption className="sr-only">National energy figures, {ctx.comparison_year}, one source; choose a column heading to sort</caption>
        <thead>
          <tr>
            <th aria-sort={sort ? "none" : "ascending"}><button className="linklike" onClick={() => setSort(null)}>Country</button></th>
            <th>Status</th>
            {cols.map((c) => (
              <th key={c} aria-sort={sort === c ? "descending" : "none"}>
                <button className="linklike" onClick={() => setSort(c)}>
                  {ctx.metrics[c].label} ({UNIT_SHORT[ctx.metrics[c].unit]})
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.a3}>
              <td>
                <button className="linklike" aria-label={`${r.name}: ${r.system_id ? "open its page" : "select it on the map"}`}
                        onClick={() => { if (r.system_id) navigate(r.system_id); else onContext(r.a3); }}>{r.name}</button>
              </td>
              <td className="small dim">{nationalStatus(r, partly, impactRecords, systemNames)}</td>
              {cols.map((c) => <td key={c} className="mono small">{fmtValue(r.values[c], ctx.metrics[c].unit).replace(/ .*$/, (s) => (s === " data" ? " data" : ""))}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function WorldProfile({ ctx, partly, impactRecords, onContext, systemNames, tableOpen = false }: {
  ctx: EnergyContext; partly: Set<string>; impactRecords: Set<string>; onContext: (a3: string) => void; systemNames: Record<string, string>; tableOpen?: boolean;
}) {
  const w = ctx.world.values;
  const total = w.total_production;
  const monitored = ctx.countries.filter((r) => r.system_id).reduce((a, r) => a + (r.values.total_production ?? 0), 0);
  const fake: ContextRow = { a3: "WLD", name: "World", on_map: false, system_id: null, values: w, newer: {}, roles: { overall: null, by_commodity: {} } };
  const shares = mixShares(fake);
  return (
    <div className="panel global-note world-profile">
      <div className="eyebrow">World energy profile, {ctx.comparison_year}</div>
      <p className="small">
        World production: {fmtValue(total, ctx.metrics.total_production.unit)}.{" "}
        {shares.map((s) => `${s.label} ${Math.round(s.share * 100)}%`).join(" · ")}.
        {total ? ` The countries containing the monitored systems produced ${Math.round((monitored / total) * 100)}% of it; the rest are shown for context only.` : ""}
      </p>
      {ctx.accounting_convention && <p className="small dim">{ctx.accounting_convention}</p>}
      {/* No "largest producers" list (iteration 20, §80): a top-N selection is a ranking even when
          printed alphabetically. The national figures are in the table below, alphabetical. */}
      <details open={tableOpen || undefined}>
        <summary className="small">National figures table ({ctx.countries.length} countries and territories)</summary>
        <NationalTable ctx={ctx} partly={partly} impactRecords={impactRecords} onContext={onContext} systemNames={systemNames} />
      </details>
      <SourceLine ctx={ctx} />
      <p className="small dim">{ctx.not_scoring}</p>
    </div>
  );
}
