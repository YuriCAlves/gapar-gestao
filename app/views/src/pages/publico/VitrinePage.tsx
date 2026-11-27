import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { foiCancelada, textoDoErro } from "../../api/http";
import { listarVitrine } from "../../api/vitrine";
import { Botao } from "../../components/Botao";
import { Aviso, Esqueleto, EstadoErro, EstadoVazio } from "../../components/Estados";
import { FotoAnimal } from "../../components/FotoAnimal";
import { IconeAvancar, IconePata } from "../../components/Icones";
import { Selo } from "../../components/Selos";
import type { AnimalPublico } from "../../types/contratos";

function textoResumo(animal: AnimalPublico): string {
  const partes = [`Porte ${animal.porte.toLowerCase()}`, animal.sexo];
  if (animal.idade_estimada?.trim()) partes.push(animal.idade_estimada.trim());
  return partes.join(" · ");
}

function GradeEsqueleto() {
  return (
    <div role="status" aria-busy="true" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <span className="sr-only">Carregando cães disponíveis para adoção...</span>
      {Array.from({ length: 6 }, (_, indice) => (
        <div
          key={indice}
          className="overflow-hidden rounded-cartao border border-creme-200 bg-white shadow-cartao"
        >
          <Esqueleto className="aspect-[4/3] w-full rounded-none" />
          <div className="space-y-3 p-4">
            <Esqueleto className="h-6 w-2/3" />
            <Esqueleto className="h-4 w-5/6" />
            <div className="flex gap-2 pt-1">
              <Esqueleto className="h-6 w-20 rounded-full" />
              <Esqueleto className="h-6 w-16 rounded-full" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function VitrinePage() {
  const [animais, setAnimais] = useState<AnimalPublico[]>([]);
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [total, setTotal] = useState(0);
  const [temMais, setTemMais] = useState(false);
  const [carregando, setCarregando] = useState(true);
  const [carregandoMais, setCarregandoMais] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [erroMais, setErroMais] = useState<string | null>(null);
  const [tentativa, setTentativa] = useState(0);

  const controleMaisRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controle = new AbortController();
    setCarregando(true);
    setErro(null);
    setErroMais(null);

    listarVitrine(1, controle.signal)
      .then((resposta) => {
        setAnimais(resposta.animais);
        setPaginaAtual(resposta.pagina);
        setTotal(resposta.total);
        setTemMais(resposta.tem_mais);
        setCarregando(false);
      })
      .catch((causa) => {
        if (foiCancelada(causa)) return;
        setErro(textoDoErro(causa));
        setCarregando(false);
      });

    return () => {
      controle.abort();
      controleMaisRef.current?.abort();
    };
  }, [tentativa]);

  const carregarMais = useCallback(() => {
    if (carregandoMais || !temMais) return;
    controleMaisRef.current?.abort();
    const controle = new AbortController();
    controleMaisRef.current = controle;

    setCarregandoMais(true);
    setErroMais(null);

    listarVitrine(paginaAtual + 1, controle.signal)
      .then((resposta) => {
        setAnimais((anteriores) => {
          const vistos = new Set(anteriores.map((item) => item.slug));
          const novos = resposta.animais.filter((item) => !vistos.has(item.slug));
          return [...anteriores, ...novos];
        });
        setPaginaAtual(resposta.pagina);
        setTotal(resposta.total);
        setTemMais(resposta.tem_mais);
        setCarregandoMais(false);
      })
      .catch((causa) => {
        if (foiCancelada(causa)) return;
        setErroMais(textoDoErro(causa));
        setCarregandoMais(false);
      });
  }, [carregandoMais, paginaAtual, temMais]);

  return (
    <section className="space-y-6" aria-labelledby="titulo-vitrine">
      <header className="space-y-2">
        <h1 id="titulo-vitrine" className="text-2xl font-extrabold text-tinta-900 sm:text-3xl">
          Cães esperando um lar
        </h1>
        <p className="max-w-2xl text-tinta-700">
          Conheça os cães acolhidos pela ONG GAPAR que estão prontos para fazer parte de uma família responsável.
        </p>
        {!carregando && !erro && total > 0 && (
          <p className="text-sm font-bold text-mata-800">
            {total === 1 ? "1 cão disponível para adoção" : `${total} cães disponíveis para adoção`}
          </p>
        )}
      </header>

      {carregando ? (
        <GradeEsqueleto />
      ) : erro && animais.length === 0 ? (
        <EstadoErro mensagem={erro} aoTentarDeNovo={() => setTentativa((n) => n + 1)} />
      ) : animais.length === 0 ? (
        <EstadoVazio icone={<IconePata tamanho={28} />} titulo="Nenhum cão disponível no momento">
          <p>Assim que novos cães estiverem prontos para adoção, eles aparecerão por aqui.</p>
        </EstadoVazio>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {animais.map((animal) => (
              <article key={animal.slug} className="min-w-0">
                <Link
                  to={`/adote/${animal.slug}`}
                  className="group flex h-full flex-col overflow-hidden rounded-cartao border border-creme-200 bg-white shadow-cartao transition-transform hover:-translate-y-0.5 hover:border-mata-200"
                >
                  <FotoAnimal
                    nome={animal.nome}
                    fotoUrl={animal.foto_url}
                    carregamento="lazy"
                    largura={400}
                    altura={300}
                    className="aspect-[4/3] w-full"
                  />
                  <div className="flex flex-1 flex-col gap-2.5 p-4">
                    <div className="space-y-1">
                      <h2 className="text-xl font-extrabold text-tinta-900 group-hover:text-mata-800">
                        {animal.nome}
                      </h2>
                      <p className="text-base text-tinta-700">{textoResumo(animal)}</p>
                    </div>

                    {(animal.is_castrado || animal.is_idoso) && (
                      <div className="flex flex-wrap gap-1.5">
                        {animal.is_castrado && <Selo cor="pedra">Castrado</Selo>}
                        {animal.is_idoso && <Selo cor="lilas">Idoso</Selo>}
                      </div>
                    )}

                    <div className="mt-auto flex min-h-11 items-center justify-between pt-1 text-base font-bold text-mata-800">
                      <span>Conhecer história</span>
                      <IconeAvancar tamanho={20} className="shrink-0 transition-transform group-hover:translate-x-0.5" />
                    </div>
                  </div>
                </Link>
              </article>
            ))}
          </div>

          {erroMais && (
            <Aviso tipo="perigo" anunciar>
              {erroMais}
            </Aviso>
          )}

          {temMais && (
            <div className="flex justify-center pt-2">
              <Botao
                variante="secundario"
                tamanho="normal"
                ocupado={carregandoMais}
                onClick={carregarMais}
                className="min-h-12 w-full sm:w-auto sm:min-w-60"
              >
                Carregar mais
              </Botao>
            </div>
          )}
        </>
      )}
    </section>
  );
}
