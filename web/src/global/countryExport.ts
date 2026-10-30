import { ENVIRONMENT_LABEL, labelFor, type CountrySystem } from "./manifest";
import { DISPUTED, NO_EVENTS, type Scale } from "./countryScale";

/** The frame drawn into a country PNG.
 *
 *  An exported image travels without the page around it, so whatever the page says to stop a
 *  misreading has to be in the pixels: that there is no index, what the colours count, and that
 *  the figures are not comparable with any other country. The theatre's briefing frame learned
 *  this in iteration 11; this is the same rule for a view with no headline number.
 */

const INK = "#d4dfea";
const DIM = "#93a5b3";
const BAND = "rgba(7, 9, 12, 0.88)";
const SANS = '"Inter", system-ui, sans-serif';

export function composeCountryFrame(map: HTMLCanvasElement, sys: CountrySystem, scale: Scale): HTMLCanvasElement {
  const W = map.width;
  const H = map.height;
  const out = document.createElement("canvas");
  out.width = W;
  out.height = H;
  const c = out.getContext("2d");
  if (!c) throw new Error("could not create a 2D context to draw the export frame");
  c.drawImage(map, 0, 0, W, H);

  const s = W / 1600;
  const pad = Math.round(24 * s);
  c.fillStyle = BAND;
  c.fillRect(0, 0, W, Math.round(96 * s));
  c.fillStyle = INK;
  c.font = `600 ${Math.round(30 * s)}px ${SANS}`;
  c.fillText(`${sys.name} — reported major energy disruptions`, pad, Math.round(42 * s));
  c.fillStyle = DIM;
  c.font = `${Math.round(16 * s)}px ${SANS}`;
  // The count never travels without the reporting environment that produced it (§6.4).
  const env = labelFor(ENVIRONMENT_LABEL, sys.reporting_environment).toLowerCase();
  c.fillText(
    `No index. ${sys.event_summary.recorded_events} qualifying events recorded (reporting: ${env}); ` +
    `${sys.event_summary.country_level} national or multi-region events not drawn. Record reviewed ${sys.record_reviewed}.`,
    pad, Math.round(74 * s));

  // Colour key: this country's own classes, so the picture cannot be read on another's scale.
  const keys: [string, string][] = [[NO_EVENTS, "none recorded"],
    ...scale.labels.map((l, i) => [scale.colors[i], l] as [string, string]), [DISPUTED, "disputed"]];
  const kx = W - pad - Math.round(330 * s);
  let ky = Math.round(120 * s);
  c.fillStyle = BAND;
  c.fillRect(kx - Math.round(10 * s), ky - Math.round(22 * s), Math.round(340 * s), Math.round((keys.length * 20 + 34) * s));
  c.fillStyle = DIM;
  c.font = `${Math.round(13 * s)}px ${SANS}`;
  c.fillText(`Events recorded per ${sys.geography.unit_label} (this country's range)`, kx, ky);
  for (const [color, label] of keys) {
    ky += Math.round(20 * s);
    c.fillStyle = color;
    c.fillRect(kx, ky - Math.round(11 * s), Math.round(14 * s), Math.round(14 * s));
    c.fillStyle = INK;
    c.fillText(label, kx + Math.round(22 * s), ky);
  }

  const fh = Math.round(58 * s);
  c.fillStyle = BAND;
  c.fillRect(0, H - fh, W, fh);
  c.fillStyle = DIM;
  c.font = `${Math.round(13 * s)}px ${SANS}`;
  c.fillText("What was reported and found, not a rate of disruption. Counts reflect this country's " +
             "reporting rules; not comparable across countries; never ranked.", pad, H - Math.round(34 * s));
  c.fillText("Energy Disruption Monitor · open sources · boundaries: Natural Earth (line of actual control)",
             pad, H - Math.round(14 * s));
  return out;
}

export function countryFilename(sys: CountrySystem): string {
  return `energy-disruption-${sys.system_id}-${sys.as_of}.png`;
}
