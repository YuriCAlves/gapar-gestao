// Horários de medicação: o servidor guarda "08:00, 20:00" (HH:MM separados por vírgula).

const FORMATO = /^([01]\d|2[0-3]):[0-5]\d$/;

export function horarioValido(horario: string): boolean {
  return FORMATO.test(horario.trim());
}

/** "08:00, 20:00" -> ["08:00", "20:00"] */
export function separarHorarios(texto: string): string[] {
  return texto
    .split(",")
    .map((parte) => parte.trim())
    .filter(Boolean);
}

/** Junta os horários preenchidos, sem repetição e em ordem, no formato aceito pelo servidor. */
export function juntarHorarios(horarios: string[]): string {
  const unicos = Array.from(new Set(horarios.map((h) => h.trim()).filter(Boolean)));
  return unicos.sort().join(", ");
}

/** Devolve a mensagem de erro para a lista de horários, ou null se estiver tudo certo. */
export function validarHorarios(horarios: string[]): string | null {
  const preenchidos = horarios.map((h) => h.trim()).filter(Boolean);
  if (preenchidos.length === 0) return "Informe pelo menos um horário.";
  if (preenchidos.some((h) => !horarioValido(h))) return "Use horários no formato 08:00.";
  if (new Set(preenchidos).size !== preenchidos.length) return "Há horários repetidos.";
  return null;
}

/** True quando o horário previsto já passou (comparação de "HH:MM" no mesmo dia). */
export function horarioJaPassou(previsto: string, agora: string): boolean {
  return previsto < agora;
}
