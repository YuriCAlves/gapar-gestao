import { useEffect, useId, useRef, useState } from "react";
import { formatarTamanho, LIMITE_DE_ENVIO_BYTES, reduzirFoto } from "../utils/foto";
import { Botao } from "./Botao";
import { IconeCamera } from "./Icones";

interface PropsDoSeletor {
  foto: File | null;
  aoEscolher: (foto: File | null) => void;
  /** Foto atual (na edição), mostrada enquanto nenhuma nova é escolhida. */
  previaAtual?: string | null;
  desabilitado?: boolean;
}

/**
 * Escolha de foto com pré-visualização. Abre a câmera no celular. A imagem é reduzida no
 * aparelho antes do envio para gastar menos dados móveis.
 */
export function SeletorDeFoto({ foto, aoEscolher, previaAtual, desabilitado }: PropsDoSeletor) {
  const id = useId();
  const entrada = useRef<HTMLInputElement>(null);
  const [previa, setPrevia] = useState<string | null>(null);
  const [preparando, setPreparando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [tamanhoOriginal, setTamanhoOriginal] = useState<number | null>(null);

  useEffect(() => {
    if (!foto) {
      setPrevia(null);
      return;
    }
    const endereco = URL.createObjectURL(foto);
    setPrevia(endereco);
    return () => URL.revokeObjectURL(endereco);
  }, [foto]);

  async function aoSelecionar(arquivo: File | undefined) {
    if (!arquivo) return;
    setErro(null);
    setPreparando(true);
    try {
      const reduzida = await reduzirFoto(arquivo);
      if (reduzida.size > LIMITE_DE_ENVIO_BYTES) {
        setErro("A foto é grande demais. Escolha uma imagem de até 10 MB.");
        return;
      }
      setTamanhoOriginal(arquivo.size);
      aoEscolher(reduzida);
    } catch (causa) {
      setErro(causa instanceof Error ? causa.message : "Não foi possível usar esta imagem.");
    } finally {
      setPreparando(false);
      if (entrada.current) entrada.current.value = "";
    }
  }

  const imagem = previa ?? previaAtual ?? null;

  return (
    <div>
      <input
        ref={entrada}
        id={id}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        disabled={desabilitado || preparando}
        onChange={(e) => void aoSelecionar(e.target.files?.[0])}
        aria-describedby={`${id}-ajuda`}
      />
      {imagem ? (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <img src={imagem} alt="Pré-visualização da foto escolhida" className="aspect-[4/3] w-full rounded-cartao object-cover sm:w-56" />
          <div className="flex flex-col gap-2">
            {foto && (
              <p id={`${id}-ajuda`} className="text-tinta-700">
                Foto pronta: {formatarTamanho(foto.size)}
                {tamanhoOriginal && tamanhoOriginal > foto.size ? ` (era ${formatarTamanho(tamanhoOriginal)})` : ""}
              </p>
            )}
            {!foto && (
              <p id={`${id}-ajuda`} className="text-tinta-700">
                Foto atual
              </p>
            )}
            <Botao variante="secundario" ocupado={preparando} disabled={desabilitado} onClick={() => entrada.current?.click()} icone={<IconeCamera />}>
              Trocar foto
            </Botao>
            {foto && (
              <Botao variante="fantasma" onClick={() => aoEscolher(null)} disabled={desabilitado}>
                Remover a foto escolhida
              </Botao>
            )}
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => entrada.current?.click()}
          disabled={desabilitado || preparando}
          className="flex w-full flex-col items-center gap-2 rounded-cartao border-2 border-dashed border-mata-600 bg-mata-50 px-4 py-7 text-center hover:bg-mata-100"
        >
          <span className="grid size-14 place-items-center rounded-full bg-white text-mata-700" aria-hidden="true">
            {preparando ? "..." : <IconeCamera tamanho={28} />}
          </span>
          <span className="text-lg font-extrabold text-mata-800">{preparando ? "Preparando a foto..." : "Tirar ou escolher foto"}</span>
          <span id={`${id}-ajuda`} className="text-tinta-700">
            A foto é reduzida antes de enviar, para gastar pouca internet.
          </span>
        </button>
      )}
      {erro && (
        <p role="alert" className="mt-2 font-semibold text-perigo-700">
          {erro}
        </p>
      )}
    </div>
  );
}
