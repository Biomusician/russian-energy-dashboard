import { useEffect, useMemo, useRef, useState } from "react";
import type { Asset, Bundle, PipelineEntity } from "../types";
import { displayName, loadPipelineRegistry, titleCase } from "../data";
import { iconSVG } from "../icons";

/** Region / asset search (§21). Type a name to jump to a region or a piece of infrastructure.
 *  Matching is a plain case-insensitive substring over PUBLIC names only (region names, asset
 *  names) — it never searches, indexes, or reveals coordinates. Picking a result selects it and
 *  asks the map to frame it; the map move is over public administrative geography and public
 *  facility points, nothing operational. */
export default function SearchBox({
  bundle, onPickRegion, onPickAsset,
}: {
  bundle: Bundle;
  onPickRegion: (code: string) => void;
  onPickAsset: (asset: Asset, index: number) => void;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  // Canonical pipelines are searchable by ALIAS as well as name (§24), which is the point:
  // a reader who knows the line as "Дружба" or "Barátság" should not have to know we call it
  // "Druzhba corridor". Loaded lazily on first focus so it costs nothing until used.
  const [entities, setEntities] = useState<PipelineEntity[]>([]);
  const regionName = (code: string | null | undefined) =>
    (code && bundle.regions.find((r) => r.code === code)?.name) || "";

  useEffect(() => {
    if (!open || entities.length) return;
    void loadPipelineRegistry().then((r) => setEntities(Object.values(r.entities)));
  }, [open, entities.length]);

  const results = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (needle.length < 2) return { regions: [], assets: [], pipelines: [] };
    const regions = bundle.regions
      .filter((r) => r.name.toLowerCase().includes(needle))
      .slice(0, 6);
    // Keep the original array index — it is the asset feature id the map selects on.
    const assets = bundle.assets
      .map((a, i) => ({ a, i }))
      .filter(({ a }) => (a.name ?? "").toLowerCase().includes(needle))
      .slice(0, 8);
    // Only CURATED entities are offered. The auto-derived ones carry a source's raw name and an
    // `auto-osm-rel-…` id, which is not an identity a reader should be searching against.
    const pipelines = entities
      .filter((e) => e.curated)
      .map((e) => {
        const name = e.canonical_name.toLowerCase();
        const alias = (e.aliases ?? []).find((a) => a.toLowerCase().includes(needle));
        if (name.includes(needle)) return { e, via: null as string | null };
        return alias ? { e, via: alias } : null;
      })
      .filter((x): x is { e: PipelineEntity; via: string | null } => x !== null)
      .slice(0, 6);
    return { regions, assets, pipelines };
  }, [q, bundle.regions, bundle.assets, entities]);

  const has =
    results.regions.length > 0 || results.assets.length > 0 || results.pipelines.length > 0;

  const pickRegion = (code: string) => { onPickRegion(code); reset(); };
  const pickAsset = (a: Asset, i: number) => { onPickAsset(a, i); reset(); };
  const reset = () => { setQ(""); setOpen(false); };

  return (
    <div className="search-box" ref={boxRef}
         onBlur={(e) => { if (!boxRef.current?.contains(e.relatedTarget as Node)) setOpen(false); }}>
      <input
        className="search-input"
        type="text"
        value={q}
        placeholder="Search region, facility or pipeline…"
        aria-label="Search for a region, facility or pipeline"
        onChange={(e) => { setQ(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "Escape") reset();
          if (e.key === "Enter") {
            if (results.regions[0]) pickRegion(results.regions[0].code);
            else if (results.assets[0]) pickAsset(results.assets[0].a, results.assets[0].i);
          }
        }}
      />
      {open && q.trim().length >= 2 && (
        <div className="search-results">
          {!has && <div className="search-empty">No region, facility or pipeline matches “{q.trim()}”.</div>}
          {results.regions.length > 0 && (
            <div className="search-group">
              <div className="eyebrow">Regions</div>
              {results.regions.map((r) => (
                <button key={r.code} className="search-row" onClick={() => pickRegion(r.code)}>
                  <span className="search-name">{r.name}</span>
                  <span className="search-meta">{r.district}</span>
                </button>
              ))}
            </div>
          )}
          {results.pipelines.length > 0 && (
            <div className="search-group">
              <div className="eyebrow">Pipelines</div>
              {results.pipelines.map(({ e, via }) => (
                <div key={e.canonical_pipeline_id} className="search-row" style={{ cursor: "default" }}>
                  <span className="search-name">{e.canonical_name}</span>
                  <span className="search-meta">
                    {titleCase(e.commodity)} · {titleCase(e.entity_level)}
                    {/* Say WHICH alias matched, so a Cyrillic or Hungarian query visibly
                        resolves to the canonical entity rather than seeming to match nothing. */}
                    {via ? ` · matched “${via}”` : ""}
                  </span>
                </div>
              ))}
            </div>
          )}
          {results.assets.length > 0 && (
            <div className="search-group">
              <div className="eyebrow">Infrastructure</div>
              {results.assets.map(({ a, i }) => (
                <button key={`${a.asset_id}:${i}`} className="search-row" onClick={() => pickAsset(a, i)}>
                  <span className="search-glyph" aria-hidden="true"
                        dangerouslySetInnerHTML={{ __html: iconSVG(a.asset_class, { size: 15, region: a.precision === "region" }) }} />
                  <span className="search-name">{displayName(a.name)}</span>
                  {/* Region as well as class: two similarly-named facilities in different
                      oblasts were otherwise indistinguishable in the result list. */}
                  <span className="search-meta">
                    {titleCase(a.asset_class)}
                    {regionName(a.region_code) ? ` · ${regionName(a.region_code)}` : ""}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
