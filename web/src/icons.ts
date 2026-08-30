/** Infrastructure icon registry — the SINGLE source of truth for infrastructure symbology
 *  (iteration 8). One shape per taxonomy class drives THREE surfaces so they can never drift:
 *    - the MapLibre map (rasterised locally to images via addImage — no glyph service, no
 *      sprite CDN, no third-party request; the deployed page stays fully self-contained);
 *    - the left-rail Infrastructure-type filter rows;
 *    - the on-map legend.
 *
 *  Grammar (do not overload one channel): SHAPE = infrastructure function; COLOUR = existing
 *  CLASS_COLOR identity (redundant coding for scan speed + colour-blind use); a dashed bracket
 *  FRAME = administrative-region placement (not a facility coordinate). Disruption/activity is
 *  carried by the region halo + choropleth, never baked into the asset glyph.
 *
 *  Each shape is monochrome markup on a 24x24 viewBox using `currentColor`, so the same string
 *  renders as an inline React SVG (legend/filter) and as a class-coloured raster (map). */

import { classColor } from "./palette";

/** Inner SVG markup for each class, monochrome (fill inherits `currentColor`). Kept simple:
 *  recognisability at 16-24px beats intricate artwork (§4). */
export const ICON_SHAPES: Record<string, string> = {
  // Chimney / generating-station stacks.
  power_plant_thermal:
    '<path d="M5 21V11h3V8h3v3h3V6h3v15z"/><circle cx="17.4" cy="3.6" r="1.5"/><circle cx="14.6" cy="2.4" r="1"/>',
  // Radiation trefoil: hub + three 60-degree blades at 60/180/300 degrees.
  power_plant_nuclear:
    '<circle cx="12" cy="12" r="2.4"/>' +
    '<path d="M12 12 5.07 8a8 8 0 0 1 6.93-4v4a4 4 0 0 0-3.46 2z"/>' +
    '<path d="M12 12h8a8 8 0 0 1-3.46 6.6l-2-3.46A4 4 0 0 0 16 12z"/>' +
    '<path d="M12 12l-4 6.93A8 8 0 0 1 4 12h4a4 4 0 0 0 2 3.46z"/>',
  // Dam wall + water below.
  power_plant_hydro:
    '<path d="M4 4h3l1 11H7z"/><path d="M17 4h3l-1 11h-1z"/><path d="M7 8h10l-.3 3H7.3z"/>' +
    '<path d="M3 18c1.5 0 1.5-1.4 3-1.4s1.5 1.4 3 1.4 1.5-1.4 3-1.4 1.5 1.4 3 1.4 1.5-1.4 3-1.4 1.5 1.4 3 1.4v3H3z"/>',
  // Lightning bolt.
  power_plant_other: '<path d="M13 2 4 14h6l-2 8 11-14h-7z"/>',
  // Tall distillation / fractionation column with a top flare.
  refinery:
    '<path d="M9 22V7a3 3 0 0 1 6 0v15z"/><path d="M8 10h8M8 14h8M8 18h8" stroke="#05070a" stroke-width="1.1"/>' +
    '<path d="M12 6c0-2 2-2 2-3.6C15.4 3 15 5 13.8 5.4 15 6 15.4 4 16 3.4c.6 1.8-.4 3.2-1.6 3.6z"/>',
  // Squat cylindrical storage tank (wide, short — distinct from the tall refinery column).
  oil_terminal:
    '<ellipse cx="12" cy="8" rx="8" ry="2.4"/><path d="M4 8v9c0 1.3 3.6 2.4 8 2.4s8-1.1 8-2.4V8z"/>' +
    '<path d="M12 11.5c-1.2 1.6-2 2.6-2 3.6a2 2 0 0 0 4 0c0-1-.8-2-2-3.6z" fill="#05070a"/>',
  // Spherical pressure vessel + flare stack. Deliberately NOT another banded vertical column:
  // against the refinery's tall fractionation tower the two were one silhouette at map sizes,
  // leaving colour as the only channel separating them.
  gas_processing:
    '<circle cx="9.5" cy="15" r="5.5"/>' +
    '<path d="M6.5 10.5h6M5.6 19h7.8" stroke="#05070a" stroke-width="1.1" fill="none"/>' +
    '<path d="M17 22V9h2.6v13z"/>' +
    '<path d="M18.3 2c1.5 1.7 2.5 2.9 2.5 4.4a2.5 2.5 0 0 1-5 0c0-1 .6-1.7 1-2.4.2.9.6 1.2 1 1.4-.4-1-.2-2.2.5-3.4z"/>',
  // Cryogenic LNG tank + snowflake. Full-opacity tank and a heavier snowflake: at 0.55 the
  // snowflake washed out and the shape collapsed to the same squat cylinder as an oil terminal.
  lng_terminal:
    '<path d="M4 9a8 3 0 0 1 16 0v8c0 1.3-3.6 2.4-8 2.4S4 18.3 4 17z"/>' +
    '<ellipse cx="12" cy="9" rx="8" ry="2.6"/>' +
    '<path d="M12 5.6v10.6M8 7.6l8 6.6M16 7.6l-8 6.6" stroke="#05070a" stroke-width="2.2" stroke-linecap="round" fill="none"/>',
  // Transformer coils (two interlocked rings) = electrical node.
  substation:
    '<circle cx="9" cy="12" r="4.4" fill="none" stroke="currentColor" stroke-width="1.9"/>' +
    '<circle cx="15" cy="12" r="4.4" fill="none" stroke="currentColor" stroke-width="1.9"/>',
  transmission_line:
    '<path d="M12 2 5 22M12 2l7 20M8 8h8M6.5 14h11" stroke="currentColor" stroke-width="1.6" fill="none"/>',
  interconnector:
    '<circle cx="6" cy="12" r="3"/><circle cx="18" cy="12" r="3"/><path d="M9 12h6" stroke="currentColor" stroke-width="2"/>',
  // Crossed pickaxes = mine.
  coal_mine:
    '<path d="M4 6c5-3 11 3 16 0 0 0-1 2-4 2.4M20 6c-3 3 3 11 0 16 0 0-2-1-2.4-4" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>' +
    '<path d="M6 8 18 20M18 8 6 20" stroke="currentColor" stroke-width="1.9"/>',
  // Conveyor loading a bulk pile = terminal (distinct from the mine's picks).
  coal_terminal:
    '<path d="M3 20h18l-9-6z"/><path d="M4 6 18 15" stroke="currentColor" stroke-width="1.8" fill="none"/>' +
    '<circle cx="4" cy="6" r="1.8"/><circle cx="18" cy="15" r="1.8"/>',
  // Pipe + valve motifs for the line classes (legend-only; these render as lines on the map).
  pipeline_oil:
    '<path d="M3 12h18" stroke="currentColor" stroke-width="2.4"/><circle cx="12" cy="12" r="3.4"/><path d="M12 8.6v6.8" stroke="#05070a" stroke-width="1.4"/>',
  pipeline_gas:
    '<path d="M3 14h18" stroke="currentColor" stroke-width="2.4"/><path d="M12 3c1.6 1.8 2.6 3 2.6 4.6a2.6 2.6 0 0 1-5.2 0C9.4 6.4 10 5.8 10.6 5c.2 1 .7 1.3 1.1 1.5C11 5.2 11.3 4.2 12 3z"/>',
};

