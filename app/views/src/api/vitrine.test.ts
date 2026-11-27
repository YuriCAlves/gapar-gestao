import { afterEach, describe, expect, it, vi } from "vitest";
import type { AnimalPublico, PaginaVitrine } from "../types/contratos";
import { linkWhatsappAdocao } from "../utils/whatsapp";
import { ErroApi } from "./http";
import { listarVitrine, obterAnimalPublico } from "./vitrine";

const ANIMAL_EXEMPLO: AnimalPublico = {
  slug: "rex-uuid",
  nome: "Rex",
  sexo: "Macho",
  porte: "Médio",
  idade_estimada: "3 anos",
  raca: "Sem raça definida",
  pelagem: "Caramelo",
  foto_url: "https://cdn.exemplo.org/rex.jpg",
  is_castrado: true,
  is_idoso: false,
  descricao_publica: "Brincalhão e muito dócil com pessoas.",
  candidaturas_pausadas: false,
};

function respostaJson(dados: unknown, status = 200): Response {
  return new Response(JSON.stringify(dados), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("API pública da vitrine", () => {
  it("listarVitrine envia credentials omit e retorna a página simulada", async () => {
    const paginaSimulada: PaginaVitrine = {
      animais: [ANIMAL_EXEMPLO],
      pagina: 1,
      por_pagina: 12,
      total: 15,
      tem_mais: true,
    };
    const fetchMock = vi.fn().mockResolvedValue(respostaJson(paginaSimulada, 200));
    vi.stubGlobal("fetch", fetchMock);

    const resultado = await listarVitrine(1);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/public/animais?pagina=1",
      expect.objectContaining({
        method: "GET",
        credentials: "omit",
        headers: { Accept: "application/json" },
      }),
    );
    expect(resultado).toEqual(paginaSimulada);
    expect(resultado.tem_mais).toBe(true);
  });

  it("obterAnimalPublico retorna o animal no 200 e envia credentials omit", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respostaJson({ animal: ANIMAL_EXEMPLO }, 200));
    vi.stubGlobal("fetch", fetchMock);

    const animal = await obterAnimalPublico("rex-uuid");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/public/animais/rex-uuid",
      expect.objectContaining({
        method: "GET",
        credentials: "omit",
        headers: { Accept: "application/json" },
      }),
    );
    expect(animal).toEqual(ANIMAL_EXEMPLO);
  });

  it("obterAnimalPublico retorna null no 404 sem lançar exceção (Regra B1)", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(respostaJson({ erro: "Não encontrado" }, 404));
    vi.stubGlobal("fetch", fetchMock);

    const animal = await obterAnimalPublico("rex-uuid");

    expect(animal).toBeNull();
  });

  it("obterAnimalPublico lança ErroApi(500) quando o servidor falha", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(respostaJson({ erro: "Erro interno" }, 500));
    vi.stubGlobal("fetch", fetchMock);

    await expect(obterAnimalPublico("rex-uuid")).rejects.toSatisfy(
      (erro: unknown) => erro instanceof ErroApi && erro.status === 500,
    );
  });
});

describe("linkWhatsappAdocao", () => {
  it("monta wa.me com acentos e espaços codificados contendo apenas o nome do animal", () => {
    const link = linkWhatsappAdocao("5541999998888", "Pingo Café");
    expect(link).not.toBeNull();
    expect(link).toMatch(/^https:\/\/wa\.me\/5541999998888\?text=/);
    expect(link).toContain(encodeURIComponent("Pingo Café"));

    const texto = decodeURIComponent((link as string).split("?text=")[1]);
    expect(texto).toContain("Pingo Café");
    expect(texto).not.toContain("rex-uuid");
    expect(texto).not.toContain("Caramelo");

    const linkAcentuado = linkWhatsappAdocao("(55) 41 99999-8888", "Lúcia Maria");
    expect(linkAcentuado).not.toBeNull();
    expect(linkAcentuado).toMatch(/^https:\/\/wa\.me\/5541999998888\?text=/);
    expect(linkAcentuado).toContain(encodeURIComponent("Lúcia Maria"));
  });

  it("retorna null quando whatsappAdocao é nulo, vazio ou sem dígitos suficientes", () => {
    expect(linkWhatsappAdocao(null, "Rex")).toBeNull();
    expect(linkWhatsappAdocao(undefined, "Rex")).toBeNull();
    expect(linkWhatsappAdocao("", "Rex")).toBeNull();
    expect(linkWhatsappAdocao("   ", "Rex")).toBeNull();
    expect(linkWhatsappAdocao("12345", "Rex")).toBeNull();
  });
});
