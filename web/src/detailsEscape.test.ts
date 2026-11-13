import { describe, expect, it } from "vitest";
import { closeFocusedDetails } from "./detailsEscape";

// Node has no DOM: the few members the handler touches are faked. The browser behaviour is
// covered in e2e/a11y-mobile.e2e.ts; this pins the decision rules.
function fake({ inDialog = false, open = true } = {}) {
  let focused = false;
  const summary = { focus: () => { focused = true; } };
  const details = {
    open,
    closest: (sel: string) => (sel === "dialog" && inDialog ? {} : null),
    querySelector: () => summary,
  };
  const active = { closest: (sel: string) => (sel === "details[open]" && details.open ? details : null) };
  const doc = { activeElement: active } as unknown as Document;
  let prevented = false;
  let stopped = false;
  const ev = (key = "Escape", defaultPrevented = false) => ({
    key, defaultPrevented,
    preventDefault: () => { prevented = true; },
    stopPropagation: () => { stopped = true; },
  }) as unknown as KeyboardEvent;
  return { doc, details, ev, state: () => ({ focused, prevented, stopped }) };
}

describe("Escape on an open <details>", () => {
  it("closes it, focuses its summary and consumes the key", () => {
    const f = fake();
    expect(closeFocusedDetails(f.ev(), f.doc)).toBe(true);
    expect(f.details.open).toBe(false);
    expect(f.state()).toEqual({ focused: true, prevented: true, stopped: true });
  });

  it("leaves a disclosure inside a modal dialog to the dialog's own Escape", () => {
    const f = fake({ inDialog: true });
    expect(closeFocusedDetails(f.ev(), f.doc)).toBe(false);
    expect(f.details.open).toBe(true);
    expect(f.state().prevented).toBe(false);
  });

  it("ignores other keys, closed disclosures and keys a component already handled", () => {
    const a = fake();
    expect(closeFocusedDetails(a.ev("Enter"), a.doc)).toBe(false);
    const b = fake({ open: false });
    expect(closeFocusedDetails(b.ev(), b.doc)).toBe(false);
    const c = fake();
    expect(closeFocusedDetails(c.ev("Escape", true), c.doc)).toBe(false);
    expect(c.details.open).toBe(true);
  });
});
