"""Checkpoint 3: API REST pura e rigor das regras de negócio (SRS v4.0)."""
import io
from datetime import date, timedelta

import pytest
from PIL import Image

from app.extensions import db
from app.models.animal import Animal
from app.models.blacklist import NonEligiblePerson
from app.models.health import Prescription


def _animal(status="em acolhimento", **kw):
    a = Animal(nome=kw.pop("nome", "Rex"), sexo="Macho", porte="Médio",
               status_operacional=status, data_entrada=date.today(), **kw)
    db.session.add(a)
    db.session.commit()
    return a


def _prescricao(animal, horarios="08:00, 20:00", dias=2):
    p = Prescription(animal_id=animal.id, nome_medicamento="Dipirona", dosagem="5 gotas",
                     horarios=horarios, data_inicio=date.today(), data_fim=date.today() + timedelta(days=dias))
    db.session.add(p)
    db.session.commit()
    return p


# --- RNF05/RN12: toda a API exige sessão ------------------------------------

@pytest.mark.parametrize("method,url", [
    ("get", "/api/animais"), ("post", "/api/animais"), ("get", "/api/animais/1"),
    ("patch", "/api/animais/1/status"), ("delete", "/api/animais/1"),
    ("get", "/api/saude/vacinas/1"), ("post", "/api/saude/prescricoes/1"),
    ("post", "/api/saude/medicacao/baixa/1"), ("get", "/api/saude/lembretes/1.ics"),
    ("post", "/api/adocoes/1"), ("get", "/api/adocoes/1"), ("get", "/api/hoje"),
    ("get", "/api/avisos"), ("get", "/api/admin/nao-aptos"),
])
def test_api_exige_login(client, method, url):
    resp = getattr(client, method)(url)
    assert resp.status_code == 401
    corpo = resp.get_json()
    assert corpo["codigo"] == 401 and "erro" in corpo


def test_voluntaria_nao_acessa_admin_rn15(vol_client):
    assert vol_client.get("/api/admin/nao-aptos").status_code == 403
    assert vol_client.get("/api/admin/auditoria").status_code == 403


# --- Formato de erro padronizado --------------------------------------------

def test_erros_em_json_padronizado(vol_client):
    for resp in (vol_client.get("/api/inexistente"), vol_client.get("/api/animais/99999"),
                 vol_client.post("/api/animais", json={})):
        corpo = resp.get_json()
        assert corpo is not None and corpo["codigo"] == resp.status_code and "erro" in corpo


def test_nao_ha_rotas_html(client):
    for path in ("/animais", "/animais/novo", "/hoje", "/entrar"):
        assert client.get(path).status_code == 404


# --- RN01 / validação de cadastro -------------------------------------------

def test_rn01_ignora_status_e_data_enviados(vol_client):
    r = vol_client.post("/api/animais", json={
        "nome": "Toto", "sexo": "Macho", "porte": "Grande",
        "status_operacional": "disponível", "data_entrada": "2001-01-01"})
    assert r.status_code == 201
    a = r.get_json()["animal"]
    assert a["status_operacional"] == "em acolhimento" and a["data_entrada"] == date.today().isoformat()


@pytest.mark.parametrize("payload", [
    {"nome": "X", "sexo": "Outro"}, {"nome": "X", "sexo": "Macho", "porte": "Gigante"},
    {"nome": "X", "sexo": "Macho", "peso_kg": "abc"}, {"nome": "X", "sexo": "Macho", "peso_kg": "-3"},
    {"nome": "  ", "sexo": "Macho"},
])
def test_cadastro_rejeita_dados_invalidos(vol_client, payload):
    assert vol_client.post("/api/animais", json=payload).status_code == 400


def test_paginacao_limitada(vol_client, app):
    for i in range(3):
        _animal(nome=f"A{i}")
    corpo = vol_client.get("/api/animais?per_page=100000&page=-4").get_json()
    assert corpo["por_pagina"] == 100 and corpo["pagina_atual"] == 1


# --- RN02: máquina de estados -----------------------------------------------

def test_rn02_transicoes_validas(vol_client, app):
    a = _animal()
    for novo in ("em tratamento", "lar temporário", "disponível", "em acolhimento"):
        assert vol_client.patch(f"/api/animais/{a.id}/status", json={"status_operacional": novo}).status_code == 200


def test_rn02_mesmo_status_e_invalido(vol_client, app):
    a = _animal()
    assert vol_client.patch(f"/api/animais/{a.id}/status", json={"status_operacional": "em acolhimento"}).status_code == 422


def test_rn02_status_desconhecido(vol_client, app):
    a = _animal()
    assert vol_client.patch(f"/api/animais/{a.id}/status", json={"status_operacional": "viajando"}).status_code == 400


# --- RN04: adotado só via registro formal -----------------------------------

