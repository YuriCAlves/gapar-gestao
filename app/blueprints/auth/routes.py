import secrets
from urllib.parse import urlencode

import requests
from flask import jsonify, request, redirect, url_for, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.extensions import db
from app.models.user import User
from app.models.whitelist import Whitelist
from app.utils.audit import log_audit_event
from . import auth_bp


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


# ---------------------------------------------------------------------------
# Núcleo da autenticação (RF01, RF02, RN12, RN13, RN14, RNF08, RN16)
# ---------------------------------------------------------------------------

def _verify_id_token(token):
    """Valida assinatura, emissor, validade e público do ID Token do Google.

    Retorna (claims, None) ou (None, mensagem_de_erro).
    """
    client_id = current_app.config.get("GOOGLE_CLIENT_ID")
    if not client_id:
        return None, "GOOGLE_CLIENT_ID não configurado no servidor."
    try:
        claims = google_id_token.verify_oauth2_token(token, google_requests.Request(), client_id)
    except (ValueError, GoogleAuthError):
        return None, "Token Google inválido ou expirado."
    if not claims.get("sub") or not claims.get("email") or not claims.get("email_verified"):
        return None, "Não foi possível confirmar a identidade da conta Google."
    return claims, None


def _initial_admin_email():
    return (current_app.config.get("INITIAL_ADMIN_EMAIL") or "").strip().lower()


def _authenticate(email, name, google_id, access_token=None, refresh_token=None):
    """Valida a Whitelist, persiste a usuária e abre a sessão.

    Único ponto de entrada de login: Google (ID Token / redirecionamento) e dev-login
    passam por aqui, então todos respeitam as mesmas regras e a mesma auditoria.
    """
    email = (email or "").strip().lower()
    if not email:
        return jsonify({"error": "E-mail não fornecido para autenticação."}), 400

    is_initial_admin = email == _initial_admin_email()
    entry = Whitelist.query.filter(db.func.lower(Whitelist.email) == email).first()

    # RN12: e-mail fora da Whitelist é barrado (a administradora inicial é a exceção, RN13)
    if not is_initial_admin and not entry:
        log_audit_event(
            acao="LOGIN_REJEITADO_FORA_WHITELIST",
            entidade="Whitelist",
            detalhes=f"Tentativa de acesso não autorizada para o e-mail: {email}",
        )
        return jsonify({
            "error": "Acesso não autorizado",
            "mensagem": "Seu e-mail não consta na Whitelist de usuárias da GAPAR (RF02, RN12). Solicite liberação à Administradora.",
        }), 403

    # RN14: cadastro desativado é rejeitado
    if not is_initial_admin and not entry.is_active:
        log_audit_event(
            acao="LOGIN_REJEITADO_USUARIA_INATIVA",
            entidade="Whitelist",
            entidade_id=entry.id,
            detalhes=f"Tentativa de login de usuária inativa na Whitelist: {email}",
        )
        return jsonify({
            "error": "Acesso revogado",
            "mensagem": "Seu cadastro está inativo na Whitelist da GAPAR (RN12, RN14).",
        }), 403

    role = "Administradora" if is_initial_admin else entry.role

    user = User.query.filter(db.func.lower(User.email) == email).first()
    if user:
        # Impede que outra identidade Google assuma uma conta existente
        if google_id and user.google_id and user.google_id != google_id:
            log_audit_event(
                acao="LOGIN_REJEITADO_IDENTIDADE_DIVERGENTE",
                entidade="User",
                entidade_id=user.id,
                detalhes=f"Identidade Google divergente para {email}",
                user=user,
            )
            return jsonify({"error": "Esta conta está vinculada a outra identidade Google."}), 403
    else:
        user = User(email=email)
        db.session.add(user)

    if is_initial_admin and not entry:
        # Garante que a administradora inicial apareça na gestão da Whitelist
        db.session.add(Whitelist(email=email, role="Administradora", is_active=True))

    user.role = role
    user.is_active = True
    if google_id:
        user.google_id = google_id
    if name:
        user.name = user.name or name
    if access_token or refresh_token:
        user.set_google_tokens(access_token, refresh_token)  # RNF08

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro ao registrar autenticação.")
        return jsonify({"error": "Não foi possível concluir o login."}), 500

    login_user(user)

    log_audit_event(
        acao="LOGIN_SUCESSO",
        entidade="User",
        entidade_id=user.id,
        detalhes=f"Login realizado com sucesso (Perfil: {user.role})",
        user=user,
    )

    return jsonify({
        "sucesso": True,
        "mensagem": "Autenticação realizada com sucesso.",
        "usuario": user.to_dict(),
    }), 200


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

@auth_bp.route("/status", methods=["GET"])
def auth_status():
    """Retorna o estado atual da autenticação."""
    if current_user.is_authenticated:
        return jsonify({
            "autenticado": True,
            "usuario": current_user.to_dict(),
            "email": current_user.email,
            "role": current_user.role,
            "ativo": current_user.is_active,
        }), 200
    return jsonify({"autenticado": False, "mensagem": "Nenhuma sessão ativa."}), 200


