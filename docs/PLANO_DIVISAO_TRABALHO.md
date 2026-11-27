# Plano de Divisão de Trabalho — Ampliação v5.0 (Fases 0, 2, 3 e 4)

> **Base:** [SDD_AMPLIACAO_FASES_2_A_4.md](SDD_AMPLIACAO_FASES_2_A_4.md) com a revisão do §10 (v5.1).
> **Executores:** **Claude Code** (núcleo crítico: dados, segurança, LGPD, regras de negócio e revisão) e **Antigravity** (telas, CRUDs simples, integrações periféricas e documentação).
> **Regra de ouro:** quem é dono de um arquivo é o único que o altera. Se precisar de mudança no arquivo do outro, abre um pedido no handoff (seção 5) em vez de editar.

---

## 1. Critério da divisão

Fica com o **Claude Code** tudo cujo erro **não se corrige com um novo deploy**:
- vaza dado pessoal (CPF, telefone, endereço, lista sigilosa);
- corrompe ou apaga dado de produção (migração, backfill, criptografia);
- quebra uma regra de negócio garantida no banco (RN03, RN05, RN16, RN18–RN25);
- abre uma rota interna para quem não está logado.

Fica com o **Antigravity** o que é visível, testável na tela e reversível: páginas React, componentes, CRUDs sem regra crítica, scripts auxiliares e documentação.

---

## 2. Propriedade de arquivos

| Área | Dono | Observação |
| :--- | :--- | :--- |
| `migrations/versions/**` | **Claude** | Nenhuma migração é criada pelo Antigravity. |
| `app/models/**` | **Claude** | Antigravity pode pedir campo novo via handoff. |
| `app/__init__.py`, `app/config.py`, `app/extensions.py` | **Claude** | Trava `/api/*`, hooks de whitelist, cookies, PRAGMA. |
| `app/utils/crypto.py`, `app/utils/validation.py` | **Claude** | |
| `app/services/` — `rate_limit`, `turnstile`, `inventory`, `pdf_termo`, `pii`, `lgpd`, `storage` (parte privada) | **Claude** | |
| `app/controllers/public_controller.py` | **Claude** | Toda superfície anônima. |
| `app/controllers/applications_controller.py` (candidaturas) | **Claude** | RN15/RN24/RN25. |
| `app/controllers/adoptions_controller.py` (devolução, termo, carteira) | **Claude** | |
| `app/controllers/og_controller.py` | **Antigravity** | Claude revisa o escape do HTML. |
| `app/controllers/inventory_controller.py` (rotas) | **Claude** | Atualizado em 27/11/2026: escrito pelo `gapar-backend-security` (spec CP03_05). |
| `app/controllers/map_controller.py`, `scripts/geocodificar.py` | **Antigravity** | Claude revisa a restrição Admin. |
| `app/controllers/isolation_controller.py` e rotas de pós-adoção | **Claude** | Atualizado em 27/11/2026: escritas pelo `gapar-backend-security`. |
| `app/views/src/**` (todas as telas e componentes) | **Antigravity** | Exceto `src/api/public.ts` e `src/types/contratos.ts` (abaixo). |
| `app/views/src/types/contratos.ts`, `app/views/src/api/public.ts` | **Claude** | Contrato da API publicado antes da tela. |
| `tests/test_canary_anti_leak.py`, `tests/test_db_constraints.py`, `tests/test_cp0*_*` das regras RN | **Claude** | |
| Testes Vitest e testes de CRUD das rotas do Antigravity | **Antigravity** | |
| `vercel.json` | **Claude** | Rewrite por User-Agent, headers, cron. |
| `scripts/homologacao.py` | **Antigravity** | Claude acrescenta os cenários de segurança. |
| `README.md`, `docs/DEPLOY.md`, textos de `/privacidade` | **Antigravity** | Claude revisa a parte LGPD. |

---

## 2.1. Agentes especialistas do lado Claude Code (`.claude/agents/`)

| Agente | Papel | Edita? |
| :--- | :--- | :-: |
| `gapar-db-architect` | Models, migrações, RLS, gatilhos, paridade SQLite/PostgreSQL | Sim (só arquivos do Claude) |
| `gapar-backend-security` | Controllers, services, superfície pública, PII/LGPD, Turnstile, cron, `vercel.json` | Sim (só arquivos do Claude) |
| `gapar-frontend-ux` | Revisão das telas do Antigravity: máscaras, flags, 360px, acessibilidade, chunks | Não |
| `gapar-qa-gatekeeper` | 7 Gates, conferência REQ → teste, parecer aprovado/reprovado | Não |

Uso por checkpoint:
1. O `gapar-db-architect` faz a migração.
2. O `gapar-backend-security` faz as rotas e os serviços.
3. Quando o Antigravity entrega, o `gapar-frontend-ux` revisa as telas.
4. O `gapar-qa-gatekeeper` dá o parecer final antes do merge.

## 3. Fluxo de cada Checkpoint

