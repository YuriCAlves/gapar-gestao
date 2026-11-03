from flask import jsonify, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.blacklist import NonEligiblePerson
from app.models.audit import AuditLog
from app.utils.decorators import admin_required
from app.utils.audit import log_audit_event
from . import admin_bp


@admin_bp.route("/whitelist", methods=["GET", "POST"])
@admin_required
def manage_whitelist():
    """Gestão de usuárias autorizadas (RF04, RN12, RN14). Exclusivo da Administradora."""
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        email = data.get("email", "").strip().lower()
        role = data.get("role", "Voluntaria").strip()
        name = data.get("name", "").strip()

        if not email:
            return jsonify({"erro": "E-mail é obrigatório."}), 400

        existente = User.query.filter(db.func.lower(User.email) == email).first()
        if existente:
            return jsonify({
                "erro": "E-mail já cadastrado",
                "mensagem": "Este e-mail já consta na Whitelist."
            }), 400

        user = User(
            email=email,
            name=name or email.split("@")[0].capitalize(),
            role=role if role in ("Administradora", "Voluntaria") else "Voluntaria",
            is_active=True
        )
        db.session.add(user)
        db.session.commit()

        log_audit_event(
            acao="WHITELIST_USUARIA_ADICIONADA",
            entidade="User",
            entidade_id=user.id,
            detalhes=f"Inclusão do e-mail {user.email} na Whitelist (Perfil: {user.role})"
        )

        return jsonify({
            "sucesso": True,
            "mensagem": f"E-mail {email} adicionado à Whitelist com sucesso.",
            "usuario": user.to_dict()
        }), 201

    usuarios = User.query.order_by(User.created_at.desc()).all()
    return jsonify({
        "sucesso": True,
        "total": len(usuarios),
        "whitelist": [u.to_dict() for u in usuarios]
    }), 200


@admin_bp.route("/whitelist/<int:user_id>/status", methods=["PATCH", "POST"])
@admin_required
def alterar_status_whitelist(user_id):
    """Ativação ou desativação de usuária na Whitelist (RN14: efeito imediato)."""
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    if "is_active" in data:
        is_active = bool(data["is_active"])
    else:
        is_active = not user.is_active

    user.is_active = is_active
    db.session.commit()

    acao = "USUARIA_ATIVADA" if is_active else "USUARIA_DESATIVADA_REVOGADA"
    log_audit_event(
        acao=acao,
        entidade="User",
        entidade_id=user.id,
        detalhes=f"Status da usuária {user.email} alterado para {'ativo' if is_active else 'inativo'} (RN14)"
    )

    return jsonify({
        "sucesso": True,
        "mensagem": f"Status da usuária {user.email} alterado com sucesso.",
        "usuario": user.to_dict()
    }), 200


@admin_bp.route("/nao-aptos", methods=["GET", "POST"])
@admin_required
def nao_aptos():
    """Lista sigilosa de pessoas não aptas a adotar (RF22, RN15). Exclusivo da Administradora."""
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        nome = data.get("nome", "").strip()
        motivo = data.get("motivo_impedimento", "").strip()

        if not nome or not motivo:
            return jsonify({"erro": "Nome e motivo do impedimento são obrigatórios."}), 400

        user_id = current_user.id if current_user.is_authenticated else None

        bloqueado = NonEligiblePerson(
            nome=nome,
            cpf=data.get("cpf", "").strip(),
            telefone=data.get("telefone", "").strip(),
            motivo_impedimento=motivo,
            cadastrado_por_user_id=user_id
        )
        db.session.add(bloqueado)
        db.session.commit()

        log_audit_event(
            acao="NAO_APTO_INCLUIDO",
            entidade="NonEligiblePerson",
            entidade_id=bloqueado.id,
            detalhes=f"Inclusão de {bloqueado.nome} na lista sigilosa de não aptos (RN15)"
        )

        return jsonify({
            "sucesso": True,
            "mensagem": "Registro incluído na lista sigilosa com sucesso (RN15).",
            "nao_apto": bloqueado.to_dict()
        }), 201

    lista = NonEligiblePerson.query.order_by(NonEligiblePerson.created_at.desc()).all()
    return jsonify({
        "sucesso": True,
        "total": len(lista),
        "nao_aptos": [item.to_dict() for item in lista]
    }), 200


@admin_bp.route("/auditoria", methods=["GET"])
@admin_required
def auditoria():
    """Consulta de logs imutáveis da trilha de auditoria (RF24, RN16). Exclusivo da Administradora."""
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
    return jsonify({
        "sucesso": True,
        "total": len(logs),
        "logs": [log.to_dict() for log in logs]
    }), 200
