import { test, expect } from "./fixtures";

/**
 * Phone, keyboard and screen-reader regressions (iteration 21, mobile + accessibility pass).
 *
 * Each block fixes one CLASS of defect that was found by using the built app at 390, 768 and
 * 1440 px wide and at 200% zoom, and asserts the structural property across every view rather
 * than one example: no content off the side of a phone, 44 px targets on primary controls, one
 * h1 and one main landmark, no two controls sharing a confusable name, Escape closing every
 * disclosure and dialog with focus returned, no motion when the reader asked for none, and a
 * usable theatre at 200% zoom. Every loop asserts it checked something.
 */

type Page = import("@playwright/test").Page;

const VIEWS = ["", "?sys=ru", "?sys=us", "?sys=sa", "?sys=bh", "?sys=ir", "?group=gulf", "?compare=us,ca,sa", "?help=glossary"];
const PHONE = { width: 390, height: 844 };

/** Open a view and wait until it has drawn: the map's own idle event, or the compare table. */
async function openView(page: Page, q: string) {
  await page.goto(`/${q}`);
  if (q.startsWith("?compare")) {
    await expect(page.locator(".compare-colhead > a").first()).toBeVisible();
    await expect(page.locator('tr[data-row="lanes"] td').first()).not.toHaveText("Loading…");
  } else {
    await expect(page.locator('[data-map-state="idle"]')).toHaveCount(1, { timeout: 45_000 });
  }
}

/** Visible leaf content that ends past the viewport edge and is not inside a sideways scroller.
 *  Map labels are excluded: a map is a 2-D surface and its place names run off its edges. */
async function offTheSide(page: Page): Promise<{ checked: number; out: string[] }> {
  return page.evaluate(() => {
    const W = window.innerWidth;
    const out: string[] = [];
    let checked = 0;
    for (const el of document.querySelectorAll<HTMLElement>("body *")) {
      if (el.children.length > 0 || el.closest(".maplibregl-map, .geo-label, dialog:not([open])")) continue;
      const s = getComputedStyle(el);
      if (s.display === "none" || s.visibility === "hidden") continue;
      const b = el.getBoundingClientRect();
      if (!b.width || !b.height || !(el.textContent?.trim() || el.matches("button,input,select,a"))) continue;
      if (el.closest(".sr-only")) continue;
      checked++;
      if (b.right <= W + 1 && b.left >= -1) continue;
      let p = el.parentElement;
      let reachable = false;
      while (p && p !== document.body) {
        const o = getComputedStyle(p).overflowX;
        if (o === "auto" || o === "scroll") { reachable = true; break; }
        p = p.parentElement;
      }
      if (!reachable) out.push(`${el.tagName.toLowerCase()}.${el.className} "${el.textContent?.trim().slice(0, 30)}" [${Math.round(b.left)},${Math.round(b.right)}]`);
    }
    return { checked, out };
  });
}

test.describe("phone width: nothing off the side", () => {
  for (const q of VIEWS) {
    test(`${q || "home"} at 390 has no page-level sideways overflow and no clipped content`, async ({ app, page }) => {
      await page.setViewportSize(PHONE);
      await openView(page, q);
      const page_ = await page.evaluate(() => Math.max(document.documentElement.scrollWidth - window.innerWidth,
        ...[...document.querySelectorAll(".global-page")].map((e) => e.scrollWidth - e.clientWidth)));
      expect(page_, "the page scrolls sideways").toBeLessThanOrEqual(1);
      const r = await offTheSide(page);
      expect(r.checked, "no visible content was checked").toBeGreaterThan(20);
      expect(r.out, "content past the edge of a 390 px screen").toEqual([]);
      expect(app.errors).toEqual([]);
    });
  }
});