def test_rn04_status_adotado_exige_registro_formal(vol_client, app):
    a = _animal("disponível")
    r = vol_client.patch(f"/api/animais/{a.id}/status", json={"status_operacional": "adotado"})
    assert r.status_code == 422
    assert db.session.get(Animal, a.id).status_operacional == "disponível"


def test_rn04_adocao_so_de_disponivel_ou_lar_temporario(vol_client, app):
    a = _animal("em tratamento")
    payload = {"adotante_nome": "Ana", "adotante_telefone": "4133334444"}
    assert vol_client.post(f"/api/adocoes/{a.id}", json=payload).status_code == 422
    a.status_operacional = "lar temporário"
    db.session.commit()
    assert vol_client.post(f"/api/adocoes/{a.id}", json=payload).status_code == 201


def test_rn04_data_adocao_invalida_nao_e_ignorada(vol_client, app):
    a = _animal("disponível")
    r = vol_client.post(f"/api/adocoes/{a.id}", json={
        "adotante_nome": "Ana", "adotante_telefone": "4133334444", "data_adocao": "31/12/2026"})
    assert r.status_code == 400


# --- RN05/RN06: congelamento total ------------------------------------------

@pytest.mark.parametrize("final", ["adotado", "óbito"])
def test_rn05_congelamento_total(admin_client, app, final):
    a = _animal(final)
    assert admin_client.patch(f"/api/animais/{a.id}", json={"nome": "Novo"}).status_code == 422
    assert admin_client.patch(f"/api/animais/{a.id}/status", json={"status_operacional": "em acolhimento"}).status_code == 422
    assert admin_client.delete(f"/api/animais/{a.id}").status_code == 422
    assert admin_client.post(f"/api/animais/{a.id}/foto").status_code == 422
    assert admin_client.post(f"/api/saude/prontuario/{a.id}", json={"diagnostico": "x"}).status_code == 422
    assert admin_client.get(f"/api/animais/{a.id}").status_code == 200  # histórico segue consultável (RN06)


def test_obito_a_partir_de_status_ativo(vol_client, app):
    a = _animal("em tratamento")
    assert vol_client.patch(f"/api/animais/{a.id}/status", json={"status_operacional": "óbito"}).status_code == 200


# --- RN03: exclusão só lógica e só da Administradora ------------------------

def test_rn03_voluntaria_nao_exclui(vol_client, app):
    a = _animal()
    assert vol_client.delete(f"/api/animais/{a.id}").status_code == 403
    assert db.session.get(Animal, a.id).is_deleted is False


# --- RN08/RN09/RF16: prescrição e baixa -------------------------------------

@pytest.mark.parametrize("status,esperado", [
    ("em acolhimento", 201), ("em tratamento", 201), ("lar temporário", 201),
    ("disponível", 422), ("adotado", 422), ("óbito", 422),
])
def test_rn08_status_que_permitem_prescricao(vol_client, app, status, esperado):
    a = _animal(status)
    r = vol_client.post(f"/api/saude/prescricoes/{a.id}", json={
        "nome_medicamento": "X", "dosagem": "1", "horarios": "08:00"})
    assert r.status_code == esperado


@pytest.mark.parametrize("horarios", ["8h", "25:00", "08:00; 12:00", ","])
def test_prescricao_horarios_invalidos(vol_client, app, horarios):
    a = _animal("em tratamento")
    r = vol_client.post(f"/api/saude/prescricoes/{a.id}", json={
        "nome_medicamento": "X", "dosagem": "1", "horarios": horarios})
    assert r.status_code == 400


def test_prescricao_periodo_invalido(vol_client, app):
    a = _animal("em tratamento")
    r = vol_client.post(f"/api/saude/prescricoes/{a.id}", json={
        "nome_medicamento": "X", "dosagem": "1", "horarios": "08:00",
        "data_inicio": "2026-05-10", "data_fim": "2026-05-01"})
    assert r.status_code == 400


def test_rf16_baixa_sem_horario_em_prescricao_de_varios(vol_client, app):
    p = _prescricao(_animal("em tratamento"))
    assert vol_client.post(f"/api/saude/medicacao/baixa/{p.id}", json={}).status_code == 400
    assert vol_client.post(f"/api/saude/medicacao/baixa/{p.id}", json={"horario_previsto": "09:30"}).status_code == 400


def test_rf16_baixa_duplicada_com_horario_unico_implicito(vol_client, app):
    p = _prescricao(_animal("em tratamento"), horarios="08:00")
    r1 = vol_client.post(f"/api/saude/medicacao/baixa/{p.id}", json={})
    r2 = vol_client.post(f"/api/saude/medicacao/baixa/{p.id}", json={})
    assert r1.status_code == 200 and not r1.get_json().get("ja_baixado")
    assert r2.get_json()["ja_baixado"] is True


def test_rn09_baixa_fora_da_vigencia(vol_client, app):
    p = _prescricao(_animal("em tratamento"), horarios="08:00")
    p.data_inicio = date.today() - timedelta(days=5)
    p.data_fim = date.today() - timedelta(days=1)
    db.session.commit()
    assert vol_client.post(f"/api/saude/medicacao/baixa/{p.id}", json={"horario_previsto": "08:00"}).status_code == 422


