import os
from pathlib import Path
from dotenv import load_dotenv

from urllib.parse import quote_plus

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def build_database_uri(default_sqlite_name: str) -> str:
    """Monta e sanitiza a URI de conexão com o banco de dados (MySQL, PostgreSQL ou SQLite)."""
    db_url = os.getenv("DATABASE_URL", "").strip()

    # 1. Se DATABASE_URL estiver configurada explicitamente
    if db_url:
        # Garante driver PyMySQL caso venha 'mysql://'
        if db_url.startswith("mysql://"):
            db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)
        # Compatibilidade com SQLAlchemy 2.x para postgres:// ou postgresql:// garantindo psycopg2
        elif db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return db_url

    # 2. Variáveis granulares de MySQL (MYSQL_HOST, MYSQL_USER, etc.)
    mysql_host = os.getenv("MYSQL_HOST")
    mysql_db = os.getenv("MYSQL_DATABASE") or os.getenv("MYSQL_DB")
    if mysql_host or mysql_db:
        user = os.getenv("MYSQL_USER", "root")
        password = os.getenv("MYSQL_PASSWORD", "")
        host = mysql_host or "localhost"
        port = os.getenv("MYSQL_PORT", "3306")
        db = mysql_db or "gapar_gestao"
        auth = f"{user}:{quote_plus(password)}" if password else user
        return f"mysql+pymysql://{auth}@{host}:{port}/{db}?charset=utf8mb4"

    # 3. Fallback padrão SQLite para dev local caso nenhuma variável de banco seja informada
    return f"sqlite:///{BASE_DIR / default_sqlite_name}"


class Config:
    """Configurações base da aplicação GAPAR Gestão."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-chave-secreta-padrao-gapar")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Engine Options para estabilidade e pooling de conexões MySQL/PostgreSQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,       # Evita erros de desconexão (MySQL server has gone away)
        "pool_recycle": 280,         # Recicla conexões antes do timeout comum de 300s
    }
    
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

    # Cookie de sessão: inacessível a scripts e não enviado em requisições vindas de outros sites
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Login de desenvolvimento (sem Google). Desligado por padrão; só Development/Testing ligam.
    DEV_LOGIN_ENABLED = False

    # Fuso do abrigo: define o "dia atual" do painel Hoje, das prescrições e das baixas.
    # O servidor de produção roda em UTC; vazio = usar o relógio do servidor.
    APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")

    # Fotos dos animais no Supabase Storage (RF06). Sem URL + chave de serviço, as fotos
    # ficam no disco local (UPLOAD_FOLDER). A chave de serviço nunca vai para o navegador.
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "animais")


class DevelopmentConfig(Config):
    """Ambiente de Desenvolvimento."""
    DEBUG = True
    DEV_LOGIN_ENABLED = True
    SQLALCHEMY_DATABASE_URI = build_database_uri("gapar_dev.db")


class TestingConfig(Config):
    """Ambiente de Testes Automatizados."""
    TESTING = True
    DEBUG = True
    DEV_LOGIN_ENABLED = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    # Os testes usam o relógio da máquina e nunca falam com o Supabase, mesmo que o .env tenha a chave.
    APP_TIMEZONE = ""
    SUPABASE_URL = ""
    SUPABASE_SERVICE_ROLE_KEY = ""


class ProductionConfig(Config):
    """Ambiente de Produção (PaaS / Linux)."""
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = build_database_uri("gapar_prod.db")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
