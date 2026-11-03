(() => {
    const area = document.querySelector("#medicacoes-demo");

    if (!area) {
        return;
    }

    const animalId = Number(area.dataset.animalId);
    const statusPermitidos = [
        "em acolhimento",
        "em tratamento",
        "disponível",
        "lar temporário"
    ];

    const permitePrescricao = statusPermitidos.includes(area.dataset.status);

    const formulario = document.querySelector("#form-prescricao");
    const listaPrescricoes = document.querySelector("#lista-prescricoes");
    const listaAplicacoes = document.querySelector("#lista-aplicacoes");
    const prescricoesVazio = document.querySelector("#prescricoes-vazio");
    const aplicacoesVazio = document.querySelector("#aplicacoes-vazio");
    const mensagemAplicacao = document.querySelector("#mensagem-aplicacao");

    function dataLocal(data = new Date()) {
        const ano = data.getFullYear();
        const mes = String(data.getMonth() + 1).padStart(2, "0");
        const dia = String(data.getDate()).padStart(2, "0");
        return `${ano}-${mes}-${dia}`;
    }

    function formatarData(valor) {
        if (!valor) return "Não informada";
        const [ano, mes, dia] = valor.split("-");
        return `${dia}/${mes}/${ano}`;
    }

    async function carregarPrescricoes() {
        try {
            const resp = await fetch(`/api/saude/prescricoes/${animalId}`);
            if (!resp.ok) return;

            const dados = await resp.json();
            const prescricoes = dados.prescricoes || [];

            listaPrescricoes.replaceChildren();

            if (prescricoes.length === 0) {
                if (prescricoesVazio) prescricoesVazio.hidden = false;
                return;
            }

            if (prescricoesVazio) prescricoesVazio.hidden = true;

            prescricoes.forEach(function (p) {
                const artigo = document.createElement("article");
                artigo.className = "saude-registro";

                const titulo = document.createElement("h4");
                titulo.textContent = `${p.nome_medicamento} — ${p.dosagem}`;

                const detalhes = document.createElement("dl");
                detalhes.className = "saude-detalhes";

                const campos = [
                    ["Horários prescritos", p.horarios],
                    ["Período", `${formatarData(p.data_inicio)} até ${formatarData(p.data_fim)}`],
                    ["Status", p.is_active ? "Em andamento" : "Finalizada / Programada"],
                    ["Instruções", p.instrucoes || "Nenhuma"]
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

                // Doses do dia de hoje para dar baixa
                if (p.is_active && permitePrescricao) {
                    const areaDoses = document.createElement("div");
                    areaDoses.className = "doses-hoje";
                    areaDoses.style.marginTop = "1rem";
                    areaDoses.style.paddingTop = "0.75rem";
                    areaDoses.style.borderTop = "1px solid var(--cor-borda, #ddd)";

                    const labelDoses = document.createElement("p");
                    labelDoses.innerHTML = "<strong>Doses de Hoje:</strong>";
                    areaDoses.append(labelDoses);

                    const horarios = (p.horarios || "").split(",").map(h => h.strip ? h.strip() : h.trim()).filter(Boolean);
                    const logsHoje = p.logs_hoje || [];
                    const horariosAplicados = new Set(logsHoje.map(l => l.horario_previsto));

                    const containerBotoes = document.createElement("div");
                    containerBotoes.style.display = "flex";
                    containerBotoes.style.gap = "0.5rem";
                    containerBotoes.style.flexWrap = "wrap";
                    containerBotoes.style.marginTop = "0.5rem";

                    horarios.forEach(function (h) {
                        const btn = document.createElement("button");
                        btn.type = "button";
                        btn.className = "botao botao--secundario";
                        btn.style.fontSize = "0.875rem";

                        if (horariosAplicados.has(h)) {
                            btn.textContent = `✓ Dose das ${h} aplicada`;
                            btn.disabled = true;
                            btn.style.opacity = "0.7";
                        } else {
                            btn.textContent = `Dar baixa (${h})`;
                            btn.addEventListener("click", function () {
                                darBaixa(p.id, h, btn);
                            });
                        }

                        containerBotoes.append(btn);
                    });

                    areaDoses.append(containerBotoes);
                    artigo.append(areaDoses);
                }

                listaPrescricoes.append(artigo);
            });
        } catch (e) {
            console.error("Erro ao carregar prescrições:", e);
        }
    }

    async function darBaixa(prescricaoId, horario, btnElement) {
        if (!window.confirm(`Confirma a administração da dose de ${horario}?`)) {
            return;
        }

        btnElement.disabled = true;
        btnElement.textContent = "Gravando...";

        try {
            const resp = await fetch(`/api/saude/medicacao/baixa/${prescricaoId}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ horario_previsto: horario })
            });

            const dados = await resp.json();
            if (resp.ok && dados.sucesso) {
                btnElement.textContent = `✓ Dose das ${horario} aplicada`;
                btnElement.style.opacity = "0.7";
                if (mensagemAplicacao) {
                    mensagemAplicacao.className = "form-mensagem form-mensagem--sucesso";
                    mensagemAplicacao.textContent = `Baixa registrada com sucesso para o horário ${horario}!`;
                }
            } else {
                btnElement.disabled = false;
                btnElement.textContent = `Dar baixa (${horario})`;
                if (mensagemAplicacao) {
                    mensagemAplicacao.className = "form-mensagem form-mensagem--erro";
                    mensagemAplicacao.textContent = dados.mensagem || "Não foi possível registrar a baixa.";
                }
            }
        } catch (e) {
            btnElement.disabled = false;
            btnElement.textContent = `Dar baixa (${horario})`;
        }
    }

    if (formulario && permitePrescricao) {
        formulario.addEventListener("submit", async function (evento) {
            evento.preventDefault();

            const dadosForm = new FormData(formulario);
            const payload = {
                nome_medicamento: dadosForm.get("nome_medicamento").trim(),
                dosagem: dadosForm.get("dosagem").trim(),
                horarios: dadosForm.get("horarios").trim(),
                data_inicio: dadosForm.get("data_inicio"),
                data_fim: dadosForm.get("data_fim"),
                instrucoes: dadosForm.get("instrucoes") ? dadosForm.get("instrucoes").trim() : ""
            };

            try {
                const resp = await fetch(`/api/saude/prescricoes/${animalId}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                const resultado = await resp.json();
                if (resp.ok && resultado.sucesso) {
                    formulario.reset();
                    carregarPrescricoes();
                    if (mensagemAplicacao) {
                        mensagemAplicacao.className = "form-mensagem form-mensagem--sucesso";
                        mensagemAplicacao.textContent = "Nova prescrição cadastrada com sucesso!";
                    }
                } else {
                    if (mensagemAplicacao) {
                        mensagemAplicacao.className = "form-mensagem form-mensagem--erro";
                        mensagemAplicacao.textContent = resultado.mensagem || "Erro ao salvar prescrição.";
                    }
                }
            } catch (e) {
                console.error("Erro ao salvar prescrição:", e);
            }
        });
    }

    carregarPrescricoes();
})();
