import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { cadastrarAnimal } from "../api/animais";
import { textoDoErro } from "../api/http";
import { Botao } from "../components/Botao";
import { Aviso } from "../components/Estados";
import { CamposDoAnimal, dadosDoAnimal, VALORES_INICIAIS, validarAnimal } from "../components/FormularioAnimal";
import type { ErrosDoAnimal, ValoresDoAnimal } from "../components/FormularioAnimal";
import { IconeCerto, IconeVoltar } from "../components/Icones";
import { SeletorDeFoto } from "../components/SeletorDeFoto";
import { useAvisos } from "../contexts/AvisosContext";
import { formatarData, hojeISO } from "../utils/datas";

export default function AnimalNovoPage() {
  const navegar = useNavigate();
  const { avisarSucesso } = useAvisos();
  const [valores, setValores] = useState<ValoresDoAnimal>(VALORES_INICIAIS);
  const [erros, setErros] = useState<ErrosDoAnimal>({});
  const [foto, setFoto] = useState<File | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [erroGeral, setErroGeral] = useState<string | null>(null);

  function mudar<K extends keyof ValoresDoAnimal>(campo: K, valor: ValoresDoAnimal[K]) {
    setValores((v) => ({ ...v, [campo]: valor }));
    if (erros[campo]) setErros((e) => ({ ...e, [campo]: undefined }));
  }

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    setErroGeral(null);
    const encontrados = validarAnimal(valores);
    setErros(encontrados);
    const primeiro = Object.keys(encontrados)[0];
    if (primeiro) {
      document.querySelector<HTMLElement>(`[name="${primeiro}"], [aria-invalid="true"]`)?.focus();
      return;
    }
    setSalvando(true);
    try {
      const animal = await cadastrarAnimal(dadosDoAnimal(valores), foto);
      avisarSucesso(`${animal.nome} foi cadastrado. Bem-vindo ao GAPAR!`);
      navegar(`/animais/${animal.id}`, { replace: true });
    } catch (causa) {
      setErroGeral(textoDoErro(causa));
      setSalvando(false);
    }
  }

  return (
    <form onSubmit={salvar} noValidate className="mx-auto max-w-2xl">
      <div className="mb-4 flex items-center gap-2">
        <Link to="/animais" className="-ml-2 grid size-11 place-items-center rounded-full hover:bg-creme-200" aria-label="Voltar para a lista de animais">
          <IconeVoltar />
        </Link>
        <div>
          <h1 className="text-2xl sm:text-3xl">Novo resgate</h1>
          <p className="text-tinta-700">
            Entra como <strong>em acolhimento</strong>, com data de hoje ({formatarData(hojeISO())}).
          </p>
        </div>
      </div>

      <div className="space-y-6">
        <section aria-label="Foto" className="rounded-cartao bg-white p-4 shadow-cartao">
          <h2 className="mb-3 text-lg">Foto</h2>
          <SeletorDeFoto foto={foto} aoEscolher={setFoto} desabilitado={salvando} />
        </section>

        <CamposDoAnimal valores={valores} erros={erros} aoMudar={mudar} />

        {erroGeral && (
          <Aviso tipo="perigo" titulo="O cadastro não foi salvo" anunciar>
            {erroGeral}
          </Aviso>
        )}
        {Object.values(erros).some(Boolean) && !erroGeral && (
          <Aviso tipo="perigo" anunciar>
            Confira os campos marcados em vermelho.
          </Aviso>
        )}
      </div>

      <div className="pb-segura sticky bottom-[calc(4.25rem+env(safe-area-inset-bottom))] z-30 -mx-4 mt-6 bg-creme-50/95 px-4 pt-3 backdrop-blur md:bottom-0">
        <Botao type="submit" tamanho="grande" larguraTotal ocupado={salvando} icone={<IconeCerto />}>
          {salvando ? "Salvando..." : "Salvar resgate"}
        </Botao>
      </div>
    </form>
  );
}
