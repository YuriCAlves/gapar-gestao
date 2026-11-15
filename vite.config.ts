import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Em dev, /api, /auth e /static (fotos enviadas) vão para o Flask local (npm run dev:api).
// Em produção a Vercel faz esse roteamento via vercel.json (mesmo domínio, sem CORS).
const FLASK_LOCAL = "http://127.0.0.1:5000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": FLASK_LOCAL,
      "/auth": FLASK_LOCAL,
      "/static": FLASK_LOCAL,
    },
  },
});
