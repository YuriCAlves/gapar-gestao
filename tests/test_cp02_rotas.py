"""CP-02 · Rotas da vitrine (REQ-24, 27, 28, 29, 30) de docs/sdd/CP02_VITRINE_SPEC.md.

A camada de dados (REQ-21 a 23, 25, 26) é testada em tests/test_cp02_vitrine.py.
"""
import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from flask import Blueprint, g
from sqlalchemy import event

from app.extensions import db
from app.models import AuditLog
from app.models.animal import Animal
from app.models.whitelist import Whitelist
from app.utils.slug import SLUG_PUBLICO_RE, gerar_slug_publico

RAIZ = Path(__file__).resolve().parent.parent
VERCEL_JSON = RAIZ / "vercel.json"
CHAVES_ANIMAL_PUBLICO = {"slug", "nome", "sexo", "porte", "idade_estimada", "raca", "pelagem", "foto_url",
                         "is_castrado", "is_idoso", "descricao_publica", "candidaturas_pausadas"}


def _animal(nome="Mel", status="disponível", publicado=False, criado=None, **extra):
    animal = Animal(nome=nome, sexo="Fêmea", porte="Pequeno", status_operacional=status,
                    data_entrada=date.today(), local_resgate="Rua Interna 123", **extra)
    if criado is not None:
        animal.created_at = criado
    if publicado:
        animal.is_publicado = True
        animal.slug_publico = gerar_slug_publico(nome)
    db.session.add(animal)
    db.session.commit()
    return animal


def _recarregar(animal_id):
    db.session.expire_all()
    return db.session.get(Animal, animal_id)


@pytest.fixture
def vitrine_ligada(app):
    app.config["FEATURES"] = {**app.config["FEATURES"], "vitrine": True}


@pytest.fixture
def contar_consultas(app):
    consultas = []

    def _anotar(_conn, _cursor, sql, *_args, **_kwargs):
        consultas.append(sql)

    event.listen(db.engine, "before_cursor_execute", _anotar)
    yield consultas
    event.remove(db.engine, "before_cursor_execute", _anotar)


# REQ-24 · PATCH /api/animais/<id>/vitrine -----------------------------------------------------

def _patch(c, animal_id, **corpo):
    return c.patch(f"/api/animais/{animal_id}/vitrine", json=corpo)


def test_patch_vitrine_voluntaria_403(app, vol_client):
    animal = _animal()
    resposta = _patch(vol_client, animal.id, publicar=True)
    assert resposta.status_code == 403
    assert _recarregar(animal.id).is_publicado is False


def test_patch_vitrine_sem_login_401(app, client):
    animal = _animal()
    assert _patch(client, animal.id, publicar=True).status_code == 401


@pytest.mark.parametrize("status", ["em acolhimento", "em tratamento", "lar temporário", "óbito"])
def test_patch_vitrine_status_errado_422(app, admin_client, status):
    animal = _animal(status=status)
    resposta = _patch(admin_client, animal.id, publicar=True)
    assert resposta.status_code == 422
    assert "disponível" in resposta.get_json()["mensagem"]
    recarregado = _recarregar(animal.id)
    assert recarregado.is_publicado is False and recarregado.slug_publico is None


def test_patch_vitrine_animal_excluido_404(app, admin_client):
    animal = _animal(is_deleted=True)
    assert _patch(admin_client, animal.id, publicar=True).status_code == 404


def test_patch_vitrine_gera_slug_na_primeira_publicacao(app, admin_client):
    animal = _animal(nome="Mel Ágata")
    resposta = _patch(admin_client, animal.id, publicar=True, descricao_publica="  Dócil e brincalhona.  ",
                      pausar_candidaturas=True)
    assert resposta.status_code == 200
    ficha = resposta.get_json()["animal"]
    assert ficha["id"] == animal.id  # resposta é a ficha interna (to_dict), como o front espera
    assert ficha["is_publicado"] is True and ficha["pausar_candidaturas"] is True
    assert ficha["descricao_publica"] == "Dócil e brincalhona."
    slug = ficha["slug_publico"]
    assert SLUG_PUBLICO_RE.fullmatch(slug) and re.fullmatch(r"mel-agata-[a-z0-9]{6}", slug)
    assert str(animal.id) not in slug.split("-")[:-1]


