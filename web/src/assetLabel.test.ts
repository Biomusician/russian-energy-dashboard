import { describe, expect, it } from "vitest";
import { assetLabel } from "./data";

// Iteration 17 defect: nine contributing facilities printed as raw internal ids in the
// comparison workspace. A reader-facing label is a name, a label derived from the slug, or
// "Unknown asset" -- never the id itself.
describe("assetLabel", () => {
  it("prefers the first name any source gives", () => {
    expect(assetLabel("kuibyshev-refinery", null, "Kuibyshev refinery", "other")).toBe("Kuibyshev refinery");
    expect(assetLabel("x", "  ", undefined, "Named")).toBe("Named");
  });

  it("derives a readable label from the slug when nothing names it", () => {
    expect(assetLabel("tikhoretsk-oil-pumping-station")).toBe("Tikhoretsk oil pumping station");
    expect(assetLabel("novobryanskaya-substation-750kv")).toBe("Novobryanskaya substation 750kv");
    // An incident-style id keeps the facility and drops the date suffix.
    expect(assetLabel("moscow-refinery:2026-06-18")).toBe("Moscow refinery");
  });

  it("says Unknown asset rather than printing an id with no words in it", () => {
    expect(assetLabel("")).toBe("Unknown asset");
    expect(assetLabel("2026-01")).toBe("Unknown asset");
  });

  it("keeps a multi-line complex name to its first line", () => {
    expect(assetLabel("ust-luga", "Ust-Luga Multimodal Complex\n* terminal")).toBe("Ust-Luga Multimodal Complex (+1)");
  });
});
