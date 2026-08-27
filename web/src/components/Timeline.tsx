import { useEffect, useMemo, useRef } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { Bundle, Incident } from "../types";
import { fmtDate, fmtNum } from "../data";
import { severityColor } from "../palette";

const PLAY_MS = 110;

/** Bottom rail: scrubber plus a trend chart of the index with the event rate behind
 *  it. Inline SVG rather than a charting library — two series and a cursor do not
 *  justify the dependency, and hand-drawing keeps the axes honest about the fact that
 *  the event bars are counts and the line is an index. */
export default function Timeline({
  bundle, step, setStep, selected, visibleIncidents,
}: {
  bundle: Bundle;
  step: number;
  setStep: Dispatch<SetStateAction<number>>;
  selected: string | null;
  visibleIncidents: Incident[];
}) {
  const { national, regional } = bundle;
  const dates = national.dates;
  const last = dates.length - 1;
  const playing = useRef(false);
  const timer = useRef<number | null>(null);

  const series = selected ? regional.regions[selected]?.esdi ?? national.esdi : national.esdi;

  /** Events per timeline step, from the full unfiltered set so the bars describe the
   *  record rather than the current filter selection. */
  const eventsPerStep = useMemo(() => {
    const counts = new Array(dates.length).fill(0);
    const pool = selected
      ? bundle.incidents.filter((i) => i.region_code === selected)
      : bundle.incidents;
    for (const inc of pool) {
      let lo = 0;
      let hi = dates.length - 1;
      if (inc.date < dates[0]) continue;
      while (lo < hi) {
        const mid = Math.ceil((lo + hi) / 2);
        if (dates[mid] <= inc.date) lo = mid;
        else hi = mid - 1;
      }
      counts[lo] += 1;
    }
    return counts;
  }, [bundle.incidents, dates, selected]);

  const stop = () => {
    playing.current = false;
    if (timer.current) window.clearInterval(timer.current);
    timer.current = null;
  };

  const toggle = () => {
    if (playing.current) return stop();
    playing.current = true;
    if (step >= last) setStep(0);
    timer.current = window.setInterval(() => {
      setStep((prev: number) => {
        if (prev >= last) {
          stop();
          return last;
        }
        return prev + 1;
      });
    }, PLAY_MS) as unknown as number;
  };

  useEffect(() => stop, []);

  const maxSeries = Math.max(1, ...series);
  const maxEvents = Math.max(1, ...eventsPerStep);
  const W = 1000;
  const H = 54;

  const path = series
    .map((v, i) => `${i === 0 ? "M" : "L"}${(i / last) * W},${H - (v / maxSeries) * H}`)
    .join(" ");

  return (
    <footer className="timeline">
      <div className="tl-controls">
        <button className="play" onClick={toggle} title="Play through time">▶</button>
        <div>
          <div className="tl-date">{fmtDate(dates[step])}</div>
          <div className="eyebrow">
            {selected ? bundle.snapshot.regions[selected]?.name : "National"} ·{" "}
            {fmtNum(series[step], 1)} index · {visibleIncidents.length} events shown
          </div>
        </div>
      </div>

      <div className="tl-chart">
        <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height: H, display: "block" }}>
          <title>Disruption exposure index and recorded event rate over time</title>
          {eventsPerStep.map((c, i) =>
            c > 0 ? (
              <rect
                key={i}
                x={(i / last) * W}
                y={H - (c / maxEvents) * H * 0.55}
                width={Math.max(1.4, W / last - 0.6)}
                height={(c / maxEvents) * H * 0.55}
                fill="#1f3b4a"
              />
            ) : null,
          )}
          <path d={path} fill="none" stroke="#2ad4ee" strokeWidth={1.4} vectorEffect="non-scaling-stroke" />
          <line
            x1={(step / last) * W}
            x2={(step / last) * W}
            y1={0}
            y2={H}
            stroke={severityColor(series[step])}
            strokeWidth={1.2}
            vectorEffect="non-scaling-stroke"
          />
        </svg>
        <input
          type="range"
          className="scrub"
          min={0}
          max={last}
          value={step}
          onChange={(e) => {
            stop();
            setStep(Number(e.target.value));
          }}
          aria-label="Timeline position"
        />
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9.5, color: "var(--text-faint)" }}>
          <span>{fmtDate(dates[0])}</span>
          <span>bars: recorded events per week · line: exposure index</span>
          <span>{fmtDate(dates[last])}</span>
        </div>
      </div>
    </footer>
  );
}
