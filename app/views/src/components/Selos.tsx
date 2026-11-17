import type { ReactNode } from "react";
import type { Animal, StatusAnimal } from "../types";
import { rotuloCurtoDoStatus, rotuloDoStatus } from "../utils/status";

export type CorDoSelo = "mata" | "barro" | "ambar" | "ceu" | "lilas" | "pedra" | "perigo";

const CORES: Record<CorDoSelo, string> = {
  mata: "bg-mata-100 text-mata-900",
  barro: "bg-barro-100 text-barro-900",
  ambar: "bg-ambar-100 text-ambar-900",
  ceu: "bg-ceu-100 text-ceu-900",
  lilas: "bg-lilas-100 text-lilas-900",
  pedra: "bg-pedra-100 text-pedra-900",
  perigo: "bg-perigo-100 text-perigo-900",
};

export function Selo({ cor, children, icone }: { cor: CorDoSelo; children: ReactNode; icone?: ReactNode }) {
  return (
    <span
      className={`inline-flex max-w-full items-center gap-1 rounded-full px-2.5 py-0.5 text-sm font-bold whitespace-nowrap ${CORES[cor]}`}
    >
      {icone}
      <span className="truncate">{children}</span>
    </span>
  );
}

const COR_DO_STATUS: Record<StatusAnimal, CorDoSelo> = {
  "em acolhimento": "barro",
  "em tratamento": "ambar",
  "disponível": "mata",
  "lar temporário": "ceu",
  "adotado": "lilas",
  "óbito": "pedra",
};

const PONTO_DO_STATUS: Record<StatusAnimal, string> = {
  "em acolhimento": "bg-barro-600",
  "em tratamento": "bg-ambar-900",
  "disponível": "bg-mata-600",
  "lar temporário": "bg-ceu-900",
  "adotado": "bg-lilas-900",
  "óbito": "bg-pedra-900",
};

export function SeloDeStatus({ status, curto = false }: { status: StatusAnimal; curto?: boolean }) {
  return (
    <Selo
      cor={COR_DO_STATUS[status] ?? "pedra"}
      icone={<span aria-hidden="true" className={`size-2 shrink-0 rounded-full ${PONTO_DO_STATUS[status] ?? "bg-pedra-900"}`} />}
    >
      {curto ? rotuloCurtoDoStatus(status) : rotuloDoStatus(status)}
    </Selo>
  );
}

/** Indicadores do cadastro: idoso, cuidados especiais, castrado (RF08). */
export function IndicadoresDoAnimal({ animal }: { animal: Pick<Animal, "is_idoso" | "is_castrado" | "cuidados_especiais"> }) {
  const temCuidados = Boolean(animal.cuidados_especiais?.trim());
  if (!animal.is_idoso && !animal.is_castrado && !temCuidados) return null;
  return (
    <span className="flex flex-wrap gap-1.5">
      {temCuidados && <Selo cor="perigo">Cuidados especiais</Selo>}
      {animal.is_idoso && <Selo cor="lilas">Idoso</Selo>}
      {animal.is_castrado && <Selo cor="pedra">Castrado</Selo>}
    </span>
  );
}
