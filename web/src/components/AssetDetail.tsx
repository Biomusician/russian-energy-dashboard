import type { Asset } from "../types";
import { CLASS_COLOR } from "../palette";
import { fmtNum, titleCase } from "../data";
import { iconSVG } from "../icons";

/** Public, non-locating attributes for one infrastructure asset. The scope boundary is
 *  enforced HERE, in one place, so neither the map hover card nor the dossier sub-card can
 *  ever leak a coordinate: this renders capacity / voltage / fuel / operator / status /
 *  source only — never lat, lon, distance, range, bearing, or route. Region-precision assets
 *  say plainly that their placement is an administrative centroid, not a facility location. */

export function assetRows(asset: Asset): [string, string][] {
  const rows: [string, string][] = [];
  if (asset.capacity_mw) rows.push(["Capacity", `${fmtNum(asset.capacity_mw, 0)} MW`]);
  if (asset.capacity_mtpa) rows.push(["Capacity", `${fmtNum(asset.capacity_mtpa, 1)} MTPA`]);
  if (asset.capacity_bcm_y) rows.push(["Capacity", `${fmtNum(asset.capacity_bcm_y, 2)} bcm/y raw gas`]);
  if (asset.voltage_kv) rows.push(["Voltage", `${fmtNum(asset.voltage_kv, 0)} kV`]);
  if (asset.fuel) rows.push(["Fuel", titleCase(asset.fuel)]);
  if (asset.operator || asset.owner) rows.push(["Operator", asset.operator || asset.owner || ""]);
  if (asset.status) rows.push(["Status", titleCase(asset.status)]);
  return rows;
}

/** The shared inner body: icon header, attribute rows, source, precision note. Layout-neutral
 *  so it drops into both a floating card and an inline dossier block. */
export function AssetAttributes({
  asset, regionName, struck,
}: {
  asset: Asset;
  regionName?: string;
  /** Whether this asset is named in disruption reporting — identity only, never a location. */
  struck?: boolean;
}) {
  const region = asset.precision === "region";
  const rows = assetRows(asset);
  return (
    <>
      <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
        <span style={{ width: 20, height: 20, flex: "0 0 auto" }}
              dangerouslySetInnerHTML={{ __html: iconSVG(asset.asset_class, { size: 20, region }) }} />
        <span style={{ fontSize: 12.5, lineHeight: 1.2 }}>{asset.name || titleCase(asset.asset_class)}</span>
      </div>
      <div className="eyebrow" style={{ marginTop: 3 }}>
        {titleCase(asset.asset_class)}{regionName ? ` · ${regionName}` : ""}
      </div>
      {rows.map(([k, v], i) => (
        <div className="kv" key={i}><span className="k">{k}</span><span className="v">{v}</span></div>
      ))}
      {asset.source && (
        <div className="kv"><span className="k">Source</span><span className="v" style={{ fontSize: 10 }}>{asset.source}</span></div>
      )}
      {struck != null && (
        <div className="kv">
          <span className="k">In disruption reporting</span>
          <span className="v" style={{ color: struck ? "var(--amber)" : "var(--text-faint)" }}>
            {struck ? "yes — named in events" : "not named"}
          </span>
        </div>
      )}
      {region ? (
        <div style={{ fontSize: 10, color: "var(--amber)", marginTop: 6, lineHeight: 1.4 }}>
          Administrative-region placement — not a facility location.
        </div>
      ) : (
        <div style={{ fontSize: 9.5, color: "var(--text-faint)", marginTop: 6 }}>
          Public-coordinate infrastructure point.
        </div>
      )}
    </>
  );
}

/** Floating hover card used on the map. Positioned at a screen point. */
export function AssetHoverCard({
  asset, x, y, regionName,
}: {
  asset: Asset;
  x: number;
  y: number;
  regionName?: string;
}) {
  const region = asset.precision === "region";
  const color = CLASS_COLOR[asset.asset_class] ?? "#5b6b78";
  return (
    <div className="map-hover" style={{ left: x, top: y, borderColor: region ? "#e0b83a" : color, maxWidth: 232 }}>
      <AssetAttributes asset={asset} regionName={regionName} />
    </div>
  );
}