// The controls a reader uses to move around and act. Inline explanations inside a sentence are
// exempt by design (they reach 24 px, the AA size); see styles/touch.css.
const PRIMARY = [
  ".global-nav-tools button", ".gsearch input", ".global-page .sys-switch select", ".home-action", ".sys-card button.ghost",
  ".start-here button", ".page-title .head-actions button", ".country-side .tabs button", ".ev-inspector-toggle",
  ".member-btn", ".compare-col-actions button", ".compare-picker select", ".map-tool",
  ".drawer-btn", ".legend-toggle", ".camera-controls button", "button.play",
  ".maplibregl-ctrl-zoom-in", ".maplibregl-ctrl-zoom-out",
].join(", ");
// The theatre header's controls: 24 px (AA), not 44, because the header's height is capped so the
// map keeps a phone screen (theatre-ux.e2e.ts asserts the cap). See styles/touch.css.
const THEATRE_HEADER = [".mode-switch button", ".tb-tools-toggle", ".theatre-bar .sys-switch select", ".why-btn", ".ribbon-more-toggle"].join(", ");

test.describe("phone width: 44 px touch targets", () => {
  for (const q of VIEWS.filter((v) => v !== "?help=glossary")) {
    test(`${q || "home"}: every visible primary control is at least 44 x 44`, async ({ page }) => {
      await page.setViewportSize(PHONE);
      await openView(page, q);
      const r = await page.evaluate((sel) => {
        const small: string[] = [];
        let checked = 0;
        for (const el of document.querySelectorAll<HTMLElement>(sel)) {
          const s = getComputedStyle(el);
          const b = el.getBoundingClientRect();
          if (s.display === "none" || s.visibility === "hidden" || !b.width) continue;
          checked++;
          if (b.height < 43.5 || b.width < 43.5) small.push(`${el.className} "${el.textContent?.trim().slice(0, 30)}" ${Math.round(b.width)}x${Math.round(b.height)}`);
        }
        return { checked, small };
      }, PRIMARY);
      expect(r.checked, "no primary control was found").toBeGreaterThan(2);
      expect(r.small).toEqual([]);
    });
  }

  test("the theatre header's controls reach 24 px and the header stays under a third of the screen", async ({ page }) => {
    await page.setViewportSize(PHONE);
    await openView(page, "?sys=ru");
    const heights = await page.locator(THEATRE_HEADER).evaluateAll((els) => els
      .filter((e) => getComputedStyle(e).display !== "none")
      .map((e) => Math.min(e.getBoundingClientRect().height, e.getBoundingClientRect().width)));
    expect(heights.length).toBeGreaterThanOrEqual(5);
    for (const h of heights) expect(h).toBeGreaterThanOrEqual(23.5);
    const header = (await page.locator(".theatre-ribbon").boundingBox())!;
    expect(header.height).toBeLessThan(PHONE.height * 0.31);
  });

  test("inline disclosures reach the 24 px AA minimum", async ({ page }) => {
    await page.setViewportSize(PHONE);
    await openView(page, "");
    const heights = await page.locator(".disclosure-button.badge, .disclosure-button.home-tag").evaluateAll(
      (els) => els.map((e) => e.getBoundingClientRect().height));
    expect(heights.length).toBeGreaterThan(0);
    for (const h of heights) expect(h).toBeGreaterThanOrEqual(23.5);
  });
});

