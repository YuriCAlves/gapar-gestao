const abas = Array.from(
    document.querySelectorAll('[role="tab"]')
);

function ativarAba(abaSelecionada) {
    abas.forEach(function (aba) {
        const selecionada = aba === abaSelecionada;

        aba.setAttribute("aria-selected", String(selecionada));
        aba.tabIndex = selecionada ? 0 : -1;

        const painel = document.getElementById(
            aba.getAttribute("aria-controls")
        );

        painel.hidden = !selecionada;
    });
}

abas.forEach(function (aba, indice) {
    aba.addEventListener("click", function () {
        ativarAba(aba);
    });

    aba.addEventListener("keydown", function (evento) {
        let proximoIndice;

        switch (evento.key) {
            case "ArrowRight":
                proximoIndice = (indice + 1) % abas.length;
                break;

            case "ArrowLeft":
                proximoIndice =
                    (indice - 1 + abas.length) % abas.length;
                break;

            case "Home":
                proximoIndice = 0;
                break;

            case "End":
                proximoIndice = abas.length - 1;
                break;

            default:
                return;
        }

        evento.preventDefault();

        const proximaAba = abas[proximoIndice];

        ativarAba(proximaAba);
        proximaAba.focus();
    });
});