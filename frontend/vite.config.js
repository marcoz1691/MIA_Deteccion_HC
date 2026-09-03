import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API_TARGET = "http://127.0.0.1:8010";
const PROXY_TIMEOUT_MS = 5 * 60 * 1000;

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/generar": { target: API_TARGET, timeout: PROXY_TIMEOUT_MS },
      "/health": { target: API_TARGET, timeout: 30_000 },
      "/historial": { target: API_TARGET, timeout: 30_000 },
      "/extraer-pdf": { target: API_TARGET, timeout: PROXY_TIMEOUT_MS },
      "/muestras-pdf": { target: API_TARGET, timeout: 30_000 },
    },
  },
});
