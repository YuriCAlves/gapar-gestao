from app.extensions import db
from .base import utcnow


class Announcement(db.Model):
    """Comunicados oficiais da Diretoria e Relatos de Turno (Mural GAPAR)."""
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)  # 'DIRETORIA' ou 'TURNO'
    titulo = db.Column(db.String(150), nullable=True)
    conteudo = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(30), nullable=False, default="Geral")
    is_urgente = db.Column(db.Boolean, default=False, nullable=False)
    is_fixado = db.Column(db.Boolean, default=False, nullable=False)

    autor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("animals.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    acks = db.relationship("AnnouncementAck", backref="announcement", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "tipo": self.tipo,
            "titulo": self.titulo,
            "conteudo": self.conteudo,
            "categoria": self.categoria,
            "is_urgente": self.is_urgente,
            "is_fixado": self.is_fixado,
            "autor_id": self.autor_id,
            "animal_id": self.animal_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AnnouncementAck(db.Model):
    """Confirmações de presença em convocações ou ciência em comunicados."""
    __tablename__ = "announcement_acks"
    __table_args__ = (
        # Cada usuária confirma um aviso uma única vez (o índice da UNIQUE cobre a FK announcement_id)
        db.UniqueConstraint("announcement_id", "user_id", name="uq_announcement_acks_aviso_usuaria"),
    )

    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo_confirmacao = db.Column(db.String(20), default="CIENTE")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "announcement_id": self.announcement_id,
            "user_id": self.user_id,
            "tipo_confirmacao": self.tipo_confirmacao,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
