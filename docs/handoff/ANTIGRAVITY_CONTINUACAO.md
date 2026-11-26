# Plano de Continuação do Antigravity (em paralelo ao Claude Code)

> **Data:** 26/11/2026 · **Vale junto com:** [ANTIGRAVITY_INSTRUCOES.md](ANTIGRAVITY_INSTRUCOES.md) (regras e propriedade de arquivos) e [CP01-claude-para-antigravity.md](CP01-claude-para-antigravity.md) (revisão do seu CP-01).
> **Ideia:** você nunca fica parado esperando o back-end. Cada trilha abaixo diz **o que você pode fazer agora** e **do que ela depende**.

---

## 0. Como os dois trabalham ao mesmo tempo nesta pasta

Os dois estamos editando **a mesma pasta de trabalho**. Para não haver conflito:
1. Só altere arquivos que são seus (seção 2 das instruções). Eu também não toco nos seus.
2. **Nunca reescreva um arquivo inteiro que você não abriu nesta sessão.** O SDD já ficou vazio uma vez por escrita concorrente.
3. Antes de cada bloco grande, rode `git status` e confira se só os seus arquivos mudaram desde o último passo.
4. Não rode `git checkout`, `git stash`, `git reset` nem formatadores no repositório inteiro. Eles mexeriam nos arquivos do outro.

---

## 1. Trilha A — Fechar o CP-01 (prioridade máxima, comece já)

| # | Tarefa | Depende de | Pronto quando |
| :-: | :--- | :--- | :--- |
| A1 | 🔴 `.env.example`: deixar **vazios** `PII_FERNET_KEYS`, `PII_HMAC_KEY`, `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY` e `CRON_SECRET`; instruções e chaves de teste só em comentários. | nada | Copiar `.env.example` para `.env` sobe o dev sem erro ao salvar CPF. |
| A2 | 🔴 `CampoMascarado`: remover o `maxLength` do `<input>`; telefone colado com 12–13 dígitos começando por `55` descarta o DDI. Mais casos no Vitest: colar `+55 (41) 99999-8888` e colar `CPF: 529.982.247-25`. | nada | Os dois casos dão `41999998888` e `52998224725`. |
| A3 | 🟡 `NaoAptos`: com CPF ou telefone incompleto, esconder a lista e mostrar só a dica. | nada | A lista inteira não aparece como se fosse resultado da busca. |
| A4 | 🟡 `DEPLOY.md`: a rotação depende do comando `flask pii-rotate` (a ser entregue); não remover a chave antiga antes disso. | nada | Texto ajustado. |
| A5 | `FlagsContext.tsx` + `useFlags()` + `<RequerFlag>` + `<RotaComFlag>` consumindo `obterConfigPublica()` de `api/public.ts`. | ✅ contrato pronto | Tudo desligado até a resposta chegar ou se ela falhar; teste no Vitest com `fetch` simulado. |
| A6 | Pôr `/adote`, `/adote/:slug` (flag `vitrine`), `/termo/:token` (`termo_digital`) e `/carteira/:token` (`carteira`) atrás de `<RotaComFlag>`. `/privacidade` fica sempre aberta. | A5 | Com a flag desligada, a rota mostra `NaoEncontradaPage`. |
| A7 | Gaveta **"Mais"** na navegação interna (folha inferior, botões `min-h-14`). Itens futuros aparecem só com flag **e** perfil. | A5 | Em 360px, as 4 abas continuam iguais e a gaveta abre e fecha com o polegar. |
| A8 | Criar `docs/handoff/CP01-antigravity-para-claude.md` (seção 3 das instruções), com prints 360px e desktop de `/privacidade`, da busca da lista sigilosa e da adoção. | A1–A7 | Eu rodo a revisão final (`gapar-frontend-ux` + `gapar-qa-gatekeeper`). |

---

## 2. Trilha B — Telas da vitrine (CP-02), em paralelo ao meu back-end

O **contrato previsto** já está em `app/views/src/types/contratos.ts`: `AnimalPublico`, `PaginaVitrine`, `RespostaAnimalPublico` e `CamposVitrineDaFicha`, com rotas, códigos e comportamento descritos nos comentários. Enquanto eu faço a migração `0004` e as rotas, você monta as telas sobre esses tipos.

