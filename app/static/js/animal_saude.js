(() => {
    const areaSaude = document.querySelector("#saude-demo");

    if (!areaSaude) {
        return;
    }

    const animalId = Number(areaSaude.dataset.animalId);

    const formVacina = document.querySelector("#form-vacina");
    const formProntuario = document.querySelector("#form-prontuario");

    const nomeVacina = document.querySelector("#vacina-nome");
    const dataAplicacao = document.querySelector("#vacina-data");
    const dataReforco = document.querySelector("#vacina-reforco");
    const dataEvento = document.querySelector("#evento-data");
    const diagnostico = document.querySelector("#evento-diagnostico");

    const mensagemVacina = document.querySelector("#mensagem-vacina");
    const mensagemProntuario = document.querySelector("#mensagem-prontuario");

    const listaVacinas = document.querySelector("#lista-vacinas");
    const listaProntuario = document.querySelector("#lista-prontuario");

    const vacinasVazio = document.querySelector("#vacinas-vazio");
    const prontuarioVazio = document.querySelector("#prontuario-vazio");

    // Estes dados existem apenas enquanto a página estiver aberta.
    const vacinas = [];
    const atendimentos = [];

    function hojeLocal() {
        const agora = new Date();
        const ano = agora.getFullYear();
        const mes = String(agora.getMonth() + 1).padStart(2, "0");
        const dia = String(agora.getDate()).padStart(2, "0");

        return `${ano}-${mes}-${dia}`;
    }

    function prepararDatas() {
        const hoje = hojeLocal();

        dataAplicacao.max = hoje;
        dataEvento.max = hoje;

        if (!dataAplicacao.value) {
            dataAplicacao.value = hoje;
        }

        if (!dataEvento.value) {
            dataEvento.value = hoje;
        }
    }

    function validarTexto(campo) {
        campo.setCustomValidity(
            campo.value.trim() === ""
                ? "Preencha este campo com um texto válido."
                : ""
        );
    }

    function validarReforco() {
        dataReforco.setCustomValidity("");

        if (dataAplicacao.value) {
            dataReforco.min = dataAplicacao.value;
        } else {
            dataReforco.removeAttribute("min");
        }

        if (
            dataReforco.value &&
            dataAplicacao.value &&
            dataReforco.value < dataAplicacao.value
        ) {
            dataReforco.setCustomValidity(
                "O reforço não pode ser anterior à aplicação."
            );
        }
    }

    function textoOpcional(formData, nome) {
        return formData.get(nome).trim() || null;
    }

    function formatarData(valor) {
        if (!valor) {
            return "Não informada";
        }

        const [ano, mes, dia] = valor.split("-");
        return `${dia}/${mes}/${ano}`;
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

    function mostrarVacinas() {
        listaVacinas.replaceChildren();
        vacinasVazio.hidden = vacinas.length > 0;

        [...vacinas]
            .sort(function (a, b) {
                return b.data_aplicacao.localeCompare(a.data_aplicacao);
            })
            .forEach(function (vacina) {
                const registro = criarRegistro(vacina.nome_vacina, [
                    ["Lote", vacina.lote],
                    ["Aplicação", formatarData(vacina.data_aplicacao)],
                    ["Reforço", formatarData(vacina.data_reforco)],
                    ["Observações", vacina.observacoes]
                ]);

                listaVacinas.append(registro);
            });
    }

    function mostrarAtendimentos() {
        listaProntuario.replaceChildren();
        prontuarioVazio.hidden = atendimentos.length > 0;

        [...atendimentos]
            .sort(function (a, b) {
                return b.data_evento.localeCompare(a.data_evento);
            })
            .forEach(function (atendimento) {
                const registro = criarRegistro(atendimento.tipo_evento, [
                    ["Data", formatarData(atendimento.data_evento)],
                    ["Veterinário", atendimento.veterinario_responsavel],
                    ["Clínica", atendimento.clinica],
                    ["Diagnóstico ou avaliação", atendimento.diagnostico],
                    ["Procedimentos", atendimento.procedimentos_realizados]
                ]);

                listaProntuario.append(registro);
            });
    }

    [nomeVacina, diagnostico].forEach(function (campo) {
        campo.addEventListener("input", function () {
            validarTexto(campo);
        });
    });

    dataAplicacao.addEventListener("input", validarReforco);
    dataReforco.addEventListener("input", validarReforco);

    formVacina.addEventListener("input", function () {
        mensagemVacina.textContent = "";
    });

    formProntuario.addEventListener("input", function () {
        mensagemProntuario.textContent = "";
    });

    formVacina.addEventListener("submit", function (evento) {
        evento.preventDefault();

        prepararDatas();
        validarTexto(nomeVacina);
        validarReforco();

        if (!formVacina.reportValidity()) {
            return;
        }

        const dados = new FormData(formVacina);

        vacinas.push({
            animal_id: animalId,
            nome_vacina: dados.get("nome_vacina").trim(),
            lote: textoOpcional(dados, "lote"),
            data_aplicacao: dados.get("data_aplicacao"),
            data_reforco: dados.get("data_reforco") || null,
            observacoes: textoOpcional(dados, "observacoes")
        });

        mostrarVacinas();
        formVacina.reset();

        mensagemVacina.textContent =
            "Vacina adicionada somente à demonstração desta página. " +
            "Nenhum dado foi salvo no banco.";
    });

    formProntuario.addEventListener("submit", function (evento) {
        evento.preventDefault();

        prepararDatas();
        validarTexto(diagnostico);

        if (!formProntuario.reportValidity()) {
            return;
        }

        const dados = new FormData(formProntuario);

        atendimentos.push({
            animal_id: animalId,
            tipo_evento: dados.get("tipo_evento"),
            data_evento: dados.get("data_evento"),
            veterinario_responsavel:
                textoOpcional(dados, "veterinario_responsavel"),
            clinica: textoOpcional(dados, "clinica"),
            diagnostico: dados.get("diagnostico").trim(),
            procedimentos_realizados:
                textoOpcional(dados, "procedimentos_realizados")
        });

        mostrarAtendimentos();
        formProntuario.reset();

        mensagemProntuario.textContent =
            "Atendimento adicionado somente à demonstração desta página. " +
            "Nenhum dado foi salvo no banco.";
    });

    formVacina.addEventListener("reset", function () {
        nomeVacina.setCustomValidity("");
        dataReforco.setCustomValidity("");
        dataReforco.removeAttribute("min");
        mensagemVacina.textContent = "";

        setTimeout(function () {
            prepararDatas();
            validarReforco();
        }, 0);
    });

    formProntuario.addEventListener("reset", function () {
        diagnostico.setCustomValidity("");
        mensagemProntuario.textContent = "";

        setTimeout(prepararDatas, 0);
    });

    prepararDatas();
    validarReforco();
})();