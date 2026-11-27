"""CP-03 · Estoque com lotes FEFO, serviço e API (REQ-34, REQ-35, REQ-36 e a parte de API da REQ-37).

Spec: docs/sdd/CP03_05_FASE2_SPEC.md. Contrato: app/views/src/types/contratos.ts ("CONTRATOS
PREVISTOS DA FASE 2"). A camada de dados tem testes próprios (test_cp03_estoque_dados.py).
"""
import threading
from datetime import timedelta
from decimal import Decimal

import pytest
from flask import jsonify
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    Animal, AuditLog, InventoryBatch, InventoryItem, InventoryMovement, MedicationLog, Prescription,
    Vaccination,
)
from app.services import inventory_service
from app.utils import tempo
from app.utils.validation import ApiError


def _ligar(app, *flags):
    app.config["FEATURES"] = {**app.config["FEATURES"], **{f: True for f in flags}}


@pytest.fixture
def estoque(app):
    _ligar(app, "estoque")


def _item(nome="V10", categoria="Vacina", unidade="doses", minimo="0", **extra):
    item = InventoryItem(nome=nome, categoria=categoria, unidade=unidade, estoque_minimo=Decimal(minimo), **extra)
    db.session.add(item)
    db.session.commit()
    return item


def _lote(item, codigo="L1", saldo="10", validade=None):
    lote = InventoryBatch(item_id=item.id, codigo_lote=codigo, saldo_atual=Decimal(saldo), data_validade=validade)
    db.session.add(lote)
    db.session.commit()
    return lote


def _animal(nome="Rex", status="em tratamento"):
    animal = Animal(nome=nome, sexo="Macho", porte="Médio", status_operacional=status, data_entrada=tempo.hoje())
    db.session.add(animal)
    db.session.commit()
    return animal


def _login_admin(app):
    """Login feito DEPOIS de registrar as rotas de teste (o Flask recusa rota nova após a 1ª requisição)."""
    from app.models import User, Whitelist
    db.session.add(Whitelist(email="admin@gapar.org.br", role="Administradora", is_active=True))
    db.session.add(User(email="admin@gapar.org.br", name="Admin", role="Administradora", is_active=True))
    db.session.commit()
    c = app.test_client()
    assert c.post("/auth/dev-login", json={"email": "admin@gapar.org.br"}).status_code == 200
    return c


def _saldo(lote_id):
    db.session.expire_all()
    return db.session.get(InventoryBatch, lote_id).saldo_atual


ROTAS = [
    ("GET", "/api/estoque/itens", None),
    ("POST", "/api/estoque/itens", {"nome": "X", "categoria": "Vacina", "unidade": "doses", "estoque_minimo": 1}),
    ("PATCH", "/api/estoque/itens/{item}", {"nome": "Y"}),
    ("GET", "/api/estoque/itens/{item}", None),
    ("POST", "/api/estoque/itens/{item}/lotes", {"codigo_lote": "N1", "quantidade": 5}),
    ("POST", "/api/estoque/lotes/{lote}/movimentos", {"tipo": "AJUSTE_MAIS", "quantidade": 1, "motivo": "Contagem"}),
    ("GET", "/api/estoque/fefo?item_id={item}&quantidade=1", None),
]
ROTAS_ADMIN = [r for r in ROTAS if r[0] != "GET"]
ROTAS_LEITURA = [r for r in ROTAS if r[0] == "GET"]


def _url(modelo, item, lote):
    return modelo.format(item=item.id, lote=lote.id)


# Flag e permissões (REQ-35) --------------------------------------------------------------------

@pytest.mark.parametrize("metodo,url,corpo", ROTAS)
def test_flag_desligada_404_ate_para_admin(app, admin_client, metodo, url, corpo):
    item = _item()
    lote = _lote(item)
    resposta = admin_client.open(_url(url, item, lote), method=metodo, json=corpo)
    assert resposta.status_code == 404


@pytest.mark.parametrize("metodo,url,corpo", ROTAS_ADMIN)
def test_voluntaria_403_nas_rotas_de_admin(app, estoque, vol_client, metodo, url, corpo):
    item = _item()
    lote = _lote(item)
    resposta = vol_client.open(_url(url, item, lote), method=metodo, json=corpo)
    assert resposta.status_code == 403
    assert _saldo(lote.id) == Decimal("10")
    assert InventoryMovement.query.count() == 0


