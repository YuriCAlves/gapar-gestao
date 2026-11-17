// Fotos dos animais: endereço de exibição e redução no aparelho antes do envio.

/** O servidor recusa requisições acima de 10 MB. */
export const LIMITE_DE_ENVIO_BYTES = 10 * 1024 * 1024;
const LADO_MAIOR_PX = 1600;
const QUALIDADE_JPEG = 0.82;

/**
 * foto_url pode ser um caminho do próprio servidor ("/static/uploads/x.jpg") ou um endereço
 * completo ("https://..."). Devolve null quando não há foto utilizável.
 */
export function enderecoDaFoto(fotoUrl: string | null | undefined): string | null {
  const valor = (fotoUrl ?? "").trim();
  if (!valor) return null;
  if (/^https?:\/\//i.test(valor) || valor.startsWith("data:") || valor.startsWith("blob:")) return valor;
  if (valor.startsWith("//")) return `https:${valor}`;
  return valor.startsWith("/") ? valor : `/${valor}`;
}

/** Calcula o tamanho final mantendo a proporção, sem nunca ampliar. */
export function calcularDimensoes(
  largura: number,
  altura: number,
  ladoMaior: number = LADO_MAIOR_PX,
): { largura: number; altura: number } {
  const maior = Math.max(largura, altura);
  if (maior <= ladoMaior || maior === 0) return { largura, altura };
  const fator = ladoMaior / maior;
  return {
    largura: Math.max(1, Math.round(largura * fator)),
    altura: Math.max(1, Math.round(altura * fator)),
  };
}

interface ImagemCarregada {
  fonte: CanvasImageSource;
  largura: number;
  altura: number;
  liberar: () => void;
}

async function carregarImagem(arquivo: File): Promise<ImagemCarregada> {
  if ("createImageBitmap" in window) {
    try {
      // "from-image" respeita a rotação gravada pela câmera do celular
      const bitmap = await createImageBitmap(arquivo, { imageOrientation: "from-image" });
      return { fonte: bitmap, largura: bitmap.width, altura: bitmap.height, liberar: () => bitmap.close() };
    } catch {
      // segue para o carregamento tradicional
    }
  }
  const endereco = URL.createObjectURL(arquivo);
  try {
    const imagem = new Image();
    imagem.src = endereco;
    await imagem.decode();
    return {
      fonte: imagem,
      largura: imagem.naturalWidth,
      altura: imagem.naturalHeight,
      liberar: () => URL.revokeObjectURL(endereco),
    };
  } catch (causa) {
    URL.revokeObjectURL(endereco);
    throw causa;
  }
}

/**
 * Reduz a foto para no máximo 1600 px no lado maior, em JPEG, para gastar menos dados móveis.
 * Se o aparelho não conseguir processar a imagem, devolve o arquivo original (o servidor
 * comprime de qualquer forma). Lança erro apenas quando o arquivo não é uma imagem.
 */
export async function reduzirFoto(arquivo: File): Promise<File> {
  if (!arquivo.type.startsWith("image/")) {
    throw new Error("Escolha um arquivo de imagem (foto).");
  }

  let imagem: ImagemCarregada;
  try {
    imagem = await carregarImagem(arquivo);
  } catch {
    return arquivo;
  }

  try {
    const { largura, altura } = calcularDimensoes(imagem.largura, imagem.altura);
    const tela = document.createElement("canvas");
    tela.width = largura;
    tela.height = altura;
    const contexto = tela.getContext("2d");
    if (!contexto) return arquivo;
    // Fundo branco para imagens com transparência (PNG), já que o destino é JPEG
    contexto.fillStyle = "#ffffff";
    contexto.fillRect(0, 0, largura, altura);
    contexto.drawImage(imagem.fonte, 0, 0, largura, altura);

    const blob = await new Promise<Blob | null>((resolver) =>
      tela.toBlob(resolver, "image/jpeg", QUALIDADE_JPEG),
    );
    if (!blob) return arquivo;
    // Se a "redução" ficou maior que o original já pequeno, mantém o original
    if (blob.size >= arquivo.size && arquivo.type === "image/jpeg") return arquivo;

    const nome = arquivo.name.replace(/\.[^.]+$/, "") || "foto";
    return new File([blob], `${nome}.jpg`, { type: "image/jpeg" });
  } finally {
    imagem.liberar();
  }
}

/** "1,4 MB", "320 KB" */
export function formatarTamanho(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1).replace(".", ",")} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}
