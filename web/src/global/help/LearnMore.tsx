import { navigateTo } from "../router";
import { anchorTitle, helpHref, type HelpAnchor } from "./anchors";

/** "Learn more": a plain link to one section of the Help page (iteration 23).
 *
 *  Never a modal and never a tooltip: a real address the reader can open in a new tab, copy or come
 *  Back from. Every page's explanations point here instead of repeating the whole caveat. The link's
 *  accessible name carries the section it opens, so a page with several does not read as a row of
 *  identical "Learn more" links. `anchor` is typed against the Help section list.
 */
export function LearnMore({ anchor, label = "Learn more", className = "" }: { anchor: HelpAnchor; label?: string; className?: string }) {
  const href = helpHref(anchor);
  return (
    <a className={`learn-more${className ? ` ${className}` : ""}`} href={href} data-help-anchor={anchor}
       onClick={(e) => {
         // A plain link for a new tab or "copy link address"; an in-page move for a normal click.
         if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
         e.preventDefault();
         navigateTo(href);
       }}>
      {label}<span className="sr-only">: {anchorTitle(anchor)}, in Help</span>
    </a>
  );
}

export default LearnMore;
