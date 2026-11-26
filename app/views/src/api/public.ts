// Cliente da API pública (/api/public/*). Arquivo de propriedade do Claude Code.
//
// Diferente de http.ts: NUNCA envia o cookie de sessão (credentials: "omit"). Assim a resposta é a
// mesma para qualquer visitante, pode vir do cache da CDN e nada da sessão interna chega à vitrine.
// Um erro aqui também nunca derruba a sessão do app interno.

import { CONFIG_PUBLICA_FECHADA, FLAGS_PUBLICAS, type ConfigPublica, type FlagPublica } from "../types/contratos";
import { ErroApi } from "./http";

async function requisitarPublico<T>(caminho: string, sinal?: AbortSignal): Promise<T> {
  let resposta: Response;
  try {
    resposta = await fetch(caminho, {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "omit",
      signal: sinal,
    });
  } catch (causa) {
    if (causa instanceof DOMException && causa.name === "AbortError") throw causa;
    throw new ErroApi(0, null);
  }
  const corpo = (resposta.headers.get("content-type") ?? "").includes("application/json")
    ? await resposta.json().catch(() => null)
    : null;
  if (!resposta.ok) throw new ErroApi(resposta.status, corpo);
  return corpo as T;
}

/** Configuração pública. Em qualquer falha devolve tudo desligado (fail-closed), sem lançar erro. */
export async function obterConfigPublica(sinal?: AbortSignal): Promise<ConfigPublica> {
  try {
    const dados = await requisitarPublico<Partial<ConfigPublica>>("/api/public/config", sinal);
    const flags = { ...CONFIG_PUBLICA_FECHADA.flags };
    for (const nome of FLAGS_PUBLICAS) flags[nome as FlagPublica] = dados.flags?.[nome] === true;
    return {
      flags,
      turnstile_site_key: typeof dados.turnstile_site_key === "string" ? dados.turnstile_site_key : null,
      whatsapp_adocao: typeof dados.whatsapp_adocao === "string" ? dados.whatsapp_adocao : null,
    };
  } catch (causa) {
    if (causa instanceof DOMException && causa.name === "AbortError") throw causa;
    return CONFIG_PUBLICA_FECHADA;
  }
}
