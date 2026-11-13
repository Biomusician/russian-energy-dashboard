import { test, expect, type App } from "./fixtures";

/**
 * The Research Coverage Explorer in a real browser.
 *
 * "How well has this country actually been searched?" Each lane (one family of sources searched as
 * a unit) is shown as it stands in its latest pass, with a categorical state as text plus a shape.
 * Every expectation below is derived from the payload the page itself loaded; what is fixed is the
 * behaviour: blocked sources read "Source unavailable", a lane stopped by the search limit is
 * never complete, missing languages are named, no percentage, and under the attack-campaign rule no
 * count of candidates, held records or outcomes.
 */

type Page = import("@playwright/test").Page;
type Lane = { lane: string; execution?: string; source_window?: string; stopped_by?: string | null;
              languages_required?: string[]; languages_executed?: string[] };
type Pass = { date: string; kind: string; lanes?: Lane[]; under_review?: boolean };

const system = (page: Page, id: string) =>
  page.evaluate((x) => fetch(`/data/systems/${x}/system.json`).then((r) => r.json()), id);

/** Each lane from the latest systematic pass that logged it; a later same-day pass wins. */
function latest(passes: Pass[]): Map<string, Lane> {
  const out = new Map<string, Lane>();
  const sys = passes.map((p, i) => ({ p, i })).filter(({ p }) => p.kind === "systematic")
    .sort((a, b) => (a.p.date < b.p.date ? -1 : a.p.date > b.p.date ? 1 : a.i - b.i));
  for (const { p } of sys) for (const l of p.lanes ?? []) { out.delete(l.lane); out.set(l.lane, l); }
  return out;
}

// The same eight words every page uses (laneCoverage.ts); the old-format state only where present.
const STATES = ["Every published item read", "Searched through the publisher's latest release",
                "Planned searches run (not exhaustive)", "Partly searched", "Source unavailable",
                "Stopped at this site's search limit", "Not started"];
const DONE_TEXT = /Every published item read|Searched through the publisher's latest release|Planned searches run/;

async function openResearch(app: App, id: string) {
  await app.open(`?sys=${id}`);
  await app.button("Research coverage").click();
}

