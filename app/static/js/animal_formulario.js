const formulario = document.querySelector("#form-animal");
const campoNome = document.querySelector("#nome");
const campoRaca = document.querySelector("#raca");
const campoFoto = document.querySelector("#foto");

const fotoPrevia = document.querySelector("#foto-previa");
const imagemPrevia = document.querySelector("#imagem-previa");
const removerFoto = document.querySelector("#remover-foto");
const fotoMensagem = document.querySelector("#foto-mensagem");
const formMensagem = document.querySelector("#form-mensagem");

const tiposPermitidos = [
    "image/jpeg",
    "image/png",
    "image/webp"
];

const tamanhoMaximo = 5 * 1024 * 1024;
let urlFoto = null;

function liberarPrevia() {
    imagemPrevia.onload = null;
    imagemPrevia.onerror = null;
    imagemPrevia.removeAttribute("src");
    fotoPrevia.hidden = true;

    if (urlFoto) {
        URL.revokeObjectURL(urlFoto);
        urlFoto = null;
    }
}

function limparFoto() {
    liberarPrevia();
    campoFoto.value = "";
    campoFoto.setCustomValidity("");
    fotoMensagem.textContent = "";
}

function validarTexto(campo) {
    campo.setCustomValidity(
        campo.value.trim() === ""
            ? "Preencha este campo com um texto válido."
            : ""
    );
}

[campoNome, campoRaca].forEach(function (campo) {
    campo.addEventListener("input", function () {
        validarTexto(campo);
    });
});

campoFoto.addEventListener("change", function () {
    liberarPrevia();
    campoFoto.setCustomValidity("");
    fotoMensagem.textContent = "";

    const arquivo = campoFoto.files[0];

    if (!arquivo) {
        return;
    }

    if (!tiposPermitidos.includes(arquivo.type)) {
        const mensagem = "Escolha uma imagem JPEG, PNG ou WebP.";
        campoFoto.setCustomValidity(mensagem);
        fotoMensagem.textContent = mensagem;
        campoFoto.reportValidity();
        return;
    }

    if (arquivo.size > tamanhoMaximo) {
        const mensagem = "A imagem deve ter no máximo 5 MB.";
        campoFoto.setCustomValidity(mensagem);
        fotoMensagem.textContent = mensagem;
        campoFoto.reportValidity();
        return;
    }

    campoFoto.setCustomValidity("Aguarde a leitura da imagem.");

    imagemPrevia.onload = function () {
        campoFoto.setCustomValidity("");
        fotoPrevia.hidden = false;
    };

    imagemPrevia.onerror = function () {
        const mensagem =
            "Não foi possível abrir essa imagem. Selecione outra.";

        liberarPrevia();
        campoFoto.setCustomValidity(mensagem);
        fotoMensagem.textContent = mensagem;
    };

    urlFoto = URL.createObjectURL(arquivo);
    imagemPrevia.src = urlFoto;
});

removerFoto.addEventListener("click", function () {
    limparFoto();
    formMensagem.textContent = "";
    campoFoto.focus();
});

formulario.addEventListener("input", function () {
    // Uma alteração invalida a mensagem da validação anterior.
    formMensagem.textContent = "";
});

formulario.addEventListener("submit", function (evento) {
    evento.preventDefault();

    validarTexto(campoNome);
    validarTexto(campoRaca);

    if (!formulario.reportValidity()) {
        return;
    }

    const dadosFormulario = new FormData(formulario);
    const peso = dadosFormulario.get("peso_kg");

    // Objeto preparado com os nomes definidos no modelo Animal.
    // Não há envio para a API nesta etapa.
    const dadosAnimal = {
        nome: dadosFormulario.get("nome").trim(),
        idade_estimada:
            dadosFormulario.get("idade_estimada").trim() || null,
        sexo: dadosFormulario.get("sexo"),
        raca: dadosFormulario.get("raca").trim(),
        porte: dadosFormulario.get("porte"),
        pelagem: dadosFormulario.get("pelagem").trim() || null,
        peso_kg: peso === "" ? null : Number(peso),
        local_resgate:
            dadosFormulario.get("local_resgate").trim() || null,
        motivo_resgate:
            dadosFormulario.get("motivo_resgate").trim() || null,
        is_castrado: dadosFormulario.has("is_castrado"),
        is_idoso: dadosFormulario.has("is_idoso"),
        cuidados_especiais:
            dadosFormulario.get("cuidados_especiais").trim() || null
    };

    formMensagem.textContent =
        `Os dados de ${dadosAnimal.nome} passaram pela validação. ` +
        "Este é um teste: nenhum cadastro ou foto foi salvo.";

    formMensagem.scrollIntoView({
        block: "nearest"
    });
});

formulario.addEventListener("reset", function () {
    limparFoto();
    campoNome.setCustomValidity("");
    campoRaca.setCustomValidity("");
    formMensagem.textContent = "";

    setTimeout(function () {
        campoNome.focus();
    }, 0);
});