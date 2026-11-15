// Datas do servidor chegam em dois formatos:
// - só data, "AAAA-MM-DD" (data de entrada, vacinas, adoção): não tem fuso, é lida como está;
// - data e hora sem fuso, em UTC (created_at dos registros): convertida para o horário do aparelho.

const MESES = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];
const DIAS_DA_SEMANA = [
  "domingo", "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado",
];

function doisDigitos(numero: number): string {
  return String(numero).padStart(2, "0");
}

function partesDaData(iso: string): { ano: number; mes: number; dia: number } | null {
  const partes = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!partes) return null;
  return { ano: Number(partes[1]), mes: Number(partes[2]), dia: Number(partes[3]) };
}

/** Data de hoje no aparelho, em "AAAA-MM-DD" (formato dos campos de data). */
export function hojeISO(agora: Date = new Date()): string {
  return `${agora.getFullYear()}-${doisDigitos(agora.getMonth() + 1)}-${doisDigitos(agora.getDate())}`;
}

/** Hora atual do aparelho em "HH:MM". */
export function horaAtual(agora: Date = new Date()): string {
  return `${doisDigitos(agora.getHours())}:${doisDigitos(agora.getMinutes())}`;
}

/** "2026-11-13" -> "13/11/2026". Devolve "—" quando não há data. */
export function formatarData(iso: string | null | undefined): string {
  if (!iso) return "—";
  const partes = partesDaData(iso);
  if (!partes) return "—";
  return `${doisDigitos(partes.dia)}/${doisDigitos(partes.mes)}/${partes.ano}`;
}

/** "2026-11-13" -> "sexta-feira, 13 de novembro". */
export function formatarDataPorExtenso(iso: string): string {
  const partes = partesDaData(iso);
  if (!partes) return "";
  const data = new Date(partes.ano, partes.mes - 1, partes.dia);
  return `${DIAS_DA_SEMANA[data.getDay()]}, ${partes.dia} de ${MESES[partes.mes - 1]}`;
}

/** Data e hora de um registro (UTC sem fuso) -> "13/11/2026 às 14:05" no horário do aparelho. */
export function formatarDataHora(iso: string | null | undefined): string {
  if (!iso) return "—";
  const temFuso = /(Z|[+-]\d{2}:?\d{2})$/.test(iso);
  const data = new Date(temFuso ? iso : `${iso}Z`);
  if (Number.isNaN(data.getTime())) return "—";
  const dia = `${doisDigitos(data.getDate())}/${doisDigitos(data.getMonth() + 1)}/${data.getFullYear()}`;
  return `${dia} às ${doisDigitos(data.getHours())}:${doisDigitos(data.getMinutes())}`;
}

/** Diferença em dias entre duas datas "AAAA-MM-DD" (fim - início). */
export function diasEntre(inicio: string, fim: string): number {
  const a = partesDaData(inicio);
  const b = partesDaData(fim);
  if (!a || !b) return 0;
  const umDia = 24 * 60 * 60 * 1000;
  return Math.round((Date.UTC(b.ano, b.mes - 1, b.dia) - Date.UTC(a.ano, a.mes - 1, a.dia)) / umDia);
}

/** Texto curto para prazos: "hoje", "amanhã", "em 12 dias", "há 3 dias". */
export function prazoRelativo(iso: string, referencia: string = hojeISO()): string {
  const dias = diasEntre(referencia, iso);
  if (dias === 0) return "hoje";
  if (dias === 1) return "amanhã";
  if (dias === -1) return "ontem";
  if (dias > 1) return `em ${dias} dias`;
  return `há ${-dias} dias`;
}
