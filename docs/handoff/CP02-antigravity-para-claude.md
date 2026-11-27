# Handoff — Antigravity → Claude Code (Rodada 3 · Fechamento CP-01 + Pré-CP-02 + C3 + B5)

- **Branch de trabalho (compartilhada):** `feat/cp01-nucleo` (sem commits feitos pelo Antigravity, conforme combinado na Rodada 3)
- **Referências seguidas:** `docs/handoff/PROMPT_ANTIGRAVITY_RODADA3.md`, `docs/handoff/CP01-claude-para-antigravity.md` (§4), `docs/sdd/CP01_NUCLEO_SPEC.md` (§7), `docs/sdd/CP02_VITRINE_SPEC.md` (REQ-21 a REQ-31) e `app/views/src/types/contratos.ts`.

---

## 1. Resumo do que foi entregue

### Tarefa 1 — Condição de merge do CP-01
1. **Busca sigilosa via `POST` (`app/views/src/api/admin.ts` + `app/views/src/api/admin.test.ts`):**
   - `listarNaoAptos` agora envia `POST /api/admin/nao-aptos/busca` com corpo JSON `BuscaListaSigilosa` (`{ cpf } | { telefone } | { q }`) sempre que houver filtro preenchido — zero dado pessoal em URL/query string.
   - Sem filtro, mantém `GET /api/admin/nao-aptos` sem parâmetros de consulta.
   - Coberto por 4 novos testes unitários em `app/views/src/api/admin.test.ts`.
2. **Passo da impressão digital das chaves PII (`docs/DEPLOY.md`):**
   - Adicionada subseção dedicada antes do backfill orientando conferir `Chaves PII em uso: fernet=… hmac=…` nos logs da produção (Vercel) contra `Chaves PII: fernet=… hmac=…` de `flask --app wsgi pii-backfill --dry-run`, **parar imediatamente se diferirem**, só então rodar `flask --app wsgi pii-backfill`, validar contagens, fazer backup no Supabase e aplicar a migração `0003b`.

### Tarefa 2 — Todos os achados acionáveis da revisão de front-end (§4, itens 1 a 8)
1. **Lista sigilosa (`app/views/src/pages/AdminPage.tsx`):** enquanto a busca por CPF/telefone está pendente ou em andamento, exibe `<Esqueleto className="h-40" />` em vez de piscar `"Ninguém encontrado"` (usando chave de consulta no `useCarregar` para eliminar até o 1 frame de transição antes do efeito).
2. **Telefone e DDD `55` (`app/views/src/utils/mascaras.ts`, `app/views/src/components/Campos.tsx`, `app/views/src/utils/mascaras.test.ts`):** criada `normalizarEntradaTelefone(bruto, anterior, colado)`. O DDI `55` só é descartado em colagem (`onPaste`) ou quando 2+ dígitos entram de uma só vez; digitar um dígito no meio de `(55) 99999-8888` preserva o número intacto e não apaga o DDD `55`. Coberto em Vitest.
3. **Timeout das flags sem `abort()` (`app/views/src/contexts/FlagsContext.tsx`):** `carregarConfigPublicaComTimeout` refatorado para `Promise.race` com temporizador de `8000 ms` resolvendo para `CONFIG_PUBLICA_FECHADA` sem chamar `abort()` (evitando `AbortError` engolido). O `abort()` permanece apenas na limpeza de desmontagem do `useEffect`.
4. **Testes SSR dos componentes de flags (`app/views/src/contexts/FlagsContext.test.ts`):** adicionados testes com `renderToString` (`react-dom/server`) + `StaticRouter` (`react-router-dom/server`) validando `<FlagsProvider>`, `<RequerFlag>` e `<RotaComFlag>` no estado inicial *fail-closed*, além da asserção de que o timeout não chama `abort()`.
5. **Um `<Suspense>` por layout (`app/views/src/App.tsx`, `app/views/src/components/Layout.tsx`, `app/views/src/components/LayoutPublico.tsx`):** removido o `<Suspense>` global; cada layout envolve seu `<Outlet />` para não desmontar/piscar o cabeçalho em telas *lazy*.
6. **Logo do `LayoutPublico` (`app/views/src/components/LayoutPublico.tsx`):** aponta para `/adote` apenas quando `ativa("vitrine")` for verdadeiro; caso contrário aponta para `/privacidade`.
7. **404 público sem montar `AuthProvider` (`app/views/src/App.tsx`):** rotas `/privacidade/*`, `/adote/*`, `/termo`, `/termo/*`, `/carteira` e `/carteira/*` caem em `<NaoEncontradaPage publica />` dentro de `LayoutPublico`, sem montar `AreaInterna`/`AuthProvider` nem chamar `/auth/status`.
8. **Gaveta `"Mais"` acessível (`app/views/src/components/Layout.tsx`):** itens internos da gaveta trocados para `<NavLink>` (garantindo `aria-current="page"` e destaque visual ativo).

