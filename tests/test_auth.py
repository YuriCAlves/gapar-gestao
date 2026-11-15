from unittest.mock import patch

from flask import g

from app.extensions import db
from app.models.user import User
from app.models.whitelist import Whitelist

VERIFY = "app.blueprints.auth.routes.google_id_token.verify_oauth2_token"


def _claims(email, sub="g-123", verified=True):
    return {"email": email, "sub": sub, "name": "Fulana", "email_verified": verified}


def _google_login(client, app, email, **kw):
    app.config["GOOGLE_CLIENT_ID"] = "cid.apps.googleusercontent.com"
    with patch(VERIFY, return_value=_claims(email, **kw)):
        return client.post("/auth/google", json={"credential": "token-falso"})


# --- Google ID Token -------------------------------------------------------

def test_google_exige_token(client):
    assert client.post("/auth/google", json={}).status_code == 400


def test_google_nao_aceita_email_sem_token(client, volunteer_user):
    """Informar só o e-mail (sem ID Token assinado) nunca autentica."""
    resp = client.post("/auth/google", json={"email": "vol@gapar.org.br"})
    assert resp.status_code == 400
    assert client.get("/auth/status").get_json()["autenticado"] is False


def test_google_token_invalido(client, app):
    app.config["GOOGLE_CLIENT_ID"] = "cid"
    with patch(VERIFY, side_effect=ValueError("assinatura inválida")):
        resp = client.post("/auth/google", json={"credential": "x"})
    assert resp.status_code == 401


def test_google_email_nao_verificado(client, app, volunteer_user):
    resp = _google_login(client, app, "vol@gapar.org.br", verified=False)
    assert resp.status_code == 401


def test_google_login_whitelist_ok(client, app, volunteer_user):
    resp = _google_login(client, app, "vol@gapar.org.br")
    assert resp.status_code == 200
    assert client.get("/auth/status").get_json()["autenticado"] is True
    assert User.query.filter_by(email="vol@gapar.org.br").first().google_id == "g-123"


def test_google_login_cria_usuaria_no_primeiro_acesso(client, app):
    db.session.add(Whitelist(email="nova@gapar.org.br", role="Voluntaria"))
    db.session.commit()
    resp = _google_login(client, app, "nova@gapar.org.br")
    assert resp.status_code == 200
    assert User.query.filter_by(email="nova@gapar.org.br").first().role == "Voluntaria"


def test_google_identidade_divergente_bloqueada(client, app, volunteer_user):
    assert _google_login(client, app, "vol@gapar.org.br", sub="g-A").status_code == 200
    client.post("/auth/logout")
    assert _google_login(client, app, "vol@gapar.org.br", sub="g-B").status_code == 403


def test_administradora_inicial_entra_sem_whitelist(client, app):
    app.config["INITIAL_ADMIN_EMAIL"] = "dona@gapar.org.br"
    resp = _google_login(client, app, "dona@gapar.org.br")
    assert resp.status_code == 200
    assert resp.get_json()["usuario"]["role"] == "Administradora"
    assert Whitelist.query.filter_by(email="dona@gapar.org.br").first() is not None


# --- Whitelist (RN12, RN14) ------------------------------------------------

def test_login_bloqueado_fora_whitelist(client, app):
    assert _google_login(client, app, "unknown@gapar.org.br").status_code == 403


def test_login_bloqueado_inativo(client, app, inactive_user):
    assert _google_login(client, app, "inactive@gapar.org.br").status_code == 403


def test_desativacao_imediata_whitelist(client, app, volunteer_user, admin_user):
    assert client.post("/auth/dev-login", json={"email": "vol@gapar.org.br"}).status_code == 200
    assert client.get("/api/admin/nao-aptos").status_code == 403  # logada, mas voluntária

    Whitelist.query.filter_by(email="vol@gapar.org.br").first().is_active = False
    db.session.commit()

    # O fixture mantém um único app context e o Flask-Login cacheia a usuária em `g`;
    # em produção cada requisição tem o próprio contexto, então limpamos o cache aqui.
    g.pop("_login_user", None)

    # Próxima requisição já perde o acesso
    assert client.get("/auth/me").status_code == 401


def test_acesso_diferenciado_admin_vs_voluntaria(client, volunteer_user, admin_user):
    client.post("/auth/dev-login", json={"email": "vol@gapar.org.br"})
    assert client.get("/api/admin/whitelist").status_code == 403
    client.post("/auth/logout")

    client.post("/auth/dev-login", json={"email": "admin@gapar.org.br"})
    assert client.get("/api/admin/whitelist").status_code == 200


def test_admin_gerencia_whitelist(client, admin_user):
    client.post("/auth/dev-login", json={"email": "admin@gapar.org.br"})
    r = client.post("/api/admin/whitelist", json={"email": "Nova@Gapar.org.br"})
    assert r.status_code == 201
    entry_id = r.get_json()["usuario"]["id"]
    assert client.post("/api/admin/whitelist", json={"email": "nova@gapar.org.br"}).status_code == 400
    r2 = client.patch(f"/api/admin/whitelist/{entry_id}/status", json={"is_active": False})
    assert r2.get_json()["usuario"]["is_active"] is False


# --- dev-login -------------------------------------------------------------

def test_dev_login_desligado_em_producao(client, app, admin_user):
    app.config["DEV_LOGIN_ENABLED"] = False
    assert client.post("/auth/dev-login", json={"email": "admin@gapar.org.br"}).status_code == 404


def test_dev_login_respeita_whitelist(client):
    assert client.post("/auth/dev-login", json={"email": "ninguem@gapar.org.br"}).status_code == 403


# --- Auditoria e tokens ----------------------------------------------------

def test_login_gera_auditoria(client, admin_user):
    from app.models.audit import AuditLog
    client.post("/auth/dev-login", json={"email": "admin@gapar.org.br"})
    assert AuditLog.query.filter_by(acao="LOGIN_SUCESSO").count() == 1


def test_criptografia_tokens_google(app, volunteer_user):
    u = User.query.filter_by(email="vol@gapar.org.br").first()
    u.set_google_tokens("access123", "refresh456")
    db.session.commit()
    raw = db.session.execute(
        db.text("SELECT google_access_token FROM users WHERE id=:id"), {"id": u.id}
    ).scalar()
    assert raw != "access123"
    assert u.get_decrypted_access_token() == "access123"


# --- Fluxo por redirecionamento (aberto pelo navegador) ----------------------

def test_callback_com_state_invalido_volta_para_login(client):
    resp = client.get("/auth/callback?state=forjado&code=x")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/entrar?erro=google")


def test_login_info_informa_opcoes(client, app):
    app.config.update(GOOGLE_CLIENT_ID="cid", GOOGLE_CLIENT_SECRET="segredo")
    corpo = client.get("/auth/login").get_json()
    assert corpo["dev_login"] is True and corpo["google_configurado"] is True
