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

/**
 * Consulta GET /api/public/config uma vez (sem cookie, sem tocar em /auth/*).
 * Fail-closed: todas as flags começam e permanecem `false` em caso de falha.
 */
export function FlagsProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<ConfigPublica>(CONFIG_PUBLICA_FECHADA);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    const controle = new AbortController();
    obterConfigPublica(controle.signal)
      .then((recebida) => {
        setConfig(recebida);
        setCarregando(false);
      })
      .catch((causa) => {
        if (foiCancelada(causa)) return;
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
