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

/**
 * GET /api/public/animais?pagina=N — 12 por página, mais recentes primeiro.
 * Cache: CDN 120 s + 60 s stale e navegador 60 s. Pior caso para um animal que saiu da vitrine
 * (RN17) continuar aparecendo: ~4 min na lista e ~3 min no detalhe. Só a FEATURE_VITRINE liga as rotas.
 */
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

// =============================================================================================
// CONTRATOS PREVISTOS DA FASE 2 (CP-03, CP-04, CP-05) — publicados antes do back-end para o
// trabalho em paralelo. Podem GANHAR campos até o handoff de cada CP; nunca perder ou renomear.
// Todas as rotas abaixo exigem login e ficam atrás da flag indicada (desligada -> 404).
// Datas: "AAAA-MM-DD"; data-hora: ISO 8601 UTC. Quantidades: number (até 2 casas decimais).
// =============================================================================================

// ---------------------------------------------------------------- CP-03 · Estoque (flag "estoque")

export type CategoriaInsumo =
  | "Vacina" | "Medicamento" | "Vermífugo" | "Antipulgas" | "Ração" | "Insumo Clínico" | "Limpeza";
export type UnidadeInsumo = "doses" | "comprimidos" | "ml" | "kg" | "unidades";
export type TipoMovimento =
  | "ENTRADA" | "SAIDA_USO" | "AJUSTE_MAIS" | "AJUSTE_MENOS" | "DESCARTE_VALIDADE" | "PERDA";

export interface ItemEstoque {
  id: number;
  nome: string;
  categoria: CategoriaInsumo;
  unidade: UnidadeInsumo;
  estoque_minimo: number;
  /** Soma dos saldos dos lotes NÃO vencidos. */
  saldo_total: number;
  abaixo_do_minimo: boolean;
  /** Validade mais próxima entre os lotes com saldo e não vencidos; null se não houver. */
  proxima_validade: string | null;
  is_active: boolean;
}

export interface LoteEstoque {
  id: number;
  item_id: number;
  codigo_lote: string;
  data_validade: string | null;
  saldo_atual: number;
  vencido: boolean;
  /** Dias até vencer (negativo = vencido há N dias); null sem validade. */
  vence_em_dias: number | null;
}

export interface MovimentoEstoque {
  id: number;
  batch_id: number;
  tipo: TipoMovimento;
  quantidade: number;
  saldo_apos: number;
  motivo: string;
  animal_id: number | null;
  /** Nome de quem registrou (equipe interna). */
  registrado_por: string | null;
  created_at: string;
}

/**
 * GET    /api/estoque/itens?categoria=&inativos=1   -> { itens: ItemEstoque[] }          (todas)
 * POST   /api/estoque/itens                         -> 201 { item }                       (Admin)
 *        { nome, categoria, unidade, estoque_minimo }
 * PATCH  /api/estoque/itens/:id                     -> { item }                           (Admin)
 *        { nome?, estoque_minimo?, is_active? }
 * GET    /api/estoque/itens/:id                     -> DetalheItemEstoque                 (todas)
 * POST   /api/estoque/itens/:id/lotes               -> 201 { lote, movimento }            (Admin)
 *        { codigo_lote, data_validade?, quantidade, motivo? }   (cria o lote com ENTRADA)
 *        409 se o código de lote já existir nesse item (use a rota de movimentos).
 * POST   /api/estoque/lotes/:id/movimentos          -> 201 { lote, movimento }            (Admin)
 *        { tipo: Exclude<TipoMovimento, "SAIDA_USO">, quantidade, motivo }  motivo obrigatório
 *        409 = saldo ficaria negativo (RN18). Movimentos nunca são editados nem apagados (RN19).
 * GET    /api/estoque/fefo?item_id=N&quantidade=Q   -> SugestaoFefo                       (todas)
 */
export interface DetalheItemEstoque {
  item: ItemEstoque;
  /** Ordem FEFO: validade mais próxima primeiro; sem validade por último; vencidos no fim. */
  lotes: LoteEstoque[];
  /** Últimos 50, mais recentes primeiro. */
  movimentos: MovimentoEstoque[];
}

