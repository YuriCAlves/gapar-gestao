import { useState } from "react";
import type { FormEvent } from "react";
import { adocaoFoiBarrada, registrarAdocao } from "../../api/adocoes";
import { textoDoErro } from "../../api/http";
import { Botao } from "../../components/Botao";
import { CaixaDeMarcacao, CampoArea, CampoTexto } from "../../components/Campos";
import { Confirmacao, Dialogo } from "../../components/Dialogo";
import { Aviso } from "../../components/Estados";
import { IconeCadeado, IconeCoracao } from "../../components/Icones";
import { useAvisos } from "../../contexts/AvisosContext";
import { formatarData, hojeISO } from "../../utils/datas";
import { podeSerAdotado, rotuloDoStatus } from "../../utils/status";
import type { PropsDaAba } from "./tipos";

const VAZIO = {
  adotante_nome: "",
  adotante_telefone: "",
  data_adocao: "",
  adotante_cpf: "",
  adotante_endereco: "",
  observacoes: "",
  termo_fisico_assinado: false,
};

export function AbaAdocao({ ficha, aoAtualizar }: PropsDaAba) {
  const { animal, adocao } = ficha;
  const { avisarSucesso } = useAvisos();
  const hoje = hojeISO();
  const [form, setForm] = useState({ ...VAZIO, data_adocao: hoje });
  const [erros, setErros] = useState<Record<string, string>>({});
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [confirmando, setConfirmando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [barrada, setBarrada] = useState(false);

  if (adocao) {
    return (
      <section className="rounded-cartao bg-white p-4 shadow-cartao" aria-labelledby="titulo-adocao">
        <h2 id="titulo-adocao" className="flex items-center gap-2 text-lg">
          <IconeCoracao className="text-barro-700" /> Adoção registrada
        </h2>
        <dl className="mt-3 grid gap-x-4 gap-y-2 sm:grid-cols-[auto_1fr]">
          <dt className="font-bold text-tinta-900">Adotante</dt>
          <dd className="break-words">{adocao.adotante_nome}</dd>
          <dt className="font-bold text-tinta-900">Telefone</dt>
          <dd>{adocao.adotante_telefone}</dd>
          <dt className="font-bold text-tinta-900">Data da adoção</dt>
          <dd>{formatarData(adocao.data_adocao)}</dd>
          {adocao.adotante_cpf && (
            <>
              <dt className="font-bold text-tinta-900">CPF</dt>
              <dd>{adocao.adotante_cpf}</dd>
            </>
          )}
          {adocao.adotante_endereco && (
            <>
              <dt className="font-bold text-tinta-900">Endereço</dt>
              <dd className="break-words">{adocao.adotante_endereco}</dd>
            </>
          )}
          <dt className="font-bold text-tinta-900">Termo em papel</dt>
          <dd>{adocao.termo_fisico_assinado ? "Assinado" : "Não informado"}</dd>
          {adocao.observacoes && (
            <>
              <dt className="font-bold text-tinta-900">Observações</dt>
              <dd className="break-words whitespace-pre-line">{adocao.observacoes}</dd>
            </>
          )}
        </dl>
        <p className="mt-4 flex items-center gap-2 text-tinta-700">
          <IconeCadeado className="shrink-0" /> Estes dados ficam guardados e não podem ser alterados.
        </p>
      </section>
    );
  }

  if (animal.status_operacional === "óbito") {
    return <Aviso tipo="preservado">Não há adoção registrada para {animal.nome}.</Aviso>;
  }

  if (!podeSerAdotado(animal.status_operacional)) {
    return (
      <Aviso tipo="informacao" titulo="Ainda não pode ser adotado">
        {animal.nome} está "{rotuloDoStatus(animal.status_operacional)}". A adoção só pode ser registrada para animais disponíveis para adoção ou em lar
        temporário. Mude a situação na aba Dados gerais quando ele estiver pronto.
      </Aviso>
    );
  }

  const mudar = (campo: keyof typeof form, valor: string | boolean) => {
    setForm((f) => ({ ...f, [campo]: valor }));
    setErros((e) => ({ ...e, [campo]: "" }));
  };

  function revisar(evento: FormEvent) {
    evento.preventDefault();
    const novos: Record<string, string> = {};
    if (!form.adotante_nome.trim()) novos.adotante_nome = "Informe o nome de quem adota.";
    const digitos = form.adotante_telefone.replace(/\D/g, "");
    if (!digitos) novos.adotante_telefone = "Informe um telefone para contato.";
    else if (digitos.length < 8) novos.adotante_telefone = "Confira o telefone: faltam números.";
    if (!form.data_adocao) novos.data_adocao = "Informe a data da adoção.";
    else if (form.data_adocao > hoje) novos.data_adocao = "A data não pode ser no futuro.";
    const cpf = form.adotante_cpf.replace(/\D/g, "");
    if (cpf && cpf.length !== 11) novos.adotante_cpf = "O CPF tem 11 números.";
    setErros(novos);
    setErroGeral(null);
    if (Object.keys(novos).length === 0) setConfirmando(true);
  }

  async function registrar() {
    setSalvando(true);
    try {
      await registrarAdocao(animal.id, {
        adotante_nome: form.adotante_nome.trim(),
        adotante_telefone: form.adotante_telefone.trim(),
        data_adocao: form.data_adocao,
        adotante_cpf: form.adotante_cpf.trim() || undefined,
        adotante_endereco: form.adotante_endereco.trim() || undefined,
        observacoes: form.observacoes.trim() || undefined,
        termo_fisico_assinado: form.termo_fisico_assinado,
      });
      setConfirmando(false);
      avisarSucesso(`Adoção de ${animal.nome} registrada. Que alegria!`);
      aoAtualizar();
    } catch (causa) {
      setConfirmando(false);
      if (adocaoFoiBarrada(causa)) setBarrada(true);
      else setErroGeral(textoDoErro(causa));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <form onSubmit={revisar} noValidate className="space-y-4 rounded-cartao bg-white p-4 shadow-cartao">
      <div>
        <h2 className="text-lg">Registrar adoção</h2>
        <p className="mt-1 text-tinta-700">Nome, telefone e data são obrigatórios. Depois de registrada, a ficha de {animal.nome} fica guardada e não pode mais ser alterada.</p>
      </div>
      <CampoTexto rotulo="Nome de quem adota" obrigatorio autoComplete="off" value={form.adotante_nome} onChange={(e) => mudar("adotante_nome", e.target.value)} erro={erros.adotante_nome} />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <CampoTexto rotulo="Telefone" obrigatorio type="tel" inputMode="tel" autoComplete="off" placeholder="(00) 00000-0000" value={form.adotante_telefone} onChange={(e) => mudar("adotante_telefone", e.target.value)} erro={erros.adotante_telefone} />
        <CampoTexto rotulo="Data da adoção" obrigatorio type="date" max={hoje} value={form.data_adocao} onChange={(e) => mudar("data_adocao", e.target.value)} erro={erros.data_adocao} />
        <CampoTexto rotulo="CPF" inputMode="numeric" autoComplete="off" placeholder="Opcional" value={form.adotante_cpf} onChange={(e) => mudar("adotante_cpf", e.target.value)} erro={erros.adotante_cpf} />
        <CampoTexto rotulo="Endereço" autoComplete="off" placeholder="Opcional" value={form.adotante_endereco} onChange={(e) => mudar("adotante_endereco", e.target.value)} />
      </div>
      <CampoArea rotulo="Observações" rows={2} value={form.observacoes} onChange={(e) => mudar("observacoes", e.target.value)} />
      <CaixaDeMarcacao rotulo="O termo de adoção em papel foi assinado" marcado={form.termo_fisico_assinado} aoMudar={(v) => mudar("termo_fisico_assinado", v)} />
      {erroGeral && (
        <Aviso tipo="perigo" titulo="A adoção não foi registrada" anunciar>
          {erroGeral}
        </Aviso>
      )}
      <Botao type="submit" tamanho="grande" larguraTotal icone={<IconeCoracao />}>
        Revisar e registrar adoção
      </Botao>

      <Confirmacao
        aberta={confirmando}
        titulo={`Confirmar a adoção de ${animal.nome}?`}
        textoConfirmar="Registrar adoção"
        ocupada={salvando}
        aoCancelar={() => setConfirmando(false)}
        aoConfirmar={() => void registrar()}
      >
        <p>
          <strong>{form.adotante_nome.trim()}</strong>, telefone {form.adotante_telefone.trim()}, em {formatarData(form.data_adocao)}.
        </p>
        <p>Depois de confirmar, isto não pode ser desfeito e a ficha de {animal.nome} não poderá mais ser alterada.</p>
      </Confirmacao>

      <Dialogo
        aberto={barrada}
        aoFechar={() => setBarrada(false)}
        titulo="Adoção não autorizada"
        papel="alertdialog"
        exigeResposta
        rodape={<Botao onClick={() => setBarrada(false)}>Entendi</Botao>}
      >
        <Aviso tipo="perigo">
          Não é possível registrar a adoção de {animal.nome} para esta pessoa. Antes de continuar, fale com a administradora do GAPAR.
        </Aviso>
        <p className="mt-3 text-tinta-700">Não combine a entrega do animal até a administradora orientar.</p>
      </Dialogo>
    </form>
  );
}