test.describe("landmarks, headings and names", () => {
  for (const q of VIEWS) {
    test(`${q || "home"}: one h1, one main, heading levels never skip`, async ({ page }) => {
      await openView(page, q);
      await expect(page.locator("h1")).toHaveCount(1);
      await expect(page.locator("main, [role=main]")).toHaveCount(1);
      const levels = await page.locator("h1, h2, h3, h4, h5, h6").evaluateAll((els) => els
        .filter((e) => { const s = getComputedStyle(e); return s.display !== "none" && s.visibility !== "hidden" && !e.closest("dialog:not([open])"); })
        .map((e) => Number(e.tagName[1])));
      expect(levels.length).toBeGreaterThan(0);
      for (let i = 1; i < levels.length; i++) {
        expect(levels[i] - levels[i - 1], `heading h${levels[i - 1]} followed by h${levels[i]}`).toBeLessThanOrEqual(1);
      }
    });

    test(`${q || "home"}: no two buttons or disclosures share a name`, async ({ page }) => {
      await openView(page, q);
      // Excluded by design: the badge disclosures (every "Research preview" opens the same one
      // definition) and the plain-text country buttons (every "Kuwait" opens the Kuwait page).
      const names = await page.locator("button:not(.disclosure-button):not(.linklike), summary").evaluateAll((els) => els
        .filter((e) => { const s = getComputedStyle(e); return s.display !== "none" && s.visibility !== "hidden" && !e.closest("dialog:not([open])"); })
        .map((e) => {
          const label = e.getAttribute("aria-label");
          if (label) return label.trim().toLowerCase();
          const c = e.cloneNode(true) as HTMLElement;
          c.querySelectorAll("[aria-hidden=true]").forEach((x) => x.remove());
          return (c.textContent ?? "").replace(/\s+/g, " ").trim().toLowerCase();
        }));
      expect(names.length).toBeGreaterThan(2);
      const seen = new Map<string, number>();
      // Same name, same action: the bar's and the Start-here panel's "How this works" both open
      // the glossary at that entry.
      const SAME_ACTION = new Set(["how this works"]);
      for (const n of names) if (!SAME_ACTION.has(n)) seen.set(n, (seen.get(n) ?? 0) + 1);
      expect([...seen].filter(([, c]) => c > 1).map(([n, c]) => `${c}x "${n}"`)).toEqual([]);
    });

    test(`${q || "home"}: every disclosure says what it controls and every table is captioned`, async ({ page }) => {
      await openView(page, q);
      const missing = await page.locator("[aria-expanded]:not([role=combobox])").evaluateAll((els) =>
        els.filter((e) => !e.getAttribute("aria-controls")).map((e) => e.outerHTML.slice(0, 80)));
      expect(missing).toEqual([]);
      const tables = await page.locator("table").evaluateAll((els) => els.map((t) => ({
        named: !!(t.querySelector("caption")?.textContent?.trim() || t.getAttribute("aria-label") || t.getAttribute("aria-labelledby")),
        th: t.querySelectorAll("th").length,
      })));
      for (const t of tables) { expect(t.named).toBe(true); expect(t.th).toBeGreaterThan(0); }
    });
  }

  test("a country page's navigation bar stays above the map on a phone, inside the reading order", async ({ page }) => {
    await page.setViewportSize(PHONE);
    let checked = 0;
    for (const q of ["?sys=us", "?sys=bh"]) {
      await openView(page, q);
      const nav = await page.getByRole("navigation", { name: "Breadcrumb" }).boundingBox();
      const map = await page.locator("[data-map-state]").boundingBox();
      const head = await page.getByRole("heading", { level: 1 }).boundingBox();
      // One header per page: the site bar comes first, then the page title (iteration 21).
      expect(nav!.y, "the site bar should precede the page title").toBeLessThan(head!.y);
      expect(nav!.y, "the breadcrumb and search fell below the map").toBeLessThan(map!.y);
      expect(map!.y, "the map starts below the first screen").toBeLessThan(PHONE.height - 150);
      checked++;
    }
    expect(checked).toBe(2);
  });

  test("the home page does not move focus on a first visit", async ({ page }) => {
    await openView(page, "");
    await expect(page.getByRole("region", { name: /Start here/ })).toBeVisible();
    expect(await page.evaluate(() => document.activeElement === document.body)).toBe(true);
    // The first Tab reaches the top of the page, not the middle.
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Energy Disruption Monitor, home" })).toBeFocused();
  });

  test("the theatre's reading order reaches the header before the drawer toggles on the map", async ({ page }) => {
    await page.setViewportSize(PHONE);
    await openView(page, "?sys=ru");
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Home" })).toBeFocused();
  });
});

