import { useState } from "react";
import type { FormEvent } from "react";
import { textoDoErro } from "../../api/http";
import { darBaixa, enderecoDosLembretes, listarPrescricoes, registrarPrescricao } from "../../api/saude";
import { Botao, classesDoBotao } from "../../components/Botao";
import { CampoArea, CampoTexto } from "../../components/Campos";
import { Dialogo } from "../../components/Dialogo";
import { Aviso, Esqueleto, EstadoErro, EstadoVazio } from "../../components/Estados";
import { IconeBaixar, IconeCerto, IconeFechar, IconeMais, IconeRemedio } from "../../components/Icones";
import { Selo } from "../../components/Selos";
import { useAvisos } from "../../contexts/AvisosContext";
import { useCarregar } from "../../hooks/useCarregar";
import type { Prescricao } from "../../types";
import { formatarData, hojeISO, horaAtual } from "../../utils/datas";
import { juntarHorarios, separarHorarios, validarHorarios } from "../../utils/horarios";
import { podeReceberPrescricao } from "../../utils/status";
import type { PropsDaAba } from "./tipos";

export function AbaMedicacoes({ ficha, congelado }: PropsDaAba) {
  const { animal } = ficha;
  const { avisarSucesso, avisarErro } = useAvisos();
  const hoje = hojeISO();
  const lista = useCarregar((sinal) => listarPrescricoes(animal.id, sinal), [animal.id]);
  const [enviando, setEnviando] = useState<string | null>(null);

  const [aberto, setAberto] = useState(false);
  const [form, setForm] = useState({ nome_medicamento: "", dosagem: "", data_inicio: hoje, data_fim: hoje, instrucoes: "" });
  const [horarios, setHorarios] = useState<string[]>(["08:00"]);
  const [erros, setErros] = useState<Record<string, string>>({});
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  const podePrescrever = !congelado && podeReceberPrescricao(animal.status_operacional);

  async function baixar(p: Prescricao, horario: string) {
    const chave = `${p.id}-${horario}`;
    setEnviando(chave);
    // Atualização imediata na tela, desfeita se o servidor recusar
    const provisoria = { id: -1, prescription_id: p.id, user_id: null, data_aplicacao: hoje, horario_previsto: horario, horario_aplicado: horaAtual(), observacoes: null, created_at: "" };
    lista.definirDados((atual) => atual?.map((x) => (x.id === p.id ? { ...x, logs_hoje: [...(x.logs_hoje ?? []), provisoria] } : x)) ?? atual);
    try {
      const resposta = await darBaixa(p.id, horario);
      avisarSucesso(resposta.ja_baixado ? `A dose das ${horario} já estava registrada.` : `Dose das ${horario} registrada.`);
      lista.definirDados(
        (atual) =>
          atual?.map((x) =>
            x.id === p.id ? { ...x, logs_hoje: [...(x.logs_hoje ?? []).filter((l) => l.id !== -1), resposta.log] } : x,
          ) ?? atual,
      );
    } catch (causa) {
      lista.definirDados((atual) => atual?.map((x) => (x.id === p.id ? { ...x, logs_hoje: (x.logs_hoje ?? []).filter((l) => l.id !== -1) } : x)) ?? atual);
      avisarErro(`A dose não foi registrada. ${textoDoErro(causa)}`);
    } finally {
      setEnviando(null);
    }
  }

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    const novos: Record<string, string> = {};
    if (!form.nome_medicamento.trim()) novos.nome_medicamento = "Informe o remédio.";
    if (!form.dosagem.trim()) novos.dosagem = "Informe a dose.";
    const erroHorarios = validarHorarios(horarios);
    if (erroHorarios) novos.horarios = erroHorarios;
    if (!form.data_inicio) novos.data_inicio = "Informe o início.";
    if (!form.data_fim) novos.data_fim = "Informe o fim.";
    else if (form.data_inicio && form.data_fim < form.data_inicio) novos.data_fim = "O fim deve ser depois do início.";
    setErros(novos);
    if (Object.keys(novos).length) return;
    setSalvando(true);
    setErroGeral(null);
    try {
      await registrarPrescricao(animal.id, {
        nome_medicamento: form.nome_medicamento.trim(),
        dosagem: form.dosagem.trim(),
        horarios: juntarHorarios(horarios),
        data_inicio: form.data_inicio,
        data_fim: form.data_fim,
        instrucoes: form.instrucoes.trim() || undefined,
      });
      avisarSucesso("Medicação prescrita.");
      setAberto(false);
      setForm({ nome_medicamento: "", dosagem: "", data_inicio: hoje, data_fim: hoje, instrucoes: "" });
      setHorarios(["08:00"]);
      lista.recarregar();
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

  const prescricoes = lista.dados ?? [];
  const ativas = prescricoes.filter((p) => p.is_active);
  const outras = prescricoes.filter((p) => !p.is_active);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2">
        {podePrescrever && (
          <Botao icone={<IconeMais />} onClick={() => setAberto(true)}>
            Prescrever medicação
          </Botao>
        )}
        <a href={enderecoDosLembretes(animal.id)} download className={classesDoBotao("secundario")}>
          <IconeBaixar />
          Lembretes para a agenda
        </a>
      </div>
      <p className="text-tinta-700">O arquivo de lembretes abre no Google Agenda ou na agenda do celular, com as medicações e reforços de vacina.</p>

      {!congelado && !podeReceberPrescricao(animal.status_operacional) && (
        <Aviso tipo="informacao">
          Novas medicações só podem ser prescritas para animais em acolhimento, em tratamento ou em lar temporário.
        </Aviso>
      )}

      {lista.erro && !lista.dados ? (
        <EstadoErro mensagem={lista.erro} aoTentarDeNovo={lista.recarregar} />
      ) : !lista.dados ? (
        <Esqueleto className="h-40" />
      ) : prescricoes.length === 0 ? (
        <EstadoVazio icone={<IconeRemedio tamanho={28} />} titulo="Nenhuma medicação prescrita" />
      ) : (
        <>
          <section aria-labelledby="titulo-ativas">
            <h2 id="titulo-ativas" className="mb-2 text-lg">
              Em uso hoje
            </h2>
            {ativas.length === 0 ? (
              <p className="rounded-2xl bg-white px-4 py-3 text-tinta-700 shadow-cartao">Nenhuma medicação em uso hoje.</p>
            ) : (
              <ul className="space-y-3">
                {ativas.map((p) => {
                  const feitas = new Map((p.logs_hoje ?? []).map((l) => [l.horario_previsto, l.horario_aplicado]));
                  return (
                    <li key={p.id} className="rounded-cartao bg-white p-4 shadow-cartao">
                      <p className="text-lg font-extrabold break-words text-tinta-900">
                        {p.nome_medicamento} · <span className="text-mata-800">{p.dosagem}</span>
                      </p>
                      <p className="text-tinta-700">
                        De {formatarData(p.data_inicio)} até {formatarData(p.data_fim)}
                      </p>
                      {p.instrucoes && <p className="mt-1 text-tinta-700">{p.instrucoes}</p>}
                      <ul className="mt-3 grid grid-cols-1 gap-2 min-[400px]:grid-cols-2">
                        {separarHorarios(p.horarios).map((h) => {
                          const aplicado = feitas.get(h);
                          return (
                            <li key={h}>
                              {aplicado ? (
                                <p className="flex min-h-12 items-center gap-2 rounded-xl bg-mata-50 px-3 font-bold text-mata-900">
                                  <IconeCerto /> {h} · dada às {aplicado}
                                </p>
                              ) : congelado ? (
                                <p className="flex min-h-12 items-center rounded-xl bg-creme-100 px-3 font-bold">{h} · não registrada</p>
                              ) : (
                                <Botao larguraTotal ocupado={enviando === `${p.id}-${h}`} onClick={() => void baixar(p, h)} icone={<IconeCerto />} aria-label={`Confirmar dose das ${h} de ${p.nome_medicamento}`}>
                                  Dose das {h}
                                </Botao>
                              )}
                            </li>
                          );
                        })}
                      </ul>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          {outras.length > 0 && (
            <section aria-labelledby="titulo-outras">
              <h2 id="titulo-outras" className="mb-2 text-lg">
                Fora do período
              </h2>
              <ul className="space-y-2">
                {outras.map((p) => (
                  <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-white px-4 py-3 shadow-cartao">
                    <span className="min-w-0 break-words">
                      <strong className="text-tinta-900">{p.nome_medicamento}</strong> · {p.dosagem} · {p.horarios}
                    </span>
                    <Selo cor={p.data_inicio && p.data_inicio > hoje ? "ceu" : "pedra"}>
                      {p.data_inicio && p.data_inicio > hoje ? `Começa ${formatarData(p.data_inicio)}` : `Terminou ${formatarData(p.data_fim)}`}
                    </Selo>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      <Dialogo
        aberto={aberto}
        aoFechar={() => !salvando && setAberto(false)}
        titulo="Prescrever medicação"
        rodape={
          <>
            <Botao variante="secundario" onClick={() => setAberto(false)} disabled={salvando}>
              Cancelar
            </Botao>
            <Botao type="submit" form="form-prescricao" ocupado={salvando}>
              Salvar prescrição
            </Botao>
          </>
        }
      >
        <form id="form-prescricao" onSubmit={salvar} noValidate className="space-y-4">
          <CampoTexto rotulo="Remédio" obrigatorio value={form.nome_medicamento} onChange={(e) => mudar("nome_medicamento", e.target.value)} erro={erros.nome_medicamento} placeholder="Ex.: Doxiciclina" />
          <CampoTexto rotulo="Dose" obrigatorio value={form.dosagem} onChange={(e) => mudar("dosagem", e.target.value)} erro={erros.dosagem} placeholder="Ex.: 100 mg, 1 comprimido" />
          <fieldset aria-describedby={erros.horarios ? "erro-horarios" : undefined}>
            <legend className="mb-1 font-bold text-tinta-900">
              Horários do dia <span className="text-perigo-700" aria-hidden="true">*</span>
            </legend>
            <ul className="space-y-2">
              {horarios.map((h, i) => (
                <li key={i} className="flex gap-2">
                  <label className="sr-only" htmlFor={`horario-${i}`}>
                    Horário {i + 1}
                  </label>
                  <input
                    id={`horario-${i}`}
                    type="time"
                    value={h}
                    onChange={(e) => {
                      const v = e.target.value;
                      setHorarios((lista) => lista.map((x, j) => (j === i ? v : x)));
                      setErros((er) => ({ ...er, horarios: "" }));
                    }}
                    className="min-h-12 flex-1 rounded-xl border-2 border-contorno bg-white px-3 text-tinta-900 focus:border-mata-700 focus:outline-none"
                  />
                  {horarios.length > 1 && (
                    <button
                      type="button"
                      onClick={() => setHorarios((lista) => lista.filter((_, j) => j !== i))}
                      className="grid size-12 shrink-0 place-items-center rounded-xl text-perigo-700 hover:bg-perigo-50"
                      aria-label={`Tirar o horário ${h || i + 1}`}
                    >
                      <IconeFechar />
                    </button>
                  )}
                </li>
              ))}
            </ul>
            <Botao variante="fantasma" tamanho="compacto" className="mt-2" icone={<IconeMais tamanho={20} />} onClick={() => setHorarios((l) => [...l, ""])}>
              Outro horário
            </Botao>
            {erros.horarios && (
              <p id="erro-horarios" className="mt-1 font-semibold text-perigo-700">
                {erros.horarios}
              </p>
            )}
          </fieldset>
          <div className="grid grid-cols-1 gap-3 min-[400px]:grid-cols-2">
            <CampoTexto rotulo="Início" obrigatorio type="date" value={form.data_inicio} onChange={(e) => mudar("data_inicio", e.target.value)} erro={erros.data_inicio} />
            <CampoTexto rotulo="Fim" obrigatorio type="date" min={form.data_inicio} value={form.data_fim} onChange={(e) => mudar("data_fim", e.target.value)} erro={erros.data_fim} />
          </div>
          <CampoArea rotulo="Instruções" value={form.instrucoes} onChange={(e) => mudar("instrucoes", e.target.value)} rows={2} placeholder="Ex.: dar com comida" />
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
