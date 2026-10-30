import { test as base, expect, type Page, type ConsoleMessage } from "@playwright/test";
import { readFileSync } from "node:fs";

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

  constructor(readonly page: Page) {
    page.on("console", (msg: ConsoleMessage) => {
      if (msg.type() === "error") this.errors.push(`console: ${msg.text()}`);
    });
    page.on("pageerror", (err) => this.errors.push(`pageerror: ${err.message}`));
  }

  /** Open the app at `query` and wait until the map has genuinely finished drawing. */
  async open(query = "") {
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

export function readBytes(path: string): Buffer {
  return readFileSync(path);
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