@pytest.mark.parametrize("metodo,url,corpo", ROTAS_LEITURA)
def test_voluntaria_le_estoque_e_fefo(app, estoque, vol_client, metodo, url, corpo):
    item = _item()
    lote = _lote(item)
    assert vol_client.open(_url(url, item, lote), method=metodo).status_code == 200


@pytest.mark.parametrize("metodo,url,corpo", ROTAS)
def test_sem_login_401(app, estoque, client, metodo, url, corpo):
    item = _item()
    lote = _lote(item)
    assert client.open(_url(url, item, lote), method=metodo, json=corpo).status_code == 401


# Itens ----------------------------------------------------------------------------------------

def test_criar_e_listar_item(app, estoque, admin_client):
    resposta = admin_client.post("/api/estoque/itens", json={
        "nome": " Vacina V10 ", "categoria": "Vacina", "unidade": "doses", "estoque_minimo": "5,5"})
    assert resposta.status_code == 201
    item = resposta.get_json()["item"]
    assert set(item) == {"id", "nome", "categoria", "unidade", "estoque_minimo", "saldo_total",
                         "abaixo_do_minimo", "proxima_validade", "is_active"}
    assert item["nome"] == "Vacina V10" and item["estoque_minimo"] == 5.5 and item["abaixo_do_minimo"] is True
    lista = admin_client.get("/api/estoque/itens").get_json()["itens"]
    assert [i["id"] for i in lista] == [item["id"]]
    assert AuditLog.query.filter_by(acao="ESTOQUE_ITEM_CRIADO").count() == 1


@pytest.mark.parametrize("corpo", [
    {"nome": "", "categoria": "Vacina", "unidade": "doses"},
    {"nome": "X", "categoria": "Brinquedo", "unidade": "doses"},
    {"nome": "X", "categoria": "Vacina", "unidade": "litros"},
    {"nome": "X", "categoria": "Vacina", "unidade": "doses", "estoque_minimo": -1},
    {"nome": "X", "categoria": "Vacina", "unidade": "doses", "estoque_minimo": "abc"},
    {"nome": "X", "categoria": "Vacina", "unidade": "doses", "estoque_minimo": 1.234},
])
def test_criar_item_invalido_400(app, estoque, admin_client, corpo):
    assert admin_client.post("/api/estoque/itens", json=corpo).status_code == 400
    assert InventoryItem.query.count() == 0


def test_listar_filtra_categoria_e_inativos(app, estoque, admin_client):
    _item("V10")
    _item("Dipirona", categoria="Medicamento", unidade="ml")
    _item("Antigo", is_active=False)
    nomes = lambda url: [i["nome"] for i in admin_client.get(url).get_json()["itens"]]
    assert nomes("/api/estoque/itens") == ["Dipirona", "V10"]
    assert nomes("/api/estoque/itens?categoria=Medicamento") == ["Dipirona"]
    assert nomes("/api/estoque/itens?inativos=1") == ["Antigo", "Dipirona", "V10"]
    assert admin_client.get("/api/estoque/itens?categoria=Nada").status_code == 400


def test_editar_item(app, estoque, admin_client):
    item = _item()
    resposta = admin_client.patch(f"/api/estoque/itens/{item.id}",
                                  json={"nome": "V8", "estoque_minimo": 3, "is_active": False})
    assert resposta.status_code == 200
    dados = resposta.get_json()["item"]
    assert (dados["nome"], dados["estoque_minimo"], dados["is_active"]) == ("V8", 3.0, False)
    assert admin_client.patch(f"/api/estoque/itens/{item.id}", json={}).status_code == 400
    assert admin_client.patch(f"/api/estoque/itens/{item.id}", json={"is_active": "sim"}).status_code == 400
    assert admin_client.patch("/api/estoque/itens/999", json={"nome": "Z"}).status_code == 404


def test_item_excluido_logicamente_some(app, estoque, admin_client):
    item = _item(is_deleted=True)
    assert admin_client.get(f"/api/estoque/itens/{item.id}").status_code == 404
    assert admin_client.get("/api/estoque/itens?inativos=1").get_json()["itens"] == []


