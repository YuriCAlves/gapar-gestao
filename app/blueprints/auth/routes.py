from flask import jsonify, request, url_for
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user
)
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.auth.exceptions import GoogleAuthError

from app.extensions import db
from app.models.user import User
from app.models.whitelist import Whitelist
from flask import current_app

from . import auth_bp


@auth_bp.route("/status", methods=["GET"])
def auth_status():
    """Retorna o estado atual da autenticação."""
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
    """Instruções para autenticação via Google."""
    return jsonify({
        "metodo": "Google Identity Services",
        "endpoint": url_for("auth.google_login"),
        "requisito": "E-mail autorizado pelo GAPAR."
    }), 200


@auth_bp.route("/google", methods=["POST"])
def google_login():
    """Valida o ID Token do Google e autentica a usuária."""

    data = request.get_json(silent=True) or {}
    token = data.get("credential") or data.get("id_token")

    if not token:
        return jsonify({
            "erro": "Token não informado."
        }), 400

    client_id = current_app.config.get("GOOGLE_CLIENT_ID")

    if not client_id:
        return jsonify({
            "erro": "GOOGLE_CLIENT_ID não configurado no servidor."
        }), 500

    # Valida assinatura, emissor, validade e público do token.
    try:
        google_user = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            client_id
        )

    except (ValueError, GoogleAuthError):
        return jsonify({
            "erro": "Token Google inválido ou expirado."
        }), 401

    email = google_user.get("email", "").strip().lower()
    google_id = google_user.get("sub")
    name = google_user.get("name")

    if not email or not google_id or not google_user.get("email_verified"):
        return jsonify({
            "erro": "Não foi possível confirmar a identidade da conta Google."
        }), 401

    # Verifica se é a administradora inicial.
    admin_email = (
        current_app.config.get("INITIAL_ADMIN_EMAIL") or ""
    ).strip().lower()

    is_initial_admin = email == admin_email

    # Usuárias comuns precisam estar na whitelist.
    authorization = None

    if not is_initial_admin:
        authorization = Whitelist.query.filter_by(email=email).first()

        if not authorization or not authorization.is_active:
            return jsonify({
                "erro": "E-mail não autorizado.",
                "mensagem": "Solicite à administradora sua inclusão na whitelist."
            }), 403

    # Procura uma conta já cadastrada.
    user = User.query.filter_by(email=email).first()

    if user:
        # Impede que outra identidade Google assuma uma conta existente.
        if user.google_id and user.google_id != google_id:
            return jsonify({
                "erro": "Esta conta está vinculada a outra identidade Google."
            }), 403

    else:
        user = User(
            email=email,
            google_id=google_id,
            name=name
        )
        db.session.add(user)

    # Define as permissões.
    if is_initial_admin:
        user.role = "Administradora"
    else:
        user.role = authorization.role

    user.google_id = google_id
    user.name = name or user.name
    user.is_active = True

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro ao registrar autenticação Google.")
        return jsonify({
            "erro": "Não foi possível concluir o login."
        }), 500

    login_user(user)

    return jsonify({
        "sucesso": True,
        "mensagem": "Autenticação realizada com sucesso.",
        "usuario": user.to_dict()
    }), 200


@auth_bp.route("/me", methods=["GET"])
@login_required
def current_user_info():
    """Retorna os dados da usuária autenticada."""
    return jsonify({
        "usuario": current_user.to_dict()
    }), 200


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Encerra a sessão."""
    logout_user()

    return jsonify({
        "sucesso": True,
        "mensagem": "Sessão finalizada com sucesso."
    }), 200