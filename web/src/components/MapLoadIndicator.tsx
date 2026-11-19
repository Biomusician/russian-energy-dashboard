import { mapLoadCanRetry, mapLoadMessage, mapLoadPhase, type MapLoadState } from "../mapLoad";
import "../styles/mapload.css";

/** What a map is waiting for, said inside the map box (iteration 22).
 *
 *  Laid over the map, so it takes no room and nothing moves when it goes. The words come from
 *  mapLoad.ts, which only real load events drive. A polite live region (`role="status"`), always in
 *  the page so a screen reader hears it change; empty once the map is drawn. When the map cannot be
 *  drawn it says so, offers "Try again", and names the list or table that carries the same
 *  information without the map.
 */
export function MapLoadIndicator({ state, onRetry, alternative }: {
  state: MapLoadState;
  onRetry?: () => void;
  /** Where the same information is without the map: "The table below has every figure." */
  alternative?: string;
}) {
  const phase = mapLoadPhase(state);
  const message = mapLoadMessage(state);
  const retry = mapLoadCanRetry(state);
  return (
    <div className={`map-load${message ? " is-on" : ""}${retry ? " is-error" : ""}`} data-map-load={phase}>
      <p className="map-load-text" role="status">
        {message}{phase === "failed" && alternative ? ` ${alternative}` : ""}
      </p>
      {retry && onRetry && <button type="button" className="ghost map-load-retry" onClick={onRetry}>Try again</button>}
    </div>
  );
}

/** The same box before a map exists: the caller is still waiting for the geometry file itself. */
export function MapGeometryPlaceholder({ failed, onRetry, alternative, className = "simple-map placeholder" }: {
  failed: boolean;
  onRetry?: () => void;
  alternative?: string;
  className?: string;
}) {
  return (
    <div className={`${className} map-load-placeholder`} data-map-load={failed ? "failed" : "geometry"}>
      <p className="map-load-text" role="status">
        {failed ? `Map unavailable.${alternative ? ` ${alternative}` : ""}` : "Loading map geometry…"}
      </p>
      {failed && onRetry && <button type="button" className="ghost map-load-retry" onClick={onRetry}>Try again</button>}
    </div>
  );
}
