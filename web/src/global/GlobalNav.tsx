import { useEffect, useId, useMemo, useRef, useState } from "react";
import { loadManifest, type Manifest } from "./manifest";
import { navigate, navigateGroup, navigateTo } from "./router";
import { GLOSSARY, HOW_IT_WORKS } from "./glossary";
import {
  CONCEPT_ENTRIES, KIND_LABEL, VIEW_ENTRIES, groupEntries, loadTheatreRegions, loadedCountryRegions,
  onCountryRegions, searchEntries, systemEntries, theatreRegionEntries,
  type SearchEntry, type SearchHit, type TheatreRegion,
} from "./searchIndex";
import { requestStartHere } from "./startHereMemory";
import "../styles/home.css";

/** Navigation shared by every global view (iteration 21): a breadcrumb home, one search box,
 *  the glossary, "How to read this" and a copy-link control. One bar per view, so one `/`
 *  shortcut and one glossary dialog per page. */

export interface Crumb { label: string; href?: string }

const GLOSSARY_EVENT = "edm:glossary";
export const START_HERE_EVENT = "edm:starthere";

/** Open the glossary, optionally at one entry. Any view's bar listens. */
export function openGlossary(id?: string) {
  window.dispatchEvent(new CustomEvent(GLOSSARY_EVENT, { detail: id ?? null }));
}

function isHome(): boolean {
  return window.location.search.replace(/^\?/, "") === "" || /^(help=glossary)?$/.test(window.location.search.slice(1));
}

/** "How to read this": on the home page it reopens the Start-here panel; elsewhere it goes home
 *  (a new history entry, so Back returns) with the panel open. */
export function howToRead() {
  if (isHome()) window.dispatchEvent(new Event(START_HERE_EVENT));
  else { requestStartHere(); navigate(null); }
}

export function GlobalNavBar({ trail, search = true, extra }: { trail: Crumb[]; search?: boolean; extra?: React.ReactNode }) {
  return (
    <div className="global-nav">
      <a className="product-home" href={window.location.pathname} onClick={(e) => go(e, "")}
        aria-label="Energy Disruption Monitor, home">Energy Disruption Monitor</a>
      <Breadcrumb trail={trail} />
      <div className="global-nav-tools">
        {search && <GlobalSearch compact />}
        <button className="ghost" type="button" onClick={howToRead}>How to read this</button>
        <button className="ghost" type="button" onClick={() => openGlossary("how-it-works")}>How this works</button>
        <button className="ghost" type="button" onClick={() => openGlossary()}>Glossary</button>
        <CopyLinkButton />
        {extra}
      </div>
      <GlossaryDialog />
    </div>
  );
}

function go(e: React.MouseEvent, href: string) {
  // A plain link for middle-click and "copy link address"; an in-page move for a normal click.
  if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  e.preventDefault();
  navigateTo(href);
}

