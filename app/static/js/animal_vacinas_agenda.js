(() => {
    const formulario = document.querySelector("#form-agendamento-vacina");

    if (!formulario) {
        return;
    }

    const conteudo = document.querySelector("#conteudo");
    const areaSaude = document.querySelector("#saude-demo");
    const nome = document.querySelector("#agenda-vacina-nome");
    const dataPrevista = document.querySelector("#agenda-vacina-data");
    const mensagem = document.querySelector("#agenda-vacina-mensagem");
    const lista = document.querySelector("#lista-agendamentos-vacina");
    const vazio = document.querySelector("#agenda-vacina-vazio");

    // Registros temporários: não são enviados ao servidor.
    const agendamentos = [];

    function hojeLocal() {
        const agora = new Date();
        const ano = agora.getFullYear();
        const mes = String(agora.getMonth() + 1).padStart(2, "0");
        const dia = String(agora.getDate()).padStart(2, "0");

        return `${ano}-${mes}-${dia}`;
    }

    function formatarData(valor) {
        const [ano, mes, dia] = valor.split("-");
        return `${dia}/${mes}/${ano}`;
    }

    function prepararData() {
        dataPrevista.min = hojeLocal();

        if (!dataPrevista.value) {
            dataPrevista.value = hojeLocal();
        }
    }

    function validarNome() {
        nome.setCustomValidity(
            nome.value.trim() === ""
                ? "Informe o nome da vacina."
                : ""
        );
    }

    function normalizarTexto(texto) {
        return texto
            .trim()
            .toLocaleLowerCase("pt-BR")
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "");
    }

    function mostrarAgendamentos() {
        lista.replaceChildren();
        vazio.hidden = agendamentos.length > 0;

        [...agendamentos]
            .sort(function (a, b) {
                return a.data_prevista.localeCompare(b.data_prevista);
            })
            .forEach(function (agendamento) {
                const artigo = document.createElement("article");
                artigo.className = "saude-registro";

                const titulo = document.createElement("h4");
                titulo.textContent = agendamento.nome_vacina;

                const detalhes = document.createElement("dl");
                detalhes.className = "saude-detalhes";

                const campos = [
                    ["Data prevista", formatarData(agendamento.data_prevista)],
                    ["Situação", "Agendada — aplicação não confirmada"],
                    ["Observações", agendamento.observacoes || "Não informadas"]
                ];

                campos.forEach(function ([rotulo, valor]) {
                    const grupo = document.createElement("div");
                    const termo = document.createElement("dt");
                    const descricao = document.createElement("dd");

                    termo.textContent = rotulo;
                    descricao.textContent = valor;

                    grupo.append(termo, descricao);
                    detalhes.append(grupo);
                });

                artigo.append(titulo, detalhes);
                lista.append(artigo);
            });
    }

    nome.addEventListener("input", validarNome);

    formulario.addEventListener("input", function () {
        mensagem.textContent = "";
    });

    formulario.addEventListener("submit", function (evento) {
        evento.preventDefault();

        if (conteudo.dataset.congelado === "true") {
            mensagem.textContent =
                "Esta ficha está somente para consulta.";
            return;
        }

        prepararData();
        validarNome();

        if (!formulario.reportValidity()) {
            return;
        }

        const dados = new FormData(formulario);
        const nomeVacina = dados.get("nome_vacina").trim();
        const data = dados.get("data_prevista");

        const duplicado = agendamentos.some(function (agendamento) {
            return (
                normalizarTexto(agendamento.nome_vacina) ===
                    normalizarTexto(nomeVacina) &&
                agendamento.data_prevista === data
            );
        });

        if (duplicado) {
            mensagem.textContent =
                "Já existe um agendamento dessa vacina para essa data.";
            return;
        }

        agendamentos.push({
            animal_id: Number(areaSaude.dataset.animalId),
            nome_vacina: nomeVacina,
            data_prevista: data,
            situacao: "agendada",
            observacoes: dados.get("observacoes").trim() || null
        });

        mostrarAgendamentos();
        formulario.reset();

        mensagem.textContent =
            "Vacinação agendada somente nesta demonstração. " +
            "Nenhum dado foi salvo e nenhum lembrete foi enviado.";
    });

    formulario.addEventListener("reset", function () {
        nome.setCustomValidity("");
        mensagem.textContent = "";

        setTimeout(prepararData, 0);
    });

    prepararData();
})();