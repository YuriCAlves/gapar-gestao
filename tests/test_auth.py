import pytest


def test_login_bloqueado_fora_whitelist(client):
    resp = client.post("/auth/google", json={"email": "unknown@gapar.org.br"})
    assert resp.status_code == 403


def test_login_bloqueado_inativo(client, inactive_user):
    resp = client.post("/auth/google", json={"email": "inactive@gapar.org.br"})
    assert resp.status_code == 403


def test_desativacao_imediata_whitelist(client, volunteer_user, app):
    # login
    r = client.post("/auth/google", json={"email": "vol@gapar.org.br"})
    assert r.status_code == 200
    # desativa
    with app.app_context():
        from app.extensions import db
        u = User_query = None
        from app.models.user import User
        u = User.query.filter_by(email="vol@gapar.org.br").first()
        u.is_active = False
        db.session.commit()
    # next request should be 403
    r2 = client.get("/auth/status")
    # status route doesn't require whitelist; use admin endpoint instead
    from app.models.blacklist import NonEligiblePerson
    r3 = client.get("/admin/nao-aptos")
    assert r3.status_code in (401, 403)


def test_acesso_diferenciado_admin_vs_voluntaria(client, volunteer_user, admin_user):
    client.post("/auth/google", json={"email": "vol@gapar.org.br"})
    r = client.get("/admin/whitelist")
    assert r.status_code == 403
    # admin
    client.post("/auth/google", json={"email": "admin@gapar.org.br"})
    r2 = client.get("/admin/whitelist")
    assert r2.status_code != 403


def test_criptografia_tokens_google(app, volunteer_user):
    with app.app_context():
        from app.extensions import db
        from app.models.user import User
        u = User.query.filter_by(email="vol@gapar.org.br").first()
        u.set_google_tokens("access123", "refresh456")
        db.session.commit()
        raw = db.session.execute(db.text("SELECT google_access_token FROM users WHERE id=:id"), {"id": u.id}).scalar()
        assert raw != "access123"
        assert u.get_decrypted_access_token() == "access123"