### Tarefa 3 — C3 · Placa da baia com QR code (`DialogoEtiquetaBaia`)
- Instalados exclusivamente `qrcode` (`^1.5.4`) e `@types/qrcode` (`^1.5.6`) em `package.json` / `package-lock.json`.
- Criado `app/views/src/components/DialogoEtiquetaBaia.tsx` com placa A6 retrato (`105 mm × 148 mm`), exibindo identificação da ONG, baia, foto, nome, resumo físico, cuidados especiais, suporte opcional a `numero_microchip` (para o CP-04) e QR code vetorial (data URL SVG, sem `dangerouslySetInnerHTML`) apontando para `/animais/:id`.
- `qrcode` é carregado via `import("qrcode")` dinâmico somente quando o diálogo é aberto, e o próprio diálogo é *lazy-loaded* a partir de `app/views/src/pages/AnimalFichaPage.tsx` atrás de `<RequerFlag flag="microchip">`.
- Regras `@media print` A6 retrato adicionadas em `app/views/src/index.css` com escopo `body:has(.area-impressao-etiqueta)` (não afeta a impressão de outras páginas).
- Criado `app/views/src/components/DialogoEtiquetaBaia.test.ts` (2 testes passando).

### Tarefa 4 — B5 · Prévia Open Graph (`app/controllers/og_controller.py`)
- Criado `app/controllers/og_controller.py` conforme REQ-29:
  - `og_bp = Blueprint("og", __name__)`
  - Rota `GET /adote/<slug>`, função `preview_animal` (endpoint `og.preview_animal`), decorada com `@cache_publico(300, 3600)`.
  - Verifica `flag_ativa("vitrine")`, consulta `Animal.buscar_publicado(slug)` e serializa exclusivamente com `animal.to_public_dict()` (nunca `to_dict()`).
  - Todos os valores interpolados no HTML passam por `markupsafe.escape`.
  - `og:image` só é emitido se `foto_url` começar com `https://`.
  - Fallback HTML mínimo institucional quando a flag estiver desligada ou o animal não for encontrado, sem revelar dados de animais.
- **Não registrado ainda em `app/controllers/__init__.py`**, pois `docs/handoff/CP02-claude-para-antigravity.md` ainda não foi publicado (aguardando seu sinal para adicionar a linha única de registro).

### Entregas já presentes na working tree da etapa anterior (Trilhas B1–B4 e C1–C2)
- `app/views/src/api/vitrine.ts` + `app/views/src/api/vitrine.test.ts`
- `app/views/src/utils/whatsapp.ts`
- `app/views/src/components/FotoAnimal.tsx` (atributos `largura`/`altura`)
- `app/views/src/pages/publico/VitrinePage.tsx` + `app/views/src/pages/publico/VitrineAnimalPage.tsx`
- `app/views/src/types/index.ts`, `app/views/src/api/animais.ts`, `app/views/src/pages/ficha/AbaDados.tsx` (controle de vitrine na ficha)
- `app/views/src/utils/microchip.ts` + `app/views/src/utils/microchip.test.ts`
- `app/views/src/hooks/useLeitorMicrochip.ts` + `app/views/src/hooks/useLeitorMicrochip.test.ts`

---

## 2. Arquivos alterados / criados pelo Antigravity

### Modificados
- `app/views/src/api/admin.ts`
- `app/views/src/api/animais.ts`
- `app/views/src/App.tsx`
- `app/views/src/components/Campos.tsx`
- `app/views/src/components/FotoAnimal.tsx`
- `app/views/src/components/Icones.tsx`
- `app/views/src/components/Layout.tsx`
- `app/views/src/components/LayoutPublico.tsx`
- `app/views/src/contexts/FlagsContext.tsx`
- `app/views/src/contexts/FlagsContext.test.ts`
- `app/views/src/index.css`
- `app/views/src/pages/AdminPage.tsx`
- `app/views/src/pages/AnimalFichaPage.tsx`
- `app/views/src/pages/ficha/AbaDados.tsx`
- `app/views/src/types/index.ts`
- `app/views/src/utils/mascaras.ts`
- `app/views/src/utils/mascaras.test.ts`
- `docs/DEPLOY.md`
- `package.json`
- `package-lock.json`

### Criados
- `app/controllers/og_controller.py` *(autorizado na Tarefa 4 — ainda não registrado em `app/controllers/__init__.py`)*
- `app/views/src/api/admin.test.ts`
- `app/views/src/api/vitrine.ts`
- `app/views/src/api/vitrine.test.ts`
- `app/views/src/components/DialogoEtiquetaBaia.tsx`
- `app/views/src/components/DialogoEtiquetaBaia.test.ts`
- `app/views/src/hooks/useLeitorMicrochip.ts`
- `app/views/src/hooks/useLeitorMicrochip.test.ts`
- `app/views/src/pages/publico/VitrineAnimalPage.tsx`
- `app/views/src/pages/publico/VitrinePage.tsx`
- `app/views/src/utils/microchip.ts`
- `app/views/src/utils/microchip.test.ts`
- `app/views/src/utils/whatsapp.ts`
- `docs/handoff/CP02-antigravity-para-claude.md`

