import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { listarAnimais } from "../api/animais";
import { foiCancelada, textoDoErro } from "../api/http";
import { Botao, classesDoBotao } from "../components/Botao";
import { CampoSelecao } from "../components/Campos";
import { Esqueleto, EstadoErro, EstadoVazio } from "../components/Estados";
import { FotoAnimal } from "../components/FotoAnimal";
import { IconeBusca, IconeFechar, IconeFiltro, IconeMais, IconePata } from "../components/Icones";
import { IndicadoresDoAnimal, SeloDeStatus } from "../components/Selos";
import type { Animal, FiltrosAnimais } from "../types";
import { rotuloDoStatus, TODOS_OS_STATUS } from "../utils/status";

const ESPERA_DA_BUSCA_MS = 350;

const CHAVES: (keyof FiltrosAnimais)[] = ["q", "status", "porte", "sexo", "castrado", "idoso", "cuidados"];

function filtrosDaUrl(parametros: URLSearchParams): FiltrosAnimais {
  const ler = (chave: string) => parametros.get(chave) ?? "";
  return {
    q: ler("q"),
    status: ler("status") as FiltrosAnimais["status"],
    porte: ler("porte") as FiltrosAnimais["porte"],
    sexo: ler("sexo") as FiltrosAnimais["sexo"],
    castrado: ler("castrado") as FiltrosAnimais["castrado"],
    idoso: ler("idoso") as FiltrosAnimais["idoso"],
    cuidados: ler("cuidados") as FiltrosAnimais["cuidados"],
  };
}

function CartaoDoAnimal({ animal }: { animal: Animal }) {
  const detalhes = [animal.sexo, animal.porte, animal.idade_estimada].filter(Boolean).join(" · ");
  return (
    <li>
      <Link
        to={`/animais/${animal.id}`}
        className="group flex h-full gap-3 rounded-cartao bg-white p-3 shadow-cartao transition-shadow hover:shadow-flutuante sm:flex-col sm:p-0"
      >
        <FotoAnimal
          nome={animal.nome}
          fotoUrl={animal.foto_url}
          className={`size-24 shrink-0 rounded-xl sm:aspect-[4/3] sm:h-auto sm:w-full sm:rounded-b-none sm:rounded-t-cartao ${animal.congelado ? "grayscale-[40%]" : ""}`}
        />
        <div className="flex min-w-0 flex-1 flex-col gap-1.5 sm:px-4 sm:pb-4">
          <p className="truncate text-lg font-extrabold text-tinta-900 group-hover:underline">{animal.nome}</p>
          <p className="text-tinta-700">{detalhes}</p>
          <span>
            <SeloDeStatus status={animal.status_operacional} curto />
          </span>
          <IndicadoresDoAnimal animal={animal} />
        </div>
      </Link>
    </li>
  );
}

