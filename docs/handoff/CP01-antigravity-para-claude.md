# Handoff CP-01 · Antigravity → Claude Code

> **Data:** 26/11/2026  
> **Branch atual:** `feat/cp01-nucleo` (pasta de trabalho compartilhada — sem `git checkout`/`git stash`/`git reset` conforme §0 de `ANTIGRAVITY_CONTINUACAO.md`)  
> **Último commit base:** `0197d3a`  
> **Escopo entregue:** Trilha A completa (**A1 a A8** — correções da revisão do CP-01 + `FlagsContext`, `<RotaComFlag>` e gaveta `"Mais"`).

---

## 1. Resumo das Correções e Entregas (A1–A7)

- **A1 (`.env.example`):** deixados **vazios** os campos `PII_FERNET_KEYS=`, `PII_HMAC_KEY=`, `TURNSTILE_SITE_KEY=`, `TURNSTILE_SECRET_KEY=`, `PUBLIC_WHATSAPP_ADOCAO=` e `CRON_SECRET=`. Instruções de geração e chaves de teste da Cloudflare ficaram apenas em comentários.
- **A2 (`mascaras.ts`, `Campos.tsx`, `mascaras.test.ts`):**
  - Removido `maxLength` do `<input>` em `CampoMascarado` (o limite de 11 dígitos é aplicado após extrair dígitos, sem truncar colagens formatadas).
  - Adicionado `normalizarDigitosTelefone()` descartando o DDI `55` em colagens de 12–13 dígitos começando por `55` (ex.: `+55 (41) 99999-8888` → `41999998888` e `+55 (41) 3222-3344` → `4132223344`), preservando proteção caso a usuária já tenha 11 dígitos do DDD `55` e digite uma tecla extra.
  - Adicionados os casos de teste no Vitest para `+55 (41) 99999-8888`, `+55 (41) 3222-3344` e `CPF: 529.982.247-25`.
- **A3 (`AdminPage.tsx` → `NaoAptos`):** nos modos de busca `CPF` e `Telefone`, enquanto o número estiver incompleto ou inválido (`aguardandoNumeroCompleto`), a lista completa fica escondida (não dispara requisição para listar todos) e exibe somente o aviso `"Digite o CPF completo para procurar."` / `"Digite o telefone completo com DDD para procurar."`.
- **A4 (`docs/DEPLOY.md`):** ajustado o texto sobre rotação de `PII_FERNET_KEYS` para informar explicitamente que a regravação depende do comando `flask pii-rotate` (a ser entregue) e que a chave antiga não deve ser removida antes disso.
- **A5 (`FlagsContext.tsx` + `FlagsContext.test.ts`):** criado `FlagsProvider`, `useFlags()`, `<RequerFlag>` e `<RotaComFlag>` consumindo exclusivamente `obterConfigPublica()` de `app/views/src/api/public.ts` (`credentials: "omit"`, fail-closed com `CONFIG_PUBLICA_FECHADA`), com testes Vitest usando `fetch` simulado (erro de rede, HTTP 500 e resposta parcial 200).
- **A6 (`App.tsx`, `NaoEncontradaPage.tsx`):** `<FlagsProvider>` montado na raiz do `<BrowserRouter>`; rotas `/adote`, `/adote/:slug` (`vitrine`), `/termo/:token` (`termo_digital`) e `/carteira/:token` (`carteira`) protegidas por `<RotaComFlag flag="..." publica>`, exibindo `NaoEncontradaPage` (sem link para `/hoje`) quando desligadas. `/privacidade` permanece sempre aberta e todas as rotas públicas seguem fora do `<AuthProvider>` (zero chamadas a `/auth/*`).
- **A7 (`Layout.tsx`, `Icones.tsx`):** mantidas as 4 abas da barra inferior em `360px` (`Hoje`, `Animais`, `Resgate`, `Gestão`) e adicionada a gaveta **"Mais"** (folha inferior via `<Dialogo>`, botões `min-h-14`). Os itens futuros (`Estoque`, `Candidaturas`, `Mapa de resgates`, `Vitrine pública`) aparecem apenas com a respectiva flag ativa **e** o perfil adequado.

