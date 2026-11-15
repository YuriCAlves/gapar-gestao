import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useLocation, useSearchParams } from "react-router-dom";
import { consultarOpcoesDeEntrada, URL_ENTRAR_COM_GOOGLE } from "../api/auth";
import { foiCancelada, textoDoErro } from "../api/http";
import { Botao, classesDoBotao } from "../components/Botao";
import { CampoTexto } from "../components/Campos";
import { Aviso, Carregando } from "../components/Estados";
import { IconePata } from "../components/Icones";
import { useAuth } from "../contexts/AuthContext";
import type { OpcoesDeEntrada } from "../types";
import { mensagemDeErroDeEntrada } from "../utils/mensagens";

const CHAVE_DESTINO = "gapar:voltarPara";

function lerDestinoGuardado(): string | null {
  try {
    return sessionStorage.getItem(CHAVE_DESTINO);
  } catch {
    return null;
  }
}

function guardarDestino(destino: string | null) {
  try {
    if (destino) sessionStorage.setItem(CHAVE_DESTINO, destino);
    else sessionStorage.removeItem(CHAVE_DESTINO);
  } catch {
    // navegador sem armazenamento: depois de entrar, a pessoa vai para "Hoje"
  }
}

function LogoGoogle() {
  return (
    <svg width="22" height="22" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.700 29.200 36 24 36c-6.600 0-12-5.400-12-12s5.400-12 12-12c3.100 0 5.800 1.200 7.900 3l5.700-5.700C34 6.100 29.300 4 24 4 12.900 4 4 12.900 4 24s8.900 20 20 20 20-8.900 20-20c0-1.300-.1-2.400-.4-3.500z" />
      <path fill="#FF3D00" d="m6.300 14.700 6.600 4.800C14.700 15.100 19 12 24 12c3.100 0 5.800 1.200 7.900 3l5.700-5.700C34 6.100 29.300 4 24 4 16.300 4 9.700 8.300 6.300 14.700z" />
      <path fill="#4CAF50" d="M24 44c5.200 0 9.900-2 13.400-5.200l-6.200-5.200C29.200 35.100 26.700 36 24 36c-5.200 0-9.600-3.300-11.300-8l-6.500 5C9.500 39.600 16.200 44 24 44z" />
      <path fill="#1976D2" d="M43.600 20.500H42V20H24v8h11.300c-.8 2.200-2.200 4.200-4.100 5.600l6.200 5.200C37 39.200 44 34 44 24c0-1.300-.1-2.400-.4-3.500z" />
    </svg>
  );
}

