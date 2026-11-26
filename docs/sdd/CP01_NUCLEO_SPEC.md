# CP-01 · Núcleo da Fase 0 — Especificação (SDD)

> **Dono:** Claude Code · **Branch:** `feat/cp01-nucleo` · **Base:** SDD v5.1 (§10), `PLANO_DIVISAO_TRABALHO.md`
> **Linha de base:** 191 testes `pytest` verdes em 26/11/2026.
> **Ordem SDD:** especificação (este arquivo) → testes de aceite → implementação → verificação → handoff.

---

## 1. Objetivo

Preparar o back-end para receber visitantes **sem login** sem abrir nenhuma rota interna, e passar a guardar CPF, telefone da lista sigilosa e endereço do adotante **cifrados**, sem perder dados que já existem e sem mudar o resultado da RN15.

## 2. Fora do escopo

- Telas (Antigravity).
- Remoção das colunas em claro: fica na migração `0003b`, aplicada só depois de o backfill ser conferido em produção.
- Rotas públicas de negócio (vitrine, candidatura, termo e carteira), que vêm nos próximos CPs. Aqui só nasce a infraestrutura.

---

## 3. Requisitos

| ID | Requisito | Critério de aceite (teste) |
| :-- | :--- | :--- |
| **REQ-01** | Toda rota `/api/*` que não pertence ao blueprint `public` continua exigindo sessão (fail-closed). | `test_cp01_superficie_publica::test_toda_rota_interna_exige_login` percorre o `url_map` inteiro: todo método de toda rota interna responde `401` sem login. |
| **REQ-02** | Rotas do blueprint `public` (`/api/public/*`) respondem sem login e **ignoram a sessão**: não leem `current_user`, não devolvem `403` para cookie revogado, não emitem `Set-Cookie` nem `Vary: Cookie`. | `test_publico_sem_login`, `test_publico_com_sessao_revogada_nao_da_403`, `test_publico_sem_set_cookie_nem_vary_cookie`. |
| **REQ-03** | Caminho com `..` ou `//` nunca é tratado como público. | `test_caminho_malformado_nao_e_publico`. |
| **REQ-04** | `GET /api/public/config` devolve `{flags, turnstile_site_key, whatsapp_adocao}` com cache de CDN (`Vercel-CDN-Cache-Control`). Flags fail-closed: `false` sem variável. | `test_config_publica_contrato`, `test_flags_padrao_desligadas`, `test_flag_ligada_por_ambiente`. |
| **REQ-05** | `@require_feature("x")` devolve `404` quando a flag está desligada. | `test_require_feature`. |
| **REQ-06** | `Animal.to_public_dict()` expõe **somente** `PUBLIC_ANIMAL_STRICT_KEYS`. | `test_canary_anti_leak::test_to_public_dict_so_allowlist` (honeytokens em toda coluna de texto fora da allowlist). |
| **REQ-07** | Nenhuma resposta pública contém dado de qualquer tabela fora da allowlist. | `test_canary_anti_leak::test_rotas_publicas_sem_honeytoken`: banco inteiro preenchido com `CANARY_SECRET_*`. |
| **REQ-08** | Toda tabela do `db.metadata` tem RLS ligado em alguma migração. | `test_cp01_migracoes::test_toda_tabela_tem_rls`. |
| **REQ-09** | A migração `0003a` sobe e desce no SQLite sem erro e só **adiciona** estruturas. | `test_cp01_migracoes::test_upgrade_downgrade_0003a`. |
| **REQ-10** | PII com chave própria: `MultiFernet(PII_FERNET_KEYS)`, aceita várias chaves (rotação), a primeira cifra. Os tokens Google continuam na chave antiga (`FERNET_KEY`/`SECRET_KEY`). | `test_cp01_pii::test_rotacao_multifernet`, `test_tokens_google_continuam_legiveis`. |
| **REQ-11** | Blind index `HMAC-SHA256(PII_HMAC_KEY, "<dominio>:v1:<normalizado>")`, determinístico, separado por domínio (`cpf`, `tel`, `nome`). | `test_blind_index_deterministico_e_por_dominio`. |
| **REQ-12** | Em produção, faltar `PII_FERNET_KEYS` (ou chave inválida, ou a chave pública dos testes) ou `PII_HMAC_KEY` (< 32 caracteres ou valor de exemplo) impede a subida. Em dev/testes há chave derivada, com aviso. A produção registra no log a impressão digital (não secreta) das chaves. | `test_producao.py::test_producao_incompleta_falha_cedo` (casos PII). |
| **REQ-13** | `NonEligiblePerson.cpf`/`telefone` e `Adoption.adotante_cpf`/`adotante_endereco` são gravados **só** cifrados (coluna em claro fica `NULL` em gravação nova). A leitura é transparente: usa a cifra e, sem ela, o valor legado. | `test_gravacao_nova_nao_fica_em_claro`, `test_leitura_de_registro_legado`. |
| **REQ-14** | RN15 consulta pela blind index, com as mesmas mensagens e prioridade de hoje (CPF → telefone → nome normalizado). Registros legados ainda sem índice continuam sendo conferidos. | Testes RN15 existentes + `test_rn15_registro_legado_sem_indice`. |
| **REQ-15** | **D2:** CPF aceito só com 11 dígitos e dígito verificador válido; telefone só com 10 ou 11 dígitos, DDD 11–99, e celular (11 dígitos) começando por 9. Vale para a lista sigilosa e a adoção. Saída de CPF formatada `000.000.000-00`. | `test_cp01_pii::test_validacao_cpf_telefone` (parametrizado). |
| **REQ-16** | **D2:** busca da lista sigilosa por `POST /api/admin/nao-aptos/busca` com UM filtro no corpo: `q` (nome, parcial), `cpf` ou `telefone` (exatos, via blind index). Dado pessoal nunca vai na URL: `GET` com `?q/?cpf/?telefone` → `400`. Número incompleto/inválido → `400`. | `test_busca_exata_lista_sigilosa`, `test_busca_com_dado_pessoal_na_url_e_recusada`. |
| **REQ-17** | `flask pii-backfill [--dry-run]` só roda com `PII_FERNET_KEYS` e `PII_HMAC_KEY` explícitas (nunca a chave derivada de dev; fora dos testes, também nunca valor de exemplo), mostra a impressão digital das chaves, cifra os legados **sem apagar** o valor em claro, confere a decifração **e o índice cego**, é idempotente e audita só contagens + impressão. Divergência → aborta sem gravar. | `test_pii_backfill*`. |
| **REQ-18** | Nenhum `AuditLog.detalhes` novo contém nome, CPF, telefone ou endereço de pessoa (adotante ou lista sigilosa). | `test_auditoria_sem_pii`. |
| **REQ-19** | `rate_limit_service.consumir(acao, identificador, limite, janela)` é atômico (upsert), não guarda IP em claro (só HMAC) e reinicia a contagem na janela seguinte. | `test_cp01_servicos::test_rate_limit_*`. |
| **REQ-20** | `turnstile_service.verificar(token, acao)` é fail-closed: erro de rede, `success=false`, ação diferente ou token ausente → `False`; sem segredo em produção → `503`; em dev/testes sem segredo → passa, com aviso. | `test_cp01_servicos::test_turnstile_*` (requests mockado). |

