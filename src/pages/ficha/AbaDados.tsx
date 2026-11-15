import { useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { alterarStatus, atualizarAnimal, enviarFoto, excluirAnimal } from "../../api/animais";
import { textoDoErro } from "../../api/http";
import { Botao } from "../../components/Botao";
import { CampoSelecao } from "../../components/Campos";
import { Confirmacao, Dialogo } from "../../components/Dialogo";
import { Aviso } from "../../components/Estados";
import { CamposDoAnimal, dadosDoAnimal, validarAnimal, valoresDoAnimal } from "../../components/FormularioAnimal";
import type { ErrosDoAnimal, ValoresDoAnimal } from "../../components/FormularioAnimal";
import { IconeCamera, IconeLapis, IconeLixeira } from "../../components/Icones";
import { SeletorDeFoto } from "../../components/SeletorDeFoto";
import { useAuth } from "../../contexts/AuthContext";
import { useAvisos } from "../../contexts/AvisosContext";
import type { StatusAnimal } from "../../types";
import { formatarData } from "../../utils/datas";
import { enderecoDaFoto } from "../../utils/foto";
import { rotuloDoStatus, statusDisponiveisParaTroca } from "../../utils/status";
import type { PropsDaAba } from "./tipos";

function Linha({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <div className="py-2.5 sm:grid sm:grid-cols-3 sm:gap-4">
      <dt className="font-bold text-tinta-900">{rotulo}</dt>
      <dd className="break-words text-tinta-700 sm:col-span-2">{children || "—"}</dd>
    </div>
  );
}

const simNao = (v: boolean) => (v ? "Sim" : "Não");

export function AbaDados({ ficha, congelado, aoAtualizar }: PropsDaAba) {
  const { animal } = ficha;
  const { ehAdministradora } = useAuth();
  const { avisarSucesso, avisarErro } = useAvisos();
  const navegar = useNavigate();

  const [editando, setEditando] = useState(false);
  const [valores, setValores] = useState<ValoresDoAnimal>(() => valoresDoAnimal(animal));
  const [erros, setErros] = useState<ErrosDoAnimal>({});
  const [salvando, setSalvando] = useState(false);
  const [erroEdicao, setErroEdicao] = useState<string | null>(null);

  const [trocandoFoto, setTrocandoFoto] = useState(false);
  const [novaFoto, setNovaFoto] = useState<File | null>(null);
  const [enviandoFoto, setEnviandoFoto] = useState(false);

  const opcoesDeStatus = statusDisponiveisParaTroca(animal.status_operacional);
  const [novoStatus, setNovoStatus] = useState<StatusAnimal | "">("");
  const [confirmarStatus, setConfirmarStatus] = useState<StatusAnimal | null>(null);
  const [mudandoStatus, setMudandoStatus] = useState(false);

  const [confirmarExclusao, setConfirmarExclusao] = useState(false);
  const [excluindo, setExcluindo] = useState(false);

  function abrirEdicao() {
    setValores(valoresDoAnimal(animal));
    setErros({});
    setErroEdicao(null);
    setEditando(true);
  }

  async function salvarEdicao(evento: FormEvent) {
    evento.preventDefault();
    const encontrados = validarAnimal(valores);
    setErros(encontrados);
    if (Object.keys(encontrados).length) {
      setErroEdicao("Confira os campos marcados em vermelho.");
      return;
    }
    setSalvando(true);
    setErroEdicao(null);
    try {
      await atualizarAnimal(animal.id, dadosDoAnimal(valores));
      avisarSucesso("Dados atualizados.");
      setEditando(false);
      aoAtualizar();
    } catch (causa) {
      setErroEdicao(textoDoErro(causa));
    } finally {
      setSalvando(false);
    }
  }

  async function salvarFoto() {
    if (!novaFoto) return;
    setEnviandoFoto(true);
    try {
      await enviarFoto(animal.id, novaFoto);
      avisarSucesso("Foto atualizada.");
      setTrocandoFoto(false);
      setNovaFoto(null);
      aoAtualizar();
    } catch (causa) {
      avisarErro(textoDoErro(causa));
    } finally {
      setEnviandoFoto(false);
    }
  }

  async function aplicarStatus(status: StatusAnimal) {
    setMudandoStatus(true);
    try {
      await alterarStatus(animal.id, status);
      avisarSucesso(`Situação alterada para "${rotuloDoStatus(status)}".`);
      setConfirmarStatus(null);
      setNovoStatus("");
      aoAtualizar();
    } catch (causa) {
      avisarErro(textoDoErro(causa));
    } finally {
      setMudandoStatus(false);
    }
  }

  async function excluir() {
    setExcluindo(true);
    try {
      await excluirAnimal(animal.id);
      avisarSucesso(`${animal.nome} foi retirado da lista de animais.`);
      navegar("/animais", { replace: true });
    } catch (causa) {
      avisarErro(textoDoErro(causa));
      setExcluindo(false);
      setConfirmarExclusao(false);
    }
  }

  return (
    <div className="space-y-5">
      {!congelado && (
        <div className="flex flex-wrap gap-2">
          <Botao icone={<IconeLapis />} onClick={abrirEdicao}>
            Editar dados
          </Botao>
          <Botao variante="secundario" icone={<IconeCamera />} onClick={() => setTrocandoFoto(true)}>
            {animal.foto_url ? "Trocar foto" : "Adicionar foto"}
          </Botao>
        </div>
      )}

      {!congelado && (
        <section className="rounded-cartao bg-white p-4 shadow-cartao" aria-labelledby="titulo-situacao">
          <h2 id="titulo-situacao" className="text-lg">
            Situação
          </h2>
          <p className="mt-1 mb-3 text-tinta-700">
            Hoje: <strong>{rotuloDoStatus(animal.status_operacional)}</strong>. Para marcar como adotado, use a aba Adoção.
          </p>
          <form
            className="flex flex-col gap-3 sm:flex-row sm:items-end"
            onSubmit={(e) => {
              e.preventDefault();
              if (novoStatus) setConfirmarStatus(novoStatus);
            }}
          >
            <CampoSelecao rotulo="Mudar para" value={novoStatus} onChange={(e) => setNovoStatus(e.target.value as StatusAnimal | "")} className="sm:w-72">
              <option value="">Escolha a nova situação</option>
              {opcoesDeStatus.map((s) => (
                <option key={s} value={s}>
                  {rotuloDoStatus(s)}
                </option>
              ))}
            </CampoSelecao>
            <Botao type="submit" variante="secundario" disabled={!novoStatus}>
              Mudar situação
            </Botao>
          </form>
          <div className="mt-4 border-t border-creme-200 pt-3">
            <Botao variante="perigoContorno" tamanho="compacto" onClick={() => setConfirmarStatus("óbito")}>
              Registrar óbito
            </Botao>
          </div>
        </section>
      )}

      <section className="rounded-cartao bg-white px-4 py-2 shadow-cartao" aria-label="Cadastro">
        <dl className="divide-y divide-creme-200">
          <Linha rotulo="Sexo">{animal.sexo}</Linha>
          <Linha rotulo="Porte">{animal.porte}</Linha>
          <Linha rotulo="Idade aproximada">{animal.idade_estimada}</Linha>
          <Linha rotulo="Raça">{animal.raca}</Linha>
          <Linha rotulo="Pelagem">{animal.pelagem}</Linha>
          <Linha rotulo="Peso">{animal.peso_kg ? `${String(animal.peso_kg).replace(".", ",")} kg` : null}</Linha>
          <Linha rotulo="Canil ou baia">{animal.localizacao_baia}</Linha>
          <Linha rotulo="Código ou coleira">{animal.codigo_identificador}</Linha>
          <Linha rotulo="Castrado">{simNao(animal.is_castrado)}</Linha>
          <Linha rotulo="Idoso">{simNao(animal.is_idoso)}</Linha>
          <Linha rotulo="Microchip">{simNao(animal.is_microchipado)}</Linha>
          <Linha rotulo="Cuidados especiais">{animal.cuidados_especiais || "Nenhum"}</Linha>
        </dl>
      </section>

      <section className="rounded-cartao bg-white px-4 py-2 shadow-cartao" aria-labelledby="titulo-resgate">
        <h2 id="titulo-resgate" className="pt-2 text-lg">
          Resgate
        </h2>
        <dl className="divide-y divide-creme-200">
          <Linha rotulo="Data de entrada">{formatarData(animal.data_entrada)}</Linha>
          <Linha rotulo="Local">{animal.local_resgate}</Linha>
          <Linha rotulo="História">{animal.motivo_resgate}</Linha>
        </dl>
      </section>

      {ehAdministradora && !congelado && (
        <section className="rounded-cartao border-2 border-perigo-100 bg-white p-4" aria-labelledby="titulo-remover">
          <h2 id="titulo-remover" className="text-lg">
            Retirar da lista
          </h2>
          <p className="mt-1 mb-3 text-tinta-700">Use só para cadastros feitos por engano ou repetidos. O registro continua guardado no histórico.</p>
          <Botao variante="perigoContorno" icone={<IconeLixeira />} onClick={() => setConfirmarExclusao(true)}>
            Retirar {animal.nome} da lista
          </Botao>
        </section>
      )}

      <Dialogo
        aberto={editando}
        aoFechar={() => !salvando && setEditando(false)}
        titulo={`Editar ${animal.nome}`}
        rodape={
          <>
            <Botao variante="secundario" onClick={() => setEditando(false)} disabled={salvando}>
              Cancelar
            </Botao>
            <Botao type="submit" form="form-editar-animal" ocupado={salvando}>
              Salvar alterações
            </Botao>
          </>
        }
      >
        <form id="form-editar-animal" onSubmit={salvarEdicao} noValidate className="-mx-1 space-y-4">
          <CamposDoAnimal
            valores={valores}
            erros={erros}
            aoMudar={(campo, valor) => {
              setValores((v) => ({ ...v, [campo]: valor }));
              setErros((e) => ({ ...e, [campo]: undefined }));
            }}
          />
          {erroEdicao && (
            <Aviso tipo="perigo" anunciar>
              {erroEdicao}
            </Aviso>
          )}
        </form>
      </Dialogo>

      <Dialogo
        aberto={trocandoFoto}
        aoFechar={() => !enviandoFoto && setTrocandoFoto(false)}
        titulo="Foto do animal"
        rodape={
          <>
            <Botao variante="secundario" onClick={() => setTrocandoFoto(false)} disabled={enviandoFoto}>
              Cancelar
            </Botao>
            <Botao onClick={() => void salvarFoto()} disabled={!novaFoto} ocupado={enviandoFoto}>
              Salvar foto
            </Botao>
          </>
        }
      >
        <SeletorDeFoto foto={novaFoto} aoEscolher={setNovaFoto} previaAtual={enderecoDaFoto(animal.foto_url)} desabilitado={enviandoFoto} />
      </Dialogo>

      <Confirmacao
        aberta={confirmarStatus !== null}
        titulo={confirmarStatus === "óbito" ? `Registrar o óbito de ${animal.nome}?` : "Mudar a situação?"}
        textoConfirmar={confirmarStatus === "óbito" ? "Registrar óbito" : "Mudar situação"}
        perigosa={confirmarStatus === "óbito"}
        ocupada={mudandoStatus}
        aoCancelar={() => setConfirmarStatus(null)}
        aoConfirmar={() => confirmarStatus && void aplicarStatus(confirmarStatus)}
      >
        {confirmarStatus === "óbito" ? (
          <>
            <p>Sentimos muito. Depois de registrado, isto não pode ser desfeito.</p>
            <p>A ficha de {animal.nome} será guardada como histórico e não poderá mais ser alterada.</p>
          </>
        ) : (
          confirmarStatus && (
            <p>
              {animal.nome} passará de <strong>{rotuloDoStatus(animal.status_operacional)}</strong> para{" "}
              <strong>{rotuloDoStatus(confirmarStatus)}</strong>.
            </p>
          )
        )}
      </Confirmacao>

      <Confirmacao
        aberta={confirmarExclusao}
        titulo={`Retirar ${animal.nome} da lista?`}
        textoConfirmar="Retirar da lista"
        perigosa
        ocupada={excluindo}
        aoCancelar={() => setConfirmarExclusao(false)}
        aoConfirmar={() => void excluir()}
      >
        <p>{animal.nome} deixará de aparecer nas listas e no painel do dia. Esta ação não pode ser desfeita pelo sistema.</p>
      </Confirmacao>
    </div>
  );
}
