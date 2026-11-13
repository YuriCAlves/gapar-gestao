import os
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.whitelist import Whitelist
from app.utils.crypto import encrypt_token


@pytest.fixture
def app():
    os.environ["FLASK_ENV"] = "testing"
    app = create_app("testing")
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _make_user(email, name, role, active=True):
    db.session.add(Whitelist(email=email, role=role, is_active=active))
    u = User(email=email, name=name, role=role, is_active=True)
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def admin_user(app):
    return _make_user("admin@gapar.org.br", "Admin", "Administradora")


@pytest.fixture
def volunteer_user(app):
    return _make_user("vol@gapar.org.br", "Vol", "Voluntaria")


@pytest.fixture
def inactive_user(app):
    return _make_user("inactive@gapar.org.br", "Inactive", "Voluntaria", active=False)


def _logged_client(app, email, name, role):
    _make_user(email, name, role)
    c = app.test_client()
    assert c.post("/auth/dev-login", json={"email": email}).status_code == 200
    return c


@pytest.fixture
def vol_client(app):
    """Cliente autenticado como Voluntária."""
    return _logged_client(app, "vol@gapar.org.br", "Vol", "Voluntaria")


@pytest.fixture
def admin_client(app):
    """Cliente autenticado como Administradora."""
    return _logged_client(app, "admin@gapar.org.br", "Admin", "Administradora")
