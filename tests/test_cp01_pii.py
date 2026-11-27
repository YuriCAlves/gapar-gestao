"""CP-01 · Dados pessoais cifrados, D2 e RN15 por índice cego (REQ-10 a REQ-18)."""
from datetime import date

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import text

from app.commands import pii_backfill
from app.extensions import db
from app.models import AuditLog, NonEligiblePerson, User
from app.models.adoption import Adoption
from app.models.animal import Animal
from app.utils.crypto import cifrar_pii, decifrar_pii, indice_cego, recifrar_pii

CPF_A = "529.982.247-25"
CPF_B = "999.888.777-14"
CPF_C = "111.222.333-96"


def _animal(status="disponível"):
    a = Animal(nome="Pingo", sexo="Macho", porte="Pequeno", status_operacional=status)
    db.session.add(a)
    db.session.commit()
    return a


def _linha(sql, **params):
    return db.session.execute(text(sql), params).mappings().first()


# REQ-10 ------------------------------------------------------------------------------------

def test_rotacao_multifernet(app):
    k1, k2 = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    app.config["PII_FERNET_KEYS"] = k1
    antigo = cifrar_pii("52998224725")

    app.config["PII_FERNET_KEYS"] = f"{k2},{k1}"  # k2 nova primária; k1 ainda decifra
    assert decifrar_pii(antigo) == "52998224725"
    rotacionado = recifrar_pii(antigo)

    app.config["PII_FERNET_KEYS"] = k2  # k1 aposentada
    assert decifrar_pii(rotacionado) == "52998224725"
    assert decifrar_pii(antigo) is None  # sem a chave antiga, a cifra antiga não abre


def test_tokens_google_continuam_legiveis(app):
    u = User(email="g@gapar.org.br", role="Voluntaria")
    u.set_google_tokens("token-de-acesso", "token-de-renovacao")
    app.config["PII_FERNET_KEYS"] = Fernet.generate_key().decode()  # trocar a chave PII...
    assert u.get_decrypted_access_token() == "token-de-acesso"  # ...não afeta os tokens Google
    assert u.get_decrypted_refresh_token() == "token-de-renovacao"


# REQ-11 ------------------------------------------------------------------------------------

def test_blind_index_deterministico_e_por_dominio(app):
    a = indice_cego("cpf", "52998224725")
    assert a == indice_cego("cpf", "52998224725") and len(a) == 64
    assert a != indice_cego("tel", "52998224725")
    assert indice_cego("cpf", "") is None
    app.config["PII_HMAC_KEY"] = "outra-chave-hmac-com-mais-de-32-caracteres"
    assert indice_cego("cpf", "52998224725") != a
    with pytest.raises(ValueError):
        indice_cego("email", "x")


# REQ-13 ------------------------------------------------------------------------------------

def test_gravacao_nova_nao_fica_em_claro(admin_client):
    r = admin_client.post("/api/admin/nao-aptos", json={
        "nome": "Fulano", "motivo_impedimento": "x", "cpf": CPF_A, "telefone": "(41) 99999-8888"})
    assert r.status_code == 201
    assert r.get_json()["nao_apto"]["cpf"] == CPF_A  # leitura transparente e formatada
    linha = _linha("SELECT cpf, telefone, cpf_cifrado, telefone_cifrado, cpf_bidx FROM non_eligible_people")
    assert linha["cpf"] is None and linha["telefone"] is None
    assert "52998224725" not in linha["cpf_cifrado"] and "41999998888" not in linha["telefone_cifrado"]
    assert len(linha["cpf_bidx"]) == 64


def test_adocao_grava_cpf_e_endereco_so_cifrados(admin_client):
    a = _animal()
    r = admin_client.post(f"/api/adocoes/{a.id}", json={
        "adotante_nome": "Ana", "adotante_telefone": "(41) 3333-4444",
        "adotante_cpf": CPF_A, "adotante_endereco": "Rua A, 1"})
    assert r.status_code == 201
    adocao = r.get_json()["adocao"]
    assert adocao["adotante_cpf"] == CPF_A and adocao["adotante_endereco"] == "Rua A, 1"
    assert adocao["adotante_telefone"] == "4133334444"
    linha = _linha("SELECT adotante_cpf, adotante_endereco, adotante_endereco_cifrado FROM adoptions")
    assert linha["adotante_cpf"] is None and linha["adotante_endereco"] is None
    assert "Rua A" not in linha["adotante_endereco_cifrado"]


