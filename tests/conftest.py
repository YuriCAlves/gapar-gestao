import os
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.utils.crypto import encrypt_token


@pytest.fixture
def app():
    os.environ["FLASK_ENV"] = "testing"
    app = create_app("default")
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


@pytest.fixture
def admin_user(app):
    u = User(email="admin@gapar.org.br", name="Admin", role="Administradora", is_active=True)
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def volunteer_user(app):
    u = User(email="vol@gapar.org.br", name="Vol", role="Voluntaria", is_active=True)
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def inactive_user(app):
    u = User(email="inactive@gapar.org.br", name="Inactive", role="Voluntaria", is_active=False)
    db.session.add(u)
    db.session.commit()
    return u
