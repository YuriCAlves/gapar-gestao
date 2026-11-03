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

const tamanhoMaximo = 10 * 1024 * 1024;
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
    if (campo) {
        campo.addEventListener("input", function () {
            validarTexto(campo);
        });
    }
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
        const mensagem = "A imagem deve ter no máximo 10 MB.";
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
        const mensagem = "Não foi possível abrir essa imagem. Selecione outra.";
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
    formMensagem.textContent = "";
});

formulario.addEventListener("submit", async function (evento) {
    evento.preventDefault();

    validarTexto(campoNome);
    if (campoRaca && campoRaca.value.trim()) {
        validarTexto(campoRaca);
    }

    if (!formulario.reportValidity()) {
        return;
    }

    const botaoSubmit = formulario.querySelector("button[type='submit']");
    if (botaoSubmit) {
        botaoSubmit.disabled = true;
    }

    formMensagem.className = "form-mensagem";
    formMensagem.textContent = "Salvando cadastro e comprimindo foto no servidor...";

    try {
        const dadosFormulario = new FormData(formulario);
        const resposta = await fetch("/api/animais", {
            method: "POST",
            body: dadosFormulario
        });

        const resultado = await resposta.json();

        if (resposta.ok && resultado.sucesso) {
            formMensagem.className = "form-mensagem form-mensagem--sucesso";
            formMensagem.textContent = `Animal ${resultado.animal.nome} cadastrado com sucesso! Redirecionando para a ficha...`;
            setTimeout(function () {
                window.location.href = `/animais/${resultado.animal.id}`;
            }, 1000);
        } else {
            formMensagem.className = "form-mensagem form-mensagem--erro";
            formMensagem.textContent = resultado.mensagem || resultado.erro || "Ocorreu um erro ao cadastrar o animal.";
            if (botaoSubmit) botaoSubmit.disabled = false;
        }
    } catch (erro) {
        formMensagem.className = "form-mensagem form-mensagem--erro";
        formMensagem.textContent = "Erro na comunicação com o servidor. Tente novamente.";
        if (botaoSubmit) botaoSubmit.disabled = false;
    }

    formMensagem.scrollIntoView({ block: "nearest" });
});

formulario.addEventListener("reset", function () {
    limparFoto();
    campoNome.setCustomValidity("");
    if (campoRaca) campoRaca.setCustomValidity("");
    formMensagem.textContent = "";

    setTimeout(function () {
        campoNome.focus();
    }, 0);
});
