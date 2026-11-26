# Instruções para o Antigravity — Ampliação GAPAR v5.1

> **Leia antes de qualquer alteração:** [PLANO_DIVISAO_TRABALHO.md](../PLANO_DIVISAO_TRABALHO.md) e o §10 do [SDD](../SDD_AMPLIACAO_FASES_2_A_4.md). O §10 (v5.1) prevalece sobre o resto do SDD.
> **Você é responsável por:** telas React, CRUDs simples, integrações periféricas (Open Graph, mapa, geocodificação), homologação e documentação.
> **O Claude Code é responsável por:** banco, criptografia, segurança, rotas públicas e regras de negócio críticas, além de revisar todo o seu diff antes do merge.

---

## 1. Decisões já tomadas pela ONG (não reabrir)

| # | Decisão | O que muda para você |
| :-: | :--- | :--- |
| **D1** | Na devolução, **o cão continua o mesmo animal**. Uma ficha tem várias adoções ao longo do tempo, com só uma vigente. | Não existe "novo ciclo" nem `ciclo_anterior_id`/`animal_raiz_id`. A `AbaAdocao` passa a mostrar a adoção vigente e um histórico de adoções encerradas. |
| **D2** | Busca de CPF e telefone na lista sigilosa **só com o número completo**. Todo campo de CPF/telefone tem **máscara que não deixa digitar nada além de dígitos no formato certo**. | Seção 4 deste documento. |

---

## 2. O que você NÃO pode fazer

1. **Não criar nem editar:** `migrations/**`, `app/models/**`, `app/__init__.py`, `app/config.py`, `app/extensions.py`, `app/utils/crypto.py`, `app/utils/validation.py`, `app/controllers/public_controller.py`, `app/controllers/applications_controller.py`, `vercel.json`, `app/views/src/types/contratos.ts`, `app/views/src/api/public.ts`.
2. **Não alterar** as partes de devolução, termo e carteira em `adoptions_controller.py` nem a busca/RN15 em `admin_controller.py`.
3. **Não serializar** model com `to_dict()` em rota ou tela pública. Use só os campos que o contrato expõe.
4. **Não gravar** CPF, telefone, endereço ou nome de candidato/adotante em `AuditLog.detalhes`, `console.log`, mensagens de erro, URLs ou query strings.
5. **Não adicionar** dependência Python. NPM só `qrcode`, `leaflet` e `supercluster`, sempre em chunk `lazy`.
6. **Não mudar** um contrato de API. Se o contrato não atender a tela, peça a mudança pelo handoff (seção 3).

Se uma tarefa exigir mexer em algo dessa lista, **pare e registre o pedido no handoff**.

---

## 3. Como trabalhar

1. Espere o arquivo `docs/handoff/CPXX-claude-para-antigravity.md`. Ele traz a branch base, o contrato e como testar. **Exceção:** as tarefas marcadas "pode começar já" não dependem dele.
2. Trabalhe na branch `feat/cpXX-telas`, criada a partir de `feat/cpXX-nucleo`.
3. Antes de pedir revisão, rode tudo e confirme que fica verde:
   ```
   npm run build
   npm test
   python -m pytest
   ```
4. Ao terminar, crie `docs/handoff/CPXX-antigravity-para-claude.md` com:
   - o último commit;
   - os arquivos alterados;
   - prints da tela em 360px e em desktop;
   - o que ficou pendente;
   - os pedidos de mudança no contrato.
5. Corrija os apontamentos da revisão. Depois disso, rode `python scripts/homologacao.py` no Preview da Vercel (Gate 6).

**Padrão de interface que já existe e deve ser mantido:**
- componentes `CampoTexto`, `Botao`, `Dialogo` e `Estados`;
- paleta e fonte Nunito;
- alvos de toque `min-h-11` ou maior;
- uso com uma mão em 360px;
- textos simples, sem jargão técnico, em português.

---

## 4. Máscaras de CPF e telefone (D2) — pode começar já

### 4.1. Utilitário `app/views/src/utils/mascaras.ts`

