from datetime import datetime
from app.extensions import db


class NonEligiblePerson(db.Model):
    """Lista Sigilosa e Restrita de Pessoas Não Aptas a Adotar (RF22, RN15).
    Acesso restrito exclusiva e unicamente à Administradora.
    """
    __tablename__ = "non_eligible_people"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False, index=True)
    cpf = db.Column(db.String(20), nullable=True, index=True)
    telefone = db.Column(db.String(30), nullable=True)
    motivo_impedimento = db.Column(db.Text, nullable=False) # Histórico de maus-tratos ou negligência
    
    # Registrado por quem (auditoria interna)
    cadastrado_por_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "cpf": self.cpf,
            "telefone": self.telefone,
            "motivo_impedimento": self.motivo_impedimento,
            "created_at": self.created_at.isoformat()
        }
