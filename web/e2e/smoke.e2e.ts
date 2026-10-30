import { test, expect } from "./fixtures";

test("the app boots, the map draws, and the headline carries its date", async ({ app, page }) => {
  await app.open();
  await expect(page).toHaveTitle(/Energy Disruption Monitor/);
  await expect(page.locator("main")).toHaveCount(1);

  // The map must actually be drawn, not merely present. A blank WebGL canvas is the exact
  // failure a DOM-only test cannot see.
  const px = await app.mapPixels();
  expect(px.width).toBeGreaterThan(400);
  expect(px.distinct, "the map rendered as (nearly) one flat colour").toBeGreaterThan(20);
  expect(px.spread, "the map has no luminance contrast — nothing was drawn").toBeGreaterThan(40);

  // The ribbon states which day the analysis is for. The date itself moves daily, so the test
  // asserts the shape and that it matches the payload the page loaded, not a hardcoded value.
  const snap = await page.evaluate(async () => (await fetch("/data/snapshot.json")).json());
  const day = new Date(`${snap.as_of}T00:00:00Z`).toLocaleDateString("en-GB",
    { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
  await expect(page.locator("header").first()).toContainText(day);
  // The headline shows one decimal: a second would claim a precision the modelled decay does not
  // support (its own sensitivity sweep spans more than 3x).
  await expect(page.locator("header").first()).toContainText(Number(snap.esdi).toFixed(1));
});
