import { afterEach, describe, expect, it, vi } from "vitest";
import { listarNaoAptos } from "./admin";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function responderJson(dados: unknown) {
  return vi.fn().mockResolvedValue(
    new Response(JSON.stringify(dados), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );
}

describe("listarNaoAptos (busca sigilosa via POST sem PII na URL)", () => {
  it("lista tudo via GET /api/admin/nao-aptos sem query string quando não há filtro", async () => {
    const fetchMock = responderJson({ sucesso: true, nao_aptos: [] });
    vi.stubGlobal("fetch", fetchMock);

    await listarNaoAptos();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/admin/nao-aptos");
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
  });

  it("busca por CPF via POST /api/admin/nao-aptos/busca com JSON e nunca na URL", async () => {
    const fetchMock = responderJson({ sucesso: true, total: 0, nao_aptos: [] });
    vi.stubGlobal("fetch", fetchMock);

    await listarNaoAptos({ cpf: "52998224725" });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/admin/nao-aptos/busca");
    expect(url).not.toContain("52998224725");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ cpf: "52998224725" });
  });

  it("busca por telefone via POST /api/admin/nao-aptos/busca com JSON e nunca na URL", async () => {
    const fetchMock = responderJson({ sucesso: true, total: 0, nao_aptos: [] });
    vi.stubGlobal("fetch", fetchMock);

    await listarNaoAptos({ telefone: "41999998888" });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/admin/nao-aptos/busca");
    expect(url).not.toContain("41999998888");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ telefone: "41999998888" });
  });

  it("busca por nome (q) via POST /api/admin/nao-aptos/busca com JSON", async () => {
    const fetchMock = responderJson({ sucesso: true, total: 0, nao_aptos: [] });
    vi.stubGlobal("fetch", fetchMock);

    await listarNaoAptos({ q: "Maria" });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/admin/nao-aptos/busca");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ q: "Maria" });
  });
});
