import os
import requests
from urllib.parse import urlencode
from flask import jsonify, request, redirect, url_for, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.utils.audit import log_audit_event
from . import auth_bp


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


@auth_bp.route("/status", methods=["GET"])
def auth_status():
    """Retorna o estado atual da autenticação da usuária."""
    if current_user.is_authenticated:
        return jsonify({
            "autenticado": True,
            "usuario": current_user.to_dict()
        }), 200
    return jsonify({
        "autenticado": False,
        "mensagem": "Nenhuma sessão ativa."
    }), 200


@auth_bp.route("/login", methods=["GET"])
def login_info():
    """Instruções e URLs para login via Google OAuth 2.0 (RF01, RF02)."""
    return jsonify({
        "metodo": "Google OAuth 2.0",
        "url_autorizacao": url_for("auth.google_login", _external=True),
        "endpoint_api_token": url_for("auth.google_token_auth", _external=True),
        "requisito": "O e-mail deve constar previamente na Whitelist (RF02, RN12)"
    }), 200


@auth_bp.route("/google", methods=["GET"])
def google_login():
    """Inicia o fluxo de autorização do Google OAuth 2.0 redirecionando o navegador."""
    client_id = current_app.config.get("GOOGLE_CLIENT_ID")
    redirect_uri = url_for("auth.google_callback", _external=True)

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    
    # Se a requisição solicitar explicitamente JSON (ex: SPA/API Client)
    if request.is_json or request.args.get("format") == "json":
        return jsonify({
            "url_redirecionamento": google_auth_url,
            "redirect_uri": redirect_uri
        }), 200

    return redirect(google_auth_url)


@auth_bp.route("/callback", methods=["GET"])
def google_callback():
    """Processa o retorno do Google OAuth 2.0, valida a Whitelist e inicia a sessão (RF01, RF02, RN12, RN14)."""
    error = request.args.get("error")
    if error:
        return jsonify({
            "error": "Falha na autorização do Google",
            "detalhes": error
        }), 400

    code = request.args.get("code")
    if not code:
        return jsonify({"error": "Código de autorização não fornecido."}), 400

    client_id = current_app.config.get("GOOGLE_CLIENT_ID")
    client_secret = current_app.config.get("GOOGLE_CLIENT_SECRET")
    redirect_uri = url_for("auth.google_callback", _external=True)

    # Troca o código pelos tokens Google
    token_payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }

    try:
        token_response = requests.post(GOOGLE_TOKEN_URL, data=token_payload, timeout=10)
        token_data = token_response.json()
        if token_response.status_code != 200 or "access_token" not in token_data:
            return jsonify({
                "error": "Falha ao obter token junto ao Google",
                "detalhes": token_data
            }), 400

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")

        # Busca perfil da usuária no Google
        userinfo_resp = requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        if userinfo_resp.status_code != 200:
            return jsonify({"error": "Falha ao consultar informações do perfil Google."}), 400

        google_profile = userinfo_resp.json()
        email = google_profile.get("email")
        google_id = google_profile.get("sub")
        name = google_profile.get("name")

        return _process_user_login(email, name, google_id, access_token, refresh_token)

    except Exception as e:
        return jsonify({
            "error": "Erro na comunicação com a API do Google",
            "detalhes": str(e)
        }), 500


@auth_bp.route("/google", methods=["POST"])
def google_token_auth():
    """Autenticação direta para clientes de API e testes via Google ID Token ou payload verificado (RF01, RF02, RN12)."""
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    name = data.get("name")
    google_id = data.get("google_id")
    id_token_str = data.get("id_token")
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")

    # Caso venha um ID Token real do Google Identity Services
    if id_token_str and not email:
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests
            client_id = current_app.config.get("GOOGLE_CLIENT_ID")
            id_info = id_token.verify_oauth2_token(id_token_str, google_requests.Request(), client_id)
            email = id_info.get("email")
            name = id_info.get("name")
            google_id = id_info.get("sub")
        except Exception as e:
            return jsonify({"error": "ID Token do Google inválido", "detalhes": str(e)}), 401

    if not email:
        return jsonify({"error": "E-mail não fornecido para autenticação."}), 400

    return _process_user_login(email, name, google_id, access_token, refresh_token)


def _process_user_login(email, name, google_id, access_token=None, refresh_token=None):
    """Lógica central de validação na Whitelist, persistência segura e criação de sessão (RN12, RN14, RNF08)."""
    normalized_email = email.strip().lower()
    user = User.query.filter(db.func.lower(User.email) == normalized_email).first()

    # 1. Validação de Whitelist (RN12): Usuário inexistente é terminantemente barrado
    if not user:
        log_audit_event(
            acao="LOGIN_REJEITADO_FORA_WHITELIST",
            entidade="User",
            detalhes=f"Tentativa de acesso não autorizada para o e-mail: {normalized_email}"
        )
        return jsonify({
            "error": "Acesso não autorizado",
            "mensagem": "Seu e-mail não consta na Whitelist de usuárias da GAPAR (RF02, RN12). Solicite liberação à Administradora."
        }), 403

    # 2. Validação de Status Ativo (RN14): Usuária desativada é rejeitada
    if not user.is_active:
        log_audit_event(
            acao="LOGIN_REJEITADO_USUARIA_INATIVA",
            entidade="User",
            entidade_id=user.id,
            detalhes=f"Tentativa de login de usuária inativa na Whitelist: {normalized_email}",
            user=user
        )
        return jsonify({
            "error": "Acesso revogado",
            "mensagem": "Seu cadastro está inativo na Whitelist da GAPAR (RN12, RN14)."
        }), 403

    # 3. Atualiza dados e armazena tokens criptografados (RNF08)
    if google_id:
        user.google_id = google_id
    if name and not user.name:
        user.name = name
    if access_token or refresh_token:
        user.set_google_tokens(access_token, refresh_token)

    db.session.commit()

    # 4. Registra login na sessão Flask-Login
    login_user(user, remember=True)

    # 5. Trilha de auditoria (RF24, RN16)
    log_audit_event(
        acao="LOGIN_SUCESSO",
        entidade="User",
        entidade_id=user.id,
        detalhes=f"Login realizado com sucesso via Google OAuth 2.0 (Perfil: {user.role})",
        user=user
    )

    return jsonify({
        "sucesso": True,
        "mensagem": "Autenticação realizada com sucesso.",
        "usuario": user.to_dict()
    }), 200


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Encerra a sessão ativa da usuária (RF01)."""
    user_email = current_user.email
    user_id = current_user.id
    logout_user()

    log_audit_event(
        acao="LOGOUT",
        entidade="User",
        entidade_id=user_id,
        detalhes=f"Sessão encerrada pela usuária: {user_email}"
    )

    return jsonify({"sucesso": True, "mensagem": "Sessão finalizada com sucesso."}), 200
