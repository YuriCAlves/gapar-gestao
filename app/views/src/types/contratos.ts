// Contratos da API pública e da Fase 0 (CP-01). Arquivo de propriedade do Claude Code:
// a tela consome estes tipos, mas não os altera. Mudança de contrato = pedido no handoff.

/** Módulos liberados por feature flag. Desconhecido ou ausente = desligado (fail-closed). */
export type FlagPublica =
  | "vitrine"
  | "estoque"
  | "microchip"
  | "isolamento"
  | "pos_adocao"
  | "termo_digital"
  | "candidaturas"
  | "carteira"
  | "mapa";

export const FLAGS_PUBLICAS: readonly FlagPublica[] = [
  "vitrine",
  "estoque",
  "microchip",
  "isolamento",
  "pos_adocao",
  "termo_digital",
  "candidaturas",
  "carteira",
  "mapa",
];

/** GET /api/public/config — sem login, com cache de CDN (60 s). */
export interface ConfigPublica {
  flags: Record<FlagPublica, boolean>;
  /** Chave pública do widget Cloudflare Turnstile; null enquanto não configurada. */
  turnstile_site_key: string | null;
  /** WhatsApp de adoção da ONG, só dígitos com DDI (ex.: "5541999990000"); null se não houver. */
  whatsapp_adocao: string | null;
}

/** Configuração usada até a resposta chegar ou quando a chamada falha: tudo desligado. */
export const CONFIG_PUBLICA_FECHADA: ConfigPublica = {
  flags: Object.fromEntries(FLAGS_PUBLICAS.map((f) => [f, false])) as Record<FlagPublica, boolean>,
  turnstile_site_key: null,
  whatsapp_adocao: null,
};

/**
 * Busca na lista sigilosa (D2) — POST /api/admin/nao-aptos/busca (só Administradora).
 * Corpo JSON com UM filtro: `q` (nome, parcial), `cpf` (11 dígitos) ou `telefone` (10–11 dígitos).
 * Dado pessoal NUNCA vai na URL: GET /api/admin/nao-aptos lista tudo e recusa (400) `?q`, `?cpf`
 * e `?telefone`. CPF/telefone incompletos ou inválidos, nenhum filtro ou mais de um -> 400.
 * Resposta: { sucesso, total, nao_aptos[] }, com `cpf` formatado (000.000.000-00).
 */
export type BuscaListaSigilosa = { q: string } | { cpf: string } | { telefone: string };

// ---------------------------------------------------------------------------------------------
// CP-02 · Vitrine pública (RN17) — CONTRATO PREVISTO, publicado antes do back-end para o trabalho
// em paralelo. Pode ganhar campos até o handoff do CP-02 (nunca perder); mudança será avisada.
// ---------------------------------------------------------------------------------------------

/** Animal como o visitante sem login vê. Nada de id, origem do resgate, baia ou saúde. */
export interface AnimalPublico {
  /** Identificador público da URL (/adote/:slug). Nunca é o id interno. */
  slug: string;
  nome: string;
  sexo: "Macho" | "Fêmea";
  porte: "Pequeno" | "Médio" | "Grande";
  idade_estimada: string | null;
  raca: string;
  pelagem: string | null;
  /** URL https absoluta, foto já comprimida (< 300 KB); null quando não houver foto. */
  foto_url: string | null;
  is_castrado: boolean;
  is_idoso: boolean;
  /** Texto escrito pela Administradora para o público (até 600 caracteres). */
  descricao_publica: string | null;
  /** true quando a ONG pausou as candidaturas deste animal (mostrar só o WhatsApp). */
  candidaturas_pausadas: boolean;
}

/** GET /api/public/animais?pagina=N — 12 por página, mais recentes primeiro, cache de CDN 5 min. */
export interface PaginaVitrine {
  animais: AnimalPublico[];
  pagina: number;
  por_pagina: number;
  total: number;
  tem_mais: boolean;
}

/**
 * GET /api/public/animais/:slug -> 200 { animal: AnimalPublico }.
 * 404 quando o animal não existe, não está publicado ou deixou de estar disponível (RN17):
 * a resposta é a mesma nos três casos, para não revelar nada. A tela mostra
 * "Este cão já encontrou um lar" com link para a vitrine.
 */
export interface RespostaAnimalPublico {
  animal: AnimalPublico;
}

/**
 * PATCH /api/animais/:id/vitrine (só Administradora)
 * Corpo: { publicar: boolean, descricao_publica?: string | null, pausar_candidaturas?: boolean }
 * 200 -> { animal: <ficha interna com os campos abaixo> }
 * 422 -> publicar=true com status diferente de "disponível" (use a `mensagem` do servidor).
 * Ao sair de "disponível" (ou ser excluído), o animal sai da vitrine sozinho (RN17).
 */
export interface CamposVitrineDaFicha {
  is_publicado: boolean;
  slug_publico: string | null;
  descricao_publica: string | null;
  pausar_candidaturas: boolean;
}