```
1. Claude  → migração + model + service + contrato (types/contratos.ts) + testes RN   [branch feat/cpXX-nucleo]
2. Claude  → publica o handoff "contrato pronto" (seção 5)
3. Antigravity → telas, CRUDs e Vitest sobre o contrato                                [branch feat/cpXX-telas]
4. Claude  → revisão do diff do Antigravity (/code-review) + Gates 1, 2, 3, 5
5. Antigravity → corrige apontamentos, atualiza README/DEPLOY, roda homologacao.py (Gate 6)
6. Merge na ordem: nucleo → telas → main. Relatório do checkpoint ao usuário.
```

O Antigravity **não começa** a tela antes do passo 2 e **não altera** o contrato; se o contrato não atender a tela, pede a mudança.

---

## 4. Divisão por Checkpoint

### CP-01 · Fase 0 — Fundamentos (o mais crítico)

**Claude Code**
- Migração `0003a`: só **adiciona** colunas `*_cifrado` / `*_bidx` em `non_eligible_people` e `adoptions` + tabela `rate_limit_buckets` + RLS. Reversível.
- `crypto.py`: `MultiFernet` com `PII_FERNET_KEYS` **mantendo a chave antiga** (derivada de `FERNET_KEY`/`SECRET_KEY`) para os tokens Google; blind index HMAC-SHA256 com `PII_HMAC_KEY` e domínios `cpf:v1:`, `tel:v1:`, `nome:v1:`.
- Comando `flask pii-backfill` (idempotente, com `--dry-run` e contagem de conferência). As colunas em claro **não** são apagadas no CP-01.
- RN15 (`_motivo_de_bloqueio`) passa a consultar por blind index, com o mesmo resultado de hoje (match exato de CPF, telefone e nome normalizado).
- `app/__init__.py`: allowlist pública nos **dois** hooks (`require_authenticated_api` e `enforce_whitelist_status`), fail-closed para o resto.
- `public_bp` vazio com `GET /api/public/config`, `Animal.to_public_dict()`, `turnstile_service`, `rate_limit_service`.
- Garantia de zero `Set-Cookie` em `/api/public/*` (teste explícito) + headers `Vercel-CDN-Cache-Control`.
- `tests/test_canary_anti_leak.py` e teste de RLS para toda tabela nova.
- Padronização: nenhum novo `AuditLog.detalhes` com PII (nem de candidatos, nem da lista sigilosa).

**Antigravity**
- `LayoutPublico.tsx`, rotas públicas vazias (`/adote`, `/adote/:slug`, `/termo/:token`, `/carteira/:token`) e página `/privacidade` (texto em componente versionado).
- `FlagsContext.tsx` + `<RequerFlag>` / `<RotaComFlag>` (fail-closed) consumindo `/api/public/config`.
- Busca da lista sigilosa na `AdminPage` ajustada para **busca exata** de CPF/telefone (ver decisão D2).
- `.env.example` e `docs/DEPLOY.md` com as novas variáveis (`PII_FERNET_KEYS`, `PII_HMAC_KEY`, `TURNSTILE_*`).

**Fecho do CP-01 (Claude, após validação em produção):** migração `0003b` remove `cpf`/`telefone` em claro — só depois de o backfill conferir 100% em produção e de um backup do Supabase.

### CP-02 · Vitrine pública (RN17)
- **Claude:** migração `0004` (`is_publicado`, `slug_publico`, `descricao_publica`, `pausar_candidaturas`, índice); hook RN17 na transição de status; `GET /api/public/animais[/<slug>]`; rewrite condicional por User-Agent no `vercel.json`; teste RN17.
- **Antigravity:** telas `/adote` e `/adote/:slug` com CTA WhatsApp; interruptor "Publicar na vitrine" na `AbaDados`; `og_controller.py` (HTML com `markupsafe.escape`); validação do preview no WhatsApp.

### CP-03 · Estoque FEFO (RN18, RN19, RN20)
- **Claude:** migração `0005` + trigger RN19; `inventory_service` com `SELECT ... FOR UPDATE`, FEFO e bloqueio de lote vencido; baixa automática na `Vaccination`; teste de corrida concorrente.
- **Antigravity:** `inventory_controller.py` (CRUD de itens/lotes chamando o service); tela `/estoque`, modal "Ajustar saldo", `<SeletorLoteFefo />` e alertas de estoque no `HojePage`.

### CP-04 · Microchip e placa QR (RN21)
- **Claude:** migração `0006` (CHECK de 15 dígitos ANSI + `UNIQUE` simples, pois pela D1 o cão devolvido é o mesmo registro); validação no service e `409` informando qual animal já usa o número.
- **Antigravity:** campo de microchip no formulário, busca HID sem debounce em `/animais`, `utils/microchip.ts` + Vitest, `<DialogoEtiquetaBaia />` A6 com `qrcode` em chunk `lazy`.

### CP-05 · Kanban e isolamento (RN22) + homologação Fase 2
- **Claude:** migração `0007` + índice único parcial `uq_isolation_aberto_por_animal`; ocultação automática na vitrine durante isolamento.
- **Antigravity:** rotas de abrir/encerrar isolamento; visão Lista ↔ Kanban (DnD nativo + folha "Mover..." em 360px); `<SeloIsolamento />`, banner e bloco no `HojePage`; `homologacao.py` Fase 2.

