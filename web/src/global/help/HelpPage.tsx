/** The Help page (iteration 23): `?view=help`, one section per anchor, `?view=help#esdi`.
 *
 *  Before it, the site explained itself in seven places that did not link to each other, and only
 *  the glossary dialog had an address. Now every explanation has one address a reader can bookmark,
 *  send or come Back to, and every page links here with "Learn more" instead of repeating a caveat.
 *
 *  HOW IT READS. One h1, a table of contents (a sticky list on a wide screen, a section picker on a
 *  phone), then the sections in reading order: each opens with a one-sentence answer, then detail,
 *  with technical depth folded into <details>. Headings are real text, so the browser's own find
 *  works; each is focusable, and a deep link moves focus to it after scrolling it clear of the top.
 *
 *  WHAT IT FETCHES. Four small files: the manifest, help_facts.json, the Evidence Confidence method
 *  and What's new. Never the snapshot or the impact corpus (pipeline/help_facts.py copies the few
 *  values Help needs). Until a file arrives its blocks say "Loading"; if it fails, they say so.
 */
import { useEffect, useRef, useState } from "react";
import { GlobalNavBar } from "../GlobalNav";
import { loadManifest, loadWhatsNew } from "../manifest";
import { LOCATION_EVENT, routeFor } from "../router";
import { loadConfidenceMethod } from "../impacts/load";
import { fmtDate } from "../../data";
import { readerText } from "../readerText";
import { HELP_SECTIONS_TOC, HELP_SUBSECTIONS, helpTitle } from "./anchors";
import { HELP_SECTIONS, type HelpBlock, type HelpSection } from "./content";
import { GLOSSARY } from "./glossary";
import { glossaryDetail } from "./glossaryDetail";
import { Derived, type HelpData, type Loaded } from "./HelpDerived";
import { loadHelpFacts } from "./facts";
import "../../styles/help.css";

function Blocks({ blocks, data }: { blocks: HelpBlock[]; data: HelpData }) {
  return (
    <>
      {blocks.map((b, i) => {
        if (b.kind === "p") return <p key={i}>{b.text}</p>;
        if (b.kind === "list") return <ul key={i}>{b.items.map((t) => <li key={t}>{t}</li>)}</ul>;
        if (b.kind === "details") {
          return (
            <details key={i} className="help-details">
              <summary>{b.summary}</summary>
              <Blocks blocks={b.blocks} data={data} />
            </details>
          );
        }
        return <Derived key={i} k={b.key} data={data} />;
      })}
    </>
  );
}

function SeeAlso({ ids }: { ids: HelpSection["seeAlso"] }) {
  if (!ids || ids.length === 0) return null;
  return (
    <p className="small help-see">See also:{" "}
      {ids.map((id, i) => <span key={id}>{i > 0 && " · "}<a href={`#${id}`}>{helpTitle(id)}</a></span>)}
    </p>
  );
}

function Glossary({ data }: { data: HelpData }) {
  // The method's own definitions replace an entry's detail once it has loaded, as on the record cards.
  const served = data.method.value;
  return (
    <div className="help-glossary">
      {GLOSSARY.map((g) => (
        <div key={g.id} className="help-term">
          <h3 id={`g-${g.id}`} tabIndex={-1}>{g.term}</h3>
          <p>{g.plain}</p>
          <details className="help-details">
            <summary className="small">More detail<span className="sr-only"> on {g.term}</span></summary>
            <p className="small">{readerText(glossaryDetail(g.id, served))}</p>
          </details>
          <p className="small help-see">Explained in: <a href={`#${g.see}`}>{helpTitle(g.see)}</a></p>
        </div>
      ))}
    </div>
  );
}