---

## 4. Design

### 4.1. Superfície pública (`app/__init__.py`)
- `is_public_request()` em `app/utils/publico.py`: `request.blueprint == "public"` **e** o caminho começa com `/api/public/` **e** não contém `..` nem `//`.
- Os dois hooks (`require_authenticated_api`, `enforce_whitelist_status`) retornam cedo para requisições públicas, **antes** de tocar em `current_user`.
- `SessaoPublicaInterface(SecureCookieSessionInterface)`: `save_session` não faz nada em requisição pública. Assim não há `Set-Cookie` nem `Vary: Cookie`, que impediriam o cache da CDN. Isso **substitui** a ideia do SDD v5.0 de "limpar o cookie revogado em rotas públicas", pois limpar exigiria um `Set-Cookie`. O cookie revogado continua sem valor nas rotas internas, que seguem devolvendo `403`.
- `cache_publico(segundos, swr)`: decorator que põe `Cache-Control: public, max-age=60` e `Vercel-CDN-Cache-Control: max-age=<s>, stale-while-revalidate=<swr>` só em respostas `200`.

### 4.2. Criptografia (`app/utils/crypto.py`)
- `encrypt_token`/`decrypt_token`: **inalterados** (tokens Google, R2).
- `cifrar_pii(texto)` e `decifrar_pii(cifra)`: `MultiFernet` com as chaves de `PII_FERNET_KEYS` (separadas por vírgula). Uma falha de decifração registra erro no log (sem o conteúdo) e devolve `None`.
- `indice_cego(dominio, valor)`: `hmac.new(PII_HMAC_KEY, f"{dominio}:v1:{valor}", sha256).hexdigest()`.
- Normalizadores em `app/utils/pii.py`:
  - `normalizar_cpf` e `normalizar_telefone`: só dígitos.
  - `normalizar_nome`: minúsculas e espaços colapsados, exatamente como a RN15 faz hoje.
