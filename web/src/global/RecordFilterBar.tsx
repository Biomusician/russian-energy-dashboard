import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import {
  DATE_PRESETS, activeFilters, dateChoiceText, describeFilters, isIsoDay, optionCounts, setDate, toggleChoice,
  type ChoiceFilter, type DateChoice, type DateFilter, type FilterDef, type FilterState,
} from "./recordFilters";
import "../styles/filters.css";

/** The filter controls over one list of published records (iteration 22).
 *
 *  Shared by the country pages and the impact atlas; the caller supplies the definitions
 *  (recordFilters.ts) and owns the state, so the state can live in the address.
 *
 *  - A compact row of menus on a wide screen; on a phone one "Filters (n)" button that opens a
 *    sheet with every filter laid out. Either way the controls are ordinary checkboxes, radio
 *    buttons and date fields, reachable by keyboard; Escape closes and returns focus to the button
 *    that opened it.
 *  - The line "Showing n of N published records" is always there, and when filters hide records it
 *    says how many and which filters are on. A filter never hides a record silently.
 *  - A number beside an option counts records in THIS list only.
 */

const PHONE = "(max-width: 600px)";

function usePhone(): boolean {
  const [phone, setPhone] = useState(() => typeof window !== "undefined" && !!window.matchMedia && window.matchMedia(PHONE).matches);
  useEffect(() => {
    if (!window.matchMedia) return;
    const mq = window.matchMedia(PHONE);
    const on = () => setPhone(mq.matches);
    on();
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return phone;
}

export interface RecordFilterBarProps<R> {
  defs: readonly FilterDef<R>[];
  state: FilterState;
  onChange: (next: FilterState) => void;
  /** The one list these filters act on. */
  records: readonly R[];
  /** How many of `records` the filters admit. */
  shown: number;
  /** The reader's day, for "last 30 days". */
  today: string;
  /** What the records are called in the count line. */
  noun?: string;
  /** Lines the reader must see: a link's filter that was ignored, a filter cleared for a linked record. */
  notes?: readonly string[];
  /** What a filter with a single possible value would have said, in place of that filter. */
  fixed?: readonly string[];
  /** Controls that belong beside the filters (the export buttons). */
  children?: ReactNode;
}

export function RecordFilterBar<R>({ defs, state, onChange, records, shown, today, noun = "published records", notes = [], fixed = [], children }: RecordFilterBarProps<R>) {
  const phone = usePhone();
  const [open, setOpen] = useState<string | null>(null);
  const [sheet, setSheet] = useState(false);
  const openRef = useRef<HTMLButtonElement>(null);
  const sheetRef = useRef<HTMLDivElement>(null);
  const rowRef = useRef<HTMLDivElement>(null);
  const total = records.length;
  const hidden = total - shown;
  const active = activeFilters(defs, state);
  const on = describeFilters(defs, state, today);

  // A click anywhere else closes an open menu, like every menu.
  useEffect(() => {
    if (!open) return;
    const away = (e: PointerEvent) => { if (!rowRef.current?.contains(e.target as Node)) setOpen(null); };
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, [open]);

  useEffect(() => { if (sheet) sheetRef.current?.focus(); }, [sheet]);
  // Leaving the phone layout with the sheet open would strand it.
  useEffect(() => { if (!phone) setSheet(false); else setOpen(null); }, [phone]);

  const closeSheet = () => { setSheet(false); openRef.current?.focus(); };
  const clear = () => onChange({ choices: {}, dates: {} });

  const sheetKeys = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closeSheet(); return; }
    if (e.key !== "Tab") return;
    // Keep Tab inside the sheet while it is open: the page behind it is covered.
    const stops = sheetRef.current?.querySelectorAll<HTMLElement>("button, input, select, a[href]");
    if (!stops || stops.length === 0) return;
    const first = stops[0];
    const last = stops[stops.length - 1];
    if (e.shiftKey && (document.activeElement === first || document.activeElement === sheetRef.current)) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  };

  const countLine = (
    <p className="rf-count small" role="status">
      Showing <strong>{shown}</strong> of <strong>{total}</strong> {noun}.
      {hidden > 0 && <> The filters hide <strong>{hidden}</strong>.</>}
      {on.length > 0 && <span className="rf-on-list"> Filters on: {on.join("; ")}.</span>}
    </p>
  );
  const clearButton = (
    <button type="button" className="ghost rf-clear" onClick={clear} disabled={active.length === 0}>Clear filters</button>
  );

  return (
    <section className="record-filters" aria-label={`Filter the ${noun}`}>
      {phone ? (
        <div className="rf-row">
          <button ref={openRef} type="button" className="ghost rf-open" aria-haspopup="dialog" aria-expanded={sheet}
                  onClick={() => setSheet(true)}>
            Filters ({active.length})<span className="sr-only">: {active.length === 0 ? "none on" : `${active.length} on`}</span>
          </button>
          {clearButton}
          {children}
        </div>
      ) : (
        <div className="rf-row" ref={rowRef}>
          {defs.map((def) => (
            <FilterMenu key={def.id} def={def} state={state} onChange={onChange} records={records} defs={defs} today={today}
                        open={open === def.id} setOpen={(v) => setOpen(v ? def.id : null)} />
          ))}
          {clearButton}
          {children}
        </div>
      )}
      {fixed.length > 0 && <p className="rf-fixed small dim">{fixed.join(" ")}</p>}
      {countLine}
      {notes.map((n) => <p key={n} className="rf-note small" role="status">{n}</p>)}

      {phone && sheet && (
        <div className="rf-backdrop" onClick={closeSheet}>
          <div className="rf-sheet" role="dialog" aria-modal="true" aria-label={`Filter the ${noun}`} ref={sheetRef} tabIndex={-1}
               onKeyDown={sheetKeys} onClick={(e) => e.stopPropagation()}>
            <div className="rf-sheet-head">
              <h3>Filters</h3>
              <button type="button" className="ghost" onClick={closeSheet}>Done</button>
            </div>
            {defs.map((def) => (
              <fieldset key={def.id} className="rf-group">
                <legend>{def.label}</legend>
                <FilterBody def={def} state={state} onChange={onChange} records={records} defs={defs} today={today} />
              </fieldset>
            ))}
            <div className="rf-sheet-foot">
              <p className="small" role="status">
                Showing <strong>{shown}</strong> of <strong>{total}</strong> {noun}.
                {hidden > 0 && <> The filters hide <strong>{hidden}</strong>.</>}
              </p>
              <button type="button" className="ghost" onClick={clear} disabled={active.length === 0}>Clear filters</button>
              <button type="button" className="ghost rf-sheet-done" onClick={closeSheet}>Show {shown} {shown === 1 ? "record" : "records"}</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

interface BodyProps<R> {
  def: FilterDef<R>;
  defs: readonly FilterDef<R>[];
  state: FilterState;
  onChange: (next: FilterState) => void;
  records: readonly R[];
  today: string;
}

/** What a menu's button says about its own filter, in words: never by colour alone. */
function buttonSummary<R>(def: FilterDef<R>, state: FilterState, today: string): string | null {
  if (def.kind === "date") {
    const c = state.dates[def.id];
    return c ? dateChoiceText(c, today) : null;
  }
  const picked = state.choices[def.id] ?? [];
  if (picked.length === 0) return null;
  if (picked.length === 1) return def.options.find((o) => o.value === picked[0])?.label ?? picked[0];
  return `${picked.length} chosen`;
}

function FilterMenu<R>({ open, setOpen, ...body }: BodyProps<R> & { open: boolean; setOpen: (v: boolean) => void }) {
  const { def, state, today } = body;
  const toggle = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  const summary = buttonSummary(def, state, today);
  const close = () => { setOpen(false); toggle.current?.focus(); };
  return (
    <div className="rf-menu"
         onKeyDown={(e) => { if (e.key === "Escape" && open) { e.preventDefault(); e.stopPropagation(); close(); } }}>
      <button ref={toggle} type="button" className={`ghost rf-toggle${summary ? " is-on" : ""}`} aria-expanded={open}
              aria-controls={panelId} onClick={() => setOpen(!open)}>
        {def.label}{summary ? <span className="rf-summary">: {summary}</span> : <span className="sr-only">: any</span>}
      </button>
      {open && (
        <div id={panelId} className="rf-panel" role="group" aria-label={`${def.label} filter`}>
          <FilterBody {...body} />
          <button type="button" className="ghost rf-done" onClick={close}>Done</button>
        </div>
      )}
    </div>
  );
}

function FilterBody<R>(p: BodyProps<R>) {
  return p.def.kind === "choice"
    ? <ChoiceBody {...p} def={p.def} />
    : <DateBody def={p.def} state={p.state} onChange={p.onChange} today={p.today} />;
}

function ChoiceBody<R>({ def, defs, state, onChange, records, today }: BodyProps<R> & { def: ChoiceFilter<R> }) {
  const picked = state.choices[def.id] ?? [];
  const counts = optionCounts(records, defs, state, today, def.id);
  return (
    <ul className="rf-options">
      {def.options.map((o) => (
        <li key={o.value}>
          <label>
            <input type="checkbox" checked={picked.includes(o.value)} onChange={() => onChange(toggleChoice(state, def.id, o.value))} />
            <span className="rf-option-label">{o.label}</span>
            {/* A count inside this one list, said as such to a screen reader. */}
            <span className="rf-n">{counts.get(o.value) ?? 0}<span className="sr-only"> of the records in this list</span></span>
          </label>
        </li>
      ))}
    </ul>
  );
}

function DateBody<R>({ def, state, onChange, today }: { def: DateFilter<R>; state: FilterState; onChange: (next: FilterState) => void; today: string }) {
  const choice: DateChoice | undefined = state.dates[def.id];
  const isCustom = !!choice && !("preset" in choice);
  // "Custom" stays chosen while its two fields are still empty, which the state reads as "off".
  const [customOpen, setCustomOpen] = useState(isCustom);
  const name = useId();
  const custom = isCustom ? (choice as { from: string | null; to: string | null }) : { from: null, to: null };
  const showCustom = isCustom || (customOpen && !choice);
  const setEnd = (end: "from" | "to", value: string) => {
    // A half-typed date is not a date yet: wait for a whole one, or an emptied field.
    if (value !== "" && !isIsoDay(value)) return;
    const next = { ...custom, [end]: value || null };
    // A range that ends before it starts admits nothing and cannot be read back from a link.
    if (next.from && next.to && next.from > next.to) return;
    onChange(setDate(state, def.id, next));
  };
  const pick = (c: DateChoice | null, openCustom: boolean) => { setCustomOpen(openCustom); onChange(setDate(state, def.id, c)); };
  return (
    <div className="rf-dates">
      <ul className="rf-options">
        <li><label><input type="radio" name={name} checked={!choice && !showCustom} onChange={() => pick(null, false)} /> <span className="rf-option-label">Any date</span></label></li>
        {DATE_PRESETS.map((p) => (
          <li key={p.id}>
            <label>
              <input type="radio" name={name} checked={!!choice && "preset" in choice && choice.preset === p.id}
                     onChange={() => pick({ preset: p.id }, false)} />
              <span className="rf-option-label">{p.label}</span>
            </label>
          </li>
        ))}
        <li><label><input type="radio" name={name} checked={showCustom} onChange={() => pick(null, true)} /> <span className="rf-option-label">Custom range</span></label></li>
      </ul>
      {showCustom && (
        <div className="rf-custom">
          <label>From <input type="date" value={custom.from ?? ""} max={custom.to ?? today} onChange={(e) => setEnd("from", e.target.value)} /></label>
          <label>To <input type="date" value={custom.to ?? ""} min={custom.from ?? undefined} max={today} onChange={(e) => setEnd("to", e.target.value)} /></label>
          <p className="small dim">A record that spans several days is shown when any of its days is in the range.</p>
        </div>
      )}
      {choice && "preset" in choice && <p className="small dim">{dateChoiceText(choice, today)}.</p>}
    </div>
  );
}

export default RecordFilterBar;
