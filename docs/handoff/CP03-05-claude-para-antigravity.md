# Handoff CP-03, CP-04 e CP-05 · Claude Code → Antigravity

> **Branch:** `feat/cp01-nucleo`. **Commits:** `8b0f514` (dados) e `6dc7cb9` (rotas e serviços, que inclui o seu `og_controller.py`). **Spec:** [docs/sdd/CP03_05_FASE2_SPEC.md](../sdd/CP03_05_FASE2_SPEC.md).
> **Estado:** API real disponível, `pytest` com 640 verdes. A revisão do gatekeeper está em andamento.
> O contrato publicado em `types/contratos.ts` foi cumprido **sem mudança de nome**. Só entraram os campos novos listados abaixo.

---

## 1. Integre agora com a API real

Ligue as flags no `.env` local: `FEATURE_ESTOQUE=true`, `FEATURE_MICROCHIP=true` e `FEATURE_ISOLAMENTO=true`. Com a flag desligada, todas as rotas do módulo respondem 404, inclusive para a Administradora.

### Estoque
- As rotas são exatamente as do contrato. Criar e editar item, criar lote e registrar movimento são só da Administradora. Leitura, detalhe e `/fefo` valem para qualquer perfil logado.
- Respostas de erro:

  | Código | `causa.erro` | Quando |
  | :-: | :--- | :--- |
  | **409** | `"Saldo insuficiente"` | A saída deixaria o saldo negativo (RN18). |
  | **409** | `"Lote duplicado"` | Já existe um lote com este código no item. |
  | **422** | `"Lote vencido"` | Saída de uso de um lote vencido (RN20). Um lote que vence hoje ainda pode ser usado. |
  | **400** | — | Tipo `SAIDA_USO` enviado pela rota de movimentos, motivo vazio ou quantidade ≤ 0. |

- **⚠️ Corresponde ao 🔴 2 da revisão:** decida pela chave `causa.erro` acima. As rotas de **saúde** têm outros 422, como "Ficha congelada" (RN05) e "Prescrição fora da validade" (RN09), que precisam mostrar a mensagem do servidor.

### Baixa na saúde
- `POST /api/saude/vacinas/:id` e `POST /api/saude/medicacao/baixa/:id` aceitam `lote_id` e `quantidade`.
- Se a baixa falhar (400, 409 ou 422), **o registro de saúde também não é gravado**.
- A resposta ganha o campo opcional **`movimento`** (`MovimentoEstoque`).
- Regras de envio:
  - `lote_id` com a flag de estoque desligada → **400 "Estoque desativado"**. Com a flag desligada, não envie `lote_id`.
  - `lote_id` nulo ou vazio é ignorado.
  - Na vacina, um lote de item que não é da categoria "Vacina" → 400.
- Uma dose de medicação já baixada devolve o "já baixado" de sempre e não consome estoque de novo.

### `/api/hoje`
- `estoque` (`AlertasEstoqueHoje`): só para a Administradora com a flag ligada.
- `isolamentos`: para qualquer perfil, com a flag ligada.
- Com a flag desligada, a chave **não vem na resposta**. Use `?.`.

### Microchip
- **⚠️ Corresponde ao 🔴 1 da revisão:** com a flag desligada, um `numero_microchip` **preenchido** → **400 "Microchip desativado"**. Vazio ou `null` é ignorado. Com a flag desligada, omita a chave.
- Com a flag ligada:
  - o número precisa ter 15 dígitos; vazio limpa;
  - número repetido → **409 `ConflitoMicrochip`** (`animal_id` e `animal_nome`), mesmo quando o outro animal foi excluído;
  - ficha congelada → 422 (RN05).
- `GET /api/animais/microchip/:numero` → `{ animal: ResumoMicrochip }` ou 404.

### Isolamento
- Abrir um isolamento responde:

  | Código | Quando |
  | :-: | :--- |
  | **409** | Já existe um isolamento aberto. |
  | **422** | Animal congelado ou excluído. |
  | **404** | Animal inexistente. |
  | **400** | Motivo vazio ou com mais de 200 caracteres, fim previsto antes do início, ou início no futuro. |

- Encerrar → **409** se já estiver encerrado. **Encerrar é permitido mesmo com a ficha congelada**, porque um animal que foi a óbito durante o isolamento precisa sair da lista de abertos.
- `isolamento_aberto` vem na ficha e em cada item de `GET /api/animais`.
- Um animal isolado sai da vitrine e volta sozinho quando o isolamento é encerrado.

---

## 2. Junto com a integração
Corrija os itens de `docs/handoff/REVISAO_RODADA4_PARA_ANTIGRAVITY.md`, começando pelos dois 🔴.

Depois rode `python scripts/homologacao.py` localmente contra `http://localhost` com `--permitir-http`, para exercitar os cenários da Fase 2 contra a API real.

**Ao terminar:** atualize `docs/handoff/CP05-antigravity-para-claude.md` (seção "Rodada 4b") com as evidências de `npm run build`, `npm test`, `python -m pytest -q` e da homologação local.
