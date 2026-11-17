"""Checkpoint 7: a configuração de produção recusa subir insegura e se adapta ao proxy da Vercel."""
import pytest
from werkzeug.middleware.proxy_fix import ProxyFix

from app import create_app
from app.config import ProductionConfig

CHAVE_FORTE = "x" * 48
PG = "postgresql+psycopg2://u:p@db.exemplo.supabase.co:6543/postgres"


@pytest.fixture
def producao_valida(monkeypatch):
    """Ambiente de produção completo, sem tocar no .env real nem no banco."""
    monkeypatch.setenv("SECRET_KEY", CHAVE_FORTE)
    monkeypatch.setenv("INITIAL_ADMIN_EMAIL", "admin@gapar.org.br")
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", CHAVE_FORTE)
    monkeypatch.setattr(ProductionConfig, "SQLALCHEMY_DATABASE_URI", PG)
    monkeypatch.setattr(ProductionConfig, "GOOGLE_CLIENT_ID", "id.apps.googleusercontent.com")
    monkeypatch.setattr(ProductionConfig, "GOOGLE_CLIENT_SECRET", "segredo")
    monkeypatch.setattr(ProductionConfig, "UPLOAD_FOLDER", "")
    monkeypatch.setattr(ProductionConfig, "PUBLIC_BASE_URL", "")


def test_producao_completa_sobe_segura(producao_valida):
    app = create_app("production")
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["REMEMBER_COOKIE_SECURE"] is True
    assert app.config["DEV_LOGIN_ENABLED"] is False
    assert isinstance(app.wsgi_app, ProxyFix)


@pytest.mark.parametrize("ajuste, trecho", [
    (lambda mp: mp.delenv("SECRET_KEY"), "SECRET_KEY"),
    (lambda mp: mp.setattr(ProductionConfig, "SECRET_KEY", "curta"), "SECRET_KEY"),
    (lambda mp: mp.setattr(ProductionConfig, "SQLALCHEMY_DATABASE_URI", "sqlite:///gapar_prod.db"), "DATABASE_URL"),
    (lambda mp: mp.setattr(ProductionConfig, "GOOGLE_CLIENT_SECRET", ""), "GOOGLE_CLIENT"),
    (lambda mp: mp.delenv("INITIAL_ADMIN_EMAIL"), "INITIAL_ADMIN_EMAIL"),
])
def test_producao_incompleta_falha_cedo(producao_valida, monkeypatch, ajuste, trecho):
    ajuste(monkeypatch)
    with pytest.raises(RuntimeError, match=trecho):
        create_app("production")


def test_callback_do_google_usa_https_atras_do_proxy(producao_valida):
    app = create_app("production")
    resp = app.test_client().get(
        "/auth/google",
        headers={"X-Forwarded-Proto": "https", "X-Forwarded-Host": "gapar.vercel.app"},
    )
    assert resp.status_code == 302
    assert "redirect_uri=https%3A%2F%2Fgapar.vercel.app%2Fauth%2Fcallback" in resp.headers["Location"]


def test_dev_login_nao_existe_em_producao(producao_valida):
    app = create_app("production")
    assert app.test_client().post("/auth/dev-login", json={}).status_code == 404


def test_foto_sem_storage_remoto_e_recusada_em_producao(producao_valida, monkeypatch):
    """Sem Supabase Storage, a foto não pode ir para o disco efêmero da Vercel (seria perdida)."""
    from app.services.storage import save_photo
    from app.utils.validation import ApiError

    monkeypatch.setattr(ProductionConfig, "SUPABASE_SERVICE_ROLE_KEY", "")
    app = create_app("production")
    with app.app_context(), pytest.raises(ApiError) as erro:
        save_photo(b"jpeg", "x.jpg")
    assert erro.value.status == 503
