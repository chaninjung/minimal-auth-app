import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev we proxy /api -> http://localhost:8080 so requests are
// same-origin from the browser's perspective. This avoids the dance of
// CORS + credentials in development. The backend still has CORS
// configured for the case where the frontend is hosted separately in
// production (different origin).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8080",
        changeOrigin: true,
      },
    },
  },
});