---

## 3. Evidências de validação

### `npm run build` (`tsc -b && vite build`) — PASSOU (0 erros)
Chunks principais e prova de separação *lazy* do `qrcode`:
- `dist/assets/index-C1sr6gIm.js` — `241.46 kB` (`gzip: 76.89 kB`)
- `dist/assets/AnimalFichaPage-BvtHjk-g.js` — `34.71 kB` (`gzip: 10.04 kB`)
- **`dist/assets/browser-G7TlpHRA.js` (`qrcode`) — `25.78 kB` (`gzip: 10.13 kB`)** *(chunk lazy separado)*
- `dist/assets/AdminPage-BjWx775u.js` — `16.76 kB` (`gzip: 5.81 kB`)
- `dist/assets/SeletorDeFoto-ht2463qn.js` — `7.72 kB` (`gzip: 2.78 kB`)
- `dist/assets/VitrineAnimalPage-Dzj5ghGW.js` — `6.75 kB` (`gzip: 2.39 kB`)
- `dist/assets/PrivacidadePage-BPFYOtBf.js` — `6.21 kB` (`gzip: 2.11 kB`)
- `dist/assets/VitrinePage-DN8Yxdf9.js` — `4.33 kB` (`gzip: 1.85 kB`)
- **`dist/assets/DialogoEtiquetaBaia-1B5g1Abr.js` — `4.29 kB` (`gzip: 1.91 kB`)** *(chunk lazy separado)*
- `dist/assets/AnimalNovoPage-DztbcdhC.js` — `2.16 kB` (`gzip: 1.19 kB`)
- `dist/assets/Abas-LtKff7GR.js` — `1.69 kB` (`gzip: 0.94 kB`)
- `dist/assets/EmBrevePublicoPage-9yJ2pMdH.js` — `0.88 kB` (`gzip: 0.51 kB`)
- `dist/assets/vitrine-Db3zsufc.js` — `0.87 kB` (`gzip: 0.50 kB`)
- `dist/assets/index-ZXnqeTlI.css` — `42.75 kB` (`gzip: 8.82 kB`)

### `npm test` (`vitest run`) — PASSOU (8 arquivos, 74/74 testes, 0 warnings)
- `src/utils/utils.test.ts` — 28 passed
- `src/utils/mascaras.test.ts` — 13 passed
- `src/hooks/useLeitorMicrochip.test.ts` — 9 passed
- `src/utils/microchip.test.ts` — 7 passed
- `src/api/vitrine.test.ts` — 6 passed
- `src/contexts/FlagsContext.test.ts` — 5 passed
- `src/api/admin.test.ts` — 4 passed
- `src/components/DialogoEtiquetaBaia.test.ts` — 2 passed

### `python -m pytest -q` — PASSOU (339/339 testes)
- `339 passed in 95.91s`

### Smoke test em memória de `app/controllers/og_controller.py` — PASSOU (`OG_SMOKE_OK`)
Validados: endpoint exato `og.preview_animal` em `/adote/<slug>`, cache CDN `max-age=300, stale-while-revalidate=3600`, flag desligada -> fallback institucional, escape XSS com `markupsafe.escape`, uso exclusivo de `to_public_dict()` (garantindo que `to_dict()` nunca é chamado), omissão de `og:image` para URL não-HTTPS (`http://`) e fallback institucional para `None`.

---

## 4. Pendências (aguardando próximo marco)

1. **Registro do `og_bp` em `app/controllers/__init__.py` (1 linha):** será feito assim que `docs/handoff/CP02-claude-para-antigravity.md` for publicado e confirmar `Animal.buscar_publicado`.
2. **Tarefa 5 (Integração real da vitrine com a API CP-02):** testar `/adote`, `/adote/:slug` e `AbaDados` (`PATCH /api/animais/:id/vitrine`, incluindo resposta `422`) contra o back-end real assim que `docs/handoff/CP02-claude-para-antigravity.md` estiver disponível.
3. **Item 9 da revisão (prints em 360 px e desktop):** pendente até o Preview da Vercel estar publicado.

---

## 5. Confirmação de propriedade de arquivos e higiene Git

- **Nenhum arquivo proibido foi editado pelo Antigravity:** não toquei em `app/models/**`, `migrations/**`, `app/controllers/__init__.py`, `app/controllers/animals_controller.py`, `app/controllers/public_controller.py`, `app/services/**`, `app/utils/**`, `app/__init__.py`, `app/config.py`, `app/extensions.py`, `vercel.json`, `tests/**`, `app/views/src/types/contratos.ts`, `app/views/src/api/public.ts` nem `docs/sdd/**`.
- **Única criação em `app/controllers/`:** `app/controllers/og_controller.py` (Tarefa 4).
- **Zero operações de escrita no Git:** não executei `git commit`, `git add`, `git checkout`, `git stash`, `git reset` nem formatadores globais.
