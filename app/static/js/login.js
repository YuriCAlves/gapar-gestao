(() => {
    const status = document.querySelector("#login-status");
    const semSessao = document.querySelector("#login-sem-sessao");
    const comSessao = document.querySelector("#login-com-sessao");
    const tentar = document.querySelector("#login-tentar");
    const email = document.querySelector("#login-email");
    const perfil = document.querySelector("#login-perfil");

    async function consultarSessao() {
        semSessao.hidden = true;
        comSessao.hidden = true;
        tentar.hidden = true;

        status.textContent = "Consultando sessão…";

        const controlador = new AbortController();
        const limite = setTimeout(function () {
            controlador.abort();
        }, 10000);

        try {
            const resposta = await fetch("/auth/status", {
                credentials: "same-origin",
                cache: "no-store",
                headers: {
                    Accept: "application/json"
                },
                signal: controlador.signal
            });

            if (!resposta.ok) {
                throw new Error("Falha ao consultar sessão.");
            }

            const dados = await resposta.json();

            if (typeof dados.autenticado !== "boolean") {
                throw new Error("Resposta de sessão inválida.");
            }

            if (!dados.autenticado) {
                status.textContent = "Nenhuma sessão ativa.";
                semSessao.hidden = false;
                return;
            }

            if (dados.ativo !== true) {
                status.textContent =
                    "O acesso desta conta está desativado. " +
                    "Procure a responsável pela ONG.";
                return;
            }

            const perfis = {
                Administradora: "Administradora",
                Voluntaria: "Voluntária"
            };

            if (
                !Object.prototype.hasOwnProperty.call(perfis, dados.role) ||
                typeof dados.email !== "string"
            ) {
                status.textContent =
                    "Não foi possível confirmar as permissões desta conta. " +
                    "Procure a responsável pela ONG.";
                return;
            }

            email.textContent = dados.email;
            perfil.textContent = perfis[dados.role];
            comSessao.hidden = false;

            status.textContent = "Sessão reconhecida pelo servidor.";
        } catch (erro) {
            status.textContent =
                "Não foi possível consultar sua sessão. " +
                "Confira se o servidor está funcionando e tente novamente.";

            tentar.hidden = false;
        } finally {
            clearTimeout(limite);
        }
    }

    tentar.addEventListener("click", consultarSessao);
    consultarSessao();
})();