export default function AnimaisPage() {
  const [parametros, setParametros] = useSearchParams();
  const filtros = filtrosDaUrl(parametros);
  const [textoBusca, setTextoBusca] = useState(filtros.q);
  const [mostrarFiltros, setMostrarFiltros] = useState(false);

  const [animais, setAnimais] = useState<Animal[]>([]);
  const [consulta, setConsulta] = useState({ chave: "", pagina: 1 });
  const [totalPaginas, setTotalPaginas] = useState(1);
  const [total, setTotal] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [tentativa, setTentativa] = useState(0);
  const sentinela = useRef<HTMLDivElement>(null);

  const chaveDosFiltros = CHAVES.map((c) => filtros[c]).join("|");

  function definirFiltro(chave: keyof FiltrosAnimais, valor: string) {
    setParametros(
      (atuais) => {
        const novos = new URLSearchParams(atuais);
        if (valor) novos.set(chave, valor);
        else novos.delete(chave);
        return novos;
      },
      { replace: true },
    );
  }

  // Busca por nome só depois de a pessoa parar de digitar
  useEffect(() => {
    if (textoBusca.trim() === filtros.q) return;
    const espera = window.setTimeout(() => definirFiltro("q", textoBusca.trim()), ESPERA_DA_BUSCA_MS);
    return () => window.clearTimeout(espera);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [textoBusca]);

  // Filtros mudaram: recomeça da primeira página (ajuste feito já na renderização,
  // para nunca buscar a página 2 de uma combinação nova de filtros)
  if (consulta.chave !== chaveDosFiltros) setConsulta({ chave: chaveDosFiltros, pagina: 1 });
  const pagina = consulta.chave === chaveDosFiltros ? consulta.pagina : 1;
  const setPagina = (atualizar: (p: number) => number) =>
    setConsulta((c) => ({ ...c, pagina: atualizar(c.pagina) }));

  useEffect(() => {
    if (consulta.chave !== chaveDosFiltros) return;
    const controle = new AbortController();
    setCarregando(true);
    setErro(null);
    listarAnimais(filtros, pagina, controle.signal)
      .then((resposta) => {
        setAnimais((atuais) => (pagina === 1 ? resposta.animais : [...atuais, ...resposta.animais.filter((a) => !atuais.some((b) => b.id === a.id))]));
        setTotalPaginas(resposta.total_paginas);
        setTotal(resposta.total_registros);
        setCarregando(false);
      })
      .catch((causa: unknown) => {
        if (foiCancelada(causa)) return;
        setErro(textoDoErro(causa));
        setCarregando(false);
      });
    return () => controle.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [consulta, tentativa]);

  const temMais = pagina < totalPaginas;

  // Carregamento progressivo: ao chegar perto do fim da lista, traz a próxima página (RNF03)
  useEffect(() => {
    const alvo = sentinela.current;
    if (!alvo || !temMais || carregando || erro) return;
    const observador = new IntersectionObserver(
      (entradas) => {
        if (entradas.some((e) => e.isIntersecting)) setPagina((p) => p + 1);
      },
      { rootMargin: "400px" },
    );
    observador.observe(alvo);
    return () => observador.disconnect();
  }, [temMais, carregando, erro]);

  const filtrosAtivos = CHAVES.filter((c) => c !== "q" && filtros[c]).length;

  function limparFiltros() {
    setTextoBusca("");
    setParametros(new URLSearchParams(), { replace: true });
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl">Animais</h1>
          <p className="mt-0.5 text-tinta-700" aria-live="polite">
            {carregando && pagina === 1 ? "Buscando..." : total === 1 ? "1 animal encontrado" : `${total} animais encontrados`}
          </p>
        </div>
        <Link to="/animais/novo" className={classesDoBotao("primario", "compacto")}>
          <IconeMais tamanho={20} />
          Novo resgate
        </Link>
      </div>

      <div className="sticky top-[4.1rem] z-30 -mx-4 bg-creme-50/95 px-4 pt-1 pb-3 backdrop-blur">
        <div className="flex gap-2">
          <div className="relative min-w-0 flex-1">
            <label htmlFor="busca-animais" className="sr-only">
              Buscar animal por nome
            </label>
            <IconeBusca className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-tinta-500" />
            <input
              id="busca-animais"
              type="search"
              value={textoBusca}
              onChange={(e) => setTextoBusca(e.target.value)}
              placeholder="Buscar por nome"
              autoComplete="off"
              enterKeyHint="search"
              className="block min-h-12 w-full rounded-xl border-2 border-contorno bg-white pr-3 pl-11 text-tinta-900 placeholder:text-tinta-500 focus:border-mata-700 focus:outline-none"
            />
          </div>
          <Botao
            variante={mostrarFiltros || filtrosAtivos ? "primario" : "secundario"}
            onClick={() => setMostrarFiltros((v) => !v)}
            aria-expanded={mostrarFiltros}
            aria-controls="painel-filtros"
            icone={<IconeFiltro />}
            className="shrink-0 px-3.5"
          >
            <span className="hidden min-[400px]:inline">Filtros</span>
            {filtrosAtivos > 0 && <span className="ml-0.5">({filtrosAtivos})</span>}
            <span className="sr-only min-[400px]:hidden">Filtros</span>
          </Botao>
        </div>

        {mostrarFiltros && (
          <div id="painel-filtros" className="mt-3 grid animate-entrar grid-cols-2 gap-3 rounded-cartao bg-white p-4 shadow-cartao sm:grid-cols-3 lg:grid-cols-6">
            <CampoSelecao rotulo="Situação" value={filtros.status} onChange={(e) => definirFiltro("status", e.target.value)} className="col-span-2 sm:col-span-1">
              <option value="">Todas</option>
              {TODOS_OS_STATUS.map((s) => (
                <option key={s} value={s}>
                  {rotuloDoStatus(s)}
                </option>
              ))}
            </CampoSelecao>
            <CampoSelecao rotulo="Porte" value={filtros.porte} onChange={(e) => definirFiltro("porte", e.target.value)}>
              <option value="">Todos</option>
              <option value="Pequeno">Pequeno</option>
              <option value="Médio">Médio</option>
              <option value="Grande">Grande</option>
            </CampoSelecao>
            <CampoSelecao rotulo="Sexo" value={filtros.sexo} onChange={(e) => definirFiltro("sexo", e.target.value)}>
              <option value="">Todos</option>
              <option value="Macho">Macho</option>
              <option value="Fêmea">Fêmea</option>
            </CampoSelecao>
            <CampoSelecao rotulo="Castrado" value={filtros.castrado} onChange={(e) => definirFiltro("castrado", e.target.value)}>
              <option value="">Tanto faz</option>
              <option value="sim">Sim</option>
              <option value="nao">Não</option>
            </CampoSelecao>
            <CampoSelecao rotulo="Idoso" value={filtros.idoso} onChange={(e) => definirFiltro("idoso", e.target.value)}>
              <option value="">Tanto faz</option>
              <option value="sim">Sim</option>
              <option value="nao">Não</option>
            </CampoSelecao>
            <CampoSelecao rotulo="Cuidados especiais" value={filtros.cuidados} onChange={(e) => definirFiltro("cuidados", e.target.value)} className="col-span-2 sm:col-span-1">
              <option value="">Tanto faz</option>
              <option value="sim">Precisa</option>
              <option value="nao">Não precisa</option>
            </CampoSelecao>
            {(filtrosAtivos > 0 || filtros.q) && (
              <Botao variante="fantasma" onClick={limparFiltros} icone={<IconeFechar tamanho={20} />} className="col-span-2 sm:col-span-3 lg:col-span-6 justify-self-start">
                Limpar busca e filtros
              </Botao>
            )}
          </div>
        )}
      </div>

      {erro && animais.length === 0 ? (
        <EstadoErro mensagem={erro} aoTentarDeNovo={() => setTentativa((t) => t + 1)} />
      ) : carregando && pagina === 1 && animais.length === 0 ? (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" aria-hidden="true">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <li key={i}>
              <Esqueleto className="h-32 sm:h-72" />
            </li>
          ))}
        </ul>
      ) : animais.length === 0 ? (
        <EstadoVazio
          icone={<IconePata tamanho={28} />}
          titulo={filtrosAtivos || filtros.q ? "Nenhum animal com essas características" : "Nenhum animal cadastrado ainda"}
          acao={
            filtrosAtivos || filtros.q ? (
              <Botao variante="secundario" onClick={limparFiltros}>
                Limpar busca e filtros
              </Botao>
            ) : (
              <Link to="/animais/novo" className={classesDoBotao("primario")}>
                Cadastrar resgate
              </Link>
            )
          }
        >
          {filtrosAtivos || filtros.q ? "Tente outro nome ou tire alguns filtros." : "Comece cadastrando o primeiro resgate."}
        </EstadoVazio>
      ) : (
        <>
          <ul className={`grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 ${carregando && pagina === 1 ? "opacity-60" : ""}`}>
            {animais.map((animal) => (
              <CartaoDoAnimal key={animal.id} animal={animal} />
            ))}
          </ul>
          <div ref={sentinela} className="mt-4 flex justify-center">
            {erro ? (
              <Botao variante="secundario" onClick={() => setTentativa((t) => t + 1)}>
                Não carregou o restante. Tentar de novo
              </Botao>
            ) : temMais ? (
              <Botao variante="secundario" ocupado={carregando} onClick={() => setPagina((p) => p + 1)}>
                Mostrar mais animais
              </Botao>
            ) : (
              total > 0 && <p className="py-2 text-tinta-700">Todos os animais foram mostrados.</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
