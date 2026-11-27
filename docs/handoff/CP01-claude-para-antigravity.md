# Handoff CP-01 · Claude Code → Antigravity

> **Branch:** `feat/cp01-nucleo` (ainda sem commit; a pasta de trabalho é compartilhada)
> **Especificação:** [docs/sdd/CP01_NUCLEO_SPEC.md](../sdd/CP01_NUCLEO_SPEC.md)
> **Estado:** núcleo pronto — `pytest` 261 verdes, `tsc` ok, `vitest` ok, `npm run build` ok.

---

## 1. Contrato pronto para uso

### `GET /api/public/config`
Sem login, sem cookie, com cache de CDN de 60 s.

```json
{
  "flags": { "vitrine": false, "estoque": false, "microchip": false, "isolamento": false,
             "pos_adocao": false, "termo_digital": false, "candidaturas": false,
             "carteira": false, "mapa": false },
  "turnstile_site_key": null,
  "whatsapp_adocao": null
}
```

- **Tipos:** `app/views/src/types/contratos.ts`, que exporta `ConfigPublica`, `FlagPublica`, `FLAGS_PUBLICAS` e `CONFIG_PUBLICA_FECHADA`.
- **Cliente:** `app/views/src/api/public.ts`, função `obterConfigPublica(sinal?)`.
  - Nunca lança erro de rede: em qualquer falha devolve `CONFIG_PUBLICA_FECHADA` (tudo desligado).
  - Usa `credentials: "omit"`. **Não troque por `requisitar()` de `http.ts`**: isso mandaria o cookie e quebraria o cache.
- **Pode começar agora** a tarefa 6 do CP-01: `FlagsContext.tsx`, `<RequerFlag>` e `<RotaComFlag>`, consumindo `obterConfigPublica()`.

### `GET /api/admin/nao-aptos` (D2)

| Parâmetro | Comportamento |
| :--- | :--- |
| `q` | Busca **só por nome**, parcial. Números no `q` não procuram mais CPF/telefone. |
| `cpf` | 11 dígitos, aceita com ou sem pontuação. Busca exata. |
| `telefone` | 10 ou 11 dígitos com DDD. Busca exata. |

- CPF/telefone incompleto ou inválido, ou os dois juntos → `400` com `mensagem` pronta para a tela.
- A sua `listarNaoAptos({cpf|telefone})` já está no formato certo ✅.

### Formato dos dados devolvidos

| Campo | Formato |
| :--- | :--- |
| `cpf` (lista sigilosa) e `adotante_cpf` (adoção, só Admin) | Formatado, `000.000.000-00`. |
| `telefone` (lista sigilosa) e `adotante_telefone` (adoção) | Só dígitos. Registros antigos podem vir como foram digitados. Use `mascararTelefone` para exibir. |

### Validação no servidor (espelho das suas máscaras)

| Campo | Regra |
| :--- | :--- |
| CPF | 11 dígitos, dígito verificador válido, não repetido. Aceita só dígitos, `.`, `-` e espaço. |
| Telefone | 10 ou 11 dígitos, DDD de 11 a 99. Com 11 dígitos, o 3º precisa ser `9`. Aceita só dígitos, `()`, `-`, `+` e espaço. |

---

## 2. Revisão do seu diff do CP-01 (Claude Code, 26/11/2026)

**No geral, está bom.**
- Máscaras completas, com cursor estável e teclas de apagar tratadas.
- Busca segmentada por Nome, CPF ou Telefone.
- `AuthProvider` isolado das rotas públicas.
- `/privacidade` coerente com o R6.
- `DEPLOY.md` com o aviso da chave.
- Build e Vitest verdes.

Só altere os arquivos da sua lista.

### 🔴 Corrigir antes do merge

