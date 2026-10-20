from datetime import datetime
from app.extensions import db


class AuditLog(db.Model):
    """Trilha Inviolável de Auditoria (RF24, RN16).
    Registra toda inclusão, alteração ou desativação lógica com usuária, data e hora.
    """
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    user_email = db.Column(db.String(120), nullable=True) # Mantido caso a usuária seja removida
    
    acao = db.Column(db.String(50), nullable=False) # 'INSERCAO', 'EDICAO', 'DESATIVACAO', 'ADOCAO', etc.
    entidade = db.Column(db.String(50), nullable=False, index=True) # 'Animal', 'Prescription', 'User', etc.
    entidade_id = db.Column(db.Integer, nullable=True)
    
    detalhes = db.Column(db.Text, nullable=True) # JSON ou resumo das alterações
    ip_origem = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

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
