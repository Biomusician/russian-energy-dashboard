import { useId, useState } from "react";
import { RESEARCH_PREVIEW_DEFINITION, RESEARCH_PREVIEW_LABEL } from "./countryCopy";
import "../styles/country.css";

/** A label that explains itself on click or tap (iteration 21). Hover does not exist on a touch
 *  screen, so no explanation on these pages lives only in a `title` tooltip. */
export function Disclosure({ label, text, className = "" }: { label: string; text: string; className?: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <span className="disclosure">
      <button type="button" className={`disclosure-button ${className}`} aria-expanded={open} aria-controls={id}
              onClick={() => setOpen((o) => !o)}>
        {label}<span className="disclosure-mark" aria-hidden="true">{open ? " −" : " ?"}</span>
      </button>
      {open && <span id={id} role="note" className="disclosure-text small">{text}</span>}
    </span>
  );
}

/** The research-preview badge, everywhere it appears. Its one definition is in countryCopy.ts. */
export function ResearchPreviewBadge() {
  return <Disclosure label={RESEARCH_PREVIEW_LABEL} text={RESEARCH_PREVIEW_DEFINITION} className="badge research-partial" />;
}

/** The same disclosure on a card that sits beside other countries' cards (home, Gulf littoral):
 *  the neutral tag style, because a status colour on side-by-side cards reads as a ranking. */
export function ResearchPreviewTag() {
  return <Disclosure label={RESEARCH_PREVIEW_LABEL} text={RESEARCH_PREVIEW_DEFINITION} className="home-tag home-tag-preview" />;
}
