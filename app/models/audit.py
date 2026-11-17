from app.extensions import db
from .base import utcnow, tornar_imutavel


@tornar_imutavel
class AuditLog(db.Model):
    """Trilha Inviolável de Auditoria (RF24, RN16).
    Registra toda inclusão, alteração ou desativação lógica com usuária, data e hora.

    Imutável: só aceita inclusão. No PostgreSQL, gatilhos rejeitam UPDATE, DELETE e TRUNCATE
    (migração 0002), sem exceção. Por isso a ação `ON DELETE SET NULL` de `user_id` nunca chega
    a ser aplicada: apagar uma usuária que tenha registros de auditoria é recusado pelo banco.
    Isso é coerente com o sistema, em que usuárias nunca são excluídas, só desativadas na
    Whitelist (RN14); `user_email` guarda o e-mail da época do registro.
    """
    __tablename__ = "audit_logs"
    __table_args__ = (
        # Consulta da auditoria por tipo de ação, mais recentes primeiro
        db.Index("ix_audit_logs_acao_created_at", "acao", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_email = db.Column(db.String(120), nullable=True) # E-mail da usuária no momento do registro
    
    acao = db.Column(db.String(50), nullable=False) # 'INSERCAO', 'EDICAO', 'DESATIVACAO', 'ADOCAO', etc.
    entidade = db.Column(db.String(50), nullable=False, index=True) # 'Animal', 'Prescription', 'User', etc.
    entidade_id = db.Column(db.Integer, nullable=True)
    
    detalhes = db.Column(db.Text, nullable=True) # JSON ou resumo das alterações
    ip_origem = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "acao": self.acao,
            "entidade": self.entidade,
            "entidade_id": self.entidade_id,
            "detalhes": self.detalhes,
            "created_at": self.created_at.isoformat()
        }
