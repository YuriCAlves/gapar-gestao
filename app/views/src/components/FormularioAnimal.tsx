import type { DadosAnimal, Porte, Sexo } from "../types";
import { CampoArea, CampoTexto, GrupoDeOpcoes, Interruptor } from "./Campos";

/** Valores do formulário como texto, do jeito que a pessoa digita. */
export interface ValoresDoAnimal {
  nome: string;
  sexo: Sexo | "";
  porte: Porte | "";
  idade_estimada: string;
  raca: string;
  pelagem: string;
  peso_kg: string;
  local_resgate: string;
  motivo_resgate: string;
  is_castrado: boolean;
  is_microchipado: boolean;
  is_idoso: boolean;
  temCuidados: boolean;
  cuidados_especiais: string;
  localizacao_baia: string;
  codigo_identificador: string;
}

export type ErrosDoAnimal = Partial<Record<keyof ValoresDoAnimal, string>>;

export const VALORES_INICIAIS: ValoresDoAnimal = {
  nome: "",
  sexo: "",
  porte: "Médio",
  idade_estimada: "",
  raca: "",
  pelagem: "",
  peso_kg: "",
  local_resgate: "",
  motivo_resgate: "",
  is_castrado: false,
  is_microchipado: false,
  is_idoso: false,
  temCuidados: false,
  cuidados_especiais: "",
  localizacao_baia: "",
  codigo_identificador: "",
};

export function valoresDoAnimal(animal: DadosAnimal): ValoresDoAnimal {
  return {
    nome: animal.nome,
    sexo: animal.sexo,
    porte: animal.porte,
    idade_estimada: animal.idade_estimada ?? "",
    raca: animal.raca ?? "",
    pelagem: animal.pelagem ?? "",
    peso_kg: animal.peso_kg !== null && animal.peso_kg !== undefined ? String(animal.peso_kg).replace(".", ",") : "",
    local_resgate: animal.local_resgate ?? "",
    motivo_resgate: animal.motivo_resgate ?? "",
    is_castrado: animal.is_castrado,
    is_microchipado: animal.is_microchipado,
    is_idoso: animal.is_idoso,
    temCuidados: Boolean(animal.cuidados_especiais?.trim()),
    cuidados_especiais: animal.cuidados_especiais ?? "",
    localizacao_baia: animal.localizacao_baia ?? "",
    codigo_identificador: animal.codigo_identificador ?? "",
  };
}

export function validarAnimal(v: ValoresDoAnimal): ErrosDoAnimal {
  const erros: ErrosDoAnimal = {};
  if (!v.nome.trim()) erros.nome = "Informe o nome ou um apelido provisório.";
  if (!v.sexo) erros.sexo = "Escolha o sexo.";
  if (!v.porte) erros.porte = "Escolha o porte.";
  if (v.peso_kg.trim()) {
    const peso = Number(v.peso_kg.replace(",", "."));
    if (!Number.isFinite(peso) || peso <= 0) erros.peso_kg = "Informe o peso em quilos, por exemplo 12,5.";
    else if (peso > 120) erros.peso_kg = "Confira o peso: parece alto demais.";
  }
  if (v.temCuidados && !v.cuidados_especiais.trim()) erros.cuidados_especiais = "Descreva os cuidados necessários.";
  return erros;
}

const textoOuNulo = (texto: string) => (texto.trim() ? texto.trim() : null);

/** Converte para o formato da API. Só chamar depois de validarAnimal sem erros. */
export function dadosDoAnimal(v: ValoresDoAnimal): DadosAnimal {
  return {
    nome: v.nome.trim(),
    sexo: v.sexo as Sexo,
    porte: v.porte as Porte,
    idade_estimada: textoOuNulo(v.idade_estimada),
    raca: textoOuNulo(v.raca),
    pelagem: textoOuNulo(v.pelagem),
    peso_kg: v.peso_kg.trim() ? Number(v.peso_kg.replace(",", ".")) : null,
    local_resgate: textoOuNulo(v.local_resgate),
    motivo_resgate: textoOuNulo(v.motivo_resgate),
    is_castrado: v.is_castrado,
    is_microchipado: v.is_microchipado,
    is_idoso: v.is_idoso,
    cuidados_especiais: v.temCuidados ? textoOuNulo(v.cuidados_especiais) : null,
    localizacao_baia: textoOuNulo(v.localizacao_baia),
    codigo_identificador: textoOuNulo(v.codigo_identificador),
  };
}

interface PropsDoFormulario {
  valores: ValoresDoAnimal;
  erros: ErrosDoAnimal;
  aoMudar: <K extends keyof ValoresDoAnimal>(campo: K, valor: ValoresDoAnimal[K]) => void;
}

