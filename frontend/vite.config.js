import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API_TARGET = "http://127.0.0.1:8010";
const PROXY_TIMEOUT_MS = 10 * 60 * 1000;

function apiProxy(timeout = PROXY_TIMEOUT_MS) {
  return { target: API_TARGET, timeout, proxyTimeout: timeout };
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/generar": apiProxy(),
      "/health": apiProxy(30_000),
      "/historial": apiProxy(30_000),
      "/extraer-pdf-estructurado": apiProxy(),
      "/extraer-pdf": apiProxy(),
      "/muestras-pdf": apiProxy(30_000),
    },
  },
});
