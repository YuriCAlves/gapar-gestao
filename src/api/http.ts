// Cliente HTTP único do app. Toda conversa com o servidor passa por aqui:
// - mesma origem, com o cookie de sessão;
// - erros sempre viram ErroApi, com uma mensagem pronta para mostrar na tela;
// - perda de sessão (401) ou acesso desativado (403 "Acesso revogado") avisam o app inteiro.

import { mensagemDeErro } from "../utils/mensagens";

export type MotivoSessaoEncerrada = "expirada" | "revogada";

interface CorpoDeErro {
  erro?: string;
  mensagem?: string;
  codigo?: number;
  [chave: string]: unknown;
}

export class ErroApi extends Error {
  /** Código HTTP da resposta; 0 quando não houve resposta (sem internet, servidor fora do ar). */
  readonly status: number;
  /** Título curto do erro, como enviado pelo servidor (ex.: "Adoção não autorizada"). */
  readonly erro: string;
  readonly corpo: CorpoDeErro | null;

  constructor(status: number, corpo: CorpoDeErro | null) {
    const erro = corpo?.erro ?? "";
    super(mensagemDeErro(status, erro, corpo?.mensagem));
    this.name = "ErroApi";
    this.status = status;
    this.erro = erro;
    this.corpo = corpo;
  }
}

type OuvinteSessao = (motivo: MotivoSessaoEncerrada) => void;
let aoEncerrarSessao: OuvinteSessao | null = null;

/** Registrado pelo AuthContext: chamado quando o servidor diz que a sessão não vale mais. */
export function definirOuvinteDeSessao(ouvinte: OuvinteSessao | null): void {
  aoEncerrarSessao = ouvinte;
}

export interface OpcoesDeRequisicao {
  metodo?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  /** Enviado como JSON. */
  json?: unknown;
  /** Enviado como multipart/form-data (fotos). */
  formulario?: FormData;
  consulta?: Record<string, string | number | undefined | null>;
  sinal?: AbortSignal;
  /** Quando true, um 401 não derruba a sessão do app (usado nas rotas de login). */
  ignorarSessao?: boolean;
}

function montarUrl(caminho: string, consulta?: OpcoesDeRequisicao["consulta"]): string {
  if (!consulta) return caminho;
  const parametros = new URLSearchParams();
  for (const [chave, valor] of Object.entries(consulta)) {
    if (valor !== undefined && valor !== null && valor !== "") parametros.set(chave, String(valor));
  }
  const texto = parametros.toString();
  return texto ? `${caminho}?${texto}` : caminho;
}

async function lerCorpo(resposta: Response): Promise<unknown> {
  const tipo = resposta.headers.get("content-type") ?? "";
  if (!tipo.includes("application/json")) return null;
  try {
    return await resposta.json();
  } catch {
    return null;
  }
}

export async function requisitar<T>(caminho: string, opcoes: OpcoesDeRequisicao = {}): Promise<T> {
  const cabecalhos: Record<string, string> = { Accept: "application/json" };
  let corpo: BodyInit | undefined;
  if (opcoes.formulario) {
    corpo = opcoes.formulario; // o navegador define o Content-Type com o separador correto
  } else if (opcoes.json !== undefined) {
    cabecalhos["Content-Type"] = "application/json";
    corpo = JSON.stringify(opcoes.json);
  }

  let resposta: Response;
  try {
    resposta = await fetch(montarUrl(caminho, opcoes.consulta), {
      method: opcoes.metodo ?? "GET",
      headers: cabecalhos,
      body: corpo,
      credentials: "same-origin",
      signal: opcoes.sinal,
    });
  } catch (causa) {
    if (causa instanceof DOMException && causa.name === "AbortError") throw causa;
    throw new ErroApi(0, null);
  }

  const dados = await lerCorpo(resposta);

  if (!resposta.ok) {
    const corpoDeErro = dados && typeof dados === "object" ? (dados as CorpoDeErro) : null;
    const erro = new ErroApi(resposta.status, corpoDeErro);
    if (!opcoes.ignorarSessao) {
      if (resposta.status === 401) aoEncerrarSessao?.("expirada");
      else if (resposta.status === 403 && erro.erro === "Acesso revogado") aoEncerrarSessao?.("revogada");
    }
    throw erro;
  }

  return dados as T;
}

/** True quando a requisição foi cancelada de propósito (troca de filtro, saída da tela). */
export function foiCancelada(causa: unknown): boolean {
  return causa instanceof DOMException && causa.name === "AbortError";
}

/** Texto seguro para mostrar à usuária a partir de qualquer erro capturado. */
export function textoDoErro(causa: unknown): string {
  if (causa instanceof ErroApi) return causa.message;
  return "Algo deu errado. Tente de novo.";
}