# Lotes e movimentos -----------------------------------------------------------------------------

def test_criar_lote_com_entrada(app, estoque, admin_client):
    item = _item()
    validade = (tempo.hoje() + timedelta(days=90)).isoformat()
    resposta = admin_client.post(f"/api/estoque/itens/{item.id}/lotes",
                                 json={"codigo_lote": "AB12", "data_validade": validade, "quantidade": 20})
    assert resposta.status_code == 201
    dados = resposta.get_json()
    assert dados["lote"]["saldo_atual"] == 20.0 and dados["lote"]["data_validade"] == validade
    mov = dados["movimento"]
    assert (mov["tipo"], mov["quantidade"], mov["saldo_apos"], mov["batch_id"]) == ("ENTRADA", 20.0, 20.0, dados["lote"]["id"])
    assert mov["registrado_por"] == "Admin" and mov["motivo"]


def test_lote_duplicado_409(app, estoque, admin_client):
    item = _item()
    _lote(item, codigo="AB12")
    resposta = admin_client.post(f"/api/estoque/itens/{item.id}/lotes", json={"codigo_lote": "AB12", "quantidade": 5})
    assert resposta.status_code == 409
    assert "Já existe um lote" in resposta.get_json()["mensagem"]
    assert InventoryBatch.query.count() == 1 and InventoryMovement.query.count() == 0


@pytest.mark.parametrize("corpo", [{"codigo_lote": "", "quantidade": 1}, {"codigo_lote": "Z", "quantidade": 0},
                                   {"codigo_lote": "Z"}, {"codigo_lote": "Z", "quantidade": 1, "data_validade": "31/12/2026"}])
def test_criar_lote_invalido_400(app, estoque, admin_client, corpo):
    item = _item()
    assert admin_client.post(f"/api/estoque/itens/{item.id}/lotes", json=corpo).status_code == 400
    assert InventoryBatch.query.count() == 0


def test_movimentos_somam_e_subtraem(app, estoque, admin_client):
    lote = _lote(_item(), saldo="10")
    url = f"/api/estoque/lotes/{lote.id}/movimentos"
    r = admin_client.post(url, json={"tipo": "AJUSTE_MAIS", "quantidade": 2.5, "motivo": "Contagem"})
    assert r.status_code == 201 and r.get_json()["movimento"]["saldo_apos"] == 12.5
    r = admin_client.post(url, json={"tipo": "PERDA", "quantidade": "2,5", "motivo": "Frasco quebrou"})
    assert r.status_code == 201 and r.get_json()["lote"]["saldo_atual"] == 10.0
    r = admin_client.post(url, json={"tipo": "AJUSTE_MENOS", "quantidade": 10, "motivo": "Contagem"})
    assert r.status_code == 201 and r.get_json()["movimento"]["saldo_apos"] == 0.0
    assert _saldo(lote.id) == Decimal("0")
    assert [m.saldo_apos for m in InventoryMovement.query.order_by(InventoryMovement.id)] == \
        [Decimal("12.5"), Decimal("10"), Decimal("0")]


def test_saida_alem_do_saldo_409_rn18(app, estoque, admin_client):
    lote = _lote(_item(), saldo="3")
    r = admin_client.post(f"/api/estoque/lotes/{lote.id}/movimentos",
                          json={"tipo": "AJUSTE_MENOS", "quantidade": 3.01, "motivo": "Contagem"})
    assert r.status_code == 409
    assert "RN18" in r.get_json()["mensagem"]
    assert _saldo(lote.id) == Decimal("3")
    assert InventoryMovement.query.count() == 0


@pytest.mark.parametrize("corpo", [
    {"tipo": "SAIDA_USO", "quantidade": 1, "motivo": "Uso"},
    {"tipo": "ROUBO", "quantidade": 1, "motivo": "x"},
    {"tipo": "PERDA", "quantidade": 1, "motivo": "  "},
    {"tipo": "PERDA", "quantidade": 1},
    {"tipo": "PERDA", "quantidade": -1, "motivo": "x"},
    {"tipo": "PERDA", "quantidade": True, "motivo": "x"},
])
def test_movimento_invalido_400(app, estoque, admin_client, corpo):
    lote = _lote(_item())
    assert admin_client.post(f"/api/estoque/lotes/{lote.id}/movimentos", json=corpo).status_code == 400
    assert _saldo(lote.id) == Decimal("10") and InventoryMovement.query.count() == 0


