# CP-03, CP-04 e CP-05 · Fase 2 — Especificação do núcleo (SDD)

> **Dono:** Claude Code (agentes `gapar-db-architect`, depois `gapar-backend-security`) · **Branch:** `feat/cp01-nucleo`.
> **Contrato do front (fonte da verdade dos nomes):** `app/views/src/types/contratos.ts`, seção "CONTRATOS PREVISTOS DA FASE 2". O Antigravity constrói as telas sobre ele **em paralelo**. Pode ganhar campos, nunca perder nem renomear.
> **Base:** SDD v5.1 §4.2 (itens 3, 4 e 5), §4.3 e §7 (RN18–RN22). D1: o microchip é `UNIQUE` simples.
> **Linha de base:** 400 testes `pytest` verdes (commit `db40ea6`).

---

## CP-03 · Estoque com lotes FEFO (RN18, RN19, RN20) · migração `0005_estoque_insumos`

| ID | Requisito |
| :-- | :--- |
| **REQ-32** | **Três tabelas novas, todas com RLS** (`TABELAS_RLS`):<br>• `inventory_items`: CHECK de `categoria` e `unidade` pelos valores de `CategoriaInsumo`/`UnidadeInsumo`; `estoque_minimo NUMERIC(10,2) >= 0`; `is_active`; `is_deleted`; `@proibir_exclusao_fisica`.<br>• `inventory_batches`: `item_id` FK; `codigo_lote`; `data_validade`; `saldo_atual NUMERIC(10,2) CHECK >= 0` (RN18); `UNIQUE(item_id, codigo_lote)`; índice FEFO `(item_id, data_validade, id)`; `@proibir_exclusao_fisica`.<br>• `inventory_movements`: `@tornar_imutavel` (RN19); `tipo` CHECK; `quantidade > 0`; `saldo_apos >= 0`; `motivo NOT NULL`; FKs opcionais para `animals`, `vaccinations` e `medication_logs`; `user_id ON DELETE SET NULL`. |
| **REQ-33** | **Gatilhos no PostgreSQL:**<br>• RN03 (sem DELETE/TRUNCATE) em `inventory_items` e `inventory_batches`;<br>• imutabilidade (sem UPDATE/DELETE/TRUNCATE) em `inventory_movements`, com uma função nova `gapar_bloquear_mutacao_registro_imutavel()`, no mesmo padrão da `0002`. |
| **REQ-34** | **`inventory_service`:**<br>• toda alteração de saldo passa por ele, com `SELECT … FOR UPDATE` no lote (no SQLite, um único UPDATE condicional);<br>• FEFO: validade mais próxima primeiro, sem validade por último, vencidos fora;<br>• saída que deixaria o saldo negativo → `409` (RN18);<br>• lote vencido usado em saída de uso → `422` (RN20);<br>• grava o movimento com `saldo_apos`. |
| **REQ-35** | **Rotas `/api/estoque/*`**, exatamente como no contrato, atrás de `@require_feature("estoque")`:<br>• criar, editar, ajustar e dar entrada: só Administradora;<br>• leitura e sugestão FEFO: qualquer perfil logado;<br>• auditoria sem dado pessoal. |
| **REQ-36** | **Baixa ao registrar saúde:**<br>• `POST /api/saude/vacinas/:id` e `POST /api/saude/medicacao/baixa/:id` aceitam `lote_id` e `quantidade` (opcionais);<br>• a baixa acontece na mesma transação do registro de saúde;<br>• lote de vacina precisa ser de item com categoria `Vacina` (senão `400`).<br>• `GET /api/hoje` ganha `estoque` (`AlertasEstoqueHoje`), só para a Administradora e com a flag ligada. |
| **REQ-37** | **Testes:**<br>• corrida concorrente: dois consumos simultâneos do último saldo, e só um passa. No SQLite, por UPDATE condicional; no PostgreSQL, documentar;<br>• RN19 pelo ORM;<br>• RN20 por data;<br>• FEFO em todas as ordens;<br>• migração sobe, desce e sobe de novo;<br>• RLS. |