def test_patch_vitrine_slug_mantido_ao_despublicar_e_republicar(app, admin_client):
    animal = _animal()
    slug = _patch(admin_client, animal.id, publicar=True).get_json()["animal"]["slug_publico"]
    despublicado = _patch(admin_client, animal.id, publicar=False).get_json()["animal"]
    assert despublicado["is_publicado"] is False and despublicado["slug_publico"] == slug
    republicado = _patch(admin_client, animal.id, publicar=True).get_json()["animal"]
    assert republicado["is_publicado"] is True and republicado["slug_publico"] == slug


def test_patch_vitrine_descricao_limite(app, admin_client):
    animal = _animal()
    resposta = _patch(admin_client, animal.id, publicar=True, descricao_publica="x" * 601)
    assert resposta.status_code == 400
    assert "600" in resposta.get_json()["mensagem"]
    assert _recarregar(animal.id).is_publicado is False
    assert _patch(admin_client, animal.id, publicar=True, descricao_publica="x" * 600).status_code == 200
    # null (ou vazio) limpa a descrição
    assert _patch(admin_client, animal.id, publicar=True, descricao_publica=None).get_json()["animal"][
        "descricao_publica"] is None


@pytest.mark.parametrize("corpo", [
    {}, {"publicar": "sim"}, {"publicar": 1}, {"publicar": None},
    {"publicar": True, "pausar_candidaturas": "talvez"}, {"publicar": True, "descricao_publica": ["x"]},
])
def test_patch_vitrine_corpo_invalido_400(app, admin_client, corpo):
    animal = _animal()
    assert admin_client.patch(f"/api/animais/{animal.id}/vitrine", json=corpo).status_code == 400
    assert _recarregar(animal.id).is_publicado is False


def test_patch_vitrine_auditoria_sem_descricao(app, admin_client):
    animal = _animal()
    texto = "Texto secreto da descricao publica"
    assert _patch(admin_client, animal.id, publicar=True, descricao_publica=texto).status_code == 200
    registros = AuditLog.query.filter_by(entidade="Animal", entidade_id=animal.id, acao="VITRINE_ATUALIZADA").all()
    assert len(registros) == 1
    detalhes = registros[0].detalhes
    assert texto not in detalhes and "secreto" not in detalhes
    assert "Mel" not in detalhes  # só o id e os campos
    assert {"is_publicado", "descricao_publica", "slug_publico"} <= set(re.findall(r"[a-z_]+", detalhes))
    assert registros[0].user_email == "admin@gapar.org.br"


def test_patch_vitrine_sem_mudanca_nao_audita(app, admin_client):
    animal = _animal()
    assert _patch(admin_client, animal.id, publicar=False).status_code == 200
    assert AuditLog.query.filter_by(acao="VITRINE_ATUALIZADA").count() == 0


def test_patch_vitrine_retenta_colisao_de_slug(app, admin_client, monkeypatch):
    from app.controllers import animals_controller
    ocupado = _animal(nome="Mel", publicado=True)
    sequencia = iter([ocupado.slug_publico, ocupado.slug_publico, "mel-novo01"])
    monkeypatch.setattr(animals_controller, "gerar_slug_publico", lambda _nome: next(sequencia))
    animal = _animal(nome="Mel")
    resposta = _patch(admin_client, animal.id, publicar=True, descricao_publica="Oi")
    assert resposta.status_code == 200
    assert resposta.get_json()["animal"]["slug_publico"] == "mel-novo01"
    recarregado = _recarregar(animal.id)
    assert recarregado.is_publicado is True and recarregado.descricao_publica == "Oi"
    assert _recarregar(ocupado.id).slug_publico == ocupado.slug_publico


def test_patch_vitrine_colisao_persistente_409(app, admin_client, monkeypatch):
    from app.controllers import animals_controller
    ocupado = _animal(nome="Mel", publicado=True)
    monkeypatch.setattr(animals_controller, "gerar_slug_publico", lambda _nome: ocupado.slug_publico)
    animal = _animal(nome="Mel")
    assert _patch(admin_client, animal.id, publicar=True).status_code == 409
    recarregado = _recarregar(animal.id)
    assert recarregado.is_publicado is False and recarregado.slug_publico is None


