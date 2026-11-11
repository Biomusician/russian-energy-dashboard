import { useEffect, useState } from "react";
import { loadManifest, type Manifest } from "./manifest";
import { navigate, navigateGroup } from "./router";

/** The monitored-system picker, shown in every view.
 *
 *  Options come from the manifest in its fixed alphabetical order, never sorted by a figure.
 *  Regional overviews (iteration 19) are listed first, also from the manifest: a group is a way
 *  to move around, never a unit with a figure of its own. If the manifest cannot be loaded the
 *  picker still offers the overview, so a reader is never stranded by a failed fetch. */
export default function SystemSwitcher({ current, group }: { current: string | null; group?: string }) {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    loadManifest()
      .then((m) => { if (live) setManifest(m); })
      .catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, []);

  const systems = manifest?.systems ?? null;
  const groups = Object.values(manifest?.groups ?? {}).filter((g) => g.slug && g.context);
  const value = group ? `group:${group}` : current ?? "";

  return (
    <label className="sys-switch">
      <span className="eyebrow">Monitored system</span>
      <select
        aria-label="Monitored system"
        value={value}
        onChange={(e) => {
          const v = e.target.value;
          if (v.startsWith("group:")) navigateGroup(v.slice(6));
          else navigate(v || null);
        }}
      >
        <option value="">Overview — all systems</option>
        {groups.length > 0 && (
          <optgroup label="Regional overviews">
            {groups.map((g) => <option key={g.slug} value={`group:${g.slug}`}>{g.label} overview</option>)}
          </optgroup>
        )}
        {systems && (
          <optgroup label="Systems, alphabetical">
            {systems.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </optgroup>
        )}
        {/* Keep the current view selectable even before (or without) the manifest. Not its id:
            "RU" flashed here on every load (iteration 17) -- an internal code, not a name. */}
        {!systems && (current || group) && <option value={value}>{failed ? "Current view" : "Loading systems…"}</option>}
      </select>
      {failed && <span className="small warn-text">System list unavailable</span>}
    </label>
  );
}