export function Breadcrumb({ trail }: { trail: Crumb[] }) {
  const items: Crumb[] = [{ label: "Home", href: "?" }, ...trail];
  return (
    <nav aria-label="Breadcrumb" className="breadcrumb">
      <ol>
        {items.map((c, i) => {
          const last = i === items.length - 1;
          return (
            <li key={`${i}:${c.label}`}>
              {last || !c.href
                ? <span aria-current={last ? "page" : undefined}>{c.label}</span>
                : <a href={c.href === "?" ? window.location.pathname : c.href} onClick={(e) => go(e, c.href === "?" ? "" : c.href!)}>{c.label}</a>}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/** The breadcrumb trail for a country: through its regional overview when it has one. Structure,
 *  not history: Iran is under the Gulf littoral whichever way the reader arrived. */
export function countryTrail(manifest: Manifest | null, id: string, name: string): Crumb[] {
  const sys = manifest?.systems.find((s) => s.id === id);
  const group = sys ? Object.values(manifest?.groups ?? {}).find((g) => g.slug && g.context && g.members.includes(id)) : undefined;
  const shown = sys?.name ?? name;
  return group ? [{ label: group.label, href: `?group=${encodeURIComponent(group.slug as string)}` }, { label: shown }] : [{ label: shown }];
}

/** The bar for a country page, with the trail worked out from the (cached) manifest. */
export function CountryNav({ id, name }: { id: string; name: string }) {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  useEffect(() => {
    let live = true;
    loadManifest().then((m) => { if (live) setManifest(m); }).catch(() => undefined);
    return () => { live = false; };
  }, []);
  return <GlobalNavBar trail={countryTrail(manifest, id, name)} />;
}

// ---- copy link --------------------------------------------------------------------------------

function fallbackCopy(text: string): boolean {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.setAttribute("readonly", "");
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch { ok = false; }
  ta.remove();
  return ok;
}

export async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Permission refused or no focus: fall through to the older route.
  }
  return fallbackCopy(text);
}

export function CopyLinkButton() {
  const [msg, setMsg] = useState("");
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const run = async () => {
    const ok = await copyText(window.location.href);
    setMsg(ok ? "Link to this view copied." : "Could not copy. The link to this view is in the address bar.");
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setMsg(""), 5000);
  };
  return (
    <span className="copy-link">
      <button className="ghost" type="button" onClick={run}>Copy view link</button>
      <span className="copy-link-msg small" role="status" aria-live="polite">{msg}</span>
    </span>
  );
}

// ---- search -----------------------------------------------------------------------------------

function editable(t: EventTarget | null): boolean {
  const el = t as HTMLElement | null;
  if (!el || !el.tagName) return false;
  return el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName);
}

function runAction(entry: SearchEntry) {
  const a = entry.action;
  if (a.type === "system") navigate(a.id || null);
  else if (a.type === "group") navigateGroup(a.slug);
  else if (a.type === "href") navigateTo(a.href);
  else openGlossary(a.id);
}

/** One accessible combobox: the ARIA 1.2 pattern, list autocomplete, no dependency. */
export function GlobalSearch({ compact = false, inputRef }: { compact?: boolean; inputRef?: React.MutableRefObject<HTMLInputElement | null> }) {
  const id = useId();
  const listId = `${id}-list`;
  const ownRef = useRef<HTMLInputElement | null>(null);
  const ref = inputRef ?? ownRef;
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [theatre, setTheatre] = useState<TheatreRegion[] | null>(null);
  const [regionsFailed, setRegionsFailed] = useState(false);
  const [countryTick, setCountryTick] = useState(0);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);

  useEffect(() => {
    let live = true;
    loadManifest().then((m) => { if (live) setManifest(m); }).catch(() => undefined);
    const off = onCountryRegions(() => setCountryTick((n) => n + 1));
    return () => { live = false; off(); };
  }, []);

  // "/" focuses the search from anywhere on the page except a field being typed in.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey || editable(e.target)) return;
      if (document.querySelector("dialog[open]")) return;
      e.preventDefault();
      ref.current?.focus();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [ref]);

  // Region names cost one small file, fetched the first time the box is focused, never on load.
  const onFocus = () => {
    if (theatre || regionsFailed) return;
    loadTheatreRegions().then(setTheatre).catch(() => setRegionsFailed(true));
  };

  const entries = useMemo(() => {
    const out: SearchEntry[] = [...VIEW_ENTRIES, ...CONCEPT_ENTRIES];
    if (manifest) {
      out.push(...systemEntries(manifest), ...groupEntries(manifest));
      const theatreName = manifest.systems.find((s) => s.kind === "theatre")?.name ?? "";
      if (theatre) out.push(...theatreRegionEntries(theatre, theatreName));
    }
    out.push(...loadedCountryRegions());
    return out;
  }, [manifest, theatre, countryTick]);  // eslint-disable-line react-hooks/exhaustive-deps

  const hits: SearchHit[] = useMemo(() => searchEntries(entries, query), [entries, query]);
  const expanded = open && query.trim() !== "";

  const choose = (h: SearchHit) => {
    setOpen(false);
    setQuery("");
    setActive(-1);
    ref.current?.blur();
    runAction(h.entry);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActive((i) => (hits.length ? (i + 1) % hits.length : -1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setOpen(true);
      setActive((i) => (hits.length ? (i <= 0 ? hits.length - 1 : i - 1) : -1));
    } else if (e.key === "Enter") {
      const h = hits[active] ?? hits[0];
      if (expanded && h) { e.preventDefault(); choose(h); }
    } else if (e.key === "Escape") {
      if (expanded) { e.preventDefault(); setOpen(false); setActive(-1); }
      else if (query) { e.preventDefault(); setQuery(""); }
    }
  };

  const optionId = (i: number) => `${id}-opt-${i}`;
  const status = !expanded ? "" : hits.length === 0 ? "No matches." : `${hits.length} ${hits.length === 1 ? "match" : "matches"}. Use the arrow keys to choose.`;

  return (
    <div className={`gsearch${compact ? " compact" : ""}`}>
      <label htmlFor={`${id}-input`} className="gsearch-label">
        Search systems, regions and terms <span className="gsearch-key">(press <kbd>/</kbd> to focus)</span>
      </label>
      <div className="gsearch-box">
        <input
          ref={ref}
          id={`${id}-input`}
          type="text"
          role="combobox"
          autoComplete="off"
          spellCheck={false}
          aria-autocomplete="list"
          aria-expanded={expanded}
          aria-controls={listId}
          aria-activedescendant={expanded && active >= 0 && hits[active] ? optionId(active) : undefined}
          aria-keyshortcuts="/"
          placeholder={compact ? "Search" : "A country, region, alias or term — e.g. Iran, ایران, Texas, exposure"}
          value={query}
          onFocus={onFocus}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); setActive(-1); }}
          onKeyDown={onKeyDown}
          onBlur={() => window.setTimeout(() => setOpen(false), 150)}
        />
        <ul id={listId} role="listbox" aria-label="Search results" className="gsearch-list" hidden={!expanded}>
          {expanded && hits.map((h, i) => (
            <li
              key={h.entry.key}
              id={optionId(i)}
              role="option"
              aria-selected={i === active}
              className={i === active ? "active" : undefined}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => choose(h)}
              onMouseEnter={() => setActive(i)}
            >
              <span className="gsearch-kind">{KIND_LABEL[h.entry.kind]}</span>
              <span className="gsearch-name">{h.entry.label}</span>
              {h.matched !== h.entry.label && <span className="gsearch-alias" dir="auto">“{h.matched}”</span>}
              <span className="gsearch-sub">{h.entry.sub}</span>
            </li>
          ))}
          {expanded && hits.length === 0 && <li role="option" aria-disabled="true" aria-selected={false} className="gsearch-none">No match. Try a country, a region, or a term such as “exposure”.</li>}
        </ul>
      </div>
      <span className="sr-only" role="status" aria-live="polite">{status}</span>
    </div>
  );
}

