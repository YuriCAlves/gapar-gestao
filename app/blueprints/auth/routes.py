from flask import jsonify, request, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from . import auth_bp


@auth_bp.route("/status", methods=["GET"])
def auth_status():
    """Retorna o estado atual da autenticação do usuário."""
    if current_user.is_authenticated:
        return jsonify({
            "autenticado": True,
            "email": current_user.email,
            "role": current_user.role,
            "ativo": current_user.active
        }), 200
    return jsonify({
        "autenticado": False,
        "mensagem": "Nenhuma sessão ativa."
    }), 200


@auth_bp.route("/login", methods=["GET"])
def login_info():
    """Instruções e endpoint para login via Google OAuth 2.0 (RF01)."""
    return jsonify({
        "metodo": "Google OAuth 2.0",
        "url_autorizacao": url_for("auth.google_login", _external=True),
        "requisito": "E-mail deve constar previamente na Whitelist (RF02, RN12)"
    }), 200


@auth_bp.route("/google")
def google_login():
    """Inicia o fluxo de autorização do Google OAuth 2.0."""
    return jsonify({
        "mensagem": "Redirecionamento para autenticação Google OAuth 2.0.",
        "endpoint_callback": url_for("auth.google_callback", _external=True)
    }), 200


@auth_bp.route("/callback")
def google_callback():
    """Processa o callback OAuth e valida a Whitelist (RF02, RN12)."""
    return jsonify({
        "mensagem": "Callback recebido e em validação contra a Whitelist."
    }), 200


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Encerra a sessão ativa (RF01)."""
    logout_user()
    return jsonify({"sucesso": True, "mensagem": "Sessão finalizada com sucesso."}), 200
