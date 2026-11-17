import { useState } from "react";
import { Link } from "react-router-dom";
import { buscarPainelHoje } from "../api/hoje";
import { textoDoErro } from "../api/http";
import { darBaixa } from "../api/saude";
import { Botao, classesDoBotao } from "../components/Botao";
import { Esqueleto, EstadoErro, EstadoVazio } from "../components/Estados";
import { FotoAnimal } from "../components/FotoAnimal";
import { IconeAtualizar, IconeCerto, IconeMais, IconeRelogio, IconeRemedio, IconeVacina } from "../components/Icones";
import { Selo } from "../components/Selos";
import { useAuth } from "../contexts/AuthContext";
import { useAvisos } from "../contexts/AvisosContext";
import { useCarregar } from "../hooks/useCarregar";
import type { MedicacaoDoDia, PainelHoje } from "../types";
import { formatarData, formatarDataPorExtenso, horaAtual, prazoRelativo } from "../utils/datas";
import { horarioJaPassou } from "../utils/horarios";

function chaveDaDose(dose: Pick<MedicacaoDoDia, "prescricao_id" | "horario_previsto">): string {
  return `${dose.prescricao_id}-${dose.horario_previsto}`;
}

function Contador({ valor, rotulo, destaque = false }: { valor: number; rotulo: string; destaque?: boolean }) {
  return (
    <div className={`rounded-cartao px-3 py-3 shadow-cartao ${destaque ? "bg-barro-50" : "bg-white"}`}>
      <p className={`text-3xl font-extrabold ${destaque ? "text-barro-700" : "text-mata-800"}`}>{valor}</p>
      <p className="font-semibold leading-tight text-tinta-700">{rotulo}</p>
    </div>
  );
}