test.describe("Research coverage explorer", () => {
  test("ir: a zero-record campaign system shows its lanes and no count of anything unpublished", async ({ app, page }) => {
    await openResearch(app, "ir");
    const sys = await system(page, "ir");
    const events = await page.evaluate(() => fetch("/data/systems/ir/events.json").then((r) => r.json()));
    expect(events.events.length).toBe(0);
    const lanes = latest(sys.research_log.passes);
    expect(lanes.size).toBeGreaterThan(0);

    const rc = page.locator("section.rc");
    await expect(rc.getByRole("heading", { name: "Research coverage", level: 2 })).toBeVisible();
    await expect(rc.locator(".rc-lane")).toHaveCount(lanes.size);
    await expect(rc.locator(".lane-table tbody tr")).toHaveCount(lanes.size);
    await expect(rc.locator(".rc-summary-line")).toHaveText(new RegExp(`^${lanes.size} source groups?: .+\\.$`));
    await expect(rc.locator(".rc-summary-line")).not.toContainText(/complete|finished/);

    const newest = sys.research_log.passes.filter((p: Pass) => p.kind === "systematic").at(-1);
    if (newest.under_review) {
      await expect(rc.locator(".rc-review")).toHaveText("Additional candidates remain under review and are not shown.");
    } else {
      await expect(rc.locator(".rc-review")).toHaveCount(0);
    }
    // No count of candidates, held, rejected or accepted records anywhere in the tab, the closed pass
    // history included.
    const all = await rc.evaluate((e) => e.textContent ?? "");
    expect(all).not.toMatch(/\b(held|candidates?|rejected|accepted|duplicates?|out of scope)\s*:?\s*\d/i);
    expect(all).not.toMatch(/\d+\s+(held|candidates?)\b/i);
    expect(all).not.toMatch(/\biteration\b/i);

    // Each lane's state, in words, follows its own execution and source window.
    for (const [id, l] of lanes) {
      const card = rc.locator(".rc-lane").filter({ has: page.locator(".rc-lane-id", { hasText: new RegExp(`^${id}$`) }) });
      const state = card.locator(".rc-lane-state .rc-state-text");
      if (l.source_window === "inaccessible") await expect(state).toHaveText("Source unavailable");
      else if (l.stopped_by === "search_limit") await expect(state).toHaveText("Stopped at this site's search limit");
      if (!["enumerated_complete", "declared_search_complete"].includes(l.execution ?? "")) {
        await expect(state).not.toHaveText(DONE_TEXT);
      }
    }
    expect(app.errors).toEqual([]);
  });

  test("us: many lanes, each with its source, languages, window and state; legend explains each state once", async ({ app, page }) => {
    await openResearch(app, "us");
    const sys = await system(page, "us");
    const lanes = latest(sys.research_log.passes);
    expect(lanes.size).toBeGreaterThanOrEqual(5);
    const rc = page.locator("section.rc");
    await expect(rc.locator(".rc-lane")).toHaveCount(lanes.size);

    // The legend: every state once, as text with its own shape.
    const legend = rc.locator(".rc-legend");
    for (const s of STATES) await expect(legend.locator("dt", { hasText: s })).toHaveCount(1);
    await expect(legend).toContainText("This can be a truthful end state");
    const shapes = await legend.locator("dt svg").evaluateAll((svgs) => svgs.map((s) => s.innerHTML));
    expect(new Set(shapes).size).toBe(shapes.length);
    // One colour for every state: the shapes are not a traffic light.
    const colours = await legend.locator("dt .rc-icon").evaluateAll((els) => els.map((e) => getComputedStyle(e).color));
    expect(new Set(colours).size).toBe(1);

    let blocked = 0, stopped = 0;
    for (const [id, l] of lanes) {
      const card = rc.locator(".rc-lane").filter({ has: page.locator(".rc-lane-id", { hasText: new RegExp(`^${id}$`) }) });
      await expect(card).toHaveCount(1);
      await expect(card.locator("dt", { hasText: "Languages" })).toBeVisible();
      await expect(card.locator("dt", { hasText: "Search window" })).toBeVisible();
      await expect(card.locator("dt", { hasText: "Covered through" })).toBeVisible();
      const state = card.locator(".rc-lane-state .rc-state-text");
      if (l.source_window === "inaccessible") { await expect(state).toHaveText("Source unavailable"); blocked += 1; }
      else if (l.stopped_by === "search_limit") { await expect(state).toHaveText("Stopped at this site's search limit"); stopped += 1; }
      const missing = (l.languages_required ?? []).filter((x) => !(l.languages_executed ?? []).includes(x));
      await expect(card.locator(".rc-missing")).toHaveCount(missing.length ? 1 : 0);
    }
    expect(blocked + stopped).toBeGreaterThan(0);
    const n = sys.research_freshness;
    // The tab's line is the country header's line: one vocabulary, the build's counts.
    await expect(rc.locator(".rc-summary-line")).toHaveText(new RegExp(`^${n.lanes_declared} source groups: `));
    const header = await page.locator(".research-status .lane-state-line").textContent();
    await expect(rc.locator(".rc-summary-line")).toHaveText(header!);
    // No coverage percentage in the explorer's own summary and overview.
    await expect(rc.locator(".rc-overview")).not.toContainText("%");
    await expect(rc.locator(".lane-table")).not.toContainText("%");

    // Research coverage and source health stay apart, and say so.
    await expect(rc.locator(".rc-distinct")).toContainText("Neither implies the other.");
    const sh = rc.locator(".rc-source-health");
    await expect(sh.getByRole("heading")).toHaveText(/^Source health/);
    await expect(sh).toContainText("Not part of research coverage.");
    await expect(rc.locator(".rc-lanes .rc-source-health, .rc-overview .rc-source-health")).toHaveCount(0);

    // Keyboard: an overview button moves focus to its lane card; the legend toggles from the keyboard.
    const first = [...lanes.keys()][0];
    await rc.getByRole("button", { name: `${first}: go to source group details` }).focus();
    await page.keyboard.press("Enter");
    await expect(rc.locator(".rc-lane").first()).toBeFocused();
    await legend.locator("summary").focus();
    await page.keyboard.press("Enter");
    await expect(legend).not.toHaveAttribute("open", "");
    await page.keyboard.press("Enter");
    await expect(legend).toHaveAttribute("open", "");
    expect(app.errors).toEqual([]);
  });

  for (const id of ["ir", "us"]) {
    test(`${id} at 390px: lanes stack as cards with no sideways scroll`, async ({ app, page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      await openResearch(app, id);
      const rc = page.locator("section.rc");
      const cards = rc.locator(".rc-lane");
      expect(await cards.count()).toBeGreaterThan(0);
      const boxes = await cards.evaluateAll((els) => els.map((e) => e.getBoundingClientRect()).map((r) => ({ x: r.x, w: r.width, y: r.y })));
      for (const b of boxes) {
        expect(b.x).toBeGreaterThanOrEqual(0);
        expect(b.x + b.w).toBeLessThanOrEqual(390);
      }
      // Stacked: each card starts below the one before it.
      for (let i = 1; i < boxes.length; i++) expect(boxes[i].y).toBeGreaterThan(boxes[i - 1].y);
      const sideways = await page.evaluate(() =>
        Math.max(document.documentElement.scrollWidth - window.innerWidth,
                 ...[...document.querySelectorAll(".global-page, section.rc")].map((e) => e.scrollWidth - e.clientWidth)));
      expect(sideways).toBeLessThanOrEqual(1);
      await expect(rc.locator(".rc-summary-line")).toBeVisible();
      expect(app.errors).toEqual([]);
    });
  }
});