1. **`.env.example`: valores de exemplo que passam por segredo real.**
   - **Problema:**
     - `TURNSTILE_SECRET_KEY=1x0000…AA` é a chave de teste da Cloudflare, que aprova qualquer requisição.
     - `PII_HMAC_KEY` e `SECRET_KEY` de exemplo têm mais de 32 caracteres, então passariam na checagem de tamanho.
     - Com a `PII_HMAC_KEY` conhecida, quem tiver acesso ao banco recalcula o índice dos ~10⁹ CPFs possíveis e descobre quem está na lista sigilosa.
     - `PII_FERNET_KEYS=SUBSTITUA…` não é uma chave Fernet válida: em desenvolvimento, quem copiar o arquivo para `.env` recebe erro 500 ao salvar um CPF.
   - **O que eu já fiz:** a produção agora **se recusa a subir** com esses valores de exemplo (`parece_valor_de_exemplo`, com testes em `test_producao.py`).
   - **O que falta da sua parte:** deixe **vazios** no `.env.example` os campos `PII_FERNET_KEYS`, `PII_HMAC_KEY`, `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY` e `CRON_SECRET`. Vazios, o desenvolvimento usa chaves derivadas automáticas e o Turnstile é ignorado. Coloque as instruções de geração e as chaves de teste só em comentários.

2. **`CampoMascarado`: o `maxLength` corta o texto colado.**
   - **Problema:** o navegador trunca a colagem no `maxLength` **antes** do `onChange`. Exemplos:
     - Telefone copiado do WhatsApp `+55 (41) 99999-8888` (19 caracteres) vira `+55 (41) 99999-`, o que dá um número errado.
     - CPF com prefixo `CPF: 529.982.247-25` perde os dígitos finais.
     - Isso contraria a regra 4.2 ("colar valor formatado dá o mesmo resultado").
   - **Correção:**
     - remova o `maxLength` do `<input>`, porque a máscara já limita a 11 dígitos;
     - no telefone, se a colagem tiver 12–13 dígitos começando com `55`, descarte o DDI;
     - acrescente esses dois casos ao Vitest.

### 🟡 Ajustes menores

3. **`AdminPage` → `NaoAptos`:** enquanto o CPF ou telefone ainda está incompleto, a tela mostra a **lista inteira**. Mostre só a dica "Digite o CPF completo para procurar." e esconda a lista até o número ficar válido. Hoje a lista inteira aparece como se fosse o resultado.
4. **`DEPLOY.md`, sobre a rotação:** "até regravar os registros" depende de um comando que ainda não existe (`flask pii-rotate`, previsto para um CP futuro). Escreva "a regravação é feita pelo comando de rotação (a ser entregue)" para ninguém tirar a chave antiga cedo demais.
5. **Rotas públicas ainda sem flag:** ok por enquanto, pois mostram só "Em breve". Coloque-as atrás de `<RotaComFlag>` assim que fizer o `FlagsContext`.

Quando terminar, crie o `CP01-antigravity-para-claude.md` (seção 3 das instruções) para a revisão final (Gate 7).

---

## 3. Lembretes da seção 2 das instruções

- `app/utils/publico.py`, `app/controllers/public_controller.py`, `types/contratos.ts` e `api/public.ts` são meus. Se precisar de algo neles, peça aqui.
- **Nenhuma tela pública pode chamar `/auth/*` nem usar o `AuthContext`.** O teste canário do back-end não enxerga isso; quem garante é a sua aba Network.

---

## 4. Rodada 2 · Revisão final do CP-01 (26/11/2026)

O `gapar-qa-gatekeeper` reprovou o CP-01 por um problema **do meu lado** (o `flask pii-backfill`), que já está corrigido. O `gapar-frontend-ux` aprovou a sua parte, **sem nenhum 🔴**. Abaixo, o que muda para você.

### 🔴 Mudança de contrato: busca da lista sigilosa por POST

O CPF e o telefone na URL ficavam gravados nos logs de acesso da Vercel. A busca agora é feita assim:

- `POST /api/admin/nao-aptos/busca`, com corpo `{ "cpf": "52998224725" }`, `{ "telefone": "41999998888" }` ou `{ "q": "parte do nome" }`.
  - Exatamente **um** filtro por chamada.
  - A resposta é a mesma de antes: `{ sucesso, total, nao_aptos[] }`.
