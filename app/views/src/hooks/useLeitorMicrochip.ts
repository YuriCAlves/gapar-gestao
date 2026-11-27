// Detecção de leitores de microchip USB HID (emulação de teclado).
// Leitores HID disparam 15 dígitos numéricos seguidos de "Enter" em rajada rápida (< 100 ms/tecla),
// permitindo diferenciar leitura automática de digitação humana e disparar busca sem debounce.

import { useMemo, useRef } from "react";
import { validarMicrochip } from "../utils/microchip";

/** Intervalo padrão (ms) entre teclas consecutivas para caracterizar rajada USB HID. */
export const LIMITE_MS_PADRAO = 100;

export interface OpcoesLeitorMicrochip {
  /** Chamado imediatamente quando uma leitura HID válida de 15 dígitos + Enter é concluída. */
  aoLer: (codigo: string) => void;
  /** Intervalo máximo em milissegundos entre teclas consecutivas da rajada (padrão: 100 ms). */
  limiteMs?: number;
}

export interface DetectorLeitorMicrochip {
  /**
   * Processa uma tecla recebida (`event.key`).
   * Retorna `true` somente quando `"Enter"` concluir uma rajada válida de 15 dígitos.
   */
  registrarTecla: (key: string, agora?: number) => boolean;
  /** Limpa o buffer acumulado e o registro de tempo da última tecla. */
  limpar: () => void;
}

/**
 * Cria a máquina de detecção pura para leitores USB HID (sem dependência de DOM/React),
 * acumulando dígitos dentro da janela `limiteMs` e disparando `aoLer` no `"Enter"`.
 */
export function criarDetectorLeitorMicrochip({
  limiteMs = LIMITE_MS_PADRAO,
  aoLer,
}: OpcoesLeitorMicrochip): DetectorLeitorMicrochip {
  let buffer = "";
  let ultimaTecla: number | null = null;

  const limpar = (): void => {
    buffer = "";
    ultimaTecla = null;
  };

  const registrarTecla = (key: string, agora: number = Date.now()): boolean => {
    if (/^\d$/.test(key)) {
      if (ultimaTecla !== null && agora - ultimaTecla <= limiteMs) {
        buffer += key;
      } else {
        buffer = key;
      }
      ultimaTecla = agora;
      return false;
    }

    if (key === "Enter") {
      const dentroDaJanela = ultimaTecla !== null && agora - ultimaTecla <= limiteMs;
      const codigo = buffer;
      limpar();

      if (dentroDaJanela && validarMicrochip(codigo)) {
        aoLer(codigo);
        return true;
      }
      return false;
    }

    // Qualquer tecla não-numérica (letras, espaços, pontuação, Backspace, etc.) quebra a rajada.
    limpar();
    return false;
  };

  return { registrarTecla, limpar };
}

/**
 * Hook React para detectar rajadas de leitor de microchip USB HID sem depender de debounce.
 * Mantém a referência mais recente de `aoLer` sem perder o buffer entre renderizações.
 */
export function useLeitorMicrochip({
  aoLer,
  limiteMs = LIMITE_MS_PADRAO,
}: OpcoesLeitorMicrochip): DetectorLeitorMicrochip {
  const aoLerRef = useRef(aoLer);
  aoLerRef.current = aoLer;

  return useMemo(
    () =>
      criarDetectorLeitorMicrochip({
        limiteMs,
        aoLer: (codigo) => aoLerRef.current(codigo),
      }),
    [limiteMs],
  );
}
