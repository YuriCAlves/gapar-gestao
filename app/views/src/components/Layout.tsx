import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Confirmacao } from "./Dialogo";
import { IconeAdmin, IconeHoje, IconeMais, IconePata, IconeSair } from "./Icones";

interface ItemDeNavegacao {
  para: string;
  rotulo: string;
  icone: JSX.Element;
  fim?: boolean;
}

function rotuloDoPerfil(perfil: string): string {
  return perfil === "Administradora" ? "Administradora" : "Voluntária";
}

function primeiroNome(nome: string | null, email: string): string {
  const base = nome?.trim() || email.split("@")[0];
  return base.split(/\s+/)[0];
}

/** Estrutura das telas internas: cabeçalho, conteúdo e navegação ao alcance do polegar. */
export function Layout() {
  const { usuario, ehAdministradora, sair } = useAuth();
  const [confirmandoSaida, setConfirmandoSaida] = useState(false);
  const [saindo, setSaindo] = useState(false);

  const itens: ItemDeNavegacao[] = [
    { para: "/hoje", rotulo: "Hoje", icone: <IconeHoje /> },
    { para: "/animais", rotulo: "Animais", icone: <IconePata />, fim: true },
    { para: "/animais/novo", rotulo: "Resgate", icone: <IconeMais /> },
  ];
  if (ehAdministradora) itens.push({ para: "/admin", rotulo: "Gestão", icone: <IconeAdmin /> });

  if (!usuario) return null;

  return (
    <div className="min-h-dvh">
      <a
        href="#conteudo"
        className="sr-only z-[70] rounded-xl bg-mata-800 px-4 py-3 font-bold text-white focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        Pular para o conteúdo
      </a>

      <header className="sticky top-0 z-40 border-b border-creme-200 bg-creme-50/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2.5">
          <Link to="/hoje" className="flex min-h-11 shrink-0 items-center gap-2 rounded-xl" aria-label="GAPAR Gestão, ir para Hoje">
            <span className="grid size-10 place-items-center rounded-xl bg-mata-700 text-creme-50" aria-hidden="true">
              <IconePata tamanho={22} />
            </span>
            <span className="hidden leading-tight font-extrabold text-tinta-900 min-[400px]:block">
              GAPAR
              <span className="block text-sm font-bold text-mata-700">Gestão</span>
            </span>
          </Link>

          <nav aria-label="Principal" className="ml-4 hidden flex-1 gap-1 md:flex">
            {itens.map((item) => (
              <NavLink
                key={item.para}
                to={item.para}
                end={item.fim}
                className={({ isActive }) =>
                  `flex min-h-11 items-center gap-2 rounded-xl px-3.5 font-bold transition-colors ${
                    isActive ? "bg-mata-700 text-white" : "text-tinta-700 hover:bg-mata-50"
                  }`
                }
              >
                {item.icone}
                {item.rotulo}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex min-w-0 items-center gap-2">
            <div className="min-w-0 text-right leading-tight">
              <p className="truncate font-bold text-tinta-900">{primeiroNome(usuario.name, usuario.email)}</p>
              <p className={`truncate text-sm font-bold ${ehAdministradora ? "text-barro-700" : "text-mata-700"}`}>
                {rotuloDoPerfil(usuario.role)}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setConfirmandoSaida(true)}
              className="grid size-11 shrink-0 place-items-center rounded-full text-tinta-700 hover:bg-creme-200"
              aria-label="Sair do sistema"
              title="Sair"
            >
              <IconeSair />
            </button>
          </div>
        </div>
      </header>

      <main id="conteudo" tabIndex={-1} className="pb-barra mx-auto max-w-6xl px-4 pt-4 outline-none md:pb-10">
        <Outlet />
      </main>

      {/* Barra inferior no celular: alvos grandes, ao alcance do polegar */}
      <nav
        aria-label="Principal"
        className="pb-segura fixed inset-x-0 bottom-0 z-40 border-t border-creme-200 bg-white/95 backdrop-blur md:hidden"
      >
        <ul className="mx-auto flex max-w-lg">
          {itens.map((item) => (
            <li key={item.para} className="flex-1">
              <NavLink
                to={item.para}
                end={item.fim}
                className={({ isActive }) =>
                  `flex min-h-16 flex-col items-center justify-center gap-0.5 text-sm font-bold ${
                    isActive ? "text-mata-800" : "text-tinta-500"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={`grid h-8 w-14 place-items-center rounded-full transition-colors ${isActive ? "bg-mata-100" : ""}`}
                    >
                      {item.icone}
                    </span>
                    {item.rotulo}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <Confirmacao
        aberta={confirmandoSaida}
        titulo="Sair do sistema?"
        textoConfirmar="Sair"
        ocupada={saindo}
        aoCancelar={() => setConfirmandoSaida(false)}
        aoConfirmar={async () => {
          setSaindo(true);
          await sair();
        }}
      >
        <p>Você vai precisar entrar de novo com sua conta Google para continuar.</p>
      </Confirmacao>
    </div>
  );
}

export function CabecalhoDaPagina({
  titulo,
  subtitulo,
  acao,
}: {
  titulo: string;
  subtitulo?: string;
  acao?: JSX.Element;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-2xl sm:text-3xl">{titulo}</h1>
        {subtitulo && <p className="mt-0.5 text-tinta-700">{subtitulo}</p>}
      </div>
      {acao}
    </div>
  );
}