| Função | Comportamento |
| :--- | :--- |
| `soDigitos(v: string): string` | Remove tudo que não é dígito. |
| `mascararCpf(v: string): string` | Aceita no máximo 11 dígitos e formata progressivamente: `123` → `123`, `1234` → `123.4`, … → `123.456.789-09`. |
| `cpfValido(v: string): boolean` | 11 dígitos, rejeita sequências repetidas (`000…`, `111…`) e confere os dois dígitos verificadores (módulo 11). |
| `mascararTelefone(v: string): string` | Aceita no máximo 11 dígitos. Com 10 dígitos: `(00) 0000-0000`. Com 11: `(00) 00000-0000`. Formata progressivamente. |
| `telefoneValido(v: string): boolean` | 10 ou 11 dígitos, DDD de `11` a `99`. Com 11 dígitos, o terceiro precisa ser `9`. |

### 4.2. Componentes `CampoCpf` e `CampoTelefone` (em `components/Campos.tsx`)

- Ficam por cima do `CampoTexto` existente.
- `inputMode="numeric"` (CPF) e `inputMode="tel"` (telefone), além de `autoComplete="off"`.
- `maxLength` de 14 (CPF) e 15 (telefone), já contando a pontuação.
- O `onChange` passa todo valor por `soDigitos`, corta no limite e aplica a máscara. **Letras, espaços e símbolos nunca aparecem no campo**, nem colados com Ctrl+V. Colar `123.456.789-09` ou `12345678909` dá o mesmo resultado.
- `onBeforeInput`/`onKeyDown` não bloqueiam Backspace, Delete, setas e Tab. O cursor não pula para o fim ao apagar um caractere do meio.
- O valor entregue ao formulário (`onValor(digitos: string)`) é **só dígitos**. A pontuação é só visual.
- Mensagem de erro ao sair do campo (`onBlur`) quando estiver incompleto ou inválido:
  - CPF: "Confira o CPF: são 11 números." ou "Este CPF não é válido. Confira os números."
  - Telefone: "Informe o DDD e o número (10 ou 11 números)."
- Placeholders: `000.000.000-00` e `(00) 00000-0000`.

### 4.3. Onde aplicar

| Tela | Campo | Regra |
| :--- | :--- | :--- |
| `AdminPage` — cadastro na lista sigilosa (linhas ~279–280) | CPF, Telefone | Opcionais, mas se preenchidos precisam ser válidos. Trocar a validação atual (`< 8` dígitos) pela do item 4.1. |
| `AdminPage` — **busca** da lista sigilosa (linha ~234) | Novo seletor "Procurar por: **Nome** · **CPF** · **Telefone**" (botões segmentados) | **Nome:** busca parcial, como hoje. **CPF/Telefone:** o campo vira `CampoCpf`/`CampoTelefone` e a busca só dispara com o número completo e válido. Enquanto isso, mostrar: "Digite o CPF completo para procurar." |
| `AdminPage` — filtro local (linha ~225) | — | Remover o `includes` parcial em CPF e telefone. Com CPF ou telefone, a busca vai ao servidor (`GET /api/admin/nao-aptos?cpf=<11 dígitos>` ou `?telefone=<10–11 dígitos>`). O contrato final vem no handoff do CP-01. |
| `ficha/AbaAdocao.tsx` (linhas ~143–145) | Telefone (obrigatório), CPF (opcional) | Mesmas máscaras e validações. |
| CP-07 `/termo/:token` | CPF de confirmação | `CampoCpf` obrigatório. |
| CP-08 pré-triagem | CPF, Telefone | `CampoCpf` e `CampoTelefone` obrigatórios. |

**Exibição de dados antigos:** registros antigos podem ter telefone com 8–9 dígitos (sem DDD). Na listagem, mostre o valor recebido formatado com `mascararTelefone` quando tiver 10–11 dígitos e o valor como veio nos outros casos. Não bloqueie a tela.

### 4.4. Testes Vitest (`utils/mascaras.test.ts`)

Cubra pelo menos:
- dígitos digitados um a um;
- colar valor formatado;
- colar texto com letras;
- limite de 11 dígitos;
- CPF válido e inválido, incluindo sequências repetidas;
- telefone fixo, celular e sem DDD.

> O back-end (Claude) também rejeita CPF e telefone fora do padrão. A máscara é a primeira barreira, não a única.

