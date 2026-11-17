import type {
  Animal,
  DadosAnimal,
  FichaAnimal,
  FiltrosAnimais,
  PaginaAnimais,
  RespostaAnimal,
  StatusAnimal,
} from "../types";
import { requisitar } from "./http";

export const ANIMAIS_POR_PAGINA = 12;

export function listarAnimais(
  filtros: FiltrosAnimais,
  pagina: number,
  sinal?: AbortSignal,
): Promise<PaginaAnimais> {
  return requisitar<PaginaAnimais>("/api/animais", {
    sinal,
    consulta: {
      page: pagina,
      per_page: ANIMAIS_POR_PAGINA,
      q: filtros.q.trim(),
      status: filtros.status,
      porte: filtros.porte,
      sexo: filtros.sexo,
      castrado: filtros.castrado,
      idoso: filtros.idoso,
      cuidados_especiais: filtros.cuidados,
    },
  });
}

export function buscarFicha(id: number, sinal?: AbortSignal): Promise<FichaAnimal> {
  return requisitar<FichaAnimal>(`/api/animais/${id}`, { sinal });
}

/**
 * Cadastro de resgate. Vai como formulário para levar a foto junto; campos vazios não são
 * enviados. O servidor define a situação inicial e a data de entrada (RN01).
 */
export async function cadastrarAnimal(dados: DadosAnimal, foto: File | null): Promise<Animal> {
  const formulario = new FormData();
  for (const [campo, valor] of Object.entries(dados)) {
    if (valor === null || valor === "") continue;
    formulario.append(campo, typeof valor === "boolean" ? (valor ? "true" : "false") : String(valor));
  }
  if (foto) formulario.append("foto", foto, foto.name);
  const resposta = await requisitar<RespostaAnimal>("/api/animais", { metodo: "POST", formulario });
  return resposta.animal;
}

export async function atualizarAnimal(id: number, dados: DadosAnimal): Promise<Animal> {
  const resposta = await requisitar<RespostaAnimal>(`/api/animais/${id}`, {
    metodo: "PUT",
    // A raça é obrigatória no banco: quando fica em branco, volta para o valor padrão.
    json: { ...dados, raca: dados.raca || "Sem Raça Definida (SRD)" },
  });
  return resposta.animal;
}

export async function alterarStatus(id: number, status: StatusAnimal): Promise<Animal> {
  const resposta = await requisitar<RespostaAnimal>(`/api/animais/${id}/status`, {
    metodo: "PATCH",
    json: { status_operacional: status },
  });
  return resposta.animal;
}

export async function enviarFoto(id: number, foto: File): Promise<string> {
  const formulario = new FormData();
  formulario.append("foto", foto, foto.name);
  const resposta = await requisitar<{ foto_url: string }>(`/api/animais/${id}/foto`, {
    metodo: "POST",
    formulario,
  });
  return resposta.foto_url;
}

/** Exclusiva da Administradora. O cadastro sai das listas, mas não é apagado do banco (RN03). */
export async function excluirAnimal(id: number): Promise<void> {
  await requisitar<unknown>(`/api/animais/${id}`, { metodo: "DELETE" });
}
