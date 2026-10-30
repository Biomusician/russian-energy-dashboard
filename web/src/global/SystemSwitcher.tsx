import { useEffect, useState } from "react";
import { loadManifest, type ManifestSystem } from "./manifest";
import { navigate } from "./router";

/** The monitored-system picker, shown in every view.
 *
 *  Options come from the manifest in its fixed alphabetical order, never sorted by a figure.
 *  If the manifest cannot be loaded the picker still offers the overview, so a reader is never
 *  stranded in one system by a failed fetch. */
export default function SystemSwitcher({ current }: { current: string | null }) {
  const [systems, setSystems] = useState<ManifestSystem[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    loadManifest()
      .then((m) => { if (live) setSystems(m.systems); })
      .catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, []);

  return (
    <label className="sys-switch">
      <span className="eyebrow">Monitored system</span>
      <select
        aria-label="Monitored system"
        value={current ?? ""}
        onChange={(e) => navigate(e.target.value || null)}
      >
        <option value="">Overview — all systems</option>
        {systems?.map((s) => (
          <option key={s.id} value={s.id}>{s.name}</option>
        ))}
        {/* Keep the current system selectable even before (or without) the manifest. */}
        {!systems && current && <option value={current}>{current.toUpperCase()}</option>}
      </select>
      {failed && <span className="small warn-text">System list unavailable</span>}
    </label>
  );
}
