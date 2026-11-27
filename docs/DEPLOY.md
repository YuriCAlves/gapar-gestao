# Deploy na Vercel e homologação (Checkpoint 7)

Um único projeto Vercel serve as duas camadas:

| Caminho | Quem atende |
|---|---|
| `/api/*`, `/auth/*` | Função Python `api/index.py` (Flask, controllers) |
| `/assets/*` e arquivos de `app/views/public` | CDN (build do Vite em `dist/`) |
| qualquer outra rota | `index.html` da SPA (React Router decide a tela) |

## 1. Variáveis de ambiente (Production)

| Variável | Obrigatória | Valor |
|---|---|---|
| `FLASK_ENV` | sim | `production` |
| `SECRET_KEY` | sim | 32+ caracteres aleatórios: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | sim | URI do **pooler de transações** do Supabase (porta `6543`, `?sslmode=require`) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | sim | Credenciais OAuth do Google Cloud |
| `INITIAL_ADMIN_EMAIL` | sim | E-mail Google da Administradora inicial (RN13) |
| `PUBLIC_BASE_URL` | recomendada | URL pública, ex.: `https://gapar.vercel.app` (vazio = host da requisição) |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | sim, na prática | Sem elas as fotos vão para `/tmp` e se perdem |
| `SUPABASE_STORAGE_BUCKET` | não | padrão `animais` |
| `APP_TIMEZONE` | não | padrão `America/Sao_Paulo` |

### Variáveis da Ampliação v5.1 (LGPD, Anti-Bot, Cron e Feature Flags)

| Variável | Obrigatória | Valor / Como gerar |
|---|---|---|
| `PII_FERNET_KEYS` | sim (a partir do CP-01) | Uma ou mais chaves Fernet separadas por vírgula (`MultiFernet`): `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `PII_HMAC_KEY` | sim (a partir do CP-01) | 32+ caracteres aleatórios para busca exata (blind index): `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET_KEY` | sim quando houver formulário público | Chaves do widget gratuito **Cloudflare Turnstile** (painel Cloudflare) |
| `PUBLIC_WHATSAPP_ADOCAO` | sim quando `FEATURE_VITRINE=true` | Número oficial de adoção só com dígitos + DDI `55`, ex.: `5541999998888` |
| `CRON_SECRET` | sim (a partir do CP-08) | Segredo aleatório para o Vercel Cron chamar `/api/cron/lgpd-anonymize`: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `RETENCAO_CANDIDATURA_DIAS` | não | padrão `180` (dias antes da anonimização RN25) |
| `FEATURE_VITRINE`, `FEATURE_ESTOQUE`, `FEATURE_MICROCHIP`, `FEATURE_ISOLAMENTO`, `FEATURE_POS_ADOCAO`, `FEATURE_TERMO_DIGITAL`, `FEATURE_CANDIDATURAS`, `FEATURE_CARTEIRA`, `FEATURE_MAPA` | não | padrão `false` — ligue (`true`) **somente após** homologar o módulo correspondente |

Sem as obrigatórias, a função **não sobe** e o log mostra exatamente o que falta
(`Configuração de produção incompleta: ...`). O login de desenvolvimento nunca existe em produção.

> Trocar o `SECRET_KEY` invalida as sessões abertas e os tokens do Google já guardados
> (as pessoas só precisam entrar de novo).
>
> **Atenção crítica sobre `PII_FERNET_KEYS`:** guarde uma cópia segura dessa chave fora da Vercel (cofre de senhas da ONG). **Perder a `PII_FERNET_KEYS` torna os CPFs (e demais dados cifrados) ilegíveis para sempre.** Para rotacionar com segurança, adicione a nova chave **antes** da antiga separada por vírgula (`nova,antiga`); a regravação é feita pelo comando de rotação (`flask pii-rotate`, a ser entregue) — não remova a chave antiga antes disso.

## 2. Google Cloud Console

Em *APIs e serviços → Credenciais → ID do cliente OAuth*, adicione em
**URIs de redirecionamento autorizados**: `https://<domínio-de-produção>/auth/callback`.

## 3. Banco

As migrações rodam fora da Vercel, a partir da máquina local apontando para o Supabase:

```bash
flask --app wsgi db upgrade
```

### Backfill de criptografia PII (CP-01 — conferência obrigatória da impressão digital)

Antes de cifrar os dados existentes em produção e remover as colunas em claro (`0003b`), siga esta ordem exata:

1. **Verifique a impressão digital das chaves em produção (Vercel):**
   - Suba o deploy com `PII_FERNET_KEYS` e `PII_HMAC_KEY` configuradas na Vercel e abra os logs da função Python.
   - Anote a linha gravada na inicialização:
     ```text
     Chaves PII em uso: fernet=<impressão-fernet> hmac=<impressão-hmac>
     ```
2. **Rode o dry-run na máquina local e compare as impressões digitais:**
   ```bash
   flask --app wsgi pii-backfill --dry-run
   ```
   - O comando imprime `Chaves PII: fernet=<...> hmac=<...>`.
   - **SE OS VALORES DE `fernet=` OU `hmac=` FOREM DIFERENTES DOS LOGS DA VERCEL, PARE IMEDIATAMENTE.** Não rode o backfill nem a migração `0003b` — cifrar com outra chave tornaria os dados ilegíveis na produção. Confira as variáveis locais e repita o `--dry-run` até as duas linhas coincidirem exatamente.
3. **Execute o backfill real e valide as contagens:**
   ```bash
   flask --app wsgi pii-backfill
   ```
   - Confirme na saída que todos os registros foram cifrados e que não restou nenhum registro pendente.
4. **Faça um backup no Supabase** antes de aplicar a migração `0003b` (que remove as colunas antigas em texto claro):
   ```bash
   flask --app wsgi db upgrade
   ```

## 4. Homologação

```bash
pip install -r requirements-dev.txt
python scripts/homologacao.py https://<domínio-de-produção>
```

O script não faz login nem altera dados. Confere SPA e links diretos, bundle, API, travas de
acesso (401), ausência do dev-login, redirecionamento ao Google com retorno em HTTPS e cookie
`Secure`/`HttpOnly`.

### Roteiro manual (com contas reais)

1. Administradora entra com Google; e-mail fora da Whitelist é barrado (RN12).
2. Cadastrar animal com foto tirada no celular; a foto abre e tem menos de 300 KB (RNF02).
3. Catálogo: busca e filtros.
4. Ficha: vacinas, prontuário e prescrição; no painel Hoje, baixar uma dose em um toque (RF16, RF23).
5. Adoção com pessoa da lista sigilosa é bloqueada (RN15); adoção válida congela a ficha (RN05).
6. Voluntária não vê a área de gestão nem CPF/endereço do adotante.
7. Desativar a voluntária na Whitelist: a próxima ação dela mostra "acesso revogado" (RN14).
8. Histórico de ações registra os passos acima (RF24).
