import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Em dev, /api e /auth vao para o Flask local (npm run dev:api).
// Em producao a Vercel faz esse roteamento via vercel.json (mesmo dominio, sem CORS).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:5000",
      "/auth": "http://127.0.0.1:5000",
    },
  },
});