def test_leitura_de_registro_legado(app):
    db.session.execute(text(
        "INSERT INTO non_eligible_people (nome, cpf, telefone, motivo_impedimento, created_at) "
        "VALUES ('Legado', '111.222.333-96', '41988887777', 'antigo', '2026-01-01 00:00:00')"))
    db.session.commit()
    pessoa = NonEligiblePerson.query.one()
    assert pessoa.cpf == "111.222.333-96" and pessoa.telefone == "41988887777"
    assert pessoa.to_dict()["cpf"] == CPF_C


# REQ-14 ------------------------------------------------------------------------------------

def test_rn15_registro_legado_sem_indice(vol_client):
    db.session.execute(text(
        "INSERT INTO non_eligible_people (nome, cpf, telefone, motivo_impedimento, created_at) "
        "VALUES ('Legado', '111.222.333-96', '41988887777', 'antigo', '2026-01-01 00:00:00')"))
    db.session.commit()
    a = _animal()
    r = vol_client.post(f"/api/adocoes/{a.id}", json={
        "adotante_nome": "Outro Nome", "adotante_telefone": "41911112222", "adotante_cpf": CPF_C})
    assert r.status_code == 422


def test_rn15_prioridade_cpf_antes_de_nome(app):
    from app.services.lista_sigilosa import MOTIVO_CPF, MOTIVO_NOME, procurar
    db.session.add_all([
        NonEligiblePerson(nome="Por Nome", motivo_impedimento="x"),
        NonEligiblePerson(nome="Outro", cpf=CPF_A, motivo_impedimento="x"),
    ])
    db.session.commit()
    assert procurar("por  NOME", CPF_A, None)[0] == MOTIVO_CPF
    assert procurar("por  NOME", None, None)[0] == MOTIVO_NOME
    assert procurar("Ninguém", "52998224700", None) == (None, None)


# REQ-15 ------------------------------------------------------------------------------------

@pytest.mark.parametrize("campo,valor,aceito", [
    ("cpf", CPF_A, True), ("cpf", "52998224725", True),
    ("cpf", "123", False), ("cpf", "111.111.111-11", False), ("cpf", "529.982.247-26", False),
    ("cpf", "529a982247-25", False), ("cpf", "529.982.247-255", False),
    ("telefone", "(41) 3333-4444", True), ("telefone", "41999998888", True),
    ("telefone", "12", False), ("telefone", "(00) 99999-9999", False), ("telefone", "41899998888", False),
    ("telefone", "4199999888x", False), ("telefone", "41 99999 8888 1", False),
])
def test_validacao_cpf_telefone(admin_client, campo, valor, aceito):
    r = admin_client.post("/api/admin/nao-aptos", json={"nome": "A", "motivo_impedimento": "x", campo: valor})
    assert r.status_code == (201 if aceito else 400)


@pytest.mark.parametrize("payload", [
    {"adotante_telefone": "4199"},
    {"adotante_telefone": "41911112222", "adotante_cpf": "000.000.000-00"},
])
def test_validacao_na_adocao(vol_client, payload):
    a = _animal()
    r = vol_client.post(f"/api/adocoes/{a.id}", json={"adotante_nome": "Ana", **payload})
    assert r.status_code == 400
    assert db.session.get(Animal, a.id).status_operacional == "disponível"


# REQ-16 ------------------------------------------------------------------------------------

def test_busca_exata_lista_sigilosa(admin_client):
    for nome, cpf, tel in (("Marcio", CPF_B, "41999998888"), ("Joana", CPF_A, "4133334444")):
        admin_client.post("/api/admin/nao-aptos", json={
            "nome": nome, "motivo_impedimento": "x", "cpf": cpf, "telefone": tel})

    def buscar(filtro):
        return admin_client.post("/api/admin/nao-aptos/busca", json=filtro)

    def total(filtro):
        return buscar(filtro).get_json()["total"]

    assert total({"cpf": CPF_B}) == 1 and total({"cpf": "99988877714"}) == 1
    assert total({"telefone": "(41) 3333-4444"}) == 1
    assert total({"q": "mar"}) == 1
    assert admin_client.get("/api/admin/nao-aptos").get_json()["total"] == 2
    assert total({"q": "41999"}) == 0  # números no `q` não procuram mais CPF/telefone
    for filtro in ({"cpf": "999.888"}, {"cpf": "52998224700"}, {"telefone": "4199"},
                   {"cpf": CPF_A, "telefone": "4133334444"}, {}, {"q": ""}):
        assert buscar(filtro).status_code == 400, filtro


def test_busca_com_dado_pessoal_na_url_e_recusada(admin_client):
    for consulta in ("cpf=52998224725", "telefone=41999998888", "q=Marcio"):
        assert admin_client.get(f"/api/admin/nao-aptos?{consulta}").status_code == 400