---

## 5. Tarefas por Checkpoint

### CP-01 · Fase 0 (Sprint 1: 14/12 a 27/12/2026)

**Pode começar já**

1. Máscaras de CPF e telefone (seção 4), incluindo o seletor de busca da `AdminPage`.
2. `components/LayoutPublico.tsx`:
   - cabeçalho com o nome da ONG;
   - **nenhuma** chamada a `/auth/status`;
   - nenhum menu interno;
   - rodapé com link para `/privacidade`.
3. Rotas públicas no `App.tsx`, fora do `AuthContext`: `/adote`, `/adote/:slug`, `/termo/:token`, `/carteira/:token` e `/privacidade`. Por enquanto, `/adote`, `/adote/:slug`, `/termo/:token` e `/carteira/:token` mostram só um estado "Em breve" atrás de flag. As páginas públicas devem ser carregadas com `lazy()`.
4. Página `/privacidade`:
   - texto em `pages/publico/PrivacidadePage.tsx`, com a constante `VERSAO_POLITICA = "v1.0-2026"`;
   - seções: quem somos, quais dados coletamos, para quê, por quanto tempo (candidaturas recusadas: 180 dias), direitos do titular e contato.
   - Marque no topo como "Texto provisório — aguarda revisão jurídica".
5. `.env.example` e `docs/DEPLOY.md` com as novas variáveis:
   - `PII_FERNET_KEYS`, `PII_HMAC_KEY`;
   - `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`;
   - `PUBLIC_WHATSAPP_ADOCAO`, `CRON_SECRET`;
   - `FEATURE_*`.
   - Valores sempre fictícios. Explique como gerar as chaves (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) e **avise que perder a `PII_FERNET_KEYS` torna os CPFs ilegíveis para sempre**.

**Depois do handoff do Claude**

6. `contexts/FlagsContext.tsx` consumindo `GET /api/public/config`. Contrato previsto, a confirmar no handoff:
   ```json
   {
     "flags": { "vitrine": false, "estoque": false, "microchip": false, "isolamento": false,
                "pos_adocao": false, "termo_digital": false, "candidaturas": false,
                "carteira": false, "mapa": false },
     "turnstile_site_key": "string | null",
     "whatsapp_adocao": "string | null"
   }
   ```
   - Fail-closed: todas as flags são `false` até a resposta chegar e continuam `false` se der erro.
   - Exporta `useFlags()`, `<RequerFlag flag="...">` e `<RotaComFlag flag="...">`. Com a flag desligada, a rota mostra `NaoEncontradaPage`.
7. Navegação interna: manter as 4 abas atuais e criar a gaveta **"Mais"** (folha inferior, botões `min-h-14`). Itens futuros (Estoque, Candidaturas, Mapa, Gestão) aparecem só com a flag ligada **e** com o perfil certo.

**Pronto quando:**
- as máscaras funcionam em todas as telas da seção 4.3, com Vitest verde;
- `/privacidade` abre sem login, em 360px, sem nenhuma chamada a `/auth/*` na aba Network;
- `npm run build` fica verde.

### CP-02 · Vitrine pública (RN17)

- **`/adote`:** grade de cards (foto, nome, porte, sexo, idade). Mostrar estado vazio amigável e paginação ou "carregar mais". Fotos com `loading="lazy"` e `width`/`height` fixos.
- **`/adote/:slug`:** fotos, descrição pública e botão **"Quero adotar pelo WhatsApp"**. O botão monta o `wa.me/<whatsapp_adocao>?text=` com mensagem pronta contendo só o nome do animal. Se o animal não estiver mais disponível, mostrar "Este cão já encontrou um lar" e link para a vitrine.
- **`AbaDados` (só Admin):** interruptor "Publicar na vitrine" e campo "Descrição para o público", com contador de caracteres. O interruptor fica desabilitado e explicado quando o status não for `disponível`.
- **`app/controllers/og_controller.py`:**
  - HTML mínimo com `og:title`, `og:description`, `og:image` (URL absoluta `https://`) e `og:url`;
  - **todo valor passa por `markupsafe.escape`**;
  - animal não disponível → fallback institucional, sem dado do animal.
  - O Claude configura o rewrite no `vercel.json`.
