# Prompt para o Antigravity — Rodada 4 (fechar a Fase 2 até o CP-05)

> Copie o bloco abaixo e cole no Antigravity.

---

Você continua na ampliação v5 do GAPAR Gestão, pasta `C:\Trabalho_gapar`, branch `feat/cp01-nucleo`. Nesta rodada você termina **todas as telas da Fase 2, até o CP-05**.

O Claude Code está, **ao mesmo tempo e na mesma pasta**, construindo o back-end dos CP-03, CP-04 e CP-05 (modelos, migrações `0005`–`0007`, rotas). Você trabalha sobre os **contratos já publicados**, com dados simulados nos testes, e integra com a API real quando cada handoff chegar.

## Leia antes de começar
1. `docs/handoff/ANTIGRAVITY_INSTRUCOES.md`: regras, seção 2 (propriedade de arquivos) e seção 5 (o "pronto quando" de cada CP).
2. `docs/handoff/CP02-claude-para-antigravity.md`: o contrato real do CP-02 e os 3 ajustes pedidos no `og_controller.py`.
3. `app/views/src/types/contratos.ts`: a seção **"CONTRATOS PREVISTOS DA FASE 2"** é o contrato dos CP-03, 04 e 05. Use os tipos como estão e não altere esse arquivo.
4. `docs/sdd/CP03_05_FASE2_SPEC.md`: o que o back-end vai fazer, incluindo os códigos 409/422 que você precisa tratar.

## Regras (iguais às da rodada 3)
- **Não edite** `app/models/**`, `migrations/**`, `app/controllers/**` (exceto `og_controller.py`, que é seu, e a linha de registro autorizada na tarefa 1), `app/services/**`, `app/utils/**`, `app/__init__.py`, `app/config.py`, `vercel.json`, `tests/**`, `types/contratos.ts`, `api/public.ts` nem `docs/sdd/**`.
- **Não faça commit** e não rode `git checkout`, `git stash`, `git reset` nem `git add`. O Claude Code faz os commits com o perfil do usuário, depois da revisão.
- Leia cada arquivo imediatamente antes de editar. Nunca reescreva por inteiro um arquivo que não é seu.
- Nenhuma dependência nova nesta rodada.
- Toda tela nova fica atrás da flag certa (`estoque`, `microchip`, `isolamento`) e é carregada com `lazy()` quando não for do uso diário.
- Se precisar de algo fora da sua lista, **pare e registre o pedido** no handoff.

---

## Tarefa 1 · Fechar o CP-02 (faça primeiro)

**a. `og_controller.py`:** os 3 ajustes do handoff CP-02.
- Use só `current_app.config["PUBLIC_BASE_URL"]`. **Nunca `request.url_root`.** Se a variável estiver vazia, omita o `og:url`.
- `Content-Type` com um único `charset`.
- O fallback institucional responde com `Cache-Control: no-store`. A prévia de um animal real usa cache de 60 s.

**b. Registro do blueprint:** registre o `og_bp` em `BLUEPRINTS`, em `app/controllers/__init__.py`. Mexa só no import e nessa tupla. Depois rode `python -m pytest -q`: o canário passa a exercitar `/adote/<slug>` e **precisa continuar verde**.

**c. Integração real da vitrine** (tarefa 5 da rodada 3):
- teste `/adote`, `/adote/:slug` e a seção da `AbaDados` contra o back-end real, com `FEATURE_VITRINE=true` no `.env`;
- trate o 422 (animal não disponível ou congelado), o 409 e o 400 com mensagens claras.

## Tarefa 2 · CP-03 Estoque (telas)

**a. `api/estoque.ts`:** uma função para cada rota do contrato (`ItemEstoque`, `DetalheItemEstoque`, `SugestaoFefo`, movimentos), com Vitest usando `fetch` simulado.

**b. Página `/estoque`** (`lazy`, flag `estoque`, na gaveta "Mais"):
- lista de itens com saldo total, selo "Acabando" (`abaixo_do_minimo`) e "Vence em X dias" (`proxima_validade`);
- filtro por categoria;
- botão "Novo item" (só Administradora).

**c. Detalhe do item:**
- lotes em ordem FEFO, com vencidos acinzentados e o selo "Vencido";
- histórico de movimentos, **sem botão de editar nem de apagar** (RN19);
- modais "Entrada de lote" (novo lote com quantidade) e "Ajustar saldo" (tipo, quantidade e **motivo obrigatório**).
- Trate o `409` de saldo insuficiente com: "Não há saldo suficiente neste lote."

