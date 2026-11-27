"""CP-04 · Microchip ISO 15 dígitos, API (REQ-39, REQ-40, RN21).

Spec: docs/sdd/CP03_05_FASE2_SPEC.md. Contrato: `ResumoMicrochip` e `ConflitoMicrochip` em
app/views/src/types/contratos.ts. Decisão: número preenchido com a flag "microchip" desligada
-> 400 (nunca descartado em silêncio); vazio/null com a flag desligada é ignorado, porque o
formulário do front manda `numero_microchip: null` sempre.
"""
from datetime import date

import pytest
from sqlalchemy import event

from app.extensions import db
from app.models.animal import Animal
from app.utils.slug import gerar_slug_publico

CHIP = "985112003456789"
OUTRO = "985112003456780"


@pytest.fixture
def microchip(app):
    app.config["FEATURES"] = {**app.config["FEATURES"], "microchip": True}


def _animal(nome="Rex", status="em acolhimento", chip=None, **extra):
    animal = Animal(nome=nome, sexo="Macho", porte="Médio", status_operacional=status,
                    data_entrada=date.today(), **extra)
    if chip:
        animal.numero_microchip = chip
    db.session.add(animal)
    db.session.commit()
    return animal


def _criar(client, **extra):
    return client.post("/api/animais", json={"nome": "Bidu", "sexo": "Macho", **extra})


# Flag desligada ----------------------------------------------------------------------------------

def test_flag_desligada_busca_404(app, vol_client):
    _animal(chip=CHIP)
    assert vol_client.get(f"/api/animais/microchip/{CHIP}").status_code == 404


def test_flag_desligada_numero_preenchido_400(app, vol_client):
    r = _criar(vol_client, numero_microchip=CHIP)
    assert r.status_code == 400 and r.get_json()["erro"] == "Microchip desativado"
    assert Animal.query.count() == 0
    a = _animal()
    assert vol_client.patch(f"/api/animais/{a.id}", json={"numero_microchip": CHIP}).status_code == 400


@pytest.mark.parametrize("valor", [None, "", "  "])
def test_flag_desligada_campo_vazio_e_ignorado(app, vol_client, valor):
    r = _criar(vol_client, numero_microchip=valor)
    assert r.status_code == 201 and r.get_json()["animal"]["numero_microchip"] is None
    a = _animal(chip=CHIP)  # legado gravado antes de a flag ser desligada não é apagado
    assert vol_client.patch(f"/api/animais/{a.id}", json={"numero_microchip": valor, "nome": "Rex2"}).status_code == 200
    db.session.expire_all()
    assert db.session.get(Animal, a.id).numero_microchip == CHIP


# Cadastro e edição (REQ-39) -----------------------------------------------------------------------

def test_cadastro_com_microchip(app, microchip, vol_client):
    r = _criar(vol_client, numero_microchip=f" {CHIP}\n", is_microchipado=False)
    assert r.status_code == 201
    animal = r.get_json()["animal"]
    assert animal["numero_microchip"] == CHIP and animal["is_microchipado"] is True


@pytest.mark.parametrize("valor", ["98511200345678", "9851120034567890", "98511200345678a", "985 112 003 456 789",
                                   "٩٨٥١١٢٠٠٣٤٥٦٧٨٩", 985112003456789, ["x"]])
def test_formato_invalido_400(app, microchip, vol_client, valor):
    r = _criar(vol_client, numero_microchip=valor)
    assert r.status_code == 400
    assert Animal.query.count() == 0
    a = _animal()
    assert vol_client.patch(f"/api/animais/{a.id}", json={"numero_microchip": valor}).status_code == 400


def test_cadastro_com_numero_repetido_409_conflito(app, microchip, vol_client):
    dono = _animal("Thor", chip=CHIP)
    r = _criar(vol_client, numero_microchip=CHIP)
    assert r.status_code == 409
    corpo = r.get_json()
    assert {"erro", "codigo", "mensagem", "animal_id", "animal_nome"} <= set(corpo)
    assert (corpo["codigo"], corpo["animal_id"], corpo["animal_nome"]) == (409, dono.id, "Thor")
    assert Animal.query.count() == 1


