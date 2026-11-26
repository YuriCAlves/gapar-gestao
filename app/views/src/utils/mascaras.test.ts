import { describe, expect, it } from "vitest";
import {
  cpfValido,
  exibirCpf,
  exibirTelefone,
  mascararCpf,
  mascararTelefone,
  mensagemErroCpf,
  mensagemErroTelefone,
  posicaoCursorNaMascara,
  soDigitos,
  telefoneValido,
} from "./mascaras";

describe("soDigitos", () => {
  it("remove letras, espaços e pontuação", () => {
    expect(soDigitos("123.456.789-09")).toBe("12345678909");
    expect(soDigitos("(41) 98765-4321")).toBe("41987654321");
    expect(soDigitos("abc 12-de 34!@#")).toBe("1234");
  });
});

describe("mascararCpf", () => {
  it("formata progressivamente dígito a dígito", () => {
    const passos: [string, string][] = [
      ["", ""],
      ["1", "1"],
      ["12", "12"],
      ["123", "123"],
      ["1234", "123.4"],
      ["12345", "123.45"],
      ["123456", "123.456"],
      ["1234567", "123.456.7"],
      ["12345678", "123.456.78"],
      ["123456789", "123.456.789"],
      ["1234567890", "123.456.789-0"],
      ["12345678909", "123.456.789-09"],
    ];
    for (const [entrada, esperado] of passos) {
      expect(mascararCpf(entrada)).toBe(esperado);
    }
  });

  it("aceita colar valor já formatado ou com letras e limita a 11 dígitos", () => {
    expect(mascararCpf("123.456.789-09")).toBe("123.456.789-09");
    expect(mascararCpf("CPF: 123a456b789c09")).toBe("123.456.789-09");
    expect(mascararCpf("123456789099999")).toBe("123.456.789-09");
  });
});

describe("cpfValido", () => {
  it("aceita CPFs válidos com ou sem pontuação", () => {
    expect(cpfValido("52998224725")).toBe(true);
    expect(cpfValido("529.982.247-25")).toBe(true);
    expect(cpfValido("11144477735")).toBe(true);
    expect(cpfValido("12345678909")).toBe(true);
  });

  it("rejeita CPFs incompletos, dígitos verificadores errados e sequências repetidas", () => {
    expect(cpfValido("")).toBe(false);
    expect(cpfValido("5299822472")).toBe(false);
    expect(cpfValido("52998224726")).toBe(false);
    expect(cpfValido("52998224715")).toBe(false);
    for (let d = 0; d <= 9; d += 1) {
      expect(cpfValido(String(d).repeat(11))).toBe(false);
    }
  });

  it("devolve as mensagens de erro esperadas", () => {
    expect(mensagemErroCpf("", false)).toBeNull();
    expect(mensagemErroCpf("", true)).toBe("Confira o CPF: são 11 números.");
    expect(mensagemErroCpf("12345")).toBe("Confira o CPF: são 11 números.");
    expect(mensagemErroCpf("11111111111")).toBe("Este CPF não é válido. Confira os números.");
    expect(mensagemErroCpf("52998224725")).toBeNull();
  });
});

describe("mascararTelefone", () => {
  it("formata progressivamente dígito a dígito para fixo (10) e celular (11)", () => {
    const passos: [string, string][] = [
      ["", ""],
      ["4", "(4"],
      ["41", "(41"],
      ["413", "(41) 3"],
      ["413222", "(41) 3222"],
      ["4132223", "(41) 3222-3"],
      ["4132223344", "(41) 3222-3344"],
      ["41987654321", "(41) 98765-4321"],
    ];
    for (const [entrada, esperado] of passos) {
      expect(mascararTelefone(entrada)).toBe(esperado);
    }
  });

  it("aceita colar formatado, ignora letras e limita a 11 dígitos", () => {
    expect(mascararTelefone("(41) 98765-4321")).toBe("(41) 98765-4321");
    expect(mascararTelefone("tel: 41abc98765def4321")).toBe("(41) 98765-4321");
    expect(mascararTelefone("419876543219999")).toBe("(41) 98765-4321");
  });
});

describe("telefoneValido", () => {
  it("aceita fixo (10 dígitos) e celular (11 dígitos com 9)", () => {
    expect(telefoneValido("4132223344")).toBe(true);
    expect(telefoneValido("(41) 3222-3344")).toBe(true);
    expect(telefoneValido("11987654321")).toBe(true);
    expect(telefoneValido("(99) 91234-5678")).toBe(true);
  });

  it("rejeita sem DDD, DDD fora de 11-99 e celular sem 9 no terceiro dígito", () => {
    expect(telefoneValido("")).toBe(false);
    expect(telefoneValido("32223344")).toBe(false);
    expect(telefoneValido("987654321")).toBe(false);
    expect(telefoneValido("10987654321")).toBe(false);
    expect(telefoneValido("0032223344")).toBe(false);
    expect(telefoneValido("41887654321")).toBe(false);
  });

  it("devolve a mensagem de erro esperada", () => {
    expect(mensagemErroTelefone("", false)).toBeNull();
    expect(mensagemErroTelefone("", true)).toBe("Informe o DDD e o número (10 ou 11 números).");
    expect(mensagemErroTelefone("987654321")).toBe("Informe o DDD e o número (10 ou 11 números).");
    expect(mensagemErroTelefone("41987654321")).toBeNull();
  });
});

describe("exibição de dados antigos e posição do cursor", () => {
  it("preserva registros antigos sem DDD e formata registros completos", () => {
    expect(exibirTelefone("3222-3344")).toBe("3222-3344");
    expect(exibirTelefone("999998888")).toBe("999998888");
    expect(exibirTelefone("41999998888")).toBe("(41) 99999-8888");
    expect(exibirTelefone("4132223344")).toBe("(41) 3222-3344");
    expect(exibirCpf("52998224725")).toBe("529.982.247-25");
    expect(exibirCpf("12345")).toBe("12345");
  });

  it("calcula posição do cursor sem pular para o fim ao editar no meio", () => {
    expect(posicaoCursorNaMascara("123.456.789-09", 0)).toBe(0);
    expect(posicaoCursorNaMascara("123.456.789-09", 3)).toBe(3);
    expect(posicaoCursorNaMascara("123.456.789-09", 4)).toBe(5);
    expect(posicaoCursorNaMascara("(41) 98765-4321", 2)).toBe(3);
    expect(posicaoCursorNaMascara("(41) 98765-4321", 3)).toBe(6);
  });
});
