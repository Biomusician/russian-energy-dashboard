/** The words for the impact layer's keys (iteration 22).
 *
 *  Every label and definition the impact components show comes from a served vocabulary: the
 *  impact payload's `vocabularies`, the confidence method's `labels`, the regional context's own.
 *  No component types one. The loaders (load.ts) register what they fetched here, so a card
 *  rendered anywhere after a load finds its words without a prop being threaded through three
 *  views; a test registers a payload's vocabularies directly.
 *
 *  A key no vocabulary has yet is shown in plain words made from the key itself ("state_linked"
 *  reads "State linked"), never dropped and never shown raw.
 */
import { useSyncExternalStore } from "react";
import type { ConfidenceMethod, VocabEntry, Vocabularies } from "./types";

const vocab = new Map<string, VocabEntry[]>();
let method: ConfidenceMethod | null = null;
let version = 0;
const listeners = new Set<() => void>();

function changed() {
  version += 1;
  listeners.forEach((f) => f());
}

/** Add served vocabularies. The first one registered under a name stays: the three files carry the
 *  same lists, and a second copy must not re-render every card on the page. */
export function registerVocabularies(v: Vocabularies | null | undefined): void {
  if (!v || typeof v !== "object") return;
  let any = false;
  for (const [name, entries] of Object.entries(v)) {
    if (!Array.isArray(entries) || entries.length === 0 || vocab.has(name)) continue;
    vocab.set(name, entries.filter((e) => e && typeof e === "object"));
    any = true;
  }
  if (any) changed();
}

export function registerMethod(m: ConfidenceMethod): void {
  if (method === m) return;
  method = m;
  registerVocabularies(m.labels);
  changed();
}

/** The confidence method, if a page has loaded it. */
export function confidenceMethod(): ConfidenceMethod | null {
  return method;
}

/** Test seam: forget every registered word. */
export function forgetVocabularies(): void {
  vocab.clear();
  method = null;
  changed();
}

function entry(name: string, id: string | number | null | undefined): VocabEntry | null {
  if (id == null) return null;
  return vocab.get(name)?.find((e) => String(e.id) === String(id)) ?? null;
}

/** The key in plain words, for a key no served vocabulary names. */
export function plainKey(id: string | number): string {
  const s = String(id).replace(/_/g, " ").toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** The served label for a key of the named vocabulary; the key in plain words if it has none. */
export function labelOf(name: string, id: string | number | null | undefined): string {
  if (id == null) return "";
  const e = entry(name, id);
  // "exact" is served with an empty label on purpose (a figure given without qualification).
  return e ? e.label : plainKey(id);
}

/** The label as it reads in the middle of a sentence: "A government" becomes "a government";
 *  an acronym ("LNG", "AI-assisted") is left alone. */
export function lowerLabel(name: string, id: string | number | null | undefined): string {
  const s = labelOf(name, id);
  return /^[A-Z][a-z]/.test(s) ? s.charAt(0).toLowerCase() + s.slice(1) : s;
}

export function definitionOf(name: string, id: string | number | null | undefined): string | null {
  return entry(name, id)?.definition ?? null;
}

/** The entries of a vocabulary, in the served order; empty if it is not loaded. */
export function vocabulary(name: string): VocabEntry[] {
  return vocab.get(name) ?? [];
}

/** True for one of the served absence words ("unknown", "not_researched", "withheld", ...), which
 *  stand where a value is absent and say why. */
export function isAbsenceWord(v: unknown): v is string {
  return typeof v === "string" && entry("absence_words", v) != null;
}

function subscribe(f: () => void): () => void {
  listeners.add(f);
  return () => { listeners.delete(f); };
}
const snapshot = () => version;

/** Re-render when a vocabulary or the method arrives. Returns a number that changes when they do. */
export function useImpactVocab(): number {
  return useSyncExternalStore(subscribe, snapshot, snapshot);
}
