import { Link } from "react-router-dom";
import { classesDoBotao } from "../components/Botao";
import { IconePata } from "../components/Icones";

export default function NaoEncontradaPage({ publica = false }: { publica?: boolean }) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center py-12 text-center">
      <span className="grid size-20 place-items-center rounded-full bg-barro-100 text-barro-700" aria-hidden="true">
        <IconePata tamanho={40} />
      </span>
      <h1 className="mt-4 text-2xl">Página não encontrada</h1>
      <p className="mt-2">
        {publica
          ? "Este endereço não existe ou ainda não está disponível."
          : "O endereço aberto não existe ou mudou de lugar. Volte para o início e continue de lá."}
      </p>
      {publica ? (
        <Link to="/privacidade" className={classesDoBotao("secundario", "normal", "mt-6")}>
          Política de Privacidade
        </Link>
      ) : (
        <Link to="/hoje" className={classesDoBotao("primario", "normal", "mt-6")}>
          Ir para o início
        </Link>
      )}
    </div>
  );
}
