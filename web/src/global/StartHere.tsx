import { useState } from "react";
import { readDismissed, writeDismissed } from "./startHereMemory";
import { impactsHref, navigate, navigateGroup, navigateTo } from "./router";
import { START_HERE } from "./help/glossary";
import { LearnMore } from "./help/LearnMore";

/** "Start here": six things a first-time reader needs, on the page rather than in a modal.
 *  Dismissing it is remembered in this browser only. The same six points open the Help page
 *  (iteration 23), which is where a reader who dismissed the panel finds them again. */
export default function StartHere({ gulfSlug, gulfLabel }: { gulfSlug: string | null; gulfLabel: string | null }) {
  const [open, setOpen] = useState(() => !readDismissed());
  const [note, setNote] = useState("");

  const dismiss = () => {
    const saved = writeDismissed(true);
    setOpen(false);
    setNote(saved ? "Start here is hidden. The same points are at the top of Help."
      : "Start here is hidden for now. This browser would not save the choice, so it will show again next time.");
  };

  return (
    <>
      <span className="sr-only" role="status" aria-live="polite">{note}</span>
      {open && (
        <section className="start-here panel" aria-labelledby="start-here-title">
          <div className="start-here-head">
            <h2 id="start-here-title" tabIndex={-1}>Start here: how to read this site</h2>
            <button className="ghost" type="button" onClick={dismiss}>Dismiss</button>
          </div>
          <ol className="start-here-list">
            {START_HERE.map((p) => <li key={p.title}><strong>{p.title}</strong> {p.text}</li>)}
          </ol>
          <p className="small start-here-impacts">
            A separate <a href={impactsHref()} onClick={(e) => { e.preventDefault(); navigateTo(impactsHref()); }}>Impact atlas</a> lists
            reviewed reports of disruptions to energy and essential civilian services in any country, with who is said to be
            responsible and how strong the evidence is; it has no score and is not a census.
          </p>
          <div className="start-here-next">
            <span className="small dim">What to open next:</span>
            <button className="ghost" type="button" onClick={() => navigate("ru")}>The indexed area</button>
            {gulfSlug && <button className="ghost" type="button" onClick={() => navigateGroup(gulfSlug)}>The {gulfLabel} overview</button>}
            <LearnMore anchor="how-it-works" label="How this works" className="start-here-how" />
          </div>
        </section>
      )}
    </>
  );
}
