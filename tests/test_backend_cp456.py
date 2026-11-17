"""Backend para os Checkpoints 4 a 6: baixa à prova de corrida, auditoria, avisos, Whitelist,
armazenamento de fotos, .ics, painel Hoje e tratamento de erros vindos do banco."""
import io
import logging
import os
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
import requests
from PIL import Image
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Announcement
from app.models.animal import Animal
from app.models.audit import AuditLog
from app.models.base import AuditoriaImutavel, ExclusaoFisicaProibida
from app.models.health import MedicationLog, Prescription, Vaccination
from app.models.whitelist import Whitelist
from app.services import ics
from app.utils import tempo
from app.services.audit import log_audit_event

HOJE = date.today()


def _animal(status="em acolhimento", nome="Rex", **kw):
    a = Animal(nome=nome, sexo="Macho", porte="Médio", status_operacional=status, data_entrada=HOJE, **kw)
    db.session.add(a)
    db.session.commit()
    return a


def _prescricao(animal, horarios="08:00", inicio=HOJE, fim=None, **kw):
    p = Prescription(animal_id=animal.id, nome_medicamento=kw.pop("nome", "Dipirona"), dosagem="5 gotas",
                     horarios=horarios, data_inicio=inicio, data_fim=fim or inicio + timedelta(days=2), **kw)
    db.session.add(p)
    db.session.commit()
    return p


def _acoes():
    return [a.acao for a in AuditLog.query.order_by(AuditLog.id).all()]


# --- 1. RF16: baixa simultânea --------------------------------------------------

def test_baixa_concorrente_vira_ja_baixado(vol_client, app):
    p = _prescricao(_animal("em tratamento"))
    # A outra baixa "chega primeiro": a dose já está no banco, mas a checagem prévia não a viu
    db.session.add(MedicationLog(prescription_id=p.id, data_aplicacao=HOJE, horario_previsto="08:00",
                                 horario_aplicado="08:01"))
    db.session.commit()
    from app.services import saude
    real = saude.find_dose_log
    with patch("app.controllers.health_controller.find_dose_log", side_effect=[None, real(p.id, HOJE, "08:00")]):
        r = vol_client.post(f"/api/saude/medicacao/baixa/{p.id}", json={"horario_previsto": "08:00"})
    assert r.status_code == 200
    corpo = r.get_json()
    assert corpo["ja_baixado"] is True and corpo["log"]["horario_aplicado"] == "08:01"
    assert MedicationLog.query.count() == 1
    assert "BAIXA_MEDICACAO" not in _acoes()


def test_baixa_horario_aplicado_invalido(vol_client, app):
    p = _prescricao(_animal("em tratamento"))
    r = vol_client.post(f"/api/saude/medicacao/baixa/{p.id}", json={"horario_aplicado": "9h"})
    assert r.status_code == 400


def test_baixa_gera_auditoria_na_mesma_transacao(vol_client, app):
    p = _prescricao(_animal("em tratamento"))
    assert vol_client.post(f"/api/saude/medicacao/baixa/{p.id}", json={}).status_code == 200
    log = AuditLog.query.filter_by(acao="BAIXA_MEDICACAO").one()
    assert log.user_email == "vol@gapar.org.br" and log.entidade_id == MedicationLog.query.one().id


# --- 2. Auditoria paginada e filtrada -------------------------------------------

def _popular_auditoria(n=7):
    for i in range(n):
        db.session.add(AuditLog(acao="ACAO_PAR" if i % 2 == 0 else "ACAO_IMPAR", entidade="Animal",
                                entidade_id=i, user_email=f"u{i % 3}@gapar.org.br"))
    db.session.commit()


def test_auditoria_sem_parametros_compativel(admin_client, app):
    _popular_auditoria()
    corpo = admin_client.get("/api/admin/auditoria").get_json()
    assert corpo["sucesso"] is True and corpo["total"] == len(corpo["logs"]) == corpo["total_registros"]
    assert corpo["pagina_atual"] == 1 and corpo["por_pagina"] == 100 and corpo["total_paginas"] == 1
    ids = [log["id"] for log in corpo["logs"]]
    assert ids == sorted(ids, reverse=True)  # mais recentes primeiro


