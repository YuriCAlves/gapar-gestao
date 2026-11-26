"""Verificação do Cloudflare Turnstile (anti-robô) nas rotas públicas de escrita (CP-01).

Fail-closed: qualquer dúvida (rede, resposta estranha, ação diferente) reprova.
Sem `TURNSTILE_SECRET_KEY`:
- produção -> `ApiError 503` (a rota pública não pode funcionar desprotegida);
- desenvolvimento/testes -> aprova, com aviso no log, para não travar o trabalho local.
"""
import requests
from flask import current_app

from app.utils.validation import ApiError

URL_VERIFICACAO = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
TEMPO_LIMITE = 5  # segundos
TAMANHO_MAXIMO_TOKEN = 2048


def verificar(token: str | None, acao: str, ip: str | None = None) -> bool:
    segredo = (current_app.config.get("TURNSTILE_SECRET_KEY") or "").strip()
    if not segredo:
        if current_app.config.get("TESTING") or current_app.debug:
            current_app.logger.warning("Turnstile não configurado: verificação ignorada (só desenvolvimento).")
            return True
        current_app.logger.error("Turnstile não configurado em produção: rota pública recusada.")
        raise ApiError("Serviço indisponível", 503,
                       "Este formulário está temporariamente indisponível. Tente mais tarde.")

    if not token or not isinstance(token, str) or len(token) > TAMANHO_MAXIMO_TOKEN:
        return False

    dados = {"secret": segredo, "response": token}
    if ip:
        dados["remoteip"] = ip
    try:
        resposta = requests.post(URL_VERIFICACAO, data=dados, timeout=TEMPO_LIMITE)
        corpo = resposta.json()
    except (requests.RequestException, ValueError) as exc:
        current_app.logger.warning("Turnstile inacessível (%s): requisição reprovada.", type(exc).__name__)
        return False

    if not isinstance(corpo, dict) or corpo.get("success") is not True:
        return False
    # O widget é renderizado com `action`; um token emitido para outra ação não vale aqui.
    return corpo.get("action") == acao
