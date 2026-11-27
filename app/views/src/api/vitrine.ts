// Cliente da API pública da vitrine de adoção (/api/public/animais/*).
//
// Assim como public.ts, NUNCA envia cookie de sessão (credentials: "omit") e NUNCA toca em /auth/*.
// Respostas públicas podem vir do cache da CDN e falhas aqui não interferem na área interna.

import type { AnimalPublico, PaginaVitrine, RespostaAnimalPublico } from "../types/contratos";
import { ErroApi } from "./http";

async function buscarPublico(caminho: string, sinal?: AbortSignal): Promise<Response> {
  try {
    return await fetch(caminho, {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "omit",
      signal: sinal,
    });
  } catch (causa) {
    if (causa instanceof DOMException && causa.name === "AbortError") throw causa;
    throw new ErroApi(0, null);
  }
}

async function lerJsonSeguro(resposta: Response): Promise<unknown> {
  const tipo = resposta.headers.get("content-type") ?? "";
  if (!tipo.includes("application/json")) return null;
  return resposta.json().catch(() => null);
}

/** Lista paginada dos cães publicados na vitrine de adoção. */
export async function listarVitrine(pagina = 1, sinal?: AbortSignal): Promise<PaginaVitrine> {
  const numeroPagina = Number.isFinite(pagina) && pagina >= 1 ? Math.trunc(pagina) : 1;
  const resposta = await buscarPublico(`/api/public/animais?pagina=${numeroPagina}`, sinal);
  const corpo = await lerJsonSeguro(resposta);
  if (!resposta.ok) {
    const erroCorpo = corpo && typeof corpo === "object" ? (corpo as Record<string, unknown>) : null;
    throw new ErroApi(resposta.status, erroCorpo);
  }
  return corpo as PaginaVitrine;
}

/**
 * Busca um cão publicado pelo slug da URL (/adote/:slug).
 * Regra B1: HTTP 404 devolve `null` sem lançar erro (a tela exibe "Este cão já encontrou um lar").
 */
export async function obterAnimalPublico(slug: string, sinal?: AbortSignal): Promise<AnimalPublico | null> {
  const resposta = await buscarPublico(`/api/public/animais/${encodeURIComponent(slug)}`, sinal);
  if (resposta.status === 404) return null;

  const corpo = await lerJsonSeguro(resposta);
  if (!resposta.ok) {
    const erroCorpo = corpo && typeof corpo === "object" ? (corpo as Record<string, unknown>) : null;
    throw new ErroApi(resposta.status, erroCorpo);
  }

  if (corpo && typeof corpo === "object" && "animal" in corpo) {
    return (corpo as RespostaAnimalPublico).animal ?? null;
  }
  return null;
}
