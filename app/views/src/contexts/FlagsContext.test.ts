import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { StaticRouter } from "react-router-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { obterConfigPublica } from "../api/public";
import { CONFIG_PUBLICA_FECHADA, FLAGS_PUBLICAS } from "../types/contratos";
import {
  carregarConfigPublicaComTimeout,
  FlagsProvider,
  RequerFlag,
  RotaComFlag,
  TIMEOUT_CONFIG_PUBLICA_MS,
} from "./FlagsContext";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("FlagsContext / obterConfigPublica (fail-closed)", () => {
  it("devolve todas as flags desligadas quando o fetch falha por rede", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchMock);

    const config = await obterConfigPublica();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/public/config",
      expect.objectContaining({
        method: "GET",
        credentials: "omit",
      }),
    );
    expect(config).toEqual(CONFIG_PUBLICA_FECHADA);
    for (const flag of FLAGS_PUBLICAS) {
      expect(config.flags[flag]).toBe(false);
    }
  });

  it("devolve tudo desligado quando o servidor responde 500", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ erro: "Erro interno" }), {
        status: 500,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const config = await obterConfigPublica();

    expect(config).toEqual(CONFIG_PUBLICA_FECHADA);
    expect(config.turnstile_site_key).toBeNull();
    expect(config.whatsapp_adocao).toBeNull();
  });

  it("liga apenas as flags explicitamente true e mantém o restante desligado (sem enviar cookies)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          flags: { vitrine: true, estoque: "true", mapa: false },
          turnstile_site_key: "site-key-prod",
          whatsapp_adocao: "5541999998888",
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const config = await obterConfigPublica();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/public/config",
      expect.objectContaining({ credentials: "omit" }),
    );
    expect(config.flags.vitrine).toBe(true);
    // String "true" não pode passar como booleano verdadeiro (fail-closed estrito)
    expect(config.flags.estoque).toBe(false);
    expect(config.flags.mapa).toBe(false);
    expect(config.flags.termo_digital).toBe(false);
    expect(config.flags.carteira).toBe(false);
    expect(config.turnstile_site_key).toBe("site-key-prod");
    expect(config.whatsapp_adocao).toBe("5541999998888");
  });

  it("encerra com fail-closed após o tempo limite sem chamar abort() quando o servidor trava", async () => {
    vi.useFakeTimers();
    const controleExterno = new AbortController();
    let sinalAbortado = false;

    const buscarTravada = vi.fn((sinal?: AbortSignal) => {
      return new Promise<typeof CONFIG_PUBLICA_FECHADA>((_, reject) => {
        sinal?.addEventListener("abort", () => {
          sinalAbortado = true;
          reject(new DOMException("Aborted", "AbortError"));
        });
      });
    });

    const promessa = carregarConfigPublicaComTimeout(
      buscarTravada,
      TIMEOUT_CONFIG_PUBLICA_MS,
      controleExterno.signal,
    );
    await vi.advanceTimersByTimeAsync(TIMEOUT_CONFIG_PUBLICA_MS);
    const config = await promessa;

    expect(sinalAbortado).toBe(false);
    expect(controleExterno.signal.aborted).toBe(false);
    expect(config).toEqual(CONFIG_PUBLICA_FECHADA);
  });

  it("renderiza RequerFlag e RotaComFlag em estado inicial fail-closed sem vazar conteúdo", () => {
    const htmlRequerFlag = renderToString(
      createElement(
        FlagsProvider,
        null,
        createElement(
          RequerFlag,
          {
            flag: "vitrine",
            fallback: createElement("p", null, "Módulo desligado"),
            children: createElement("p", null, "Conteúdo da vitrine"),
          },
        ),
      ),
    );
    expect(htmlRequerFlag).toContain("Módulo desligado");
    expect(htmlRequerFlag).not.toContain("Conteúdo da vitrine");

    const htmlRotaComFlag = renderToString(
      createElement(
        StaticRouter,
        { location: "/adote" },
        createElement(
          FlagsProvider,
          null,
          createElement(RotaComFlag, {
            flag: "vitrine",
            publica: true,
            children: createElement("p", null, "Conteúdo protegido da rota"),
          }),
        ),
      ),
    );
    expect(htmlRotaComFlag).toContain("Carregando");
    expect(htmlRotaComFlag).not.toContain("Conteúdo protegido da rota");
  });
});