- `GET /api/admin/nao-aptos` continua listando tudo, mas **devolve 400** se receber `?q`, `?cpf` ou `?telefone`.
- O tipo está documentado em `types/contratos.ts`, em `BuscaListaSigilosa`.

**O que fazer:**
- Em `api/admin.ts`, a `listarNaoAptos({cpf|telefone})` passa a chamar `requisitar("/api/admin/nao-aptos/busca", { metodo: "POST", json: filtro })`.
- Sem filtro, continua no `GET`.
- **Até você trocar, a busca por CPF ou telefone na tela responde 400.**

### 🟡 Achados da revisão de front-end (nenhum bloqueia)

Os três primeiros são os mais importantes.

| # | Onde | Problema | Correção |
| :-: | :--- | :--- | :--- |
| 1 | `AdminPage.tsx`, busca de CPF/telefone | Ao completar o número, aparece "Ninguém encontrado" durante a requisição. No 3G, a administradora pode achar que a pessoa está liberada. | Com `lista.carregando` e uma busca válida, mostre `<Esqueleto>`, não o estado vazio. |
| 2 | `Campos.tsx`, linhas 244–251, e `mascaras.ts`, linhas 48–54 | Digitar um dígito **no meio** de `(55) 99999-8888` faz o "55" ser descartado como DDI. O número errado é salvo sem nenhum erro. | Descarte o DDI só quando entram 2 ou mais dígitos de uma vez (colagem). Teste no Vitest. |
| 3 | `FlagsContext.tsx`, linhas 29–42 | Se `/api/public/config` nunca responder (portal cativo, 3G ruim), as páginas públicas ficam em "Carregando..." para sempre. | Tempo limite de ~8 s que encerra o carregando e mantém tudo fechado. Não use `abort()`: o `AbortError` é engolido. |
| 4 | `FlagsContext.test.ts` | Os testes cobrem só `obterConfigPublica`, que é meu, e não o provider. | `renderToString` (de `react-dom/server`) com `<RequerFlag>` e `<RotaComFlag>` no estado inicial. |
| 5 | `App.tsx`, linhas 103–146 | Um único `<Suspense>` faz o cabeçalho público piscar ao carregar uma página lazy. | Um `<Suspense>` em volta do `<Outlet/>` de cada layout. |
| 6 | `LayoutPublico.tsx`, linhas 20–21 | Com a vitrine desligada, o logo leva a "Página não encontrada". | Logo para `/adote` só com a flag `vitrine` ligada; senão, para `/privacidade`. |
| 7 | `App.tsx`, linhas 149–172 | `/termo`, `/carteira/` e `/adote/x/y` caem no `*` interno, que chama `/auth/status` e leva ao login. | Rotas públicas de 404 para esses prefixos dentro do `LayoutPublico`. |
| 8 | `Layout.tsx`, linhas 204–218 | Os itens da gaveta "Mais" não marcam a página atual. | Usar `NavLink`, que já põe `aria-current`. |
| 9 | `CP01-antigravity-para-claude.md` | Faltam os prints em 360px e desktop. | Anexe quando houver Preview. |

**Correção sobre o seu handoff:** a alteração no `vercel.json` (deploy desligado para a branch) foi feita **por mim** e entrou no mesmo commit que o seu fechamento. A sua declaração de não ter mexido em arquivos meus está correta.

### Parecer final do gatekeeper (rodada 2): APROVADO, com uma condição para o merge

- **Condição antes do merge na `main`:** trocar a busca da lista sigilosa para `POST /api/admin/nao-aptos/busca` em `api/admin.ts` (seção 4, acima). Sem isso, a busca por CPF ou telefone fica quebrada.
- **`docs/DEPLOY.md`:** acrescente o passo da **impressão digital** antes do backfill, como está no §7 de `docs/sdd/CP01_NUCLEO_SPEC.md`:
  1. comparar a linha `Chaves PII em uso` do log da Vercel com a saída de `flask pii-backfill --dry-run`;
  2. se forem diferentes, parar.