# REQ-27 · GET /api/public/animais ------------------------------------------------------------

def _sem_cookie(resposta):
    return "Set-Cookie" not in resposta.headers and "cookie" not in (resposta.headers.get("Vary") or "").lower()


def test_vitrine_lista_filtro(app, client, vitrine_ligada):
    publicado = _animal(nome="Mel", publicado=True)
    _animal(nome="Nao Publicado")
    _animal(nome="Em Tratamento", status="em tratamento")
    excluido = _animal(nome="Excluido", publicado=True)
    excluido.is_deleted = True
    db.session.commit()
    corpo = client.get("/api/public/animais").get_json()
    assert [a["slug"] for a in corpo["animais"]] == [publicado.slug_publico]
    assert corpo["total"] == 1 and corpo["tem_mais"] is False
    assert set(corpo["animais"][0]) == CHAVES_ANIMAL_PUBLICO
    assert "Rua Interna" not in json.dumps(corpo, ensure_ascii=False)


def test_vitrine_lista_paginacao_e_ordem(app, client, vitrine_ligada, contar_consultas):
    base = datetime(2026, 1, 1)
    animais = [_animal(nome=f"Cao {i}", publicado=True, criado=base + timedelta(days=i)) for i in range(13)]
    esperado = [a.slug_publico for a in reversed(animais)]  # mais recentes primeiro
    contar_consultas.clear()
    pagina1 = client.get("/api/public/animais").get_json()
    assert len(contar_consultas) == 2  # a página e o total: sem N+1
    assert set(pagina1) == {"animais", "pagina", "por_pagina", "total", "tem_mais"}
    assert (pagina1["pagina"], pagina1["por_pagina"], pagina1["total"], pagina1["tem_mais"]) == (1, 12, 13, True)
    assert [a["slug"] for a in pagina1["animais"]] == esperado[:12]
    pagina2 = client.get("/api/public/animais?pagina=2").get_json()
    assert (pagina2["pagina"], pagina2["total"], pagina2["tem_mais"]) == (2, 13, False)
    assert [a["slug"] for a in pagina2["animais"]] == esperado[12:]
    pagina3 = client.get("/api/public/animais?pagina=3").get_json()
    assert pagina3["animais"] == [] and pagina3["tem_mais"] is False
    assert client.get("/api/public/animais?pagina=500").status_code == 200


def test_vitrine_lista_doze_exatos_sem_mais(app, client, vitrine_ligada):
    for i in range(12):
        _animal(nome=f"Cao {i}", publicado=True)
    corpo = client.get("/api/public/animais").get_json()
    assert len(corpo["animais"]) == 12 and corpo["tem_mais"] is False


@pytest.mark.parametrize("pagina", ["0", "501", "abc", "-1", "1.5", "", " 1", "1e2", "٣", "0001"])
def test_vitrine_lista_pagina_invalida_400(app, client, vitrine_ligada, pagina):
    resposta = client.get("/api/public/animais", query_string={"pagina": pagina})
    assert resposta.status_code == 400
    assert resposta.headers["Cache-Control"] == "no-store"
    assert "Vercel-CDN-Cache-Control" not in resposta.headers
    assert _sem_cookie(resposta)


@pytest.mark.parametrize("logado", [False, True])
def test_vitrine_lista_cabecalhos(app, client, admin_client, vitrine_ligada, logado):
    _animal(publicado=True)
    resposta = (admin_client if logado else client).get("/api/public/animais")
    assert resposta.status_code == 200
    assert resposta.headers["Cache-Control"].startswith("public")
    assert resposta.headers["Vercel-CDN-Cache-Control"] == "max-age=120, stale-while-revalidate=60"
    assert _sem_cookie(resposta)


def test_vitrine_flag_desligada_404(app, client):
    animal = _animal(publicado=True)
    for url in ("/api/public/animais", f"/api/public/animais/{animal.slug_publico}"):
        resposta = client.get(url)
        assert resposta.status_code == 404
        assert resposta.headers["Cache-Control"] == "no-store"


