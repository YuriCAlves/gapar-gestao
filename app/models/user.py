from datetime import datetime
from flask_login import UserMixin
from app.extensions import db, login_manager
from flask import current_app


class User(UserMixin, db.Model):
    """Modelo de Usuária e controle de Whitelist (RF01, RF02, RF03, RF04, RN12, RN14)."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=True)
    google_id = db.Column(db.String(120), unique=True, nullable=True)
    
    # Roles: 'Administradora' ou 'Voluntaria' (RF03, RN13)
    role = db.Column(db.String(20), nullable=False, default="Voluntaria")
    
    # Whitelist status (RN14: Se False, revoga imediatamente no próximo request)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Tokens do Google criptografados (RNF08)
    google_access_token = db.Column(db.Text, nullable=True)
    google_refresh_token = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @property
    def is_admin(self):
        return self.role == "Administradora"

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@login_manager.user_loader
def load_user(user_id):
    """Carrega a usuária e revalida sua autorização em cada request."""
    try:
        user = db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None

    if not user or not user.is_active:
        return None

    admin_email = (
        current_app.config.get("INITIAL_ADMIN_EMAIL") or ""
    ).strip().lower()

    if user.email.lower() == admin_email:
        return user

    # Importação local para evitar dependência circular.
    from app.models.whitelist import Whitelist

    authorization = Whitelist.query.filter_by(
        email=user.email.lower(),
        is_active=True
    ).first()

    if not authorization:
        return None

    user.role = authorization.role
    return user