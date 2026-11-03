(() => {
    const area = document.querySelector("#adocao-demo");

    if (!area) {
        return;
    }

    const animalId = Number(area.dataset.animalId);
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
        if (!valor) return "Não informada";
        const [ano, mes, dia] = valor.split("-");
        return `${dia}/${mes}/${ano}`;
    }

    function bloquearOperacoes() {
        congelado = true;
        conteudo.dataset.congelado = "true";

        ["#painel-saude", "#painel-medicacoes"].forEach(function (seletor) {
            const painel = document.querySelector(seletor);
            if (!painel) return;

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
                    "Novos registros e aplicações estão bloqueados para este animal (RN05).";

                painel.prepend(aviso);
            }
        });
    }

    // Bloqueia ações em caso de animal congelado
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

    // Carrega histórico de adoção se já estiver adotado
    async function carregarHistoricoAdocao() {
        try {
            const resp = await fetch(`/api/adocoes/${animalId}`);
            if (resp.ok) {
                const dados = await resp.json();
                if (dados.adocao) {
                    mostrarRegistro(dados.adocao);
                    bloquearOperacoes();
                }
            }
        } catch (e) {
            console.error("Erro ao carregar histórico de adoção:", e);
        }
    }

    if (congelado) {
        bloquearOperacoes();
        carregarHistoricoAdocao();
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
                : "Informe um telefone com DDD ou número com +."
        );
    }

    function mostrarRegistro(dados) {
        const artigo = document.createElement("article");
        artigo.className = "saude-registro";

        const titulo = document.createElement("h3");
        titulo.textContent = "Adoção Formal Registrada";

        const detalhes = document.createElement("dl");
        detalhes.className = "saude-detalhes";

        const campos = [
            ["Adotante", dados.adotante_nome],
            ["Telefone", dados.adotante_telefone],
            ["CPF", dados.adotante_cpf || "Não informado"],
            ["Data da adoção", formatarData(dados.data_adocao)],
            ["Termo assinado", dados.termo_assinado ? "Sim" : "Não"],
            ["Observações", dados.observacoes || "Nenhuma"]
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

    formulario.addEventListener("submit", async function (evento) {
        evento.preventDefault();

        prepararData();
        validarNome();
        validarTelefone();

        if (!formulario.reportValidity()) {
            return;
        }

        const confirmou = window.confirm(
            "Confirmar formalização desta adoção?\n\n" +
            "A ficha do animal será permanentemente congelada para novos cadastros ou procedimentos clínicos (RN05)."
        );

        if (!confirmou) {
            return;
        }

        const valores = new FormData(formulario);

        const payload = {
            adotante_nome: valores.get("adotante_nome").trim(),
            adotante_telefone: valores.get("adotante_telefone").trim(),
            adotante_cpf: valores.get("adotante_cpf") ? valores.get("adotante_cpf").trim() : "",
            data_adocao: valores.get("data_adocao"),
            termo_assinado: valores.has("termo_assinado"),
            termo_fisico_assinado: valores.has("termo_assinado"),
            observacoes: valores.get("observacoes") ? valores.get("observacoes").trim() : ""
        };

        mensagem.className = "form-mensagem";
        mensagem.textContent = "Processando registro de adoção e consultando validações...";

        try {
            const resposta = await fetch(`/api/adocoes/${animalId}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const resultado = await resposta.json();

            if (resposta.ok && resultado.sucesso) {
                mostrarRegistro(resultado.adocao);

                area.dataset.status = "adotado";
                const situacao = document.querySelector(".ficha-situacao");
                if (situacao) situacao.textContent = "Adotado";

                bloquearOperacoes();
                formulario.reset();
                formulario.hidden = true;

                mensagem.className = "form-mensagem form-mensagem--sucesso";
                mensagem.textContent = "Adoção registrada com sucesso! A ficha do cão foi congelada (RN05).";
            } else {
                mensagem.className = "form-mensagem form-mensagem--erro";
                mensagem.textContent = resultado.mensagem || resultado.erro || "Não foi possível registrar a adoção.";
            }
        } catch (erro) {
            mensagem.className = "form-mensagem form-mensagem--erro";
            mensagem.textContent = "Erro na comunicação com o servidor. Verifique a conexão.";
        }

        mensagem.scrollIntoView({ block: "nearest" });
    });

    formulario.addEventListener("reset", function () {
        nome.setCustomValidity("");
        telefone.setCustomValidity("");

        setTimeout(prepararData, 0);
    });

    prepararData();
    carregarHistoricoAdocao();
})();