# REQ-28 · GET /api/public/animais/<slug> -----------------------------------------------------

def test_vitrine_detalhe_200(app, client, vitrine_ligada):
    animal = _animal(publicado=True, descricao_publica="Muito dócil", pausar_candidaturas=True)
    resposta = client.get(f"/api/public/animais/{animal.slug_publico}")
    assert resposta.status_code == 200
    publico = resposta.get_json()["animal"]
    assert set(resposta.get_json()) == {"animal"}
    assert set(publico) == CHAVES_ANIMAL_PUBLICO
    assert publico["slug"] == animal.slug_publico and publico["candidaturas_pausadas"] is True
    assert publico["descricao_publica"] == "Muito dócil"
    assert "Vercel-CDN-Cache-Control" in resposta.headers and _sem_cookie(resposta)


def _assinatura(resposta):
    cabecalhos = {k: v for k, v in resposta.headers.items()}
    return resposta.status_code, resposta.get_data(), cabecalhos


def test_vitrine_detalhe_404_identico_e_sem_cache(app, client, vitrine_ligada, contar_consultas):
    despublicado = _animal(nome="Despublicado", publicado=True)
    despublicado.is_publicado = False
    indisponivel = _animal(nome="Indisponivel", publicado=True)
    indisponivel.status_operacional = "em tratamento"  # RN17: sai da vitrine
    excluido = _animal(nome="Excluido", publicado=True)
    excluido.is_deleted = True
    db.session.commit()
    slugs = ["inexistente-abc123", despublicado.slug_publico, indisponivel.slug_publico,
             excluido.slug_publico, "Mel-ABC123", "ab", "x" * 41, "mel_abc"]
    assinaturas = [_assinatura(client.get(f"/api/public/animais/{s}")) for s in slugs]
    assert assinaturas[0][0] == 404
    assert all(a == assinaturas[0] for a in assinaturas), "404 da vitrine revela a diferença entre os casos"
    assert assinaturas[0][2]["Cache-Control"] == "no-store"
    assert "Vercel-CDN-Cache-Control" not in assinaturas[0][2]
    assert "Set-Cookie" not in assinaturas[0][2]


def test_vitrine_detalhe_slug_invalido_nao_consulta_banco(app, client, vitrine_ligada, contar_consultas):
    contar_consultas.clear()
    assert client.get("/api/public/animais/Mel-ABC123").status_code == 404
    assert contar_consultas == []


# RN17 de ponta a ponta -----------------------------------------------------------------------

def test_rn17_ponta_a_ponta_publicar_mudar_status(app, admin_client, client, vitrine_ligada):
    animal = _animal()
    slug = _patch(admin_client, animal.id, publicar=True).get_json()["animal"]["slug_publico"]
    assert [a["slug"] for a in client.get("/api/public/animais").get_json()["animais"]] == [slug]
    assert client.get(f"/api/public/animais/{slug}").status_code == 200

    resposta = admin_client.patch(f"/api/animais/{animal.id}/status", json={"status_operacional": "em tratamento"})
    assert resposta.status_code == 200 and resposta.get_json()["animal"]["is_publicado"] is False
    assert client.get("/api/public/animais").get_json()["animais"] == []
    assert client.get(f"/api/public/animais/{slug}").status_code == 404

    # Voltou a ficar disponível: continua fora até ser republicado, e então com o mesmo link
    admin_client.patch(f"/api/animais/{animal.id}/status", json={"status_operacional": "disponível"})
    assert client.get(f"/api/public/animais/{slug}").status_code == 404
    assert _patch(admin_client, animal.id, publicar=True).get_json()["animal"]["slug_publico"] == slug
    assert client.get(f"/api/public/animais/{slug}").status_code == 200


# REQ-29 · superfície Open Graph (blueprint `og`, regra simulada) -----------------------------

