// Máscara e validação de microchip animal padrão ISO 11784/11785 (15 dígitos numéricos).
// O formulário guarda e envia apenas dígitos; os espaços a cada 3 números são somente visuais.

import { soDigitos } from "./mascaras";

/** Quantidade exata de dígitos de um microchip padrão ISO 11784/11785. */
export const TAMANHO_MICROCHIP = 15;

const MENSAGEM_ERRO_MICROCHIP = "O número do microchip precisa ter exatamente 15 números.";

/**
 * Extrai apenas os dígitos (0–9) do valor informado e limita a 15 caracteres,
 * preservando zeros à esquerda e permitindo colagem com espaços, hífens ou prefixos.
 */
export function limparMicrochip(valor: string): string {
  return soDigitos(valor).slice(0, TAMANHO_MICROCHIP);
}

/**
 * Valida se o valor informado possui exatamente 15 dígitos numéricos (padrão ISO),
 * ignorando espaços, hífens ou prefixos textuais.
 */
export function validarMicrochip(valor: string): boolean {
  return /^\d{15}$/.test(soDigitos(valor));
}

/**
 * Formata progressivamente o número do microchip em grupos de 3 dígitos (000 000 000 000 000):
 * 9001 → 900 1 | 900123456789012 → 900 123 456 789 012
 */
export function formatarMicrochip(valor: string): string {
  const digitos = limparMicrochip(valor);
  if (!digitos) return "";
  return digitos.match(/.{1,3}/g)?.join(" ") ?? digitos;
}

/**
 * Aplica a máscara visual de microchip em campos de texto sem depender de `maxLength`,
 * permitindo colar códigos com pontuação ou prefixos.
 */
export function mascararMicrochip(valor: string): string {
  return formatarMicrochip(limparMicrochip(valor));
}

/**
 * Mensagem de erro padronizada para microchip (usada no blur e no envio do formulário).
 */
export function mensagemErroMicrochip(valor: string, obrigatorio = false): string | null {
  const digitos = soDigitos(valor);
  if (!digitos) return obrigatorio ? MENSAGEM_ERRO_MICROCHIP : null;
  if (!validarMicrochip(valor)) return MENSAGEM_ERRO_MICROCHIP;
  return null;
}
