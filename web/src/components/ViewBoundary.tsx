/** Error containment per view and per panel (iteration 21).
 *
 *  The top-level ErrorBoundary (main.tsx) catches everything, but by replacing the whole page: one
 *  country's corrupt file, or a chunk a stale tab could no longer download, took the system picker
 *  and every other view down with it. These boundaries sit lower.
 *
 *  - `ViewBoundary` wraps the route switch in Root and is KEYED on the route, so each view gets a
 *    fresh boundary: a failure stays with the view that failed, and choosing another view (from the
 *    picker, the link below, or Back) mounts that one cleanly. A new route needs nothing here.
 *  - `PanelBoundary` wraps one independent panel inside a view, so a panel that fails costs that
 *    panel and nothing else.
 *
 *  Shape validation at load (manifest.ts) is the first line: a malformed file is refused and the
 *  view says it could not be loaded. These are the net for what validation cannot enumerate, such as
 *  a leaf of the wrong type, and for chunk downloads that fail.
 */

import { Component, type ErrorInfo, type ReactNode } from "react";
import { navigate } from "../global/router";
import SystemSwitcher from "../global/SystemSwitcher";

interface State {
  error: Error | null;
}

// Chromium, Firefox and Safari word a failed dynamic import differently; Vite's preload helper has its own.
const CHUNK_FAILURE = /dynamically imported module|Importing a module script failed|error loading dynamically imported|Unable to preload/i;

interface ViewProps {
  label: string;
  /** The view's own address without saved state, e.g. "?sys=ru". Offered when the link had more. */
  cleanHref?: string;
  home?: boolean;
  children: ReactNode;
}

export class ViewBoundary extends Component<ViewProps, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Nothing is sent anywhere: the console is the only place the detail goes.
    console.error(`${this.props.label} failed:`, error, info.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    const chunk = CHUNK_FAILURE.test(error.message || "");
    // A deep link's saved state is the likeliest cause of a render failure (iteration 12).
    const { cleanHref } = this.props;
    const stateful = !!cleanHref && new URLSearchParams(window.location.search).toString()
      !== new URLSearchParams(cleanHref.replace(/^\?/, "")).toString();
    // The picker stays, so every other view is one choice away (it copes with a missing manifest).
    return (
      <div className="global-page">
        <header className="global-head">
          <div className="ribbon-title">Energy Disruption Monitor</div>
          <SystemSwitcher current={null} />
        </header>
        <main className="global-main">
          <section className="panel view-failed" role="alert" aria-label={`${this.props.label} could not be shown`}>
            <h1 className="ribbon-title">{this.props.label} could not be shown</h1>
            <p>
              {chunk
                ? "Part of the site could not be downloaded. This usually means the site was updated while the page was open; reloading fetches the current version."
                : "Something in this view failed while it was being drawn. The other views are not affected."}
            </p>
            {stateful && (
              <p>
                The link you opened carries saved view state, which may be the cause.{" "}
                <a href={this.props.cleanHref}>Open this view without it</a>.
              </p>
            )}
            <p>
              {!this.props.home && (
                <>
                  <button className="ghost" onClick={() => navigate(null)}>Return to the overview</button>{" "}
                </>
              )}
              <button className="ghost" onClick={() => window.location.reload()}>Reload</button>
            </p>
            <p className="small dim">Details, for a bug report: <code>{error.message || String(error)}</code></p>
          </section>
        </main>
      </div>
    );
  }
}

export class PanelBoundary extends Component<{ label: string; children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`${this.props.label} panel failed:`, error, info.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <section className="panel global-note panel-failed" role="alert" aria-label={`${this.props.label}: could not be shown`}>
        <p className="small warn-text">{this.props.label} could not be shown. The rest of this page is not affected.</p>
        <p className="small dim">Details: <code>{error.message || String(error)}</code></p>
      </section>
    );
  }
}
