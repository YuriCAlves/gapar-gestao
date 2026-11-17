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

Sem as obrigatórias, a função **não sobe** e o log mostra exatamente o que falta
(`Configuração de produção incompleta: ...`). O login de desenvolvimento nunca existe em produção.

> Trocar o `SECRET_KEY` invalida as sessões abertas e os tokens do Google já guardados
> (as pessoas só precisam entrar de novo).

## 2. Google Cloud Console

Em *APIs e serviços → Credenciais → ID do cliente OAuth*, adicione em
**URIs de redirecionamento autorizados**: `https://<domínio-de-produção>/auth/callback`.

## 3. Banco

As migrações rodam fora da Vercel, a partir da máquina local apontando para o Supabase:

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