def test_movimento_em_lote_inexistente_404(app, estoque, admin_client):
    r = admin_client.post("/api/estoque/lotes/999/movimentos", json={"tipo": "PERDA", "quantidade": 1, "motivo": "x"})
    assert r.status_code == 404


def test_descarte_de_lote_vencido_e_permitido(app, estoque, admin_client):
    lote = _lote(_item(), saldo="4", validade=tempo.hoje() - timedelta(days=1))
    r = admin_client.post(f"/api/estoque/lotes/{lote.id}/movimentos",
                          json={"tipo": "DESCARTE_VALIDADE", "quantidade": 4, "motivo": "Vencido"})
    assert r.status_code == 201 and _saldo(lote.id) == Decimal("0")


def test_auditoria_sem_texto_livre_do_motivo(app, estoque, admin_client):
    lote = _lote(_item())
    segredo = "Doação de Maria Silva 11987654321"
    r = admin_client.post(f"/api/estoque/lotes/{lote.id}/movimentos",
                          json={"tipo": "AJUSTE_MAIS", "quantidade": 1, "motivo": segredo})
    assert r.status_code == 201
    detalhes = " ".join(a.detalhes or "" for a in AuditLog.query.all())
    assert "ESTOQUE_MOVIMENTO" in {a.acao for a in AuditLog.query.all()}
    assert "Maria" not in detalhes and "11987654321" not in detalhes


# Detalhe e FEFO ---------------------------------------------------------------------------------

def test_detalhe_em_ordem_fefo_com_movimentos(app, estoque, admin_client):
    hoje = tempo.hoje()
    item = _item()
    sem_validade = _lote(item, "SV", "5")
    vencido = _lote(item, "VE", "5", hoje - timedelta(days=2))
    longe = _lote(item, "LO", "5", hoje + timedelta(days=60))
    perto = _lote(item, "PE", "5", hoje + timedelta(days=5))
    admin_client.post(f"/api/estoque/lotes/{perto.id}/movimentos", json={"tipo": "PERDA", "quantidade": 1, "motivo": "x"})
    dados = admin_client.get(f"/api/estoque/itens/{item.id}").get_json()
    assert [l["id"] for l in dados["lotes"]] == [perto.id, longe.id, sem_validade.id, vencido.id]
    assert dados["item"]["saldo_total"] == 14.0  # vencido fora da soma
    assert len(dados["movimentos"]) == 1 and dados["movimentos"][0]["tipo"] == "PERDA"


def test_sugestao_fefo(app, estoque, vol_client):
    hoje = tempo.hoje()
    item = _item()
    _lote(item, "VE", "50", hoje - timedelta(days=1))   # vencido: fora
    _lote(item, "ZE", "0", hoje + timedelta(days=1))    # sem saldo: fora
    pouco = _lote(item, "PO", "1", hoje + timedelta(days=3))
    muito = _lote(item, "MU", "9", hoje + timedelta(days=30))
    sem = _lote(item, "SV", "20")
    dados = vol_client.get(f"/api/estoque/fefo?item_id={item.id}&quantidade=2").get_json()
    assert [l["id"] for l in dados["lotes"]] == [pouco.id, muito.id, sem.id]
    assert dados["sugerido_id"] == muito.id
    assert vol_client.get(f"/api/estoque/fefo?item_id={item.id}").get_json()["sugerido_id"] == pouco.id
    assert vol_client.get(f"/api/estoque/fefo?item_id={item.id}&quantidade=100").get_json()["sugerido_id"] is None
    assert vol_client.get("/api/estoque/fefo").status_code == 400
    assert vol_client.get("/api/estoque/fefo?item_id=999").status_code == 404
    assert vol_client.get(f"/api/estoque/fefo?item_id={item.id}&quantidade=0").status_code == 400


# Serviço: RN20 e saldo_apos ---------------------------------------------------------------------