@pytest.fixture
def app_og(monkeypatch):
    """App próprio com um blueprint `og` de mentira, registrado antes do primeiro request.

    O og_controller.py real é do Antigravity (B5); aqui só se prova a regra de `is_public_request`,
    por isso o `og` real (se já estiver em BLUEPRINTS) fica de fora deste app.
    """
    from app import controllers, create_app
    from flask import session
    monkeypatch.setattr(controllers, "BLUEPRINTS", tuple(b for b in controllers.BLUEPRINTS if b.name != "og"))
    os.environ["FLASK_ENV"] = "testing"
    app = create_app("testing")
    app.config.update({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                       "SECRET_KEY": "test-secret", "WTF_CSRF_ENABLED": False})
    if "og" in app.blueprints:
        pytest.skip("og_controller.py real já registrado; este teste usa um blueprint simulado")
    og = Blueprint("og", __name__)

    @og.route("/adote/<slug>")
    def preview_animal(slug):
        session.modified = True  # uma rota pública que tocasse a sessão não pode gerar cookie
        return f"<html>{slug}</html>"

    @og.route("/api/og-interno")
    def fora_do_prefixo():
        return "segredo"

    @og.route("/adote/<slug>/extra")
    def extra(slug):
        return slug

    app.register_blueprint(og)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _login(app, email, role="Voluntaria"):
    from app.models.user import User
    db.session.add(Whitelist(email=email, role=role, is_active=True))
    db.session.add(User(email=email, name="X", role=role, is_active=True))
    db.session.commit()
    c = app.test_client()
    assert c.post("/auth/dev-login", json={"email": email}).status_code == 200
    return c


def test_is_public_request_og_sem_set_cookie_nem_vary(app_og):
    for c in (app_og.test_client(), _login(app_og, "vol@gapar.org.br")):
        resposta = c.get("/adote/mel-abc123")
        assert resposta.status_code == 200
        assert "Set-Cookie" not in resposta.headers
        assert "cookie" not in (resposta.headers.get("Vary") or "").lower()


def test_is_public_request_og_sessao_revogada_nao_da_403(app_og):
    c = _login(app_og, "vol@gapar.org.br")
    Whitelist.query.filter_by(email="vol@gapar.org.br").update({"is_active": False})
    db.session.commit()
    g.pop("_login_user", None)
    assert c.get("/adote/mel-abc123").status_code == 200
    g.pop("_login_user", None)
    assert c.get("/api/animais").status_code == 403  # a área interna continua bloqueando


def test_is_public_request_og_fora_do_prefixo_continua_fechado(app_og):
    assert app_og.test_client().get("/api/og-interno").status_code == 401


@pytest.mark.parametrize("caminho, esperado", [
    ("/adote/mel-abc123", True),
    ("/adote//mel-abc123", False),
    ("/adote/../api/animais", False),
    ("/adote/x/../y", False),
    ("/api/og-interno", False),
    ("/api/public/config", False),
    ("/adotemel", False),
])
def test_is_public_request_og_caminho_canonico(app_og, caminho, esperado):
    from flask import request
    from app.utils.publico import is_public_request
    regra = next(r for r in app_og.url_map.iter_rules() if r.endpoint == "og.preview_animal")
    with app_og.test_request_context(caminho):
        request.url_rule = regra  # simula o roteamento ter aceitado o caminho
        assert request.blueprint == "og"
        assert is_public_request() is esperado


def test_is_public_request_outro_blueprint_com_prefixo_adote_nao_e_publico(app_og):
    from flask import request
    from app.utils.publico import is_public_request
    regra = next(r for r in app_og.url_map.iter_rules() if r.endpoint == "animals.list_animals")
    with app_og.test_request_context("/adote/mel-abc123"):
        request.url_rule = regra
        assert is_public_request() is False


def test_canario_exige_caso_para_rota_og(app_og):
    """Uma rota nova em `og.*` sem caso explícito reprova o canário."""
    from test_canary_anti_leak import _casos_publicos
    casos, sem_caso = _casos_publicos(app_og, {"slug_valido": "mel-abc123"})
    assert ("GET", "/adote/mel-abc123", None) in casos  # og.preview_animal usa o caso explícito
    assert ("GET", "/api/og-interno", None) in casos     # GET sem parâmetro: coberto sozinho
    assert sem_caso == ["og.extra"]


# REQ-30 · vercel.json ----------------------------------------------------------------------

