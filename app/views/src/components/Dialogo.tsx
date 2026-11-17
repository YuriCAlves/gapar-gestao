import { useId, useLayoutEffect, useRef } from "react";
import type { ReactNode } from "react";
import { Botao } from "./Botao";
import { IconeFechar } from "./Icones";

interface PropsDoDialogo {
  aberto: boolean;
  aoFechar: () => void;
  titulo: string;
  children: ReactNode;
  rodape?: ReactNode;
  /** Quando true, não fecha ao tocar fora nem mostra o X (alertas que exigem leitura). */
  exigeResposta?: boolean;
  /** "alertdialog" para confirmações e alertas impeditivos. */
  papel?: "dialog" | "alertdialog";
}

/**
 * Janela sobre a tela, feita com <dialog> nativo: o foco fica preso dentro dela, Esc fecha
 * e o foco volta para onde estava. No celular sobe como folha a partir do rodapé.
 */
export function Dialogo({ aberto, aoFechar, titulo, children, rodape, exigeResposta = false, papel = "dialog" }: PropsDoDialogo) {
  if (!aberto) return null;
  return (
    <DialogoAberto aoFechar={aoFechar} titulo={titulo} rodape={rodape} exigeResposta={exigeResposta} papel={papel}>
      {children}
    </DialogoAberto>
  );
}

function DialogoAberto({ aoFechar, titulo, children, rodape, exigeResposta, papel }: Omit<PropsDoDialogo, "aberto">) {
  const referencia = useRef<HTMLDialogElement>(null);
  const idTitulo = useId();
  const idCorpo = useId();

  useLayoutEffect(() => {
    const dialogo = referencia.current;
    if (!dialogo) return;
    const focoAnterior = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (!dialogo.open) dialogo.showModal();
    return () => {
      if (dialogo.open) dialogo.close();
      focoAnterior?.focus();
    };
  }, []);

  return (
    <dialog
      ref={referencia}
      role={papel}
      aria-labelledby={idTitulo}
      aria-describedby={papel === "alertdialog" ? idCorpo : undefined}
      onCancel={(evento) => {
        evento.preventDefault();
        aoFechar();
      }}
      onClick={(evento) => {
        if (!exigeResposta && evento.target === referencia.current) aoFechar();
      }}
      className="fixed inset-0 mt-auto mb-0 flex max-h-[92dvh] w-full max-w-full animate-subir flex-col overflow-hidden rounded-t-3xl bg-white p-0 shadow-flutuante sm:m-auto sm:max-w-lg sm:rounded-3xl"
    >
      <div className="flex items-start justify-between gap-3 px-5 pt-5 pb-2">
        <h2 id={idTitulo} className="text-xl" tabIndex={-1}>
          {titulo}
        </h2>
        {!exigeResposta && (
          <button
            type="button"
            onClick={aoFechar}
            className="-mt-1.5 -mr-2 grid size-11 shrink-0 place-items-center rounded-full text-tinta-700 hover:bg-creme-100"
            aria-label="Fechar"
          >
            <IconeFechar />
          </button>
        )}
      </div>
      <div id={idCorpo} className="min-h-0 flex-1 overflow-y-auto px-5 pt-1 pb-5">
        {children}
      </div>
      {rodape && (
        <div className="pb-segura flex flex-col-reverse gap-2 border-t border-creme-200 bg-creme-50 px-5 pt-3 sm:flex-row sm:justify-end sm:pb-3">
          {rodape}
        </div>
      )}
    </dialog>
  );
}

interface PropsDaConfirmacao {
  aberta: boolean;
  titulo: string;
  children: ReactNode;
  textoConfirmar: string;
  textoCancelar?: string;
  /** Ações sem volta usam o botão vermelho. */
  perigosa?: boolean;
  ocupada?: boolean;
  aoConfirmar: () => void;
  aoCancelar: () => void;
}

/** Pergunta obrigatória antes de qualquer ação que não tem volta. */
export function Confirmacao({
  aberta,
  titulo,
  children,
  textoConfirmar,
  textoCancelar = "Voltar",
  perigosa = false,
  ocupada = false,
  aoConfirmar,
  aoCancelar,
}: PropsDaConfirmacao) {
  return (
    <Dialogo
      aberto={aberta}
      aoFechar={() => {
        if (!ocupada) aoCancelar();
      }}
      titulo={titulo}
      papel="alertdialog"
      rodape={
        <>
          {/* O botão de voltar vem primeiro no foco: confirmar exige um gesto deliberado */}
          <Botao variante="secundario" onClick={aoCancelar} disabled={ocupada} autoFocus>
            {textoCancelar}
          </Botao>
          <Botao variante={perigosa ? "perigo" : "primario"} onClick={aoConfirmar} ocupado={ocupada}>
            {textoConfirmar}
          </Botao>
        </>
      }
    >
      <div className="space-y-2">{children}</div>
    </Dialogo>
  );
}
