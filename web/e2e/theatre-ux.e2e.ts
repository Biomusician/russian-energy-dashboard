import { test, expect, type App } from "./fixtures";
import type { Page } from "@playwright/test";

/**
 * The theatre's first-viewport UX (iteration 21), in a real browser at desktop and phone sizes.
 *
 * Values are read from the payload the page itself loaded, never hardcoded: the payload is
 * rebuilt every morning.
 */

const DESKTOP = { width: 1600, height: 900 };
const PHONE = { width: 390, height: 844 };
const SIZES = [["desktop", DESKTOP], ["phone", PHONE]] as const;

async function payload(page: Page, file: string) {
  return page.evaluate(async (f) => (await fetch(`/data/${f}`)).json(), file);
}

function within(box: { x: number; y: number; width: number; height: number } | null, vw: number, vh: number) {
  expect(box, "element has no box").not.toBeNull();
  expect(box!.x).toBeGreaterThanOrEqual(-1);
  expect(box!.y).toBeGreaterThanOrEqual(-1);
  expect(box!.x + box!.width).toBeLessThanOrEqual(vw + 1);
  expect(box!.y + box!.height).toBeLessThanOrEqual(vh + 1);
}

function overlap(a: { x: number; y: number; width: number; height: number }, b: typeof a) {
  return a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
}

/** Every URL parameter except the camera. Resizing the map (which map focus does) makes MapLibre
 *  report a camera, and the URL mirrors it — that was so before the view switch existed. What
 *  must never change is the selection, metric, layers, filters, date and comparison tray. */
function shareable(url: string): Record<string, string> {
  const p = Object.fromEntries(new URL(url).searchParams);
  delete p.cam;
  return p;
}

async function openTools(app: App, page: Page) {
  const toggle = page.locator(".tb-tools-toggle");
  if (await toggle.isVisible()) await toggle.click();
}

test.describe("where am I, and the way home", () => {
  for (const [name, size] of SIZES) {
    test(`${name}: the header names the theatre as the manifest does and Home returns to the overview`, async ({ app, page }) => {
      await page.setViewportSize(size);
      await app.open();
      const manifest = await payload(page, "global/manifest.json");
      const theatre = manifest.systems.find((s: { kind: string }) => s.kind === "theatre");
      const crumbs = page.getByRole("navigation", { name: "Breadcrumb" });
      await expect(crumbs).toBeVisible();
      await expect(crumbs.locator('[aria-current="page"]')).toHaveText(theatre.name);
      await expect(page).toHaveTitle(`Energy Disruption Monitor — ${theatre.name}`);
      await crumbs.getByRole("link", { name: "Home" }).click();
      await expect(page.getByRole("heading", { name: "Monitored systems" })).toBeVisible();
      await expect(page).not.toHaveURL(/sys=/);
      await page.goBack();
      await app.mapIdle();
      await expect(page.getByRole("navigation", { name: "Breadcrumb" })).toBeVisible();
    });
  }
});

