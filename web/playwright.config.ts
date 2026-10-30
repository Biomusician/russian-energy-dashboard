import { defineConfig, devices } from "@playwright/test";

/**
 * The real-browser test tier.
 *
 * WHY THIS EXISTS. Iterations 11, 12 and 13 each shipped a defect that only a real browser could
 * see — an exported PNG with no map in it, a staleness banner covering the words "NOT CURRENT",
 * "has not rebuilt in 11 days ago" — and each time the unit suite was green, because vitest runs
 * in node with no DOM and no WebGL. The lesson was written down three times: testing the layer
 * before the shipped layer is not enough. This is the shipped layer.
 *
 * WHAT IT RUNS AGAINST. By default, a production build served by `vite preview` — the same
 * bundle Vercel serves, not the dev server with its HMR and unminified React. Set
 * E2E_BASE_URL to point the identical suite at a deployed site, e.g. production.
 *
 * WHY 1.62.0 EXACTLY. That release pins chromium-1234, which is already in the machine's
 * Playwright cache, so the suite runs with no browser download. package.json pins it without a
 * caret for the same reason: a minor bump would ask for a different Chromium.
 */

const BASE = process.env.E2E_BASE_URL;
const PORT = 4178;

export default defineConfig({
  testDir: "./e2e",
  // `.e2e.ts`, not `.spec.ts`: vitest's default glob claims every *.spec.ts and would try to run
  // these in node, where there is no browser.
  testMatch: /.*\.e2e\.ts$/,
  outputDir: "./e2e-results",
  snapshotPathTemplate: "{testDir}/__screenshots__/{testFilePath}/{arg}-{platform}{ext}",
  timeout: 90_000,
  expect: { timeout: 20_000 },
  // One worker. Software WebGL is CPU-bound, and two maps rendering at once on one machine
  // makes timings meaningless and readiness flaky.
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { outputFolder: "e2e-report", open: "never" }]],
  use: {
    ...devices["Desktop Chrome"],
    baseURL: BASE ?? `http://127.0.0.1:${PORT}`,
    viewport: { width: 1600, height: 900 },
    acceptDownloads: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    // Analytical dates are ISO calendar days and must never move with the reader's clock. A
    // fixed zone makes any test that depends on "today" deterministic and catches the class of
    // bug where UTC and local dates disagree on one page (iteration 12 found one).
    timezoneId: "UTC",
    launchOptions: {
      // Headless Chromium has no GPU. SwiftShader gives MapLibre a real WebGL context in
      // software; recent Chrome requires the explicit opt-in to keep using it.
      args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
    },
  },
  projects: [{ name: "chromium" }],
  webServer: BASE
    ? undefined
    : {
        command: `npm run preview -- --port ${PORT} --strictPort --host 127.0.0.1`,
        url: `http://127.0.0.1:${PORT}`,
        reuseExistingServer: !process.env.CI,
        timeout: 60_000,
      },
});
