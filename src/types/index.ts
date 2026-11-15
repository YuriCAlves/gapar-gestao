// Tipos que espelham o contrato da API Flask (métodos to_dict em app/models e respostas das rotas).

export type Perfil = "Administradora" | "Voluntaria";

export interface Usuaria {
  id: number;
  email: string;
  name: string | null;
  role: Perfil;
  is_active: boolean;
  created_at?: string | null;
}

export interface SituacaoSessao {
  autenticado: boolean;
  usuario?: Usuaria;
}

export interface OpcoesDeEntrada {
  dev_login: boolean;
  google_configurado: boolean;
}

export interface RespostaLogin {
  sucesso: boolean;
  mensagem?: string;
  usuario: Usuaria;
}

// ---------------------------------------------------------------------------
// Animais
// ---------------------------------------------------------------------------

export type StatusAnimal =
  | "em acolhimento"
  | "em tratamento"
  | "disponível"
  | "lar temporário"
  | "adotado"
  | "óbito";

export type Sexo = "Macho" | "Fêmea";
export type Porte = "Pequeno" | "Médio" | "Grande";

export interface Animal {
  id: number;
  nome: string;
  idade_estimada: string | null;
  sexo: Sexo;
  raca: string;
  porte: Porte;
  pelagem: string | null;
  peso_kg: number | null;
  foto_url: string | null;
  local_resgate: string | null;
  data_entrada: string | null;
  motivo_resgate: string | null;
  is_castrado: boolean;
  is_microchipado: boolean;
  is_idoso: boolean;
  cuidados_especiais: string | null;
  localizacao_baia: string | null;
  codigo_identificador: string | null;
  status_operacional: StatusAnimal;
  congelado: boolean;
  created_at: string | null;
}

export interface FiltrosAnimais {
  q: string;
  status: StatusAnimal | "";
  porte: Porte | "";
  sexo: Sexo | "";
  castrado: "" | "sim" | "nao";
  idoso: "" | "sim" | "nao";
  cuidados: "" | "sim" | "nao";
}

export interface PaginaAnimais {
  pagina_atual: number;
  por_pagina: number;
  total_registros: number;
  total_paginas: number;
  animais: Animal[];
}

/** Campos editáveis do cadastro (RF05, RF07, RF08). */
export interface DadosAnimal {
  nome: string;
  sexo: Sexo;
  porte: Porte;
  idade_estimada: string | null;
  raca: string | null;
  pelagem: string | null;
  peso_kg: number | null;
  local_resgate: string | null;
  motivo_resgate: string | null;
  is_castrado: boolean;
  is_microchipado: boolean;
  is_idoso: boolean;
  cuidados_especiais: string | null;
  localizacao_baia: string | null;
  codigo_identificador: string | null;
}

export interface RespostaAnimal {
  sucesso: boolean;
  mensagem?: string;
  animal: Animal;
}

// ---------------------------------------------------------------------------
// Saúde
// ---------------------------------------------------------------------------

export interface Vacina {
  id: number;
  animal_id: number;
  nome_vacina: string;
  lote: string | null;
  data_aplicacao: string | null;
  data_reforco: string | null;
  observacoes: string | null;
  aplicado_por_user_id: number | null;
  reforco_pendente?: boolean;
  reforco_atrasado?: boolean;
}

export interface NovaVacina {
  nome_vacina: string;
  lote?: string;
  data_aplicacao: string;
  data_reforco?: string;
  observacoes?: string;
}

export interface RegistroProntuario {
  id: number;
  animal_id: number;
  tipo_evento: string;
  data_evento: string | null;
  veterinario_responsavel: string | null;
  clinica: string | null;
  diagnostico: string;
  procedimentos_realizados: string | null;
  cadastrado_por_user_id: number | null;
}

export interface NovoRegistroProntuario {
  tipo_evento: string;
  data_evento: string;
  diagnostico: string;
  veterinario_responsavel?: string;
  clinica?: string;
  procedimentos_realizados?: string;
}

export interface BaixaMedicacao {
  id: number;
  prescription_id: number;
  user_id: number | null;
  data_aplicacao: string | null;
  horario_previsto: string | null;
  horario_aplicado: string;
  observacoes: string | null;
  created_at: string;
}

