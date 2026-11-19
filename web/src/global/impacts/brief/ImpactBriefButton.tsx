import { useState } from "react";
import { downloadBlob } from "../../../download";
import { canvasPng } from "../../compareExport";
import { loadContext, rowForSystem } from "../../context";
import { exportCampaignLine } from "../../countryExport";
import { coverageSummary, latestLanes } from "../../laneCoverage";
import { ENVIRONMENT_LABEL, labelFor, loadCountrySystem, loadManifest } from "../../manifest";
import { loadConfidenceMethod, loadImpacts, loadRegionalContext } from "../load";
import { contextDescribes, countryBriefFilename, countryBriefInput } from "./briefInputs";
import { drawCountryImpactBrief } from "./drawImpactBrief";

/** "Download impact brief" for one country system (iteration 22).
 *
 *  Mount it anywhere with the system's id: `<ImpactBriefButton systemId="ir" />`. Everything the
 *  brief needs is fetched when the button is pressed, through the page's request cache, so a page
 *  that never presses it pays nothing. A file that fails to load is said in the brief in words
 *  ("could not be loaded"); it is never drawn as an empty record.
 *
 *  The regional context statements are included only for a system in the group that context
 *  describes, which is read from the manifest's own groups: no country is named here.
 */
export function ImpactBriefButton({ systemId, className = "ghost" }: { systemId: string; className?: string }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const run = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const manifest = await loadManifest();
      const entry = manifest.systems.find((s) => s.id === systemId && s.kind === "country");
      if (!entry) throw new Error(`There is no country system called "${systemId}".`);
      const [system, payload, regional, method, national] = await Promise.all([
        loadCountrySystem(entry),
        loadImpacts().catch(() => null),
        loadRegionalContext().catch(() => null),
        loadConfidenceMethod().catch(() => null),
        loadContext().catch(() => null),
      ]);
      const groups = entry.regional_groups ?? [];
      const inContextGroup = !!regional && groups.some((g) => contextDescribes(regional, g));
      const passes = system.research_log.passes;
      const canvas = drawCountryImpactBrief(countryBriefInput({
        name: system.name,
        a3: null,
        system,
        coverage: coverageSummary(latestLanes(passes), passes.length),
        campaignLine: exportCampaignLine(system),
        reportingEnvironment: labelFor(ENVIRONMENT_LABEL, system.reporting_environment).toLowerCase(),
        national: national ? { row: rowForSystem(national, systemId), ctx: national } : null,
        payload,
        regional: inContextGroup ? regional : null,
        method,
        buildDate: manifest.build_time,
      }));
      downloadBlob(await canvasPng(canvas), countryBriefFilename(systemId, manifest.build_time));
      setMsg(`Impact brief saved (${canvas.width}×${canvas.height}). It carries its own caveats.`);
    } catch (err) {
      setMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <span className="impact-brief-control">
      <button type="button" className={className} onClick={run} disabled={busy} aria-busy={busy}>
        Download impact brief (PNG)
      </button>
      {msg && <span className="small" role="status"> {msg}</span>}
    </span>
  );
}

export default ImpactBriefButton;
