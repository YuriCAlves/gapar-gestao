// Regras de situação do animal que a interface precisa refletir (RN02, RN04, RN05, RN08).
// O servidor é quem impõe; aqui só evitamos oferecer o que ele recusaria.

import type { StatusAnimal } from "../types";

export const STATUS_ATIVOS: StatusAnimal[] = [
  "em acolhimento",
  "em tratamento",
  "disponível",
  "lar temporário",
];

export const TODOS_OS_STATUS: StatusAnimal[] = [...STATUS_ATIVOS, "adotado", "óbito"];

const ROTULOS: Record<StatusAnimal, string> = {
  "em acolhimento": "Em acolhimento",
  "em tratamento": "Em tratamento",
  "disponível": "Disponível para adoção",
  "lar temporário": "Lar temporário",
  "adotado": "Adotado",
  "óbito": "Óbito",
};

const ROTULOS_CURTOS: Record<StatusAnimal, string> = {
  "em acolhimento": "Acolhimento",
  "em tratamento": "Tratamento",
  "disponível": "Disponível",
  "lar temporário": "Lar temporário",
  "adotado": "Adotado",
  "óbito": "Óbito",
};

export function rotuloDoStatus(status: StatusAnimal): string {
  return ROTULOS[status] ?? status;
}

export function rotuloCurtoDoStatus(status: StatusAnimal): string {
  return ROTULOS_CURTOS[status] ?? status;
}

export function estaCongelado(status: StatusAnimal): boolean {
  return status === "adotado" || status === "óbito";
}

/** Situações que podem ser escolhidas na troca simples (sem "adotado", que exige o registro de adoção, e sem "óbito", que tem confirmação própria). */
export function statusDisponiveisParaTroca(atual: StatusAnimal): StatusAnimal[] {
  if (estaCongelado(atual)) return [];
  return STATUS_ATIVOS.filter((status) => status !== atual);
}

/** RN08: só recebe prescrição quem está sob cuidados diretos. */
export function podeReceberPrescricao(status: StatusAnimal): boolean {
  return status === "em acolhimento" || status === "em tratamento" || status === "lar temporário";
}

/** RF20: a adoção só é registrada a partir de "disponível" ou "lar temporário". */
export function podeSerAdotado(status: StatusAnimal): boolean {
  return status === "disponível" || status === "lar temporário";
}
