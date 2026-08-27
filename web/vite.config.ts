import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // MapLibre is ~1 MB and changes only when the dependency is bumped. Keeping
        // it in its own chunk means an app-code edit does not invalidate it in the
        // CDN or the browser cache.
        manualChunks: { maplibre: ["maplibre-gl"] },
      },
    },
  },
});