test.describe("Escape closes, focus returns", () => {
  async function escapeCloses(page: Page, opener: import("@playwright/test").Locator) {
    await opener.focus();
    await page.keyboard.press("Enter");
    await expect(opener).toHaveAttribute("aria-expanded", "true");
    await page.keyboard.press("Escape");
    await expect(opener).toHaveAttribute("aria-expanded", "false");
    await expect(opener).toBeFocused();
  }

  test("badge disclosures, the evidence inspector and the theatre's toggles", async ({ app, page }) => {
    let checked = 0;
    await openView(page, "");
    await escapeCloses(page, page.locator(".disclosure-button").first()); checked++;
    await openView(page, "?sys=us");
    const toggle = page.locator(".ev-inspector-toggle").first();
    await escapeCloses(page, toggle); checked++;
    await expect(page.locator(".ev-inspector")).toHaveCount(0);
    // Below the wide layout the sector strip folds behind its toggle.
    await page.setViewportSize({ width: 1440, height: 900 });
    await openView(page, "?sys=ru");
    // Its label changes when open ("Hide sectors & recovery"), so it is found by its class.
    await escapeCloses(page, page.locator(".ribbon-more-toggle")); checked++;
    await page.setViewportSize(PHONE);
    await openView(page, "?sys=ru");
    await escapeCloses(page, page.locator(".legend-toggle")); checked++;
    for (const name of [/^Layers/, /^Overview/, "Tools"]) {
      await escapeCloses(page, page.getByRole("button", { name }).first()); checked++;
    }
    expect(checked).toBe(7);
    expect(app.errors).toEqual([]);
  });

  test("a native <details> closes on Escape and gives focus back to its summary", async ({ page }) => {
    let checked = 0;
    for (const [q, sel] of [["?compare=us,ca,sa", "details.compare-def"], ["?group=gulf", "details"], ["", "details.dq-system"]] as const) {
      await openView(page, q);
      const details = page.locator(sel).filter({ has: page.locator("summary:visible") }).first();
      const summary = details.locator("summary");
      await summary.focus();
      await page.keyboard.press("Enter");
      await expect(details).toHaveAttribute("open", "");
      await page.keyboard.press("Escape");
      await expect(details).not.toHaveAttribute("open", "");
      await expect(summary).toBeFocused();
      checked++;
    }
    expect(checked).toBe(3);
  });

  test("the theatre's tool menu returns focus to its toggle, and a modal opened from it returns there too", async ({ page }) => {
    await page.setViewportSize(PHONE);
    await openView(page, "?sys=ru");
    const tools = page.getByRole("button", { name: "Tools" });
    await tools.focus();
    await page.keyboard.press("Enter");
    await page.keyboard.press("Tab");
    await expect(page.locator(".tb-tools button").first()).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(tools).toHaveAttribute("aria-expanded", "false");
    await expect(tools).toBeFocused();
    // Methodology from the menu: focus moves into the dialog, then comes back to the toggle.
    await page.keyboard.press("Enter");
    await page.locator(".tb-tools").getByRole("button", { name: "Methodology & caveats" }).focus();
    await page.keyboard.press("Enter");
    const dlg = page.getByRole("dialog", { name: "Methodology and caveats" });
    await expect(dlg).toBeVisible();
    expect(await dlg.evaluate((d) => d.contains(document.activeElement))).toBe(true);
    await page.keyboard.press("Escape");
    await expect(dlg).toHaveCount(0);
    await expect(tools).toBeFocused();
  });

  test("the methodology dialog takes focus, keeps Tab inside, and Escape returns to its button", async ({ page }) => {
    await openView(page, "?sys=ru");
    const btn = page.getByRole("button", { name: "Methodology & caveats" });
    await btn.focus();
    await page.keyboard.press("Enter");
    const dlg = page.getByRole("dialog", { name: "Methodology and caveats" });
    await expect(dlg).toBeVisible();
    for (let i = 0; i < 25; i++) {
      await page.keyboard.press("Tab");
      expect(await dlg.evaluate((d) => d.contains(document.activeElement)), `Tab ${i + 1} left the dialog`).toBe(true);
    }
    await page.keyboard.press("Escape");
    await expect(dlg).toHaveCount(0);
    await expect(btn).toBeFocused();
  });

  test("the glossary closes on Escape from every view that has it", async ({ page }) => {
    let checked = 0;
    for (const q of ["", "?sys=us", "?group=gulf"]) {
      await openView(page, q);
      const btn = page.getByRole("button", { name: "Glossary", exact: true });
      await btn.focus();
      await page.keyboard.press("Enter");
      await expect(page.getByRole("dialog", { name: "Glossary" })).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(page.getByRole("dialog", { name: "Glossary" })).toBeHidden();
      await expect(btn).toBeFocused();
      checked++;
    }
    expect(checked).toBe(3);
  });
});

