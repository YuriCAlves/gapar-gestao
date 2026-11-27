import { describe, expect, it, vi } from "vitest";
import { criarDetectorLeitorMicrochip } from "./useLeitorMicrochip";

function simularDigitacao(
  registrarTecla: (key: string, agora?: number) => boolean,
  teclas: string[],
  intervaloMs: number,
  inicioMs = 1000,
): { resultados: boolean[]; fimMs: number } {
  const resultados: boolean[] = [];
  let agora = inicioMs;
  for (const tecla of teclas) {
    resultados.push(registrarTecla(tecla, agora));
    agora += intervaloMs;
  }
  return { resultados, fimMs: agora };
}

describe("criarDetectorLeitorMicrochip", () => {
  it("dispara aoLer exatamente 1 vez e retorna true em rajada HID de 15 dígitos (5 ms) + Enter", () => {
    const aoLer = vi.fn();
    const detector = criarDetectorLeitorMicrochip({ aoLer });
    const codigo = "900123456789012";

    const { resultados } = simularDigitacao(detector.registrarTecla, [...codigo, "Enter"], 5);

    expect(resultados.slice(0, 15).every((r) => r === false)).toBe(true);
    expect(resultados[15]).toBe(true);
    expect(aoLer).toHaveBeenCalledTimes(1);
    expect(aoLer).toHaveBeenCalledWith(codigo);
  });

  it("preserva zeros à esquerda na leitura HID", () => {
    const aoLer = vi.fn();
    const detector = criarDetectorLeitorMicrochip({ aoLer });
    const codigo = "000123456789012";

    const { resultados } = simularDigitacao(detector.registrarTecla, [...codigo, "Enter"], 5);

    expect(resultados[resultados.length - 1]).toBe(true);
    expect(aoLer).toHaveBeenCalledTimes(1);
    expect(aoLer).toHaveBeenCalledWith(codigo);
  });

  it("não dispara aoLer na digitação humana lenta (150 ms entre teclas) + Enter", () => {
    const aoLer = vi.fn();
    const detector = criarDetectorLeitorMicrochip({ aoLer });
    const codigo = "900123456789012";

    const { resultados } = simularDigitacao(detector.registrarTecla, [...codigo, "Enter"], 150);

    expect(resultados.every((r) => r === false)).toBe(true);
    expect(aoLer).not.toHaveBeenCalled();
  });

  it("não dispara aoLer se o Enter chegar fora da janela limiteMs após 15 dígitos rápidos", () => {
    const aoLer = vi.fn();
    const detector = criarDetectorLeitorMicrochip({ aoLer, limiteMs: 100 });
    const codigo = "900123456789012";

    const { fimMs } = simularDigitacao(detector.registrarTecla, [...codigo], 5, 1000);
    const ultimoDigitoMs = fimMs - 5;
    const resultadoEnter = detector.registrarTecla("Enter", ultimoDigitoMs + 150);

    expect(resultadoEnter).toBe(false);
    expect(aoLer).not.toHaveBeenCalled();
  });

  it("não dispara aoLer em rajada curta (10 dígitos) + Enter", () => {
    const aoLer = vi.fn();
    const detector = criarDetectorLeitorMicrochip({ aoLer });

    const { resultados } = simularDigitacao(detector.registrarTecla, [..."9001234567", "Enter"], 5);

    expect(resultados.every((r) => r === false)).toBe(true);
    expect(aoLer).not.toHaveBeenCalled();
  });

  it("não dispara aoLer em rajada longa (16 dígitos) + Enter", () => {
    const aoLer = vi.fn();
    const detector = criarDetectorLeitorMicrochip({ aoLer });

    const { resultados } = simularDigitacao(
      detector.registrarTecla,
      [..."9001234567890123", "Enter"],
      5,
    );

    expect(resultados.every((r) => r === false)).toBe(true);
    expect(aoLer).not.toHaveBeenCalled();
  });

  it("quebra o buffer corretamente ao receber tecla não-numérica no meio da rajada", () => {
    const aoLer = vi.fn();
    const detector = criarDetectorLeitorMicrochip({ aoLer });

    const { resultados } = simularDigitacao(
      detector.registrarTecla,
      [..."9001234", "a", ..."56789012", "Enter"],
      5,
    );

    expect(resultados.every((r) => r === false)).toBe(true);
    expect(aoLer).not.toHaveBeenCalled();

    // Uma nova rajada completa após a interrupção deve ser reconhecida normalmente.
    const codigoValido = "900987654321098";
    const segunda = simularDigitacao(detector.registrarTecla, [...codigoValido, "Enter"], 5, 5000);

    expect(segunda.resultados[segunda.resultados.length - 1]).toBe(true);
    expect(aoLer).toHaveBeenCalledTimes(1);
    expect(aoLer).toHaveBeenCalledWith(codigoValido);
  });

  it("reconhece duas leituras consecutivas de forma independente após limpeza do buffer", () => {
    const aoLer = vi.fn();
    const detector = criarDetectorLeitorMicrochip({ aoLer });
    const primeiro = "900123456789012";
    const segundo = "982000111222333";

    const primeiraLeitura = simularDigitacao(
      detector.registrarTecla,
      [...primeiro, "Enter"],
      5,
      1000,
    );
    const segundaLeitura = simularDigitacao(
      detector.registrarTecla,
      [...segundo, "Enter"],
      5,
      primeiraLeitura.fimMs + 10,
    );

    expect(primeiraLeitura.resultados[primeiraLeitura.resultados.length - 1]).toBe(true);
    expect(segundaLeitura.resultados[segundaLeitura.resultados.length - 1]).toBe(true);
    expect(aoLer).toHaveBeenCalledTimes(2);
    expect(aoLer).toHaveBeenNthCalledWith(1, primeiro);
    expect(aoLer).toHaveBeenNthCalledWith(2, segundo);
  });

  it("descarta dígitos acumulados ao chamar limpar()", () => {
    const aoLer = vi.fn();
    const detector = criarDetectorLeitorMicrochip({ aoLer });

    const { fimMs } = simularDigitacao(detector.registrarTecla, [..."900123456789012"], 5, 1000);
    detector.limpar();
    const resultadoEnter = detector.registrarTecla("Enter", fimMs);

    expect(resultadoEnter).toBe(false);
    expect(aoLer).not.toHaveBeenCalled();
  });
});
