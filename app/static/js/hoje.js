(() => {
    const lista = document.querySelector("#hoje-lista");
    const tipo = document.querySelector("#hoje-tipo");
    const situacao = document.querySelector("#hoje-situacao");
    const limpar = document.querySelector("#hoje-limpar");
    const resultados = document.querySelector("#hoje-resultados");
    const mensagem = document.querySelector("#hoje-mensagem");
    const vazio = document.querySelector("#hoje-vazio");

    function dataLocal() {
        const agora = new Date();
        const ano = agora.getFullYear();
        const mes = String(agora.getMonth() + 1).padStart(2, "0");
        const dia = String(agora.getDate()).padStart(2, "0");

        return `${ano}-${mes}-${dia}`;
    }

    const dataReferencia = dataLocal();

    document.querySelector("#data-hoje").textContent =
        new Intl.DateTimeFormat("pt-BR", {
            dateStyle: "full"
        }).format(new Date());

    // Exemplos independentes dos registros das fichas.
    const tarefas = [
        {
            id: 1,
            animal: "Rex",
            animalId: 1,
            tipo: "medicacao",
            nome: "Medicamento de exemplo A",
            dosagem: "Dosagem fictícia",
            horario: "08:00",
            concluida: false
        },
        {
            id: 2,
            animal: "Luna",
            animalId: 2,
            tipo: "medicacao",
            nome: "Medicamento de exemplo B",
            dosagem: "Dosagem fictícia",
            horario: "14:00",
            concluida: false
        },
        {
            id: 3,
            animal: "Rex",
            animalId: 1,
            tipo: "medicacao",
            nome: "Medicamento de exemplo A",
            dosagem: "Dosagem fictícia",
            horario: "20:00",
            concluida: false
        },
        {
            id: 4,
            animal: "Luna",
            animalId: 2,
            tipo: "vacina",
            nome: "Vacina de exemplo",
            horario: null,
            concluida: false
        }
    ];

    function criarTexto(tag, texto, classe) {
        const elemento = document.createElement(tag);
        elemento.textContent = texto;

        if (classe) {
            elemento.className = classe;
        }

        return elemento;
    }

    function registrarAplicacao(tarefa) {
        if (tarefa.concluida || tarefa.tipo !== "medicacao") {
            return;
        }

        if (dataLocal() !== dataReferencia) {
            mensagem.textContent =
                "O dia mudou. Atualize a página para carregar os exemplos de hoje.";
            return;
        }

        const confirmou = window.confirm(
            `Confirma que a dose de ${tarefa.animal}, ` +
            `prevista para ${tarefa.horario}, já foi aplicada?\n\n` +
            "Esta ação é apenas uma demonstração."
        );

        if (!confirmou) {
            return;
        }

        if (dataLocal() !== dataReferencia) {
            mensagem.textContent =
                "O dia mudou durante a confirmação. Atualize a página.";
            return;
        }

        tarefa.concluida = true;
        tarefa.horarioRegistrado = new Intl.DateTimeFormat("pt-BR", {
            hour: "2-digit",
            minute: "2-digit",
            hour12: false
        }).format(new Date());

        renderizar();

        mensagem.textContent =
            `Aplicação de ${tarefa.animal} registrada na demonstração. ` +
            "Nenhum dado foi salvo no banco.";

        // O botão anterior foi recriado ou removido pelo filtro.
        const linkFicha = document.querySelector(
            `[data-tarefa-id="${tarefa.id}"] .hoje-link-ficha`
        );

        if (linkFicha) {
            linkFicha.focus();
        } else {
            situacao.focus();
        }
    }

    function atualizarContadores() {
        document.querySelector("#total-medicacoes").textContent =
            tarefas.filter(function (tarefa) {
                return tarefa.tipo === "medicacao" && !tarefa.concluida;
            }).length;

        document.querySelector("#total-vacinas").textContent =
            tarefas.filter(function (tarefa) {
                return tarefa.tipo === "vacina" && !tarefa.concluida;
            }).length;

        document.querySelector("#total-aplicadas").textContent =
            tarefas.filter(function (tarefa) {
                return tarefa.tipo === "medicacao" && tarefa.concluida;
            }).length;
    }

    function renderizar() {
        lista.replaceChildren();
        atualizarContadores();

        const filtradas = tarefas.filter(function (tarefa) {
            const correspondeTipo =
                tipo.value === "" || tarefa.tipo === tipo.value;

            const correspondeSituacao =
                situacao.value === "" ||
                (situacao.value === "concluida" && tarefa.concluida) ||
                (situacao.value === "pendente" && !tarefa.concluida);

            return correspondeTipo && correspondeSituacao;
        });

        resultados.textContent = filtradas.length === 1
            ? "1 tarefa encontrada."
            : `${filtradas.length} tarefas encontradas.`;

        vazio.hidden = filtradas.length > 0;

        filtradas.forEach(function (tarefa) {
            const card = document.createElement("article");
            card.className = "hoje-tarefa";
            card.dataset.tarefaId = tarefa.id;

            const cabecalho = document.createElement("div");
            cabecalho.className = "hoje-tarefa__cabecalho";

            cabecalho.append(
                criarTexto(
                    "span",
                    tarefa.tipo === "medicacao" ? "Medicação" : "Vacinação",
                    "hoje-tipo"
                ),
                criarTexto(
                    "span",
                    tarefa.concluida ? "Concluída" : "Pendente",
                    "hoje-status"
                )
            );

            card.append(
                cabecalho,
                criarTexto("h3", tarefa.animal),
                criarTexto("p", tarefa.nome),
                criarTexto(
                    "p",
                    tarefa.horario
                        ? `Horário previsto: ${tarefa.horario}`
                        : "Prevista para hoje — horário não informado"
                )
            );

            if (tarefa.dosagem) {
                card.append(
                    criarTexto("p", `Dosagem: ${tarefa.dosagem}`)
                );
            }

            if (tarefa.concluida) {
                card.append(
                    criarTexto(
                        "p",
                        `Registrada às ${tarefa.horarioRegistrado}.`
                    )
                );
            }

            const acoes = document.createElement("div");
            acoes.className = "form-acoes";

            const link = document.createElement("a");
            link.className =
                "botao botao--secundario hoje-link-ficha";
            link.href = `/animais/${tarefa.animalId}`;
            link.textContent = "Ver ficha";
            link.setAttribute(
                "aria-label",
                `Ver ficha de ${tarefa.animal}`
            );

            acoes.append(link);

            if (tarefa.tipo === "medicacao") {
                const botao = document.createElement("button");
                botao.type = "button";
                botao.className = "botao botao--principal";
                botao.disabled = tarefa.concluida;

                botao.textContent = tarefa.concluida
                    ? "Aplicação registrada"
                    : "Registrar aplicação";

                botao.setAttribute(
                    "aria-label",
                    `${botao.textContent}: ${tarefa.animal}, ${tarefa.horario}`
                );

                botao.addEventListener("click", function () {
                    registrarAplicacao(tarefa);
                });

                acoes.append(botao);
            } else {
                card.append(
                    criarTexto(
                        "p",
                        "A confirmação vinculada ao agendamento " +
                        "ainda não está disponível nesta demonstração.",
                        "ajuda"
                    )
                );
            }

            card.append(acoes);
            lista.append(card);
        });
    }

    tipo.addEventListener("change", renderizar);
    situacao.addEventListener("change", renderizar);

    limpar.addEventListener("click", function () {
        tipo.value = "";
        situacao.value = "";
        renderizar();
        tipo.focus();
    });

    renderizar();
})();