- Dev/testes sem chave: derivação estável de `SECRET_KEY` com prefixo de domínio e aviso no log.

### 4.3. Modelos
- `NonEligiblePerson`:
  - coluna em claro mapeada como `cpf_legado` (nome físico `cpf`) e `telefone_legado` (nome físico `telefone`);
  - colunas novas `cpf_cifrado`, `cpf_bidx`, `telefone_cifrado`, `telefone_bidx`, `nome_bidx`;
  - propriedades `cpf` e `telefone` (leitura transparente, gravação só cifrada);
  - `@validates("nome")` mantém `nome_bidx`.
- `Adoption`:
  - colunas em claro `adotante_cpf_legado` e `adotante_endereco_legado`;
  - colunas novas `adotante_cpf_cifrado`, `adotante_cpf_bidx`, `adotante_endereco_cifrado`;
  - propriedades `adotante_cpf` e `adotante_endereco`. O `to_dict` não muda de formato.
- `RateLimitBucket` (`rate_limit_buckets`): `bucket_key VARCHAR(120) PK`, `window_start DATETIME`, `hit_count INTEGER`.
- `Animal.PUBLIC_ANIMAL_STRICT_KEYS = (nome, sexo, porte, idade_estimada, raca, pelagem, foto_url, is_castrado, is_idoso)` e `to_public_dict()`. `slug_publico` entra no CP-02.

### 4.4. Migração `0003a` (aditiva e reversível)
- `add_column` das colunas acima, com índices `ix_*_bidx`.
- `create_table rate_limit_buckets`.
- PostgreSQL: `ENABLE ROW LEVEL SECURITY` em `rate_limit_buckets`. O RLS nunca é desligado no `downgrade`.
- Constante `TABELAS_RLS` no módulo, para o teste REQ-08.

### 4.5. RN15 (`app/services/lista_sigilosa.py`)
- `motivo_de_bloqueio(nome, cpf, telefone)`:
  1. faz um `SELECT` por `cpf_bidx`, `telefone_bidx` ou `nome_bidx`;
  2. em seguida, faz a varredura antiga **só** nos registros com `nome_bidx IS NULL` (legados ainda não processados pelo backfill).
- A prioridade das mensagens é preservada.

### 4.6. Validação D2 (`app/utils/validation.py`)
- `parse_cpf(valor, campo, obrigatorio=False)` e `parse_telefone(...)` devolvem só dígitos ou levantam `ApiError 400`.
- `formatar_cpf(digitos)` para a saída.

### 4.7. Serviços
- **`rate_limit_service.consumir`:** `INSERT … ON CONFLICT (bucket_key) DO UPDATE SET hit_count = CASE WHEN window_start = excluded.window_start THEN hit_count + 1 ELSE 1 END, window_start = excluded.window_start RETURNING hit_count`. Funciona no PostgreSQL e no SQLite ≥ 3.35. Deve ser chamado no início da requisição, porque faz commit. A chave é `"<acao>:" + indice_cego("rl", identificador)`. A limpeza de buckets antigos entra no cron do CP-08.
- **`turnstile_service.verificar`:** `POST https://challenges.cloudflare.com/turnstile/v0/siteverify` com timeout de 5 s. O log registra só o tipo do erro.

### 4.8. Contrato para o front-end
- `app/views/src/types/contratos.ts`: `ConfigPublica`, `FlagPublica`.
- `app/views/src/api/public.ts`: `obterConfigPublica()` com `credentials: "omit"`, para nunca enviar o cookie e manter o cache da CDN.

### 4.9. `vercel.json`
- Cabeçalhos de segurança globais:
  - `X-Content-Type-Options: nosniff`;
  - `Referrer-Policy: strict-origin-when-cross-origin`;
  - `X-Frame-Options: DENY`;
  - `Permissions-Policy: camera=(), microphone=(), geolocation=(self)`.

---

## 5. Variáveis de ambiente novas

