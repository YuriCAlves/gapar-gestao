(() => {
    const areaSaude = document.querySelector("#saude-demo");

    if (!areaSaude) {
        return;
    }

    const animalId = Number(areaSaude.dataset.animalId);

    const formVacina = document.querySelector("#form-vacina");
    const formProntuario = document.querySelector("#form-prontuario");

    const mensagemVacina = document.querySelector("#mensagem-vacina");
    const mensagemProntuario = document.querySelector("#mensagem-prontuario");

    const listaVacinas = document.querySelector("#lista-vacinas");
    const listaProntuario = document.querySelector("#lista-prontuario");

    const vacinasVazio = document.querySelector("#vacinas-vazio");
    const prontuarioVazio = document.querySelector("#prontuario-vazio");

    function formatarData(valor) {
        if (!valor) return "Não informada";
        const [ano, mes, dia] = valor.split("-");
        return `${dia}/${mes}/${ano}`;
    }

    async function carregarVacinas() {
        try {
            const resp = await fetch(`/api/saude/vacinas/${animalId}`);
            if (!resp.ok) return;

            const dados = await resp.json();
            const vacinas = dados.vacinas || [];

            listaVacinas.replaceChildren();

            if (vacinas.length === 0) {
                if (vacinasVazio) vacinasVazio.hidden = false;
                return;
            }

            if (vacinasVazio) vacinasVazio.hidden = true;

            vacinas.forEach(function (v) {
                const artigo = document.createElement("article");
                artigo.className = "saude-registro";

                const titulo = document.createElement("h4");
                titulo.textContent = v.nome_vacina;

                const detalhes = document.createElement("dl");
                detalhes.className = "saude-detalhes";

                const campos = [
                    ["Data de aplicação", formatarData(v.data_aplicacao)],
                    ["Próximo reforço", formatarData(v.data_reforco)],
                    ["Lote", v.lote || "Não informado"],
                    ["Observações", v.observacoes || "Nenhuma"]
                ];

                campos.forEach(function ([rotulo, valor]) {
                    const grupo = document.createElement("div");
                    const termo = document.createElement("dt");
                    const desc = document.createElement("dd");
                    termo.textContent = rotulo;
                    desc.textContent = valor;
                    grupo.append(termo, desc);
                    detalhes.append(grupo);
                });

                artigo.append(titulo, detalhes);
                listaVacinas.append(artigo);
            });
        } catch (e) {
            console.error("Erro ao carregar vacinas:", e);
        }
    }

    async function carregarProntuarios() {
        try {
            const resp = await fetch(`/api/saude/prontuario/${animalId}`);
            if (!resp.ok) return;

            const dados = await resp.json();
            const prontuarios = dados.prontuarios || [];

            listaProntuario.replaceChildren();

            if (prontuarios.length === 0) {
                if (prontuarioVazio) prontuarioVazio.hidden = false;
                return;
            }

            if (prontuarioVazio) prontuarioVazio.hidden = true;

            prontuarios.forEach(function (p) {
                const artigo = document.createElement("article");
                artigo.className = "saude-registro";

                const titulo = document.createElement("h4");
                titulo.textContent = `${p.tipo_evento} — ${formatarData(p.data_evento)}`;

                const detalhes = document.createElement("dl");
                detalhes.className = "saude-detalhes";

                const campos = [
                    ["Diagnóstico / Avaliação", p.diagnostico],
                    ["Veterinário(a)", p.veterinario_responsavel || "Não informado"],
                    ["Clínica", p.clinica || "Não informada"],
                    ["Procedimentos", p.procedimentos_realizados || "Nenhum"]
                ];

                campos.forEach(function ([rotulo, valor]) {
                    const grupo = document.createElement("div");
                    const termo = document.createElement("dt");
                    const desc = document.createElement("dd");
                    termo.textContent = rotulo;
                    desc.textContent = valor;
                    grupo.append(termo, desc);
                    detalhes.append(grupo);
                });

                artigo.append(titulo, detalhes);
                listaProntuario.append(artigo);
            });
        } catch (e) {
            console.error("Erro ao carregar prontuários:", e);
        }
    }

    if (formVacina) {
        formVacina.addEventListener("submit", async function (evento) {
            evento.preventDefault();

            const dadosForm = new FormData(formVacina);
            const payload = {
                nome_vacina: dadosForm.get("nome_vacina").trim(),
                data_aplicacao: dadosForm.get("data_aplicacao"),
                data_reforco: dadosForm.get("data_reforco") || null,
                lote: dadosForm.get("lote") ? dadosForm.get("lote").trim() : null,
                observacoes: dadosForm.get("observacoes") ? dadosForm.get("observacoes").trim() : null
            };

            try {
                const resp = await fetch(`/api/saude/vacinas/${animalId}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                const resultado = await resp.json();
                if (resp.ok && resultado.sucesso) {
                    formVacina.reset();
                    carregarVacinas();
                    if (mensagemVacina) {
                        mensagemVacina.className = "form-mensagem form-mensagem--sucesso";
                        mensagemVacina.textContent = "Vacina registrada com sucesso!";
                    }
                } else {
                    if (mensagemVacina) {
                        mensagemVacina.className = "form-mensagem form-mensagem--erro";
                        mensagemVacina.textContent = resultado.mensagem || "Erro ao registrar vacina.";
                    }
                }
            } catch (e) {
                console.error("Erro ao salvar vacina:", e);
            }
        });
    }

    if (formProntuario) {
        formProntuario.addEventListener("submit", async function (evento) {
            evento.preventDefault();

            const dadosForm = new FormData(formProntuario);
            const payload = {
                tipo_evento: dadosForm.get("tipo_evento"),
                data_evento: dadosForm.get("data_evento"),
                veterinario_responsavel: dadosForm.get("veterinario_responsavel") ? dadosForm.get("veterinario_responsavel").trim() : null,
                clinica: dadosForm.get("clinica") ? dadosForm.get("clinica").trim() : null,
                diagnostico: dadosForm.get("diagnostico").trim(),
                procedimentos_realizados: dadosForm.get("procedimentos_realizados") ? dadosForm.get("procedimentos_realizados").trim() : null
            };

            try {
                const resp = await fetch(`/api/saude/prontuario/${animalId}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                const resultado = await resp.json();
                if (resp.ok && resultado.sucesso) {
                    formProntuario.reset();
                    carregarProntuarios();
                    if (mensagemProntuario) {
                        mensagemProntuario.className = "form-mensagem form-mensagem--sucesso";
                        mensagemProntuario.textContent = "Atendimento registrado no prontuário com sucesso!";
                    }
                } else {
                    if (mensagemProntuario) {
                        mensagemProntuario.className = "form-mensagem form-mensagem--erro";
                        mensagemProntuario.textContent = resultado.mensagem || "Erro ao registrar atendimento.";
                    }
                }
            } catch (e) {
                console.error("Erro ao salvar prontuário:", e);
            }
        });
    }

    carregarVacinas();
    carregarProntuarios();
})();
