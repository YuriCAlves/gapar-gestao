import { Suspense } from "react";
import { Link, Outlet } from "react-router-dom";
import { useFlags } from "../contexts/FlagsContext";
import { Carregando } from "./Estados";
import { IconePata } from "./Icones";

/**
 * Estrutura das páginas públicas da ONG GAPAR (/adote, /termo, /carteira, /privacidade).
 * Fica fora do AuthContext: não consulta /auth/status nem exibe menu interno.
 */
export function LayoutPublico() {
  const { ativa } = useFlags();
  const destinoLogo = ativa("vitrine") ? "/adote" : "/privacidade";

  return (
    <div className="flex min-h-dvh flex-col bg-creme-50 text-tinta-900">
      <a
        href="#conteudo"
        className="sr-only z-[70] rounded-xl bg-mata-800 px-4 py-3 font-bold text-white focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        Pular para o conteúdo
      </a>

      <header className="sticky top-0 z-40 border-b border-creme-200 bg-creme-50/95 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3">
          <Link
            to={destinoLogo}
            className="flex min-h-11 items-center gap-2.5 rounded-xl"
            aria-label={ativa("vitrine") ? "ONG GAPAR, ir para a vitrine de adoção" : "ONG GAPAR, política de privacidade"}
          >
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-mata-700 text-creme-50" aria-hidden="true">
              <IconePata tamanho={22} />
            </span>
            <span className="leading-tight font-extrabold text-tinta-900">
              ONG GAPAR
              <span className="block text-sm font-bold text-mata-700">Proteção e adoção responsável</span>
            </span>
          </Link>
        </div>
      </header>

      <main id="conteudo" tabIndex={-1} className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 outline-none">
        <Suspense
          fallback={
            <div className="grid min-h-64 place-items-center px-4">
              <Carregando />
            </div>
          }
        >
          <Outlet />
        </Suspense>
      </main>

      <footer className="mt-auto border-t border-creme-200 bg-creme-100">
        <div className="mx-auto flex max-w-5xl flex-col gap-2 px-4 py-5 text-sm text-tinta-700 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-semibold">ONG GAPAR · Grupo de Apoio e Proteção Animal</p>
          <Link
            to="/privacidade"
            className="inline-flex min-h-11 items-center font-bold text-mata-800 underline underline-offset-4 hover:text-mata-700"
          >
            Política de Privacidade
          </Link>
        </div>
      </footer>
    </div>
  );
}
