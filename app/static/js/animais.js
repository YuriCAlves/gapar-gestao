const formularioBusca = document.querySelector(".busca");
const campoBusca = document.querySelector("#busca-nome");
const filtroStatus = document.querySelector("#filtro-status");
const cards = document.querySelectorAll(".animal-card");
const mensagemBusca = document.querySelector("#mensagem-busca");

function normalizarTexto(texto) {
    return texto
        .trim()
        .toLocaleLowerCase("pt-BR")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "");
}

function filtrarAnimais() {
    const busca = normalizarTexto(campoBusca.value);
    const situacaoSelecionada = normalizarTexto(filtroStatus.value);
    let encontrados = 0;

    cards.forEach(function (card) {
        const nome = normalizarTexto(
            card.querySelector("h3").textContent
        );

        const situacao = normalizarTexto(
            card.querySelector(".animal-card__status").textContent
        );

        const correspondeNome = nome.includes(busca);
        const correspondeSituacao =
            situacaoSelecionada === "" ||
            situacao === situacaoSelecionada;

        const corresponde = correspondeNome && correspondeSituacao;

        card.hidden = !corresponde;

        if (corresponde) {
            encontrados++;
        }
    });

    if (encontrados === 0) {
        mensagemBusca.textContent =
            "Nenhum animal encontrado. Tente outro nome ou situação.";
    } else if (encontrados === 1) {
        mensagemBusca.textContent = "1 animal encontrado.";
    } else {
        mensagemBusca.textContent =
            `${encontrados} animais encontrados.`;
    }
}

formularioBusca.addEventListener("submit", function (evento) {
    evento.preventDefault();
    filtrarAnimais();
});

filtroStatus.addEventListener("change", filtrarAnimais);