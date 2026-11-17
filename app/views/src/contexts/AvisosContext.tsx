import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { IconeAlerta, IconeCerto, IconeFechar } from "../components/Icones";

// Avisos rápidos no rodapé ("Baixa registrada", "Não foi possível salvar...").
// Ficam numa região anunciada por leitores de tela.

type TipoDeAviso = "sucesso" | "erro";

interface Aviso {
  id: number;
  tipo: TipoDeAviso;
  texto: string;
}

interface ValorDoContexto {
  avisarSucesso: (texto: string) => void;
  avisarErro: (texto: string) => void;
}

const AvisosContext = createContext<ValorDoContexto | null>(null);

const DURACAO_SUCESSO_MS = 4000;
const DURACAO_ERRO_MS = 8000;

export function AvisosProvider({ children }: { children: ReactNode }) {
  const [avisos, setAvisos] = useState<Aviso[]>([]);
  const proximoId = useRef(1);

  const fechar = useCallback((id: number) => {
    setAvisos((lista) => lista.filter((aviso) => aviso.id !== id));
  }, []);

  const avisar = useCallback(
    (tipo: TipoDeAviso, texto: string) => {
      const id = proximoId.current++;
      setAvisos((lista) => [...lista.slice(-2), { id, tipo, texto }]);
      window.setTimeout(() => fechar(id), tipo === "erro" ? DURACAO_ERRO_MS : DURACAO_SUCESSO_MS);
    },
    [fechar],
  );

  const valor = useMemo<ValorDoContexto>(
    () => ({
      avisarSucesso: (texto) => avisar("sucesso", texto),
      avisarErro: (texto) => avisar("erro", texto),
    }),
    [avisar],
  );

  return (
    <AvisosContext.Provider value={valor}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-0 bottom-[calc(5.75rem+env(safe-area-inset-bottom))] z-[60] flex flex-col items-center gap-2 px-3 md:bottom-6"
        aria-live="polite"
        role="status"
      >
        {avisos.map((aviso) => (
          <div
            key={aviso.id}
            className={`pointer-events-auto flex w-full max-w-md animate-entrar items-start gap-3 rounded-2xl px-4 py-3 font-semibold text-white shadow-flutuante ${
              aviso.tipo === "erro" ? "bg-perigo-700" : "bg-mata-800"
            }`}
          >
            <span className="mt-0.5 shrink-0" aria-hidden="true">
              {aviso.tipo === "erro" ? <IconeAlerta /> : <IconeCerto />}
            </span>
            <p className="min-w-0 flex-1 break-words">
              {aviso.tipo === "erro" && <span className="sr-only">Erro: </span>}
              {aviso.texto}
            </p>
            <button
              type="button"
              onClick={() => fechar(aviso.id)}
              className="-m-2 grid size-11 shrink-0 place-items-center rounded-full hover:bg-white/15 focus-visible:outline-white"
              aria-label="Fechar aviso"
            >
              <IconeFechar />
            </button>
          </div>
        ))}
      </div>
    </AvisosContext.Provider>
  );
}

export function useAvisos(): ValorDoContexto {
  const contexto = useContext(AvisosContext);
  if (!contexto) throw new Error("useAvisos precisa estar dentro de <AvisosProvider>.");
  return contexto;
}
