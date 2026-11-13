import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "maplibre-gl/dist/maplibre-gl.css";
import "./theme.css";
import Root from "./Root";
import ErrorBoundary from "./components/ErrorBoundary";
import { installDetailsEscape } from "./detailsEscape";
import "./styles/touch.css";

installDetailsEscape();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <Root />
    </ErrorBoundary>
  </StrictMode>,
);
