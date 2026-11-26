"""CP-01 · Superfície pública (REQ-01 a REQ-05 de docs/sdd/CP01_NUCLEO_SPEC.md)."""
import pytest
from werkzeug.routing import IntegerConverter

from app.extensions import db
from app.models.whitelist import Whitelist
from app.utils.publico import FLAGS, require_feature


def _url_de_exemplo(app, regra):
    valores = {arg: (1 if isinstance(regra._converters.get(arg), IntegerConverter) else "x")
               for arg in regra.arguments}
    return app.url_map.bind("localhost").build(regra.endpoint, valores, force_external=False)


def _rotas_internas(app):
    for regra in app.url_map.iter_rules():
        if regra.rule.startswith("/api/") and not regra.endpoint.startswith("public."):
            for metodo in sorted(regra.methods - {"HEAD", "OPTIONS"}):
                yield regra, metodo


# REQ-01 ------------------------------------------------------------------------------------

def test_toda_rota_interna_exige_login(app, client):
    rotas = list(_rotas_internas(app))
    assert len(rotas) > 30  # sanidade: o mapa de rotas foi de fato percorrido
    abertas = []
    for regra, metodo in rotas:
        resposta = client.open(_url_de_exemplo(app, regra), method=metodo, json={})
        if resposta.status_code != 401:
            abertas.append(f"{metodo} {regra.rule} -> {resposta.status_code}")
    assert not abertas, "Rotas internas respondendo sem login: " + "; ".join(abertas)


def test_existe_ao_menos_uma_rota_publica(app):
    assert any(r.endpoint.startswith("public.") for r in app.url_map.iter_rules())


# REQ-02 ------------------------------------------------------------------------------------

def test_publico_sem_login(client):
    resposta = client.get("/api/public/config")
    assert resposta.status_code == 200


def test_publico_com_sessao_revogada_nao_da_403(app, vol_client):
    from flask import g
    Whitelist.query.filter_by(email="vol@gapar.org.br").update({"is_active": False})
    db.session.commit()
    # O fixture mantém um único app context e o Flask-Login cacheia a usuária em `g`
    # (em produção cada requisição tem o próprio contexto); limpamos como em test_auth.py.
    g.pop("_login_user", None)
    assert vol_client.get("/api/public/config").status_code == 200
    # A rota interna continua bloqueando a sessão revogada (RN14)
    g.pop("_login_user", None)
    assert vol_client.get("/api/animais").status_code == 403


@pytest.mark.parametrize("logado", [False, True])
def test_publico_sem_set_cookie_nem_vary_cookie(app, client, admin_client, logado):
    c = admin_client if logado else client
    resposta = c.get("/api/public/config")
    assert resposta.status_code == 200
    assert "Set-Cookie" not in resposta.headers
    assert "cookie" not in (resposta.headers.get("Vary") or "").lower()


def test_rota_interna_continua_gravando_sessao(app, client):
    from app.models.user import User
    db.session.add(Whitelist(email="nova@gapar.org.br", role="Voluntaria", is_active=True))
    db.session.add(User(email="nova@gapar.org.br", name="Nova", role="Voluntaria"))
    db.session.commit()
    resposta = client.post("/auth/dev-login", json={"email": "nova@gapar.org.br"})
    assert resposta.status_code == 200
    assert "Set-Cookie" in resposta.headers  # a interface de sessão só muda o comportamento público


# REQ-03 ------------------------------------------------------------------------------------

@pytest.mark.parametrize("caminho", [
    "/api/public//config",
    "/api/public/../public/config",
    "/api/public/rota-que-nao-existe",
])
def test_caminho_malformado_nao_e_publico(client, caminho):
    assert client.get(caminho).status_code == 401


# REQ-04 ------------------------------------------------------------------------------------

def test_config_publica_contrato(client):
    resposta = client.get("/api/public/config")
    corpo = resposta.get_json()
    assert set(corpo) == {"flags", "turnstile_site_key", "whatsapp_adocao"}
    assert set(corpo["flags"]) == set(FLAGS)
    assert resposta.headers["Cache-Control"].startswith("public")
    assert "max-age=" in resposta.headers["Vercel-CDN-Cache-Control"]


def test_flags_padrao_desligadas(client):
    corpo = client.get("/api/public/config").get_json()
    assert all(valor is False for valor in corpo["flags"].values())
    assert corpo["turnstile_site_key"] is None and corpo["whatsapp_adocao"] is None


def test_flag_ligada_por_ambiente(app, client):
    app.config["FEATURES"] = {**app.config["FEATURES"], "vitrine": True}
    app.config["PUBLIC_WHATSAPP_ADOCAO"] = "+55 (41) 99999-0000"
    corpo = client.get("/api/public/config").get_json()
    assert corpo["flags"]["vitrine"] is True and corpo["flags"]["mapa"] is False
    assert corpo["whatsapp_adocao"] == "5541999990000"


def test_flag_lida_do_ambiente(monkeypatch):
    from app import config as modulo_config
    monkeypatch.setenv("FEATURE_ESTOQUE", "true")
    monkeypatch.setenv("FEATURE_MAPA", "talvez")
    assert modulo_config._flag_do_ambiente("estoque") is True
    assert modulo_config._flag_do_ambiente("mapa") is False
    assert modulo_config._flag_do_ambiente("vitrine") is False


# REQ-05 ------------------------------------------------------------------------------------

def test_require_feature(app):
    @require_feature("estoque")
    def rota():
        return "ok"

    with app.test_request_context("/api/estoque"):
        _, status = rota()
        assert status == 404
        app.config["FEATURES"] = {**app.config["FEATURES"], "estoque": True}
        assert rota() == "ok"


def test_require_feature_recusa_flag_desconhecida():
    with pytest.raises(ValueError):
        require_feature("flag-inexistente")
