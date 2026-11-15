import type { NovaAdocao, RespostaAdocao } from "../types";
import { ErroApi, requisitar } from "./http";

/**
 * Registro formal da adoção (RN04). É o único caminho para a situação "adotado";
 * depois dele a ficha fica congelada (RN05).
 */
export function registrarAdocao(animalId: number, dados: NovaAdocao): Promise<RespostaAdocao> {
  return requisitar<RespostaAdocao>(`/api/adocoes/${animalId}`, { metodo: "POST", json: dados });
}

/**
 * RN15: o servidor recusou a adoção por causa da lista sigilosa. A interface deve apenas
 * orientar a procurar a administradora, sem expor motivo nem dados.
 */
export function adocaoFoiBarrada(causa: unknown): boolean {
  return causa instanceof ErroApi && causa.status === 422 && causa.erro === "Adoção não autorizada";
}