**d. `<SeletorLoteFefo />`** nos formulários de **Vacina** (`AbaSaude`) e **Baixa de medicação** (`AbaMedicacoes`):
- consulta `/api/estoque/fefo` e sugere o `sugerido_id`;
- mostra os lotes vencidos desabilitados;
- quantidade padrão 1;
- envia `lote_id` e `quantidade` nas rotas existentes;
- trate o `422` (lote vencido) e o `409` (saldo).
- Com a flag desligada, o seletor não aparece e o formulário continua igual ao de hoje.

**e. `HojePage`:** bloco "Estoque" (só Administradora, com a flag ligada) mostrando `estoque.acabando` e `estoque.vencendo` (`AlertasEstoqueHoje`). Se o campo vier ausente, não mostre nada.

## Tarefa 3 · CP-04 Microchip (telas; utilitários e etiqueta já prontos)
- **Campo "Número do microchip"** no `FormularioAnimal`: use a sua `mascararMicrochip`, só dígitos, sem `maxLength`, exibido como `000 000 000 000 000`, com erro ao sair do campo se não tiver 15 dígitos.
- **`409` `ConflitoMicrochip`:** mostre "Este número já está no cadastro de {animal_nome}", com link para `/animais/{animal_id}`.
- **Leitor USB em `/animais`:** ligue o seu `useLeitorMicrochip` a `GET /api/animais/microchip/:numero`.
  - Se encontrar, abre a ficha direto.
  - Se der `404`, mostre "Nenhum animal com este microchip."
- **Na ficha:** mostre o número formatado e passe `numero_microchip` para a `<DialogoEtiquetaBaia />`.
- Tudo atrás da flag `microchip`.

## Tarefa 4 · CP-05 Isolamento e Kanban (telas)

**a. `api/isolamentos.ts`:** listar, abrir e encerrar, como no contrato (`IsolamentoRegistro`), com Vitest.

**b. Na ficha:**
- **banner de isolamento** quando `isolamento_aberto` não for nulo (motivo, desde quando, previsão);
- botões **"Colocar em isolamento"** (diálogo com motivo obrigatório até 200 caracteres, protocolo de cuidados, data de início e previsão de fim) e **"Encerrar isolamento"** (observações de alta);
- histórico de isolamentos.
- Trate o `409` com "Este animal já está em isolamento" e o `422` com "Ficha congelada (adotado ou óbito)".

**c. `<SeloIsolamento />`** nos cards de `/animais`, usando `isolamento_aberto` de cada item.

**d. Lista ↔ Quadro em `/animais`:**
- um botão alterna entre a lista e o Kanban;
- uma coluna por status operacional;
- **drag-and-drop HTML5 nativo** no desktop, sem biblioteca;
- em 360px, botão **"Mover…"** que abre uma folha inferior só com os status permitidos;
- usa o `PATCH /api/animais/:id/status` existente;
- `adotado` **nunca** aparece como destino, e os cartões adotados ou em óbito não são arrastáveis;
- trate o erro do servidor, voltando o cartão para a coluna original.
- Lembre a última visão escolhida em `localStorage`, dentro de `try/catch`.

**e. `HojePage`:** bloco prioritário **"Em isolamento"** no topo, com `isolamentos`, mostrado só com a flag ligada.

## Tarefa 5 · Homologação da Fase 2
Em `scripts/homologacao.py`, que é seu, acrescente os cenários da Fase 2, cada um **pulado com aviso quando a flag correspondente estiver desligada**:
- **vitrine:** publicar → aparece em `/api/public/animais` → mudar o status → some;
- **estoque:**
  - criar um item e um lote;
  - consumir o lote ao registrar uma vacina;
  - tentar consumir além do saldo e receber 409;
- **microchip:** cadastrar com número → buscar pelo número → tentar o mesmo número em outro animal e receber 409;
- **isolamento:** abrir → tentar abrir de novo e receber 409 → encerrar.

O script precisa limpar o que criar (exclusão lógica ou despublicação).

---

## Integração com a API real
O Claude Code vai publicar os handoffs `docs/handoff/CP03-claude-para-antigravity.md`, `CP04-…` e `CP05-…`. Até lá, use dados simulados nos testes. Quando cada handoff chegar, teste contra o back-end real e ajuste o que divergir.

## Ao terminar
1. Rode `npm run build` (anote os chunks: `/estoque` e o Kanban precisam ficar fora do `index`), `npm test` e `python -m pytest -q`.
2. Crie `docs/handoff/CP05-antigravity-para-claude.md`, cobrindo as tarefas 1 a 5, com:
   - os arquivos alterados;
   - as evidências;
   - as pendências;
   - a confirmação de propriedade de arquivos (cite a exceção usada na tarefa 1b).
