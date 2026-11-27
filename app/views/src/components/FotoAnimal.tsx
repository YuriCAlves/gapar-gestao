import { useEffect, useState } from "react";
import { enderecoDaFoto } from "../utils/foto";

const PALETAS = [
  { fundo: "#d6ead9", orelha: "#2a7048", rosto: "#b0d4b7", focinho: "#ecf5ee" },
  { fundo: "#f8dfcf", orelha: "#94421f", rosto: "#f0c3a8", focinho: "#fcf0e8" },
  { fundo: "#f9e7b0", orelha: "#7a5a12", rosto: "#f3d27a", focinho: "#fdf4d9" },
  { fundo: "#d3e2f4", orelha: "#1f4470", rosto: "#a9c5e6", focinho: "#e8f0f9" },
] as const;

function paletaDoNome(nome: string) {
  let soma = 0;
  for (const letra of nome) soma += letra.codePointAt(0) ?? 0;
  return PALETAS[soma % PALETAS.length];
}

/** Ilustração usada quando o animal ainda não tem foto (ou a foto não carregou). */
function SemFoto({ nome }: { nome: string }) {
  const cores = paletaDoNome(nome);
  return (
    <svg
      viewBox="0 0 120 120"
      preserveAspectRatio="xMidYMid slice"
      role="img"
      aria-label={`${nome} ainda não tem foto`}
      className="size-full"
    >
      <rect width="120" height="120" fill={cores.fundo} />
      <path d="M37 36c-13 1-21 15-18 35 1.500 9 10 9.500 13 1l8-27z" fill={cores.orelha} />
      <path d="M83 36c13 1 21 15 18 35-1.500 9-10 9.500-13 1l-8-27z" fill={cores.orelha} />
      <ellipse cx="60" cy="62" rx="27" ry="30" fill={cores.rosto} />
      <ellipse cx="60" cy="77" rx="15" ry="12.500" fill={cores.focinho} />
      <ellipse cx="60" cy="70.500" rx="5.500" ry="4" fill="#1f2a24" />
      <circle cx="48.500" cy="56" r="3.300" fill="#1f2a24" />
      <circle cx="71.500" cy="56" r="3.300" fill="#1f2a24" />
      <path
        d="M60 74.500v5c-2 4-7.500 4-8.500.500M60 79.500c2 4 7.500 4 8.500.500"
        fill="none"
        stroke="#1f2a24"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

interface PropsDaFoto {
  nome: string;
  fotoUrl: string | null | undefined;
  className?: string;
  /** "eager" para a foto principal da ficha; nas listas as fotos carregam sob demanda. */
  carregamento?: "lazy" | "eager";
  largura?: number;
  altura?: number;
}

export function FotoAnimal({ nome, fotoUrl, className = "", carregamento = "lazy", largura, altura }: PropsDaFoto) {
  const endereco = enderecoDaFoto(fotoUrl);
  const [falhou, setFalhou] = useState(false);

  useEffect(() => setFalhou(false), [endereco]);

  return (
    <div className={`overflow-hidden bg-creme-200 ${className}`}>
      {endereco && !falhou ? (
        <img
          src={endereco}
          alt={`Foto de ${nome}`}
          width={largura}
          height={altura}
          loading={carregamento}
          decoding="async"
          onError={() => setFalhou(true)}
          className="size-full object-cover"
        />
      ) : (
        <SemFoto nome={nome} />
      )}
    </div>
  );
}