test.describe("the headline and what it means", () => {
  for (const [name, size] of SIZES) {
    test(`${name}: "Why this number?" sits on the headline and opens the Evidence Inspector`, async ({ app, page }) => {
      await page.setViewportSize(size);
      await app.open();
      const snap = await payload(page, "snapshot.json");
      const headline = page.getByRole("region", { name: "Headline" });
      await expect(headline).toContainText(Number(snap.esdi).toFixed(1));
      await expect(headline).toContainText("0–100 exposure index");
      await expect(headline).toContainText("not measured loss");
      await expect(headline).toContainText(/peak to date \d+\.\d/);
      const why = headline.getByRole("button", { name: /why this number/i });
      within(await why.boundingBox(), size.width, size.height);
      await why.click();
      const dlg = page.getByRole("dialog", { name: /evidence inspector/i });
      await expect(dlg).toBeVisible();
      await expect(dlg).toContainText(/refining/i);
      // One precision for the headline: the Inspector says it is published to one decimal.
      await expect(dlg).toContainText(`The headline reads ${Number(snap.esdi).toFixed(1)}`);
    });
  }

  test("scrubbed to a past date, \"Why this number?\" opens that date's decomposition", async ({ app, page }) => {
    await app.open("?sys=ru&d=2024-06-01");
    await page.getByRole("region", { name: "Headline" }).getByRole("button", { name: /why this number/i }).click();
    await expect(page.getByRole("dialog", { name: /evidence inspector/i })).toContainText(/historical date/i);
  });

  for (const [w, h] of [[1600, 900], [1440, 900], [1024, 768], [390, 844]] as const) {
    test(`at ${w}x${h} both coverage ratios are on screen, at one size, and the header never scrolls sideways`, async ({ app, page }) => {
      await page.setViewportSize({ width: w, height: h });
      await app.open();
      const snap = await payload(page, "snapshot.json");
      const known = page.getByRole("region", { name: "How much is known" });
      within(await known.boundingBox(), w, h);
      await expect(known).toContainText(`${snap.coverage.enumerated_in_this_dataset} / ${snap.coverage.reported_total_strikes}`);
      await expect(known).toContainText(`${snap.incidents_with_quantified_capacity} of ${snap.incident_total}`);
      const sizes = await known.locator(".known-num").evaluateAll((els) => els.map((e) => getComputedStyle(e).fontSize));
      expect(sizes.length).toBe(2);
      expect(new Set(sizes).size, "the two ratios are at different weights").toBe(1);
      const m = await page.evaluate(() => {
        const r = document.querySelector(".theatre-ribbon") as HTMLElement;
        const clipped = [...r.querySelectorAll<HTMLElement>("*")].filter((e) =>
          e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflowX !== "visible"
          && e.tagName !== "SELECT" && e.clientWidth > 1).map((e) => e.className);
        return { clipped, height: r.getBoundingClientRect().height, page: document.documentElement.scrollWidth - innerWidth };
      });
      expect(m.clipped, "an element in the header scrolls or clips sideways").toEqual([]);
      expect(m.page).toBeLessThanOrEqual(1);
      // The map keeps the screen: the header stays well under a third of the viewport.
      expect(m.height).toBeLessThan(h * 0.31);
    });
  }

  test("every scored sector is visible with its value and a plain-language basis; narrow screens fold it behind a toggle", async ({ app, page }) => {
    await app.open();
    const snap = await payload(page, "snapshot.json");
    const strip = page.getByRole("group", { name: "Sector scores in the index" });
    const cells = strip.locator(".sector-cell.as-button");
    await expect(cells).toHaveCount(snap.sectors_covered.length);
    expect(snap.sectors_covered.length).toBeGreaterThan(0);
    for (let i = 0; i < snap.sectors_covered.length; i++) {
      const box = await cells.nth(i).boundingBox();
      expect(box!.width, "a sector cell is squeezed to nothing").toBeGreaterThan(80);
      within(box, DESKTOP.width, DESKTOP.height);
    }
    await expect(strip.getByText("event-burden proxy")).toHaveCount(
      Object.values(snap.explanations.sectors as Record<string, { basis: string }>)
        .filter((e) => e.basis === "event_burden").length);
    await expect(strip).toContainText("excluded, not zero");

    await page.setViewportSize({ width: 1024, height: 768 });
    await expect(strip).toBeHidden();
    await page.getByRole("button", { name: "Sector scores & recovery" }).click();
    await expect(strip).toBeVisible();
    await expect(page.locator(".recovery-group")).toContainText("latest build");
  });
});

