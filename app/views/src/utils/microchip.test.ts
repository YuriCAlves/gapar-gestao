import { describe, expect, it } from "vitest";
import {
  TAMANHO_MICROCHIP,
  formatarMicrochip,
  limparMicrochip,
  mascararMicrochip,
  mensagemErroMicrochip,
  validarMicrochip,
} from "./microchip";

const ERRO_ESPERADO = "O número do microchip precisa ter exatamente 15 números.";

describe("limparMicrochip", () => {
  it("mantém apenas dígitos, preserva zeros à esquerda e limita a 15 caracteres", () => {
    expect(TAMANHO_MICROCHIP).toBe(15);
    expect(limparMicrochip("")).toBe("");
    expect(limparMicrochip("900 123 456 789 012")).toBe("900123456789012");
    expect(limparMicrochip("Chip: 900-123-456-789-012")).toBe("900123456789012");
    expect(limparMicrochip("000 123 456 789 012")).toBe("000123456789012");
    expect(limparMicrochip("9001234567890129999")).toBe("900123456789012");
  });
});

describe("formatarMicrochip e mascararMicrochip", () => {
  it("formata progressivamente dígito a dígito em grupos de 3", () => {
    const passos: [string, string][] = [
      ["", ""],
      ["9", "9"],
      ["90", "90"],
      ["900", "900"],
      ["9001", "900 1"],
      ["90012", "900 12"],
      ["900123", "900 123"],
      ["9001234", "900 123 4"],
      ["90012345", "900 123 45"],
      ["900123456", "900 123 456"],
      ["9001234567", "900 123 456 7"],
      ["90012345678", "900 123 456 78"],
      ["900123456789", "900 123 456 789"],
      ["9001234567890", "900 123 456 789 0"],
      ["90012345678901", "900 123 456 789 01"],
      ["900123456789012", "900 123 456 789 012"],
    ];

    for (const [entrada, esperado] of passos) {
      expect(formatarMicrochip(entrada)).toBe(esperado);
      expect(mascararMicrochip(entrada)).toBe(esperado);
    }
  });

  it("aceita colagem formatada, com prefixo/letras, zeros à esquerda e limita a 15 dígitos", () => {
    expect(mascararMicrochip("900 123 456 789 012")).toBe("900 123 456 789 012");
    expect(mascararMicrochip("Chip: 900-123-456-789-012")).toBe("900 123 456 789 012");
    expect(mascararMicrochip("000123456789012")).toBe("000 123 456 789 012");
    expect(mascararMicrochip("9001234567890123456")).toBe("900 123 456 789 012");
    expect(formatarMicrochip("Chip: 900-123-456-789-012-999")).toBe("900 123 456 789 012");
  });
});

describe("validarMicrochip", () => {
  it("aceita exatamente 15 dígitos, preservando zeros à esquerda", () => {
    expect(validarMicrochip("900123456789012")).toBe(true);
    expect(validarMicrochip("900 123 456 789 012")).toBe(true);
    expect(validarMicrochip("Chip: 900-123-456-789-012")).toBe(true);
    expect(validarMicrochip("000123456789012")).toBe(true);
    expect(validarMicrochip("000 123 456 789 012")).toBe(true);
  });

  it("rejeita vazio, 14 dígitos e 16 dígitos", () => {
    expect(validarMicrochip("")).toBe(false);
    expect(validarMicrochip("   ")).toBe(false);
    expect(validarMicrochip("90012345678901")).toBe(false);
    expect(validarMicrochip("9001234567890123")).toBe(false);
    expect(validarMicrochip("900 123 456 789 012 3")).toBe(false);
  });
});

describe("mensagemErroMicrochip", () => {
  it("devolve null quando vazio e opcional, ou quando tiver 15 dígitos válidos", () => {
    expect(mensagemErroMicrochip("")).toBeNull();
    expect(mensagemErroMicrochip("", false)).toBeNull();
    expect(mensagemErroMicrochip("   ", false)).toBeNull();
    expect(mensagemErroMicrochip("900123456789012")).toBeNull();
    expect(mensagemErroMicrochip("900 123 456 789 012", true)).toBeNull();
    expect(mensagemErroMicrochip("000123456789012", true)).toBeNull();
  });

  it("devolve mensagem humana quando obrigatório e vazio ou quando tamanho difere de 15", () => {
    expect(mensagemErroMicrochip("", true)).toBe(ERRO_ESPERADO);
    expect(mensagemErroMicrochip("   ", true)).toBe(ERRO_ESPERADO);
    expect(mensagemErroMicrochip("90012345678901")).toBe(ERRO_ESPERADO);
    expect(mensagemErroMicrochip("9001234567890123")).toBe(ERRO_ESPERADO);
    expect(mensagemErroMicrochip("12345", true)).toBe(ERRO_ESPERADO);
  });
});
