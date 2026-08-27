/** Colour assignments, kept out of components so the taxonomy stays data-driven.
 *  Asset classes come from the pipeline; anything without an entry here falls back
 *  to a neutral grey rather than throwing or silently vanishing. */

export const CLASS_COLOR: Record<string, string> = {
  power_plant_thermal: "#f2b134",
  power_plant_nuclear: "#a98bfa",
  power_plant_hydro: "#3fb6f5",
  power_plant_other: "#6b7d8c",
  refinery: "#f0534a",
  oil_terminal: "#fb7185",
  pipeline_oil: "#f7862f",
  pipeline_gas: "#2ad4ee",
  gas_processing: "#2dd4bf",
  lng_terminal: "#14b8a6",
  substation: "#e0b83a",
  transmission_line: "#40566a",
  coal: "#94a3b8",
  interconnector: "#c084fc",
};

export const NEUTRAL = "#5b6b78";

export function classColor(cls: string | null | undefined): string {
  return (cls && CLASS_COLOR[cls]) || NEUTRAL;
}

/** Severity ramp for the choropleth. Six stops, deliberately not a rainbow: the eye
 *  should read intensity, and a shape should never depend on hue alone to be
 *  interpretable, which is why every filled region also reports a number. */
// Stop 0 is the resting colour of an AOI region with no exposure. It is deliberately
// lighter than the ocean/context fills so the analytic surface stays visually dominant
// (iteration 2 added surrounding geography underneath it).
export const SEVERITY_STOPS: [number, string][] = [
  [0, "#22303d"],
  [0.5, "#1f5a61"],
  [1.5, "#188084"],
  [3, "#b0901f"],
  [6, "#c86828"],
  [12, "#c23a30"],
];

export function severityColor(value: number): string {
  let color = SEVERITY_STOPS[0][1];
  for (const [stop, c] of SEVERITY_STOPS) {
    if (value >= stop) color = c;
  }
  return color;
}

export const CONFIDENCE_ORDER = ["confirmed", "probable", "possible", "unverified"] as const;

export const CAUSE_COLOR: Record<string, string> = {
  kinetic_strike: "#f0534a",
  sabotage: "#f7862f",
  cyber: "#a98bfa",
  technical: "#2ad4ee",
  sanctions: "#e0b83a",
  maintenance: "#6b7d8c",
  unknown: "#4e5f6d",
};

/** Observed / estimated / modelled visual language. The single most important
 *  distinction in the product: a sourced observation must never look like a guess.
 *  Observed reads as solid fact (green), estimated as provisional (amber), modelled as
 *  a pure assumption (muted, dashed in the UI). */
export const EVIDENCE: Record<string, { color: string; label: string; glyph: string }> = {
  observed: { color: "#3ecf8e", label: "Observed", glyph: "●" },
  estimated: { color: "#f2b134", label: "Estimated", glyph: "◐" },
  modelled: { color: "#7f929f", label: "Modelled", glyph: "○" },
  unknown: { color: "#4e5f6d", label: "Unknown", glyph: "·" },
  not_applicable: { color: "#4e5f6d", label: "N/A", glyph: "–" },
};

export function evidence(kind: string | null | undefined) {
  return (kind && EVIDENCE[kind]) || EVIDENCE.unknown;
}
