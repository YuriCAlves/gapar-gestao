import { useEffect, useRef } from "react";
import type { KeyboardEvent, ReactNode } from "react";

export interface DefinicaoDeAba<T extends string> {
  id: T;
  rotulo: string;
  /** Número pequeno ao lado do rótulo (ex.: doses pendentes). */
  contador?: number;
}

interface PropsDasAbas<T extends string> {
  /** Prefixo dos ids, para ligar cada aba ao seu painel. */
  prefixo: string;
  rotulo: string;
  abas: DefinicaoDeAba<T>[];
  ativa: T;
  aoMudar: (aba: T) => void;
}

/**
 * Faixa de abas. Em telas estreitas a faixa rola na horizontal (só ela, nunca a página);
 * as setas do teclado trocam de aba.
 */
export function Abas<T extends string>({ prefixo, rotulo, abas, ativa, aoMudar }: PropsDasAbas<T>) {
  const faixa = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const botao = faixa.current?.querySelector<HTMLElement>('[aria-selected="true"]');
    botao?.scrollIntoView({ block: "nearest", inline: "center" });
  }, [ativa]);

  function aoTeclar(evento: KeyboardEvent<HTMLDivElement>) {
    const indice = abas.findIndex((aba) => aba.id === ativa);
    let proximo = indice;
    if (evento.key === "ArrowRight") proximo = (indice + 1) % abas.length;
    else if (evento.key === "ArrowLeft") proximo = (indice - 1 + abas.length) % abas.length;
    else if (evento.key === "Home") proximo = 0;
    else if (evento.key === "End") proximo = abas.length - 1;
    else return;
    evento.preventDefault();
    const destino = abas[proximo];
    aoMudar(destino.id);
    document.getElementById(`${prefixo}-aba-${destino.id}`)?.focus();
  }

  return (
    <div
      ref={faixa}
      role="tablist"
      aria-label={rotulo}
      onKeyDown={aoTeclar}
      className="rolagem-sem-barra -mx-4 flex gap-1 overflow-x-auto border-b-2 border-creme-200 px-4 sm:mx-0 sm:px-0"
    >
      {abas.map((aba) => {
        const selecionada = aba.id === ativa;
        return (
          <button
            key={aba.id}
            id={`${prefixo}-aba-${aba.id}`}
            type="button"
            role="tab"
            aria-selected={selecionada}
            aria-controls={`${prefixo}-painel-${aba.id}`}
            tabIndex={selecionada ? 0 : -1}
            onClick={() => aoMudar(aba.id)}
            className={`-mb-0.5 flex min-h-12 shrink-0 items-center gap-2 border-b-4 px-3.5 font-bold whitespace-nowrap transition-colors ${
              selecionada
                ? "border-mata-700 text-mata-800"
                : "border-transparent text-tinta-500 hover:border-creme-300 hover:text-tinta-900"
            }`}
          >
            {aba.rotulo}
            {aba.contador !== undefined && aba.contador > 0 && (
              <span className="grid min-w-6 place-items-center rounded-full bg-barro-600 px-1.5 text-sm leading-6 text-white">
                {aba.contador}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export function PainelDaAba({
  prefixo,
  id,
  children,
}: {
  prefixo: string;
  id: string;
  children: ReactNode;
}) {
  return (
    <div
      role="tabpanel"
      id={`${prefixo}-painel-${id}`}
      aria-labelledby={`${prefixo}-aba-${id}`}
      tabIndex={-1}
      className="animate-entrar pt-5 outline-none"
    >
      {children}
    </div>
  );
}
