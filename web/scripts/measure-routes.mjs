// Route performance measurement (iteration 21).
//
// WHY. "Feels fast" is not a measurement. This opens each route in a fresh browser context (a cold
// cache, as a first-time reader gets) against an already-running `vite preview`, and records what
// the page fetched, how many bytes came over the wire, when the map first finished drawing, how
// many maps were created, long main-thread tasks and layout shift. It prints a JSON report and a
// table. It is a measuring tool, not a test: timings on software WebGL vary run to run, so it
// reports the median of several runs and the test suite asserts only the structural facts
// (which files load, how often).
//
// USAGE (from web/, after `vite build` and with `vite preview --port <P>` running):
//   node scripts/measure-routes.mjs http://127.0.0.1:<P> [runs]

import { chromium } from "@playwright/test";

const BASE = process.argv[2] ?? "http://127.0.0.1:4186";
const RUNS = Number(process.argv[3] ?? 3);

// Installed before any page script: long tasks, layout shift, and every time a map container
// reaches MapLibre's idle state or a new map canvas is created.
const INIT = () => {
  const w = window;
  w.__perf = { longTasks: [], cls: 0, mapIdleAt: null, mapsCreated: 0 };
  try {
    new PerformanceObserver((l) => { for (const e of l.getEntries()) w.__perf.longTasks.push(Math.round(e.duration)); })
      .observe({ type: "longtask", buffered: true });
  } catch { /* not supported */ }
  try {
    new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) w.__perf.cls += e.value; })
      .observe({ type: "layout-shift", buffered: true });
  } catch { /* not supported */ }
  // A canvas can be reported twice (as itself and inside its container), so count distinct ones.
  const seen = new WeakSet();
  const count = (c) => { if (!seen.has(c)) { seen.add(c); w.__perf.mapsCreated += 1; } };
  new MutationObserver((records) => {
    for (const r of records) {
      if (r.type === "attributes" && r.target.dataset?.mapState === "idle" && w.__perf.mapIdleAt == null) {
        w.__perf.mapIdleAt = Math.round(performance.now());
      }
      for (const n of r.addedNodes) {
        if (n.nodeType !== 1) continue;
        if (n.classList?.contains("maplibregl-canvas")) count(n);
        n.querySelectorAll?.(".maplibregl-canvas").forEach(count);
      }
    }
  }).observe(document, { subtree: true, childList: true, attributes: true, attributeFilter: ["data-map-state"] });
};

function attach(page, bucket) {
  page.on("requestfinished", async (req) => {
    // MapLibre starts its worker from a blob: URL. It is not a network request.
    if (req.url().startsWith("blob:")) return;
    const url = new URL(req.url());
    let bytes = 0;
    try {
      const s = await req.sizes();
      bytes = s.responseBodySize + s.responseHeadersSize;
    } catch { /* aborted */ }
    bucket.push({ path: url.origin === new URL(BASE).origin ? url.pathname + url.search : url.href, bytes, type: req.resourceType() });
  });
  page.on("requestfailed", (req) => bucket.push({ path: new URL(req.url()).pathname, bytes: 0, type: "failed" }));
}

function summarise(reqs) {
  const data = reqs.filter((r) => r.path.includes("/data/"));
  const counts = new Map();
  for (const r of data) counts.set(r.path, (counts.get(r.path) ?? 0) + 1);
  return {
    requests: reqs.length,
    dataRequests: data.length,
    kb: Math.round(reqs.reduce((a, r) => a + r.bytes, 0) / 1024),
    dataKb: Math.round(data.reduce((a, r) => a + r.bytes, 0) / 1024),
    jsKb: Math.round(reqs.filter((r) => r.type === "script").reduce((a, r) => a + r.bytes, 0) / 1024),
    duplicates: [...counts].filter(([, n]) => n > 1).map(([p, n]) => `${p.replace(/^.*\/data\//, "")} x${n}`),
    countryEventsLoaded: data.filter((r) => /\/systems\/[^/]+\/events\.json/.test(r.path)).map((r) => r.path.replace(/^.*\/data\//, "")),
    external: reqs.filter((r) => !r.path.startsWith("/")).map((r) => r.path),
    files: [...counts.keys()].map((p) => p.replace(/^.*\/data\//, "")),
  };
}

async function waitIdle(page) {
  await page.waitForFunction(() => window.__perf.mapIdleAt != null, null, { timeout: 60_000 });
  // Let late, non-map loads (panels below the fold) finish so they are counted.
  await page.waitForLoadState("networkidle");
}

async function measureRoute(browser, query) {
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 } });
  const page = await ctx.newPage();
  await page.addInitScript(INIT);
  const reqs = [];
  attach(page, reqs);
  await page.goto(`${BASE}/${query}`);
  await waitIdle(page);
  const perf = await page.evaluate(() => window.__perf);
  await ctx.close();
  return { ...summarise(reqs), mapReadyMs: perf.mapIdleAt, maps: perf.mapsCreated,
           longTasks: perf.longTasks.length, longTaskMs: perf.longTasks.reduce((a, b) => a + b, 0),
           cls: Number(perf.cls.toFixed(4)) };
}

// Open one country, then switch to another with the system picker: what the SWITCH costs.
async function measureSwitch(browser, from, to) {
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 } });
  const page = await ctx.newPage();
  await page.addInitScript(INIT);
  const reqs = [];
  attach(page, reqs);
  await page.goto(`${BASE}/?sys=${from}`);
  await waitIdle(page);
  reqs.length = 0;
  const t0 = await page.evaluate(() => { window.__perf.mapIdleAt = null; window.__perf.mapsCreated = 0; window.__perf.longTasks = []; return performance.now(); });
  await page.getByRole("combobox", { name: "Monitored system" }).selectOption(to);
  await waitIdle(page);
  const perf = await page.evaluate(() => window.__perf);
  await ctx.close();
  return { ...summarise(reqs), mapReadyMs: Math.round(perf.mapIdleAt - t0), maps: perf.mapsCreated,
           longTasks: perf.longTasks.length, longTaskMs: perf.longTasks.reduce((a, b) => a + b, 0), cls: Number(perf.cls.toFixed(4)) };
}

const median = (xs) => { const s = [...xs].sort((a, b) => a - b); return s[Math.floor(s.length / 2)]; };

const ROUTES = [["home", ""], ["gulf", "?group=gulf"], ["ir", "?sys=ir"], ["us", "?sys=us"], ["ru", "?sys=ru"]];

const browser = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
const report = {};
for (const [name, q] of [...ROUTES, ["switch ir->sa", null]]) {
  const runs = [];
  for (let i = 0; i < RUNS; i++) runs.push(q === null ? await measureSwitch(browser, "ir", "sa") : await measureRoute(browser, q));
  const last = runs[runs.length - 1];
  report[name] = { ...last, mapReadyMs: median(runs.map((r) => r.mapReadyMs)), longTaskMs: median(runs.map((r) => r.longTaskMs)),
                   cls: median(runs.map((r) => r.cls)), mapReadyRuns: runs.map((r) => r.mapReadyMs) };
}
await browser.close();

console.log(JSON.stringify(report, null, 1));
console.log("\nroute | requests | data req | KB total | JS KB | data KB | map ready ms (median) | maps | long-task ms | CLS | duplicates");
for (const [k, r] of Object.entries(report)) {
  console.log(`${k} | ${r.requests} | ${r.dataRequests} | ${r.kb} | ${r.jsKb} | ${r.dataKb} | ${r.mapReadyMs} | ${r.maps} | ${r.longTaskMs} | ${r.cls} | ${r.duplicates.join(", ") || "none"}`);
}