def test_saida_uso_de_lote_vencido_422_rn20(app):
    hoje = tempo.hoje()
    vencido = _lote(_item(), "VE", "5", hoje - timedelta(days=1))
    with pytest.raises(ApiError) as erro:
        inventory_service.movimentar(vencido, "SAIDA_USO", Decimal("1"), "Uso")
    assert erro.value.status == 422 and "RN20" in erro.value.mensagem
    db.session.rollback()
    assert _saldo(vencido.id) == Decimal("5")


def test_saida_uso_de_lote_que_vence_hoje_passa(app):
    lote = _lote(_item(), "HJ", "5", tempo.hoje())
    mov = inventory_service.movimentar(lote, "SAIDA_USO", Decimal("2"), "Uso")
    db.session.commit()
    assert mov.saldo_apos == Decimal("3") and _saldo(lote.id) == Decimal("3")


def test_saida_uso_respeita_hoje_do_fuso(app, monkeypatch):
    """RN20 usa `tempo.hoje()`: o mesmo lote é aceito na véspera e recusado no dia seguinte."""
    hoje = tempo.hoje()
    lote = _lote(_item(), "FU", "5", hoje)
    monkeypatch.setattr(tempo, "hoje", lambda: hoje + timedelta(days=1))
    with pytest.raises(ApiError) as erro:
        inventory_service.movimentar(lote, "SAIDA_USO", Decimal("1"), "Uso")
    assert erro.value.status == 422


def test_decimais_sem_residuo(app):
    lote = _lote(_item(), "DC", "0.3")
    for _ in range(3):
        inventory_service.movimentar(lote, "PERDA", Decimal("0.1"), "x")
    db.session.commit()
    assert _saldo(lote.id) == Decimal("0")


# Baixa na saúde (REQ-36) ------------------------------------------------------------------------

def _vacina(client, animal, **extra):
    return client.post(f"/api/saude/vacinas/{animal.id}", json={"nome_vacina": "V10", **extra})


def test_vacina_com_baixa_liga_movimento(app, estoque, vol_client):
    animal = _animal()
    lote = _lote(_item(), "AB12", "5")
    r = _vacina(vol_client, animal, lote_id=lote.id)
    assert r.status_code == 201
    vacina = r.get_json()["vacina"]
    assert vacina["lote"] == "AB12"  # sem lote digitado, o cartão guarda o código do estoque
    mov = InventoryMovement.query.one()
    assert (mov.tipo, mov.quantidade, mov.saldo_apos) == ("SAIDA_USO", Decimal("1"), Decimal("4"))
    assert (mov.vaccination_id, mov.animal_id, mov.medication_log_id) == (vacina["id"], animal.id, None)
    assert r.get_json()["movimento"]["id"] == mov.id
    assert _vacina(vol_client, animal, lote_id=lote.id, quantidade=2).status_code == 201
    assert _saldo(lote.id) == Decimal("2")


def test_vacina_sem_lote_nao_mexe_no_estoque(app, estoque, vol_client):
    animal = _animal()
    lote = _lote(_item())
    assert _vacina(vol_client, animal, quantidade=3).status_code == 201
    assert InventoryMovement.query.count() == 0 and _saldo(lote.id) == Decimal("10")


@pytest.mark.parametrize("cenario,status", [
    ("saldo", 409), ("vencido", 422), ("categoria", 400), ("inexistente", 400), ("quantidade", 400),
])
def test_vacina_falha_na_baixa_desfaz_o_registro(app, estoque, vol_client, cenario, status):
    animal = _animal()
    hoje = tempo.hoje()
    if cenario == "categoria":
        lote = _lote(_item("Dipirona", categoria="Medicamento", unidade="ml"))
    elif cenario == "vencido":
        lote = _lote(_item(), validade=hoje - timedelta(days=1))
    else:
        lote = _lote(_item(), saldo="1")
    corpo = {"lote_id": 999 if cenario == "inexistente" else lote.id,
             "quantidade": {"saldo": 2, "quantidade": 0}.get(cenario, 1)}
    r = _vacina(vol_client, animal, **corpo)
    assert r.status_code == status
    db.session.expire_all()
    assert Vaccination.query.count() == 0, "a vacina não pode ficar gravada sem a baixa"
    assert InventoryMovement.query.count() == 0
    assert AuditLog.query.filter_by(acao="VACINA_REGISTRADA").count() == 0


