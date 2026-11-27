import { useEffect, useState } from "react";
import type { Animal } from "../types";
import { formatarMicrochip } from "../utils/microchip";
import { Botao } from "./Botao";
import { Dialogo } from "./Dialogo";
import { Aviso, Carregando } from "./Estados";
import { FotoAnimal } from "./FotoAnimal";
import { IconeImprimir, IconePata } from "./Icones";

/** Campos opcionais que entram na ficha em checkpoints seguintes (ex.: microchip no CP-04). */
type AnimalComExtras = Animal & {
  numero_microchip?: string | null;
};

/** Monta a URL interna da ficha do animal para o QR code da placa da baia (zero dado pessoal). */
export function montarUrlFichaAnimal(animalId: number, origem?: string): string {
  const base = (origem ?? (typeof window !== "undefined" ? window.location.origin : "")).replace(/\/+$/, "");
  return `${base}/animais/${animalId}`;
}

/**
 * Carrega a biblioteca `qrcode` sob demanda (chunk lazy separado) e devolve uma data URL SVG
 * nítida para tela e impressão em papel A6, sem usar innerHTML.
 */
export async function gerarDataUrlQrCode(conteudo: string): Promise<string> {
  const QRCode = await import("qrcode");
  const svg = await QRCode.toString(conteudo, {
    type: "svg",
    margin: 1,
    width: 240,
    errorCorrectionLevel: "M",
    color: {
      dark: "#1f2a24",
      light: "#ffffff",
    },
  });
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

interface PropsDialogoEtiquetaBaia {
  animal: AnimalComExtras;
  aberto: boolean;
  aoFechar: () => void;
}

/**
 * Diálogo com a placa da baia em formato A6 retrato (105 mm × 148 mm) e QR code da ficha.
 * A biblioteca `qrcode` só é baixada quando este diálogo é aberto.
 */
export default function DialogoEtiquetaBaia({ animal, aberto, aoFechar }: PropsDialogoEtiquetaBaia) {
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [erroQr, setErroQr] = useState<string | null>(null);

  const urlFicha = montarUrlFichaAnimal(animal.id);
  const microchipFormatado = animal.numero_microchip ? formatarMicrochip(animal.numero_microchip) : "";
  const resumoFisico = [animal.sexo, animal.porte, animal.raca, animal.pelagem].filter(Boolean).join(" · ");

  useEffect(() => {
    if (!aberto) return;
    let ativo = true;
    setQrDataUrl(null);
    setErroQr(null);

    gerarDataUrlQrCode(urlFicha)
      .then((src) => {
        if (ativo) setQrDataUrl(src);
      })
      .catch(() => {
        if (ativo) setErroQr("Não foi possível gerar o QR code agora. Tente novamente.");
      });

    return () => {
      ativo = false;
    };
  }, [aberto, urlFicha]);

  return (
    <Dialogo
      aberto={aberto}
      aoFechar={aoFechar}
      titulo="Placa da baia (A6)"
      rodape={
        <div className="nao-imprimir flex flex-wrap justify-end gap-2">
          <Botao variante="secundario" onClick={aoFechar}>
            Fechar
          </Botao>
          <Botao icone={<IconeImprimir />} onClick={() => window.print()} disabled={!qrDataUrl}>
            Imprimir placa (A6)
          </Botao>
        </div>
      }
    >
      <p className="nao-imprimir mb-3 text-sm text-tinta-700">
        Formato pronto para papel A6 retrato (105 × 148 mm). Na janela de impressão, só a placa abaixo será impressa.
      </p>

      <section
        aria-label={`Placa da baia de ${animal.nome}`}
        className="area-impressao-etiqueta mx-auto flex w-full max-w-sm flex-col items-center gap-3 rounded-2xl border-2 border-mata-700 bg-white p-4 text-center text-tinta-900"
      >
        <div className="flex w-full items-center justify-between gap-2 border-b border-creme-200 pb-2">
          <div className="flex items-center gap-1.5 text-left">
            <span className="grid size-7 shrink-0 place-items-center rounded-lg bg-mata-700 text-white" aria-hidden="true">
              <IconePata tamanho={16} />
            </span>
            <span className="text-sm font-extrabold tracking-tight text-mata-800">ONG GAPAR</span>
          </div>
          <span className="rounded-full bg-mata-50 px-2.5 py-0.5 text-xs font-extrabold text-mata-800">
            {animal.localizacao_baia?.trim() || "Baia não informada"}
          </span>
        </div>

        <div className="flex w-full items-center gap-3 text-left">
          <FotoAnimal
            nome={animal.nome}
            fotoUrl={animal.foto_url}
            carregamento="eager"
            largura={80}
            altura={80}
            className="size-20 shrink-0 rounded-xl"
          />
          <div className="min-w-0 flex-1">
            <h3 className="text-2xl leading-tight font-extrabold break-words text-tinta-900">{animal.nome}</h3>
            {resumoFisico && <p className="mt-0.5 text-sm font-semibold text-tinta-700">{resumoFisico}</p>}
            {microchipFormatado && (
              <p className="mt-1 font-mono text-xs font-bold text-mata-800">Chip {microchipFormatado}</p>
            )}
          </div>
        </div>

        {animal.cuidados_especiais?.trim() && (
          <div className="w-full rounded-xl border border-barro-200 bg-barro-50 px-3 py-2 text-left">
            <p className="text-xs font-extrabold tracking-wide text-barro-900 uppercase">Cuidados especiais</p>
            <p className="mt-0.5 text-sm font-semibold break-words text-tinta-900">{animal.cuidados_especiais.trim()}</p>
          </div>
        )}

        <div className="flex flex-col items-center gap-1.5 pt-1">
          {erroQr ? (
            <Aviso tipo="perigo">{erroQr}</Aviso>
          ) : !qrDataUrl ? (
            <div className="grid size-44 place-items-center rounded-xl border border-creme-200 bg-creme-50">
              <Carregando texto="Gerando QR code..." />
            </div>
          ) : (
            <img
              src={qrDataUrl}
              alt={`QR code para abrir a ficha de ${animal.nome}`}
              width={176}
              height={176}
              className="size-44 rounded-xl border border-creme-200 bg-white p-1.5"
            />
          )}
          <p className="text-xs font-bold text-tinta-700">Aponte a câmera para abrir a ficha completa</p>
          <p className="font-mono text-[11px] break-all text-tinta-500">Ficha #{animal.id}</p>
        </div>
      </section>
    </Dialogo>
  );
}
