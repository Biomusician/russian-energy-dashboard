import { useEffect, useRef, useState } from "react";
import { readDismissed, takeStartHereRequest, writeDismissed } from "./startHereMemory";
import { START_HERE_EVENT, openGlossary } from "./GlobalNav";
import { navigate, navigateGroup } from "./router";

/** "Start here": six things a first-time reader needs, on the page rather than in a modal.
 *  Dismissing it is remembered in this browser only; "How to read this" brings it back. */
export default function StartHere({ gulfSlug, gulfLabel }: { gulfSlug: string | null; gulfLabel: string | null }) {
  const [open, setOpen] = useState(() => takeStartHereRequest() || !readDismissed());
  const [note, setNote] = useState("");
  const headRef = useRef<HTMLHeadingElement | null>(null);

  useEffect(() => {
    const reopen = () => {
      writeDismissed(false);
      setOpen(true);
      setNote("");
      window.setTimeout(() => {
        headRef.current?.focus();
        headRef.current?.scrollIntoView?.({ block: "nearest" });
      }, 0);
    };
    window.addEventListener(START_HERE_EVENT, reopen);
    return () => window.removeEventListener(START_HERE_EVENT, reopen);
  }, []);

  // Opened from another view: move focus to it so the reader lands on what they asked for.
  useEffect(() => {
    if (open && document.activeElement === document.body) headRef.current?.focus();
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  const dismiss = () => {
    const saved = writeDismissed(true);
    setOpen(false);
    setNote(saved ? "Start here is hidden. Reopen it with “How to read this”."
      : "Start here is hidden for now. This browser would not save the choice, so it will show again next time.");
  };

  return (
    <>
      <span className="sr-only" role="status" aria-live="polite">{note}</span>
      {open && (
        <section className="start-here panel" aria-labelledby="start-here-title">
          <div className="start-here-head">
            <h2 id="start-here-title" ref={headRef} tabIndex={-1}>Start here: how to read this site</h2>
            <button className="ghost" type="button" onClick={dismiss}>Dismiss</button>
          </div>
          <ol className="start-here-list">
            <li><strong>One system has an index.</strong> The Russia, Belarus &amp; Crimea theatre is the only system with a
              score, the exposure index (ESDI).</li>
            <li><strong>The other systems are countries with evidence and context, and no score.</strong> Each shows reviewed
              reports of major disruptions and sourced background.</li>
            <li><strong>No index is not zero.</strong> A country without an index has no figure computed; it is not rated
              as calm or safe.</li>
            <li><strong>Research coverage differs by country.</strong> Some are research previews. A missing record is not
              evidence that nothing happened.</li>
            <li><strong>National energy context is not disruption.</strong> Production and consumption figures describe an
              energy system; they say nothing about damage or importance.</li>
            <li><strong>Maps mean different things by view.</strong> The world map is coloured by a national energy figure;
              a country map is coloured by where records were placed; the theatre map shows exposure. Each map's legend says which.</li>
          </ol>
          <div className="start-here-next">
            <span className="small dim">What to open next:</span>
            <button className="ghost" type="button" onClick={() => navigate("ru")}>The indexed theatre</button>
            {gulfSlug && <button className="ghost" type="button" onClick={() => navigateGroup(gulfSlug)}>The {gulfLabel} overview</button>}
            <button className="ghost" type="button" onClick={() => openGlossary("how-it-works")}>How this works</button>
          </div>
        </section>
      )}
    </>
  );
}