export interface SugestaoFefo {
  /** Só lotes não vencidos com saldo > 0, em ordem FEFO. */
  lotes: LoteEstoque[];
  /** 1º lote FEFO com saldo suficiente para `quantidade`; null se nenhum tiver. */
  sugerido_id: number | null;
}

/**
 * Baixa de estoque ao registrar saúde (CP-03):
 * - POST /api/saude/vacinas/:animal_id  ganha { lote_id?: number, quantidade?: number (padrão 1) }.
 *   Com lote_id: saída SAIDA_USO na mesma transação. 422 lote vencido (RN20), 409 saldo (RN18),
 *   400 lote de outro tipo de item que não seja "Vacina".
 * - POST /api/saude/medicacao/baixa/:prescription_id ganha { lote_id?: number, quantidade?: number }.
 *   Opcional; mesmas regras.
 * - GET /api/hoje ganha, só para Administradora com a flag ligada:
 *   estoque: { acabando: ItemEstoque[], vencendo: LoteEstoque[] }  (vencendo = até 30 dias)
 */
export interface AlertasEstoqueHoje {
  acabando: ItemEstoque[];
  vencendo: (LoteEstoque & { item_nome: string })[];
}

// ---------------------------------------------------------------- CP-04 · Microchip (flag "microchip")

/**
 * A ficha interna do animal (to_dict) ganha `numero_microchip: string | null` (15 dígitos).
 * - POST /api/animais e PATCH /api/animais/:id aceitam `numero_microchip` (15 dígitos; vazio/null limpa).
 *   Preenchido -> is_microchipado vira true. 400 formato inválido.
 *   409 número já usado: { erro, codigo, mensagem, animal_id, animal_nome } (mostre link para a ficha).
 * - GET /api/animais/microchip/:numero -> 200 { animal: ResumoMicrochip } | 404  (leitor USB HID).
 * - O microchip NUNCA aparece na vitrine pública.
 */
export interface ResumoMicrochip {
  id: number;
  nome: string;
  status_operacional: string;
  foto_url: string | null;
  localizacao_baia: string | null;
}

export interface ConflitoMicrochip {
  erro: string;
  codigo: 409;
  mensagem: string;
  animal_id: number;
  animal_nome: string;
}

// ---------------------------------------------------------------- CP-05 · Isolamento (flag "isolamento")

export interface IsolamentoRegistro {
  id: number;
  animal_id: number;
  motivo: string;
  protocolo_cuidados: string | null;
  data_inicio: string;
  data_fim_prevista: string | null;
  /** Preenchido ao encerrar; null = isolamento aberto. */
  fim_real: string | null;
  observacoes_alta: string | null;
  aberto_por: string | null;
  encerrado_por: string | null;
  aberto: boolean;
  created_at: string;
}

/**
 * - GET  /api/animais/:id/isolamentos          -> { isolamentos: IsolamentoRegistro[] } (recentes 1º)
 * - POST /api/animais/:id/isolamentos          -> 201 { isolamento }              (todas as perfis)
 *        { motivo (≤200), protocolo_cuidados?, data_inicio? (padrão hoje), data_fim_prevista? }
 *        409 já existe isolamento aberto (RN22); 422 animal adotado/óbito (RN05) ou excluído.
 * - POST /api/isolamentos/:id/encerrar         -> { isolamento }                  (todas as perfis)
 *        { observacoes_alta? }  409 já encerrado.
 * - A ficha (to_dict) e cada item de GET /api/animais ganham:
 *        isolamento_aberto: { id, motivo, data_inicio, data_fim_prevista } | null
 * - GET /api/hoje ganha (flag ligada): isolamentos: (IsolamentoRegistro & { animal_nome: string })[]
 *   (só os abertos; prioridade no topo do painel).
 * - Animal com isolamento aberto sai da vitrine pública automaticamente (RN17 ampliada).
 * - Kanban: usa o PATCH /api/animais/:id/status já existente (mesmas transições; nunca "adotado").
 */
export interface IsolamentoAbertoResumo {
  id: number;
  motivo: string;
  data_inicio: string;
  data_fim_prevista: string | null;
}