def test_lote_id_com_flag_estoque_desligada_400(app, vol_client):
    animal = _animal()
    lote = _lote(_item())
    r = _vacina(vol_client, animal, lote_id=lote.id)
    assert r.status_code == 400 and r.get_json()["erro"] == "Estoque desativado"
    assert Vaccination.query.count() == 0
    # Sem lote (ou com lote vazio, como o formulário manda) segue normal
    assert _vacina(vol_client, animal, lote_id=None).status_code == 201
    assert _vacina(vol_client, animal, lote_id="").status_code == 201


def _prescricao(animal):
    hoje = tempo.hoje()
    p = Prescription(animal_id=animal.id, nome_medicamento="Dipirona", dosagem="1 ml", horarios="08:00",
                     data_inicio=hoje, data_fim=hoje + timedelta(days=2))
    db.session.add(p)
    db.session.commit()
    return p


def test_baixa_de_medicacao_com_estoque(app, estoque, vol_client):
    animal = _animal()
    p = _prescricao(animal)
    lote = _lote(_item("Dipirona", categoria="Medicamento", unidade="ml"), saldo="10")
    r = vol_client.post(f"/api/saude/medicacao/baixa/{p.id}", json={"lote_id": lote.id, "quantidade": 1.5})
    assert r.status_code == 200
    log_id = r.get_json()["log"]["id"]
    mov = InventoryMovement.query.one()
    assert (mov.medication_log_id, mov.animal_id, mov.vaccination_id) == (log_id, animal.id, None)
    assert mov.saldo_apos == Decimal("8.5")
    # Dose já baixada: devolve "já baixado" e NÃO consome de novo
    r2 = vol_client.post(f"/api/saude/medicacao/baixa/{p.id}", json={"lote_id": lote.id, "quantidade": 1.5})
    assert r2.status_code == 200 and r2.get_json()["ja_baixado"] is True
    assert InventoryMovement.query.count() == 1 and _saldo(lote.id) == Decimal("8.5")


@pytest.mark.parametrize("cenario,status", [("saldo", 409), ("vencido", 422), ("flag", 400)])
def test_baixa_de_medicacao_falha_desfaz_a_dose(app, vol_client, cenario, status):
    if cenario != "flag":
        _ligar(app, "estoque")
    animal = _animal()
    p = _prescricao(animal)
    validade = tempo.hoje() - timedelta(days=1) if cenario == "vencido" else None
    lote = _lote(_item("Dipirona", categoria="Medicamento", unidade="ml"), saldo="1", validade=validade)
    r = vol_client.post(f"/api/saude/medicacao/baixa/{p.id}",
                        json={"lote_id": lote.id, "quantidade": 2 if cenario == "saldo" else 1})
    assert r.status_code == status
    db.session.expire_all()
    assert MedicationLog.query.count() == 0 and InventoryMovement.query.count() == 0
    assert _saldo(lote.id) == Decimal("1")


# /api/hoje (REQ-36) -----------------------------------------------------------------------------

def _dados_de_alerta():
    hoje = tempo.hoje()
    acabando = _item("Dipirona", categoria="Medicamento", unidade="ml", minimo="5")
    _lote(acabando, "D1", "2")
    farto = _item("V10", minimo="1")
    vencendo = _lote(farto, "V1", "10", hoje + timedelta(days=10))
    _lote(farto, "V2", "10", hoje + timedelta(days=200))
    return acabando, vencendo


def test_hoje_traz_estoque_para_admin_com_flag(app, estoque, admin_client):
    acabando, vencendo = _dados_de_alerta()
    dados = admin_client.get("/api/hoje").get_json()
    assert [i["id"] for i in dados["estoque"]["acabando"]] == [acabando.id]
    assert [(l["id"], l["item_nome"]) for l in dados["estoque"]["vencendo"]] == [(vencendo.id, "V10")]


def test_hoje_sem_estoque_para_voluntaria(app, estoque, vol_client):
    _dados_de_alerta()
    assert "estoque" not in vol_client.get("/api/hoje").get_json()


