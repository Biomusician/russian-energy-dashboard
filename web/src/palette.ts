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
export const SEVERITY_STOPS: [number, string][] = [
  [0, "#16202a"],
  [0.5, "#14484f"],
  [1.5, "#157c7f"],
  [3, "#a8871f"],
  [6, "#c26326"],
  [12, "#b8382f"],
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
