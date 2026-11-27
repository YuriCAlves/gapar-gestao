import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { foiCancelada, textoDoErro } from "../../api/http";
import { obterAnimalPublico } from "../../api/vitrine";
import { classesDoBotao } from "../../components/Botao";
import { Aviso, Esqueleto, EstadoErro } from "../../components/Estados";
import { FotoAnimal } from "../../components/FotoAnimal";
import { IconeCoracao, IconeVoltar } from "../../components/Icones";
import { Selo } from "../../components/Selos";
import { useFlags } from "../../contexts/FlagsContext";
import type { AnimalPublico } from "../../types/contratos";
import { linkWhatsappAdocao } from "../../utils/whatsapp";

function IconeConversa() {
  return (
    <svg
      width={22}
      height={22}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className="shrink-0"
    >
      <path d="M20 11.5a8.5 8.5 0 0 1-12.5 7.5L4 20l1.1-3.4A8.5 8.5 0 1 1 20 11.5z" />
      <path d="M9.5 9.5c.3 1.7 2.3 3.7 4 4l1.2-1.1a.9.9 0 0 1 1-.1l1.3.6" />
    </svg>
  );
}

function EsqueletoDetalhe() {
  return (
    <div role="status" aria-busy="true" className="space-y-5">
      <span className="sr-only">Carregando detalhes do cão...</span>
      <Esqueleto className="h-11 w-44" />
      <div className="rounded-cartao border border-creme-200 bg-white p-4 shadow-cartao sm:p-6 lg:p-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="lg:col-span-6">
            <Esqueleto className="aspect-[4/3] w-full rounded-cartao" />
          </div>
          <div className="space-y-4 lg:col-span-6">
            <Esqueleto className="h-9 w-2/3" />
            <div className="flex flex-wrap gap-2">
              <Esqueleto className="h-7 w-24 rounded-full" />
              <Esqueleto className="h-7 w-20 rounded-full" />
              <Esqueleto className="h-7 w-24 rounded-full" />
            </div>
            <Esqueleto className="h-24 w-full rounded-2xl" />
            <Esqueleto className="h-20 w-full" />
            <Esqueleto className="h-14 w-full" />
          </div>
        </div>
      </div>
    </div>
  );
}

function JaEncontrouUmLar() {
  return (
    <section
      aria-labelledby="titulo-ja-adotado"
      className="mx-auto max-w-xl rounded-cartao border border-creme-200 bg-white px-5 py-10 text-center shadow-cartao sm:px-8 sm:py-12"
    >
      <span
        className="mx-auto mb-4 grid size-16 place-items-center rounded-full bg-mata-50 text-mata-700"
        aria-hidden="true"
      >
        <IconeCoracao tamanho={32} />
      </span>
      <h1 id="titulo-ja-adotado" className="text-2xl font-extrabold text-tinta-900 sm:text-3xl">
        Este cão já encontrou um lar
      </h1>
      <p className="mx-auto mt-3 max-w-md text-tinta-700">
        Que notícia boa! Ele não está mais disponível para adoção por aqui, mas outros amigos continuam esperando por uma família carinhosa.
      </p>
      <div className="mt-6">
        <Link to="/adote" className={classesDoBotao("primario", "normal", "w-full sm:w-auto")}>
          Ver outros cães disponíveis
        </Link>
      </div>
    </section>
  );
}