export interface Prescricao {
  id: number;
  animal_id: number;
  nome_medicamento: string;
  dosagem: string;
  /** Horários "HH:MM" separados por vírgula. */
  horarios: string;
  data_inicio: string | null;
  data_fim: string | null;
  instrucoes: string | null;
  prescrito_por_user_id: number | null;
  is_active: boolean;
  google_event_id: string | null;
  /** Presente apenas em GET /api/saude/prescricoes/<id>. */
  logs_hoje?: BaixaMedicacao[];
}

export interface NovaPrescricao {
  nome_medicamento: string;
  dosagem: string;
  horarios: string;
  data_inicio: string;
  data_fim: string;
  instrucoes?: string;
}

export interface RespostaBaixa {
  sucesso: boolean;
  mensagem?: string;
  ja_baixado?: boolean;
  log: BaixaMedicacao;
}

// ---------------------------------------------------------------------------
// Adoção
// ---------------------------------------------------------------------------

export interface Adocao {
  id: number;
  animal_id: number;
  adotante_nome: string;
  adotante_telefone: string;
  adotante_cpf: string | null;
  adotante_endereco: string | null;
  data_adocao: string | null;
  termo_assinado: boolean;
  termo_fisico_assinado: boolean;
  observacoes: string | null;
  cadastrado_por_user_id: number | null;
  created_at: string;
}

export interface NovaAdocao {
  adotante_nome: string;
  adotante_telefone: string;
  data_adocao: string;
  adotante_cpf?: string;
  adotante_endereco?: string;
  termo_fisico_assinado?: boolean;
  observacoes?: string;
}

export interface RespostaAdocao {
  sucesso: boolean;
  mensagem?: string;
  adocao: Adocao;
  animal: Animal;
}

export interface FichaAnimal {
  animal: Animal;
  vacinas: Vacina[];
  prescricoes: Prescricao[];
  prontuarios: RegistroProntuario[];
  adocao: Adocao | null;
  congelado: boolean;
}

// ---------------------------------------------------------------------------
// Painel Hoje
// ---------------------------------------------------------------------------

export interface MedicacaoDoDia {
  prescricao_id: number;
  animal_id: number;
  animal_nome: string;
  localizacao_baia: string;
  medicamento: string;
  dosagem: string;
  horario_previsto: string;
  horario_aplicado: string | null;
  aplicado: boolean;
  instrucoes: string;
  atrasada?: boolean;
  animal_foto_url?: string | null;
}

export interface VacinaDoDia {
  vacina_id: number;
  animal_id: number;
  animal_nome: string;
  localizacao_baia: string;
  nome_vacina: string;
  data_reforco: string | null;
  atrasada: boolean;
  animal_foto_url?: string | null;
}

export interface PainelHoje {
  data_referencia: string;
  hora_referencia?: string;
  kpis: {
    total_acolhidos: number;
    em_tratamento: number;
    disponiveis_adocao: number;
    total_medicacoes_pendentes: number;
    total_vacinas_pendentes: number;
  };
  medicacoes_hoje: MedicacaoDoDia[];
  vacinas_hoje: VacinaDoDia[];
}

// ---------------------------------------------------------------------------
// Administração
// ---------------------------------------------------------------------------

export interface PessoaAutorizada {
  id: number;
  email: string;
  role: Perfil;
  is_active: boolean;
  created_at: string | null;
  is_admin_inicial?: boolean;
  is_voce?: boolean;
}

export interface PessoaNaoApta {
  id: number;
  nome: string;
  cpf: string | null;
  telefone: string | null;
  motivo_impedimento: string;
  created_at: string;
}

export interface NovaPessoaNaoApta {
  nome: string;
  motivo_impedimento: string;
  cpf?: string;
  telefone?: string;
}

export interface RegistroAuditoria {
  id: number;
  user_id: number | null;
  user_email: string | null;
  acao: string;
  entidade: string;
  entidade_id: number | null;
  detalhes: string | null;
  created_at: string;
}

/** Página do histórico de ações, já normalizada (o servidor pode ou não paginar). */
export interface PaginaAuditoria {
  registros: RegistroAuditoria[];
  paginaAtual: number;
  totalPaginas: number;
  /** Total informado pelo servidor, quando houver. */
  total: number | null;
}
