import { useEffect, useRef, useState } from "react";
import { loadContext, type EnergyContext } from "./context";
import { NationalFigures, SourceLine } from "./NationalContext";
import type { CardAction, CardModel } from "./homeSelection";

/** What the reader has selected on the home map (iteration 23): in the panel on a wide screen, in
 *  a bottom sheet on a phone or after a tap. One component either way, so a phone and a desktop
 *  are told the same thing.
 *
 *  The sheet is not modal: the map above it stays usable, and a second tap replaces it. Escape or
 *  Close dismisses it and gives focus back to whatever opened it. Its buttons go to addresses the
 *  site already has; a country with no system and no record gets no button at all. */

export default function SelectionCard({ card, sheet, onClose, onAction }: {
  card: CardModel; sheet: boolean; onClose: () => void; onAction: (a: CardAction) => void;
}) {
  const Heading = sheet ? "h2" : "h3";
  return (
    <aside className={`sel-card${sheet ? " sel-sheet" : " panel"}`} aria-labelledby="sel-card-title" data-sel={card.key}
      onKeyDown={(e) => { if (e.key === "Escape") { e.stopPropagation(); onClose(); } }}>
      <div className="sel-card-head">
        <Heading id="sel-card-title" className="sel-card-title">{card.heading}</Heading>
        <button type="button" className="ghost sel-close" onClick={onClose} aria-label={`Close ${card.heading}`}>Close</button>
      </div>
      <p className="sel-status">{card.status}</p>
      {card.lines.map((l) => <p key={l} className="small sel-line">{l}</p>)}
      {card.links.length > 0 && (
        <ul className="sel-links">
          {card.links.map((a) => (
            <li key={a.href}><a href={a.href} data-ret={a.ret} onClick={(e) => follow(e, a, onAction)}>{a.label}</a></li>
          ))}
        </ul>
      )}
      {card.actions.length > 0 && (
        <div className="sel-actions">
          {card.actions.map((a) => (
            <a key={a.href} className={`home-action${a.primary ? " primary" : ""}`} href={a.href} data-ret={a.ret}
               onClick={(e) => follow(e, a, onAction)}>{a.label}</a>
          ))}
        </div>
      )}
      {card.contextA3 && <NationalContextDisclosure a3={card.contextA3} />}
    </aside>
  );
}

function follow(e: React.MouseEvent, a: CardAction, onAction: (a: CardAction) => void) {
  // A real link for a new tab and for "copy link address"; an in-page move for a plain click.
  if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  e.preventDefault();
  onAction(a);
}

/** National figures on request: the file is fetched the first time a card opens this, never with
 *  the page. Context, not monitoring, as the source line says. */
function NationalContextDisclosure({ a3 }: { a3: string }) {
  const [open, setOpen] = useState(false);
  const [ctx, setCtx] = useState<EnergyContext | null>(null);
  const [failed, setFailed] = useState(false);
  const ref = useRef<HTMLDetailsElement | null>(null);
  useEffect(() => {
    if (!open || ctx) return;
    let live = true;
    loadContext().then((c) => { if (live) setCtx(c); }).catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, [open, ctx]);
  const row = ctx?.countries.find((r) => r.a3 === a3);
  return (
    <details ref={ref} className="sel-context" onToggle={() => setOpen(!!ref.current?.open)}>
      <summary className="small">National energy context</summary>
      {failed && <p className="small warn-text" role="alert">Global energy context unavailable.</p>}
      {open && !ctx && !failed && <p className="small dim" role="status">Loading…</p>}
      {ctx && row && (
        <>
          <NationalFigures row={row} ctx={ctx} />
          <SourceLine ctx={ctx} />
          <p className="small dim">{ctx.not_scoring}</p>
        </>
      )}
      {ctx && !row && <p className="small dim">No national figures for this place in the source.</p>}
    </details>
  );
}
