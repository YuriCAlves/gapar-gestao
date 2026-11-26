import { useState } from "react";
import type { FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import {
  alterarPerfil,
  autorizarPessoa,
  cadastrarNaoApto,
  definirAcesso,
  listarAuditoria,
  listarNaoAptos,
  listarPessoasAutorizadas,
  listarTiposDeAuditoria,
} from "../api/admin";
import type { FiltrosAuditoria } from "../api/admin";
import { textoDoErro } from "../api/http";
import { Abas, PainelDaAba } from "../components/Abas";
import { Botao } from "../components/Botao";
import { CampoArea, CampoCpf, CampoSelecao, CampoTelefone, CampoTexto } from "../components/Campos";
import { Confirmacao, Dialogo } from "../components/Dialogo";
import { Aviso, Esqueleto, EstadoErro, EstadoVazio } from "../components/Estados";
import { IconeCadeado, IconeMais, IconePessoa } from "../components/Icones";
import { Selo } from "../components/Selos";
import { useAvisos } from "../contexts/AvisosContext";
import { useCarregar } from "../hooks/useCarregar";
import type { Perfil, PessoaAutorizada } from "../types";
import { formatarDataHora } from "../utils/datas";
import { cpfValido, exibirCpf, exibirTelefone, mensagemErroCpf, mensagemErroTelefone, telefoneValido } from "../utils/mascaras";
import { limparTextoDoServidor } from "../utils/mensagens";

type IdDaAba = "pessoas" | "nao-aptos" | "historico";

const rotuloDoPerfil = (p: Perfil) => (p === "Administradora" ? "Administradora" : "Voluntária");

// ---------------------------------------------------------------------------
// Pessoas autorizadas
// ---------------------------------------------------------------------------

function PessoasAutorizadas() {
  const { avisarSucesso, avisarErro } = useAvisos();
  const lista = useCarregar((sinal) => listarPessoasAutorizadas(sinal), []);
  const [email, setEmail] = useState("");
  const [perfil, setPerfil] = useState<Perfil>("Voluntaria");
  const [erroEmail, setErroEmail] = useState<string | null>(null);
  const [adicionando, setAdicionando] = useState(false);
  const [alvo, setAlvo] = useState<{ pessoa: PessoaAutorizada; acao: "desativar" | "ativar" | "perfil" } | null>(null);
  const [aplicando, setAplicando] = useState(false);

  async function adicionar(evento: FormEvent) {
    evento.preventDefault();
    const valor = email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(valor)) {
      setErroEmail("Digite um e-mail válido, por exemplo maria@gmail.com.");
      return;
    }
    setAdicionando(true);
    setErroEmail(null);
    try {
      await autorizarPessoa(valor, perfil);
      avisarSucesso(`${valor} agora pode entrar no sistema.`);
      setEmail("");
      setPerfil("Voluntaria");
      lista.recarregar();
    } catch (causa) {
      setErroEmail(textoDoErro(causa));
    } finally {
      setAdicionando(false);
    }
  }

  async function aplicar() {
    if (!alvo) return;
    setAplicando(true);
    try {
      if (alvo.acao === "perfil") {
        const novo: Perfil = alvo.pessoa.role === "Administradora" ? "Voluntaria" : "Administradora";
        await alterarPerfil(alvo.pessoa.id, novo);
        avisarSucesso(`${alvo.pessoa.email} agora é ${rotuloDoPerfil(novo)}.`);
      } else {
        await definirAcesso(alvo.pessoa.id, alvo.acao === "ativar");
        avisarSucesso(alvo.acao === "ativar" ? `Acesso de ${alvo.pessoa.email} reativado.` : `Acesso de ${alvo.pessoa.email} desativado.`);
      }
      setAlvo(null);
      lista.recarregar();
    } catch (causa) {
      avisarErro(textoDoErro(causa));
    } finally {
      setAplicando(false);
    }
  }

  return (
    <div className="space-y-5">
      <form onSubmit={adicionar} noValidate className="grid gap-3 rounded-cartao bg-white p-4 shadow-cartao sm:grid-cols-[1fr_auto_auto] sm:items-end">
        <CampoTexto rotulo="E-mail Google da pessoa" type="email" inputMode="email" autoComplete="off" value={email} onChange={(e) => setEmail(e.target.value)} erro={erroEmail} />
        <CampoSelecao rotulo="Perfil" value={perfil} onChange={(e) => setPerfil(e.target.value as Perfil)}>
          <option value="Voluntaria">Voluntária</option>
          <option value="Administradora">Administradora</option>
        </CampoSelecao>
        <Botao type="submit" ocupado={adicionando} icone={<IconeMais />} className={erroEmail ? "sm:mb-9" : ""}>
          Autorizar
        </Botao>
      </form>

      {lista.erro && !lista.dados ? (
        <EstadoErro mensagem={lista.erro} aoTentarDeNovo={lista.recarregar} />
      ) : !lista.dados ? (
        <Esqueleto className="h-48" />
      ) : lista.dados.length === 0 ? (
        <EstadoVazio icone={<IconePessoa tamanho={28} />} titulo="Ninguém autorizado ainda" />
      ) : (
        <ul className="space-y-2">
          {lista.dados.map((p) => {
            const protegida = Boolean(p.is_voce || p.is_admin_inicial);
            return (
              <li key={p.id} className={`flex flex-col gap-3 rounded-2xl bg-white p-4 shadow-cartao sm:flex-row sm:items-center ${p.is_active ? "" : "opacity-80"}`}>
                <div className="min-w-0 flex-1">
                  <p className="font-bold break-all text-tinta-900">{p.email}</p>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    <Selo cor={p.role === "Administradora" ? "barro" : "mata"}>{rotuloDoPerfil(p.role)}</Selo>
                    <Selo cor={p.is_active ? "ceu" : "pedra"}>{p.is_active ? "Acesso ativo" : "Acesso desativado"}</Selo>
                    {p.is_voce && <Selo cor="lilas">Você</Selo>}
                    {p.is_admin_inicial && !p.is_voce && <Selo cor="lilas">Responsável principal</Selo>}
                  </div>
                </div>
                {protegida ? (
                  <p className="text-tinta-700 sm:max-w-48">{p.is_voce ? "Você não pode alterar o próprio acesso." : "O acesso da responsável principal não pode ser alterado."}</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {p.is_active && (
                      <Botao variante="secundario" tamanho="compacto" onClick={() => setAlvo({ pessoa: p, acao: "perfil" })}>
                        Tornar {p.role === "Administradora" ? "voluntária" : "administradora"}
                      </Botao>
                    )}
                    {p.is_active ? (
                      <Botao variante="perigoContorno" tamanho="compacto" onClick={() => setAlvo({ pessoa: p, acao: "desativar" })}>
                        Desativar acesso
                      </Botao>
                    ) : (
                      <Botao variante="secundario" tamanho="compacto" onClick={() => setAlvo({ pessoa: p, acao: "ativar" })}>
                        Reativar acesso
                      </Botao>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <Confirmacao
        aberta={alvo !== null}
        titulo={alvo?.acao === "desativar" ? "Desativar o acesso?" : alvo?.acao === "ativar" ? "Reativar o acesso?" : "Mudar o perfil?"}
        textoConfirmar={alvo?.acao === "desativar" ? "Desativar acesso" : alvo?.acao === "ativar" ? "Reativar acesso" : "Mudar perfil"}
        perigosa={alvo?.acao === "desativar"}
        ocupada={aplicando}
        aoCancelar={() => setAlvo(null)}
        aoConfirmar={() => void aplicar()}
      >
        {alvo?.acao === "desativar" && <p>{alvo.pessoa.email} perde o acesso imediatamente, mesmo se estiver usando o sistema agora.</p>}
        {alvo?.acao === "ativar" && <p>{alvo.pessoa.email} poderá entrar de novo com a conta Google.</p>}
        {alvo?.acao === "perfil" && (
          <p>
            {alvo.pessoa.email} passará a ser{" "}
            <strong>{alvo.pessoa.role === "Administradora" ? "Voluntária" : "Administradora"}</strong>
            {alvo.pessoa.role === "Administradora" ? " e deixará de ver esta área de gestão." : " e terá acesso a esta área de gestão, incluindo a lista sigilosa."}
          </p>
        )}
      </Confirmacao>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Lista sigilosa de pessoas não aptas a adotar
// ---------------------------------------------------------------------------

type TipoBuscaNaoAptos = "nome" | "cpf" | "telefone";

const MODOS_BUSCA_NAO_APTOS: { valor: TipoBuscaNaoAptos; rotulo: string }[] = [
  { valor: "nome", rotulo: "Nome" },
  { valor: "cpf", rotulo: "CPF" },
  { valor: "telefone", rotulo: "Telefone" },
];

function NaoAptos() {
  const { avisarSucesso } = useAvisos();
  const [tipoBusca, setTipoBusca] = useState<TipoBuscaNaoAptos>("nome");
  const [busca, setBusca] = useState("");
  const cpfPronto = tipoBusca === "cpf" && cpfValido(busca) ? busca : "";
  const telefonePronto = tipoBusca === "telefone" && telefoneValido(busca) ? busca : "";

  const lista = useCarregar(
    (sinal) => {
      if (cpfPronto) return listarNaoAptos({ cpf: cpfPronto }, sinal);
      if (telefonePronto) return listarNaoAptos({ telefone: telefonePronto }, sinal);
      return listarNaoAptos({}, sinal);
    },
    [cpfPronto, telefonePronto],
  );
  const [aberto, setAberto] = useState(false);
  const [form, setForm] = useState({ nome: "", cpf: "", telefone: "", motivo_impedimento: "" });
  const [erros, setErros] = useState<Record<string, string>>({});
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  const mudar = (campo: keyof typeof form, valor: string) => {
    setForm((f) => ({ ...f, [campo]: valor }));
    setErros((e) => ({ ...e, [campo]: "" }));
  };

  function trocarTipoBusca(novo: TipoBuscaNaoAptos) {
    if (novo === tipoBusca) return;
    setTipoBusca(novo);
    setBusca("");
  }

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    const novos: Record<string, string> = {};
    if (!form.nome.trim()) novos.nome = "Informe o nome completo.";
    if (!form.motivo_impedimento.trim()) novos.motivo_impedimento = "Descreva o motivo.";
    const erroCpf = mensagemErroCpf(form.cpf, false);
    if (erroCpf) novos.cpf = erroCpf;
    const erroTel = mensagemErroTelefone(form.telefone, false);
    if (erroTel) novos.telefone = erroTel;
    setErros(novos);
    if (Object.keys(novos).length) return;
    setSalvando(true);
    setErroGeral(null);
    try {
      await cadastrarNaoApto({
        nome: form.nome.trim(),
        motivo_impedimento: form.motivo_impedimento.trim(),
        cpf: form.cpf || undefined,
        telefone: form.telefone || undefined,
      });
      avisarSucesso("Pessoa incluída na lista sigilosa.");
      setAberto(false);
      setForm({ nome: "", cpf: "", telefone: "", motivo_impedimento: "" });
      lista.recarregar();
    } catch (causa) {
      setErroGeral(textoDoErro(causa));
    } finally {
      setSalvando(false);
    }
  }

  const termoNome = tipoBusca === "nome" ? busca.trim().toLowerCase() : "";
  const filtrados =
    tipoBusca === "nome"
      ? (lista.dados ?? []).filter((p) => !termoNome || p.nome.toLowerCase().includes(termoNome))
      : (lista.dados ?? []);
  const aguardandoNumeroCompleto =
    (tipoBusca === "cpf" && !cpfPronto) || (tipoBusca === "telefone" && !telefonePronto);
  const temBuscaAtiva = Boolean(termoNome || cpfPronto || telefonePronto);

  return (
    <div className="space-y-4">
      <Aviso tipo="preservado" titulo="Informação sigilosa">
        Só a administradora vê esta lista. Quando alguém daqui tenta adotar, o sistema bloqueia a adoção sem mostrar o motivo para a voluntária.
      </Aviso>

      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div role="group" aria-label="Procurar por" className="flex flex-wrap items-center gap-2">
            <span className="font-bold text-tinta-900">Procurar por:</span>
            <div className="inline-flex rounded-xl border-2 border-contorno bg-white p-0.5">
              {MODOS_BUSCA_NAO_APTOS.map((modo) => (
                <button
                  key={modo.valor}
                  type="button"
                  aria-pressed={tipoBusca === modo.valor}
                  onClick={() => trocarTipoBusca(modo.valor)}
                  className={`min-h-11 rounded-lg px-3.5 font-bold transition-colors ${
                    tipoBusca === modo.valor ? "bg-mata-700 text-white" : "text-tinta-700 hover:bg-mata-50"
                  }`}
                >
                  {modo.rotulo}
                </button>
              ))}
            </div>
          </div>
          <Botao icone={<IconeMais />} onClick={() => setAberto(true)}>
            Incluir pessoa
          </Botao>
        </div>

        <div>
          {tipoBusca === "nome" && (
            <CampoTexto
              rotulo="Procurar por nome"
              type="search"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Digite parte do nome"
            />
          )}
          {tipoBusca === "cpf" && (
            <CampoCpf
              rotulo="Procurar por CPF"
              valor={busca}
              onValor={setBusca}
              dica={aguardandoNumeroCompleto ? "Digite o CPF completo para procurar." : undefined}
            />
          )}
          {tipoBusca === "telefone" && (
            <CampoTelefone
              rotulo="Procurar por telefone"
              valor={busca}
              onValor={setBusca}
              dica={aguardandoNumeroCompleto ? "Digite o telefone completo com DDD para procurar." : undefined}
            />
          )}
        </div>
      </div>

      {lista.erro && !lista.dados ? (
        <EstadoErro mensagem={lista.erro} aoTentarDeNovo={lista.recarregar} />
      ) : !lista.dados ? (
        <Esqueleto className="h-40" />
      ) : filtrados.length === 0 ? (
        <EstadoVazio icone={<IconeCadeado tamanho={28} />} titulo={temBuscaAtiva ? "Ninguém encontrado" : "Lista vazia"} />
      ) : (
        <ul className={`space-y-2 ${lista.carregando ? "opacity-60" : ""}`}>
          {filtrados.map((p) => {
            const cpfFormatado = exibirCpf(p.cpf);
            const telFormatado = exibirTelefone(p.telefone);
            return (
              <li key={p.id} className="rounded-2xl bg-white p-4 shadow-cartao">
                <p className="font-extrabold break-words text-tinta-900">{p.nome}</p>
                <p className="text-tinta-700">
                  {[cpfFormatado && `CPF ${cpfFormatado}`, telFormatado && `Tel. ${telFormatado}`].filter(Boolean).join(" · ") || "Sem CPF ou telefone"}
                </p>
                <p className="mt-1 break-words whitespace-pre-line">{p.motivo_impedimento}</p>
                <p className="mt-1 text-tinta-700">Incluída em {formatarDataHora(p.created_at)}</p>
              </li>
            );
          })}
        </ul>
      )}

      <Dialogo
        aberto={aberto}
        aoFechar={() => !salvando && setAberto(false)}
        titulo="Incluir na lista sigilosa"
        rodape={
          <>
            <Botao variante="secundario" onClick={() => setAberto(false)} disabled={salvando}>
              Cancelar
            </Botao>
            <Botao type="submit" form="form-nao-apto" ocupado={salvando}>
              Incluir
            </Botao>
          </>
        }
      >
        <form id="form-nao-apto" onSubmit={salvar} noValidate className="space-y-4">
          <CampoTexto rotulo="Nome completo" obrigatorio autoComplete="off" value={form.nome} onChange={(e) => mudar("nome", e.target.value)} erro={erros.nome} />
          <div className="grid grid-cols-1 gap-3 min-[400px]:grid-cols-2">
            <CampoCpf rotulo="CPF" valor={form.cpf} onValor={(v) => mudar("cpf", v)} erro={erros.cpf} />
            <CampoTelefone rotulo="Telefone" valor={form.telefone} onValor={(v) => mudar("telefone", v)} erro={erros.telefone} />
          </div>
          <CampoArea rotulo="Motivo do impedimento" obrigatorio value={form.motivo_impedimento} onChange={(e) => mudar("motivo_impedimento", e.target.value)} erro={erros.motivo_impedimento} />
          <p className="text-tinta-700">CPF e telefone ajudam o sistema a reconhecer a pessoa mesmo com o nome escrito de outro jeito.</p>
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

// ---------------------------------------------------------------------------
// Histórico de ações (auditoria)
// ---------------------------------------------------------------------------

const ROTULOS_DE_ACAO: Record<string, string> = {
  LOGIN_SUCESSO: "Entrou no sistema",
  LOGOUT: "Saiu do sistema",
  LOGIN_REJEITADO_FORA_WHITELIST: "Entrada recusada (e-mail não autorizado)",
  LOGIN_REJEITADO_USUARIA_INATIVA: "Entrada recusada (acesso desativado)",
  LOGIN_REJEITADO_IDENTIDADE_DIVERGENTE: "Entrada recusada (conta Google diferente)",
  ANIMAL_CADASTRADO: "Cadastrou animal",
  ANIMAL_ATUALIZADO: "Editou dados do animal",
  STATUS_ANIMAL_ALTERADO: "Mudou a situação do animal",
  ANIMAL_EXCLUIDO_LOGICO: "Retirou animal da lista",
  FOTO_ANIMAL_ATUALIZADA: "Trocou a foto do animal",
  VACINA_REGISTRADA: "Registrou vacina",
  PRONTUARIO_REGISTRADO: "Registrou no prontuário",
  PRESCRICAO_CADASTRADA: "Prescreveu medicação",
  BAIXA_MEDICACAO: "Confirmou dose de medicação",
  ADOCAO_FORMALIZADA: "Registrou adoção",
  TENTATIVA_ADOCAO_BLOQUEADA_NAO_APTO: "Adoção bloqueada (lista sigilosa)",
  WHITELIST_USUARIA_ADICIONADA: "Autorizou pessoa",
  USUARIA_ATIVADA: "Reativou acesso",
  USUARIA_DESATIVADA_REVOGADA: "Desativou acesso",
  NAO_APTO_INCLUIDO: "Incluiu na lista sigilosa",
};

function rotuloDaAcao(acao: string): string {
  if (ROTULOS_DE_ACAO[acao]) return ROTULOS_DE_ACAO[acao];
  const texto = acao.toLowerCase().replace(/_/g, " ").replace(/\bwhitelist\b/g, "pessoas autorizadas");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

const ROTULOS_DE_CADASTRO: Record<string, string> = {
  Animal: "Animal",
  Vaccination: "Vacina",
  MedicalRecord: "Prontuário",
  Prescription: "Medicação",
  MedicationLog: "Dose",
  Adoption: "Adoção",
  Whitelist: "Pessoas autorizadas",
  User: "Usuária",
  NonEligiblePerson: "Lista sigilosa",
  Announcement: "Aviso",
};

function Historico() {
  const [pagina, setPagina] = useState(1);
  const [filtros, setFiltros] = useState<FiltrosAuditoria>({});
  const [rascunho, setRascunho] = useState<FiltrosAuditoria>({});
  const tipos = useCarregar((sinal) => listarTiposDeAuditoria(sinal).catch(() => ({ acoes: [], entidades: [] })), []);
  const chave = JSON.stringify(filtros);
  const historico = useCarregar((sinal) => listarAuditoria(pagina, filtros, sinal), [pagina, chave]);

  function aplicar(evento: FormEvent) {
    evento.preventDefault();
    const limpo = Object.fromEntries(Object.entries(rascunho).filter(([, v]) => v)) as FiltrosAuditoria;
    setFiltros(limpo);
    setPagina(1);
  }

  const dados = historico.dados;

  return (
    <div className="space-y-4">
      <details className="rounded-cartao bg-white shadow-cartao">
        <summary className="flex min-h-12 items-center px-4 font-bold text-mata-800">Filtrar histórico{Object.keys(filtros).length ? ` (${Object.keys(filtros).length})` : ""}</summary>
        <form onSubmit={aplicar} className="grid gap-3 px-4 pb-4 sm:grid-cols-2 lg:grid-cols-3">
          <CampoSelecao rotulo="Ação" value={rascunho.acao ?? ""} onChange={(e) => setRascunho((r) => ({ ...r, acao: e.target.value }))}>
            <option value="">Todas</option>
            {(tipos.dados?.acoes ?? []).map((a) => (
              <option key={a} value={a}>
                {rotuloDaAcao(a)}
              </option>
            ))}
          </CampoSelecao>
          <CampoSelecao rotulo="Cadastro" value={rascunho.entidade ?? ""} onChange={(e) => setRascunho((r) => ({ ...r, entidade: e.target.value }))}>
            <option value="">Todos</option>
            {(tipos.dados?.entidades ?? []).map((a) => (
              <option key={a} value={a}>
                {ROTULOS_DE_CADASTRO[a] ?? a}
              </option>
            ))}
          </CampoSelecao>
          <CampoTexto rotulo="E-mail de quem fez" type="search" value={rascunho.email ?? ""} onChange={(e) => setRascunho((r) => ({ ...r, email: e.target.value }))} />
          <CampoTexto rotulo="De" type="date" value={rascunho.data_inicio ?? ""} onChange={(e) => setRascunho((r) => ({ ...r, data_inicio: e.target.value }))} />
          <CampoTexto rotulo="Até" type="date" value={rascunho.data_fim ?? ""} onChange={(e) => setRascunho((r) => ({ ...r, data_fim: e.target.value }))} />
          <div className="flex items-end gap-2">
            <Botao type="submit">Filtrar</Botao>
            <Botao
              variante="fantasma"
              onClick={() => {
                setRascunho({});
                setFiltros({});
                setPagina(1);
              }}
            >
              Limpar
            </Botao>
          </div>
        </form>
      </details>

      {historico.erro && !dados ? (
        <EstadoErro mensagem={historico.erro} aoTentarDeNovo={historico.recarregar} />
      ) : !dados ? (
        <Esqueleto className="h-64" />
      ) : dados.registros.length === 0 ? (
        <EstadoVazio titulo="Nenhuma ação encontrada" />
      ) : (
        <>
          {dados.total !== null && <p className="text-tinta-700">{dados.total} ações registradas</p>}
          <ol className={`divide-y divide-creme-200 rounded-cartao bg-white shadow-cartao ${historico.carregando ? "opacity-60" : ""}`}>
            {dados.registros.map((r) => (
              <li key={r.id} className="px-4 py-3">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                  <p className="font-bold text-tinta-900">{rotuloDaAcao(r.acao)}</p>
                  <p className="text-tinta-700">{formatarDataHora(r.created_at)}</p>
                </div>
                <p className="break-all text-tinta-700">{r.user_email ?? "Sistema"}</p>
                {r.detalhes && <p className="mt-0.5 break-words">{limparTextoDoServidor(r.detalhes)}</p>}
              </li>
            ))}
          </ol>
          {dados.totalPaginas > 1 && (
            <nav aria-label="Páginas do histórico" className="flex items-center justify-between gap-2">
              <Botao variante="secundario" disabled={pagina <= 1 || historico.carregando} onClick={() => setPagina((p) => p - 1)}>
                Anteriores
              </Botao>
              <p className="text-center text-tinta-700">
                Página {dados.paginaAtual} de {dados.totalPaginas}
              </p>
              <Botao variante="secundario" disabled={pagina >= dados.totalPaginas || historico.carregando} onClick={() => setPagina((p) => p + 1)}>
                Seguintes
              </Botao>
            </nav>
          )}
        </>
      )}
    </div>
  );
}

export default function AdminPage() {
  const [parametros, setParametros] = useSearchParams();
  const pedida = parametros.get("aba") as IdDaAba | null;
  const aba: IdDaAba = pedida === "nao-aptos" || pedida === "historico" ? pedida : "pessoas";

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-2xl sm:text-3xl">Gestão</h1>
      <p className="mt-0.5 mb-4 text-tinta-700">Área exclusiva da administradora.</p>
      <Abas
        prefixo="admin"
        rotulo="Gestão"
        abas={[
          { id: "pessoas", rotulo: "Pessoas autorizadas" },
          { id: "nao-aptos", rotulo: "Lista sigilosa" },
          { id: "historico", rotulo: "Histórico de ações" },
        ]}
        ativa={aba}
        aoMudar={(nova) => setParametros({ aba: nova }, { replace: true })}
      />
      <PainelDaAba prefixo="admin" id={aba}>
        {aba === "pessoas" && <PessoasAutorizadas />}
        {aba === "nao-aptos" && <NaoAptos />}
        {aba === "historico" && <Historico />}
      </PainelDaAba>
    </div>
  );
}
