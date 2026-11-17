// Traduz as respostas de erro do servidor para um português sem termos técnicos (RNF13).
// O servidor manda textos com referências internas ("(RN05)", "Whitelist", "endpoint");
// aqui elas são retiradas ou trocadas antes de chegar à tela.

const NOMES_DE_CAMPOS: Record<string, string> = {
  peso_kg: "peso",
  data_aplicacao: "data da aplicação",
  data_reforco: "data do reforço",
  data_evento: "data",
  data_inicio: "data de início",
  data_fim: "data final",
  data_adocao: "data da adoção",
  horario_previsto: "horário",
  sexo: "sexo",
  porte: "porte",
  foto: "foto",
};

/** Remove códigos de requisito e troca jargão por palavras do dia a dia. */
export function limparTextoDoServidor(texto: string): string {
  let limpo = texto
    // "(RN05)", "(RN04, RF20)", "(RN12/RN14)", "(RF16)"
    .replace(/\s*\((?:R[NF]{1,2}\d+)(?:\s*[,/e]\s*(?:R[NF]{1,2}\d+))*\)/gi, "")
    .replace(/\bna Whitelist de usuárias da GAPAR\b/gi, "na lista de pessoas autorizadas")
    .replace(/\bna Whitelist\b/gi, "na lista de pessoas autorizadas")
    .replace(/\bà Whitelist\b/gi, "à lista de pessoas autorizadas")
    .replace(/\bda Whitelist\b/gi, "da lista de pessoas autorizadas")
    .replace(/\bWhitelist\b/gi, "lista de pessoas autorizadas")
    .replace(/\bGoogle OAuth\b/gi, "conta Google")
    .replace(/\bstatus operacional\b/gi, "situação")
    .replace(/\bstatus\b/gi, "situação")
    .replace(/\bendpoint\b/gi, "recurso")
    .replace(/\bexcluído logicamente\b/gi, "removido da lista");

  limpo = limpo.replace(/O campo '([a-z_]+)'/g, (_, campo: string) => {
    const nome = NOMES_DE_CAMPOS[campo] ?? campo.replace(/_/g, " ");
    return `O campo "${nome}"`;
  });
  limpo = limpo.replace(/'([a-z_]+)'/g, (trecho, campo: string) =>
    campo in NOMES_DE_CAMPOS ? `"${NOMES_DE_CAMPOS[campo]}"` : trecho,
  );

  return limpo.replace(/\s{2,}/g, " ").replace(/\s+\./g, ".").trim();
}

export function mensagemDeErro(status: number, erro: string, mensagem?: string): string {
  if (status === 0) {
    return "Não foi possível falar com o sistema. Confira sua internet e tente de novo.";
  }
  if (status === 401) {
    return "Sua sessão terminou. Entre de novo para continuar.";
  }
  if (status === 403) {
    if (erro === "Acesso revogado") {
      return "Seu acesso foi desativado pela administradora.";
    }
    if (erro === "Acesso não autorizado") {
      return "Este e-mail não está na lista de pessoas autorizadas. Peça a liberação à administradora.";
    }
    return "Esta área é exclusiva da administradora.";
  }
  if (status === 404) {
    return "Não encontramos o que você procurava. Pode ter sido removido.";
  }
  if (status === 413) {
    return "A foto é grande demais. Escolha uma imagem de até 10 MB.";
  }
  if (status >= 500) {
    return "O sistema teve um problema inesperado. Tente de novo em instantes.";
  }
  if (mensagem && mensagem.trim()) return limparTextoDoServidor(mensagem);
  if (erro && erro.trim() && erro !== "Erro") return limparTextoDoServidor(erro);
  return "Não foi possível concluir. Confira os dados e tente de novo.";
}

/** Mensagens da tela de entrada para os códigos de ?erro= devolvidos pelo servidor. */
export function mensagemDeErroDeEntrada(codigo: string | null): string | null {
  switch (codigo) {
    case null:
    case "":
      return null;
    case "google":
      return "Não conseguimos confirmar sua conta com o Google. Tente entrar de novo.";
    case "sem_acesso":
      return "Este e-mail não tem permissão para usar o sistema, ou o acesso foi desativado. Fale com a administradora da GAPAR.";
    case "falha":
      return "Não foi possível concluir a entrada agora. Tente de novo em instantes.";
    default:
      return "Não foi possível entrar. Tente de novo.";
  }
}