/** Campos do cadastro do animal, na ordem do atendimento: o essencial primeiro. */
export function CamposDoAnimal({ valores, erros, aoMudar }: PropsDoFormulario) {
  return (
    <div className="space-y-6">
      <fieldset className="space-y-4 rounded-cartao bg-white p-4 shadow-cartao">
        <legend className="sr-only">Identificação</legend>
        <CampoTexto
          rotulo="Nome ou apelido"
          obrigatorio
          value={valores.nome}
          onChange={(e) => aoMudar("nome", e.target.value)}
          erro={erros.nome}
          placeholder="Ex.: Thor, ou Pretinho da praça"
          autoComplete="off"
          maxLength={100}
          name="nome"
        />
        <GrupoDeOpcoes
          rotulo="Sexo"
          nome="sexo"
          obrigatorio
          valor={valores.sexo}
          aoMudar={(v) => aoMudar("sexo", v)}
          erro={erros.sexo}
          opcoes={[
            { valor: "Macho", rotulo: "Macho" },
            { valor: "Fêmea", rotulo: "Fêmea" },
          ]}
        />
        <GrupoDeOpcoes
          rotulo="Porte"
          nome="porte"
          obrigatorio
          valor={valores.porte}
          aoMudar={(v) => aoMudar("porte", v)}
          erro={erros.porte}
          opcoes={[
            { valor: "Pequeno", rotulo: "Pequeno" },
            { valor: "Médio", rotulo: "Médio" },
            { valor: "Grande", rotulo: "Grande" },
          ]}
        />
        <div className="grid grid-cols-2 gap-3">
          <CampoTexto rotulo="Idade aproximada" value={valores.idade_estimada} onChange={(e) => aoMudar("idade_estimada", e.target.value)} placeholder="Ex.: 3 anos" maxLength={50} />
          <CampoTexto
            rotulo="Peso (kg)"
            inputMode="decimal"
            value={valores.peso_kg}
            onChange={(e) => aoMudar("peso_kg", e.target.value)}
            erro={erros.peso_kg}
            placeholder="Ex.: 12,5"
          />
          <CampoTexto rotulo="Raça" value={valores.raca} onChange={(e) => aoMudar("raca", e.target.value)} placeholder="Sem raça definida" maxLength={100} />
          <CampoTexto rotulo="Pelagem" value={valores.pelagem} onChange={(e) => aoMudar("pelagem", e.target.value)} placeholder="Ex.: caramelo" maxLength={50} />
        </div>
      </fieldset>

      <fieldset className="space-y-4 rounded-cartao bg-white p-4 shadow-cartao">
        <legend className="float-left mb-1 text-lg font-extrabold text-tinta-900">Resgate</legend>
        <CampoTexto className="clear-both" rotulo="Local do resgate" value={valores.local_resgate} onChange={(e) => aoMudar("local_resgate", e.target.value)} placeholder="Ex.: Bairro Centro, perto do mercado" maxLength={200} />
        <CampoArea rotulo="Motivo e história do resgate" value={valores.motivo_resgate} onChange={(e) => aoMudar("motivo_resgate", e.target.value)} placeholder="Como foi encontrado, estado em que estava..." />
        <div className="grid grid-cols-2 gap-3">
          <CampoTexto rotulo="Canil ou baia" value={valores.localizacao_baia} onChange={(e) => aoMudar("localizacao_baia", e.target.value)} placeholder="Ex.: Canil 04" maxLength={100} />
          <CampoTexto rotulo="Código ou coleira" value={valores.codigo_identificador} onChange={(e) => aoMudar("codigo_identificador", e.target.value)} placeholder="Opcional" maxLength={50} />
        </div>
      </fieldset>

      <fieldset className="rounded-cartao bg-white px-4 py-2 shadow-cartao">
        <legend className="sr-only">Características especiais</legend>
        <div className="divide-y divide-creme-200">
          <Interruptor rotulo="Castrado" dica="Já passou pela castração" marcado={valores.is_castrado} aoMudar={(v) => aoMudar("is_castrado", v)} />
          <Interruptor rotulo="Idoso" dica="Pode ser adotado normalmente" marcado={valores.is_idoso} aoMudar={(v) => aoMudar("is_idoso", v)} />
          <Interruptor rotulo="Tem microchip" marcado={valores.is_microchipado} aoMudar={(v) => aoMudar("is_microchipado", v)} />
          <Interruptor rotulo="Precisa de cuidados especiais" dica="Deficiência, doença crônica, dieta..." marcado={valores.temCuidados} aoMudar={(v) => aoMudar("temCuidados", v)} />
        </div>
        {valores.temCuidados && (
          <CampoArea
            className="pb-3"
            rotulo="Quais cuidados?"
            obrigatorio
            value={valores.cuidados_especiais}
            onChange={(e) => aoMudar("cuidados_especiais", e.target.value)}
            erro={erros.cuidados_especiais}
            placeholder="Ex.: cego de um olho, ração renal"
          />
        )}
      </fieldset>
    </div>
  );
}
