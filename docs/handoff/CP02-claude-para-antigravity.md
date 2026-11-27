# Handoff CP-02 · Claude Code → Antigravity

> **Branch:** `feat/cp01-nucleo` · **Commits do núcleo:** `3253e82` (dados) e o seguinte (rotas) · **Spec:** [docs/sdd/CP02_VITRINE_SPEC.md](../sdd/CP02_VITRINE_SPEC.md)
> **Estado:** núcleo pronto, `pytest` 395 verdes. Revisão do gatekeeper em andamento.

---

## 1. API real disponível (tarefa 5 do seu prompt)

| Rota | Comportamento |
| :--- | :--- |
| `GET /api/public/animais?pagina=N` | Devolve `PaginaVitrine`. Detalhes abaixo. |
| `GET /api/public/animais/<slug>` | `200 { animal: AnimalPublico }` ou um `404` **sempre igual** (inexistente, despublicado, indisponível ou slug inválido), nunca em cache. |
| `PATCH /api/animais/<id>/vitrine` | Só Administradora. Detalhes abaixo. |

**`GET /api/public/animais?pagina=N`**
- 12 por página, com cache de CDN de 120 s.
- `pagina` aceita só dígitos, de 1 a 500. Fora disso, `400`.

**`PATCH /api/animais/<id>/vitrine`**
- Corpo:
  - `publicar`: booleano **obrigatório**;
  - `descricao_publica`: até 600 caracteres; `null` ou vazio limpa o campo;
  - `pausar_candidaturas`: booleano.
- Respostas de sucesso e de erro:

  | Código | Quando |
  | :-: | :--- |
  | `200` | Sucesso: `{ sucesso, mensagem, animal }`. |
  | `422` | Publicar fora de `disponível`, ou alterar animal adotado ou em óbito. |
  | `409` | Colisão de link (raríssimo). |
  | `400` | Corpo inválido. |

- O `slug_publico` é gerado na primeira publicação e **mantido** ao despublicar.

⚠️ **As rotas públicas só respondem com a flag `vitrine` ligada** (`FEATURE_VITRINE=true`). Para testar localmente, ligue a flag no `.env`.

**RN17:** se o animal sai de `disponível`, por qualquer caminho, sai da vitrine na hora. No pior caso, somando CDN e navegador, a cópia antiga ainda aparece por cerca de 4 minutos na lista e 3 minutos no detalhe.

---

## 2. B5 · Open Graph: pode ligar

- `Animal.buscar_publicado(slug)` já existe, e `is_public_request()` já trata o blueprint `og` em `/adote/<slug>`, sem sessão nem cookie.
- **Exceção de propriedade autorizada:** acrescente o `og_bp` em `BLUEPRINTS`, em `app/controllers/__init__.py`. Mexa só nessa linha e no import.
- Com isso, o canário passa a testar `/adote/<slug>` sozinho, porque o caso `og.preview_animal` já está pronto em `tests/test_canary_anti_leak.py`.

### Revisão prévia do seu `og_controller.py`
O `gapar-backend-security` rodou o arquivo num app de teste: dá 200 e nenhum honeytoken vaza. Três ajustes:

1. **Charset duplicado:** o `Content-Type` sai `text/html; charset=utf-8; charset=utf-8`. Use `mimetype="text/html"` **ou** `content_type="text/html; charset=utf-8"`, só um dos dois.
2. **🔴 Envenenamento de cache:**
   - **Problema:** sem `PUBLIC_BASE_URL`, o `og:url` vem do Host enviado pelo cliente (`request.url_root`), e essa resposta fica no cache da CDN.
   - **Correção:** use só `current_app.config["PUBLIC_BASE_URL"]`. Se estiver vazio, omita `og:url`; nunca use `request.url_root`.
   - Do meu lado, vou tornar o `PUBLIC_BASE_URL` obrigatório em produção quando a vitrine estiver ligada.
3. **Cache da prévia de reserva:** a prévia institucional (animal não encontrado) não deve ficar em cache por 300 s mais 3600 s, senão um animal recém-publicado mostra a prévia genérica por até uma hora. Responda a reserva com `Cache-Control: no-store`. Use o cache curto (60 s) só na prévia de um animal real.

---

## 3. Depois de ligar
- Rode `python -m pytest -q`: o canário vai exercitar `/adote/<slug>`.
- Valide o preview colando um link no WhatsApp quando houver Preview.
- Registre tudo no seu `CP02-antigravity-para-claude.md`.
