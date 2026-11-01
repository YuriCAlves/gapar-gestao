const formularioBusca = document.querySelector(".busca");
const campoBusca = document.querySelector("#busca-nome");
const cards = document.querySelectorAll(".animal-card");

function normalizarTexto(texto) {
    return texto
        .trim()
        .toLocaleLowerCase("pt-BR")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "");
}

formularioBusca.addEventListener("submit", function (evento) {
    evento.preventDefault();

    const busca = normalizarTexto(campoBusca.value);

    cards.forEach(function (card) {
        const nome = card.querySelector("h3").textContent;
        card.hidden = !normalizarTexto(nome).includes(busca);
    });
});