## CP-04 · Microchip ISO 15 dígitos (RN21) · migração `0006_microchip_iso`

| ID | Requisito |
| :-- | :--- |
| **REQ-38** | **Coluna `animals.numero_microchip`:**<br>• `VARCHAR(15) NULL`, com **`UNIQUE` simples** (D1: o cão devolvido é o mesmo registro);<br>• CHECK ANSI: `numero_microchip IS NULL OR (length(numero_microchip) = 15 AND ltrim(numero_microchip, '0123456789') = '')`.<br>• Os dados legados continuam valendo: `is_microchipado=True` sem número é aceito. |
| **REQ-39** | **Cadastro e edição:**<br>• `POST/PATCH /api/animais` aceitam `numero_microchip`, que, preenchido, deixa `is_microchipado=True`;<br>• `400` para formato inválido;<br>• `409` `ConflitoMicrochip` com `animal_id` e `animal_nome` (só para usuário logado).<br>• A edição continua bloqueada para ficha congelada (RN05). |
| **REQ-40** | **`GET /api/animais/microchip/:numero`:**<br>• devolve `ResumoMicrochip` ou `404`;<br>• número fora do formato → `404` sem consultar o banco;<br>• atrás de `@require_feature("microchip")`.<br>• O campo **não** entra na allowlist pública (o canário continua verde). |

## CP-05 · Isolamento sanitário e Kanban (RN22) · migração `0007_isolamento_sanitario`

| ID | Requisito |
| :-- | :--- |
| **REQ-41** | **Tabela `isolation_records`:**<br>• colunas como no SDD §4.2-5, com `@proibir_exclusao_fisica` e RLS;<br>• CHECK `data_fim_prevista >= data_inicio`;<br>• **índice único parcial `uq_isolation_aberto_por_animal ON (animal_id) WHERE fim_real IS NULL`** (RN22), com `postgresql_where` **e** `sqlite_where`;<br>• gatilho RN03 no PostgreSQL. |
| **REQ-42** | **Rotas** exatamente como no contrato, atrás de `@require_feature("isolamento")`:<br>• abrir → `409` se já houver isolamento aberto; `422` se o animal estiver congelado ou excluído;<br>• encerrar → `409` se já estiver encerrado;<br>• auditoria. |
| **REQ-43** | **`isolamento_aberto`** aparece no `to_dict` e em cada item de `GET /api/animais`, sem N+1 (uma consulta para a página).<br>• `GET /api/hoje` ganha `isolamentos` com a flag ligada. |
| **REQ-44** | **RN17 ampliada:** animal com isolamento aberto **não aparece na vitrine** (`query_vitrine` e `buscar_publicado`). Ao abrir um isolamento, `is_publicado` não muda: quando ele é encerrado, o animal volta para a vitrine se continuar publicado e disponível. Escolha documentada: o isolamento é temporário e não deve exigir republicação. |
| **REQ-45** | **Testes:**<br>• RN22 no ORM e no banco (dois abertos → IntegrityError no SQLite);<br>• abrir, encerrar e reabrir;<br>• vitrine escondendo o animal isolado;<br>• N+1;<br>• migração e RLS. |

---

## Ordem e entregas

1. **`gapar-db-architect`:** modelos, migrações `0005` → `0006` → `0007` (encadeadas depois da `0004`), gatilhos, RLS e os testes de banco de cada uma.
2. **`gapar-backend-security`:** services, rotas, `/api/hoje`, baixa na saúde e testes de API.
3. **`gapar-qa-gatekeeper`:** 7 Gates e mutações dos três CPs.
4. **Claude Code:** handoffs `CP03-…`, `CP04-…` e `CP05-claude-para-antigravity.md`.