export default function VitrineAnimalPage() {
  const { slug } = useParams<{ slug: string }>();
  const { whatsappAdocao } = useFlags();

  const [animal, setAnimal] = useState<AnimalPublico | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    if (!slug) {
      setAnimal(null);
      setErro(null);
      setCarregando(false);
      return;
    }

    const controle = new AbortController();
    setCarregando(true);
    setErro(null);

    obterAnimalPublico(slug, controle.signal)
      .then((recebido) => {
        setAnimal(recebido);
        setCarregando(false);
      })
      .catch((causa) => {
        if (foiCancelada(causa)) return;
        setErro(textoDoErro(causa));
        setCarregando(false);
      });

    return () => controle.abort();
  }, [slug, tentativa]);

  if (carregando) {
    return <EsqueletoDetalhe />;
  }

  if (erro) {
    return (
      <div className="space-y-5">
        <Link
          to="/adote"
          className="inline-flex min-h-11 items-center gap-2 rounded-xl px-2 font-bold text-mata-800 hover:bg-mata-50"
        >
          <IconeVoltar tamanho={20} />
          <span>Voltar para a vitrine</span>
        </Link>
        <EstadoErro mensagem={erro} aoTentarDeNovo={() => setTentativa((n) => n + 1)} />
      </div>
    );
  }

  if (!animal) {
    return <JaEncontrouUmLar />;
  }

  const linkWhatsapp = linkWhatsappAdocao(whatsappAdocao, animal.nome);
  const descricao =
    animal.descricao_publica?.trim() ||
    "Este cão está recebendo todo o carinho da equipe da ONG GAPAR enquanto aguarda uma família responsável.";

  return (
    <article className="space-y-5" aria-labelledby="titulo-animal">
      <div>
        <Link
          to="/adote"
          className="inline-flex min-h-11 items-center gap-2 rounded-xl px-2 font-bold text-mata-800 hover:bg-mata-50"
        >
          <IconeVoltar tamanho={20} />
          <span>Voltar para a vitrine</span>
        </Link>
      </div>

      <div className="rounded-cartao border border-creme-200 bg-white p-4 shadow-cartao sm:p-6 lg:p-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-start">
          <div className="lg:col-span-6">
            <FotoAnimal
              nome={animal.nome}
              fotoUrl={animal.foto_url}
              carregamento="eager"
              largura={800}
              altura={600}
              className="aspect-[4/3] w-full rounded-cartao"
            />
          </div>

          <div className="min-w-0 space-y-5 lg:col-span-6">
            <header className="space-y-3">
              <h1 id="titulo-animal" className="text-2xl font-extrabold text-tinta-900 sm:text-3xl">
                {animal.nome}
              </h1>
              <div className="flex flex-wrap gap-2">
                <Selo cor="mata">Porte {animal.porte.toLowerCase()}</Selo>
                <Selo cor="ceu">{animal.sexo}</Selo>
                {animal.is_castrado && <Selo cor="pedra">Castrado</Selo>}
                {animal.is_idoso && <Selo cor="lilas">Idoso</Selo>}
              </div>
            </header>

            <dl className="grid grid-cols-1 gap-3 rounded-2xl border border-creme-200 bg-creme-50 p-4 sm:grid-cols-3">
              <div className="min-w-0">
                <dt className="text-sm font-bold text-tinta-500">Raça</dt>
                <dd className="mt-0.5 font-extrabold text-tinta-900">
                  {animal.raca?.trim() || "Sem raça definida"}
                </dd>
              </div>
              <div className="min-w-0">
                <dt className="text-sm font-bold text-tinta-500">Idade estimada</dt>
                <dd className="mt-0.5 font-extrabold text-tinta-900">
                  {animal.idade_estimada?.trim() || "Não informada"}
                </dd>
              </div>
              <div className="min-w-0">
                <dt className="text-sm font-bold text-tinta-500">Pelagem</dt>
                <dd className="mt-0.5 font-extrabold text-tinta-900">
                  {animal.pelagem?.trim() || "Não informada"}
                </dd>
              </div>
            </dl>

            <section className="space-y-2" aria-labelledby="sobre-o-cao">
              <h2 id="sobre-o-cao" className="text-lg font-extrabold text-tinta-900">
                Sobre {animal.nome}
              </h2>
              <p className="whitespace-pre-line leading-relaxed text-tinta-900">{descricao}</p>
            </section>

            {animal.candidaturas_pausadas && (
              <Aviso tipo="atencao" titulo="Candidaturas pausadas no momento">
                {linkWhatsapp
                  ? "As candidaturas pelo site estão temporariamente pausadas para este cão. Se quiser tirar dúvidas sobre a adoção, fale com a nossa equipe pelo WhatsApp."
                  : "As candidaturas para este cão estão temporariamente pausadas. Em breve traremos novidades por aqui."}
              </Aviso>
            )}

            {linkWhatsapp && (
              <div className="space-y-2 pt-1">
                <a
                  href={linkWhatsapp}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={classesDoBotao("primario", "grande", "w-full")}
                >
                  <IconeConversa />
                  <span>Quero adotar pelo WhatsApp</span>
                </a>
                <p className="text-center text-sm text-tinta-700">
                  Você vai conversar diretamente com a equipe da ONG GAPAR pelo WhatsApp.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}
