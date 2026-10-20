import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Configurações base da aplicação GAPAR Gestão."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-chave-secreta-padrao-gapar")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Uploads e diretórios de armazenamento
    UPLOAD_FOLDER = os.path.join(BASE_DIR, os.getenv("UPLOAD_FOLDER", "app/static/uploads"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))  # 10 MB
    MAX_IMAGE_SIZE_KB = 300  # RNF02: compressão de fotos no servidor para < 300 KB
    
    # Google OAuth 2.0
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_DISCOVERY_URL = os.getenv(
        "GOOGLE_DISCOVERY_URL",
        "https://accounts.google.com/.well-known/openid-configuration"
    )
    
    # Administradora Inicial (RN13)
    INITIAL_ADMIN_EMAIL = os.getenv("INITIAL_ADMIN_EMAIL", "admin@gapar.org.br")


class DevelopmentConfig(Config):
    """Ambiente de Desenvolvimento."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'gapar_dev.db'}")


class TestingConfig(Config):
    """Ambiente de Testes Automatizados."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Ambiente de Produção (PaaS / Linux)."""
    DEBUG = False
    TESTING = False
    # Converte postgres:// do Heroku/Render para postgresql:// exigido pelo SQLAlchemy 2.x
    _db_url = os.getenv("DATABASE_URL", "")
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url or f"sqlite:///{BASE_DIR / 'gapar_prod.db'}"


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