def test_hoje_sem_estoque_com_flag_desligada(app, admin_client):
    _dados_de_alerta()
    assert "estoque" not in admin_client.get("/api/hoje").get_json()


# Imutabilidade (RN19) no tratador de erros ------------------------------------------------------

def test_tratador_cita_rn19_para_movimento_e_rn16_para_auditoria(app):
    from app.models.base import AuditoriaImutavel, RegistroImutavel

    @app.route("/api/_teste/imutavel/<tipo>")
    def _imutavel(tipo):
        raise (RegistroImutavel if tipo == "mov" else AuditoriaImutavel)("x")

    class _Orig(Exception):
        pgcode = "23001"

    @app.route("/api/_teste/23001")
    def _restricao():
        raise IntegrityError("UPDATE", {}, _Orig())

    c = _login_admin(app)
    mov = c.get("/api/_teste/imutavel/mov")
    assert mov.status_code == 422 and "RN19" in mov.get_json()["mensagem"] and "RN16" not in mov.get_json()["mensagem"]
    aud = c.get("/api/_teste/imutavel/aud")
    assert aud.status_code == 422 and "RN16" in aud.get_json()["mensagem"]
    r = c.get("/api/_teste/23001")
    assert r.status_code == 422 and "RN19" in r.get_json()["mensagem"]


def test_movimento_alterado_pelo_orm_vira_422_rn19(app):
    lote = _lote(_item())
    mov = inventory_service.movimentar(lote, "ENTRADA", Decimal("1"), "Compra")
    db.session.commit()

    @app.route("/api/_teste/alterar-mov")
    def _alterar():
        m = db.session.get(InventoryMovement, mov.id)
        m.motivo = "outro"
        db.session.commit()
        return jsonify({})

    c = _login_admin(app)
    r = c.get("/api/_teste/alterar-mov")
    assert r.status_code == 422 and "RN19" in r.get_json()["mensagem"]


# Concorrência (REQ-37): dois consumos do último saldo -------------------------------------------

def test_dois_consumos_simultaneos_do_ultimo_saldo_so_um_passa(tmp_path, monkeypatch):
    """Duas sessões e duas conexões independentes (uma por thread, cada uma no seu app context)
    sobre um SQLite em ARQUIVO disputam a última unidade do lote. Só uma passa; a outra recebe
    409 (RN18) do UPDATE condicional (rowcount 0), e não um erro do CHECK do banco.

    No PostgreSQL vale o mesmo `UPDATE ... WHERE id = :id AND saldo_atual >= :q`: o UPDATE trava
    a linha, a segunda transação espera o commit da primeira e reavalia o WHERE sobre a versão
    nova (READ COMMITTED), achando saldo 0 -> rowcount 0 -> 409. Por isso não há `FOR UPDATE`.
    """
    from app import create_app
    from app.config import TestingConfig

    banco = tmp_path / "corrida.db"
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{banco.as_posix()}")
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        lote_id = _lote(_item(), "ULT", "1").id
        db.session.remove()

    barreira = threading.Barrier(2)
    resultados = []

    def consumir():
        with app.app_context():
            try:
                lote = db.session.get(InventoryBatch, lote_id)
                barreira.wait(timeout=10)
                inventory_service.movimentar(lote, "SAIDA_USO", Decimal("1"), "Uso")
                db.session.commit()
                resultados.append("ok")
            except ApiError as erro:
                db.session.rollback()
                resultados.append(erro.status)
            except Exception as erro:  # qualquer outra coisa (ex.: CHECK do banco) reprova o teste
                db.session.rollback()
                resultados.append(type(erro).__name__)
            finally:
                db.session.remove()

    threads = [threading.Thread(target=consumir) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert sorted(resultados, key=str) == [409, "ok"], resultados
    with app.app_context():
        assert db.session.get(InventoryBatch, lote_id).saldo_atual == Decimal("0")
        movimentos = InventoryMovement.query.filter_by(tipo="SAIDA_USO").all()
        assert [m.saldo_apos for m in movimentos] == [Decimal("0")]
        db.session.remove()
        db.engine.dispose()