def test_numero_de_animal_excluido_tambem_conflita(app, microchip, vol_client):
    dono = _animal("Thor", chip=CHIP, is_deleted=True)
    r = _criar(vol_client, numero_microchip=CHIP)
    assert r.status_code == 409 and r.get_json()["animal_id"] == dono.id


def test_edicao_com_numero_de_outro_409(app, microchip, vol_client):
    dono = _animal("Thor", chip=CHIP)
    a = _animal("Bidu")
    r = vol_client.patch(f"/api/animais/{a.id}", json={"numero_microchip": CHIP, "nome": "Bidu II"})
    assert r.status_code == 409 and r.get_json()["animal_id"] == dono.id
    db.session.expire_all()
    assert db.session.get(Animal, a.id).nome == "Bidu"


def test_edicao_grava_mantem_e_limpa(app, microchip, vol_client):
    a = _animal("Bidu")
    r = vol_client.patch(f"/api/animais/{a.id}", json={"numero_microchip": CHIP, "is_microchipado": False})
    assert r.status_code == 200
    assert r.get_json()["animal"]["numero_microchip"] == CHIP and r.get_json()["animal"]["is_microchipado"] is True
    # O próprio número de novo não é conflito
    assert vol_client.patch(f"/api/animais/{a.id}", json={"numero_microchip": CHIP}).status_code == 200
    r = vol_client.patch(f"/api/animais/{a.id}", json={"numero_microchip": ""})
    assert r.status_code == 200 and r.get_json()["animal"]["numero_microchip"] is None
    assert r.get_json()["animal"]["is_microchipado"] is True  # limpar não desliga (legado)


def test_ficha_congelada_continua_bloqueada_rn05(app, microchip, vol_client):
    a = _animal("Bidu", status="óbito")
    assert vol_client.patch(f"/api/animais/{a.id}", json={"numero_microchip": CHIP}).status_code == 422


def test_corrida_no_unique_vira_409_conflito(app, microchip, vol_client, monkeypatch):
    """A checagem prévia não vê o outro animal (gravado entre a checagem e o INSERT): o UNIQUE do
    banco recusa e a rota devolve o mesmo `ConflitoMicrochip`, e não o 409 genérico."""
    dono = _animal("Thor", chip=CHIP)
    original = Animal.buscar_por_microchip.__func__
    chamadas = {"n": 0}

    def buscar(cls, numero, incluir_excluidos=False):
        chamadas["n"] += 1
        return None if chamadas["n"] == 1 else original(cls, numero, incluir_excluidos)

    monkeypatch.setattr(Animal, "buscar_por_microchip", classmethod(buscar))
    r = _criar(vol_client, numero_microchip=CHIP)
    assert r.status_code == 409 and r.get_json()["animal_id"] == dono.id
    assert r.get_json()["animal_nome"] == "Thor"

    a = _animal("Bidu")
    chamadas["n"] = 0
    r = vol_client.patch(f"/api/animais/{a.id}", json={"numero_microchip": CHIP})
    assert r.status_code == 409 and r.get_json()["animal_id"] == dono.id


# Busca pelo leitor (REQ-40) -----------------------------------------------------------------------

def test_busca_por_microchip(app, microchip, vol_client):
    a = _animal("Thor", chip=CHIP, localizacao_baia="Baia 3")
    r = vol_client.get(f"/api/animais/microchip/{CHIP}")
    assert r.status_code == 200
    assert r.get_json()["animal"] == {"id": a.id, "nome": "Thor", "status_operacional": "em acolhimento",
                                      "foto_url": None, "localizacao_baia": "Baia 3"}
    assert vol_client.get(f"/api/animais/microchip/{OUTRO}").status_code == 404


