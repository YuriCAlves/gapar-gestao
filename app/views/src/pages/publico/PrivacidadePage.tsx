import { Aviso } from "../../components/Estados";

export const VERSAO_POLITICA = "v1.0-2026";

export default function PrivacidadePage() {
  return (
    <article className="mx-auto max-w-3xl space-y-6 rounded-cartao bg-white p-5 shadow-cartao sm:p-8">
      <header className="space-y-3 border-b border-creme-200 pb-5">
        <Aviso tipo="informacao" titulo="Texto provisório — aguarda revisão jurídica">
          Esta versão preliminar descreve como a ONG GAPAR trata dados pessoais na plataforma. O texto passará por revisão jurídica antes da abertura pública dos formulários.
        </Aviso>
        <h1 className="text-2xl font-extrabold text-tinta-900 sm:text-3xl">Política de Privacidade</h1>
        <p className="text-tinta-700">
          Explicamos de forma direta quais informações pedimos, por que precisamos delas e quais são os seus direitos conforme a Lei Geral de Proteção de Dados (LGPD — Lei nº 13.709/2018).
        </p>
      </header>

      <section className="space-y-2" aria-labelledby="sec-quem-somos">
        <h2 id="sec-quem-somos" className="text-xl font-extrabold text-mata-800">
          1. Quem somos
        </h2>
        <p className="leading-relaxed text-tinta-900">
          A <strong>ONG GAPAR</strong> (Grupo de Apoio e Proteção Animal) é a organização responsável pelo cuidado dos animais acolhidos e pelo tratamento dos dados pessoais coletados nesta plataforma.
        </p>
      </section>

      <section className="space-y-2" aria-labelledby="sec-dados">
        <h2 id="sec-dados" className="text-xl font-extrabold text-mata-800">
          2. Quais dados coletamos
        </h2>
        <ul className="list-disc space-y-1.5 pl-5 leading-relaxed text-tinta-900">
          <li>
            <strong>Interessados em adotar (pré-triagem):</strong> nome completo, CPF, telefone, cidade/estado e respostas sobre rotina e moradia informadas voluntariamente no formulário.
          </li>
          <li>
            <strong>Adotantes:</strong> nome completo, telefone, CPF, endereço, data da adoção e registro do aceite do termo de guarda responsável (incluindo data, hora e canal do aceite).
          </li>
          <li>
            <strong>Pessoas autorizadas da equipe (voluntárias e administradoras):</strong> nome e e-mail Google usados para controle de acesso e histórico interno das ações realizadas no abrigo.
          </li>
        </ul>
        <p className="leading-relaxed text-tinta-700">
          Nenhuma informação pessoal de adotantes ou candidatas é publicada na vitrine de adoção nem na carteira pública de vacinas.
        </p>
      </section>

      <section className="space-y-2" aria-labelledby="sec-finalidade">
        <h2 id="sec-finalidade" className="text-xl font-extrabold text-mata-800">
          3. Para quê usamos esses dados
        </h2>
        <ul className="list-disc space-y-1.5 pl-5 leading-relaxed text-tinta-900">
          <li>Avaliar se o ambiente é seguro e adequado para o bem-estar do animal (adoção responsável).</li>
          <li>Formalizar o termo de adoção, entregar a carteira digital de vacinas e fazer os contatos de acompanhamento pós-adoção.</li>
          <li>Prevenir situações de risco ou maus-tratos já registradas internamente pela administração da ONG.</li>
          <li>Garantir segurança contra robôs e acessos indevidos nos formulários públicos.</li>
        </ul>
        <p className="leading-relaxed text-tinta-700">
          Seus dados nunca são vendidos, alugados nem compartilhados para fins comerciais ou publicitários.
        </p>
      </section>

      <section className="space-y-2" aria-labelledby="sec-retencao">
        <h2 id="sec-retencao" className="text-xl font-extrabold text-mata-800">
          4. Por quanto tempo guardamos
        </h2>
        <ul className="list-disc space-y-1.5 pl-5 leading-relaxed text-tinta-900">
          <li>
            <strong>Candidaturas recusadas ou desistentes:</strong> os dados pessoais são mantidos por até <strong>180 dias</strong> após o encerramento da análise e depois são anonimizados de forma irreversível.
          </li>
          <li>
            <strong>Adoções formalizadas e termos aceitos:</strong> preservados para comprovação da guarda responsável, acompanhamento do animal e cumprimento de obrigações legais.
          </li>
          <li>
            <strong>Registros históricos de auditoria interna:</strong> mantidos em trilha imutável para segurança e rastreabilidade das ações da equipe. Registros anteriores à atualização v5.1 podem conter nomes gravados historicamente e permanecem restritos apenas à administração.
          </li>
        </ul>
      </section>

      <section className="space-y-2" aria-labelledby="sec-direitos">
        <h2 id="sec-direitos" className="text-xl font-extrabold text-mata-800">
          5. Seus direitos como titular
        </h2>
        <p className="leading-relaxed text-tinta-900">
          Você pode solicitar à ONG GAPAR, a qualquer momento:
        </p>
        <ul className="list-disc space-y-1.5 pl-5 leading-relaxed text-tinta-900">
          <li>Confirmação de que tratamos seus dados e acesso às informações guardadas sobre você.</li>
          <li>Correção de dados incompletos, inexatos ou desatualizados.</li>
          <li>Anonimização ou eliminação de dados pessoais quando não houver obrigação legal ou necessidade de preservação do termo de adoção.</li>
          <li>Revogação do consentimento dado em candidaturas ainda em andamento.</li>
        </ul>
      </section>

      <section className="space-y-2" aria-labelledby="sec-contato">
        <h2 id="sec-contato" className="text-xl font-extrabold text-mata-800">
          6. Contato
        </h2>
        <p className="leading-relaxed text-tinta-900">
          Para tirar dúvidas ou exercer qualquer direito previsto nesta política, procure diretamente a coordenação da <strong>ONG GAPAR</strong> pelos canais oficiais divulgados pela organização.
        </p>
      </section>

      <footer className="border-t border-creme-200 pt-4 text-sm text-tinta-700">
        Versão do documento: <strong className="text-tinta-900">{VERSAO_POLITICA}</strong>
      </footer>
    </article>
  );
}
