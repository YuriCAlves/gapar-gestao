import { useCallback, useEffect, useRef, useState } from "react";
import { foiCancelada, textoDoErro } from "../api/http";

interface EstadoDoCarregamento<T> {
  dados: T | null;
  carregando: boolean;
  erro: string | null;
  recarregar: () => void;
  /** Troca os dados na tela sem ir ao servidor (atualização imediata). */
  definirDados: (atualizar: (atual: T | null) => T | null) => void;
}

/**
 * Busca dados ao abrir a tela e sempre que as dependências mudarem, cancelando a busca
 * anterior. Erros viram texto pronto para a tela.
 */
export function useCarregar<T>(
  buscar: (sinal: AbortSignal) => Promise<T>,
  dependencias: readonly unknown[],
): EstadoDoCarregamento<T> {
  const [dados, setDados] = useState<T | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [versao, setVersao] = useState(0);
  const buscarRef = useRef(buscar);
  buscarRef.current = buscar;

  useEffect(() => {
    const controle = new AbortController();
    setCarregando(true);
    setErro(null);
    buscarRef
      .current(controle.signal)
      .then((resultado) => {
        setDados(resultado);
        setCarregando(false);
      })
      .catch((causa: unknown) => {
        if (foiCancelada(causa)) return;
        setErro(textoDoErro(causa));
        setCarregando(false);
      });
    return () => controle.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...dependencias, versao]);

  const recarregar = useCallback(() => setVersao((v) => v + 1), []);
  const definirDados = useCallback((atualizar: (atual: T | null) => T | null) => setDados(atualizar), []);

  return { dados, carregando, erro, recarregar, definirDados };
}
