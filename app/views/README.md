# Camada View (MVC)

SPA em React + TypeScript (Vite + Tailwind) que consome a API JSON servida pelos controllers.

- `index.html` — ponto de entrada do Vite
- `public/` — arquivos estáticos copiados como estão para o build
- `src/` — código da interface (`pages/`, `components/`, `contexts/`, `hooks/`, `api/`, `utils/`, `types/`)

Os comandos (`npm run dev`, `npm run build`, `npm test`) continuam sendo executados na raiz do
repositório; o `vite.config.ts` aponta a raiz do Vite para esta pasta e gera o build em `/dist`.
