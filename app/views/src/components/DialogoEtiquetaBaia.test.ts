import { describe, expect, it } from "vitest";
import { gerarDataUrlQrCode, montarUrlFichaAnimal } from "./DialogoEtiquetaBaia";

describe("DialogoEtiquetaBaia (C3 — placa da baia com QR code)", () => {
  it("monta a URL da ficha apenas com o identificador do animal, sem dados pessoais", () => {
    expect(montarUrlFichaAnimal(42, "https://gapar.vercel.app")).toBe("https://gapar.vercel.app/animais/42");
    expect(montarUrlFichaAnimal(7, "https://gapar.vercel.app/")).toBe("https://gapar.vercel.app/animais/7");
  });

  it("carrega qrcode sob demanda e gera uma data URL SVG válida", async () => {
    const dataUrl = await gerarDataUrlQrCode("https://gapar.vercel.app/animais/42");
    expect(dataUrl.startsWith("data:image/svg+xml;charset=utf-8,")).toBe(true);
    const svg = decodeURIComponent(dataUrl.replace("data:image/svg+xml;charset=utf-8,", ""));
    expect(svg).toContain("<svg");
    expect(svg).toContain("</svg>");
  });
});
