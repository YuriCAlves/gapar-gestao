import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { consultarSessao, encerrarSessao, entrarEmModoDeTeste } from "../api/auth";
import { definirOuvinteDeSessao, foiCancelada } from "../api/http";
import type { MotivoSessaoEncerrada } from "../api/http";
import type { Usuaria } from "../types";

/** Por que a pessoa está na tela de entrada sem ter pedido para sair. */
export type AvisoDeSessao = MotivoSessaoEncerrada | null;

type Situacao = "verificando" | "autenticada" | "anonima" | "indisponivel";

interface ValorDoContexto {
  situacao: Situacao;
  usuario: Usuaria | null;
  ehAdministradora: boolean;
  /** Preenchido quando o servidor encerrou a sessão (tempo esgotado ou acesso desativado). */
  avisoDeSessao: AvisoDeSessao;
  /** True logo depois de a própria pessoa tocar em "Sair". */
  saiuPorVontade: boolean;
  verificarSessao: () => Promise<void>;
  entrarEmModoDeTeste: (email?: string) => Promise<void>;
  sair: () => Promise<void>;
}

const AuthContext = createContext<ValorDoContexto | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [situacao, setSituacao] = useState<Situacao>("verificando");
  const [usuario, setUsuario] = useState<Usuaria | null>(null);
  const [avisoDeSessao, setAvisoDeSessao] = useState<AvisoDeSessao>(null);
  const [saiuPorVontade, setSaiuPorVontade] = useState(false);
  const autenticada = useRef(false);

  const verificarSessao = useCallback(async (sinal?: AbortSignal) => {
    setSituacao("verificando");
    try {
      const atual = await consultarSessao(sinal);
      autenticada.current = atual !== null;
      setUsuario(atual);
      setSituacao(atual ? "autenticada" : "anonima");
    } catch (causa) {
      if (foiCancelada(causa)) return;
      setSituacao("indisponivel");
    }
  }, []);

  // Sessão consultada uma vez ao abrir o app
  useEffect(() => {
    const controle = new AbortController();
    void verificarSessao(controle.signal);
    return () => controle.abort();
  }, [verificarSessao]);

  // Qualquer tela que receba "sessão inválida" do servidor devolve a pessoa para a entrada
  useEffect(() => {
    definirOuvinteDeSessao((motivo) => {
      if (!autenticada.current) return;
      autenticada.current = false;
      setUsuario(null);
      setSaiuPorVontade(false);
      setAvisoDeSessao(motivo);
      setSituacao("anonima");
    });
    return () => definirOuvinteDeSessao(null);
  }, []);

  const entrar = useCallback(async (email?: string) => {
    const novo = await entrarEmModoDeTeste(email);
    autenticada.current = true;
    setAvisoDeSessao(null);
    setSaiuPorVontade(false);
    setUsuario(novo);
    setSituacao("autenticada");
  }, []);

  const sair = useCallback(async () => {
    try {
      await encerrarSessao();
    } catch {
      // Mesmo que o servidor não responda, a pessoa pediu para sair: seguimos para a entrada.
    }
    autenticada.current = false;
    setAvisoDeSessao(null);
    setSaiuPorVontade(true);
    setUsuario(null);
    setSituacao("anonima");
  }, []);

  const valor = useMemo<ValorDoContexto>(
    () => ({
      situacao,
      usuario,
      ehAdministradora: usuario?.role === "Administradora",
      avisoDeSessao,
      saiuPorVontade,
      verificarSessao: () => verificarSessao(),
      entrarEmModoDeTeste: entrar,
      sair,
    }),
    [situacao, usuario, avisoDeSessao, saiuPorVontade, verificarSessao, entrar, sair],
  );

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}

export function useAuth(): ValorDoContexto {
  const contexto = useContext(AuthContext);
  if (!contexto) throw new Error("useAuth precisa estar dentro de <AuthProvider>.");
  return contexto;
}
