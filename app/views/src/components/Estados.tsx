import type { ReactNode } from "react";
import { Botao, Girando } from "./Botao";
import { IconeAlerta, IconeAtualizar, IconeCadeado, IconeCerto, IconeInfo } from "./Icones";

// Estados de tela: carregando, vazio, erro, e caixas de aviso.

export function Carregando({ texto = "Carregando..." }: { texto?: string }) {
  return (
    <div role="status" className="flex flex-col items-center justify-center gap-3 py-14 text-mata-800">
      <Girando tamanho={36} />
      <p className="font-semibold text-tinta-700">{texto}</p>
    </div>
  );
}

/** Blocos cinzentos no lugar do conteúdo enquanto ele chega. */
export function Esqueleto({ className = "" }: { className?: string }) {
  return <div aria-hidden="true" className={`animate-pulsar rounded-xl bg-creme-200 ${className}`} />;
}

export function EstadoVazio({
  icone,
  titulo,
  children,
  acao,
}: {
  icone?: ReactNode;
  titulo: string;
  children?: ReactNode;
  acao?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-cartao border-2 border-dashed border-creme-300 bg-white/60 px-5 py-10 text-center">
      {icone && (
        <span className="mb-1 grid size-14 place-items-center rounded-full bg-mata-50 text-mata-700" aria-hidden="true">
          {icone}
        </span>
      )}
      <h3 className="text-lg">{titulo}</h3>
      {children && <div className="max-w-md text-tinta-700">{children}</div>}
      {acao && <div className="mt-3">{acao}</div>}
    </div>
  );
}

export function EstadoErro({
  mensagem,
  aoTentarDeNovo,
}: {
  mensagem: string;
  aoTentarDeNovo?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-2 rounded-cartao border-2 border-perigo-100 bg-perigo-50 px-5 py-8 text-center"
    >
      <span className="grid size-14 place-items-center rounded-full bg-white text-perigo-700" aria-hidden="true">
        <IconeAlerta tamanho={28} />
      </span>
      <h3 className="text-lg text-perigo-900">Não deu para carregar</h3>
      <p className="max-w-md text-perigo-900">{mensagem}</p>
      {aoTentarDeNovo && (
        <Botao variante="secundario" onClick={aoTentarDeNovo} icone={<IconeAtualizar tamanho={20} />} className="mt-3">
          Tentar de novo
        </Botao>
      )}
    </div>
  );
}

type TipoDeAviso = "informacao" | "atencao" | "perigo" | "sucesso" | "preservado";

const ESTILOS_DE_AVISO: Record<TipoDeAviso, { caixa: string; icone: ReactNode }> = {
  informacao: { caixa: "border-ceu-100 bg-ceu-50 text-ceu-900", icone: <IconeInfo /> },
  atencao: { caixa: "border-ambar-100 bg-ambar-50 text-ambar-900", icone: <IconeAlerta /> },
  perigo: { caixa: "border-perigo-100 bg-perigo-50 text-perigo-900", icone: <IconeAlerta /> },
  sucesso: { caixa: "border-mata-200 bg-mata-50 text-mata-900", icone: <IconeCerto /> },
  preservado: { caixa: "border-pedra-200 bg-pedra-100 text-pedra-900", icone: <IconeCadeado /> },
};

export function Aviso({
  tipo = "informacao",
  titulo,
  children,
  anunciar = false,
  className = "",
}: {
  tipo?: TipoDeAviso;
  titulo?: string;
  children?: ReactNode;
  /** Lido imediatamente por leitores de tela (erros de formulário, bloqueios). */
  anunciar?: boolean;
  className?: string;
}) {
  const estilo = ESTILOS_DE_AVISO[tipo];
  return (
    <div
      role={anunciar ? "alert" : undefined}
      className={`flex gap-3 rounded-2xl border-2 px-4 py-3 ${estilo.caixa} ${className}`}
    >
      <span className="mt-0.5 shrink-0" aria-hidden="true">
        {estilo.icone}
      </span>
      <div className="min-w-0 flex-1">
        {titulo && <p className="font-extrabold">{titulo}</p>}
        {children && <div className="break-words">{children}</div>}
      </div>
    </div>
  );
}
