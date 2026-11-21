import { Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Manifest } from "./manifest";
import { PanelBoundary } from "../components/ViewBoundary";
import SystemPanel from "./SystemPanel";
import SelectionCard from "./SelectionCard";
import { hrefFor } from "./router";
import {
  HOME_SELECT_EVENT, STATUS, cardFor, groupBounds, indexWorld, openFromHome, readHomeState, stateOf, systemOf, unitName,
  unitsOf, writeHomeState, type Bbox, type CardAction, type Feature, type PanelRow,
} from "./homeSelection";
import type { HomeMapMode } from "./WorldContext";

// MapLibre is a megabyte: its own chunk, so the panel and the search are drawn from the manifest
// first and work whether or not the map ever draws (no WebGL, a slow device, a failed download).
const WorldContext = lazy(() => import("./WorldContext"));

interface Selection { key: string; feature?: Feature; touch: boolean; opener: HTMLElement | null }

// A unit whose box spans less than this many degrees is a few pixels wide at world zoom: choosing it
// from a list or the search zooms the map to it, so the reader can see what was chosen.
const SMALL_DEGREES = 4;

function useNarrow(): boolean {
  const q = "(max-width: 720px)";
  const [narrow, setNarrow] = useState(() => !!window.matchMedia?.(q).matches);
  useEffect(() => {
    const mq = window.matchMedia?.(q);
    if (!mq) return;
    const on = () => setNarrow(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return narrow;
}

/** The home's first screen below the strip (iteration 23): the map and the panel beside it (below
 *  it on a phone), sharing one selection. Search, map clicks, panel rows and the A to Z list all
 *  go through `pick`.
 *
 *  ONE CLICK, AS LABELLED. With a mouse, a monitored system opens in one click (its hover label
 *  says so). A country without a system has no page, so a click selects it and its card is the
 *  destination. A finger on a phone gets the card first for everything, systems included: a
 *  fat-finger jump from India into China costs more than a second tap. */
export default function HomeStage({ manifest, world, worldError, preview }: {
  manifest: Manifest; world: GeoJSON.FeatureCollection | null; worldError: string | null; preview: string | null;
}) {
  const index = useMemo(() => (world ? indexWorld(world) : null), [world]);
  const narrow = useNarrow();
  // Restored from this history entry: Back returns to the selection the reader left from.
  const [initial] = useState(readHomeState);
  const [selection, setSelection] = useState<Selection | null>(() =>
    (initial.focus && cardFor(initial.focus, null, manifest) ? { key: initial.focus, touch: false, opener: null } : null));
  const [pointed, setPointed] = useState<string | null>(null);
  const [fitTo, setFitTo] = useState<Bbox | null>(null);
  const [mode, setMode] = useState<HomeMapMode>("explore");
  const [announce, setAnnounce] = useState("");
  const opened = initial.ret;
  const stageRef = useRef<HTMLDivElement | null>(null);

  const isSystem = useCallback((key: string) => !!systemOf(manifest, key), [manifest]);

  const select = useCallback((key: string, opts: { touch?: boolean; feature?: Feature; zoom?: boolean } = {}) => {
    const opener = document.activeElement instanceof HTMLElement && document.activeElement !== document.body ? document.activeElement : null;
    setSelection({ key, feature: opts.feature, touch: !!opts.touch, opener });
    writeHomeState(key, null);
    if (key.startsWith("group:")) {
      setFitTo(groupBounds(manifest, key.slice("group:".length)));
    } else if (opts.zoom) {
      const b = index?.bounds.get(key);
      if (b && Math.max(b[2] - b[0], b[3] - b[1]) < SMALL_DEGREES) setFitTo([b[0] - 3, b[1] - 3, b[2] + 3, b[3] + 3]);
    }
    const label = key.startsWith("group:") ? manifest.groups?.[key.slice("group:".length)]?.label ?? key : unitName(key, index, manifest);
    const status = key.startsWith("group:") ? "Regional overview" : STATUS[stateOf(key, index, manifest)];
    setAnnounce(`Selected ${label}: ${status}`);
  }, [manifest, index]);

  const open = useCallback((href: string, ret: string | null) => {
    openFromHome(href, selection?.key ?? null, ret);
  }, [selection]);

  /** Everything that chooses a place comes here. */
  const pick = useCallback((key: string, opts: { touch?: boolean; feature?: Feature; ret?: string; fromList?: boolean } = {}) => {
    if (isSystem(key) && !opts.touch) { open(hrefFor(key), opts.ret ?? `row:${key}`); return; }
    select(key, { touch: opts.touch, feature: opts.feature, zoom: opts.fromList });
  }, [isSystem, open, select]);

  const close = useCallback(() => {
    const back = selection?.opener;
    setSelection(null);
    writeHomeState(null, null);
    setAnnounce("");
    if (back && document.contains(back)) back.focus();
    else document.getElementById("where-to-explore")?.focus();
  }, [selection]);

  // A search result for a country without a system, chosen on this page.
  useEffect(() => {
    const on = (e: Event) => { const key = (e as CustomEvent<string>).detail; if (key) pick(key, { fromList: true }); };
    window.addEventListener(HOME_SELECT_EVENT, on);
    return () => window.removeEventListener(HOME_SELECT_EVENT, on);
  }, [pick]);

  // Escape closes the card or sheet wherever focus is (on the map canvas, for one).
  useEffect(() => {
    if (!selection) return;
    const on = (e: KeyboardEvent) => {
      if (e.key !== "Escape" || document.querySelector("dialog[open]") || e.defaultPrevented) return;
      close();
    };
    document.addEventListener("keydown", on);
    return () => document.removeEventListener("keydown", on);
  }, [selection, close]);

  // Back: focus returns to the control the reader left from.
  useEffect(() => {
    if (!initial.ret) return;
    const el = document.querySelector<HTMLElement>(`[data-ret="${CSS.escape(initial.ret)}"]`);
    const details = el?.closest("details");
    if (details && !details.open) details.open = true;
    el?.focus();
    // Once given back, forgotten: a reload of this entry does not move focus again.
    writeHomeState(initial.focus, null);
  }, [initial]);

  const card = selection ? cardFor(selection.key, index, manifest, selection.feature) : null;
  const sheet = !!card && (narrow || !!selection?.touch);
  const onAction = (a: CardAction) => open(a.href, a.ret);
  const cardNode = card ? <SelectionCard card={card} sheet={sheet} onClose={close} onAction={onAction} /> : null;

  const highlightKey = pointed ?? preview;
  const highlighted = highlightKey?.startsWith("group:") ? unitsOf(highlightKey, manifest) : highlightKey;

  return (
    <div className="home-stage" ref={stageRef}>
      <div className="home-stage-map">
        <PanelBoundary label="The world map">
          <Suspense fallback={<div className="home-map home-map-wait"><div className="home-map-box simple-map placeholder">Loading map…</div></div>}>
            <WorldContext world={world} worldError={worldError} manifest={manifest} index={index}
              mode={mode} onMode={setMode}
              selected={selection ? unitsOf(selection.key, manifest) : []}
              highlighted={highlighted ?? null} fitTo={fitTo}
              onPick={(p, how) => {
                const key = p.system_id ? String(p.system_id) : String(p.a3);
                const name = String(p.name ?? "");
                const feature = name && name !== unitName(key, index, manifest) ? { name, occupied: p.status === "occupied" } : undefined;
                pick(key, { touch: how.touch, feature });
              }} />
          </Suspense>
        </PanelBoundary>
      </div>
      <PanelBoundary label="The list of places to explore">
        <SystemPanel manifest={manifest} index={index} opened={opened}
          onHighlight={setPointed}
          onOpen={(r: PanelRow) => open(r.href, r.key)}
          onShowGroup={(id) => select(`group:${id}`)}
          onPickCountry={(unit, ret) => pick(unit, { ret, fromList: true })}
          card={sheet ? null : cardNode} />
      </PanelBoundary>
      {sheet && cardNode}
      <p className="sr-only" role="status" aria-live="polite">{announce}</p>
    </div>
  );
}
