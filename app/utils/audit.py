from flask import request
from flask_login import current_user
from app.extensions import db
from app.models.audit import AuditLog


def log_audit_event(acao: str, entidade: str, entidade_id: int | None = None, detalhes: str | None = None, user=None):
    """Registra evento na trilha de auditoria inviolável (RF24, RN16)."""
    try:
        active_user = user if user else (current_user if current_user.is_authenticated else None)
        user_id = active_user.id if active_user else None
        user_email = active_user.email if active_user else None
        ip_origem = request.remote_addr if request else None

        audit_entry = AuditLog(
            user_id=user_id,
            user_email=user_email,
            acao=acao,
            entidade=entidade,
            entidade_id=entidade_id,
            detalhes=detalhes,
            ip_origem=ip_origem
        )
        db.session.add(audit_entry)
        db.session.commit()
        return audit_entry
    except Exception as e:
        db.session.rollback()
        # Não interrompe a requisição principal caso ocorra falha ao gravar log
        return None
