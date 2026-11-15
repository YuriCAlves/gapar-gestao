from app.extensions import db
from .base import utcnow, sql_in, PERFIS


class Whitelist(db.Model):
    """E-mails autorizados a acessar o GAPAR (RF02, RN12, RN14).

    É a fonte de verdade da autorização: a conta em `users` só existe depois do
    primeiro login e é revalidada contra esta tabela a cada requisição.
    """
    __tablename__ = "whitelist"
    __table_args__ = (
        db.CheckConstraint(sql_in("role", PERFIS), name="ck_whitelist_role"),
    )

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False, default="Voluntaria")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
