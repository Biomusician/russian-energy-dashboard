/** Escape closes the open <details> disclosure that holds the keyboard focus (iteration 21).
 *
 *  A native <details> opens and closes with Enter or Space on its summary, but Escape does
 *  nothing, while every other disclosure on the site (the badges, the evidence inspector, the
 *  drawers) closes on Escape. One listener covers every <details> on every view, so a new one
 *  needs no code.
 *
 *  Layering: a component that handles Escape itself stops the event before it reaches the
 *  document, so this never fights it. Inside a modal <dialog> (the glossary) Escape keeps its
 *  native meaning, closing the dialog. When this does close a disclosure it stops the event, so
 *  one key press closes one thing: a drawer around the disclosure stays open until the next. */

export function closeFocusedDetails(e: KeyboardEvent, doc: Document = document): boolean {
  if (e.key !== "Escape" || e.defaultPrevented) return false;
  const active = doc.activeElement;
  if (!active || typeof (active as Element).closest !== "function") return false;
  const details = (active as Element).closest("details[open]") as HTMLDetailsElement | null;
  if (!details || details.closest("dialog")) return false;
  details.open = false;
  details.querySelector<HTMLElement>(":scope > summary")?.focus();
  e.preventDefault();
  e.stopPropagation();
  return true;
}

export function installDetailsEscape(doc: Document = document): () => void {
  const on = (e: KeyboardEvent) => { closeFocusedDetails(e, doc); };
  doc.addEventListener("keydown", on);
  return () => doc.removeEventListener("keydown", on);
}
