(() => {
    const lista = document.querySelector("#hoje-lista");
    const tipo = document.querySelector("#hoje-tipo");
    const situacao = document.querySelector("#hoje-situacao");
    const limpar = document.querySelector("#hoje-limpar");
    const resultados = document.querySelector("#hoje-resultados");
    const mensagem = document.querySelector("#hoje-mensagem");
    const vazio = document.querySelector("#hoje-vazio");

    let tarefas = [];

    document.querySelector("#data-hoje").textContent =
        new Intl.DateTimeFormat("pt-BR", {
            dateStyle: "full"
        }).format(new Date());

    function criarTexto(tag, texto, classe) {
        const elemento = document.createElement(tag);
        elemento.textContent = texto;
        if (classe) elemento.className = classe;
        return elemento;
    }

    async function carregarPainelHoje() {
        try {
            const resp = await fetch("/api/hoje");
            if (!resp.ok) return;

            const dados = await resp.json();
            tarefas = [];

            // Adiciona medicações
            (dados.medicacoes_hoje || []).forEach(function (m, idx) {
                tarefas.push({
                    id: `med-${m.prescricao_id}-${m.horario_previsto}`,
                    prescricao_id: m.prescricao_id,
                    animal: m.animal_nome,
                    animalId: m.animal_id,
                    tipo: "medicacao",
                    nome: `${m.medicamento} (${m.dosagem})`,
                    baia: m.localizacao_baia,
                    horario: m.horario_previsto,
                    concluida: m.aplicado,
                    horario_aplicado: m.horario_aplicado
                });
            });

            // Adiciona vacinas
            (dados.vacinas_hoje || []).forEach(function (v, idx) {
                tarefas.push({
                    id: `vac-${v.vacina_id}`,
                    vacina_id: v.vacina_id,
                    animal: v.animal_nome,
                    animalId: v.animal_id,
                    tipo: "vacina",
                    nome: `Vacina: ${v.nome_vacina}`,
                    baia: v.localizacao_baia,
                    horario: "Dia de hoje",
                    concluida: false
                });
            });

            atualizarLista();
        } catch (e) {
            console.error("Erro ao carregar tarefas do dia:", e);
        }
    }

    async function registrarAplicacao(tarefa, botao) {
        if (tarefa.concluida || tarefa.tipo !== "medicacao") {
            return;
        }

        const confirmou = window.confirm(
            `Confirma que a dose de ${tarefa.animal} (${tarefa.nome}), ` +
            `prevista para as ${tarefa.horario}, foi administrada?`
        );

        if (!confirmou) {
            return;
        }

        if (botao) {
            botao.disabled = true;
            botao.textContent = "Gravando...";
        }

        try {
            const resp = await fetch(`/api/saude/medicacao/baixa/${tarefa.prescricao_id}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ horario_previsto: tarefa.horario })
            });

            const resultado = await resp.json();

            if (resp.ok && resultado.sucesso) {
                tarefa.concluida = true;
                mensagem.className = "form-mensagem form-mensagem--sucesso";
                mensagem.textContent = `Dose das ${tarefa.horario} aplicada com sucesso para ${tarefa.animal}!`;
                atualizarLista();
            } else {
                if (botao) {
                    botao.disabled = false;
                    botao.textContent = "Dar baixa";
                }
                mensagem.className = "form-mensagem form-mensagem--erro";
                mensagem.textContent = resultado.mensagem || "Não foi possível registrar a baixa.";
            }
        } catch (e) {
            if (botao) {
                botao.disabled = false;
                botao.textContent = "Dar baixa";
            }
            mensagem.className = "form-mensagem form-mensagem--erro";
            mensagem.textContent = "Erro na comunicação com o servidor.";
        }
    }

    function criarCard(tarefa) {
        const item = document.createElement("li");
        item.className = "hoje-card";

        const tipoTexto = tarefa.tipo === "medicacao" ? "Medicação" : "Vacina";
        item.append(criarTexto("span", tipoTexto, "hoje-card__tipo"));

        const cabecalho = document.createElement("div");
        cabecalho.className = "hoje-card__cabecalho";

        const link = document.createElement("a");
        link.href = `/animais/${tarefa.animalId}`;
        link.textContent = tarefa.animal;
        cabecalho.append(link);

        if (tarefa.baia) {
            cabecalho.append(criarTexto("span", ` · ${tarefa.baia}`));
        }

        cabecalho.append(criarTexto("span", ` — ${tarefa.nome}`));
        item.append(cabecalho);

        if (tarefa.horario) {
            item.append(criarTexto("p", `Horário: ${tarefa.horario}`, "hoje-card__horario"));
        }

        const rodape = document.createElement("div");
        rodape.className = "hoje-card__rodape";

        if (tarefa.concluida) {
            const statusConcluido = criarTexto("span", "✓ Dose administrada hoje", "hoje-card__concluida");
            statusConcluido.style.color = "var(--cor-sucesso, #155724)";
            statusConcluido.style.fontWeight = "bold";
            rodape.append(statusConcluido);
        } else if (tarefa.tipo === "medicacao") {
            const botao = document.createElement("button");
            botao.type = "button";
            botao.className = "botao botao--principal";
            botao.textContent = "Dar baixa na dose";
            botao.addEventListener("click", function () {
                registrarAplicacao(tarefa, botao);
            });
            rodape.append(botao);
        } else {
            const linkVacina = document.createElement("a");
            linkVacina.href = `/animais/${tarefa.animalId}`;
            linkVacina.className = "botao botao--secundario";
            linkVacina.textContent = "Ver cartão de vacinas";
            rodape.append(linkVacina);
        }

        item.append(rodape);
        return item;
    }

    function filtrarTarefas() {
        return tarefas.filter(function (tarefa) {
            const filtroTipo = tipo.value;
            const filtroSituacao = situacao.value;

            const correspondeTipo = filtroTipo === "" || tarefa.tipo === filtroTipo;
            const correspondeSituacao =
                filtroSituacao === "" ||
                (filtroSituacao === "pendentes" && !tarefa.concluida) ||
                (filtroSituacao === "concluidas" && tarefa.concluida);

            return correspondeTipo && correspondeSituacao;
        });
    }

    function atualizarLista() {
        const filtradas = filtrarTarefas();
        lista.replaceChildren();

        filtradas.forEach(function (tarefa) {
            lista.append(criarCard(tarefa));
        });

        vazio.hidden = filtradas.length !== 0;

        if (filtradas.length === 0) {
            resultados.textContent = "Nenhuma tarefa encontrada.";
        } else if (filtradas.length === 1) {
            resultados.textContent = "1 tarefa listada.";
        } else {
            resultados.textContent = `${filtradas.length} tarefas listadas.`;
        }
    }

    if (tipo) tipo.addEventListener("change", atualizarLista);
    if (situacao) situacao.addEventListener("change", atualizarLista);
    if (limpar) {
        limpar.addEventListener("click", function () {
            if (tipo) tipo.value = "";
            if (situacao) situacao.value = "";
            atualizarLista();
        });
    }

    carregarPainelHoje();
})();