export default function LoginPage() {
  const { situacao, avisoDeSessao, saiuPorVontade, entrarEmModoDeTeste } = useAuth();
  const local = useLocation();
  const [parametros] = useSearchParams();
  const [opcoes, setOpcoes] = useState<OpcoesDeEntrada | null>(null);
  const [erroOpcoes, setErroOpcoes] = useState<string | null>(null);
  const [emailTeste, setEmailTeste] = useState("");
  const [entrando, setEntrando] = useState(false);
  const [erroTeste, setErroTeste] = useState<string | null>(null);

  // A rota pedida antes do login. Fica guardada também para a volta do Google (que passa por "/").
  const estado = local.state as { voltarPara?: string } | null;
  const destinoPedido = estado?.voltarPara && estado.voltarPara !== "/entrar" ? estado.voltarPara : null;
  useEffect(() => {
    if (destinoPedido) guardarDestino(destinoPedido);
  }, [destinoPedido]);

  useEffect(() => {
    const controle = new AbortController();
    consultarOpcoesDeEntrada(controle.signal)
      .then(setOpcoes)
      .catch((causa: unknown) => {
        if (!foiCancelada(causa)) setErroOpcoes(textoDoErro(causa));
      });
    return () => controle.abort();
  }, []);

  if (situacao === "autenticada") {
    const destino = destinoPedido ?? lerDestinoGuardado() ?? "/hoje";
    guardarDestino(null);
    return <Navigate to={destino} replace />;
  }

  const erroGoogle = mensagemDeErroDeEntrada(parametros.get("erro"));
  const avisoSessao =
    avisoDeSessao === "revogada"
      ? "Seu acesso foi desativado pela administradora. Se achar que é um engano, fale com ela."
      : avisoDeSessao === "expirada"
        ? "Sua sessão terminou. Entre de novo para continuar de onde parou. Se a entrada for recusada, seu acesso pode ter sido desativado: fale com a administradora."
        : null;

  async function entrarTeste(evento: FormEvent) {
    evento.preventDefault();
    setErroTeste(null);
    setEntrando(true);
    try {
      await entrarEmModoDeTeste(emailTeste.trim() || undefined);
    } catch (causa) {
      setErroTeste(textoDoErro(causa));
      setEntrando(false);
    }
  }

  return (
    <main className="flex min-h-dvh flex-col bg-mata-800 sm:items-center sm:justify-center sm:p-6">
      <div className="flex flex-col items-center gap-3 px-6 pt-12 pb-8 text-center text-creme-50 sm:pt-0">
        <span className="grid size-16 place-items-center rounded-2xl bg-creme-50 text-mata-700" aria-hidden="true">
          <IconePata tamanho={36} />
        </span>
        <h1 className="text-3xl text-creme-50">GAPAR Gestão</h1>
        <p className="max-w-xs text-mata-50">Cuidado diário dos animais acolhidos pelo GAPAR.</p>
      </div>

      <div className="flex-1 rounded-t-3xl bg-creme-50 px-5 pt-7 pb-10 sm:w-full sm:max-w-md sm:flex-none sm:rounded-3xl sm:px-8">
        <h2 className="text-xl">Entrar</h2>
        <p className="mt-1 mb-5">Use a conta Google que a administradora liberou para você.</p>

        <div className="space-y-3">
          {saiuPorVontade && !erroGoogle && <Aviso tipo="sucesso">Você saiu do sistema. Até logo!</Aviso>}
          {avisoSessao && (
            <Aviso tipo={avisoDeSessao === "revogada" ? "perigo" : "atencao"} anunciar>
              {avisoSessao}
            </Aviso>
          )}
          {erroGoogle && (
            <Aviso tipo="perigo" titulo="Não foi possível entrar" anunciar>
              {erroGoogle}
            </Aviso>
          )}
        </div>

        <div className="mt-5">
          {!opcoes && !erroOpcoes && <Carregando texto="Preparando a entrada..." />}
          {erroOpcoes && (
            <Aviso tipo="perigo" anunciar>
              {erroOpcoes}
            </Aviso>
          )}
          {opcoes && (
            <>
              {opcoes.google_configurado ? (
                <a href={URL_ENTRAR_COM_GOOGLE} className={classesDoBotao("secundario", "grande", "w-full border-contorno text-tinta-900")}>
                  <LogoGoogle />
                  Entrar com Google
                </a>
              ) : (
                <>
                  <Botao variante="secundario" tamanho="grande" larguraTotal disabled aria-describedby="google-indisponivel" icone={<LogoGoogle />}>
                    Entrar com Google
                  </Botao>
                  <p id="google-indisponivel" className="mt-2 text-tinta-700">
                    A entrada com Google ainda não foi ativada neste sistema. Avise a administradora.
                  </p>
                </>
              )}

              {opcoes.dev_login && (
                <form onSubmit={entrarTeste} className="mt-8 rounded-2xl border-2 border-dashed border-barro-200 bg-white p-4">
                  <h3 className="text-lg">Entrada de teste</h3>
                  <p className="mt-1 mb-3 text-tinta-700">
                    Disponível só no computador de desenvolvimento. Deixe o e-mail em branco para entrar como administradora.
                  </p>
                  <CampoTexto
                    rotulo="E-mail autorizado"
                    type="email"
                    autoComplete="email"
                    inputMode="email"
                    placeholder="voluntaria1@gapar.org.br"
                    value={emailTeste}
                    onChange={(e) => setEmailTeste(e.target.value)}
                    erro={erroTeste}
                  />
                  <Botao type="submit" className="mt-3" larguraTotal ocupado={entrando}>
                    Entrar para testar
                  </Botao>
                </form>
              )}
            </>
          )}
        </div>
      </div>
    </main>
  );
}
