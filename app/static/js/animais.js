const formularioBusca = document.querySelector(".busca");
const campoBusca = document.querySelector("#busca-nome");
const filtroStatus = document.querySelector("#filtro-status");
const filtroPorte = document.querySelector("#filtro-porte");
const filtroSexo = document.querySelector("#filtro-sexo");
const filtroCastrado = document.querySelector("#filtro-castrado");
const filtroIdoso = document.querySelector("#filtro-idoso");

const cards = document.querySelectorAll(".animal-card");
const mensagemBusca = document.querySelector("#mensagem-busca");
const estadoVazio = document.querySelector("#estado-vazio");

function normalizarTexto(texto) {
    return texto
        .trim()
        .toLocaleLowerCase("pt-BR")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "");
}

function filtrarAnimais() {
    const busca = normalizarTexto(campoBusca.value);
    let encontrados = 0;

    cards.forEach(function (card) {
        const nome = normalizarTexto(
            card.querySelector("h3").textContent
        );

        const correspondeNome = nome.includes(busca);

        const correspondeStatus =
            filtroStatus.value === "" ||
            card.dataset.status === filtroStatus.value;

        const correspondePorte =
            filtroPorte.value === "" ||
            card.dataset.porte === filtroPorte.value;

        const correspondeSexo =
            filtroSexo.value === "" ||
            card.dataset.sexo === filtroSexo.value;

        const correspondeCastrado =
            !filtroCastrado.checked ||
            card.dataset.castrado === "true";

        const correspondeIdoso =
            !filtroIdoso.checked ||
            card.dataset.idoso === "true";

        const corresponde =
            correspondeNome &&
            correspondeStatus &&
            correspondePorte &&
            correspondeSexo &&
            correspondeCastrado &&
            correspondeIdoso;

        card.hidden = !corresponde;

        if (corresponde) {
            encontrados++;
        }
    });

    estadoVazio.hidden = encontrados !== 0;

    if (encontrados === 0) {
        mensagemBusca.textContent = "Nenhum animal encontrado.";
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

// Atualiza os resultados enquanto o nome é digitado.
campoBusca.addEventListener("input", filtrarAnimais);

// Atualiza os resultados ao mudar qualquer filtro.
[
    filtroStatus,
    filtroPorte,
    filtroSexo,
    filtroCastrado,
    filtroIdoso
].forEach(function (filtro) {
    filtro.addEventListener("change", filtrarAnimais);
});

formularioBusca.addEventListener("reset", function () {
    // Aguarda o navegador restaurar os valores do formulário.
    setTimeout(function () {
        filtrarAnimais();
        campoBusca.focus();
    }, 0);
});

// Mostra a contagem assim que a página é carregada.
filtrarAnimais();