| # | Tarefa | Depende de | Observação |
| :-: | :--- | :--- | :--- |
| B1 | `api/vitrine.ts`: `listarVitrine(pagina)` e `obterAnimalPublico(slug)`. Siga o padrão de `api/public.ts` (`credentials: "omit"`, sem `requisitar`). O 404 vira o estado "já encontrou um lar". | contrato previsto | **Não edite** `api/public.ts`; crie um arquivo seu. |
| B2 | Página `/adote`: grade de cards em 360px (1 coluna) e desktop (3 colunas), "Carregar mais" com `tem_mais`, estados vazio, carregando e erro. Fotos com `loading="lazy"` e `width`/`height` fixos. | B1 | Use dados simulados num teste Vitest até a rota existir. |
| B3 | Página `/adote/:slug`: foto, dados e `descricao_publica`. O botão "Quero adotar pelo WhatsApp" monta `wa.me/<whatsapp_adocao>?text=` com mensagem contendo **só o nome do animal**. Sem `whatsapp_adocao`, o botão não aparece. | B1, A5 | Com `candidaturas_pausadas`, mostrar só o WhatsApp (o formulário do CP-08 vem depois). |
| B4 | Ficha (Admin) na `AbaDados`: interruptor "Publicar na vitrine", campo "Descrição para o público" com contador até 600 e "Pausar candidaturas". O interruptor fica desabilitado, com explicação, fora de `disponível`. Tratar o `422`. | contrato previsto | A chamada `PATCH /api/animais/:id/vitrine` vai em `api/animais.ts` (seu). |
| B5 | `app/controllers/og_controller.py`: HTML mínimo com `og:title`, `og:description`, `og:image`, `og:url`, tudo com `markupsafe.escape`, e fallback institucional. | **meu handoff do CP-02** (precisa do campo `slug_publico` no modelo) | Pode escrever o HTML e o teste com um animal simulado; ligue ao modelo quando o campo existir. |

**Pronto quando:** as telas funcionam com dados simulados, e o Vitest cobre a montagem do link `wa.me` (nome com acento e espaço) e o estado 404. A integração real e a validação do preview no WhatsApp ficam para quando eu entregar o handoff do CP-02.

---

## 3. Trilha C — Partes do CP-04 (microchip) que não dependem do banco

| # | Tarefa | Depende de |
| :-: | :--- | :--- |
| C1 | `utils/microchip.ts`: `validarMicrochip` (exatamente 15 dígitos), `formatarMicrochip` (`000 000 000 000 000`) e `mascararMicrochip` (mesma técnica do CPF, sem `maxLength`), mais Vitest. | nada |
| C2 | Detector de leitor USB HID em `/animais`: 15 dígitos seguidos de `Enter` em menos de ~100 ms disparam a busca **sem debounce**. Isolar num hook `useLeitorMicrochip` testável. | nada; a busca real liga no CP-04 |
| C3 | `<DialogoEtiquetaBaia />` A6 retrato com `@media print`. `qrcode` carregado por `import()` só ao abrir o diálogo. Pode usar dados da ficha atual; o número do microchip entra no CP-04. | nada |

---

## 4. Ordem recomendada e o que eu faço no mesmo período

| Período | Antigravity | Claude Code |
| :--- | :--- | :--- |
| Agora | Trilha A (A1→A8) | Preparar a `0003b` (remoção das colunas em claro, **sem aplicar**) e o `flask pii-rotate` |
| Depois do A8 | Trilha B (B1→B4) | Revisão do seu CP-01; spec e núcleo do CP-02: migração `0004`, RN17, `GET /api/public/animais[/<slug>]`, `PATCH /vitrine`, rewrite por User-Agent no `vercel.json` |
| Depois do B4 | Trilha C enquanto espera | Handoff do CP-02 → você faz o B5 e integra B1–B4 com a API real |

**Regra de parada:** se uma tarefa exigir mudar um arquivo meu ou um contrato, **pare e escreva o pedido** no seu handoff, em vez de contornar.