def test_busca_ignora_animal_excluido(app, microchip, vol_client):
    _animal("Thor", chip=CHIP, is_deleted=True)
    assert vol_client.get(f"/api/animais/microchip/{CHIP}").status_code == 404


def test_busca_sem_login_401(app, microchip, client):
    _animal("Thor", chip=CHIP)
    assert client.get(f"/api/animais/microchip/{CHIP}").status_code == 401


@pytest.mark.parametrize("numero", ["123", "98511200345678x", "9851120034567890"])
def test_busca_com_formato_invalido_404_sem_consultar_animais(app, microchip, vol_client, numero):
    vol_client.get("/api/animais/microchip/" + CHIP)  # aquece a sessão
    consultas = []

    def contar(conn, cursor, sql, *args):
        if "animals" in sql:
            consultas.append(sql)

    event.listen(db.engine, "before_cursor_execute", contar)
    try:
        assert vol_client.get(f"/api/animais/microchip/{numero}").status_code == 404
    finally:
        event.remove(db.engine, "before_cursor_execute", contar)
    assert consultas == []


# Canário: o microchip nunca sai na vitrine ------------------------------------------------------

def test_microchip_fora_da_vitrine_publica(app, microchip, client):
    app.config["FEATURES"] = {**app.config["FEATURES"], "vitrine": True}
    a = _animal("Mel", status="disponível", chip=CHIP)
    a.is_publicado = True
    a.slug_publico = gerar_slug_publico("Mel")
    db.session.commit()
    lista = client.get("/api/public/animais")
    detalhe = client.get(f"/api/public/animais/{a.slug_publico}")
    assert lista.status_code == 200 and detalhe.status_code == 200
    for resposta in (lista, detalhe):
        assert CHIP not in resposta.get_data(as_text=True)
        assert "microchip" not in resposta.get_data(as_text=True)


def test_nenhuma_rota_publica_da_fase_2(app):
    proibidos = ("microchip", "estoque", "isolamento")
    publicas = [r.rule for r in app.url_map.iter_rules() if r.endpoint.startswith(("public.", "og."))]
    assert publicas
    assert not [r for r in publicas if any(p in r for p in proibidos)]
    for regra in app.url_map.iter_rules():
        if any(p in regra.rule for p in proibidos):
            assert not regra.rule.startswith(("/api/public/", "/adote/")), regra.rule


# Parecer do gatekeeper (Fase 2) -----------------------------------------------------------------

def test_desmarcar_microchipado_com_numero_gravado_400(app, microchip, admin_client):
    """RN21: com número gravado o animal é microchipado; desmarcar exige apagar o número antes."""
    animal = _animal(chip="982000123456789")
    r = admin_client.patch(f"/api/animais/{animal.id}", json={"is_microchipado": False})
    assert r.status_code == 400
    db.session.expire_all()
    assert db.session.get(Animal, animal.id).is_microchipado is True
    # Apagando o número junto, pode desmarcar
    r = admin_client.patch(f"/api/animais/{animal.id}", json={"is_microchipado": False, "numero_microchip": None})
    assert r.status_code == 200
    db.session.expire_all()
    salvo = db.session.get(Animal, animal.id)
    assert salvo.numero_microchip is None and salvo.is_microchipado is False


def test_conflito_com_ficha_excluida_avisa(app, microchip, admin_client):
    dono = _animal("Antigo", chip="982000123456789")
    dono.is_deleted = True
    db.session.commit()
    r = _criar(admin_client, porte="Médio", numero_microchip="982000123456789")
    assert r.status_code == 409
    corpo = r.get_json()
    assert corpo["animal_excluido"] is True and corpo["animal_id"] == dono.id
    assert "excluída" in corpo["mensagem"]


def test_conflito_com_ficha_ativa_marca_nao_excluida(app, microchip, admin_client):
    _animal("Ativo", chip="982000123456780")
    corpo = _criar(admin_client, porte="Médio", numero_microchip="982000123456780").get_json()
    assert corpo["animal_excluido"] is False
