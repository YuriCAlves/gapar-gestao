import { Suspense, useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useFlags } from "../contexts/FlagsContext";
import type { FlagPublica } from "../types/contratos";
import { Confirmacao, Dialogo } from "./Dialogo";
import { Carregando } from "./Estados";
import {
  IconeAdmin,
  IconeCoracao,
  IconeHoje,
  IconeInfo,
  IconeLocal,
  IconeMais,
  IconeMenu,
  IconePata,
  IconeRemedio,
  IconeSair,
} from "./Icones";

interface ItemDeNavegacao {
  para: string;
  rotulo: string;
  icone: JSX.Element;
  fim?: boolean;
}

interface ItemDaGaveta {
  para: string;
  rotulo: string;
  descricao: string;
  icone: JSX.Element;
  flag?: FlagPublica;
  somenteAdmin?: boolean;
}

const ITENS_FUTUROS_GAVETA: ItemDaGaveta[] = [
  { para: "/estoque", rotulo: "Estoque", descricao: "Vacinas, remédios e alertas de validade", icone: <IconeRemedio />, flag: "estoque" },
  { para: "/candidaturas", rotulo: "Candidaturas", descricao: "Pedidos de adoção vindos da vitrine", icone: <IconeCoracao />, flag: "candidaturas" },
  { para: "/mapa", rotulo: "Mapa de resgates", descricao: "Origem dos resgates por bairro", icone: <IconeLocal />, flag: "mapa", somenteAdmin: true },
  { para: "/adote", rotulo: "Vitrine pública", descricao: "Ver a página aberta de adoção", icone: <IconePata />, flag: "vitrine" },
];

function rotuloDoPerfil(perfil: string): string {
  return perfil === "Administradora" ? "Administradora" : "Voluntária";
}

function primeiroNome(nome: string | null, email: string): string {
  const base = nome?.trim() || email.split("@")[0];
  return base.split(/\s+/)[0];
}

/** Estrutura das telas internas: cabeçalho, conteúdo, 4 abas e gaveta "Mais" ao alcance do polegar. */
export function Layout() {
  const { usuario, ehAdministradora, sair } = useAuth();
  const { ativa } = useFlags();
  const [gavetaAberta, setGavetaAberta] = useState(false);
  const [confirmandoSaida, setConfirmandoSaida] = useState(false);
  const [saindo, setSaindo] = useState(false);

  const itens: ItemDeNavegacao[] = [
    { para: "/hoje", rotulo: "Hoje", icone: <IconeHoje /> },
    { para: "/animais", rotulo: "Animais", icone: <IconePata />, fim: true },
    { para: "/animais/novo", rotulo: "Resgate", icone: <IconeMais /> },
  ];
  if (ehAdministradora) itens.push({ para: "/admin", rotulo: "Gestão", icone: <IconeAdmin /> });

  const extrasAtivos = ITENS_FUTUROS_GAVETA.filter(
    (item) => (!item.flag || ativa(item.flag)) && (!item.somenteAdmin || ehAdministradora),
  );

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
            {extrasAtivos.map((item) => (
              <NavLink
                key={item.para}
                to={item.para}
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

      {/* Barra inferior no celular: 4 abas mantidas + gaveta "Mais", ao alcance do polegar em 360px */}
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
                  `flex min-h-16 flex-col items-center justify-center gap-0.5 text-xs font-bold min-[380px]:text-sm ${
                    isActive ? "text-mata-800" : "text-tinta-500"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={`grid h-8 w-12 place-items-center rounded-full transition-colors min-[380px]:w-14 ${isActive ? "bg-mata-100" : ""}`}
                    >
                      {item.icone}
                    </span>
                    {item.rotulo}
                  </>
                )}
              </NavLink>
            </li>
          ))}
          <li className="flex-1">
            <button
              type="button"
              onClick={() => setGavetaAberta(true)}
              aria-expanded={gavetaAberta}
              aria-haspopup="dialog"
              className={`flex min-h-16 w-full flex-col items-center justify-center gap-0.5 text-xs font-bold min-[380px]:text-sm ${
                gavetaAberta ? "text-mata-800" : "text-tinta-500"
              }`}
            >
              <span
                className={`grid h-8 w-12 place-items-center rounded-full transition-colors min-[380px]:w-14 ${gavetaAberta ? "bg-mata-100" : ""}`}
              >
                <IconeMenu />
              </span>
              Mais
            </button>
          </li>
        </ul>
      </nav>

      {/* Gaveta "Mais" (folha inferior com botões min-h-14) */}
      <Dialogo aberto={gavetaAberta} aoFechar={() => setGavetaAberta(false)} titulo="Mais opções">
        <div className="space-y-2">
          {extrasAtivos.map((item) => (
            <NavLink
              key={item.para}
              to={item.para}
              onClick={() => setGavetaAberta(false)}
              className={({ isActive }) =>
                `flex min-h-14 items-center gap-3 rounded-xl border px-4 py-2.5 text-left transition-colors ${
                  isActive
                    ? "border-mata-700 bg-mata-50"
                    : "border-creme-200 bg-white hover:bg-mata-50"
                }`
              }
            >
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-mata-50 text-mata-700" aria-hidden="true">
                {item.icone}
              </span>
              <span className="min-w-0">
                <span className="block font-extrabold text-tinta-900">{item.rotulo}</span>
                <span className="block text-sm text-tinta-700">{item.descricao}</span>
              </span>
            </NavLink>
          ))}

          {ehAdministradora && (
            <NavLink
              to="/admin"
              onClick={() => setGavetaAberta(false)}
              className={({ isActive }) =>
                `flex min-h-14 items-center gap-3 rounded-xl border px-4 py-2.5 text-left transition-colors ${
                  isActive
                    ? "border-mata-700 bg-mata-50"
                    : "border-creme-200 bg-white hover:bg-mata-50"
                }`
              }
            >
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-barro-50 text-barro-700" aria-hidden="true">
                <IconeAdmin />
              </span>
              <span className="min-w-0">
                <span className="block font-extrabold text-tinta-900">Gestão</span>
                <span className="block text-sm text-tinta-700">Pessoas autorizadas, lista sigilosa e histórico</span>
              </span>
            </NavLink>
          )}

          <NavLink
            to="/privacidade"
            onClick={() => setGavetaAberta(false)}
            className={({ isActive }) =>
              `flex min-h-14 items-center gap-3 rounded-xl border px-4 py-2.5 text-left transition-colors ${
                isActive
                  ? "border-mata-700 bg-mata-50"
                  : "border-creme-200 bg-white hover:bg-mata-50"
              }`
            }
          >
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-creme-100 text-tinta-700" aria-hidden="true">
              <IconeInfo />
            </span>
            <span className="min-w-0">
              <span className="block font-extrabold text-tinta-900">Política de Privacidade</span>
              <span className="block text-sm text-tinta-700">Como a ONG GAPAR protege dados pessoais</span>
            </span>
          </NavLink>

          <button
            type="button"
            onClick={() => {
              setGavetaAberta(false);
              setConfirmandoSaida(true);
            }}
            className="flex min-h-14 w-full items-center gap-3 rounded-xl border border-perigo-100 bg-white px-4 py-2.5 text-left transition-colors hover:bg-perigo-100/40"
          >
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-perigo-100 text-perigo-700" aria-hidden="true">
              <IconeSair />
            </span>
            <span className="min-w-0">
              <span className="block font-extrabold text-perigo-700">Sair do sistema</span>
              <span className="block text-sm text-tinta-700">Encerrar sua sessão neste aparelho</span>
            </span>
          </button>
        </div>
      </Dialogo>

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