BOTS = [
    "WhatsApp/2.23.20.0 A",
    "WhatsApp/2.2329.7 i",
    "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
    "Facebot",
    "Twitterbot/1.0",
    "TelegramBot (like TwitterBot)",
    "LinkedInBot/1.0 (compatible; Mozilla/5.0; Apache-HttpClient +http://www.linkedin.com)",
    "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
    "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)",
]
NAVEGADORES = [
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Android 14; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/23.0 "
    "Chrome/115.0.0.0 Mobile Safari/537.36",
]


def _vercel():
    return json.loads(VERCEL_JSON.read_text(encoding="utf-8"))


def _rewrite_og(config):
    return next(r for r in config["rewrites"] if r["source"] == "/adote/:slug")


def test_vercel_json_valido_e_preserva_configuracao():
    config = _vercel()
    assert config["git"]["deploymentEnabled"] == {"feat/cp01-nucleo": False}
    chaves = {h["key"] for bloco in config["headers"] for h in bloco["headers"]}
    assert {"X-Content-Type-Options", "Referrer-Policy", "X-Frame-Options", "Permissions-Policy"} <= chaves


def test_vercel_json_ordem_dos_rewrites():
    fontes = [r["source"] for r in _vercel()["rewrites"]]
    og, spa = fontes.index("/adote/:slug"), fontes.index("/((?!assets/).*)")
    assert fontes.index("/api/(.*)") < og and fontes.index("/auth/(.*)") < og
    assert og < spa and spa == len(fontes) - 1


def test_vercel_json_rewrite_og_condicional():
    regra = _rewrite_og(_vercel())
    assert regra["destination"] == "/api/index"
    (condicao,) = regra["has"]  # sem a condição, todo visitante humano cairia no Flask
    assert condicao["type"] == "header" and condicao["key"] == "user-agent"


def test_vercel_json_regex_cobre_bots_e_nao_navegadores():
    padrao = re.compile(_rewrite_og(_vercel())["has"][0]["value"])
    for ua in BOTS:
        assert padrao.fullmatch(ua), f"Robô sem prévia: {ua}"
        assert padrao.fullmatch(ua.upper()) and padrao.fullmatch(ua.lower())
    for ua in NAVEGADORES:
        assert not padrao.search(ua), f"Navegador desviado para o Flask: {ua}"


# Parecer do gatekeeper (CP-02) -----------------------------------------------------------------

def test_detalhe_tem_cache_curto_exato(app, client, vitrine_ligada):
    """RN17 x CDN: um cão adotado não pode ficar horas em /adote/<slug> por cache longo."""
    animal = _animal("Bela", publicado=True)
    resposta = client.get(f"/api/public/animais/{animal.slug_publico}")
    assert resposta.status_code == 200
    assert resposta.headers["Vercel-CDN-Cache-Control"] == "max-age=60, stale-while-revalidate=60"


@pytest.mark.parametrize("status_final", ["adotado", "óbito"])
def test_patch_vitrine_em_ficha_congelada_da_422(admin_client, status_final):
    """RN05: ficha adotada/óbito não muda, nem a descrição pública com publicar=false."""
    animal = _animal("Tico", publicado=True)
    animal.status_operacional = status_final
    db.session.commit()
    r = admin_client.patch(f"/api/animais/{animal.id}/vitrine", json={"publicar": False, "descricao_publica": "nova"})
    assert r.status_code == 422
    db.session.expire_all()
    assert db.session.get(Animal, animal.id).descricao_publica != "nova"


def test_banco_recusa_publicado_excluido_por_sql_direto(app):
    """O hook RN17 de is_deleted só age pelo ORM; o CHECK segura o SQL direto."""
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    animal = _animal("Zeca", publicado=True)
    with pytest.raises(IntegrityError):
        db.session.execute(text("UPDATE animals SET is_deleted = 1 WHERE id = :i"), {"i": animal.id})
        db.session.commit()
    db.session.rollback()


def test_banco_recusa_publicado_sem_slug(app):
    from sqlalchemy.exc import IntegrityError
    animal = Animal(nome="Sem Slug", sexo="Macho", porte="Pequeno", status_operacional="disponível",
                    is_publicado=True)
    db.session.add(animal)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
