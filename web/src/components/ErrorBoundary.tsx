/** Last line of defence (iteration 12).
 *
 *  There was none. Any throw during render unmounted the whole tree and left a white page — no
 *  message, no map, no way back except knowing to edit the address bar. A hostile or merely stale
 *  deep link could reach it: `?cmp=constructor` put a phantom region in the comparison tray, the
 *  tray read `sectors` off it, and the app vanished.
 *
 *  The specific hole is fixed in urlState/App, but the class of fault is not fixable by fixing
 *  instances. A dashboard whose entire purpose is to be honest about what it does not know must
 *  not answer "something went wrong" with a blank rectangle.
 *
 *  The recovery offered is to reload WITHOUT the query string, because a link is the most likely
 *  thing to have caused it and the plain dashboard is almost certainly fine.
 */

import { Component, type ErrorInfo, type ReactNode } from "react";

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Nothing is sent anywhere — this project makes no runtime network requests at all. The
    // console is the only place a reader (or the person they report it to) can see the detail.
    console.error("Dashboard crashed:", error, info.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    const hasQuery = typeof window !== "undefined" && window.location.search.length > 1;
    return (
      <div className="empty" style={{ padding: 40, maxWidth: 640 }}>
        <div className="eyebrow">The dashboard stopped</div>
        <p style={{ lineHeight: 1.6 }}>
          Something in this view failed to render. Nothing is wrong with the underlying data —
          the figures are static files and were loaded before this happened.
        </p>
        {hasQuery && (
          <p style={{ lineHeight: 1.6 }}>
            The link you opened carries saved view state, which is the most likely cause.
            {" "}
            <a href={window.location.pathname}>Open the dashboard without it</a>.
          </p>
        )}
        <p className="small" style={{ color: "var(--text-faint)" }}>
          Details, for a bug report: <code>{error.message || String(error)}</code>
        </p>
      </div>
    );
  }
}