| Variável | Obrigatória em produção | Formato |
| :--- | :-: | :--- |
| `PII_FERNET_KEYS` | Sim | Uma ou mais chaves Fernet separadas por vírgula. A primeira cifra; as demais só decifram (rotação). **Perder todas torna os CPFs ilegíveis.** |
| `PII_HMAC_KEY` | Sim | Texto aleatório com ≥ 32 caracteres. **Nunca rotacionar** sem reindexar (`pii-backfill --reindex`, CP futuro). |
| `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET_KEY` | A partir do CP-07 | Chaves do Cloudflare Turnstile. |
| `PUBLIC_WHATSAPP_ADOCAO` | Não | Número com DDI, só dígitos. |
| `FEATURE_<NOME>` | Não | `1`/`true` liga. Nomes: `VITRINE`, `ESTOQUE`, `MICROCHIP`, `ISOLAMENTO`, `POS_ADOCAO`, `TERMO_DIGITAL`, `CANDIDATURAS`, `CARTEIRA`, `MAPA`. |

## 6. Resultado da verificação (26/11/2026)

| Gate | Resultado |
| :--- | :--- |
| 1 · Migração | `0003a` sobe → desce → sobe em SQLite (subprocesso `flask db`); o downgrade **se recusa** a rodar quando há dado só cifrado; o modelo e a migração têm as mesmas colunas; toda tabela tem RLS. |
| 2 · `pytest` | **Ver §6.1** (191 originais + novos do CP-01). Testes antigos ajustados só onde usavam CPF/telefone inválidos (D2) ou a busca parcial de CPF (D2). |
| 3 · Canário | Verde. **Teste de mutação:** quebrar a checagem do blueprint, a interface de sessão ou a allowlist do animal deixa os testes vermelhos. |
| 4 · Front | `tsc --noEmit` ok, `vitest` ok, `npm run build` ok. |
| R8 | `PRAGMA foreign_keys = ON` no SQLite ligado sem quebrar a suíte; teste `test_sqlite_confere_chave_estrangeira`. |

### 6.1. Correções do parecer do gatekeeper (REPROVADO → reenviado)

| Achado | Correção |
| :--- | :--- |
| 🔴 1 · backfill com chave derivada de dev desligaria a RN15 | O comando exige chaves explícitas, recusa valor de exemplo fora dos testes, mostra a impressão digital (comparável ao log `Chaves PII em uso` da produção) e confere também o índice cego. |
| 2 · `PRAGMA foreign_keys` nas migrações do SQLite | `migrations/env.py` desliga o PRAGMA durante a migração. Teste com migração temporária que recria `animals`, que reprova sem a correção. |
| 3 · chave Fernet de teste aceita em produção | `CHAVE_FERNET_DE_TESTE` é recusada por `problemas_chaves_pii`. |
| 4 · canário parcial | Toda rota `public.*` precisa de cobertura (automática ou em `CASOS_PUBLICOS_EXPLICITOS`); saúde e avisos recebem honeytokens; CPF e telefone são procurados formatados e sem formatação. |
| 5 · mutantes sobreviventes | Testes novos: prioridade CPF→telefone, edição de legado limpa o valor em claro, backfill aborta em divergência, allowlist congelada, `no-store` em erro, `..`/`//` com rota pública simulada. |
| 6 · CPF na URL | Busca passou para `POST /api/admin/nao-aptos/busca`; `GET` com filtro → 400. |
| 7 · `vercel.json` "do Antigravity" | Falso positivo: a alteração foi feita pelo Claude Code e entrou no mesmo commit. |

**Desvios em relação ao SDD v5.0, já refletidos acima:**
- A sessão revogada não é "limpa" em rota pública: ela é ignorada. Limpar exigiria `Set-Cookie`, o que quebraria o cache.
- O `adotante_telefone` da adoção continua em claro (a Voluntária precisa dele para o contato), mas passa a ser validado e gravado só com dígitos.
- Os detalhes de auditoria de adoção e da lista sigilosa passam a citar só números de registro, sem nomes (R6).

## 7. Ordem de implantação em produção

1. Configurar `PII_FERNET_KEYS` e `PII_HMAC_KEY` na Vercel **e** guardar uma cópia fora dela (cofre de senhas da ONG).
2. Fazer o deploy, que aplica a migração `0003a`.
3. Rodar `flask pii-backfill --dry-run` e depois `flask pii-backfill`.
4. Conferir as contagens, fazer backup do Supabase e só então aplicar a `0003b` (fecho do CP-01).
