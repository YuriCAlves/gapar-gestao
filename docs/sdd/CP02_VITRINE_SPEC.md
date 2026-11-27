# CP-02 · Vitrine pública (RN17) — Especificação do núcleo (SDD)

> **Dono:** Claude Code (agentes `gapar-db-architect` e `gapar-backend-security`) · **Branch:** `feat/cp01-nucleo` (continua nela até o merge do CP-01) · **Base:** SDD v5.1 §4.2-2, §5.2, contrato previsto em `app/views/src/types/contratos.ts` (`AnimalPublico`, `PaginaVitrine`, `RespostaAnimalPublico`, `CamposVitrineDaFicha`).
> **Linha de base:** 282 testes `pytest` verdes (commit `88f662e`).
> **O contrato já foi publicado e o Antigravity já construiu telas sobre ele:** só pode **ganhar** campos, nunca perder ou mudar de nome.

---

## 1. Objetivo

Permitir que a Administradora publique na vitrine os cães **disponíveis**, que visitantes sem login vejam só os campos públicos, e que **o animal saia da vitrine sozinho** ao deixar de estar disponível (RN17).

## 2. Fora do escopo

- **Telas:** `/adote`, `/adote/:slug` e o controle na `AbaDados` já foram feitos pelo Antigravity sobre o contrato.
- **`og_controller.py`:** é do Antigravity (tarefa B5).
- **Isolamento sanitário:** a vitrine ainda não o considera; o critério entra no CP-05.

### Decisões tomadas na implementação (aceitas pelo Claude Code)
- As rotas públicas da vitrine exigem a flag `vitrine` (`FEATURE_VITRINE=true`). Desligada, respondem o mesmo 404 sem cache.
- Três colisões seguidas de slug → `409`. Animal adotado ou em óbito → `422` (RN05).
- O `PATCH` responde `{sucesso, mensagem, animal}`, que é o formato que o front lê.
- `pagina` aceita só dígitos (`0001` e vazio → `400`).
- Cache de CDN: lista com 120 s mais 60 s de *stale*; detalhe com 60 s mais 60 s. Assim a RN17 vale também na CDN em poucos minutos.

---

## 3. Requisitos

