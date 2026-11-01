import { test as base, expect, type Page, type ConsoleMessage } from "@playwright/test";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

/**
 * Shared harness for the real-browser tier.
 *
 * Every test gets an `app` that has already collected console errors and uncaught page errors
 * from the moment the page opened, and fails the test at the end if there were any. A console
 * error the reader never sees is still a defect, and checking for them once per feature is the
 * kind of check that gets forgotten.
 */

export type PixelStats = { width: number; height: number; distinct: number; spread: number };

export class App {
  readonly errors: string[] = [];
  private allowed: RegExp[] = [];

  constructor(readonly page: Page) {
    page.on("console", (msg: ConsoleMessage) => {
      if (msg.type() === "error" && !this.allowed.some((r) => r.test(msg.text()))) {
        this.errors.push(`console: ${msg.text()}`);
      }
    });
    page.on("pageerror", (err) => this.errors.push(`pageerror: ${err.message}`));
  }

  /** A test that deliberately breaks something (a failed fetch) declares the exact console line
   *  it expects. Everything else still fails the test. */
  allowConsoleError(pattern: RegExp) {
    this.allowed.push(pattern);
  }

  /** Open the app at `query` and wait until the map has genuinely finished drawing.
   *  The default is the Russia theatre: since iteration 14 a bare URL is the global home. */
  async open(query = "?sys=ru") {
    await this.page.goto(`/${query}`);
    await this.mapIdle();
  }

  /** MapLibre's own `idle` event, surfaced on the container. Not a timeout guess. */
  async mapIdle() {
    await expect(this.page.locator('[data-map-state="idle"]')).toHaveCount(1, { timeout: 45_000 });
  }

  button(name: string | RegExp, opts: { exact?: boolean } = {}) {
    return this.page.getByRole("button", { name, ...opts });
  }

  /**
   * Pixel statistics of the rendered map, from a real screenshot of the map container.
   *
   * WebGL canvases default to preserveDrawingBuffer: false, so reading the canvas back with
   * toDataURL can return a blank image even when the map is drawn. A screenshot is what the
   * reader sees, which is the thing being tested.
   */
  async mapPixels(): Promise<PixelStats> {
    const box = this.page.locator('[data-map-state]').first();
    const png = await box.screenshot();
    return pixelStats(this.page, png);
  }
}

/**
 * Decode a PNG in the browser and summarise its pixels.
 *
 * Done in the page rather than in node because the project has no PNG decoder dependency and
 * the browser has a perfectly good one. `distinct` counts quantised colours and `spread` the
 * luminance range: a blank or single-colour image scores near 1 and 0.
 */
export async function pixelStats(page: Page, png: Buffer, region?: [number, number, number, number]) {
  const b64 = png.toString("base64");
  return page.evaluate(async ({ b64, region }) => {
    const img = new Image();
    img.src = `data:image/png;base64,${b64}`;
    await img.decode();
    const c = document.createElement("canvas");
    c.width = img.naturalWidth;
    c.height = img.naturalHeight;
    const ctx = c.getContext("2d")!;
    ctx.drawImage(img, 0, 0);
    const [x, y, w, h] = region ?? [0, 0, c.width, c.height];
    const data = ctx.getImageData(x, y, w, h).data;
    const seen = new Set<number>();
    let lo = 255;
    let hi = 0;
    // Sample every 7th pixel: plenty for these statistics, and fast on a 1600px export.
    for (let i = 0; i < data.length; i += 4 * 7) {
      const r = data[i], g = data[i + 1], bl = data[i + 2];
      seen.add(((r >> 4) << 8) | ((g >> 4) << 4) | (bl >> 4));
      const lum = (r * 299 + g * 587 + bl * 114) / 1000;
      if (lum < lo) lo = lum;
      if (lum > hi) hi = lum;
    }
    return { width: c.width, height: c.height, distinct: seen.size, spread: Math.round(hi - lo) };
  }, { b64, region });
}

/**
 * The mean colour of each cell in a coarse grid over a PNG (iteration 16).
 *
 * WHY. The pixel goldens are recorded on Windows and Linux renders fonts and anti-aliasing
 * differently, so CI could not catch a catastrophic visual failure at all. Cell means over a
 * coarse grid are insensitive to text and edge rendering but change completely when the map is
 * blank, drawn at the wrong extent, or painted the wrong colours.
 */
export async function colourGrid(page: Page, png: Buffer, cols = 8, rows = 5): Promise<number[][]> {
  const b64 = png.toString("base64");
  return page.evaluate(async ({ b64, cols, rows }) => {
    const img = new Image();
    img.src = `data:image/png;base64,${b64}`;
    await img.decode();
    const c = document.createElement("canvas");
    c.width = img.naturalWidth;
    c.height = img.naturalHeight;
    const ctx = c.getContext("2d")!;
    ctx.drawImage(img, 0, 0);
    const out: number[][] = [];
    const cw = Math.floor(c.width / cols), ch = Math.floor(c.height / rows);
    for (let j = 0; j < rows; j++) {
      for (let i = 0; i < cols; i++) {
        const d = ctx.getImageData(i * cw, j * ch, cw, ch).data;
        let r = 0, g = 0, b = 0, n = 0;
        for (let k = 0; k < d.length; k += 4 * 5) { r += d[k]; g += d[k + 1]; b += d[k + 2]; n++; }
        out.push([Math.round(r / n), Math.round(g / n), Math.round(b / n)]);
      }
    }
    return out;
  }, { b64, cols, rows });
}

export function readBytes(path: string): Buffer {
  return readFileSync(path);
}

/** Read a recorded structure profile, or record it when UPDATE_STRUCTURE=1 (any platform). */
export function structureProfile(path: string, current: number[][]): number[][] | null {
  if (process.env.UPDATE_STRUCTURE === "1" || !existsSync(path)) {
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, JSON.stringify(current) + "\n", "utf-8");
    return null;
  }
  return JSON.parse(readFileSync(path, "utf-8"));
}

/** Read a recorded structure profile without ever writing one (for negative controls). */
export function readStructure(path: string): number[][] | null {
  return existsSync(path) ? JSON.parse(readFileSync(path, "utf-8")) : null;
}

export const test = base.extend<{ app: App }>({
  app: async ({ page }, use) => {
    const app = new App(page);
    await use(app);
    // Every test, every feature: a console error fails it. The allow-list is deliberately empty.
    expect(app.errors, `console or page errors during the test:\n${app.errors.join("\n")}`).toEqual([]);
  },
});

export { expect };
