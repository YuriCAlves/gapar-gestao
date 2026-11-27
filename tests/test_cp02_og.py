"""CP-02 · REQ-29 · Prévia Open Graph REAL (`og.preview_animal`), parecer do gatekeeper da Fase 2.

Os testes de `test_cp02_rotas.py` usam um blueprint `og` de mentira para provar a superfície
pública; estes exercitam o `og_controller.py` de verdade, que serve uma página pública guardada
em cache pela CDN: escape, cache, `og:url` sem depender do Host e só campos públicos.
"""
from datetime import date

import pytest

from app.extensions import db
from app.models.animal import Animal
from app.models.isolation import IsolationRecord
from app.utils.slug import gerar_slug_publico

BASE = "https://gapar.exemplo.org"
SEGREDOS_INTERNOS = ("Rua Interna 123", "Baia Secreta 7", "Motivo interno do resgate", "982000123456789")


@pytest.fixture
def vitrine(app):
    app.config["FEATURES"] = {**app.config["FEATURES"], "vitrine": True}
    app.config["PUBLIC_BASE_URL"] = BASE
    return app


def _publicado(nome="Mel", **extra):
    dados = dict(nome=nome, sexo="Fêmea", porte="Pequeno", status_operacional="disponível",
                 data_entrada=date.today(), local_resgate="Rua Interna 123",
                 localizacao_baia="Baia Secreta 7", motivo_resgate="Motivo interno do resgate",
                 is_publicado=True, slug_publico=gerar_slug_publico(nome))
    dados.update(extra)
    animal = Animal(**dados)
    db.session.add(animal)
    db.session.commit()
    return animal


def _html(resposta):
    return resposta.get_data(as_text=True)


def test_og_e_a_rota_real_registrada(app):
    regra = next(r for r in app.url_map.iter_rules() if r.endpoint == "og.preview_animal")
    assert regra.rule == "/adote/<slug>"


def test_sucesso_cache_curto_e_campos_publicos(vitrine, client):
    animal = _publicado(descricao_publica="Muito dócil", foto_url="https://cdn.exemplo/mel.jpg")
    resposta = client.get(f"/adote/{animal.slug_publico}")
    html = _html(resposta)
    assert resposta.status_code == 200
    assert resposta.headers["Cache-Control"] == "public, max-age=60"
    assert resposta.headers["Vercel-CDN-Cache-Control"] == "max-age=60, stale-while-revalidate=60"
    assert resposta.mimetype == "text/html" and resposta.headers["Content-Type"].count("charset") == 1
    assert "Set-Cookie" not in resposta.headers and "cookie" not in (resposta.headers.get("Vary") or "").lower()
    assert "Mel" in html and "Muito dócil" in html
    assert f'<meta property="og:url" content="{BASE}/adote/{animal.slug_publico}" />' in html
    assert 'og:image" content="https://cdn.exemplo/mel.jpg"' in html
    for segredo in SEGREDOS_INTERNOS:
        assert segredo not in html


@pytest.mark.parametrize("campo", ["nome", "descricao_publica"])
def test_escape_contra_xss(vitrine, client, campo):
    ataque = '"><script>alert(1)</script><img src=x onerror=alert(2)>'
    animal = _publicado(**{campo: ("Mel" if campo != "nome" else "") + ataque})
    html = _html(client.get(f"/adote/{animal.slug_publico}"))
    # Nenhuma tag injetada e as aspas escapadas: o ataque não fecha o atributo `content="..."`
    assert "<script>" not in html and "<img src=x" not in html
    assert '"><' not in html
    assert "&lt;script&gt;" in html and "&#34;&gt;" in html


@pytest.mark.parametrize("foto", ["http://cdn.exemplo/mel.jpg", "javascript:alert(1)", "/static/uploads/mel.jpg"])
def test_imagem_so_https(vitrine, client, foto):
    animal = _publicado(foto_url=foto)
    html = _html(client.get(f"/adote/{animal.slug_publico}"))
    assert "og:image" not in html


def test_host_malicioso_nao_vira_og_url(vitrine, client):
    animal = _publicado()
    html = _html(client.get(f"/adote/{animal.slug_publico}", headers={"Host": "atacante.example"}))
    assert "atacante.example" not in html
    assert f"{BASE}/adote/{animal.slug_publico}" in html


def test_sem_public_base_url_omite_og_url(vitrine, client):
    vitrine.config["PUBLIC_BASE_URL"] = ""
    animal = _publicado()
    html = _html(client.get(f"/adote/{animal.slug_publico}", headers={"Host": "atacante.example"}))
    assert "og:url" not in html and "atacante.example" not in html


def _fallback_ok(resposta, slug):
    html = _html(resposta)
    assert resposta.status_code == 200
    assert resposta.headers["Cache-Control"] == "no-store"
    assert "Vercel-CDN-Cache-Control" not in resposta.headers
    assert "ONG GAPAR" in html and slug not in html
    for segredo in SEGREDOS_INTERNOS:
        assert segredo not in html


def test_fallback_slug_inexistente_sem_cache_e_sem_o_slug(vitrine, client):
    _fallback_ok(client.get("/adote/nao-existe-abc123"), "nao-existe-abc123")
    assert f'content="{BASE}/adote" />' in _html(client.get("/adote/nao-existe-abc123"))


def test_fallback_flag_desligada(vitrine, client):
    animal = _publicado()
    vitrine.config["FEATURES"] = {**vitrine.config["FEATURES"], "vitrine": False}
    _fallback_ok(client.get(f"/adote/{animal.slug_publico}"), animal.slug_publico)


def test_fallback_animal_despublicado_por_rn17(vitrine, client):
    animal = _publicado()
    animal.status_operacional = "em tratamento"
    db.session.commit()
    _fallback_ok(client.get(f"/adote/{animal.slug_publico}"), animal.slug_publico)


def test_fallback_animal_isolado(vitrine, client):
    animal = _publicado()
    db.session.add(IsolationRecord(animal_id=animal.id, motivo="Suspeita de cinomose", data_inicio=date.today()))
    db.session.commit()
    _fallback_ok(client.get(f"/adote/{animal.slug_publico}"), animal.slug_publico)


def test_microchip_nunca_aparece(vitrine, client):
    vitrine.config["FEATURES"] = {**vitrine.config["FEATURES"], "microchip": True}
    animal = _publicado(numero_microchip="982000123456789")
    assert "982000123456789" not in _html(client.get(f"/adote/{animal.slug_publico}"))


def test_og_nunca_usa_to_dict(vitrine, client, monkeypatch):
    """A prévia pública só pode partir de `to_public_dict()` (allowlist); `to_dict()` traz campos internos."""
    animal = _publicado()

    def proibido(self, *args, **kwargs):
        raise AssertionError("og_controller chamou Animal.to_dict()")
    monkeypatch.setattr(Animal, "to_dict", proibido)
    assert client.get(f"/adote/{animal.slug_publico}").status_code == 200
