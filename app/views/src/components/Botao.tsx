import { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export type VarianteDoBotao = "primario" | "secundario" | "suave" | "perigo" | "perigoContorno" | "fantasma";
export type TamanhoDoBotao = "normal" | "grande" | "compacto";

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-xl font-bold leading-tight text-center " +
  "transition-colors select-none disabled:cursor-not-allowed aria-disabled:cursor-not-allowed";

const VARIANTES: Record<VarianteDoBotao, string> = {
  primario:
    "bg-mata-700 text-white hover:bg-mata-800 active:bg-mata-900 " +
    "disabled:bg-creme-200 disabled:text-tinta-500 aria-disabled:bg-creme-200 aria-disabled:text-tinta-500",
  secundario:
    "border-2 border-mata-700 bg-white text-mata-800 hover:bg-mata-50 active:bg-mata-100 " +
    "disabled:border-creme-300 disabled:bg-creme-100 disabled:text-tinta-500",
  suave:
    "bg-mata-50 text-mata-900 hover:bg-mata-100 active:bg-mata-200 " +
    "disabled:bg-creme-100 disabled:text-tinta-500",
  perigo:
    "bg-perigo-600 text-white hover:bg-perigo-700 active:bg-perigo-900 " +
    "disabled:bg-creme-200 disabled:text-tinta-500",
  perigoContorno:
    "border-2 border-perigo-600 bg-white text-perigo-700 hover:bg-perigo-50 active:bg-perigo-100 " +
    "disabled:border-creme-300 disabled:bg-creme-100 disabled:text-tinta-500",
  fantasma: "text-mata-800 hover:bg-mata-50 active:bg-mata-100 disabled:text-tinta-500",
};

const TAMANHOS: Record<TamanhoDoBotao, string> = {
  compacto: "min-h-11 px-3.5 text-base",
  normal: "min-h-12 px-5 text-base",
  grande: "min-h-14 px-6 text-lg",
};

/** Classes de botão, para usar também em links (<Link>, <a>). */
export function classesDoBotao(
  variante: VarianteDoBotao = "primario",
  tamanho: TamanhoDoBotao = "normal",
  extra = "",
): string {
  return `${BASE} ${VARIANTES[variante]} ${TAMANHOS[tamanho]} ${extra}`.trim();
}

interface PropsDoBotao extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: VarianteDoBotao;
  tamanho?: TamanhoDoBotao;
  /** Mostra o indicador de espera e impede novos toques. */
  ocupado?: boolean;
  icone?: ReactNode;
  larguraTotal?: boolean;
}

export const Botao = forwardRef<HTMLButtonElement, PropsDoBotao>(function Botao(
  { variante = "primario", tamanho = "normal", ocupado = false, icone, larguraTotal, className = "", children, disabled, type, ...resto },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type ?? "button"}
      disabled={disabled || ocupado}
      aria-busy={ocupado || undefined}
      className={classesDoBotao(variante, tamanho, `${larguraTotal ? "w-full" : ""} ${className}`)}
      {...resto}
    >
      {ocupado ? <Girando /> : icone}
      <span className="min-w-0">{children}</span>
    </button>
  );
});

export function Girando({ tamanho = 20 }: { tamanho?: number }) {
  return (
    <svg
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      className="shrink-0 animate-spin"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeOpacity="0.3" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}
