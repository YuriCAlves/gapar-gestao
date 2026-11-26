"""Superfície pública da API (`/api/public/*`), CP-01.

Regras:
- só é pública a requisição roteada para o blueprint `public` E com caminho canônico
  `/api/public/...` (sem `..` nem `//`). Todo o resto de `/api/*` continua exigindo sessão;
- requisição pública ignora a sessão: não lê `current_user`, não grava cookie e não adiciona
  `Vary: Cookie`, para que a CDN da Vercel possa guardar a resposta em cache.
"""
from functools import wraps

from flask import current_app, has_request_context, jsonify, make_response, request
from flask.sessions import SecureCookieSessionInterface

from app.config import FLAGS_DISPONIVEIS as FLAGS

PREFIXO_PUBLICO = "/api/public/"
BLUEPRINT_PUBLICO = "public"


def is_public_request() -> bool:
    if not has_request_context():
        return False
    caminho = request.path or ""
    return (
        request.blueprint == BLUEPRINT_PUBLICO
        and caminho.startswith(PREFIXO_PUBLICO)
        and ".." not in caminho
        and "//" not in caminho
    )


class SessaoPublicaInterface(SecureCookieSessionInterface):
    """Não grava cookie de sessão (nem `Vary: Cookie`) em respostas de rotas públicas."""

    def save_session(self, app, session, response):
        if is_public_request():
            return None
        return super().save_session(app, session, response)


def flag_ativa(nome: str) -> bool:
    """Feature flag lida da configuração (`FEATURES`). Desconhecida ou ausente = desligada."""
    return bool((current_app.config.get("FEATURES") or {}).get(nome, False))


def flags_publicas() -> dict:
    return {nome: flag_ativa(nome) for nome in FLAGS}


def require_feature(nome: str):
    """Rota indisponível (404) enquanto a flag estiver desligada: o módulo nem parece existir."""
    if nome not in FLAGS:
        raise ValueError(f"Feature flag desconhecida: {nome}")

    def decorador(f):
        @wraps(f)
        def envolvida(*args, **kwargs):
            if not flag_ativa(nome):
                return jsonify({"erro": "Recurso não encontrado", "codigo": 404,
                                "mensagem": "A rota ou registro solicitado não existe."}), 404
            return f(*args, **kwargs)
        return envolvida
    return decorador


def cache_publico(segundos: int = 300, revalidar: int = 3600, navegador: int = 60):
    """Cabeçalhos de cache de CDN só para respostas 200 (erro nunca vai para o cache)."""

    def decorador(f):
        @wraps(f)
        def envolvida(*args, **kwargs):
            resposta = make_response(f(*args, **kwargs))
            if resposta.status_code == 200:
                resposta.headers["Cache-Control"] = f"public, max-age={navegador}"
                resposta.headers["Vercel-CDN-Cache-Control"] = (
                    f"max-age={segundos}, stale-while-revalidate={revalidar}"
                )
            else:
                resposta.headers["Cache-Control"] = "no-store"
            return resposta
        return envolvida
    return decorador
