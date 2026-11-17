import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Camada View (MVC): a SPA React fica em app/views; o build sai em /dist (lido pela Vercel).
const VIEWS = fileURLToPath(new URL("./app/views", import.meta.url));
const DIST = fileURLToPath(new URL("./dist", import.meta.url));

// Em dev, /api, /auth e /static (fotos enviadas) vão para o Flask local (npm run dev:api).
// Em produção a Vercel faz esse roteamento via vercel.json (mesmo domínio, sem CORS).
const FLASK_LOCAL = "http://127.0.0.1:5000";

export default defineConfig({
  root: VIEWS,
  plugins: [react(), tailwindcss()],
  build: {
    outDir: DIST,
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": FLASK_LOCAL,
      "/auth": FLASK_LOCAL,
      "/static": FLASK_LOCAL,
    },
  },
});
