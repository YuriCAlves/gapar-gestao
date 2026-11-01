(() => {
    const area = document.querySelector("#medicacoes-demo");

    if (!area) {
        return;
    }

    const statusPermitidos = [
        "em acolhimento",
        "em tratamento",
        "lar temporário"
    ];

    const permitePrescricao = statusPermitidos.includes(
        area.dataset.status
    );

    const formulario = document.querySelector("#form-prescricao");
    const listaPrescricoes = document.querySelector("#lista-prescricoes");
    const listaAplicacoes = document.querySelector("#lista-aplicacoes");
    const prescricoesVazio = document.querySelector("#prescricoes-vazio");
    const aplicacoesVazio = document.querySelector("#aplicacoes-vazio");
    const mensagemAplicacao = document.querySelector("#mensagem-aplicacao");

    const prescricoes = [];
    const aplicacoes = [];
    let proximoId = 1;

    function dataLocal(data = new Date()) {
        const ano = data.getFullYear();
        const mes = String(data.getMonth() + 1).padStart(2, "0");
        const dia = String(data.getDate()).padStart(2, "0");

        return `${ano}-${mes}-${dia}`;
    }

    function horaLocal(data = new Date()) {
        const hora = String(data.getHours()).padStart(2, "0");
        const minuto = String(data.getMinutes()).padStart(2, "0");

        return `${hora}:${minuto}`;
    }

    function formatarData(valor) {
        const [ano, mes, dia] = valor.split("-");
        return `${dia}/${mes}/${ano}`;
    }

    function situacaoPrescricao(prescricao) {
        const hoje = dataLocal();

        if (hoje < prescricao.data_inicio) {
            return "Programada";
        }

        if (hoje > prescricao.data_fim) {
            return "Encerrada";
        }

        return "Ativa";
    }

    function doseRegistrada(prescricaoId, horario) {
        return aplicacoes.some(function (aplicacao) {
            return (
                aplicacao.prescription_id === prescricaoId &&
                aplicacao.horario_previsto === horario &&
                aplicacao.data_aplicacao === dataLocal()
            );
        });
    }

    function criarRegistro(titulo, campos) {
        const artigo = document.createElement("article");
        artigo.className = "saude-registro";

        const cabecalho = document.createElement("h4");
        cabecalho.textContent = titulo;

        const detalhes = document.createElement("dl");
        detalhes.className = "saude-detalhes";

        campos.forEach(function ([rotulo, valor]) {
            const grupo = document.createElement("div");
            const termo = document.createElement("dt");
            const descricao = document.createElement("dd");

            termo.textContent = rotulo;
            descricao.textContent = valor || "Não informado";

            grupo.append(termo, descricao);
            detalhes.append(grupo);
        });

        artigo.append(cabecalho, detalhes);
        return artigo;
    }

    function mostrarAplicacoes() {
        listaAplicacoes.replaceChildren();

        const aplicacoesHoje = aplicacoes.filter(function (aplicacao) {
            return aplicacao.data_aplicacao === dataLocal();
        });

        aplicacoesVazio.hidden = aplicacoesHoje.length > 0;

        [...aplicacoesHoje].reverse().forEach(function (aplicacao) {
            const prescricao = prescricoes.find(function (item) {
                return item.id === aplicacao.prescription_id;
            });

            listaAplicacoes.append(
                criarRegistro(prescricao.nome_medicamento, [
                    ["Data", formatarData(aplicacao.data_aplicacao)],
                    ["Horário previsto", aplicacao.horario_previsto],
                    ["Horário registrado", aplicacao.horario_aplicado]
                ])
            );
        });
    }

    function registrarAplicacao(prescricao, horario) {
        if (
            !permitePrescricao ||
            situacaoPrescricao(prescricao) !== "Ativa"
        ) {
            mensagemAplicacao.textContent =
                "Esta prescrição não permite aplicação nesta demonstração.";
            mostrarPrescricoes();
            return;
        }

        if (doseRegistrada(prescricao.id, horario)) {
            mensagemAplicacao.textContent =
                "Essa dose já foi registrada hoje.";
            return;
        }

        const confirmou = window.confirm(
            `Confirma que a dose de ${prescricao.nome_medicamento}, ` +
            `prevista para ${horario}, já foi aplicada?\n\n` +
            "Este registro é apenas uma demonstração."
        );

        if (!confirmou) {
            return;
        }

        const agora = new Date();

        if (
            situacaoPrescricao(prescricao) !== "Ativa" ||
            doseRegistrada(prescricao.id, horario)
        ) {
            mostrarPrescricoes();
            return;
        }

        aplicacoes.push({
            prescription_id: prescricao.id,
            data_aplicacao: dataLocal(agora),
            horario_previsto: horario,
            horario_aplicado: horaLocal(agora),
            observacoes: null
        });

        mostrarPrescricoes();
        mostrarAplicacoes();

        mensagemAplicacao.textContent =
            "Aplicação registrada somente nesta página. " +
            "Nenhum dado foi salvo no banco.";
    }

    function mostrarPrescricoes() {
        listaPrescricoes.replaceChildren();
        prescricoesVazio.hidden = prescricoes.length > 0;

        prescricoes.forEach(function (prescricao) {
            const situacao = situacaoPrescricao(prescricao);

            const artigo = criarRegistro(
                prescricao.nome_medicamento,
                [
                    ["Dosagem prescrita", prescricao.dosagem],
                    ["Horários", prescricao.horarios],
                    ["Início", formatarData(prescricao.data_inicio)],
                    ["Fim", formatarData(prescricao.data_fim)],
                    ["Situação", situacao],
                    ["Instruções", prescricao.instrucoes]
                ]
            );

            if (situacao === "Ativa" && permitePrescricao) {
                const tituloDoses = document.createElement("h5");
                tituloDoses.textContent =
                    `Doses de hoje — ${formatarData(dataLocal())}`;

                const acoes = document.createElement("div");
                acoes.className = "medicacao-doses";

                prescricao.horarios.split(", ").forEach(function (horario) {
                    const registrada = doseRegistrada(
                        prescricao.id,
                        horario
                    );

                    const botao = document.createElement("button");
                    botao.type = "button";
                    botao.className = "botao botao--secundario";
                    botao.disabled = registrada;

                    botao.textContent = registrada
                        ? `${horario} — registrada`
                        : `Registrar aplicação — ${horario}`;

                    botao.setAttribute(
                        "aria-label",
                        `${botao.textContent}: ${prescricao.nome_medicamento}`
                    );

                    botao.addEventListener("click", function () {
                        registrarAplicacao(prescricao, horario);
                    });

                    acoes.append(botao);
                });

                artigo.append(tituloDoses, acoes);
            }

            listaPrescricoes.append(artigo);
        });
    }

    if (!formulario || !permitePrescricao) {
        return;
    }

    const nome = document.querySelector("#medicamento-nome");
    const dose = document.querySelector("#medicamento-dose");
    const horarios = document.querySelector("#medicamento-horarios");
    const inicio = document.querySelector("#medicamento-inicio");
    const fim = document.querySelector("#medicamento-fim");
    const mensagemPrescricao = document.querySelector("#mensagem-prescricao");

    function validarTexto(campo) {
        campo.setCustomValidity(
            campo.value.trim() === ""
                ? "Preencha este campo com um texto válido."
                : ""
        );
    }

    function validarHorarios() {
        horarios.setCustomValidity("");

        const valores = horarios.value
            .split(",")
            .map(function (horario) {
                return horario.trim();
            });

        const formatoValido = valores.every(function (horario) {
            return /^([01]\d|2[0-3]):[0-5]\d$/.test(horario);
        });

        if (!formatoValido) {
            horarios.setCustomValidity(
                "Use horários como 08:00, 20:00, entre 00:00 e 23:59."
            );
        } else if (new Set(valores).size !== valores.length) {
            horarios.setCustomValidity(
                "Não repita o mesmo horário na prescrição."
            );
        }

        return valores;
    }

    function validarPeriodo() {
        fim.setCustomValidity("");

        if (inicio.value) {
            fim.min = inicio.value;
        } else {
            fim.removeAttribute("min");
        }

        if (inicio.value && fim.value && fim.value < inicio.value) {
            fim.setCustomValidity(
                "A data final não pode ser anterior à inicial."
            );
        }
    }

    [nome, dose].forEach(function (campo) {
        campo.addEventListener("input", function () {
            validarTexto(campo);
        });
    });

    horarios.addEventListener("input", validarHorarios);
    inicio.addEventListener("input", validarPeriodo);
    fim.addEventListener("input", validarPeriodo);

    formulario.addEventListener("input", function () {
        mensagemPrescricao.textContent = "";
    });

    formulario.addEventListener("submit", function (evento) {
        evento.preventDefault();

        validarTexto(nome);
        validarTexto(dose);
        const horariosValidados = validarHorarios();
        validarPeriodo();

        if (!formulario.reportValidity()) {
            return;
        }

        const dados = new FormData(formulario);

        prescricoes.push({
            id: proximoId++,
            animal_id: Number(area.dataset.animalId),
            nome_medicamento: dados.get("nome_medicamento").trim(),
            dosagem: dados.get("dosagem").trim(),
            horarios: horariosValidados.sort().join(", "),
            data_inicio: dados.get("data_inicio"),
            data_fim: dados.get("data_fim"),
            instrucoes: dados.get("instrucoes").trim() || null
        });

        mostrarPrescricoes();
        formulario.reset();

        mensagemPrescricao.textContent =
            "Prescrição adicionada somente à demonstração. " +
            "Nenhum dado foi salvo ou enviado ao Google Agenda.";
    });

    formulario.addEventListener("reset", function () {
        [nome, dose, horarios, fim].forEach(function (campo) {
            campo.setCustomValidity("");
        });

        fim.removeAttribute("min");
        mensagemPrescricao.textContent = "";

        setTimeout(function () {
            inicio.value = dataLocal();
            validarPeriodo();
        }, 0);
    });

    inicio.value = dataLocal();
    validarPeriodo();
})();