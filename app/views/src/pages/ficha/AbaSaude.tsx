import { useState } from "react";
import type { FormEvent } from "react";
import { textoDoErro } from "../../api/http";
import { registrarVacina } from "../../api/saude";
import { Botao } from "../../components/Botao";
import { CampoArea, CampoTexto } from "../../components/Campos";
import { Dialogo } from "../../components/Dialogo";
import { Aviso, EstadoVazio } from "../../components/Estados";
import { IconeMais, IconeVacina } from "../../components/Icones";
import { Selo } from "../../components/Selos";
import { useAvisos } from "../../contexts/AvisosContext";
import type { Vacina } from "../../types";
import { formatarData, hojeISO, prazoRelativo } from "../../utils/datas";
import type { PropsDaAba } from "./tipos";

function situacaoDoReforco(vacina: Vacina, hoje: string): "atrasado" | "agendado" | null {
  if (!vacina.data_reforco) return null;
  if (vacina.reforco_pendente === false) return null;
  const atrasado = vacina.reforco_atrasado ?? vacina.data_reforco < hoje;
  return atrasado ? "atrasado" : "agendado";
}

export function AbaSaude({ ficha, congelado, aoAtualizar }: PropsDaAba) {
  const { avisarSucesso } = useAvisos();
  const hoje = hojeISO();
  const [aberto, setAberto] = useState(false);
  const [form, setForm] = useState({ nome_vacina: "", lote: "", data_aplicacao: hoje, data_reforco: "", observacoes: "" });
  const [erros, setErros] = useState<Record<string, string>>({});
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  const reforcos = ficha.vacinas
    .map((v) => ({ vacina: v, situacao: situacaoDoReforco(v, hoje) }))
    .filter((r) => r.situacao !== null)
    .sort((a, b) => (a.vacina.data_reforco ?? "").localeCompare(b.vacina.data_reforco ?? ""));

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    const novos: Record<string, string> = {};
    if (!form.nome_vacina.trim()) novos.nome_vacina = "Informe o nome da vacina.";
    if (!form.data_aplicacao) novos.data_aplicacao = "Informe a data da aplicação.";
    else if (form.data_aplicacao > hoje) novos.data_aplicacao = "A aplicação não pode ser em data futura.";
    if (form.data_reforco && form.data_aplicacao && form.data_reforco < form.data_aplicacao)
      novos.data_reforco = "O reforço deve ser depois da aplicação.";
    setErros(novos);
    if (Object.keys(novos).length) return;
    setSalvando(true);
    setErroGeral(null);
    try {
      await registrarVacina(ficha.animal.id, {
        nome_vacina: form.nome_vacina.trim(),
        data_aplicacao: form.data_aplicacao,
        lote: form.lote.trim() || undefined,
        data_reforco: form.data_reforco || undefined,
        observacoes: form.observacoes.trim() || undefined,
      });
      avisarSucesso("Vacina registrada no cartão.");
      setAberto(false);
      setForm({ nome_vacina: "", lote: "", data_aplicacao: hoje, data_reforco: "", observacoes: "" });
      aoAtualizar();
    } catch (causa) {
      setErroGeral(textoDoErro(causa));
    } finally {
      setSalvando(false);
    }
  }

  const mudar = (campo: keyof typeof form, valor: string) => {
    setForm((f) => ({ ...f, [campo]: valor }));
    setErros((e) => ({ ...e, [campo]: "" }));
  };

  return (
    <div className="space-y-5">
      {!congelado && (
        <Botao icone={<IconeMais />} onClick={() => setAberto(true)}>
          Registrar vacina
        </Botao>
      )}

      <section aria-labelledby="titulo-reforcos">
        <h2 id="titulo-reforcos" className="mb-2 text-lg">
          Reforços agendados
        </h2>
        {reforcos.length === 0 ? (
          <p className="rounded-2xl bg-white px-4 py-3 text-tinta-700 shadow-cartao">Nenhum reforço pendente.</p>
        ) : (
          <ul className="space-y-2">
            {reforcos.map(({ vacina, situacao }) => (
              <li
                key={vacina.id}
                className={`flex flex-wrap items-center justify-between gap-2 rounded-2xl border-l-8 bg-white px-4 py-3 shadow-cartao ${situacao === "atrasado" ? "border-perigo-600" : "border-ambar-900"}`}
              >
                <span className="font-bold text-tinta-900">{vacina.nome_vacina}</span>
                <Selo cor={situacao === "atrasado" ? "perigo" : "ambar"}>
                  {situacao === "atrasado" ? "Atrasado" : "Previsto"}: {formatarData(vacina.data_reforco)} ({prazoRelativo(vacina.data_reforco ?? hoje, hoje)})
                </Selo>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="titulo-cartao">
        <h2 id="titulo-cartao" className="mb-2 text-lg">
          Cartão de vacinação
        </h2>
        {ficha.vacinas.length === 0 ? (
          <EstadoVazio icone={<IconeVacina tamanho={28} />} titulo="Nenhuma vacina registrada">
            {congelado ? "Não há vacinas no histórico deste animal." : "Registre as vacinas aplicadas e a data do reforço."}
          </EstadoVazio>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {ficha.vacinas.map((v) => (
              <li key={v.id} className="rounded-cartao bg-white p-4 shadow-cartao">
                <p className="text-lg font-extrabold text-tinta-900">{v.nome_vacina}</p>
                <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 text-tinta-700">
                  <dt className="font-bold">Aplicada em</dt>
                  <dd>{formatarData(v.data_aplicacao)}</dd>
                  <dt className="font-bold">Reforço</dt>
                  <dd>{v.data_reforco ? formatarData(v.data_reforco) : "Sem reforço"}</dd>
                  <dt className="font-bold">Lote</dt>
                  <dd className="break-all">{v.lote || "—"}</dd>
                </dl>
                {v.observacoes && <p className="mt-2 text-tinta-700">{v.observacoes}</p>}
              </li>
            ))}
          </ul>
        )}
      </section>

      <Dialogo
        aberto={aberto}
        aoFechar={() => !salvando && setAberto(false)}
        titulo="Registrar vacina"
        rodape={
          <>
            <Botao variante="secundario" onClick={() => setAberto(false)} disabled={salvando}>
              Cancelar
            </Botao>
            <Botao type="submit" form="form-vacina" ocupado={salvando}>
              Salvar vacina
            </Botao>
          </>
        }
      >
        <form id="form-vacina" onSubmit={salvar} noValidate className="space-y-4">
          <CampoTexto rotulo="Vacina" obrigatorio value={form.nome_vacina} onChange={(e) => mudar("nome_vacina", e.target.value)} erro={erros.nome_vacina} placeholder="Ex.: V10, Antirrábica" />
          <CampoTexto rotulo="Lote" value={form.lote} onChange={(e) => mudar("lote", e.target.value)} />
          <div className="grid grid-cols-1 gap-3 min-[400px]:grid-cols-2">
            <CampoTexto rotulo="Aplicada em" obrigatorio type="date" max={hoje} value={form.data_aplicacao} onChange={(e) => mudar("data_aplicacao", e.target.value)} erro={erros.data_aplicacao} />
            <CampoTexto rotulo="Data do reforço" type="date" min={form.data_aplicacao} value={form.data_reforco} onChange={(e) => mudar("data_reforco", e.target.value)} erro={erros.data_reforco} />
          </div>
          <CampoArea rotulo="Observações" value={form.observacoes} onChange={(e) => mudar("observacoes", e.target.value)} rows={2} />
          {erroGeral && (
            <Aviso tipo="perigo" anunciar>
              {erroGeral}
            </Aviso>
          )}
        </form>
      </Dialogo>
    </div>
  );
}
