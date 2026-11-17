import { describe, expect, it } from "vitest";
import { normalizarAuditoria } from "../api/admin";
import { diasEntre, formatarData, prazoRelativo } from "./datas";
import { calcularDimensoes, enderecoDaFoto } from "./foto";
import { juntarHorarios, validarHorarios } from "./horarios";
import { limparTextoDoServidor, mensagemDeErro, mensagemDeErroDeEntrada } from "./mensagens";
import { podeReceberPrescricao, podeSerAdotado, statusDisponiveisParaTroca } from "./status";

describe("situação do animal", () => {
  it("nunca oferece 'adotado' na troca simples e nada para fichas congeladas", () => {
    expect(statusDisponiveisParaTroca("em acolhimento")).toEqual(["em tratamento", "disponível", "lar temporário"]);
    expect(statusDisponiveisParaTroca("adotado")).toEqual([]);
    expect(statusDisponiveisParaTroca("óbito")).toEqual([]);
  });
  it("segue RN08 e as condições de adoção", () => {
    expect(podeReceberPrescricao("disponível")).toBe(false);
    expect(podeReceberPrescricao("lar temporário")).toBe(true);
    expect(podeSerAdotado("em tratamento")).toBe(false);
    expect(podeSerAdotado("lar temporário")).toBe(true);
  });
});

describe("horários", () => {
  it("valida e junta no formato aceito pelo servidor", () => {
    expect(validarHorarios(["08:00", "20:00"])).toBeNull();
    expect(validarHorarios([""])).not.toBeNull();
    expect(validarHorarios(["8h"])).not.toBeNull();
    expect(validarHorarios(["08:00", "08:00"])).not.toBeNull();
    expect(juntarHorarios(["20:00", "08:00", ""])).toBe("08:00, 20:00");
  });
});

describe("mensagens", () => {
  it("retira códigos de requisito e jargão", () => {
    expect(limparTextoDoServidor("Ficha congelada (RN05).")).toBe("Ficha congelada.");
    expect(limparTextoDoServidor("Seu e-mail foi desativado na Whitelist pela administração (RN12/RN14).")).toBe(
      "Seu e-mail foi desativado na lista de pessoas autorizadas pela administração.",
    );
    expect(limparTextoDoServidor("O campo 'peso_kg' deve ser numérico.")).toBe('O campo "peso" deve ser numérico.');
  });
  it("traduz códigos de erro", () => {
    expect(mensagemDeErro(0, "")).toMatch(/internet/);
    expect(mensagemDeErro(401, "")).toMatch(/sessão/);
    expect(mensagemDeErroDeEntrada("sem_acesso")).toMatch(/administradora/);
    expect(mensagemDeErroDeEntrada(null)).toBeNull();
  });
});

describe("datas", () => {
  it("formata e calcula prazos", () => {
    expect(formatarData("2026-11-05")).toBe("05/11/2026");
    expect(formatarData(null)).toBe("—");
    expect(diasEntre("2026-11-01", "2026-11-13")).toBe(12);
    expect(prazoRelativo("2026-11-14", "2026-11-13")).toBe("amanhã");
    expect(prazoRelativo("2026-11-10", "2026-11-13")).toBe("há 3 dias");
  });
});

describe("fotos", () => {
  it("aceita caminho do servidor e endereço completo", () => {
    expect(enderecoDaFoto("/static/uploads/a.jpg")).toBe("/static/uploads/a.jpg");
    expect(enderecoDaFoto("static/uploads/a.jpg")).toBe("/static/uploads/a.jpg");
    expect(enderecoDaFoto("https://x.supabase.co/a.jpg")).toBe("https://x.supabase.co/a.jpg");
    expect(enderecoDaFoto("  ")).toBeNull();
  });
  it("reduz para 1600 px no lado maior sem ampliar", () => {
    expect(calcularDimensoes(4000, 3000)).toEqual({ largura: 1600, altura: 1200 });
    expect(calcularDimensoes(800, 600)).toEqual({ largura: 800, altura: 600 });
  });
});

describe("histórico de ações", () => {
  it("funciona com e sem paginação do servidor", () => {
    const semPaginas = normalizarAuditoria({ logs: [], total: 100 }, 1);
    expect(semPaginas).toMatchObject({ paginaAtual: 1, totalPaginas: 1, total: null });
    const comPaginas = normalizarAuditoria({ logs: [], pagina_atual: 2, total_paginas: 5, total_registros: 140 }, 2);
    expect(comPaginas).toMatchObject({ paginaAtual: 2, totalPaginas: 5, total: 140 });
  });
});

// RNF12: contraste mínimo 4.5:1 dos pares de texto/fundo usados no app
function luminancia(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function contraste(a: string, b: string): number {
  const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}

describe("contraste das cores", () => {
  const pares: [string, string, string][] = [
    ["tinta-700 em creme-50", "#3d4a43", "#fbf7f0"],
    ["tinta-500 em branco", "#56625b", "#ffffff"],
    ["tinta-500 em creme-50", "#56625b", "#fbf7f0"],
    ["branco em mata-700", "#ffffff", "#1f5c3a"],
    ["mata-800 em mata-50", "#184a2e", "#ecf5ee"],
    ["mata-700 em branco", "#1f5c3a", "#ffffff"],
    ["barro-700 em branco", "#94421f", "#ffffff"],
    ["barro-700 em barro-50", "#94421f", "#fcf0e8"],
    ["barro-900 em barro-100", "#6b2c12", "#f8dfcf"],
    ["ambar-900 em ambar-100", "#5e4200", "#f9e7b0"],
    ["ceu-900 em ceu-100", "#1f4470", "#d3e2f4"],
    ["lilas-900 em lilas-100", "#4d3470", "#e3d6f0"],
    ["pedra-900 em pedra-100", "#403d39", "#e9e6e1"],
    ["perigo-900 em perigo-100", "#6e1511", "#f9d4d0"],
    ["perigo-700 em branco", "#8f1d17", "#ffffff"],
    ["branco em perigo-600", "#ffffff", "#b3261e"],
    ["branco em barro-600", "#ffffff", "#b0522b"],
    ["tinta-500 em creme-200", "#56625b", "#e8decd"],
    ["mata-50 em mata-800", "#ecf5ee", "#184a2e"],
  ];
  it.each(pares)("%s passa de 4.5:1", (_, texto, fundo) => {
    expect(contraste(texto, fundo)).toBeGreaterThanOrEqual(4.5);
  });
});
