// Geração de links de WhatsApp para a vitrine pública de adoção.
// A mensagem leva apenas o nome do animal — nunca dados internos ou pessoais.

const MINIMO_DIGITOS_TELEFONE = 10;

/**
 * Monta o link do WhatsApp para iniciar uma conversa sobre adoção de um cão específico.
 * Devolve `null` quando o número da ONG não estiver configurado ou não tiver dígitos suficientes.
 */
export function linkWhatsappAdocao(
  whatsappAdocao: string | null | undefined,
  nomeAnimal: string,
): string | null {
  const soDigitos = (whatsappAdocao ?? "").replace(/\D/g, "");
  if (soDigitos.length < MINIMO_DIGITOS_TELEFONE) return null;

  const nome = nomeAnimal.trim() || "um cão";
  const mensagem = `Olá! Vi ${nome} na vitrine da ONG GAPAR e gostaria de saber como funciona a adoção.`;
  return `https://wa.me/${soDigitos}?text=${encodeURIComponent(mensagem)}`;
}