---

## 2. Arquivos Criados e Alterados (exclusivamente de propriedade do Antigravity)

### Criados
- `app/views/src/contexts/FlagsContext.tsx`
- `app/views/src/contexts/FlagsContext.test.ts`
- `app/views/src/components/LayoutPublico.tsx` *(etapa anterior do CP-01)*
- `app/views/src/pages/publico/PrivacidadePage.tsx` *(etapa anterior do CP-01)*
- `app/views/src/pages/publico/EmBrevePublicoPage.tsx` *(etapa anterior do CP-01)*
- `app/views/src/utils/mascaras.ts`
- `app/views/src/utils/mascaras.test.ts`
- `docs/handoff/CP01-antigravity-para-claude.md`

### Alterados
- `.env.example`
- `docs/DEPLOY.md`
- `app/views/src/App.tsx`
- `app/views/src/api/admin.ts`
- `app/views/src/components/Campos.tsx`
- `app/views/src/components/Icones.tsx`
- `app/views/src/components/Layout.tsx`
- `app/views/src/pages/AdminPage.tsx`
- `app/views/src/pages/NaoEncontradaPage.tsx`
- `app/views/src/pages/ficha/AbaAdocao.tsx`

> **Conformidade com a Seção 2:** nenhum arquivo de propriedade do Claude Code (`migrations/**`, `app/models/**`, `app/__init__.py`, `app/config.py`, `app/extensions.py`, `app/utils/crypto.py`, `app/utils/validation.py`, `app/controllers/*`, `vercel.json`, `app/views/src/types/contratos.ts`, `app/views/src/api/public.ts`) foi alterado.

---

## 3. Verificações Executadas

- `npm run build` (`tsc -b && vite build`): **0 erros** (`built in 8.92s`, chunk principal `76.15 kB` gzip; `PrivacidadePage` `2.11 kB` gzip; `EmBrevePublicoPage` `0.52 kB` gzip).
- `npm test` (`vitest run`): **3 arquivos, 44/44 testes verdes**:
  - `src/utils/mascaras.test.ts` — 13/13
  - `src/contexts/FlagsContext.test.ts` — 3/3
  - `src/utils/utils.test.ts` — 28/28
- Higiene de privacidade: **0** ocorrências de `console.log` ou chamadas `/auth/*` nas rotas/componentes públicos.

---

## 4. Pendências / Conferências Externas

1. **`python -m pytest`:** nenhum arquivo Python foi tocado nesta entrega; a execução de `pytest` no ambiente Windows/sandbox local depende de permissão fora do sandbox, ficando pendente para a rodada de revisão/CI do Claude Code.
2. **Prints em `360px` e desktop:** não foi possível capturar screenshots locais diretamente do sandbox (servidor local não é alcançável entre sessões no Windows sandbox). Recomenda-se validar visualmente no dev/Preview da Vercel:
   - `/privacidade` em `360px` e desktop confirmando **0** chamadas a `/auth/*` na aba Network e apenas `GET /api/public/config`;
   - `/adote`, `/termo/teste` e `/carteira/teste` exibindo `NaoEncontradaPage` enquanto flags estão `false`;
   - `AdminPage` → aba `Lista sigilosa` nos modos **CPF** e **Telefone** escondendo a lista até o número ficar completo;
   - `AbaAdocao` colando `+55 (41) 99999-8888` e `CPF: 529.982.247-25`;
   - Gaveta **"Mais"** abrindo e fechando em `360px` ao lado das 4 abas atuais.

---

## 5. Pedidos de Mudança no Contrato

Nenhum pedido de mudança no contrato do CP-01. Os tipos de `app/views/src/types/contratos.ts` e o cliente `app/views/src/api/public.ts` atenderam integralmente às telas.