// ---- glossary ---------------------------------------------------------------------------------

/** The glossary as a modal dialog: Escape closes it and focus returns to what opened it.
 *  `?help=glossary` opens it on load, so a link can point straight at it. */
export function GlossaryDialog() {
  const ref = useRef<HTMLDialogElement | null>(null);
  const opener = useRef<HTMLElement | null>(null);
  const [focusId, setFocusId] = useState<string | null>(null);
  const [initial] = useState(() => new URLSearchParams(window.location.search).get("help") === "glossary");

  const show = (entry: string | null) => {
    const d = ref.current;
    if (!d) return;
    if (!d.open) {
      opener.current = document.activeElement as HTMLElement | null;
      d.showModal();
    }
    setFocusId(entry);
    const target = entry ? d.querySelector<HTMLElement>(`#gl-${entry} h3`) : d.querySelector<HTMLElement>("h2");
    target?.focus();
    target?.scrollIntoView?.({ block: "start" });
  };

  useEffect(() => {
    const on = (e: Event) => show((e as CustomEvent).detail ?? null);
    window.addEventListener(GLOSSARY_EVENT, on);
    if (initial) show(null);
    return () => window.removeEventListener(GLOSSARY_EVENT, on);
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  const onClose = () => {
    setFocusId(null);
    const p = new URLSearchParams(window.location.search);
    if (p.get("help") === "glossary") {
      p.delete("help");
      const q = p.toString();
      window.history.replaceState(null, "", q ? `${window.location.pathname}?${q}` : window.location.pathname);
    }
    const o = opener.current;
    opener.current = null;
    if (o && document.contains(o)) o.focus();
  };

  return (
    <dialog ref={ref} className="glossary-dialog" aria-labelledby="glossary-title" onClose={onClose}>
      <div className="glossary-head">
        <h2 id="glossary-title" tabIndex={-1}>Glossary</h2>
        <button className="ghost" type="button" onClick={() => ref.current?.close()}>Close</button>
      </div>
      <p className="small dim">Plain-language meanings of the words this site uses. Open “More detail” for the technical version.
        Press Escape to close.</p>
      <section id="gl-how-it-works" className={`glossary-entry how-it-works${focusId === "how-it-works" ? " focused" : ""}`} aria-labelledby="gl-how-it-works-t">
        <h3 id="gl-how-it-works-t" tabIndex={-1}>How this works</h3>
        <ol className="small">
          {HOW_IT_WORKS.map((s) => <li key={s.step}><strong>{s.step}.</strong> {s.text}</li>)}
        </ol>
      </section>
      <h3 className="eyebrow glossary-terms-head">Terms, alphabetical</h3>
      <div className="glossary-list">
        {GLOSSARY.map((g) => (
          <section key={g.id} id={`gl-${g.id}`} className={`glossary-entry${focusId === g.id ? " focused" : ""}`} aria-labelledby={`gl-${g.id}-t`}>
            <h3 id={`gl-${g.id}-t`} tabIndex={-1}>{g.term}</h3>
            <p>{g.plain}</p>
            <details open={focusId === g.id || undefined}>
              <summary className="small">More detail</summary>
              <p className="small dim">{g.detail}</p>
            </details>
          </section>
        ))}
      </div>
    </dialog>
  );
}