def test_auditoria_paginacao_e_teto(admin_client, app):
    _popular_auditoria(7)
    total = AuditLog.query.count()
    corpo = admin_client.get("/api/admin/auditoria?page=2&per_page=3").get_json()
    assert corpo["pagina_atual"] == 2 and corpo["por_pagina"] == 3 and len(corpo["logs"]) == 3
    assert corpo["total_registros"] == total and corpo["total_paginas"] == -(-total // 3)
    assert admin_client.get("/api/admin/auditoria?per_page=99999").get_json()["por_pagina"] == 200


def test_auditoria_filtros(admin_client, app):
    _popular_auditoria(7)
    corpo = admin_client.get("/api/admin/auditoria?acao=acao_par&entidade=animal&email=u0@").get_json()
    assert corpo["logs"] and all(l["acao"] == "ACAO_PAR" and l["user_email"] == "u0@gapar.org.br" for l in corpo["logs"])
    assert admin_client.get("/api/admin/auditoria?entidade_id=3").get_json()["total_registros"] == 1

    from app.models.base import utcnow
    db.session.add(AuditLog(acao="ANTIGO", entidade="Animal", user_email="x@gapar.org.br",
                            created_at=utcnow() - timedelta(days=10)))
    db.session.commit()
    ontem = (HOJE - timedelta(days=1)).isoformat()
    hoje_txt = HOJE.isoformat()
    recentes = admin_client.get(f"/api/admin/auditoria?data_inicio={ontem}&data_fim={hoje_txt}").get_json()
    assert all(l["acao"] != "ANTIGO" for l in recentes["logs"])
    velho = admin_client.get(f"/api/admin/auditoria?data_fim={(HOJE - timedelta(days=5)).isoformat()}").get_json()
    assert [l["acao"] for l in velho["logs"]] == ["ANTIGO"]
    assert admin_client.get("/api/admin/auditoria?data_inicio=ontem").status_code == 400
    assert admin_client.get(f"/api/admin/auditoria?data_inicio={hoje_txt}&data_fim={ontem}").status_code == 400
    acoes = admin_client.get("/api/admin/auditoria/acoes").get_json()
    assert "ANTIGO" in acoes["acoes"] and "Animal" in acoes["entidades"]


def test_auditoria_acoes_exclusiva_admin(vol_client):
    assert vol_client.get("/api/admin/auditoria/acoes").status_code == 403


# --- 3. Cobertura da trilha (RN16) ----------------------------------------------

def test_todas_as_alteracoes_geram_auditoria(admin_client, app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    c = admin_client
    aid = c.post("/api/animais", json={"nome": "Lua", "sexo": "Fêmea"}).get_json()["animal"]["id"]
    assert c.patch(f"/api/animais/{aid}", json={"pelagem": "Preta"}).status_code == 200
    assert c.patch(f"/api/animais/{aid}/status", json={"status_operacional": "em tratamento"}).status_code == 200
    vid = c.post(f"/api/saude/vacinas/{aid}", json={"nome_vacina": "V10"}).get_json()["vacina"]["id"]
    assert c.patch(f"/api/saude/vacinas/item/{vid}", json={"lote": "L1"}).status_code == 200
    assert c.post(f"/api/saude/prontuario/{aid}", json={"diagnostico": "ok"}).status_code == 201
    pid = c.post(f"/api/saude/prescricoes/{aid}", json={"nome_medicamento": "X", "dosagem": "1",
                                                         "horarios": "08:00"}).get_json()["prescricao"]["id"]
    assert c.patch(f"/api/saude/prescricoes/item/{pid}", json={"dosagem": "2"}).status_code == 200
    assert c.post(f"/api/saude/medicacao/baixa/{pid}", json={}).status_code == 200
    assert c.post("/api/avisos", json={"conteudo": "Oi"}).status_code == 201
    nid = c.post("/api/admin/nao-aptos", json={"nome": "Fulano", "motivo_impedimento": "x"}).get_json()["nao_apto"]["id"]
    assert c.patch(f"/api/admin/nao-aptos/{nid}", json={"telefone": "41999990000"}).status_code == 200
    wid = c.post("/api/admin/whitelist", json={"email": "n@gapar.org.br"}).get_json()["usuario"]["id"]
    assert c.patch(f"/api/admin/whitelist/{wid}", json={"role": "Administradora"}).status_code == 200
    assert c.patch(f"/api/admin/whitelist/{wid}/status", json={"is_active": False}).status_code == 200
    assert c.patch(f"/api/animais/{aid}/status", json={"status_operacional": "disponível"}).status_code == 200
    a2 = _animal("disponível", nome="Bidu")
    assert c.post(f"/api/adocoes/{aid}", json={"adotante_nome": "Ana", "adotante_telefone": "4133334444"}).status_code == 201
    assert c.delete(f"/api/animais/{a2.id}").status_code == 200

    acoes = _acoes()
    for esperado in ("ANIMAL_CADASTRADO", "ANIMAL_ATUALIZADO", "STATUS_ANIMAL_ALTERADO", "VACINA_REGISTRADA",
                     "VACINA_ATUALIZADA", "PRONTUARIO_REGISTRADO", "PRESCRICAO_CADASTRADA", "PRESCRICAO_ATUALIZADA",
                     "BAIXA_MEDICACAO", "AVISO_PUBLICADO", "NAO_APTO_INCLUIDO", "NAO_APTO_ALTERADO",
                     "WHITELIST_USUARIA_ADICIONADA", "WHITELIST_PERFIL_ALTERADO", "USUARIA_DESATIVADA_REVOGADA",
                     "ADOCAO_FORMALIZADA", "ANIMAL_EXCLUIDO_LOGICO"):
        assert esperado in acoes, esperado
    assert all(log.user_email == "admin@gapar.org.br" for log in AuditLog.query.filter(AuditLog.acao != "LOGIN_SUCESSO"))


def test_edicao_sem_mudanca_nao_gera_registro(vol_client, app):
    a = _animal()
    antes = AuditLog.query.count()
    assert vol_client.patch(f"/api/animais/{a.id}", json={"nome": "Rex"}).status_code == 200
    assert AuditLog.query.count() == antes


def test_falha_na_auditoria_avulsa_vai_para_o_log(app, caplog):
    with app.test_request_context("/"), patch("app.services.audit._build_entry", side_effect=RuntimeError("x")):
        with caplog.at_level(logging.ERROR):
            assert log_audit_event("TESTE", "Animal") is None
    assert "Falha ao gravar a trilha de auditoria" in caplog.text


def test_auditoria_registra_ip_do_proxy(vol_client, app):
    a = _animal()
    vol_client.patch(f"/api/animais/{a.id}", json={"pelagem": "Caramelo"}, headers={"X-Forwarded-For": "200.1.2.3, 10.0.0.1"})
    assert AuditLog.query.filter_by(acao="ANIMAL_ATUALIZADO").one().ip_origem == "200.1.2.3"


# --- 4. Avisos ------------------------------------------------------------------

@pytest.mark.parametrize("payload,status", [
    ({}, 400), ({"conteudo": "   "}, 400), ({"conteudo": "x", "tipo": "OUTRO"}, 400),
    ({"conteudo": "x", "titulo": "t" * 151}, 400), ({"conteudo": "x", "animal_id": "abc"}, 400),
    ({"conteudo": "x", "animal_id": 9999}, 400), ({"conteudo": "x", "tipo": "DIRETORIA"}, 403),
])
def test_avisos_validacao(vol_client, payload, status):
    r = vol_client.post("/api/avisos", json=payload)
    assert r.status_code == status and r.get_json()["codigo"] == status


def test_avisos_fluxo_completo(vol_client, app):
    a = _animal()
    r = vol_client.post("/api/avisos", json={"conteudo": " Dar banho ", "tipo": "turno", "animal_id": a.id,
                                             "is_fixado": "sim", "is_urgente": "false"})
    assert r.status_code == 201
    aviso = r.get_json()["aviso"]
    assert aviso["tipo"] == "TURNO" and aviso["conteudo"] == "Dar banho" and aviso["is_fixado"] is True
    assert aviso["is_urgente"] is False

    lista = vol_client.get(f"/api/avisos?animal_id={a.id}").get_json()["avisos"]
    assert lista[0]["confirmado_por_mim"] is False
    assert vol_client.post(f"/api/avisos/{aviso['id']}/confirmar", json={}).status_code == 201
    assert vol_client.post(f"/api/avisos/{aviso['id']}/confirmar", json={}).get_json()["ja_confirmado"] is True
    assert vol_client.get("/api/avisos").get_json()["avisos"][0]["confirmado_por_mim"] is True
    assert vol_client.post("/api/avisos/9999/confirmar", json={}).status_code == 404
    assert vol_client.get("/api/avisos?tipo=xyz").status_code == 400
    assert "AVISO_CONFIRMADO" in _acoes()


def test_admin_publica_comunicado_da_diretoria(admin_client):
    assert admin_client.post("/api/avisos", json={"conteudo": "Reunião", "tipo": "DIRETORIA"}).status_code == 201


# --- 5. Whitelist e não aptos ---------------------------------------------------

@pytest.mark.parametrize("email", ["semarroba", "a@b", "a b@gapar.org", "x@.com", "a..b@gapar.org", ""])
def test_whitelist_rejeita_email_invalido(admin_client, email):
    r = admin_client.post("/api/admin/whitelist", json={"email": email})
    assert r.status_code == 400 and r.get_json()["erro"] == "E-mail válido é obrigatório."


def test_whitelist_lista_marca_entradas(admin_client, app):
    app.config["INITIAL_ADMIN_EMAIL"] = "admin@gapar.org.br"
    corpo = admin_client.get("/api/admin/whitelist").get_json()
    eu = next(e for e in corpo["whitelist"] if e["email"] == "admin@gapar.org.br")
    assert eu["is_voce"] is True and eu["is_admin_inicial"] is True
    assert admin_client.get("/api/admin/whitelist?ativo=false").get_json()["total"] == 0


def test_admin_inicial_nao_pode_ser_desativada(admin_client, app):
    app.config["INITIAL_ADMIN_EMAIL"] = "admin@gapar.org.br"
    eid = Whitelist.query.filter_by(email="admin@gapar.org.br").one().id
    r = admin_client.patch(f"/api/admin/whitelist/{eid}/status", json={"is_active": False})
    assert r.status_code == 422 and "inicial" in r.get_json()["mensagem"]
    assert admin_client.patch(f"/api/admin/whitelist/{eid}", json={"role": "Voluntaria"}).status_code == 422
    assert db.session.get(Whitelist, eid).is_active is True


def test_admin_nao_se_tranca_para_fora(admin_client, app):
    app.config["INITIAL_ADMIN_EMAIL"] = "dona@gapar.org.br"
    eu = Whitelist.query.filter_by(email="admin@gapar.org.br").one()
    r = admin_client.patch(f"/api/admin/whitelist/{eu.id}/status", json={"is_active": False})
    assert r.status_code == 422 and "próprio" in r.get_json()["mensagem"]
    # Toggle sem corpo também é barrado
    assert admin_client.patch(f"/api/admin/whitelist/{eu.id}/status", json={}).status_code == 422

    outra = Whitelist(email="outra@gapar.org.br", role="Administradora", is_active=True)
    db.session.add(outra)
    db.session.commit()
    assert admin_client.patch(f"/api/admin/whitelist/{outra.id}/status", json={"is_active": False}).status_code == 200
    # Reativar e rebaixar a outra é permitido enquanto eu continuar Administradora
    assert admin_client.patch(f"/api/admin/whitelist/{outra.id}", json={"is_active": True, "role": "Voluntaria"}).status_code == 200
    assert db.session.get(Whitelist, outra.id).role == "Voluntaria"


def test_ultima_administradora_ativa_protegida(admin_client, app):
    """Cenário em que a entrada alterada é a última Administradora ativa (chamada direta da regra)."""
    app.config["INITIAL_ADMIN_EMAIL"] = "dona@gapar.org.br"
    unica = Whitelist(email="unica@gapar.org.br", role="Administradora", is_active=True)
    db.session.add(unica)
    Whitelist.query.filter_by(email="admin@gapar.org.br").one().role = "Voluntaria"
    db.session.commit()
    from app.controllers.admin_controller import _proteger_contra_trancamento
    from app.utils.validation import ApiError
    with app.test_request_context("/"), patch("app.controllers.admin_controller.current_user", MagicMock(email="admin@gapar.org.br")):
        with pytest.raises(ApiError) as exc:
            _proteger_contra_trancamento(unica, False, "Administradora")
    assert "ao menos uma Administradora" in exc.value.mensagem


def test_whitelist_perfil_invalido(admin_client):
    wid = admin_client.post("/api/admin/whitelist", json={"email": "z@gapar.org.br"}).get_json()["usuario"]["id"]
    assert admin_client.patch(f"/api/admin/whitelist/{wid}", json={"role": "Chefe"}).status_code == 400
    assert admin_client.patch(f"/api/admin/whitelist/{wid}", json={}).status_code == 400
    assert admin_client.patch("/api/admin/whitelist/9999", json={"role": "Voluntaria"}).status_code == 404


@pytest.mark.parametrize("payload", [
    {"nome": "", "motivo_impedimento": "x"}, {"nome": "A", "motivo_impedimento": " "},
    {"nome": "A", "motivo_impedimento": "x", "cpf": "123"}, {"nome": "A", "motivo_impedimento": "x", "telefone": "12"},
    {"nome": "A" * 151, "motivo_impedimento": "x"},
])
def test_nao_aptos_validacao(admin_client, payload):
    assert admin_client.post("/api/admin/nao-aptos", json=payload).status_code == 400


def test_nao_aptos_busca(admin_client):
    admin_client.post("/api/admin/nao-aptos", json={"nome": "Marcio", "motivo_impedimento": "x", "cpf": "999.888.777-66"})
    assert admin_client.get("/api/admin/nao-aptos?q=marc").get_json()["total"] == 1
    assert admin_client.get("/api/admin/nao-aptos?q=999.888").get_json()["total"] == 1
    assert admin_client.get("/api/admin/nao-aptos?q=zzz").get_json()["total"] == 0


def test_nao_aptos_edicao_exclusiva_admin(vol_client):
    assert vol_client.patch("/api/admin/nao-aptos/1", json={"nome": "X"}).status_code == 403


# --- 6. Armazenamento de fotos ---------------------------------------------------

def _imagem(tamanho=(1500, 1500)):
    buf = io.BytesIO()
    Image.frombytes("RGB", tamanho, os.urandom(tamanho[0] * tamanho[1] * 3)).save(buf, format="PNG")
    buf.seek(0)
    return buf


def _supabase(app):
    app.config.update(SUPABASE_URL="https://proj.supabase.co/", SUPABASE_SERVICE_ROLE_KEY="chave-servico")


def test_foto_vai_para_supabase(vol_client, app, tmp_path):
    _supabase(app)
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    a = _animal()
    resposta = MagicMock(status_code=200, text="{}")
    with patch("app.services.storage.requests.post", return_value=resposta) as post:
        r = vol_client.post(f"/api/animais/{a.id}/foto", data={"foto": (_imagem(), "f.png")},
                            content_type="multipart/form-data")
    assert r.status_code == 200
    url = r.get_json()["foto_url"]
    assert url.startswith("https://proj.supabase.co/storage/v1/object/public/animais/animal_") and url.endswith(".jpg")
    args, kwargs = post.call_args
    assert args[0] == "https://proj.supabase.co/storage/v1/object/animais/" + url.rsplit("/", 1)[-1]
    assert kwargs["headers"]["Authorization"] == "Bearer chave-servico"
    assert kwargs["headers"]["Content-Type"] == "image/jpeg"
    assert 0 < len(kwargs["data"]) <= 300 * 1024 and kwargs["data"][:2] == b"\xff\xd8"
    assert list(tmp_path.iterdir()) == []  # nada gravado no disco local
    assert db.session.get(Animal, a.id).foto_url == url


@pytest.mark.parametrize("efeito", [MagicMock(status_code=400, text="mime type not supported"),
                                    requests.ConnectionError("sem rede")])
def test_falha_no_supabase_vira_erro_json(vol_client, app, efeito):
    _supabase(app)
    a = _animal()
    kwargs = {"side_effect": efeito} if isinstance(efeito, Exception) else {"return_value": efeito}
    with patch("app.services.storage.requests.post", **kwargs):
        r = vol_client.post(f"/api/animais/{a.id}/foto", data={"foto": (_imagem((300, 300)), "f.png")},
                            content_type="multipart/form-data")
    assert r.status_code == 502
    corpo = r.get_json()
    assert corpo["codigo"] == 502 and corpo["erro"] == "Falha ao salvar a foto" and "chave-servico" not in r.get_data(as_text=True)
    assert db.session.get(Animal, a.id).foto_url is None


def test_cadastro_com_foto_no_supabase(vol_client, app):
    _supabase(app)
    with patch("app.services.storage.requests.post", return_value=MagicMock(status_code=200, text="")):
        r = vol_client.post("/api/animais", data={"nome": "Nuvem", "sexo": "Fêmea", "foto": (_imagem((400, 400)), "n.png")},
                            content_type="multipart/form-data")
    assert r.status_code == 201 and "/storage/v1/object/public/animais/" in r.get_json()["animal"]["foto_url"]


def test_sem_supabase_continua_no_disco(vol_client, app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    a = _animal()
    with patch("app.services.storage.requests.post") as post:
        r = vol_client.post(f"/api/animais/{a.id}/foto", data={"foto": (_imagem((300, 300)), "f.png")},
                            content_type="multipart/form-data")
    assert r.status_code == 200 and r.get_json()["foto_url"].startswith("/static/uploads/")
    post.assert_not_called()


def test_foto_url_texto_invalida(vol_client):
    assert vol_client.post("/api/animais", json={"nome": "X", "sexo": "Macho", "foto_url": "javascript:alert(1)"}).status_code == 400


# --- 7. Lembretes .ics ----------------------------------------------------------

def _linhas(corpo):
    """Desdobra as linhas (RFC 5545) para facilitar as verificações."""
    return corpo.replace("\r\n ", "").split("\r\n")


def test_ics_valido(vol_client, app):
    a = _animal("em tratamento", nome="Bolt, o Veloz; filho")
    _prescricao(a, horarios="08:00, 20:00", fim=HOJE + timedelta(days=4), nome="Amoxicilina",
                instrucoes="Dar com comida,\nsem pressa")
    _prescricao(a, inicio=HOJE - timedelta(days=10), fim=HOJE - timedelta(days=1), nome="Encerrada")
    db.session.add_all([
        Vaccination(animal_id=a.id, nome_vacina="Raiva", data_aplicacao=HOJE - timedelta(days=300),
                    data_reforco=HOJE + timedelta(days=65)),
        Vaccination(animal_id=a.id, nome_vacina="V10", data_aplicacao=HOJE - timedelta(days=400),
                    data_reforco=HOJE - timedelta(days=35)),
    ])
    db.session.commit()

    r = vol_client.get(f"/api/saude/lembretes/{a.id}.ics")
    assert r.status_code == 200 and r.mimetype == "text/calendar"
    corpo = r.get_data(as_text=True)
    assert corpo.endswith("END:VCALENDAR\r\n") and "\n" not in corpo.replace("\r\n", "")
    assert all(len(l.encode()) <= 75 for l in corpo.split("\r\n"))
    linhas = _linhas(corpo)
    assert linhas[0] == "BEGIN:VCALENDAR" and "VERSION:2.0" in linhas
    assert linhas.count("BEGIN:VEVENT") == 3 == int(r.headers["X-Total-Lembretes"])  # 2 horários + 1 reforço futuro
    assert sum(l.startswith("DTSTAMP:") and l.endswith("Z") for l in linhas) == 3
    assert len({l for l in linhas if l.startswith("UID:")}) == 3
    assert f"RRULE:FREQ=DAILY;COUNT=5" in linhas
    assert f"DTSTART:{HOJE.strftime('%Y%m%d')}T080000" in linhas
    assert "SUMMARY:Medicação: Amoxicilina (Bolt\\, o Veloz\\; filho)" in linhas
    assert any("Dar com comida\\,\\nsem pressa" in l for l in linhas)
    reforco = HOJE + timedelta(days=65)
    assert f"DTSTART;VALUE=DATE:{reforco.strftime('%Y%m%d')}" in linhas
    assert f"DTEND;VALUE=DATE:{(reforco + timedelta(days=1)).strftime('%Y%m%d')}" in linhas
    assert "Encerrada" not in corpo and "V10" not in corpo
    # O arquivo é aceito por uma biblioteca de calendário
    from icalendar import Calendar
    assert len(Calendar.from_ical(corpo).walk("VEVENT")) == 3


def test_ics_animal_congelado_sem_lembretes(vol_client, app):
    a = _animal("em tratamento")
    _prescricao(a)
    a.status_operacional = "óbito"
    db.session.commit()
    corpo = vol_client.get(f"/api/saude/lembretes/{a.id}.ics").get_data(as_text=True)
    assert "BEGIN:VEVENT" not in corpo and "BEGIN:VCALENDAR" in corpo


def test_ics_geral_e_reforco_atendido(vol_client, app):
    a = _animal("em tratamento", nome="Mel")
    b = _animal("em acolhimento", nome="Fofa")
    _prescricao(b)
    futuro = HOJE + timedelta(days=10)
    db.session.add_all([
        Vaccination(animal_id=a.id, nome_vacina="Gripe", data_aplicacao=HOJE - timedelta(days=20), data_reforco=futuro),
        # Reforço já aplicado hoje: o anterior deixa de ser lembrete
        Vaccination(animal_id=a.id, nome_vacina="gripe ", data_aplicacao=HOJE),
    ])
    db.session.commit()
    corpo = vol_client.get("/api/saude/lembretes.ics").get_data(as_text=True)
    assert "Fofa" in corpo and "Gripe" not in corpo


def test_ics_quebra_de_linha_utf8():
    linha = "DESCRIPTION:" + "ção" * 40
    dobrada = ics.fold_line(linha)
    assert all(len(p.encode()) <= 75 for p in dobrada.split("\r\n"))
    assert dobrada.replace("\r\n ", "") == linha
    assert ics.escape_text("a;b,c\\d\ne") == "a\\;b\\,c\\\\d\\ne"


# --- 8. Painel Hoje -------------------------------------------------------------

def _contar_consultas(app):
    contador = {"n": 0}

    def antes(*_):
        contador["n"] += 1
    event.listen(db.engine, "before_cursor_execute", antes)
    return contador, lambda: event.remove(db.engine, "before_cursor_execute", antes)


def test_hoje_sem_n_mais_1(vol_client, app):
    def popular(qtd):
        for i in range(qtd):
            a = _animal("em tratamento", nome=f"A{i}{qtd}")
            _prescricao(a, horarios="08:00, 20:00")
            db.session.add(Vaccination(animal_id=a.id, nome_vacina="V", data_aplicacao=HOJE - timedelta(days=30),
                                       data_reforco=HOJE))
        db.session.commit()

    popular(2)
    contador, parar = _contar_consultas(app)
    vol_client.get("/api/hoje")
    poucos = contador["n"]
    popular(8)
    contador["n"] = 0
    corpo = vol_client.get("/api/hoje").get_json()
    parar()
    assert contador["n"] == poucos
    assert len(corpo["medicacoes_hoje"]) == 20 and len(corpo["vacinas_hoje"]) == 10
    assert corpo["kpis"]["em_tratamento"] == 10 and corpo["kpis"]["total_acolhidos"] == 10


def test_hoje_formato_e_regras(vol_client, app):
    a = _animal("em tratamento", nome="Dara", localizacao_baia="Baia 3")
    p = _prescricao(a, horarios="00:00, 23:59")
    _animal("disponível", nome="Disp")
    _animal("adotado", nome="Foi")
    db.session.add_all([
        Vaccination(animal_id=a.id, nome_vacina="Raiva", data_aplicacao=HOJE - timedelta(days=400),
                    data_reforco=HOJE - timedelta(days=30)),
        Vaccination(animal_id=a.id, nome_vacina="V8", data_aplicacao=HOJE - timedelta(days=400),
                    data_reforco=HOJE - timedelta(days=30)),
        Vaccination(animal_id=a.id, nome_vacina="V8", data_aplicacao=HOJE - timedelta(days=2)),  # reforço atendido
    ])
    db.session.commit()
    vol_client.post(f"/api/saude/medicacao/baixa/{p.id}", json={"horario_previsto": "23:59"})

    corpo = vol_client.get("/api/hoje").get_json()
    assert set(corpo) >= {"data_referencia", "kpis", "total_medicacoes_pendentes", "total_vacinas_pendentes",
                          "medicacoes_hoje", "vacinas_hoje"}
    assert corpo["kpis"] == {"total_acolhidos": 2, "em_tratamento": 1, "disponiveis_adocao": 1,
                             "total_medicacoes_pendentes": 1, "total_vacinas_pendentes": 1}
    m0, m1 = corpo["medicacoes_hoje"]
    assert (m0["horario_previsto"], m0["aplicado"]) == ("00:00", False) and m1["aplicado"] is True
    assert m0["localizacao_baia"] == "Baia 3" and m1["horario_aplicado"]
    assert [v["nome_vacina"] for v in corpo["vacinas_hoje"]] == ["Raiva"] and corpo["vacinas_hoje"][0]["atrasada"] is True

    ficha = vol_client.get(f"/api/animais/{a.id}").get_json()
    situacao = {(v["nome_vacina"], v["data_aplicacao"]): v["reforco_pendente"] for v in ficha["vacinas"]}
    assert situacao[("Raiva", (HOJE - timedelta(days=400)).isoformat())] is True
    assert situacao[("V8", (HOJE - timedelta(days=400)).isoformat())] is False


def test_fuso_do_abrigo(app):
    app.config["APP_TIMEZONE"] = "America/Sao_Paulo"
    with app.app_context():
        assert tempo.agora().utcoffset() == timedelta(hours=-3)
        app.config["APP_TIMEZONE"] = "Fuso/Inexistente"
        assert tempo.agora().utcoffset() == timedelta(hours=-3)


# --- 9/10. Erros vindos do banco e outras lacunas ---------------------------------

class _OrigPg(Exception):
    pgcode = "23001"


def test_erros_do_banco_viram_json(app):
    def exclusao():
        raise ExclusaoFisicaProibida("animals")

    def imutavel():
        raise AuditoriaImutavel("audit_logs")

    def gatilho():
        raise IntegrityError("DELETE", {}, _OrigPg("bloqueado"))

    def unico():
        raise IntegrityError("INSERT", {}, Exception("UNIQUE constraint failed"))

    for nome, fn in (("exclusao", exclusao), ("imutavel", imutavel), ("gatilho", gatilho), ("unico", unico)):
        app.add_url_rule(f"/teste-erro/{nome}", nome, fn)
    c = app.test_client()
    for nome, status in (("exclusao", 422), ("imutavel", 422), ("gatilho", 422), ("unico", 409)):
        r = c.get(f"/teste-erro/{nome}")
        corpo = r.get_json()
        assert r.status_code == status and corpo["codigo"] == status and corpo["mensagem"], nome
        assert "constraint" not in r.get_data(as_text=True).lower()


def test_check_do_banco_nao_vira_500(vol_client, app):
    """Um valor que escapa da validação e bate num CHECK do banco devolve 409 em JSON."""
    a = _animal()
    with patch("app.controllers.animals_controller.require_choice", side_effect=lambda v, *a: v):
        r = vol_client.patch(f"/api/animais/{a.id}", json={"porte": "Gigante"})
    assert r.status_code == 409 and r.get_json()["codigo"] == 409
    assert db.session.get(Animal, a.id).porte == "Médio"


def test_corpo_que_nao_e_objeto(vol_client):
    assert vol_client.post("/api/animais", json=["nome"]).status_code == 400
    assert vol_client.post("/api/avisos", json="texto").status_code == 400


@pytest.mark.parametrize("payload", [
    {"nome": "X", "sexo": "Macho", "peso_kg": "0"}, {"nome": "X" * 101, "sexo": "Macho"},
    {"nome": "X", "sexo": "Macho", "codigo_identificador": "C" * 51}, {"nome": {"a": 1}, "sexo": "Macho"},
])
def test_cadastro_limites_de_tamanho_e_peso(vol_client, payload):
    assert vol_client.post("/api/animais", json=payload).status_code == 400


def test_catalogo_filtros_novos(vol_client, app):
    _animal(nome="Cuidado", cuidados_especiais="Diabético")
    _animal(nome="Normal")
    _animal("adotado", nome="Antigo")
    _animal(nome="100%_raro")
    nomes = lambda url: {x["nome"] for x in vol_client.get(url).get_json()["animais"]}
    assert nomes("/api/animais?cuidados_especiais=sim") == {"Cuidado"}
    assert "Antigo" not in nomes("/api/animais?ativos=sim") and nomes("/api/animais?ativos=nao") == {"Antigo"}
    assert nomes("/api/animais?q=%25") == {"100%_raro"}  # '%' digitado é texto, não curinga


def test_edicao_data_entrada(vol_client, app):
    a = _animal()
    ontem = (HOJE - timedelta(days=1)).isoformat()
    assert vol_client.patch(f"/api/animais/{a.id}", json={"data_entrada": ontem}).get_json()["animal"]["data_entrada"] == ontem
    assert vol_client.patch(f"/api/animais/{a.id}", json={"data_entrada": (HOJE + timedelta(days=1)).isoformat()}).status_code == 400


def test_prescricao_normaliza_e_edicao_respeita_rn08(vol_client, app):
    a = _animal("em tratamento")
    r = vol_client.post(f"/api/saude/prescricoes/{a.id}", json={"nome_medicamento": "X", "dosagem": "1",
                                                                "horarios": "20:00,08:00, 08:00"})
    p = r.get_json()["prescricao"]
    assert p["horarios"] == "08:00, 20:00"
    vol_client.patch(f"/api/animais/{a.id}/status", json={"status_operacional": "disponível"})
    mais = (HOJE + timedelta(days=30)).isoformat()
    assert vol_client.patch(f"/api/saude/prescricoes/item/{p['id']}", json={"data_fim": mais}).status_code == 422
    assert vol_client.patch(f"/api/saude/prescricoes/item/{p['id']}", json={"data_fim": HOJE.isoformat()}).status_code == 200
    assert vol_client.patch(f"/api/saude/prescricoes/item/{p['id']}", json={"data_inicio": mais}).status_code == 400
    assert vol_client.patch("/api/saude/prescricoes/item/9999", json={"dosagem": "1"}).status_code == 404


def test_edicoes_de_saude_bloqueadas_apos_congelamento(vol_client, app):
    a = _animal("em tratamento")
    p = _prescricao(a)
    v = Vaccination(animal_id=a.id, nome_vacina="V", data_aplicacao=HOJE)
    db.session.add(v)
    a.status_operacional = "óbito"
    db.session.commit()
    assert vol_client.patch(f"/api/saude/prescricoes/item/{p.id}", json={"dosagem": "2"}).status_code == 422
    assert vol_client.patch(f"/api/saude/vacinas/item/{v.id}", json={"lote": "2"}).status_code == 422


def test_adocao_data_futura_e_termo_texto(vol_client, app):
    a = _animal("disponível")
    futuro = (HOJE + timedelta(days=3)).isoformat()
    base = {"adotante_nome": "Ana", "adotante_telefone": "4133334444"}
    assert vol_client.post(f"/api/adocoes/{a.id}", json=dict(base, data_adocao=futuro)).status_code == 400
    r = vol_client.post(f"/api/adocoes/{a.id}", json=dict(base, termo_fisico_assinado="false"))
    assert r.status_code == 201 and r.get_json()["adocao"]["termo_fisico_assinado"] is False


def test_rn15_nome_com_espacos_internos(vol_client, app):
    from app.models.blacklist import NonEligiblePerson
    db.session.add(NonEligiblePerson(nome="Joao  da Silva", motivo_impedimento="x"))
    a = _animal("disponível")
    r = vol_client.post(f"/api/adocoes/{a.id}", json={"adotante_nome": "joao da  silva", "adotante_telefone": "4100001111"})
    assert r.status_code == 422