- Validar o preview colando o link no WhatsApp e mandar print no handoff.

### CP-03 · Estoque FEFO (RN18–RN20)

- **`app/controllers/inventory_controller.py` (`/api/estoque`):**
  - CRUD de itens e lotes (`@admin_required` para criar, editar e ajustar);
  - **toda alteração de saldo chama `inventory_service`**; nunca altere `saldo_atual` direto;
  - movimentos não têm rota de editar nem de apagar.
- **Tela `/estoque`:**
  - lista de itens com saldo total e selos "Acabando" (abaixo do mínimo) e "Vence em X dias";
  - detalhe com lotes em ordem FEFO;
  - modal "Entrada de lote" e modal "Ajustar saldo", com motivo obrigatório.
- **`<SeletorLoteFefo />`** nos formulários de Vacina e Medicação:
  - sugere o primeiro lote válido;
  - lotes vencidos aparecem desabilitados com o texto "Vencido";
  - a quantidade fica limitada ao saldo;
  - tratar os retornos `409`/`422` com mensagem clara.
- **Bloco "Estoque" no `HojePage`** (só Admin, atrás de flag): itens acabando e lotes vencendo em 30 dias.

### CP-04 · Microchip e placa QR (RN21)

- Campo "Número do microchip" no `FormularioAnimal`:
  - só dígitos, máximo 15, mesma técnica de máscara da seção 4;
  - exibição em grupos `000 000 000 000 000`.
- `utils/microchip.ts` (`validarMicrochip`, `formatarMicrochip`) com Vitest.
- **Busca em `/animais`:** ao receber 15 dígitos seguidos de `Enter` (leitor USB HID), buscar **sem debounce** e abrir a ficha direto se houver um único resultado.
- Erro `409` ("número já usado por <animal>"): mostrar o nome do animal com link para a ficha dele.
- **`<DialogoEtiquetaBaia />`:**
  - etiqueta A6 retrato com nome, foto, baia, microchip e QR para a ficha interna;
  - `@media print` esconde todo o resto;
  - `qrcode` carregado com `import()` só ao abrir o diálogo.

### CP-05 · Kanban, isolamento (RN22) e homologação da Fase 2

- **Rotas:** abrir isolamento (motivo, protocolo, data prevista) e encerrar isolamento (observações de alta). A RN22 já é garantida no banco; trate o `409` com "Este animal já está em isolamento".
- **Alternância Lista ↔ Quadro em `/animais`:**
  - no Kanban, uma coluna por status;
  - drag-and-drop **nativo** (HTML5) no desktop;
  - em 360px, botão "Mover…" que abre uma folha com os status permitidos;
  - respeitar as transições do back-end: `adotado` nunca aparece como destino.
- `<SeloIsolamento />` no card, banner na ficha e bloco prioritário "Em isolamento" no topo do `HojePage`.
- `scripts/homologacao.py`: cenários da Fase 2 (vitrine, estoque, microchip, isolamento).

### CP-06 · Pós-adoção e devolução (D1: mesmo animal)

- **`AbaAdocao`:**
  - adoção vigente no topo;
  - abaixo, a seção "Histórico de adoções" com as adoções encerradas (data, adotante, data e motivo da devolução), todas só leitura.
- **Diálogo "Registrar devolução"** (só Admin):
  - campos: data, motivo e observações;
  - confirmação explícita: "{nome} volta para o abrigo como 'em acolhimento'. A adoção atual fica guardada no histórico.";
  - depois de confirmar, a ficha volta a ser editável.
- **Retornos 30/90/180 dias:**
  - lista de retornos na `AbaAdocao` com o botão "Registrar retorno" (canal, resultado `ok`/`atenção`/`devolução`, observações);
  - o resultado "devolução" sugere abrir o diálogo de devolução.
- **Bloco "Retornos de hoje" no `HojePage`:** botão `wa.me` com o telefone do adotante. A mensagem pronta não deve incluir o CPF.

### CP-07 · Termo digital (RN23)

- **Página pública `/termo/:token`:**
  - mostra o texto do termo e campos de confirmação: Nome completo e `CampoCpf`;
  - widget Turnstile e botão "Li e aceito";
  - estados: link expirado, já assinado, bloqueado por tentativas e sucesso (com download do PDF).
