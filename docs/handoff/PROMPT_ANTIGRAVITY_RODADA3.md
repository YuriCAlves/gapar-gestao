# Prompt para o Antigravity — Rodada 3 (em paralelo ao CP-02 do Claude Code)

> Copie o bloco abaixo e cole no Antigravity.

---

Você continua na ampliação v5 do GAPAR Gestão, pasta `C:\Trabalho_gapar`, branch `feat/cp01-nucleo`. O Claude Code está trabalhando **ao mesmo tempo na mesma pasta**, no núcleo do CP-02: modelo, migração `0004`, rotas públicas da vitrine e `vercel.json`.

## Antes de começar, leia
1. `docs/handoff/ANTIGRAVITY_INSTRUCOES.md`: as regras e a propriedade de arquivos (seção 2), que continuam valendo.
2. `docs/handoff/CP01-claude-para-antigravity.md`, **seção 4 inteira**: a mudança de contrato da busca e os 9 achados da revisão.
3. `docs/sdd/CP02_VITRINE_SPEC.md`: o que o Claude Code está construindo agora, para você saber o que vai chegar.
4. `app/views/src/types/contratos.ts`: o contrato. Você usa, mas não altera.

## Regras desta rodada
- **Não edite** `app/models/**`, `migrations/**`, `app/controllers/**`, `app/services/**`, `app/utils/**`, `app/__init__.py`, `app/config.py`, `vercel.json`, `tests/**`, `app/views/src/types/contratos.ts`, `app/views/src/api/public.ts` nem `docs/sdd/**`. A única exceção está na tarefa 4.
- **Não faça commit**, e não rode `git checkout`, `git stash`, `git reset` nem `git add`. O Claude Code faz os commits com o perfil do usuário, depois da revisão.
- Leia cada arquivo imediatamente antes de editar e nunca reescreva por inteiro um arquivo que não é seu.
- Se precisar mudar algo que não é seu, **pare e registre o pedido** no seu handoff.

## Tarefas, nesta ordem

### 1. Condição para o merge do CP-01 (faça primeiro)
a. **`api/admin.ts`:** a busca por `cpf`, `telefone` ou nome passa a ser `requisitar("/api/admin/nao-aptos/busca", { metodo: "POST", json: { cpf } | { telefone } | { q } })`.
   - Sem filtro, continua `GET /api/admin/nao-aptos`.
   - Hoje a busca por CPF ou telefone responde 400, porque o servidor já recusa dado pessoal na URL.
b. **`docs/DEPLOY.md`:** acrescente o passo da **impressão digital** antes do backfill, como no §7 de `docs/sdd/CP01_NUCLEO_SPEC.md`:
   - comparar a linha `Chaves PII em uso: fernet=… hmac=…` do log da Vercel com a saída de `flask pii-backfill --dry-run`;
   - se forem diferentes, **parar**.

### 2. Os 9 achados da revisão de front-end (seção 4 do handoff do CP-01)
Faça os itens 1, 2 e 3 primeiro:
1. **Busca de CPF/telefone:** mostre `<Esqueleto>` em vez de "Ninguém encontrado" enquanto carrega.
2. **DDI 55:** descarte o DDI só em colagem (2 ou mais dígitos de uma vez), nunca numa digitação no meio do número. Cubra com teste no Vitest.
3. **`FlagsContext`:** tempo limite de cerca de 8 s, mantendo tudo fechado. Não use `abort()`.

Depois, os itens 4 a 8:

4. **Testes do provider:** teste o `FlagsProvider`, o `<RequerFlag>` e o `<RotaComFlag>` com `renderToString`.
5. **`<Suspense>`:** coloque um `<Suspense>` por layout, em volta do `<Outlet/>`.
6. **Logo:** o logo público aponta para `/adote` só com a flag `vitrine` ligada.
7. **404 público:** `/termo`, `/carteira/` e `/adote/x/y` mostram o 404 público, sem passar pelo `AuthProvider`.
8. **Gaveta "Mais":** use `NavLink`, com `aria-current`.

O item 9 (os prints) fica para quando houver Preview.

### 3. C3 · Etiqueta da baia com QR code
- Pode instalar `qrcode` e `@types/qrcode`, que são as únicas dependências novas autorizadas.
- Crie o `<DialogoEtiquetaBaia />` em A6 retrato, com `@media print`.
- Carregue o `qrcode` por `import()` só ao abrir o diálogo. Confira no `npm run build` que ele fica num chunk separado.
- O número do microchip entra no CP-04; por enquanto use os dados da ficha.

### 4. B5 · Prévia do link no WhatsApp (Open Graph): comece a escrever, ligue quando eu avisar
O contrato está fixado na REQ-29 da spec do CP-02:

**`app/controllers/og_controller.py`:**
- `og_bp = Blueprint("og", __name__)`;
- rota `GET /adote/<slug>`, com o nome de função **`preview_animal`** (o endpoint precisa ser `og.preview_animal`);
- usa `Animal.buscar_publicado(slug)`, que devolve o animal ou `None`.

**HTML mínimo:**
- `<title>`, `og:title`, `og:description`, `og:image` e `og:url`;
- **todo valor passa por `markupsafe.escape`**;
- `og:image` só quando `foto_url` começa com `https://`;
- no `None`, um fallback institucional da ONG, sem nenhum dado de animal.

**Cuidados:**
- Responda com `Cache-Control` adequado, usando o `cache_publico` de `app/utils/publico.py`.
- Nunca use `to_dict()`.
- **Exceção de propriedade:** você pode acrescentar uma linha em `app/controllers/__init__.py` para registrar o `og_bp`, mas só depois do meu handoff do CP-02, quando `Animal.buscar_publicado` existir.

### 5. Integração da vitrine com a API real
Depois do meu handoff `docs/handoff/CP02-claude-para-antigravity.md`:
- teste `/adote`, `/adote/:slug` e o controle da `AbaDados` contra o back-end real;
- ajuste o que divergir;
- valide o 422, quando o animal não está disponível.

## Ao terminar
1. Rode `npm run build`, `npm test` e `python -m pytest -q`. O `pytest` é obrigatório nesta rodada.
2. Crie `docs/handoff/CP02-antigravity-para-claude.md` com:
   - os arquivos alterados;
   - as evidências (contagens e tamanhos dos chunks);
   - o que ficou pendente;
   - a confirmação de que não tocou em arquivos fora da sua lista, citando a exceção da tarefa 4 se ela foi usada.
