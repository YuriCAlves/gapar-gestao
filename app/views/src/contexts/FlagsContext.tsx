import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { obterConfigPublica } from "../api/public";
import { foiCancelada } from "../api/http";
import { Carregando } from "../components/Estados";
import NaoEncontradaPage from "../pages/NaoEncontradaPage";
import { CONFIG_PUBLICA_FECHADA } from "../types/contratos";
import type { ConfigPublica, FlagPublica } from "../types/contratos";

interface ValorDasFlags {
  config: ConfigPublica;
  flags: Record<FlagPublica, boolean>;
  carregando: boolean;
  turnstileSiteKey: string | null;
  whatsappAdocao: string | null;
  ativa: (flag: FlagPublica) => boolean;
}

const FlagsContext = createContext<ValorDasFlags | null>(null);

/** Tempo máximo de espera por GET /api/public/config antes de fechar como fail-closed. */
export const TIMEOUT_CONFIG_PUBLICA_MS = 8000;

/**
 * Executa a busca de configuração pública com tempo limite rígido, sem chamar abort() no timeout
 * (evitando que o AbortError seja engolido). Se o prazo vencer, resolve como CONFIG_PUBLICA_FECHADA
 * para que nenhuma página pública fique presa em "Carregando...".
 */
export async function carregarConfigPublicaComTimeout(
  buscar: (sinal?: AbortSignal) => Promise<ConfigPublica> = obterConfigPublica,
  timeoutMs = TIMEOUT_CONFIG_PUBLICA_MS,
  sinalExterno?: AbortSignal,
): Promise<ConfigPublica> {
  if (sinalExterno?.aborted) {
    throw new DOMException("Cancelado", "AbortError");
  }

  let temporizador: ReturnType<typeof globalThis.setTimeout> | undefined;
  const promessaTimeout = new Promise<ConfigPublica>((resolve) => {
    temporizador = globalThis.setTimeout(() => {
      resolve(CONFIG_PUBLICA_FECHADA);
    }, timeoutMs);
  });

  const promessaBusca = Promise.resolve()
    .then(() => buscar(sinalExterno))
    .catch((causa) => {
      if (foiCancelada(causa)) throw causa;
      return CONFIG_PUBLICA_FECHADA;
    });

  try {
    return await Promise.race([promessaBusca, promessaTimeout]);
  } finally {
    if (temporizador !== undefined) {
      globalThis.clearTimeout(temporizador);
    }
  }
}

/**
 * Consulta GET /api/public/config uma vez (sem cookie, sem tocar em /auth/*), com tempo limite.
 * Fail-closed: todas as flags começam e permanecem `false` em caso de falha ou timeout.
 */
export function FlagsProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<ConfigPublica>(CONFIG_PUBLICA_FECHADA);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    const controle = new AbortController();
    carregarConfigPublicaComTimeout(obterConfigPublica, TIMEOUT_CONFIG_PUBLICA_MS, controle.signal)
      .then((recebida) => {
        if (controle.signal.aborted) return;
        setConfig(recebida);
        setCarregando(false);
      })
      .catch((causa) => {
        if (foiCancelada(causa) || controle.signal.aborted) return;
        setConfig(CONFIG_PUBLICA_FECHADA);
        setCarregando(false);
      });
    return () => controle.abort();
  }, []);

  const valor = useMemo<ValorDasFlags>(
    () => ({
      config,
      flags: config.flags,
      carregando,
      turnstileSiteKey: config.turnstile_site_key,
      whatsappAdocao: config.whatsapp_adocao,
      ativa: (flag) => config.flags[flag] === true,
    }),
    [config, carregando],
  );

  return <FlagsContext.Provider value={valor}>{children}</FlagsContext.Provider>;
}

export function useFlags(): ValorDasFlags {
  const contexto = useContext(FlagsContext);
  if (!contexto) throw new Error("useFlags precisa estar dentro de <FlagsProvider>.");
  return contexto;
}

/** Mostra `children` apenas quando a flag estiver ligada (fail-closed). */
export function RequerFlag({
  flag,
  fallback = null,
  children,
}: {
  flag: FlagPublica;
  fallback?: ReactNode;
  children: ReactNode;
}) {
  const { ativa } = useFlags();
  return <>{ativa(flag) ? children : fallback}</>;
}

/** Protege uma rota por feature flag. Com a flag desligada, exibe NaoEncontradaPage. */
export function RotaComFlag({
  flag,
  publica = false,
  children,
}: {
  flag: FlagPublica;
  publica?: boolean;
  children: ReactNode;
}) {
  const { carregando, ativa } = useFlags();

  if (carregando) {
    return (
      <div className="grid min-h-64 place-items-center px-4">
        <Carregando />
      </div>
    );
  }

  if (!ativa(flag)) {
    return <NaoEncontradaPage publica={publica} />;
  }

  return <>{children}</>;
}
