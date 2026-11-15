import type {
  NovaPrescricao,
  NovaVacina,
  NovoRegistroProntuario,
  Prescricao,
  RegistroProntuario,
  RespostaBaixa,
  Vacina,
} from "../types";
import { requisitar } from "./http";

export async function registrarVacina(animalId: number, dados: NovaVacina): Promise<Vacina> {
  const resposta = await requisitar<{ vacina: Vacina }>(`/api/saude/vacinas/${animalId}`, {
    metodo: "POST",
    json: dados,
  });
  return resposta.vacina;
}

export async function registrarProntuario(
  animalId: number,
  dados: NovoRegistroProntuario,
): Promise<RegistroProntuario> {
  const resposta = await requisitar<{ registro: RegistroProntuario }>(`/api/saude/prontuario/${animalId}`, {
    metodo: "POST",
    json: dados,
  });
  return resposta.registro;
}

/** Prescrições do animal já com as baixas de hoje (campo logs_hoje). */
export async function listarPrescricoes(animalId: number, sinal?: AbortSignal): Promise<Prescricao[]> {
  const resposta = await requisitar<{ prescricoes: Prescricao[] }>(`/api/saude/prescricoes/${animalId}`, {
    sinal,
  });
  return resposta.prescricoes;
}

export async function registrarPrescricao(animalId: number, dados: NovaPrescricao): Promise<Prescricao> {
  const resposta = await requisitar<{ prescricao: Prescricao }>(`/api/saude/prescricoes/${animalId}`, {
    metodo: "POST",
    json: dados,
  });
  return resposta.prescricao;
}

/**
 * Baixa de uma dose do dia (RF16). Se a dose já tinha sido baixada por outra pessoa, o servidor
 * responde com ja_baixado: true, o que também é sucesso.
 */
export function darBaixa(prescricaoId: number, horarioPrevisto: string): Promise<RespostaBaixa> {
  return requisitar<RespostaBaixa>(`/api/saude/medicacao/baixa/${prescricaoId}`, {
    metodo: "POST",
    json: { horario_previsto: horarioPrevisto },
  });
}

/** Arquivo de calendário com os lembretes de saúde do animal (RF18). */
export function enderecoDosLembretes(animalId: number): string {
  return `/api/saude/lembretes/${animalId}.ics`;
}
