import { useEffect, useMemo, useState } from "react";
import type maplibregl from "maplibre-gl";
import SimpleMap from "../SimpleMap";
import { loadWorld } from "../manifest";
import { PRESENCE_MARK, PRESENCE_NONE, presenceFill } from "./atlasModel";

/** The Impact Atlas's presence map (iteration 22).
 *
 *  A country is marked when it has at least one published record in the current view. ONE mark
 *  colour: nothing is graded by how many records there are, because a darker country would be read
 *  as a more attacked one, and the corpus cannot support that reading. The list beside the map
 *  says the same thing in text; picking a country sets the country filter.
 */
export default function ImpactPresenceMap({ codes, selected, onPick }: {
  codes: readonly string[]; selected: string | null; onPick: (a3: string) => void;
}) {
  const [world, setWorld] = useState<GeoJSON.FeatureCollection | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let live = true;
    loadWorld().then((w) => { if (live) setWorld(w); }).catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, []);
  const key = codes.join(",");
  const fill = useMemo(() => presenceFill(codes) as maplibregl.ExpressionSpecification | string, [key]);  // eslint-disable-line react-hooks/exhaustive-deps
  const marked = useMemo(() => new Set(codes), [key]);  // eslint-disable-line react-hooks/exhaustive-deps

  if (failed) return <p className="small dim" role="status">The map could not be loaded. The list below says the same thing.</p>;
  if (!world) return <div className="simple-map placeholder atlas-map" role="status">Loading map…</div>;
  return (
    <div className="atlas-map-wrap">
      <div className="atlas-map">
        <SimpleMap
          data={world}
          bounds={[-170, -50, 179, 78]}
          fill={fill}
          idProp="a3"
          selected={selected}
          pickable={(p) => marked.has(String(p.a3))}
          onPick={(id) => { if (id) onPick(id); }}
          ariaLabel="World map marking the countries with at least one published record in the current view. The same countries are listed below."
          attribution="Boundaries: Natural Earth (public domain), line of actual control. Crimea is drawn as Ukrainian territory under Russian occupation."
          emptyMessage={codes.length === 0 ? "No country has a published record in this view." : null}
          tableHref="#atlas-country-list"
          pageScrollsFirst
        />
      </div>
      <p className="small atlas-map-key">
        <span className="atlas-key-swatch" style={{ background: PRESENCE_MARK }} aria-hidden="true" /> At least one published record in this view
        <span className="atlas-key-swatch" style={{ background: PRESENCE_NONE }} aria-hidden="true" /> No published record in this view (not the same as nothing happened)
      </p>
    </div>
  );
}