- **Ficha (Admin):**
  - botão "Gerar link do termo" com cópia do link e envio por `wa.me`;
  - selo "Termo aceito em dd/mm/aaaa (versão X)" e botão para baixar o PDF.
- **Tela Admin "Modelos de termo":**
  - lista de versões e "Nova versão" (título e texto);
  - sem editar nem apagar versões antigas.

### CP-08 · Pré-triagem online (RN24, RN25)

- **`<FormularioPreTriagem />` em `/adote/:slug`, em 3 passos curtos:**
  1. Contato: nome, `CampoCpf`, `CampoTelefone`, cidade/UF.
  2. Moradia e rotina.
  3. Consentimento LGPD (caixa não marcada por padrão, com link para `/privacidade`) e Turnstile.
- **Resposta sempre igual:** "Recebemos seu formulário! Protocolo GP-XXXXXXXX." **Nunca** mostre nada diferente conforme a resposta do servidor, além de erro de validação dos campos.
- Com `pausar_candidaturas`, mostrar "As candidaturas para {nome} estão pausadas" e só o botão do WhatsApp.
- **Fila `/candidaturas`:**
  - filtros por etapa;
  - a Voluntária vê o CPF mascarado e nenhum alerta;
  - a Admin vê o selo "Atenção: lista sigilosa" quando o contrato trouxer `alerta_rn15`;
  - botão "Converter em adoção" (1 clique, abre a `AbaAdocao` preenchida).
- Botão "Pausar candidaturas" na ficha (Admin).

### CP-09 · Carteira de vacinas e homologação da Fase 3

- **Página pública `/carteira/:token`:**
  - estilo caderneta: foto, nome, vacinas aplicadas e próximos reforços;
  - botão "Adicionar lembretes ao calendário" (`.ics`);
  - **nenhum dado do adotante**;
  - link revogado → "Este link não está mais ativo. Fale com a ONG."
- **Ficha (Admin):** "Gerar link da carteira", "Reenviar pelo WhatsApp" e "Revogar link", com confirmação.
- `homologacao.py`, fluxo completo: candidatura → termo → carteira → primeiro retorno.

### CP-10 · Mapa de resgates

- **`<CapturaLocalizacao />` no cadastro de animal:**
  - botão "Usar minha localização" (`navigator.geolocation`, só com o clique da usuária);
  - fallback de marcar no mapa;
  - campo de bairro.
- **`scripts/geocodificar.py`:**
  - Nominatim com **1 requisição/s**;
  - `User-Agent` genérico da ONG, **sem e-mail pessoal**;
  - usa `geocoding_cache`;
  - resultados ambíguos marcados como `ambiguo_revisar`;
  - opção `--dry-run`.
- **`app/controllers/map_controller.py` (`/api/mapa`, `@admin_required`):**
  - pontos com filtros;
  - resumo por bairro;
  - exportação **somente da contagem por bairro**.
- **Página `/mapa`** (Admin, `lazy`):
  - `leaflet` + `supercluster` em chunk `vendor-mapa`;
  - `L.divIcon` na paleta do sistema;
  - confirmar no build que o chunk não é baixado em `/hoje` nem em `/animais`.

### CP-11 · Encerramento

- `scripts/homologacao.py` v5.0 cobrindo as 4 fases.
- Atualização de `README.md`, `docs/DEPLOY.md` e Requisitos v5.0, com as RN17–RN25 e a RN05 reescrita.

---

## 6. Checklist antes de cada pedido de revisão

- [ ] Não alterei nenhum arquivo da seção 2.
- [ ] `npm run build`, `npm test` e `python -m pytest` estão verdes.
- [ ] Testei em 360px e em desktop.
- [ ] Nenhum dado pessoal aparece em log, console, URL ou mensagem de erro.
- [ ] Toda tela nova está atrás da flag certa e é carregada com `lazy()` quando não é usada no dia a dia.
- [ ] Os campos de CPF/telefone usam `CampoCpf`/`CampoTelefone`.
- [ ] O handoff `CPXX-antigravity-para-claude.md` está criado.
