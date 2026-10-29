from flask import jsonify, request
from flask_login import login_required
from app.utils.decorators import admin_required
from . import admin_bp


@admin_bp.route("/whitelist", methods=["GET", "POST"])
@admin_required
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
        "sucesso": True,
        "whitelist": []
    }), 200


@admin_bp.route("/whitelist/<int:user_id>/desativar", methods=["PATCH", "POST"])
@admin_required
def desativar_whitelist(user_id):
    return jsonify({"sucesso": True, "mensagem": "Usuária desativada."}), 200


@admin_bp.route("/nao-aptos", methods=["GET", "POST"])
@admin_required
def nao_aptos():
    return jsonify({"sucesso": True, "nao_aptos": []}), 200


@admin_bp.route("/auditoria", methods=["GET"])
@admin_required
def auditoria():
    return jsonify({"sucesso": True, "logs": []}), 200
