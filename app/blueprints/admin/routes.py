from flask import jsonify, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.whitelist import Whitelist
from app.models.blacklist import NonEligiblePerson
from app.models.audit import AuditLog
from app.utils.decorators import admin_required
from app.utils.audit import log_audit_event
from . import admin_bp


@admin_bp.route("/whitelist", methods=["GET", "POST"])
@admin_required
def manage_whitelist():
    """Gestão de e-mails autorizados (RF04, RN12, RN14). Exclusivo da Administradora."""
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        email = (data.get("email") or "").strip().lower()
        role = (data.get("role") or "Voluntaria").strip()

        if not email or "@" not in email:
            return jsonify({"erro": "E-mail válido é obrigatório."}), 400

        if Whitelist.query.filter(db.func.lower(Whitelist.email) == email).first():
            return jsonify({
                "erro": "E-mail já cadastrado",
                "mensagem": "Este e-mail já consta na Whitelist."
            }), 400

        entry = Whitelist(
            email=email,
            role=role if role in ("Administradora", "Voluntaria") else "Voluntaria",
            is_active=True
        )
        db.session.add(entry)
        db.session.commit()

        log_audit_event(
            acao="WHITELIST_USUARIA_ADICIONADA",
            entidade="Whitelist",
            entidade_id=entry.id,
            detalhes=f"Inclusão do e-mail {entry.email} na Whitelist (Perfil: {entry.role})"
        )

        return jsonify({
            "sucesso": True,
            "mensagem": f"E-mail {email} adicionado à Whitelist com sucesso.",
            "usuario": entry.to_dict()
        }), 201

    entradas = Whitelist.query.order_by(Whitelist.created_at.desc()).all()
    return jsonify({
        "sucesso": True,
        "total": len(entradas),
        "whitelist": [e.to_dict() for e in entradas]
    }), 200


@admin_bp.route("/whitelist/<int:entry_id>/status", methods=["PATCH", "POST"])
@admin_required
def alterar_status_whitelist(entry_id):
    """Ativação ou desativação na Whitelist (RN14: efeito imediato na próxima requisição)."""
    entry = db.get_or_404(Whitelist, entry_id)
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    is_active = bool(data["is_active"]) if "is_active" in data else not entry.is_active

    entry.is_active = is_active
    db.session.commit()

    log_audit_event(
        acao="USUARIA_ATIVADA" if is_active else "USUARIA_DESATIVADA_REVOGADA",
        entidade="Whitelist",
        entidade_id=entry.id,
        detalhes=f"Status de {entry.email} alterado para {'ativo' if is_active else 'inativo'} (RN14)"
    )

    return jsonify({
        "sucesso": True,
        "mensagem": f"Status de {entry.email} alterado com sucesso.",
        "usuario": entry.to_dict()
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
