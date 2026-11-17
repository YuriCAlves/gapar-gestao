import { useId } from "react";
import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

// Campos de formulário: sempre com rótulo visível, mensagem de erro ligada ao campo
// e altura confortável para o toque.

const CAIXA =
  "block w-full rounded-xl border-2 bg-white px-3.5 text-tinta-900 placeholder:text-tinta-500 " +
  "transition-colors focus:border-mata-700 focus:outline-none focus-visible:outline-3 " +
  "disabled:border-creme-300 disabled:bg-creme-100 disabled:text-tinta-500";

function classesDaCaixa(comErro: boolean, extra = ""): string {
  return `${CAIXA} ${comErro ? "border-perigo-600" : "border-contorno"} ${extra}`;
}

interface PropsComuns {
  rotulo: string;
  /** Texto de ajuda abaixo do rótulo. */
  dica?: string;
  erro?: string | null;
  obrigatorio?: boolean;
  className?: string;
}

function Rotulo({ para, rotulo, obrigatorio }: { para: string; rotulo: string; obrigatorio?: boolean }) {
  return (
    <label htmlFor={para} className="mb-1 block font-bold text-tinta-900">
      {rotulo}
      {obrigatorio && (
        <span className="text-perigo-700" aria-hidden="true">
          {" "}
          *
        </span>
      )}
    </label>
  );
}

function Dica({ id, children }: { id: string; children: ReactNode }) {
  return (
    <p id={id} className="mb-1.5 text-tinta-500">
      {children}
    </p>
  );
}

function Erro({ id, children }: { id: string; children: ReactNode }) {
  return (
    <p id={id} className="mt-1.5 font-semibold text-perigo-700">
      {children}
    </p>
  );
}

function descricao(idDica: string, idErro: string, dica?: string, erro?: string | null): string | undefined {
  const ids = [dica ? idDica : "", erro ? idErro : ""].filter(Boolean).join(" ");
  return ids || undefined;
}

type PropsDoCampoTexto = PropsComuns & Omit<InputHTMLAttributes<HTMLInputElement>, "className" | "required">;

export function CampoTexto({ rotulo, dica, erro, obrigatorio, className = "", id, ...resto }: PropsDoCampoTexto) {
  const gerado = useId();
  const idCampo = id ?? gerado;
  return (
    <div className={className}>
      <Rotulo para={idCampo} rotulo={rotulo} obrigatorio={obrigatorio} />
      {dica && <Dica id={`${idCampo}-dica`}>{dica}</Dica>}
      <input
        id={idCampo}
        aria-required={obrigatorio || undefined}
        aria-invalid={erro ? true : undefined}
        aria-describedby={descricao(`${idCampo}-dica`, `${idCampo}-erro`, dica, erro)}
        className={classesDaCaixa(Boolean(erro), "min-h-12")}
        {...resto}
      />
      {erro && <Erro id={`${idCampo}-erro`}>{erro}</Erro>}
    </div>
  );
}

type PropsDoCampoArea = PropsComuns & Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "className" | "required">;

export function CampoArea({ rotulo, dica, erro, obrigatorio, className = "", id, rows = 3, ...resto }: PropsDoCampoArea) {
  const gerado = useId();
  const idCampo = id ?? gerado;
  return (
    <div className={className}>
      <Rotulo para={idCampo} rotulo={rotulo} obrigatorio={obrigatorio} />
      {dica && <Dica id={`${idCampo}-dica`}>{dica}</Dica>}
      <textarea
        id={idCampo}
        rows={rows}
        aria-required={obrigatorio || undefined}
        aria-invalid={erro ? true : undefined}
        aria-describedby={descricao(`${idCampo}-dica`, `${idCampo}-erro`, dica, erro)}
        className={classesDaCaixa(Boolean(erro), "py-2.5 leading-normal")}
        {...resto}
      />
      {erro && <Erro id={`${idCampo}-erro`}>{erro}</Erro>}
    </div>
  );
}

type PropsDoCampoSelecao = PropsComuns &
  Omit<SelectHTMLAttributes<HTMLSelectElement>, "className" | "required"> & { children: ReactNode };

export function CampoSelecao({ rotulo, dica, erro, obrigatorio, className = "", id, children, ...resto }: PropsDoCampoSelecao) {
  const gerado = useId();
  const idCampo = id ?? gerado;
  return (
    <div className={className}>
      <Rotulo para={idCampo} rotulo={rotulo} obrigatorio={obrigatorio} />
      {dica && <Dica id={`${idCampo}-dica`}>{dica}</Dica>}
      <select
        id={idCampo}
        aria-required={obrigatorio || undefined}
        aria-invalid={erro ? true : undefined}
        aria-describedby={descricao(`${idCampo}-dica`, `${idCampo}-erro`, dica, erro)}
        className={classesDaCaixa(Boolean(erro), "min-h-12 pr-9")}
        {...resto}
      >
        {children}
      </select>
      {erro && <Erro id={`${idCampo}-erro`}>{erro}</Erro>}
    </div>
  );
}