def test_busca_exclusiva_da_administradora(vol_client):
    # Sem login (401) já é coberto por test_toda_rota_interna_exige_login
    assert vol_client.post("/api/admin/nao-aptos/busca", json={"q": "a"}).status_code == 403


# REQ-17 ------------------------------------------------------------------------------------

def _inserir_legados():
    a = _animal("adotado")
    db.session.execute(text(
        "INSERT INTO non_eligible_people (nome, cpf, telefone, motivo_impedimento, created_at) "
        "VALUES ('João  Legado', '111.222.333-96', '(41) 98888-7777', 'antigo', '2026-01-01 00:00:00')"))
    db.session.execute(text(
        "INSERT INTO adoptions (animal_id, adotante_nome, adotante_telefone, adotante_cpf, adotante_endereco, "
        "data_adocao, termo_assinado, termo_fisico_assinado, created_at) VALUES "
        "(:a, 'Fernanda', '41991234567', '987.654.321-00', 'Rua das Flores, 120', '2026-01-01', 1, 0, "
        "'2026-01-01 00:00:00')"), {"a": a.id})
    db.session.commit()


def test_pii_backfill(app):
    _inserir_legados()
    runner = app.test_cli_runner()

    simulacao = runner.invoke(pii_backfill, ["--dry-run"])
    assert simulacao.exit_code == 0, simulacao.output
    assert _linha("SELECT cpf_cifrado FROM non_eligible_people")["cpf_cifrado"] is None

    resultado = runner.invoke(pii_backfill)
    assert resultado.exit_code == 0, resultado.output
    pessoa = _linha("SELECT * FROM non_eligible_people")
    assert pessoa["cpf"] == "111.222.333-96"  # o valor em claro NÃO é apagado (fica para a 0003b)
    assert decifrar_pii(pessoa["cpf_cifrado"]) == "11122233396"
    assert decifrar_pii(pessoa["telefone_cifrado"]) == "41988887777"
    assert pessoa["cpf_bidx"] == indice_cego("cpf", "11122233396")
    assert pessoa["nome_bidx"] == indice_cego("nome", "joão legado")
    adocao = _linha("SELECT * FROM adoptions")
    assert decifrar_pii(adocao["adotante_cpf_cifrado"]) == "98765432100"
    assert decifrar_pii(adocao["adotante_endereco_cifrado"]) == "Rua das Flores, 120"

    db.session.expire_all()
    assert NonEligiblePerson.query.one().cpf == "11122233396"  # passa a ler da cifra

    log = AuditLog.query.filter_by(acao="PII_BACKFILL").one()
    assert "111" not in log.detalhes and "Fernanda" not in log.detalhes

    repetido = runner.invoke(pii_backfill)  # idempotente
    assert repetido.exit_code == 0
    assert "non_eligible_people.cpf_legado: 0" in repetido.output


# REQ-18 ------------------------------------------------------------------------------------

def test_auditoria_sem_pii(admin_client):
    r = admin_client.post("/api/admin/nao-aptos", json={
        "nome": "Fulano Sigiloso", "motivo_impedimento": "x", "cpf": CPF_B, "telefone": "41977776666"})
    nid = r.get_json()["nao_apto"]["id"]
    admin_client.patch(f"/api/admin/nao-aptos/{nid}", json={"telefone": "41955554444"})

    a1, a2 = _animal(), _animal()
    admin_client.post(f"/api/adocoes/{a1.id}", json={
        "adotante_nome": "Beltrana Adotante", "adotante_telefone": "41933332222", "adotante_cpf": CPF_A,
        "adotante_endereco": "Rua Secreta, 9"})
    bloqueada = admin_client.post(f"/api/adocoes/{a2.id}", json={
        "adotante_nome": "Ciclano Tentativa", "adotante_telefone": "41911110000", "adotante_cpf": CPF_B})
    assert bloqueada.status_code == 422

    detalhes = " ".join(l.detalhes or "" for l in AuditLog.query.all())
    assert detalhes  # houve registros
    for proibido in ("Fulano", "Beltrana", "Ciclano", "Sigiloso", "Rua Secreta",
                     "99988877714", "999.888.777-14", "52998224725", "41977776666", "41955554444", "41933332222"):
        assert proibido not in detalhes, proibido


# Parecer do gatekeeper (CP-01): bloqueador do backfill e mutantes sobreviventes ----------------

