from functools import wraps
from flask import jsonify
from flask_login import current_user, logout_user


def whitelist_required(f):
    """Garante que a usuária autenticada continue ativa na Whitelist (RF02, RN12, RN14).
    Caso tenha sido desativada, desconecta a sessão e retorna HTTP 403.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                "error": "Não autenticado",
                "mensagem": "Autenticação prévia via Google OAuth e Whitelist obrigatória."
            }), 401

        if not current_user.is_active:
            # Revogação imediata (RN14)
            logout_user()
            return jsonify({
                "error": "Acesso revogado",
                "mensagem": "Seu e-mail foi desativado na Whitelist pela administração (RN12/RN14)."
            }), 403

        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Garante que apenas usuárias com perfil 'Administradora' acessem o recurso (RF03, RN13).
    Voluntárias recebem HTTP 403 Forbidden.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                "error": "Não autenticado",
                "mensagem": "Autenticação prévia via Google OAuth e Whitelist obrigatória."
            }), 401

        if not current_user.is_active:
            logout_user()
            return jsonify({
                "error": "Acesso revogado",
                "mensagem": "Seu e-mail foi desativado na Whitelist pela administração (RN12/RN14)."
            }), 403

        if current_user.role != "Administradora":
            return jsonify({
                "error": "Acesso proibido",
                "mensagem": "Este endpoint é de acesso exclusivo da Administradora (RN13)."
            }), 403

        return f(*args, **kwargs)
    return decorated_function