interface PropsDoGrupoDeOpcoes<T extends string> {
  rotulo: string;
  nome: string;
  opcoes: { valor: T; rotulo: string }[];
  valor: T | "";
  aoMudar: (valor: T) => void;
  erro?: string | null;
  obrigatorio?: boolean;
  className?: string;
}

/** Escolha única em botões lado a lado: mais rápida no celular do que uma lista suspensa. */
export function GrupoDeOpcoes<T extends string>({
  rotulo,
  nome,
  opcoes,
  valor,
  aoMudar,
  erro,
  obrigatorio,
  className = "",
}: PropsDoGrupoDeOpcoes<T>) {
  const id = useId();
  return (
    <fieldset
      className={className}
      aria-required={obrigatorio || undefined}
      aria-invalid={erro ? true : undefined}
      aria-describedby={erro ? `${id}-erro` : undefined}
    >
      <legend className="mb-1 block font-bold text-tinta-900">
        {rotulo}
        {obrigatorio && (
          <span className="text-perigo-700" aria-hidden="true">
            {" "}
            *
          </span>
        )}
      </legend>
      <div className="flex gap-2">
        {opcoes.map((opcao) => (
          <label
            key={opcao.valor}
            className={`flex min-h-12 min-w-0 flex-1 cursor-pointer items-center justify-center rounded-xl border-2 px-2 text-center font-bold transition-colors has-focus-visible:outline-3 has-focus-visible:outline-offset-2 has-focus-visible:outline-barro-600 ${
              valor === opcao.valor
                ? "border-mata-700 bg-mata-700 text-white"
                : `bg-white text-tinta-900 hover:bg-mata-50 ${erro ? "border-perigo-600" : "border-contorno"}`
            }`}
          >
            <input
              type="radio"
              name={nome}
              value={opcao.valor}
              checked={valor === opcao.valor}
              onChange={() => aoMudar(opcao.valor)}
              className="sr-only"
            />
            {opcao.rotulo}
          </label>
        ))}
      </div>
      {erro && <Erro id={`${id}-erro`}>{erro}</Erro>}
    </fieldset>
  );
}

interface PropsDoInterruptor {
  rotulo: string;
  dica?: string;
  marcado: boolean;
  aoMudar: (marcado: boolean) => void;
  desabilitado?: boolean;
}

/** Liga/desliga em linha inteira tocável. */
export function Interruptor({ rotulo, dica, marcado, aoMudar, desabilitado }: PropsDoInterruptor) {
  const id = useId();
  return (
    <label
      htmlFor={id}
      className="flex min-h-14 cursor-pointer items-center justify-between gap-4 py-2 has-disabled:cursor-not-allowed"
    >
      <span className="min-w-0">
        <span className="block font-bold text-tinta-900">{rotulo}</span>
        {dica && (
          <span id={`${id}-dica`} className="block text-tinta-500">
            {dica}
          </span>
        )}
      </span>
      <span className="relative inline-flex shrink-0 items-center">
        <input
          id={id}
          type="checkbox"
          role="switch"
          checked={marcado}
          disabled={desabilitado}
          onChange={(evento) => aoMudar(evento.target.checked)}
          aria-describedby={dica ? `${id}-dica` : undefined}
          className="peer sr-only"
        />
        <span
          aria-hidden="true"
          className="h-8 w-14 rounded-full border-2 border-contorno bg-white transition-colors peer-checked:border-mata-700 peer-checked:bg-mata-700 peer-focus-visible:outline-3 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-barro-600 peer-disabled:opacity-50"
        />
        <span
          aria-hidden="true"
          className="absolute left-1.5 size-5 rounded-full bg-contorno transition-transform peer-checked:translate-x-6 peer-checked:bg-white"
        />
      </span>
    </label>
  );
}

/** Caixa de marcação simples com rótulo ao lado. */
export function CaixaDeMarcacao({
  rotulo,
  marcado,
  aoMudar,
}: {
  rotulo: string;
  marcado: boolean;
  aoMudar: (marcado: boolean) => void;
}) {
  const id = useId();
  return (
    <label htmlFor={id} className="flex min-h-12 cursor-pointer items-center gap-3 font-semibold text-tinta-900">
      <input
        id={id}
        type="checkbox"
        checked={marcado}
        onChange={(evento) => aoMudar(evento.target.checked)}
        className="size-6 shrink-0 accent-mata-700"
      />
      {rotulo}
    </label>
  );
}
