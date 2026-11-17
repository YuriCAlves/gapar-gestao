from flask import current_app, has_request_context, request
from flask_login import current_user
from app.extensions import db
from app.models.audit import AuditLog
from app.utils.validation import column_length


def log_audit_event(acao: str, entidade: str, entidade_id: int | None = None, detalhes: str | None = None,
                    user=None, commit: bool = True):
    """Registra evento na trilha de auditoria inviolável (RF24, RN16).

    Há dois modos de uso:

    - `commit=False`: o registro entra na transação em andamento e é gravado junto com a alteração
      que ele descreve, no mesmo commit de quem chamou. É o modo usado nas inclusões, alterações e
      desativações: ou as duas coisas são gravadas, ou nenhuma. Erros sobem para quem chamou.
    - `commit=True` (padrão): grava sozinho, para eventos que não acompanham alteração de dados
      (login recusado, tentativa de adoção bloqueada). Uma falha aqui não derruba a requisição, mas
      fica registrada no log da aplicação em vez de sumir em silêncio.
    """
    if not commit:
        entry = _build_entry(acao, entidade, entidade_id, detalhes, user)
        db.session.add(entry)
        return entry

    try:
        entry = _build_entry(acao, entidade, entidade_id, detalhes, user)
        db.session.add(entry)
        db.session.commit()
        return entry
    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Falha ao gravar a trilha de auditoria (acao=%s, entidade=%s, entidade_id=%s).",
            acao, entidade, entidade_id,
        )
        return None


def _build_entry(acao, entidade, entidade_id, detalhes, user):
    active_user = user if user else (current_user if current_user and current_user.is_authenticated else None)
    limite_acao = column_length(AuditLog, "acao")
    return AuditLog(
        user_id=active_user.id if active_user else None,
        user_email=active_user.email if active_user else None,
        acao=acao[:limite_acao] if limite_acao else acao,
        entidade=entidade,
        entidade_id=entidade_id,
        detalhes=detalhes,
        ip_origem=_client_ip(),
    )


def _client_ip():
    """IP de origem. Atrás do proxy da hospedagem, o endereço real vem em X-Forwarded-For."""
    if not has_request_context():
        return None
    encaminhado = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    ip = encaminhado or request.remote_addr
    return ip[:45] if ip else None