/** Ordered class list for the legend (point classes first, then the line classes). */
export const ICON_CLASS_ORDER = [
  "refinery", "oil_terminal", "gas_processing", "lng_terminal",
  "power_plant_thermal", "power_plant_nuclear", "power_plant_hydro", "power_plant_other",
  "substation", "coal_mine", "coal_terminal", "interconnector",
  "transmission_line", "pipeline_oil", "pipeline_gas",
];

export function hasIcon(cls: string): boolean {
  return cls in ICON_SHAPES;
}

/** A full inline SVG string for a class, coloured by its class identity, optionally with the
 *  dashed region-placement frame. Used by the React legend/filter and to rasterise map images. */
export function iconSVG(
  cls: string,
  opts: { size?: number; region?: boolean; color?: string; stacked?: boolean } = {},
): string {
  const size = opts.size ?? 24;
  const color = opts.color ?? classColor(cls);
  const shape = ICON_SHAPES[cls];
  const body = shape
    ? `<g fill="${color}" stroke="none">${shape.replace(/currentColor/g, color)}</g>`
    // Unknown class: a hollow diamond so it is visibly a fallback, never a confident glyph.
    : `<path d="M12 3l9 9-9 9-9-9z" fill="none" stroke="${color}" stroke-width="1.6"/>`;
  const frame = opts.region
    // Dashed bracket frame = administrative-region placement (uncertainty), not a facility coordinate.
    ? `<path d="M4 8V4h4M16 4h4v4M20 16v4h-4M8 20H4v-4" fill="none" stroke="${color}" stroke-width="1.4" stroke-dasharray="2 1.6" opacity="0.9"/>`
    : "";
  // "Stacked cards" backplate = SEVERAL assets share this administrative centroid. It is a
  // cartographic marker for multiplicity, not a second location: the exact members are named in
  // the hover/click card. Drawn behind the glyph and offset up-right so the shape stays readable.
  // Offset far enough (4 units) that the plates stay separable at map sizes — at the previous
  // 2.5 they merged into a single thin box and read as a selection highlight rather than
  // "several". Filled with the page ground so the rear plates read as cards behind the glyph.
  const stack = opts.stacked
    ? `<g stroke="${color}" stroke-width="1.3" fill="#05070a">` +
      `<rect x="9" y="1.5" width="13.5" height="13.5" rx="1.6" stroke-opacity="0.5"/>` +
      `<rect x="5" y="5.5" width="13.5" height="13.5" rx="1.6" stroke-opacity="0.8"/></g>`
    : "";
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24">${stack}${body}${frame}</svg>`;
}

