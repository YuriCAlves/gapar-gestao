from flask_login import UserMixin
from app.extensions import db, login_manager
from .base import utcnow, sql_in, PERFIS


class User(UserMixin, db.Model):
    """Modelo de Usuária e controle de Whitelist (RF01, RF02, RF03, RF04, RN12, RN14)."""
    __tablename__ = "users"
    __table_args__ = (
        db.CheckConstraint(sql_in("role", PERFIS), name="ck_users_role"),
    )

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=True)
    google_id = db.Column(db.String(120), unique=True, nullable=True)
    
    # Roles: 'Administradora' ou 'Voluntaria' (RF03, RN13)
    role = db.Column(db.String(20), nullable=False, default="Voluntaria")
    
    # Whitelist status (RN14: Se False, revoga imediatamente no próximo request)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Tokens do Google criptografados em repouso (RNF08)
    google_access_token = db.Column(db.Text, nullable=True)
    google_refresh_token = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    @property
    def is_admin(self):
        return self.role == "Administradora"

    @property
    def active(self):
        """Compatibilidade para acessos como current_user.active."""
        return self.is_active

    def set_google_tokens(self, access_token=None, refresh_token=None):
        """Cifra e armazena tokens no banco (RNF08)."""
        from app.utils.crypto import encrypt_token
        if access_token is not None:
            self.google_access_token = encrypt_token(access_token)
        if refresh_token is not None:
            self.google_refresh_token = encrypt_token(refresh_token)

    def get_decrypted_access_token(self):
        """Retorna o access_token decifrado em memória (RNF08)."""
        from app.utils.crypto import decrypt_token
        return decrypt_token(self.google_access_token)

    def get_decrypted_refresh_token(self):
        """Retorna o refresh_token decifrado em memória (RNF08)."""
        from app.utils.crypto import decrypt_token
        return decrypt_token(self.google_refresh_token)

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
    """Carrega a usuária e revalida a Whitelist a cada requisição (RN12, RN14)."""
    from flask import current_app
    from app.models.whitelist import Whitelist

    try:
        user = db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None

    if not user or not user.is_active:
        return None

    email = user.email.strip().lower()
    admin_email = (current_app.config.get("INITIAL_ADMIN_EMAIL") or "").strip().lower()
    if admin_email and email == admin_email:
        return user

    entry = Whitelist.query.filter_by(email=email, is_active=True).first()
    if not entry:
        return None

    user.role = entry.role  # perfil sempre sincronizado com a Whitelist
    return user
