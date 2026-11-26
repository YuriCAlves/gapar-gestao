// Máscaras e validações de CPF e telefone (decisão D2).
// Os formulários guardam e enviam apenas dígitos; a pontuação é somente visual.

const LIMITE_DIGITOS = 11;

/** Remove tudo o que não for dígito numérico (0-9). */
export function soDigitos(valor: string): string {
  return valor.replace(/\D/g, "");
}

/**
 * Formata progressivamente um CPF (máx. 11 dígitos):
 * 123 → 123 | 1234 → 123.4 | 1234567 → 123.456.7 | 12345678909 → 123.456.789-09
 */
export function mascararCpf(valor: string): string {
  const digitos = soDigitos(valor).slice(0, LIMITE_DIGITOS);
  if (digitos.length <= 3) return digitos;
  if (digitos.length <= 6) return `${digitos.slice(0, 3)}.${digitos.slice(3)}`;
  if (digitos.length <= 9) return `${digitos.slice(0, 3)}.${digitos.slice(3, 6)}.${digitos.slice(6)}`;
  return `${digitos.slice(0, 3)}.${digitos.slice(3, 6)}.${digitos.slice(6, 9)}-${digitos.slice(9)}`;
}

/**
 * Valida CPF: exatamente 11 dígitos, rejeita sequências repetidas (000..., 111...)
 * e confere os dois dígitos verificadores pelo módulo 11.
 */
export function cpfValido(valor: string): boolean {
  const digitos = soDigitos(valor);
  if (digitos.length !== 11) return false;
  if (/^(\d)\1{10}$/.test(digitos)) return false;

  const calcularDigito = (tamanho: number): number => {
    let soma = 0;
    for (let i = 0; i < tamanho; i += 1) {
      soma += Number(digitos[i]) * (tamanho + 1 - i);
    }
    const resto = (soma * 10) % 11;
    return resto === 10 ? 0 : resto;
  };

  return calcularDigito(9) === Number(digitos[9]) && calcularDigito(10) === Number(digitos[10]);
}

/**
 * Formata progressivamente um telefone brasileiro (máx. 11 dígitos):
 * 10 dígitos: (00) 0000-0000 | 11 dígitos: (00) 00000-0000
 */
export function mascararTelefone(valor: string): string {
  const digitos = soDigitos(valor).slice(0, LIMITE_DIGITOS);
  if (digitos.length === 0) return "";
  if (digitos.length <= 2) return `(${digitos}`;
  if (digitos.length <= 6) return `(${digitos.slice(0, 2)}) ${digitos.slice(2)}`;
  if (digitos.length <= 10) return `(${digitos.slice(0, 2)}) ${digitos.slice(2, 6)}-${digitos.slice(6)}`;
  return `(${digitos.slice(0, 2)}) ${digitos.slice(2, 7)}-${digitos.slice(7)}`;
}

/**
 * Valida telefone brasileiro: 10 ou 11 dígitos, DDD entre 11 e 99.
 * Com 11 dígitos (celular), o terceiro dígito precisa ser 9.
 */
export function telefoneValido(valor: string): boolean {
  const digitos = soDigitos(valor);
  if (digitos.length !== 10 && digitos.length !== 11) return false;
  const ddd = Number(digitos.slice(0, 2));
  if (ddd < 11 || ddd > 99) return false;
  if (digitos.length === 11 && digitos[2] !== "9") return false;
  return true;
}

/** Mensagem de erro padronizada para CPF (usada no blur e no envio do formulário). */
export function mensagemErroCpf(valor: string, obrigatorio = false): string | null {
  const digitos = soDigitos(valor);
  if (!digitos) return obrigatorio ? "Confira o CPF: são 11 números." : null;
  if (digitos.length !== 11) return "Confira o CPF: são 11 números.";
  if (!cpfValido(digitos)) return "Este CPF não é válido. Confira os números.";
  return null;
}

/** Mensagem de erro padronizada para telefone (usada no blur e no envio do formulário). */
export function mensagemErroTelefone(valor: string, obrigatorio = false): string | null {
  const digitos = soDigitos(valor);
  if (!digitos) return obrigatorio ? "Informe o DDD e o número (10 ou 11 números)." : null;
  if (!telefoneValido(digitos)) return "Informe o DDD e o número (10 ou 11 números).";
  return null;
}

/**
 * Exibe CPF na tela: formata quando tiver 11 dígitos e mantém o valor original em dados antigos.
 */
export function exibirCpf(valor: string | null | undefined): string {
  const limpo = valor?.trim() ?? "";
  if (!limpo) return "";
  const digitos = soDigitos(limpo);
  return digitos.length === 11 ? mascararCpf(digitos) : limpo;
}

/**
 * Exibe telefone na tela: formata com máscara quando tiver 10–11 dígitos e mostra como veio
 * nos registros antigos (ex.: 8–9 dígitos sem DDD), sem bloquear a exibição.
 */
export function exibirTelefone(valor: string | null | undefined): string {
  const limpo = valor?.trim() ?? "";
  if (!limpo) return "";
  const digitos = soDigitos(limpo);
  return digitos.length === 10 || digitos.length === 11 ? mascararTelefone(digitos) : limpo;
}

/**
 * Encontra a posição exata do cursor no texto já mascarado após `digitosAntesDoCursor` dígitos,
 * evitando que o cursor pule para o final ao editar ou apagar no meio do campo.
 */
export function posicaoCursorNaMascara(textoMascarado: string, digitosAntesDoCursor: number): number {
  if (digitosAntesDoCursor <= 0) return 0;
  let vistos = 0;
  for (let i = 0; i < textoMascarado.length; i += 1) {
    if (/\d/.test(textoMascarado[i])) {
      vistos += 1;
      if (vistos === digitosAntesDoCursor) {
        return i + 1;
      }
    }
  }
  return textoMascarado.length;
}
