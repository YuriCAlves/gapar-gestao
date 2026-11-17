import type { PainelHoje } from "../types";
import { requisitar } from "./http";

export function buscarPainelHoje(sinal?: AbortSignal): Promise<PainelHoje> {
  return requisitar<PainelHoje>("/api/hoje", { sinal });
}
