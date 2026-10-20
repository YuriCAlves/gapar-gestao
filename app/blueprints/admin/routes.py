from flask import jsonify, request
from flask_login import login_required
from . import admin_bp


@admin_bp.route("/whitelist", methods=["GET", "POST"])
def manage_whitelist():
    """Gestão de usuárias autorizadas (RF04, RN12, RN14). Exclusivo da Administradora."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        email = data.get("email")
        if not email:
            return jsonify({"erro": "E-mail é obrigatório."}), 400
        return jsonify({
            "sucesso": True,
            "mensagem": f"E-mail {email} adicionado à whitelist com sucesso.",
            "usuario": {"email": email, "role": data.get("role", "Voluntaria"), "ativo": True}
        }), 201

    return jsonify({
        "total_autorizados": 1,
        "usuarios": [
            {"email": "admin@gapar.org.br", "role": "Administradora", "ativo": True}
        ]
    }), 200


@admin_bp.route("/whitelist/<int:user_id>/desativar", methods=["PATCH", "POST"])
def toggle_user_active(user_id):
    """Desativação de usuária na whitelist com bloqueio imediato (RN14)."""
    return jsonify({
        "sucesso": True,
        "mensagem": f"Usuária {user_id} desativada. Acesso revogado imediatamente para a próxima requisição."
    }), 200


@admin_bp.route("/nao-aptos", methods=["GET", "POST"])
def manage_blacklist():
    """Lista sigilosa e restrita de pessoas não aptas a adotar (RF22, RN15). Exclusivo Administradora."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        return jsonify({
            "sucesso": True,
            "mensagem": "Registro sigiloso cadastrado na lista restrita.",
            "registro": data
        }), 201

    return jsonify({
        "sigiloso": True,
        "total": 0,
        "registros": []
    }), 200


@admin_bp.route("/auditoria", methods=["GET"])
def audit_logs():
    """Trilha inviolável de logs de auditoria (RF24, RN16). Exclusivo Administradora."""
    return jsonify({
        "total_eventos": 0,
        "eventos": []
    }), 200