def test_vacina_data_invalida(vol_client, app):
    a = _animal()
    r = vol_client.post(f"/api/saude/vacinas/{a.id}", json={"nome_vacina": "V10", "data_aplicacao": "ontem"})
    assert r.status_code == 400
    r = vol_client.post(f"/api/saude/vacinas/{a.id}", json={
        "nome_vacina": "V10", "data_aplicacao": "2026-05-10", "data_reforco": "2026-05-01"})
    assert r.status_code == 400


# --- RN15: lista sigilosa ----------------------------------------------------

@pytest.mark.parametrize("campo,valor", [
    ("adotante_cpf", "999.888.777-14"), ("adotante_telefone", "(41) 99999-8888"), ("adotante_nome", "  marcio inapto ")])
def test_rn15_bloqueia_por_cpf_telefone_ou_nome(vol_client, app, campo, valor):
    db.session.add(NonEligiblePerson(nome="Marcio Inapto", cpf="999.888.777-14",
                                     telefone="41999998888", motivo_impedimento="Maus tratos"))
    a = _animal("disponível")
    payload = {"adotante_nome": "Fulano", "adotante_telefone": "41911110000", "adotante_cpf": "529.982.247-25"}
    payload[campo] = valor
    r = vol_client.post(f"/api/adocoes/{a.id}", json=payload)
    assert r.status_code == 422
    assert "Maus tratos" not in r.get_data(as_text=True)  # não expõe o motivo sigiloso
    assert db.session.get(Animal, a.id).status_operacional == "disponível"


# --- RNF02: fotos -----------------------------------------------------------

def _imagem(tamanho=(1500, 1500), fmt="PNG"):
    import os
    buf = io.BytesIO()
    Image.frombytes("RGB", tamanho, os.urandom(tamanho[0] * tamanho[1] * 3)).save(buf, format=fmt)
    buf.seek(0)
    return buf


def test_rnf02_foto_grande_vira_menos_de_300kb(vol_client, app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    a = _animal()
    r = vol_client.post(f"/api/animais/{a.id}/foto", data={"foto": (_imagem(), "foto.png")},
                        content_type="multipart/form-data")
    assert r.status_code == 200
    arquivo = tmp_path / r.get_json()["foto_url"].rsplit("/", 1)[-1]
    assert 0 < arquivo.stat().st_size <= 300 * 1024


def test_foto_acima_de_10mb_retorna_413(vol_client, app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    a = _animal()
    r = vol_client.post(f"/api/animais/{a.id}/foto", data={"foto": (io.BytesIO(b"0" * (11 * 1024 * 1024)), "g.jpg")},
                        content_type="multipart/form-data")
    assert r.status_code == 413 and r.get_json()["codigo"] == 413


def test_foto_que_nao_e_imagem_retorna_400(vol_client, app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    a = _animal()
    r = vol_client.post(f"/api/animais/{a.id}/foto", data={"foto": (io.BytesIO(b"nao sou imagem"), "x.jpg")},
                        content_type="multipart/form-data")
    assert r.status_code == 400 and r.get_json()["codigo"] == 400


def test_cadastro_com_foto_multipart(vol_client, app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    r = vol_client.post("/api/animais", data={"nome": "Foto", "sexo": "Fêmea", "foto": (_imagem((800, 600)), "f.png")},
                        content_type="multipart/form-data")
    assert r.status_code == 201 and r.get_json()["animal"]["foto_url"].startswith("/static/uploads/")


# --- RNF07/LGPD: CPF e endereço do adotante só para a Administradora ---------

def test_lgpd_voluntaria_nao_ve_cpf_nem_endereco(app, vol_client, admin_client):
    from flask import g

    def como(cliente, metodo, url, **kw):
        g.pop("_login_user", None)  # os fixtures compartilham um app context; cada chamada recarrega a sessão
        return getattr(cliente, metodo)(url, **kw)

    a = _animal("disponível")
    r = como(vol_client, "post", f"/api/adocoes/{a.id}", json={
        "adotante_nome": "Ana", "adotante_telefone": "41999990000",
        "adotante_cpf": "123.456.789-09", "adotante_endereco": "Rua A, 1"})
    assert r.status_code == 201
    for corpo in (r.get_json()["adocao"],
                  como(vol_client, "get", f"/api/adocoes/{a.id}").get_json()["adocao"],
                  como(vol_client, "get", f"/api/animais/{a.id}").get_json()["adocao"]):
        assert "adotante_cpf" not in corpo and "adotante_endereco" not in corpo
        assert corpo["adotante_telefone"] == "41999990000"
    completo = como(admin_client, "get", f"/api/animais/{a.id}").get_json()["adocao"]
    assert completo["adotante_cpf"] == "123.456.789-09" and completo["adotante_endereco"] == "Rua A, 1"
