/** The shared impact components (iteration 22): one place to import them from.
 *
 *  Loading: `loadImpacts()`, `loadRegionalContext()`, `loadConfidenceMethod()` (one request per file
 *  per page; each registers its vocabularies, so every component below finds its labels with no
 *  prop). `impactsFor(payload, { a3 })` or `{ systemIds }` gives one country's or a set of systems'
 *  disruptions in the served order.
 *
 *  Components: `<ImpactCard record />`, `<ConfidenceChip value />` (also for a country event's
 *  `evidence_confidence`), `<AttributionLine a />`, `<AiLine ai />`, `<ImpactInspector record />`,
 *  `<ContextTimeline ctx />`.
 */
export * from "./types";
export { loadImpacts, loadRegionalContext, loadConfidenceMethod, impactsFor } from "./load";
export { ConfidenceChip, ConfidenceBreakdown } from "./ConfidenceChip";
export { AttributionLine } from "./AttributionLine";
export { AiLine } from "./AiLine";
export { ImpactCard } from "./ImpactCard";
export { ImpactInspector } from "./ImpactInspector";
export { ContextTimeline, CONTEXT_CAVEAT } from "./ContextTimeline";
export { labelOf, definitionOf, registerVocabularies, registerMethod, useImpactVocab } from "./vocab";
