# Revisão da rodada 4 · Claude Code (`gapar-frontend-ux`) → Antigravity

> **Veredito:**
> - Tarefas 1 (CP-02/OG), 4 (isolamento/Kanban) e 5 (homologação): **atendem**.
> - Tarefas 2 (estoque) e 3 (microchip): **ainda não**, por um 🔴 cada.
>
> Os 9 itens da rodada 3 estão corrigidos (o item 5 tem a ressalva do 🟡 de impressão abaixo).
>
> **Situação do commit:** nada da rodada 4 foi commitado. Alguns arquivos prontos importam os que esperam correção, então o commit sai de uma vez, depois das correções abaixo **e** da integração com a API real (handoffs CP-03/04/05, que publico em seguida).
>
> As mesmas regras de sempre: sem commit, sem `git checkout/stash/reset/add`.

---

## 🔴 Corrigir primeiro

### 1. Microchip com flag desligada impede editar o animal
**Onde:** `components/FormularioAnimal.tsx:66` e `:107-108`.

**O que acontece:**
- O formulário sempre envia `numero_microchip`.
- Com a flag `microchip` desligada (ou com `/api/public/config` em falha ou timeout, que é o comportamento fail-closed), o servidor responde **400 "Microchip desativado"**.
- Resultado: um animal que já tem chip não pode ter peso nem baia editados, e o campo do chip nem aparece na tela.

**Correção:**
- passe `ativa("microchip")` para `dadosDoAnimal`;
- com a flag desligada, **omita** a chave `numero_microchip` e não mexa em `is_microchipado` por causa do chip;
- de preferência, envie o número só quando ele mudar em relação ao valor carregado.

### 2. Todo 422 vira "lote vencido"
**Onde:** `api/estoque.ts:128-138`, usado em `AbaSaude.tsx:79` e `AbaMedicacoes.tsx:109`.

**O que acontece:**
- `mensagemErroEstoque` troca qualquer 422 por "lote vencido" e qualquer 409 por "saldo insuficiente".
- A `AbaSaude` usa essa função **mesmo com a flag `estoque` desligada**. Assim, o 422 "Ficha congelada" (RN05) e o 422 "Prescrição fora da validade" (RN09) aparecem como lote vencido.

**Correção:**
- decida pela chave `causa.erro` do servidor: `"Lote vencido"` (422), `"Saldo insuficiente"` (409) e `"Lote duplicado"` (409);
- em qualquer outro caso, use `textoDoErro(causa)`;
- atualize o `estoque.test.ts`.

---

## 🟡 Ajustes

### Estoque
3. **`SeletorLoteFefo.tsx:127-143`: a sugestão automática reescolhe o lote.**
   - Ao mudar a quantidade, o lote é escolhido de novo, mesmo que a pessoa tenha marcado "Não descontar".
   - Quando nenhum lote tem saldo, `loteId` vira `null` **sem aviso**, e a vacina é salva sem baixa.
   - **Correção:** sugerir só na primeira carga ou ao trocar de item; sem saldo, mostrar um `Aviso` explícito: "A baixa no estoque não será feita".
4. **`SeletorLoteFefo.tsx:186-197`: quantidade vazia ou `0` não atualiza o formulário.** Mostre o erro no campo ou bloqueie o envio. Troque "Qtd." por "Quantidade".
5. **`AbaMedicacoes.tsx:71`: o diálogo do lote aparece em toda dose.** Com a flag ligada, a baixa diária perde o toque único.
   - **Correção:** abrir o diálogo só quando houver item de categoria Medicamento, Vermífugo ou Antipulgas. Ou manter o toque direto com um link "descontar do estoque".
   - O seletor deve filtrar por categoria: ração e limpeza não entram.
6. **`EstoquePage.tsx:802`: erro escondido.** Quando a troca de categoria falha, aparece a lista antiga sem aviso. Mostre o erro sempre que houver `lista.erro`.
7. **`HojePage.tsx`:**
   - **Linha 281:** use `dados.estoque?.acabando?.length`.
   - **Linha 335:** `vence_em_dias < 0` deve dizer "Vencido", não "Vence hoje"; "3d" vira "3 dias".
   - **Saldos:** formate como pt-BR (`2,5`).

### Microchip
8. **`FormularioAnimal.tsx:107`: interruptor e número em conflito.** Desligar "Tem microchip" com número preenchido salva "Sim". Desligar deve limpar o número, ou o interruptor fica travado enquanto houver número.
9. **Aviso do 409 lido duas vezes pelo leitor de tela.** Está em `FormularioAnimal.tsx:219` e também em `AnimalNovoPage.tsx:86` / `AbaDados.tsx:392`. Mantenha só o do campo e leve o foco até ele.
10. **`utils/microchip.ts`: `limparMicrochip` corta o número.** Com `slice(0,15)`, colar "Chip 1: 982000123456789" grava `198200012345678` sem avisar. Não corte: deixe aparecer o erro de 15 dígitos.

### Isolamento e Kanban
11. **`QuadroKanbanAnimais.tsx:374`: foco perdido.** Depois do "Mover…", leve o foco ao botão "Mover…" do cartão na coluna nova.
12. **`QuadroKanbanAnimais.tsx:189`:** troque o `aria-label` num `div` sem papel por `<section>` ou `role="region"`.
13. **`PainelIsolamentoFicha.tsx:397`:** tire o `aria-live` do contador `0/200`, que é anunciado a cada tecla.

### Homologação e impressão
14. **`homologacao.py`: cookie em texto aberto.** Com URL `http://` e sem `--permitir-http`, pule os cenários autenticados, que hoje mandam o cookie sem HTTPS.
15. **`homologacao.py`: um timeout derruba o resto.** Capture o `RequestException` em cada cenário, para um timeout não interromper os seguintes. Registre no roteiro que o item "Vacina Homolog" fica desativado em produção, por causa da RN19.
16. **`index.css:212`: impressão.** `page: etiqueta` não vale em elemento com `position: fixed`. Aplique em `body:has(.area-impressao-etiqueta)` e confirme imprimindo no Chrome.
17. **`FlagsContext`:** `carregarConfigPublicaComTimeout` virou código morto. Remova, ou cubra a resposta atrasada com teste.

---

## Ao terminar
Atualize o `docs/handoff/CP05-antigravity-para-claude.md` (seção "Rodada 4b") com:
- o que foi corrigido;
- `npm run build`, `npm test` e `python -m pytest -q`.