@auth_bp.route("/me", methods=["GET"])
@login_required
def current_user_info():
    """Retorna os dados da usuária autenticada."""
    return jsonify({"usuario": current_user.to_dict()}), 200


@auth_bp.route("/login", methods=["GET"])
def login_info():
    """Instruções para login via Google (RF01, RF02)."""
    return jsonify({
        "metodo": "Google OAuth 2.0",
        "url_autorizacao": url_for("auth.google_login", _external=True),
        "endpoint_id_token": url_for("auth.google_token_auth", _external=True),
        "requisito": "O e-mail deve constar previamente na Whitelist (RF02, RN12)",
        "dev_login": bool(current_app.config.get("DEV_LOGIN_ENABLED")),
        "google_configurado": bool(
            current_app.config.get("GOOGLE_CLIENT_ID") and current_app.config.get("GOOGLE_CLIENT_SECRET")
        ),
    }), 200


@auth_bp.route("/google", methods=["POST"])
def google_token_auth():
    """Login com ID Token do Google Identity Services (campo `credential` ou `id_token`)."""
    data = request.get_json(silent=True) or {}
    token = data.get("credential") or data.get("id_token")
    if not token:
        return jsonify({"error": "Token não informado."}), 400

    claims, erro = _verify_id_token(token)
    if erro:
        status = 500 if "GOOGLE_CLIENT_ID" in erro else 401
        return jsonify({"error": erro}), status

    return _authenticate(claims["email"], claims.get("name"), claims["sub"])


@auth_bp.route("/google", methods=["GET"])
def google_login():
    """Inicia o fluxo OAuth 2.0 por redirecionamento (com `state` contra CSRF)."""
    client_id = current_app.config.get("GOOGLE_CLIENT_ID")
    if not client_id:
        return jsonify({"error": "GOOGLE_CLIENT_ID não configurado no servidor."}), 500

    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    redirect_uri = url_for("auth.google_callback", _external=True)

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    google_auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    if request.args.get("format") == "json":
        return jsonify({"url_redirecionamento": google_auth_url, "redirect_uri": redirect_uri}), 200
    return redirect(google_auth_url)


@auth_bp.route("/callback", methods=["GET"])
def google_callback():
    """Conclui o fluxo por redirecionamento: troca o code, valida o ID Token e abre a sessão."""
    # Esta rota é aberta pelo navegador (não por fetch), então toda falha volta para a tela de
    # login do SPA com um código curto em ?erro=, em vez de mostrar JSON cru para a usuária.
    def falhou(codigo):
        return redirect(f"/entrar?erro={codigo}")

    expected_state = session.pop("oauth_state", None)
    if not expected_state or request.args.get("state") != expected_state:
        return falhou("google")

    code = request.args.get("code")
    if request.args.get("error") or not code:
        return falhou("google")

    try:
        token_response = requests.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": current_app.config.get("GOOGLE_CLIENT_ID"),
            "client_secret": current_app.config.get("GOOGLE_CLIENT_SECRET"),
            "redirect_uri": url_for("auth.google_callback", _external=True),
            "grant_type": "authorization_code",
        }, timeout=10)
        token_data = token_response.json()
    except (requests.RequestException, ValueError):
        return falhou("google")

    if token_response.status_code != 200 or "id_token" not in token_data:
        return falhou("google")

    claims, erro = _verify_id_token(token_data["id_token"])
    if erro:
        return falhou("google")

    _, status = _authenticate(
        claims["email"], claims.get("name"), claims["sub"],
        token_data.get("access_token"), token_data.get("refresh_token"),
    )
    if status == 200:
        return redirect("/")
    return falhou("sem_acesso" if status == 403 else "falha")


@auth_bp.route("/dev-login", methods=["POST"])
def dev_login():
    """Login de desenvolvimento/testes, sem Google. Só existe quando DEV_LOGIN_ENABLED (nunca em produção)."""
    if not current_app.config.get("DEV_LOGIN_ENABLED"):
        return jsonify({"error": "Recurso não encontrado"}), 404

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        entry = (Whitelist.query.filter_by(role="Administradora", is_active=True).first()
                 or Whitelist.query.filter_by(is_active=True).first())
        if not entry:
            return jsonify({
                "error": "Nenhum usuário ativo na Whitelist.",
                "mensagem": "Cadastre uma usuária na Whitelist ou utilize o comando 'flask seed'.",
            }), 400
        email = entry.email

    return _authenticate(email, name=None, google_id=None)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Encerra a sessão ativa (RF01)."""
    user_email, user_id = current_user.email, current_user.id
    logout_user()

    log_audit_event(
        acao="LOGOUT",
        entidade="User",
        entidade_id=user_id,
        detalhes=f"Sessão encerrada pela usuária: {user_email}",
    )
    return jsonify({"sucesso": True, "mensagem": "Sessão finalizada com sucesso."}), 200
