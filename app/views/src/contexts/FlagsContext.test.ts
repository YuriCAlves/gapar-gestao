import { afterEach, describe, expect, it, vi } from "vitest";
import { obterConfigPublica } from "../api/public";
import { CONFIG_PUBLICA_FECHADA, FLAGS_PUBLICAS } from "../types/contratos";

afterEach(() => {
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
});
