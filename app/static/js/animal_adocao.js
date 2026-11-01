(() => {
    const area = document.querySelector("#adocao-demo");

    if (!area) {
        return;
    }

    const formulario = document.querySelector("#form-adocao");
    const mensagem = document.querySelector("#adocao-mensagem");
    const registro = document.querySelector("#adocao-registro");
    const conteudo = document.querySelector("#conteudo");

    const statusFinalizados = ["adotado", "óbito"];
    let congelado = statusFinalizados.includes(area.dataset.status);

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

    function bloquearOperacoes() {
        congelado = true;
        conteudo.dataset.congelado = "true";

        ["#painel-saude", "#painel-medicacoes"].forEach(function (seletor) {
            const painel = document.querySelector(seletor);

            painel.querySelectorAll(
                "input, select, textarea, button"
            ).forEach(function (controle) {
                controle.disabled = true;
            });

            if (!painel.querySelector(".aviso-congelado")) {
                const aviso = document.createElement("p");
                aviso.className = "informacao aviso-congelado";
                aviso.textContent =
                    "Ficha somente para consulta. " +
                    "Novos registros e aplicações estão bloqueados.";

                painel.prepend(aviso);
            }
        });
    }

    // Bloqueia também ações de botões que possam ser recriados
    // dinamicamente pelos outros módulos.
    conteudo.addEventListener("click", function (evento) {
        if (!congelado) {
            return;
        }

        const painel = evento.target.closest(
            "#painel-saude, #painel-medicacoes"
        );

        if (painel && evento.target.closest("button")) {
            evento.preventDefault();
            evento.stopImmediatePropagation();
        }
    }, true);

    conteudo.addEventListener("submit", function (evento) {
        if (!congelado) {
            return;
        }

        if (evento.target.closest(
            "#painel-saude, #painel-medicacoes, #painel-adocao"
        )) {
            evento.preventDefault();
            evento.stopImmediatePropagation();
        }
    }, true);

    if (congelado) {
        bloquearOperacoes();
        return;
    }

    if (!formulario) {
        return;
    }

    const nome = document.querySelector("#adotante-nome");
    const telefone = document.querySelector("#adotante-telefone");
    const dataAdocao = document.querySelector("#adocao-data");

    function prepararData() {
        dataAdocao.max = hojeLocal();

        if (!dataAdocao.value) {
            dataAdocao.value = hojeLocal();
        }
    }

    function validarNome() {
        nome.setCustomValidity(
            nome.value.trim() === ""
                ? "Informe o nome do adotante."
                : ""
        );
    }

    function validarTelefone() {
        const valor = telefone.value.trim();
        const numeros = valor.replace(/\D/g, "");
        const caracteresValidos = /^\+?[\d\s().-]+$/.test(valor);

        const tamanhoValido = valor.startsWith("+")
            ? numeros.length >= 8 && numeros.length <= 15
            : numeros.length === 10 || numeros.length === 11;

        telefone.setCustomValidity(
            caracteresValidos && tamanhoValido
                ? ""
                : "Informe um telefone com DDD ou um número internacional com +."
        );
    }

    function mostrarRegistro(dados) {
        const artigo = document.createElement("article");
        artigo.className = "saude-registro";

        const titulo = document.createElement("h3");
        titulo.textContent = "Adoção de exemplo registrada";

        const detalhes = document.createElement("dl");
        detalhes.className = "saude-detalhes";

        const campos = [
            ["Adotante", dados.adotante_nome],
            ["Telefone", dados.adotante_telefone],
            ["Data da adoção", formatarData(dados.data_adocao)],
            ["Termo assinado", dados.termo_assinado ? "Sim" : "Não"],
            ["Observações", dados.observacoes || "Não informadas"]
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
        registro.replaceChildren(artigo);
    }

    nome.addEventListener("input", validarNome);
    telefone.addEventListener("input", validarTelefone);

    formulario.addEventListener("submit", function (evento) {
        evento.preventDefault();

        prepararData();
        validarNome();
        validarTelefone();

        if (!formulario.reportValidity()) {
            return;
        }

        const confirmou = window.confirm(
            "Confirmar esta adoção de exemplo?\n\n" +
            "A ficha ficará somente para consulta nesta página. " +
            "Nenhuma informação será salva no banco."
        );

        if (!confirmou) {
            return;
        }

        const valores = new FormData(formulario);

        const dadosAdocao = {
            animal_id: Number(area.dataset.animalId),
            adotante_nome: valores.get("adotante_nome").trim(),
            adotante_telefone: valores.get("adotante_telefone").trim(),
            data_adocao: valores.get("data_adocao"),
            termo_assinado: valores.has("termo_assinado"),
            observacoes: valores.get("observacoes").trim() || null
        };

        mostrarRegistro(dadosAdocao);

        area.dataset.status = "adotado";

        const situacao = document.querySelector(".ficha-situacao");
        situacao.textContent = "Adotado — demonstração";

        const areaMedicacoes = document.querySelector("#medicacoes-demo");

        if (areaMedicacoes) {
            areaMedicacoes.dataset.status = "adotado";
        }

        bloquearOperacoes();

        formulario.reset();
        formulario.hidden = true;

        mensagem.textContent =
            "Adoção simulada. Esta ficha está somente para consulta. " +
            "Nenhum dado foi salvo; atualizar a página desfaz a demonstração.";

        mensagem.scrollIntoView({ block: "nearest" });
    });

    formulario.addEventListener("reset", function () {
        nome.setCustomValidity("");
        telefone.setCustomValidity("");

        setTimeout(prepararData, 0);
    });

    prepararData();
})();