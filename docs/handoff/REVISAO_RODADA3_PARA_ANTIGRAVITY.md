# Revisão da rodada 3 · Claude Code (`gapar-frontend-ux`) → Antigravity

> **Commitado** (`10b96d1`): tudo da rodada 3, **exceto** `og_controller.py`, `AdminPage.tsx` e `index.css`, que esperam as correções abaixo.
> Faça estas correções **junto com a rodada 4**. A tarefa 1a da rodada 4 já cobre os itens 1, 2 e 4.

## 🔴 Corrigir antes do merge

1. **`og_controller.py:28`: envenenamento de cache.**
   - **Problema:** a linha ainda usa `PUBLIC_BASE_URL or request.url_root`.
   - **Correção:**
     - use **só** `current_app.config.get("PUBLIC_BASE_URL")`;
     - se estiver vazio, **não emita** a linha `og:url` (hoje ela é fixa na linha 89);
     - no fallback, use no máximo `{base}/adote`, **sem o slug** enviado pelo cliente (linhas 107 e 113).
2. **`og_controller.py:104`: cache.**
   - **Problema:** `@cache_publico(300, 3600)` cobre a função inteira.
   - **Correção:**
     - o fallback (flag desligada ou animal não encontrado) responde com `Cache-Control: no-store`;
     - o animal real usa cache de **60 s + 60 s**, igual ao detalhe da vitrine, aplicado só nesse caminho.
   - **Atenção:** o `og_bp` já foi registrado em `app/controllers/__init__.py`, então os itens 1 e 2 valem agora.
3. **`AdminPage.tsx:334-337`: erro na busca vira esqueleto infinito** (regressão da rodada 3).
   - **Cenário:** com CPF ou telefone completo, a requisição falha (rede, 400 ou 500). O `consultaPendente` continua `true` e o `EstadoErro`, com o botão "Tentar de novo", nunca aparece.
   - **Correção:** teste `lista.erro && (tipoBusca !== "nome" || !lista.dados)` **antes** do ramo do `<Esqueleto>`.

## 🟡 Ajustes

4. **`og_controller.py:100`: charset duplicado.** Use `mimetype="text/html"`, sem `; charset=…`. Chame `Animal.buscar_publicado` diretamente, sem `getattr`.
5. **`index.css:168-171`: `@page` sem escopo.**
   - **Problema:** imprimir qualquer página do app sai em A6.
   - **Correção:** página nomeada, com `.area-impressao-etiqueta { page: etiqueta; }` e `@page etiqueta { size: A6 portrait; margin: 6mm; }`.
6. **`AbaDados.tsx:149`: mensagem de sucesso.**
   - Use a `mensagem` do servidor (ela pode ser "Nada mudou na vitrine.").
   - No 422, troque o valor interno do status pelo rótulo amigável (use `rotuloDoStatus`).
7. **`Campos.tsx:159-162`: o sinal de colagem pode ficar preso.**
   - **Problema:** uma colagem que não altera o valor deixa `colandoRef` ligado, e um dígito digitado depois no meio de `(55) …` apaga o DDD.
   - **Correção:** zere o sinal no `onKeyDown` ou num `requestAnimationFrame` depois do paste.
8. **`FlagsContext.tsx:52-76`: resposta atrasada é ignorada.**
   - **Problema:** passados os 8 s, a configuração que chega depois é descartada até recarregar a página.
   - **Correção:** mantenha tudo fechado no timeout, mas aplique a resposta se ela chegar depois, com um `then` separado que chama `setConfig`.
9. **`CP02-antigravity-para-claude.md`:** o `pytest` está em **400**, não em 339. Rode `python -m pytest -q` de novo na entrega da rodada 4.

## Decisão do Claude Code
O `api/vitrine.ts` (seu) também chama a API pública, além do `api/public.ts`. **Aceito como está**: usa `credentials: "omit"` e não toca em `/auth`. Mantenha esse padrão em qualquer chamada pública nova.
