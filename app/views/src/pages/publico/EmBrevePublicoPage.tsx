import { Link } from "react-router-dom";
import { IconePata } from "../../components/Icones";

/**
 * Estado temporário exibido nas rotas públicas enquanto os módulos da ampliação
 * ainda estão sendo homologados atrás de feature flags.
 */
export default function EmBrevePublicoPage({ titulo = "Em breve" }: { titulo?: string }) {
  return (
    <section className="mx-auto flex max-w-md flex-col items-center rounded-cartao bg-white px-5 py-10 text-center shadow-cartao">
      <span className="grid size-16 place-items-center rounded-full bg-mata-50 text-mata-700" aria-hidden="true">
        <IconePata tamanho={32} />
      </span>
      <h1 className="mt-4 text-2xl font-extrabold text-tinta-900">{titulo}</h1>
      <p className="mt-2 text-tinta-700">
        Em breve esta página estará disponível para quem deseja adotar ou acompanhar um animal cuidado pela ONG GAPAR.
      </p>
      <Link
        to="/privacidade"
        className="mt-5 inline-flex min-h-11 items-center rounded-xl px-3 font-bold text-mata-800 underline underline-offset-4 hover:bg-mata-50"
      >
        Ler nossa Política de Privacidade
      </Link>
    </section>
  );
}