/** The table of contents: a list on wide screens, a picker on phones. CSS shows one of them. */
function Contents({ current }: { current: string }) {
  return (
    <nav className="help-toc" aria-label="Help sections">
      <p className="help-toc-head">On this page</p>
      <ol className="help-toc-list">
        {HELP_SECTIONS_TOC.map((s) => (
          <li key={s.id}><a href={`#${s.id}`} aria-current={current === s.id ? "location" : undefined}>{s.title}</a></li>
        ))}
      </ol>
      <label className="help-picker">
        <span className="small dim">Jump to a section</span>
        <select value={HELP_SECTIONS_TOC.some((s) => s.id === current) ? current : ""}
                onChange={(e) => { if (e.target.value) window.location.hash = e.target.value; }}>
          <option value="">Choose a section…</option>
          {HELP_SECTIONS_TOC.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
        </select>
      </label>
    </nav>
  );
}

/** The whole Help text, given whatever files have loaded. Pure, so it renders the same in a test. */
export function HelpDocument({ data, current = "" }: { data: HelpData; current?: string }) {
  const m = data.manifest.value, meth = data.method.value, f = data.facts.value;
  return (
    <div className="help-layout">
      <Contents current={current} />
      <main id="main-content" className="help-main">
        <h1 className="help-title">Help: how to read this site</h1>
        <p className="small dim help-meta">
          {f ? `Built ${fmtDate(f.as_of)}` : m ? `Built ${fmtDate(m.build_time.slice(0, 10))}` : "Build date loading"}
          {f?.theatre.method_version ? ` · index method version ${f.theatre.method_version}` : ""}
          {meth ? ` · evidence-confidence method ${meth.version}${meth.status ? ` (${readerText(meth.status)})` : ""}` : ""}
        </p>
        {HELP_SECTIONS.map((s) => (
          <section key={s.id} className="help-section" aria-labelledby={s.id}>
            <h2 id={s.id} tabIndex={-1}>{helpTitle(s.id)}</h2>
            <p className="help-answer">{s.answer}</p>
            <Blocks blocks={s.blocks} data={data} />
            {s.subsections?.map((sub) => (
              <div key={sub.id} className="help-subsection">
                <h3 id={sub.id} tabIndex={-1}>{HELP_SUBSECTIONS.find((x) => x.id === sub.id)!.title}</h3>
                <Blocks blocks={sub.blocks} data={data} />
              </div>
            ))}
            {s.id === "glossary" && <Glossary data={data} />}
            <SeeAlso ids={s.seeAlso} />
          </section>
        ))}
      </main>
    </div>
  );
}

const PENDING = { value: null, failed: false };

function useLoaded<T>(load: () => Promise<T>): Loaded<T> {
  const [state, setState] = useState<Loaded<T>>(PENDING);
  useEffect(() => {
    let live = true;
    load().then((value) => { if (live) setState({ value, failed: false }); })
      .catch(() => { if (live) setState({ value: null, failed: true }); });
    return () => { live = false; };
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps
  return state;
}

const hashId = () => {
  try { return decodeURIComponent(window.location.hash.slice(1)); } catch { return ""; }
};

export default function HelpPage() {
  const data: HelpData = {
    facts: useLoaded(loadHelpFacts),
    manifest: useLoaded(loadManifest),
    method: useLoaded(loadConfidenceMethod),
    whatsNew: useLoaded(loadWhatsNew),
  };
  const [current, setCurrent] = useState(hashId);
  const pageRef = useRef<HTMLDivElement | null>(null);
  // Set once the reader scrolls or types: from then on a late-arriving file never pulls the page back.
  const moved = useRef(false);

  // Scroll the address's section into view and, when asked, move focus to its heading. With no
  // section in the address, the top. The page is its own scroll container (theme.css), so a
  // browser's own restoration on Back does not reach it: this does it for every move.
  const show = (focus: boolean) => {
    const id = hashId();
    setCurrent(id);
    if (!id) { if (pageRef.current) pageRef.current.scrollTop = 0; return; }
    const el = document.getElementById(id);
    if (!el) return;
    el.scrollIntoView({ block: "start" });
    if (focus) el.focus({ preventScroll: true });
  };

  useEffect(() => {
    show(true);
    const onMove = () => { if (routeFor(window.location.search).view === "help") { moved.current = false; show(true); } };
    window.addEventListener("hashchange", onMove);
    window.addEventListener("popstate", onMove);
    window.addEventListener(LOCATION_EVENT, onMove);
    const page = pageRef.current;
    const stop = () => { moved.current = true; };
    page?.addEventListener("wheel", stop, { passive: true });
    page?.addEventListener("touchmove", stop, { passive: true });
    page?.addEventListener("keydown", stop);
    return () => {
      window.removeEventListener("hashchange", onMove);
      window.removeEventListener("popstate", onMove);
      window.removeEventListener(LOCATION_EVENT, onMove);
      page?.removeEventListener("wheel", stop);
      page?.removeEventListener("touchmove", stop);
      page?.removeEventListener("keydown", stop);
    };
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  // Each file that arrives can grow the blocks above the section in the address; keep that section
  // at the top until the reader moves.
  const settled = [data.facts, data.manifest, data.method, data.whatsNew].filter((d) => d.value || d.failed).length;
  useEffect(() => {
    if (settled > 0 && !moved.current && hashId()) show(false);
  }, [settled]);  // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="global-page help-page" ref={pageRef}>
      <header className="site-head">
        <GlobalNavBar trail={[{ label: "Help" }]} />
      </header>
      <HelpDocument data={data} current={current} />
    </div>
  );
}