/** MapLibre image id for a class + precision + multiplicity variant. */
export function iconImageId(cls: string, region: boolean, stacked = false): string {
  return `asset-${hasIcon(cls) ? cls : "unknown"}${region ? "-region" : ""}${stacked ? "-stack" : ""}`;
}

export const ICON_SCALE = 3;

/** Every (class, precision) image id + its ImageData, rasterised locally ONCE (memoised at
 *  module scope). Fully in-memory — SVG string -> data-URI -> <img> -> offscreen-canvas
 *  ImageData — so no glyph service, sprite sheet, or network request of any kind. The map
 *  registers these with addImage() AFTER its style has loaded (avoiding the styleimagemissing
 *  deadlock where addImage fails mid-load and the style never finishes). */
let prewarmPromise: Promise<{ id: string; data: ImageData }[]> | null = null;

export function prewarmIcons(): Promise<{ id: string; data: ImageData }[]> {
  if (prewarmPromise) return prewarmPromise;
  const px = 24 * ICON_SCALE;
  const specs: { id: string; cls: string; region: boolean; stacked: boolean }[] = [];
  // Every (class x precision x multiplicity) variant, including the "unknown" fallback, so no
  // draw can ever miss an image and fall back to an undifferentiated dot.
  for (const cls of [...Object.keys(ICON_SHAPES), "__none__"]) {
    for (const region of [false, true]) {
      for (const stacked of [false, true]) {
        // Only administrative-centroid assets can share a point, so a stacked marker is always
        // also region-placed; rasterising the impossible pairing would be a quarter of this
        // work thrown away.
        if (stacked && !region) continue;
        specs.push({ id: iconImageId(cls, region, stacked), cls, region, stacked });
      }
    }
  }
  prewarmPromise = Promise.all(
    specs.map((s) =>
      rasterise(iconSVG(s.cls, { size: px, region: s.region, stacked: s.stacked }), px)
        .then((data) => ({ id: s.id, data })),
    ),
  ).then((results) => results.filter((r): r is { id: string; data: ImageData } => r.data != null));
  return prewarmPromise;
}

/** Classes the map may render as points but that carry no deliberate shape. Should always be
 *  empty: a new taxonomy class must get a designed glyph, not silently inherit the fallback
 *  diamond. Surfaced in dev and asserted by a test so it cannot pass unnoticed. */
export function unknownPointClasses(classes: Iterable<string>): string[] {
  return [...new Set(classes)].filter((c) => c && !hasIcon(c)).sort();
}

function rasterise(svg: string, px: number): Promise<ImageData | null> {
  return new Promise((resolve) => {
    const url = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
    const img = new Image();
    img.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = px;
        canvas.height = px;
        const ctx = canvas.getContext("2d");
        if (!ctx) return resolve(null);
        ctx.drawImage(img, 0, 0, px, px);
        resolve(ctx.getImageData(0, 0, px, px));
      } catch {
        resolve(null);
      }
    };
    img.onerror = () => resolve(null);
    img.src = url;
  });
}