test.describe("the view switch: Analyze · Map focus · Briefing", () => {
  for (const [name, size] of SIZES) {
    test(`${name}: switching views never changes the shareable URL or the selection`, async ({ app, page }) => {
      await page.setViewportSize(size);
      await app.open("?sys=ru&r=RU-PER&m=ev&ly=lines,oil&cmp=RU-SAM");
      const url = page.url();
      expect(url).toMatch(/r=RU-PER/);
      // On a phone the linked region's dossier opens as a drawer over the page; close it first.
      if (await page.locator("#dossier-panel.drawer-open").count()) await page.keyboard.press("Escape");
      const view = page.getByRole("group", { name: "View" });
      const analyze = view.getByRole("button", { name: "Analyze" });
      const focus = view.getByRole("button", { name: "Map focus" });
      const brief = view.getByRole("button", { name: "Briefing & export" });
      await expect(analyze).toHaveAttribute("aria-pressed", "true");
      const before = (await page.locator("[data-map-state]").boundingBox())!;

      await focus.click();
      await app.mapIdle();
      await expect(focus).toHaveAttribute("aria-pressed", "true");
      expect(shareable(page.url())).toEqual(shareable(url));
      const focused = (await page.locator("[data-map-state]").boundingBox())!;
      expect(focused.width * focused.height).toBeGreaterThanOrEqual(before.width * before.height);

      await brief.click();
      await expect(brief).toHaveAttribute("aria-pressed", "true");
      await expect(page.locator(".briefing-frame")).toBeVisible();
      expect(shareable(page.url())).toEqual(shareable(url));

      await analyze.click();
      await app.mapIdle();
      await expect(page.locator(".briefing-frame")).toHaveCount(0);
      await expect(analyze).toHaveAttribute("aria-pressed", "true");
      expect(shareable(page.url())).toEqual(shareable(url));
      const back = (await page.locator("[data-map-state]").boundingBox())!;
      expect(Math.round(back.width)).toBe(Math.round(before.width));
      expect(Math.round(back.height)).toBe(Math.round(before.height));
      // The selection survives (its dossier may be a closed drawer, so read the DOM, not roles).
      await expect(page.locator("#dossier-panel h2").first()).toHaveText(/perm/i);
    });
  }

  for (const [name, size] of SIZES) {
    test(`${name}: the tools lead to Compare, as home and the country pages do`, async ({ app, page }) => {
      await page.setViewportSize(size);
      await app.open();
      await openTools(app, page);
      const link = page.locator("#theatre-tools").getByRole("link", { name: "Compare systems" });
      await expect(link).toBeVisible();
      await expect(link).toHaveAttribute("href", "?compare=");
      await link.click();
      await expect(page).toHaveURL(/\?compare=$/);
      await expect(page.getByRole("heading", { name: "Compare systems" })).toBeVisible();
      await page.goBack();
      await expect(page.locator(".theatre-bar")).toBeVisible();
    });
  }

  test("phone: the tools fold behind one toggle and still open their panels", async ({ app, page }) => {
    await page.setViewportSize(PHONE);
    await app.open();
    const toggle = page.locator(".tb-tools-toggle");
    await expect(toggle).toBeVisible();
    await expect(app.button(/^data quality$/i)).toBeHidden();
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await app.button(/^data quality$/i).click();
    await expect(page.getByRole("dialog", { name: /evidence inspector/i })).toBeVisible();
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  for (const [name, size] of SIZES) {
    test(`${name}: in briefing the frame is not drawn over map controls, the legend or the scrubber`, async ({ app, page }) => {
      await page.setViewportSize(size);
      await app.open();
      const snap = await payload(page, "snapshot.json");
      await openTools(app, page);
      await page.getByRole("group", { name: "View" }).getByRole("button", { name: "Briefing & export" }).click();
      await expect(page.locator(".briefing-frame")).toBeVisible();
      await expect(page.locator(".brief-value")).toHaveText(Number(snap.esdi).toFixed(1));
      await expect(page.locator(".camera-controls")).toBeHidden();
      await expect(page.locator(".drawer-toggles").first()).toBeHidden();
      // The frame shows the scope note, so the map's duplicate is hidden — but every caveat stays.
      await expect(page.locator(".map-scope-note")).toBeHidden();
      await expect(page.locator(".brief-caveat").first()).toContainText("not measured capacity loss");
      await expect(page.locator(".brief-foot")).toContainText("Crimea is internationally recognised");
      const legend = (await page.locator(".map-legend").boundingBox())!;
      const foot = (await page.locator(".brief-foot").boundingBox())!;
      expect(overlap(legend, foot), "the footer caveats sit on the legend").toBe(false);
      const controls = (await page.locator(".brief-controls").boundingBox())!;
      const scrub = (await page.locator(".timeline input.scrub").boundingBox())!;
      expect(overlap(controls, scrub), "the briefing controls cover the scrubber").toBe(false);
      // Untick the scope note: the map's own scope note (with the Crimea statement) comes back.
      await app.button("Export options").click();
      await page.getByRole("checkbox", { name: "Scope note" }).uncheck();
      await expect(page.locator(".map-scope-note")).toBeVisible();
    });
  }
});

test.describe("phone map overlays", () => {
  test("the legend and the attribution no longer cover each other, and both open on demand", async ({ app, page }) => {
    await page.setViewportSize(PHONE);
    await app.open();
    const attrib = page.locator(".maplibregl-ctrl-attrib");
    await expect(attrib).not.toHaveClass(/maplibregl-compact-show/);
    const legend = (await page.locator(".map-legend").boundingBox())!;
    const attribBox = (await attrib.boundingBox())!;
    expect(overlap(legend, attribBox)).toBe(false);
    await expect(page.locator(".map-legend")).toContainText("Crimea");
    await page.getByRole("button", { name: "All keys" }).click();
    await expect(page.locator(".map-legend")).toContainText("Recorded events");
    await page.locator(".maplibregl-ctrl-attrib-button").click();
    await expect(attrib).toContainText("Natural Earth");
    // The presets and the scope note no longer sit on each other.
    const presets = (await page.locator(".camera-controls").boundingBox())!;
    const scope = (await page.locator(".map-scope-note").boundingBox())!;
    expect(overlap(presets, scope)).toBe(false);
  });
});

test.describe("dossier tabs at 1440 (production report)", () => {
  test("clicking each tab switches it and never slides the app sideways", async ({ app, page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await app.open();
    // The mechanism: a scroll into the CLOSED drawer used to move #root ~400px left, hiding the
    // filters rail and the system picker. Forced here directly, before any click.
    const forced = await page.evaluate(() => {
      document.querySelector("#dossier-panel [role=tab]:last-child")!.scrollIntoView();
      (document.getElementById("root") as HTMLElement).scrollLeft = 400;
      return [...document.querySelectorAll("html, body, #root, .shell")].map((e) => e.scrollLeft);
    });
    expect(forced).toEqual([0, 0, 0, 0]);
    await expect(page.locator("#dossier-panel")).toHaveCSS("visibility", "hidden");

    await page.locator('.drawer-btn[aria-controls="dossier-panel"]').click();
    await expect(page.locator("#dossier-panel")).toHaveClass(/drawer-open/);
    const tabs = page.locator("#dossier-panel [role=tab]");
    const n = await tabs.count();
    let clicked = 0;
    for (let i = 0; i < n; i++) {
      const tab = tabs.nth(i);
      await tab.scrollIntoViewIfNeeded();
      const b = (await tab.boundingBox())!;
      await page.mouse.click(b.x + Math.min(10, b.width / 2), b.y + b.height / 2);
      await expect(tab).toHaveAttribute("aria-selected", "true");
      const s = await page.evaluate(() => ({
        lefts: [...document.querySelectorAll("html, body, #root, .shell")].map((e) => e.scrollLeft),
        select: document.querySelector(".sys-switch select")!.getBoundingClientRect().left,
      }));
      expect(s.lefts).toEqual([0, 0, 0, 0]);
      expect(s.select).toBeGreaterThanOrEqual(0);
      clicked++;
    }
    expect(clicked).toBeGreaterThan(3);
  });
});

test.describe("withheld facility status (active campaign)", () => {
  test("a withheld row says only \"Status withheld\" — no modelled status chip, age or horizon", async ({ app, page }) => {
    await app.open();
    type Live = { asset_id: string; region_code: string | null; recovery: { publication_note?: string } };
    type Inc = { asset_id: string; region_code: string | null; date: string };
    const snap = await payload(page, "snapshot.json");
    const incidents: Inc[] = await payload(page, "incidents.json");
    const isWithheld = (d: Live) => (d.recovery.publication_note ?? "").startsWith("Current facility status withheld");
    const withheld: Live[] = snap.live_disruptions.filter(isWithheld);
    expect(withheld.length, "the build carries no withheld record to test against").toBeGreaterThan(0);

    // Open the region of a withheld facility, so its Recent list must contain withheld rows,
    // and work out from the payload exactly how many (the list is that region's ten latest).
    const region = withheld[0].region_code!;
    const byAsset = new Map<string, Live>(snap.live_disruptions.map((d: Live) => [d.asset_id, d]));
    const expected = incidents
      .filter((i) => i.region_code === region && i.date <= snap.as_of)
      .sort((a, b) => b.date.localeCompare(a.date)).slice(0, 10)
      .filter((i) => { const d = byAsset.get(i.asset_id); return d && isWithheld(d); }).length;
    expect(expected).toBeGreaterThan(0);

    await app.open(`?sys=ru&r=${region}`);
    await page.locator("#dossier-panel").getByRole("tab", { name: /recent/i }).click();
    const rows = page.locator("#dossier-panel .rc").filter({ has: page.locator(".withheld-status") });
    await expect(rows).toHaveCount(expected);
    for (let i = 0; i < expected; i++) {
      const row = rows.nth(i);
      await expect(row.locator(".withheld-status summary")).toHaveText("Status withheld");
      await expect(row.locator(".rc-recovery .ev")).toHaveCount(0);
      await expect(row).not.toContainText(/impaired \d+ d|modelled horizon|est\. ~|Impaired/);
    }
    // The plain meaning is one tap away.
    await rows.first().locator("summary").click();
    await expect(rows.first()).toContainText("does not publish the current condition");
  });

  test("Recent summaries read as sentences: \"an oil refinery\", never \"a oil\" or \"pipeline oil\"", async ({ app, page }) => {
    await app.open();
    await page.locator("#dossier-panel").getByRole("tab", { name: /recent/i }).click();
    const summaries = await page.locator("#dossier-panel .rc-summary").allTextContents();
    expect(summaries.length).toBeGreaterThan(0);
    for (const s of summaries) {
      expect(s).not.toMatch(/\ba [aeiou]/i);
      expect(s).not.toMatch(/pipeline oil|pipeline gas/i);
    }
  });
});

test.describe("methodology reads cleanly", () => {
  test("a five-line summary comes first, and the spliced sentence is gone", async ({ app, page }) => {
    await app.open();
    await app.button(/methodology & caveats/i).click();
    const dlg = page.getByRole("dialog", { name: /methodology and caveats/i });
    const summary = dlg.locator(".method-summary li");
    await expect(summary).toHaveCount(5);
    await expect(dlg).not.toContainText(".,");
    await expect(dlg).not.toContainText(/\d{4}-\d{2}-\d{2}/);
  });
});
