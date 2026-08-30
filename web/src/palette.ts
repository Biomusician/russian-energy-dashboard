/** Colour assignments, kept out of components so the taxonomy stays data-driven.
 *  Asset classes come from the pipeline; anything without an entry here falls back
 *  to a neutral grey rather than throwing or silently vanishing. */

/** Class identity colours. Chosen against the #05070a map ground; several were lifted in
 *  iteration 8 after a contrast audit found three classes effectively invisible and two pairs
 *  separable only by hue at map sizes (where shape is no longer legible). */
export const CLASS_COLOR: Record<string, string> = {
  power_plant_thermal: "#f2b134",
  power_plant_nuclear: "#a98bfa",
  power_plant_hydro: "#3fb6f5",
  // was #6b7d8c — too dark to read against the ground
  power_plant_other: "#9fb2c0",
  refinery: "#f0534a",
  oil_terminal: "#fb7185",
  pipeline_oil: "#f7862f",
  pipeline_gas: "#2ad4ee",
  gas_processing: "#2dd4bf",
  // was #14b8a6 — adjacent to gas_processing's teal, so the two were one colour at icon sizes
  lng_terminal: "#7ee0d0",
  // was #e0b83a — the same yellow family as thermal, and substations are 73% of all point assets,
  // so the map read as one undifferentiated amber swarm. Moved to the far side of the wheel from
  // thermal (169 deg apart) and into the same slate family as transmission_line, which is the
  // honest grouping: they are one subsystem, they never share a mark (points vs lines), and this
  // lets the least analytically salient class recede instead of competing with generation.
  substation: "#9ab8d4",
  // was #40566a — invisible against the ground
  transmission_line: "#5f7a92",
  coal_mine: "#94a3b8",
  // was #78716c — invisible against the ground
  coal_terminal: "#b3a99f",
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

/** Diverging ramp for the "change in ESDI" choropleth (§14-15). This is deliberately a
 *  DIFFERENT visual language from the sequential severity ramp: blue = the index FELL
 *  (recovery / de-escalation), red = it ROSE, dark slate = ~unchanged. Blue never appears in
 *  the exposure ramp, so a reader can never confuse "improved" with "low exposure". The scale
 *  is symmetric and saturates near ±3, which covers the observed regional deltas (max ~2.8
 *  over 30 days). It is a modelled DELTA of the exposure index, never a claim of physical
 *  damage or repair — the legend and copy say so. */
export const ESDI_DELTA_STOPS: [number, string][] = [
  [-3, "#2f7dc4"],
  [-1, "#3f8fb0"],
  [-0.25, "#39616d"],
  [0, "#313f4a"],
  [0.25, "#6f5636"],
  [1, "#c07a2c"],
  [3, "#c23a30"],
];

export function esdiDeltaColor(value: number): string {
  const stops = ESDI_DELTA_STOPS;
  if (value <= stops[0][0]) return stops[0][1];
  if (value >= stops[stops.length - 1][0]) return stops[stops.length - 1][1];
  let color = stops[0][1];
  for (const [stop, c] of stops) {
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
