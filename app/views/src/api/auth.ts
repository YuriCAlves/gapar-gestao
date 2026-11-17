import type { OpcoesDeEntrada, RespostaLogin, SituacaoSessao, Usuaria } from "../types";
import { requisitar } from "./http";

/** Endereço que inicia a entrada com Google. Deve ser aberto por navegação, não por fetch. */
export const URL_ENTRAR_COM_GOOGLE = "/auth/google";

export async function consultarSessao(sinal?: AbortSignal): Promise<Usuaria | null> {
  const situacao = await requisitar<SituacaoSessao>("/auth/status", { sinal, ignorarSessao: true });
  return situacao.autenticado && situacao.usuario ? situacao.usuario : null;
}

export async function consultarOpcoesDeEntrada(sinal?: AbortSignal): Promise<OpcoesDeEntrada> {
  const dados = await requisitar<Partial<OpcoesDeEntrada>>("/auth/login", { sinal, ignorarSessao: true });
  return {
    dev_login: Boolean(dados.dev_login),
    google_configurado: Boolean(dados.google_configurado),
  };
}

/** Entrada de desenvolvimento. Sem e-mail, entra como a primeira Administradora da lista. */
export async function entrarEmModoDeTeste(email?: string): Promise<Usuaria> {
  const resposta = await requisitar<RespostaLogin>("/auth/dev-login", {
    metodo: "POST",
    json: email ? { email } : {},
    ignorarSessao: true,
  });
  return resposta.usuario;
}

export async function encerrarSessao(): Promise<void> {
  await requisitar<unknown>("/auth/logout", { metodo: "POST", ignorarSessao: true });
}