export default function HojePage() {
  const { usuario } = useAuth();
  const { avisarSucesso, avisarErro } = useAvisos();
  const painel = useCarregar((sinal) => buscarPainelHoje(sinal), []);
  const [enviando, setEnviando] = useState<Set<string>>(new Set());

  function marcarDose(chave: string, aplicado: boolean, horario: string | null) {
    painel.definirDados((atual) => {
      if (!atual) return atual;
      const medicacoes = atual.medicacoes_hoje.map((m) =>
        chaveDaDose(m) === chave ? { ...m, aplicado, horario_aplicado: horario } : m,
      );
      const pendentes = medicacoes.filter((m) => !m.aplicado).length;
      return { ...atual, medicacoes_hoje: medicacoes, kpis: { ...atual.kpis, total_medicacoes_pendentes: pendentes } } satisfies PainelHoje;
    });
  }

  async function confirmarDose(dose: MedicacaoDoDia) {
    const chave = chaveDaDose(dose);
    if (enviando.has(chave)) return;
    // Atualiza a tela na hora; se o servidor recusar, desfaz e explica
    marcarDose(chave, true, horaAtual());
    setEnviando((s) => new Set(s).add(chave));
    try {
      const resposta = await darBaixa(dose.prescricao_id, dose.horario_previsto);
      marcarDose(chave, true, resposta.log?.horario_aplicado ?? horaAtual());
      avisarSucesso(
        resposta.ja_baixado
          ? `A dose das ${dose.horario_previsto} de ${dose.animal_nome} já tinha sido registrada.`
          : `Dose de ${dose.medicamento} para ${dose.animal_nome} registrada.`,
      );
    } catch (causa) {
      marcarDose(chave, false, null);
      avisarErro(`Não registramos a dose de ${dose.animal_nome}. ${textoDoErro(causa)}`);
    } finally {
      setEnviando((s) => {
        const novo = new Set(s);
        novo.delete(chave);
        return novo;
      });
    }
  }

  const saudacao = (() => {
    const hora = new Date().getHours();
    const nome = usuario?.name?.split(" ")[0] ?? "";
    const parte = hora < 12 ? "Bom dia" : hora < 18 ? "Boa tarde" : "Boa noite";
    return nome ? `${parte}, ${nome}` : parte;
  })();

  const dados = painel.dados;
  const agora = dados?.hora_referencia ?? horaAtual();
  const pendentes = dados?.medicacoes_hoje.filter((m) => !m.aplicado) ?? [];
  const feitas = dados?.medicacoes_hoje.filter((m) => m.aplicado) ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl">{saudacao}</h1>
          <p className="mt-0.5 text-tinta-700 first-letter:uppercase">
            {dados ? formatarDataPorExtenso(dados.data_referencia) : "Rotina de hoje"}
          </p>
        </div>
        <div className="flex gap-2">
          <Botao variante="fantasma" tamanho="compacto" onClick={painel.recarregar} icone={<IconeAtualizar tamanho={20} />} ocupado={painel.carregando && Boolean(dados)}>
            Atualizar
          </Botao>
          <Link to="/animais/novo" className={classesDoBotao("primario", "compacto")}>
            <IconeMais tamanho={20} />
            Novo resgate
          </Link>
        </div>
      </div>

      {painel.erro && !dados && <EstadoErro mensagem={painel.erro} aoTentarDeNovo={painel.recarregar} />}

      {!dados && !painel.erro && (
        <div className="space-y-3" aria-hidden="true">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[0, 1, 2, 3].map((i) => <Esqueleto key={i} className="h-24" />)}
          </div>
          <Esqueleto className="h-32" />
          <Esqueleto className="h-32" />
        </div>
      )}

      {dados && (
        <>
          <section aria-label="Resumo do abrigo" className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Contador valor={dados.kpis.total_medicacoes_pendentes} rotulo="doses a dar hoje" destaque={dados.kpis.total_medicacoes_pendentes > 0} />
            <Contador valor={dados.kpis.total_acolhidos} rotulo="animais sob cuidado" />
            <Contador valor={dados.kpis.em_tratamento} rotulo="em tratamento" />
            <Contador valor={dados.kpis.disponiveis_adocao} rotulo="prontos para adoção" />
          </section>

          <section aria-labelledby="titulo-medicacoes">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h2 id="titulo-medicacoes" className="flex items-center gap-2 text-xl">
                <IconeRemedio className="text-barro-700" /> Medicações de hoje
              </h2>
              {pendentes.length > 0 && <Selo cor="barro">{pendentes.length === 1 ? "1 pendente" : `${pendentes.length} pendentes`}</Selo>}
            </div>

            {dados.medicacoes_hoje.length === 0 ? (
              <EstadoVazio icone={<IconeCerto tamanho={28} />} titulo="Nenhuma medicação para hoje">
                Quando um animal tiver remédio prescrito, as doses do dia aparecem aqui.
              </EstadoVazio>
            ) : (
              <>
                {pendentes.length === 0 && (
                  <p className="mb-3 rounded-2xl bg-mata-50 px-4 py-3 font-bold text-mata-900">Todas as doses de hoje foram dadas. Obrigada!</p>
                )}
                <ul className="grid gap-3 md:grid-cols-2">
                  {pendentes.map((dose) => {
                    const atrasada = dose.atrasada ?? horarioJaPassou(dose.horario_previsto, agora);
                    return (
                      <li key={chaveDaDose(dose)} className="flex flex-col gap-3 rounded-cartao bg-white p-3 shadow-cartao">
                        <div className="flex gap-3">
                          <Link to={`/animais/${dose.animal_id}?aba=medicacoes`} className="shrink-0 rounded-xl" aria-label={`Abrir ficha de ${dose.animal_nome}`}>
                            <FotoAnimal nome={dose.animal_nome} fotoUrl={dose.animal_foto_url} className="size-20 rounded-xl" />
                          </Link>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center justify-between gap-1">
                              <p className="truncate text-lg font-extrabold text-tinta-900">{dose.animal_nome}</p>
                              <Selo cor={atrasada ? "perigo" : "ambar"} icone={<IconeRelogio tamanho={16} />}>
                                {dose.horario_previsto}
                                {atrasada ? " · atrasada" : ""}
                              </Selo>
                            </div>
                            <p className="text-tinta-700">{dose.localizacao_baia}</p>
                            <p className="font-bold break-words text-mata-800">
                              {dose.medicamento} · {dose.dosagem}
                            </p>
                            {dose.instrucoes && <p className="text-tinta-700">{dose.instrucoes}</p>}
                          </div>
                        </div>
                        <Botao
                          tamanho="grande"
                          larguraTotal
                          icone={<IconeCerto />}
                          onClick={() => void confirmarDose(dose)}
                          aria-label={`Confirmar dose das ${dose.horario_previsto} de ${dose.medicamento} para ${dose.animal_nome}`}
                        >
                          Confirmar dose dada
                        </Botao>
                      </li>
                    );
                  })}
                </ul>

                {feitas.length > 0 && (
                  <details className="mt-4 rounded-cartao bg-white shadow-cartao">
                    <summary className="flex min-h-12 items-center px-4 font-bold text-mata-800">Doses já dadas hoje ({feitas.length})</summary>
                    <ul className="divide-y divide-creme-200 px-4 pb-2">
                      {feitas.map((dose) => (
                        <li key={chaveDaDose(dose)} className="flex items-center gap-3 py-2.5">
                          <IconeCerto className="shrink-0 text-mata-700" />
                          <span className="min-w-0 flex-1">
                            <span className="font-bold text-tinta-900">{dose.animal_nome}</span> · {dose.medicamento} das {dose.horario_previsto}
                          </span>
                          <span className="shrink-0 text-tinta-700">{enviando.has(chaveDaDose(dose)) ? "enviando..." : `às ${dose.horario_aplicado ?? "—"}`}</span>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </>
            )}
          </section>

          <section aria-labelledby="titulo-vacinas">
            <h2 id="titulo-vacinas" className="mb-3 flex items-center gap-2 text-xl">
              <IconeVacina className="text-barro-700" /> Vacinas e reforços
            </h2>
            {dados.vacinas_hoje.length === 0 ? (
              <EstadoVazio icone={<IconeVacina tamanho={28} />} titulo="Nenhum reforço para hoje">
                Reforços com data de hoje ou atrasados aparecem aqui.
              </EstadoVazio>
            ) : (
              <ul className="grid gap-3 md:grid-cols-2">
                {dados.vacinas_hoje.map((vacina) => (
                  <li key={vacina.vacina_id}>
                    <Link
                      to={`/animais/${vacina.animal_id}?aba=saude`}
                      className={`flex items-center gap-3 rounded-cartao border-l-8 bg-white p-3 shadow-cartao hover:bg-creme-100 ${vacina.atrasada ? "border-perigo-600" : "border-ambar-900"}`}
                    >
                      <FotoAnimal nome={vacina.animal_nome} fotoUrl={vacina.animal_foto_url} className="size-14 shrink-0 rounded-xl" />
                      <span className="flex min-w-0 flex-1 flex-col items-start gap-1">
                        <span className="block max-w-full truncate font-extrabold text-tinta-900">{vacina.animal_nome}</span>
                        <span className="block break-words text-tinta-700">
                          {vacina.nome_vacina} · {vacina.localizacao_baia}
                        </span>
                        <Selo cor={vacina.atrasada ? "perigo" : "ambar"}>
                          {vacina.atrasada && vacina.data_reforco
                            ? `Atrasada desde ${formatarData(vacina.data_reforco)}`
                            : vacina.data_reforco
                              ? `Reforço ${prazoRelativo(vacina.data_reforco, dados.data_referencia)}`
                              : "Reforço hoje"}
                        </Selo>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
