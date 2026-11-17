import { useState } from "react";
import type { FormEvent } from "react";
import { textoDoErro } from "../../api/http";
import { registrarProntuario } from "../../api/saude";
import { Botao } from "../../components/Botao";
import { CampoArea, CampoSelecao, CampoTexto } from "../../components/Campos";
import { Dialogo } from "../../components/Dialogo";
import { Aviso, EstadoVazio } from "../../components/Estados";
import { IconeMais, IconeProntuario } from "../../components/Icones";
import { Selo } from "../../components/Selos";
import { useAvisos } from "../../contexts/AvisosContext";
import { formatarData, hojeISO } from "../../utils/datas";
import type { PropsDaAba } from "./tipos";

const TIPOS = ["Consulta", "Exame", "Cirurgia", "Procedimento"];

const VAZIO = { tipo_evento: "Consulta", data_evento: "", diagnostico: "", veterinario_responsavel: "", clinica: "", procedimentos_realizados: "" };

export function AbaProntuario({ ficha, congelado, aoAtualizar }: PropsDaAba) {
  const { avisarSucesso } = useAvisos();
  const hoje = hojeISO();
  const [aberto, setAberto] = useState(false);
  const [form, setForm] = useState({ ...VAZIO, data_evento: hoje });
  const [erros, setErros] = useState<Record<string, string>>({});
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  const mudar = (campo: keyof typeof form, valor: string) => {
    setForm((f) => ({ ...f, [campo]: valor }));
    setErros((e) => ({ ...e, [campo]: "" }));
  };

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    const novos: Record<string, string> = {};
    if (!form.diagnostico.trim()) novos.diagnostico = "Descreva o que foi visto ou decidido.";
    if (!form.data_evento) novos.data_evento = "Informe a data.";
    setErros(novos);
    if (Object.keys(novos).length) return;
    setSalvando(true);
    setErroGeral(null);
    try {
      await registrarProntuario(ficha.animal.id, {
        tipo_evento: form.tipo_evento,
        data_evento: form.data_evento,
        diagnostico: form.diagnostico.trim(),
        veterinario_responsavel: form.veterinario_responsavel.trim() || undefined,
        clinica: form.clinica.trim() || undefined,
        procedimentos_realizados: form.procedimentos_realizados.trim() || undefined,
      });
      avisarSucesso("Registro adicionado ao prontuário.");
      setAberto(false);
      setForm({ ...VAZIO, data_evento: hoje });
      aoAtualizar();
    } catch (causa) {
      setErroGeral(textoDoErro(causa));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="space-y-5">
      {!congelado && (
        <Botao icone={<IconeMais />} onClick={() => setAberto(true)}>
          Novo registro
        </Botao>
      )}

      {ficha.prontuarios.length === 0 ? (
        <EstadoVazio icone={<IconeProntuario tamanho={28} />} titulo="Prontuário vazio">
          {congelado ? "Não há consultas ou exames no histórico." : "Registre consultas, exames, cirurgias e procedimentos."}
        </EstadoVazio>
      ) : (
        <ol className="relative space-y-3 border-l-4 border-mata-100 pl-4">
          {ficha.prontuarios.map((r) => (
            <li key={r.id} className="relative rounded-cartao bg-white p-4 shadow-cartao">
              <span aria-hidden="true" className="absolute top-5 -left-[1.6rem] size-4 rounded-full border-4 border-creme-50 bg-mata-700" />
              <div className="flex flex-wrap items-center gap-2">
                <Selo cor="ceu">{r.tipo_evento}</Selo>
                <span className="font-bold text-tinta-900">{formatarData(r.data_evento)}</span>
              </div>
              <p className="mt-2 break-words whitespace-pre-line text-tinta-900">{r.diagnostico}</p>
              {r.procedimentos_realizados && (
                <p className="mt-1 break-words whitespace-pre-line text-tinta-700">
                  <strong>Procedimentos:</strong> {r.procedimentos_realizados}
                </p>
              )}
              {(r.veterinario_responsavel || r.clinica) && (
                <p className="mt-1 text-tinta-700">{[r.veterinario_responsavel, r.clinica].filter(Boolean).join(" · ")}</p>
              )}
            </li>
          ))}
        </ol>
      )}

      <Dialogo
        aberto={aberto}
        aoFechar={() => !salvando && setAberto(false)}
        titulo="Novo registro no prontuário"
        rodape={
          <>
            <Botao variante="secundario" onClick={() => setAberto(false)} disabled={salvando}>
              Cancelar
            </Botao>
            <Botao type="submit" form="form-prontuario" ocupado={salvando}>
              Salvar registro
            </Botao>
          </>
        }
      >
        <form id="form-prontuario" onSubmit={salvar} noValidate className="space-y-4">
          <div className="grid grid-cols-1 gap-3 min-[400px]:grid-cols-2">
            <CampoSelecao rotulo="Tipo" value={form.tipo_evento} onChange={(e) => mudar("tipo_evento", e.target.value)}>
              {TIPOS.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </CampoSelecao>
            <CampoTexto rotulo="Data" obrigatorio type="date" max={hoje} value={form.data_evento} onChange={(e) => mudar("data_evento", e.target.value)} erro={erros.data_evento} />
          </div>
          <CampoArea rotulo="Diagnóstico ou observação" obrigatorio value={form.diagnostico} onChange={(e) => mudar("diagnostico", e.target.value)} erro={erros.diagnostico} />
          <CampoArea rotulo="Procedimentos realizados" value={form.procedimentos_realizados} onChange={(e) => mudar("procedimentos_realizados", e.target.value)} rows={2} />
          <div className="grid grid-cols-1 gap-3 min-[400px]:grid-cols-2">
            <CampoTexto rotulo="Veterinária(o)" value={form.veterinario_responsavel} onChange={(e) => mudar("veterinario_responsavel", e.target.value)} />
            <CampoTexto rotulo="Clínica" value={form.clinica} onChange={(e) => mudar("clinica", e.target.value)} />
          </div>
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
