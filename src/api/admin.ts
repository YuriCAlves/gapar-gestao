import type {
  NovaPessoaNaoApta,
  PaginaAuditoria,
  Perfil,
  PessoaAutorizada,
  PessoaNaoApta,
  RegistroAuditoria,
} from "../types";
import { requisitar } from "./http";

// Todas estas rotas são exclusivas da Administradora (RF03, RF04, RF22, RF24).

export async function listarPessoasAutorizadas(sinal?: AbortSignal): Promise<PessoaAutorizada[]> {
  const resposta = await requisitar<{ whitelist: PessoaAutorizada[] }>("/api/admin/whitelist", { sinal });
  return resposta.whitelist;
}

export async function autorizarPessoa(email: string, perfil: Perfil): Promise<PessoaAutorizada> {
  const resposta = await requisitar<{ usuario: PessoaAutorizada }>("/api/admin/whitelist", {
    metodo: "POST",
    json: { email, role: perfil },
  });
  return resposta.usuario;
}

/** Ativa ou desativa o acesso. A desativação vale já na próxima ação da pessoa (RN14). */
export async function definirAcesso(id: number, ativo: boolean): Promise<PessoaAutorizada> {
  const resposta = await requisitar<{ usuario: PessoaAutorizada }>(`/api/admin/whitelist/${id}/status`, {
    metodo: "PATCH",
    json: { is_active: ativo },
  });
  return resposta.usuario;
}

export async function listarNaoAptos(sinal?: AbortSignal): Promise<PessoaNaoApta[]> {
  const resposta = await requisitar<{ nao_aptos: PessoaNaoApta[] }>("/api/admin/nao-aptos", { sinal });
  return resposta.nao_aptos;
}

export async function cadastrarNaoApto(dados: NovaPessoaNaoApta): Promise<PessoaNaoApta> {
  const resposta = await requisitar<{ nao_apto: PessoaNaoApta }>("/api/admin/nao-aptos", {
    metodo: "POST",
    json: dados,
  });
  return resposta.nao_apto;
}

interface RespostaAuditoria {
  logs?: RegistroAuditoria[];
  total?: number;
  total_registros?: number;
  pagina_atual?: number;
  total_paginas?: number;
}

export const AUDITORIA_POR_PAGINA = 30;

/**
 * Histórico de ações. Funciona com o servidor paginando (pagina_atual / total_paginas)
 * ou devolvendo tudo de uma vez: sem esses campos, a resposta é tratada como página única.
 */
export function normalizarAuditoria(resposta: RespostaAuditoria, paginaPedida: number): PaginaAuditoria {
  const registros = Array.isArray(resposta.logs) ? resposta.logs : [];
  const temPaginacao =
    typeof resposta.pagina_atual === "number" && typeof resposta.total_paginas === "number";
  const total =
    typeof resposta.total_registros === "number"
      ? resposta.total_registros
      : temPaginacao && typeof resposta.total === "number"
        ? resposta.total
        : null;
  return {
    registros,
    paginaAtual: temPaginacao ? (resposta.pagina_atual as number) : paginaPedida,
    totalPaginas: temPaginacao ? Math.max(resposta.total_paginas as number, 1) : 1,
    total,
  };
}

export interface FiltrosAuditoria {
  acao?: string;
  entidade?: string;
  email?: string;
  data_inicio?: string;
  data_fim?: string;
}

export async function listarAuditoria(
  pagina: number,
  filtros: FiltrosAuditoria = {},
  sinal?: AbortSignal,
): Promise<PaginaAuditoria> {
  const resposta = await requisitar<RespostaAuditoria>("/api/admin/auditoria", {
    sinal,
    consulta: { page: pagina, per_page: AUDITORIA_POR_PAGINA, ...filtros },
  });
  return normalizarAuditoria(resposta, pagina);
}

/** Tipos de ação e de cadastro existentes no histórico, para montar os filtros. */
export async function listarTiposDeAuditoria(sinal?: AbortSignal): Promise<{ acoes: string[]; entidades: string[] }> {
  const resposta = await requisitar<{ acoes?: string[]; entidades?: string[] }>("/api/admin/auditoria/acoes", { sinal });
  return { acoes: resposta.acoes ?? [], entidades: resposta.entidades ?? [] };
}

export async function alterarPerfil(id: number, perfil: Perfil): Promise<PessoaAutorizada> {
  const resposta = await requisitar<{ usuario: PessoaAutorizada }>(`/api/admin/whitelist/${id}`, {
    metodo: "PATCH",
    json: { role: perfil },
  });
  return resposta.usuario;
}