def test_pii_backfill_recusa_rodar_sem_chaves_reais(app):
    """Sem PII_* explícitas o comando cifraria com a chave derivada de dev e desligaria a RN15."""
    _inserir_legados()
    app.config["PII_FERNET_KEYS"] = ""
    resultado = app.test_cli_runner().invoke(pii_backfill)
    assert resultado.exit_code != 0
    assert "PII_FERNET_KEYS" in resultado.output
    assert _linha("SELECT cpf_cifrado, nome_bidx FROM non_eligible_people") == {"cpf_cifrado": None, "nome_bidx": None}


def test_pii_backfill_recusa_chave_de_exemplo_fora_dos_testes(app):
    _inserir_legados()
    app.config.update(TESTING=False, PII_HMAC_KEY="substitua-por-segredo-aleatorio-minimo-32-caracteres")
    try:
        resultado = app.test_cli_runner().invoke(pii_backfill)
    finally:
        app.config["TESTING"] = True
    assert resultado.exit_code != 0
    assert _linha("SELECT cpf_cifrado FROM non_eligible_people")["cpf_cifrado"] is None


def test_pii_backfill_mostra_e_audita_impressao_das_chaves(app):
    from app.utils.crypto import impressao_digital_pii
    _inserir_legados()
    resultado = app.test_cli_runner().invoke(pii_backfill)
    impressao = impressao_digital_pii(app.config)
    assert f"fernet={impressao['fernet']}" in resultado.output and f"hmac={impressao['hmac']}" in resultado.output
    log = AuditLog.query.filter_by(acao="PII_BACKFILL").one()
    assert impressao["hmac"] in log.detalhes
    assert app.config["PII_HMAC_KEY"] not in log.detalhes  # a impressão não é a chave


@pytest.mark.parametrize("estragar", ["decifrar", "indice"])
def test_pii_backfill_aborta_sem_gravar_quando_a_conferencia_falha(app, monkeypatch, estragar):
    import app.utils.crypto as crypto
    _inserir_legados()
    if estragar == "decifrar":
        monkeypatch.setattr(crypto, "decifrar_pii", lambda cifra: "valor-diferente")
    else:
        # A gravação usa um índice errado; a conferência recalcula com o correto e precisa notar.
        import app.models.pii_mixin as pii_mixin
        monkeypatch.setattr(pii_mixin, "indice_cego", lambda dominio, valor: "0" * 64)
    resultado = app.test_cli_runner().invoke(pii_backfill)
    assert resultado.exit_code != 0 and "não conferem" in resultado.output
    db.session.rollback()
    assert _linha("SELECT cpf_cifrado FROM non_eligible_people")["cpf_cifrado"] is None
    assert AuditLog.query.filter_by(acao="PII_BACKFILL").count() == 0


def test_rn15_prioridade_cpf_antes_de_telefone(app):
    from app.services.lista_sigilosa import MOTIVO_CPF, MOTIVO_TELEFONE, procurar
    db.session.add_all([
        NonEligiblePerson(nome="Pelo Telefone", telefone="41999998888", motivo_impedimento="x"),
        NonEligiblePerson(nome="Pelo CPF", cpf=CPF_A, motivo_impedimento="x"),
    ])
    db.session.commit()
    motivo, registro = procurar("Ninguém", CPF_A, "41999998888")
    assert motivo == MOTIVO_CPF and registro.nome == "Pelo CPF"
    assert procurar("Ninguém", None, "41999998888")[0] == MOTIVO_TELEFONE


def test_editar_registro_legado_limpa_o_valor_em_claro(admin_client):
    db.session.execute(text(
        "INSERT INTO non_eligible_people (nome, cpf, telefone, motivo_impedimento, created_at) "
        "VALUES ('Legado', '111.222.333-96', '41988887777', 'antigo', '2026-01-01 00:00:00')"))
    db.session.commit()
    nid = NonEligiblePerson.query.one().id
    r = admin_client.patch(f"/api/admin/nao-aptos/{nid}", json={"cpf": CPF_A, "telefone": "41977776666"})
    assert r.status_code == 200
    linha = _linha("SELECT cpf, telefone, cpf_cifrado FROM non_eligible_people")
    assert linha["cpf"] is None and linha["telefone"] is None and linha["cpf_cifrado"]


def test_pii_backfill_aborta_se_indice_do_nome_nao_confere(app):
    """Um nome_bidx gravado com outra chave (ou adulterado) precisa ser notado pela conferência."""
    _inserir_legados()
    db.session.execute(text("UPDATE non_eligible_people SET nome_bidx = :x"), {"x": "0" * 64})
    db.session.commit()
    resultado = app.test_cli_runner().invoke(pii_backfill)
    assert resultado.exit_code != 0 and "não conferem" in resultado.output
    db.session.rollback()
    assert _linha("SELECT cpf_cifrado FROM non_eligible_people")["cpf_cifrado"] is None