### CP-06 · Pós-adoção e devolução
- **Claude:** migração `0008` (`adoptions` 1:N com `encerrada_em`/`motivo_encerramento`, índice único parcial de adoção vigente por animal, `adoption_follow_ups`); transição `adotado → em acolhimento` exclusiva da rota de devolução (Admin), com congelamento das adoções encerradas; testes RN05/RN06.
- **Antigravity:** rotas de registrar retorno; lembretes 30/90/180 dias no `HojePage` com `wa.me`; diálogo "Registrar devolução" e histórico de adoções na `AbaAdocao`.

### CP-07 · Termo digital (RN23)
- **Claude:** migração `0009` (`term_templates` append-only + trigger `gapar_proteger_evidencia_termo`); link 48h com hash; aceite com Nome+CPF+Turnstile e bloqueio após 5 falhas; `pdf_termo_service` (`reportlab`); upload em bucket **privado** com URL assinada.
- **Antigravity:** página `/termo/:token`, selo de aceite e download do PDF na ficha; tela Admin para cadastrar nova versão do termo.

### CP-08 · Pré-triagem online (RN24, RN25)
- **Claude:** migração `0010` (PII cifrada, CHECK bicondicional LGPD); `POST /api/public/candidaturas` constant-work; `applications_controller` (máscara para Voluntária, alerta RN15 só Admin, conversão em adoção); anonimização como endpoint `/api/cron/lgpd-anonymize` protegido por `CRON_SECRET` + cron diário no `vercel.json` + comando `flask lgpd-anonymize` para uso manual.
- **Antigravity:** `<FormularioPreTriagem />` em 3 passos; fila `/candidaturas`; botão "pausar candidaturas"; textos de consentimento.

### CP-09 · Carteira de vacinas + homologação Fase 3
- **Claude:** migração `0011` (token hash + cifrado + revogação); `GET /api/public/carteira/<token>` e `.ics` sem PII; teste de revogação imediata.
- **Antigravity:** página `/carteira/:token` estilo caderneta; botão de gerar/revogar/reenviar link na ficha; `homologacao.py` Fase 3.

### CP-10 · Mapa de resgates
- **Claude:** migração `0012` + `geocoding_cache` + RLS; revisão de que coordenadas exatas só saem para Admin.
- **Antigravity:** `<CapturaLocalizacao />`, `scripts/geocodificar.py` (Nominatim 1 req/s, User-Agent genérico da ONG), `map_controller.py`, página `/mapa` com `leaflet` + `supercluster` em chunk `vendor-mapa`.

### CP-11 · Encerramento
- **Claude:** revisão final de segurança, índices, N+1 e cotas; varredura de PII em logs.
- **Antigravity:** `homologacao.py` v5.0 completo, `README.md`, `docs/DEPLOY.md`, Requisitos v5.0.

---

## 5. Protocolo de handoff

Cada passagem de bastão é um arquivo em `docs/handoff/CPXX-<de>-para-<para>.md` com:
1. Branch e último commit.
2. Contrato: rotas, payloads, códigos de erro e o trecho de `types/contratos.ts`.
3. O que **não** pode ser feito (ex.: "não gravar `cpf` em `AuditLog`").
4. Pedidos ao outro lado (campo novo, ajuste de contrato).
5. Como testar localmente.

---

## 6. Regras para o Antigravity

- Não criar nem editar migrações, models, `crypto.py`, `app/__init__.py`, `public_controller.py` ou `vercel.json`.
- Não serializar model com `to_dict()` em rota pública; usar só o que o contrato expõe.
- Não gravar CPF, telefone, endereço ou nome de candidato/adotante em `AuditLog.detalhes`, `console.log` ou mensagens de erro.
- Não adicionar dependência Python; dependência NPM só `qrcode`, `leaflet` e `supercluster`, sempre em chunk `lazy`.
- Rodar `npm run build`, `npm test` e `python -m pytest` antes de pedir revisão.

---

## 7. Decisões pendentes da ONG

| # | Decisão | Prazo | Padrão se não houver resposta |
| :-: | :--- | :--- | :--- |
| **D1** | Devolução | ✅ **Decidido 26/11/2026:** o cão **continua o mesmo animal**. `adoptions` passa a 1:N (uma adoção vigente por vez) e a transição `adotado → em acolhimento` só existe pelo fluxo de devolução da Administradora (RN05 reescrita). Microchip vira `UNIQUE` simples. | — | — |
| **D2** | Busca da lista sigilosa | ✅ **Decidido 26/11/2026:** CPF e telefone só **completos**, com máscara que impede digitar qualquer outra coisa; nome segue com busca parcial. | — | — |
| **D3** | Prazo de retenção de candidaturas recusadas. | Antes do CP-08 | 180 dias (`RETENCAO_CANDIDATURA_DIAS`). |
| **D4** | Número de WhatsApp de adoção. | Antes do CP-02 | Variável `PUBLIC_WHATSAPP_ADOCAO`. |