test.describe("reduced motion", () => {
  async function moving(page: Page) {
    return page.evaluate(() => {
      let checked = 0;
      const out: string[] = [];
      for (const el of document.querySelectorAll<HTMLElement>("*")) {
        checked++;
        const s = getComputedStyle(el);
        const durations = [...s.transitionDuration.split(","), ...s.animationDuration.split(",")].map((d) => parseFloat(d) || 0);
        if (durations.some((d) => d > 0)) out.push(`${el.tagName.toLowerCase()}.${String(el.className).split(" ")[0]} ${s.transitionDuration}`);
      }
      return { checked, out, smooth: getComputedStyle(document.documentElement).scrollBehavior };
    });
  }

  test("with prefers-reduced-motion, nothing on any view transitions or animates", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    for (const q of ["", "?sys=ru", "?sys=us", "?group=gulf", "?compare=us,ca"]) {
      await openView(page, q);
      const r = await moving(page);
      expect(r.checked).toBeGreaterThan(50);
      expect(r.out, `${q || "home"} still moves`).toEqual([]);
      expect(r.smooth).not.toBe("smooth");
    }
    // The drawers, the case that used to escape the old rule, opened at phone width.
    await page.setViewportSize(PHONE);
    await openView(page, "?sys=ru");
    await page.getByRole("button", { name: /^Layers/ }).click();
    expect(await page.locator(".filters").evaluate((e) => getComputedStyle(e).transitionDuration)).toBe("0s");
  });

  test("control: without the preference the drawers do slide, so the check above can fail", async ({ page }) => {
    await page.setViewportSize(PHONE);
    await openView(page, "?sys=ru");
    const d = await page.locator(".filters").evaluate((e) => getComputedStyle(e).transitionDuration);
    expect(d.split(",").some((x) => parseFloat(x) > 0)).toBe(true);
  });
});

test.describe("200% zoom", () => {
  test("the theatre at 720x450 keeps every ribbon figure readable and the map usable", async ({ app, page }) => {
    await page.setViewportSize({ width: 720, height: 450 });
    await openView(page, "?sys=ru");
    const ribbon = (await page.locator(".ribbon").boundingBox())!;
    const map = (await page.locator("[data-map-state]").boundingBox())!;
    const legend = (await page.locator(".map-legend").boundingBox())!;
    expect(map.height, "map row").toBeGreaterThanOrEqual(300);
    expect(legend.y, "the legend is drawn over the ribbon").toBeGreaterThanOrEqual(ribbon.y + ribbon.height - 1);
    // The page scrolls down, never sideways.
    const doc = await page.evaluate(() => ({ w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight }));
    expect(doc.w).toBeLessThanOrEqual(720);
    expect(doc.h).toBeGreaterThan(450);
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    await expect(page.locator("button.play")).toBeInViewport();
    expect(app.errors).toEqual([]);
  });

  test("the document views at 720 px wide keep their content on screen", async ({ page }) => {
    await page.setViewportSize({ width: 720, height: 450 });
    let checked = 0;
    for (const q of ["", "?sys=us", "?sys=bh", "?group=gulf", "?compare=us,ca,sa"]) {
      await openView(page, q);
      const r = await offTheSide(page);
      expect(r.checked).toBeGreaterThan(20);
      expect(r.out, q || "home").toEqual([]);
      checked++;
    }
    expect(checked).toBe(5);
  });

  test("the theatre legend never covers the attribution strip", async ({ page }) => {
    let checked = 0;
    for (const size of [{ width: 768, height: 1024 }, { width: 1440, height: 900 }]) {
      await page.setViewportSize(size);
      await openView(page, "?sys=ru");
      const legend = (await page.locator(".map-legend").boundingBox())!;
      const attrib = (await page.locator(".maplibregl-ctrl-attrib").boundingBox())!;
      const overlap = legend.x < attrib.x + attrib.width && attrib.x < legend.x + legend.width
        && legend.y < attrib.y + attrib.height && attrib.y < legend.y + legend.height;
      expect(overlap, `legend over attribution at ${size.width}`).toBe(false);
      checked++;
    }
    expect(checked).toBe(2);
  });
});
