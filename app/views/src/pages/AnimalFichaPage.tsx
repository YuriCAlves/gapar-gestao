import { lazy, Suspense, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { buscarFicha } from "../api/animais";
import { Abas, PainelDaAba } from "../components/Abas";
import type { DefinicaoDeAba } from "../components/Abas";
import { Botao } from "../components/Botao";
import { Aviso, Esqueleto, EstadoErro } from "../components/Estados";
import { FotoAnimal } from "../components/FotoAnimal";
import { IconeQrCode, IconeVoltar } from "../components/Icones";
import { IndicadoresDoAnimal, SeloDeStatus } from "../components/Selos";
import { RequerFlag } from "../contexts/FlagsContext";
import { useCarregar } from "../hooks/useCarregar";
import { formatarData } from "../utils/datas";
import { AbaAdocao } from "./ficha/AbaAdocao";
import { AbaDados } from "./ficha/AbaDados";
import { AbaMedicacoes } from "./ficha/AbaMedicacoes";
import { AbaProntuario } from "./ficha/AbaProntuario";
import { AbaSaude } from "./ficha/AbaSaude";

const DialogoEtiquetaBaia = lazy(() => import("../components/DialogoEtiquetaBaia"));

type IdDaAba = "dados" | "saude" | "prontuario" | "medicacoes" | "adocao";
const ABAS_VALIDAS: IdDaAba[] = ["dados", "saude", "prontuario", "medicacoes", "adocao"];

export default function AnimalFichaPage() {
  const { id } = useParams();
  const animalId = Number(id);
  const [parametros, setParametros] = useSearchParams();
  const pedida = parametros.get("aba") as IdDaAba | null;
  const aba: IdDaAba = pedida && ABAS_VALIDAS.includes(pedida) ? pedida : "dados";
  const [etiquetaAberta, setEtiquetaAberta] = useState(false);

  const ficha = useCarregar((sinal) => buscarFicha(animalId, sinal), [animalId]);

  if (!Number.isInteger(animalId) || animalId <= 0) {
    return <EstadoErro mensagem="Este endereço não corresponde a nenhum animal." />;
  }

  const dados = ficha.dados;

  if (!dados) {
    return ficha.erro ? (
      <div className="space-y-4">
        <Link to="/animais" className="inline-flex min-h-11 items-center gap-2 font-bold text-mata-800">
          <IconeVoltar /> Voltar para Animais
        </Link>
        <EstadoErro mensagem={ficha.erro} aoTentarDeNovo={ficha.recarregar} />
      </div>
    ) : (
      <div className="space-y-4" aria-busy="true">
        <span className="sr-only" role="status">
          Carregando a ficha...
        </span>
        <Esqueleto className="h-40" />
        <Esqueleto className="h-12" />
        <Esqueleto className="h-64" />
      </div>
    );
  }

  const { animal } = dados;
  const congelado = dados.congelado || animal.congelado;

  const abas: DefinicaoDeAba<IdDaAba>[] = [
    { id: "dados", rotulo: "Dados gerais" },
    { id: "saude", rotulo: "Vacinas" },
    { id: "prontuario", rotulo: "Prontuário" },
    { id: "medicacoes", rotulo: "Medicações" },
    { id: "adocao", rotulo: "Adoção" },
  ];

  const props = { ficha: dados, congelado, aoAtualizar: ficha.recarregar };

  return (
    <div className="mx-auto max-w-4xl">
      <Link to="/animais" className="-ml-1 mb-2 inline-flex min-h-11 items-center gap-2 font-bold text-mata-800 hover:underline">
        <IconeVoltar /> Animais
      </Link>

      <header className="flex gap-4 rounded-cartao bg-white p-3 shadow-cartao sm:p-4">
        <FotoAnimal nome={animal.nome} fotoUrl={animal.foto_url} carregamento="eager" className="size-24 shrink-0 rounded-2xl sm:size-36" />
        <div className="flex min-w-0 flex-col gap-1.5">
          <h1 className="text-2xl break-words sm:text-3xl">{animal.nome}</h1>
          <p className="text-tinta-700">
            {[animal.sexo, animal.porte, animal.idade_estimada].filter(Boolean).join(" · ")}
          </p>
          <span>
            <SeloDeStatus status={animal.status_operacional} />
          </span>
          <IndicadoresDoAnimal animal={animal} />
          <p className="text-tinta-700">No GAPAR desde {formatarData(animal.data_entrada)}</p>
          <RequerFlag flag="microchip">
            <div className="pt-1">
              <Botao
                variante="secundario"
                tamanho="compacto"
                icone={<IconeQrCode tamanho={18} />}
                onClick={() => setEtiquetaAberta(true)}
              >
                Placa da baia (QR)
              </Botao>
            </div>
          </RequerFlag>
        </div>
      </header>

      {etiquetaAberta && (
        <Suspense fallback={null}>
          <DialogoEtiquetaBaia
            animal={animal}
            aberto={etiquetaAberta}
            aoFechar={() => setEtiquetaAberta(false)}
          />
        </Suspense>
      )}

      {congelado && (
        <Aviso tipo="preservado" titulo="Histórico preservado" className="mt-4">
          {animal.status_operacional === "adotado"
            ? `${animal.nome} foi adotado. A ficha fica guardada para consulta, mas não pode mais ser alterada.`
            : `A ficha de ${animal.nome} fica guardada para consulta, mas não pode mais ser alterada.`}
        </Aviso>
      )}

      <div className="mt-5">
        <Abas
          prefixo="ficha"
          rotulo={`Ficha de ${animal.nome}`}
          abas={abas}
          ativa={aba}
          aoMudar={(nova) =>
            setParametros(
              (atuais) => {
                const novos = new URLSearchParams(atuais);
                novos.set("aba", nova);
                return novos;
              },
              { replace: true },
            )
          }
        />
        <PainelDaAba prefixo="ficha" id={aba}>
          {aba === "dados" && <AbaDados {...props} />}
          {aba === "saude" && <AbaSaude {...props} />}
          {aba === "prontuario" && <AbaProntuario {...props} />}
          {aba === "medicacoes" && <AbaMedicacoes {...props} />}
          {aba === "adocao" && <AbaAdocao {...props} />}
        </PainelDaAba>
      </div>
    </div>
  );
}