| ID | Requisito | Critério de aceite (teste) |
| :-- | :--- | :--- |
| **REQ-21** | Migração `0004` **aditiva e reversível** em `animals`, com quatro colunas novas e um índice:<br>• `is_publicado BOOLEAN NOT NULL DEFAULT false`;<br>• `slug_publico VARCHAR(40) NULL UNIQUE`;<br>• `descricao_publica TEXT NULL`;<br>• `pausar_candidaturas BOOLEAN NOT NULL DEFAULT false`;<br>• índice `ix_animals_vitrine (is_deleted, is_publicado, status_operacional, created_at)`.<br>O `server_default` garante as linhas antigas. Nenhuma tabela nova, então não há RLS novo. | `test_cp02_vitrine.py::test_migracao_0004_*`: upgrade → downgrade → upgrade em subprocesso; as colunas do modelo são iguais às da migração. |
| **REQ-22** | **RN17, garantida pelo modelo.** Quando `status_operacional` deixa de ser `disponível` ou `is_deleted` vira `True`, o `is_publicado` vira `False` **na mesma transação**, qualquer que seja a rota (`PATCH status`, adoção, exclusão lógica, edição). O `slug_publico` é mantido: se o animal voltar a ficar disponível e for republicado, o link é o mesmo. | `test_rn17_sai_da_vitrine_*`: um teste para cada caminho (mudança de status, adoção, óbito, exclusão lógica) e um teste direto no modelo. |
| **REQ-23** | `CHECK (NOT is_publicado OR (status_operacional = 'disponível' AND NOT is_deleted AND slug_publico IS NOT NULL))`: o banco recusa um animal publicado fora de `disponível`, excluído ou sem slug, inclusive por SQL direto (ampliado pelo parecer do gatekeeper; a `0004` ainda não foi aplicada em nenhum ambiente). | `test_check_publicado_so_disponivel` (IntegrityError). |
| **REQ-24** | `PATCH /api/animais/<id>/vitrine`, **só Administradora**. Corpo: `{ publicar: bool, descricao_publica?: str\|null (≤ 600), pausar_candidaturas?: bool }`.<br>• `publicar=true` fora de `disponível` → `422`, com `mensagem`.<br>• Na **primeira** publicação gera `slug_publico` = nome normalizado (minúsculas, sem acento, só `a-z0-9-`, até 24 caracteres) + `-` + 6 caracteres aleatórios de `secrets`. O slug nunca contém o `id`.<br>• Responde `200 { animal: <to_dict> }`.<br>• Grava `AuditLog` só com o id e o que mudou, sem o texto da descrição. | `test_patch_vitrine_*`: Voluntária → 403; sem login → 401; status errado → 422; formato do slug; descrição com mais de 600 → 400; auditoria. |
| **REQ-25** | `Animal.to_dict()` passa a incluir `is_publicado`, `slug_publico`, `descricao_publica` e `pausar_candidaturas` (`CamposVitrineDaFicha`). | Teste de contrato. |
| **REQ-26** | `Animal.to_public_dict()` passa a ser **exatamente** `AnimalPublico`: os campos de hoje mais `slug` (de `slug_publico`), `descricao_publica` e `candidaturas_pausadas` (de `pausar_candidaturas`). O `ALLOWLIST_APROVADA` do canário é atualizado no mesmo diff. | `test_canary_anti_leak.py` com as chaves iguais a `AnimalPublico`. |
| **REQ-27** | `GET /api/public/animais?pagina=N`:<br>• 12 por página, mais recentes primeiro;<br>• só `is_publicado AND status='disponível' AND NOT is_deleted`;<br>• `pagina` vai de 1 a 500 (fora disso, ou não numérica, → `400`);<br>• resposta no formato `PaginaVitrine`, com `@cache_publico(120, 60)` (detalhe: `60, 60`; janelas curtas para a RN17 valer também na CDN);<br>• uma consulta para a página e uma para o total, sem N+1. | `test_vitrine_lista_*`: paginação, filtro, ordem e cabeçalhos de cache. |
| **REQ-28** | `GET /api/public/animais/<slug>`:<br>• `200 { animal }` se publicado e disponível;<br>• `404` **idêntico** (corpo e cabeçalhos) para slug inexistente, despublicado ou fora de disponível;<br>• slug fora do formato `^[a-z0-9-]{3,40}$` → o mesmo `404`, sem ir ao banco;<br>• o `404` não pode ficar em cache. | `test_vitrine_detalhe_*`. |
| **REQ-29** | **Superfície Open Graph.**<br>• `is_public_request()` passa a aceitar também o blueprint `og` com caminho canônico `/adote/<slug>` (sem `..`, sem `//`). Com isso não há sessão, cookie nem `Vary: Cookie`.<br>• Contrato para o Antigravity (B5): blueprint `og`, endpoint `og.preview_animal`, rota `GET /adote/<slug>`, que usa `Animal.buscar_publicado(slug)`.<br>• `Animal.buscar_publicado(slug)` devolve o animal ou `None`, com os mesmos critérios da REQ-28. | `test_is_public_request_og_*` (com regra simulada) e `test_buscar_publicado`. |
| **REQ-30** | **`vercel.json`.**<br>• Rewrite condicional por `User-Agent` (`has`, regex sem distinção de maiúsculas para `whatsapp\|facebookexternalhit\|facebot\|twitterbot\|telegrambot\|linkedinbot\|slackbot\|discordbot`) de `/adote/:slug` para `/api/index`, **antes** do rewrite da SPA.<br>• Visitantes humanos continuam recebendo `index.html` da CDN. | `test_vercel_json_*`: o JSON é válido, a ordem dos rewrites está certa e a regex cobre os bots e não cobre navegadores comuns (testada em Python contra uma lista de User-Agents reais). |
| **REQ-31** | **Canário.**<br>• `CASOS_PUBLICOS_EXPLICITOS` ganha `public.animal_publico` (com o slug de um animal publicado do fixture).<br>• Já fica pronto o caso `og.preview_animal`, usado só quando o endpoint existir.<br>• O fixture publica o animal "Mel" com canários nos campos internos. | `test_rotas_publicas_sem_honeytoken` cobrindo lista e detalhe. |

---

## 4. Ordem de execução pelos agentes

1. **`gapar-db-architect`:** REQ-21, 22, 23, 25 e 26 (modelo, migração, hook RN17, `to_dict`/`to_public_dict`, `buscar_publicado`, `query_vitrine`) e os testes dessas REQs.
2. **`gapar-backend-security`:** REQ-24, 27, 28, 29, 30 e 31 (rotas, `publico.py`, `vercel.json`, canário) e os testes dessas REQs.
3. **`gapar-qa-gatekeeper`:** os 7 Gates e as mutações.
4. **Claude Code:** handoff `docs/handoff/CP02-claude-para-antigravity.md`.
