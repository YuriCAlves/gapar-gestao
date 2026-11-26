"""Integridade no nível do banco (migração 0002), verificada no SQLite dos testes.

Os CHECKs e UNIQUEs são declarados nos modelos, então valem também com `db.create_all()`.
Os gatilhos RN03/RN16 só existem no PostgreSQL; aqui se testam as travas equivalentes do ORM.
"""
from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    Animal, Announcement, AnnouncementAck, AuditLog, AuditoriaImutavel, ExclusaoFisicaProibida,
    MedicalRecord, MedicationLog, Prescription, User, Vaccination, Whitelist,
)

HOJE = date.today()


def _animal(**kw):
    dados = dict(nome="Rex", sexo="Macho", porte="Médio", status_operacional="em acolhimento")
    dados.update(kw)
    a = Animal(**dados)
    db.session.add(a)
    db.session.commit()
    return a


def _falha_ao_gravar(obj):
    db.session.add(obj)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def _prescricao(animal, **kw):
    dados = dict(animal_id=animal.id, nome_medicamento="Amoxicilina", dosagem="1 comp",
                 horarios="08:00, 20:00", data_inicio=HOJE, data_fim=HOJE + timedelta(days=3))
    dados.update(kw)
    p = Prescription(**dados)
    db.session.add(p)
    db.session.commit()
    return p


# ---------------------------------------------------------------- domínios fechados

@pytest.mark.parametrize("status", Animal.VALID_STATUSES)
def test_status_validos_sao_aceitos(app, status):
    assert _animal(status_operacional=status).id


@pytest.mark.parametrize("campo,valor", [
    ("status_operacional", "perdido"),
    ("status_operacional", "Adotado"),
    ("sexo", "Gato"),
    ("porte", "Gigante"),
    ("peso_kg", 0),
    ("peso_kg", -2.5),
])
def test_animal_com_valor_fora_do_dominio_e_rejeitado(app, campo, valor):
    dados = dict(nome="X", sexo="Fêmea", porte="Pequeno", status_operacional="em acolhimento")
    dados[campo] = valor
    _falha_ao_gravar(Animal(**dados))


def test_peso_nulo_e_aceito(app):
    assert _animal(peso_kg=None).peso_kg is None


@pytest.mark.parametrize("modelo", [User, Whitelist])
def test_perfil_invalido_e_rejeitado(app, modelo):
    _falha_ao_gravar(modelo(email="x@gapar.org.br", role="Gerente"))


def test_perfis_validos_sao_aceitos(app):
    db.session.add_all([Whitelist(email="a@gapar.org.br", role="Administradora"),
                        User(email="v@gapar.org.br", role="Voluntaria")])
    db.session.commit()


# ---------------------------------------------------------------- datas

def test_prescricao_com_fim_antes_do_inicio_e_rejeitada(app):
    a = _animal()
    _falha_ao_gravar(Prescription(animal_id=a.id, nome_medicamento="M", dosagem="1", horarios="08:00",
                                  data_inicio=HOJE, data_fim=HOJE - timedelta(days=1)))


def test_prescricao_de_um_dia_e_aceita(app):
    assert _prescricao(_animal(), data_fim=HOJE).id


def test_reforco_antes_da_aplicacao_e_rejeitado(app):
    a = _animal()
    _falha_ao_gravar(Vaccination(animal_id=a.id, nome_vacina="V10", data_aplicacao=HOJE,
                                 data_reforco=HOJE - timedelta(days=1)))


@pytest.mark.parametrize("reforco", [None, HOJE, HOJE + timedelta(days=365)])
def test_reforco_valido_ou_ausente_e_aceito(app, reforco):
    a = _animal()
    db.session.add(Vaccination(animal_id=a.id, nome_vacina="V10", data_aplicacao=HOJE, data_reforco=reforco))
    db.session.commit()


# ---------------------------------------------------------------- unicidade (RF16 e avisos)

def test_dose_baixada_duas_vezes_e_rejeitada(app):
    p = _prescricao(_animal())
    db.session.add(MedicationLog(prescription_id=p.id, data_aplicacao=HOJE, horario_previsto="08:00",
                                 horario_aplicado="08:05"))
    db.session.commit()
    _falha_ao_gravar(MedicationLog(prescription_id=p.id, data_aplicacao=HOJE, horario_previsto="08:00",
                                   horario_aplicado="08:30"))
    assert MedicationLog.query.count() == 1


def test_nome_da_constraint_de_dose(app):
    nomes = {c.name for c in MedicationLog.__table__.constraints}
    assert "uq_medication_logs_dose" in nomes


def test_outras_doses_do_mesmo_dia_e_de_outro_dia_sao_aceitas(app):
    p = _prescricao(_animal())
    db.session.add_all([
        MedicationLog(prescription_id=p.id, data_aplicacao=HOJE, horario_previsto="08:00", horario_aplicado="08:00"),
        MedicationLog(prescription_id=p.id, data_aplicacao=HOJE, horario_previsto="20:00", horario_aplicado="20:00"),
        MedicationLog(prescription_id=p.id, data_aplicacao=HOJE + timedelta(days=1), horario_previsto="08:00",
                      horario_aplicado="08:00"),
    ])
    db.session.commit()
    assert MedicationLog.query.count() == 3


def test_confirmacao_de_aviso_duplicada_e_rejeitada(app):
    u = User(email="v@gapar.org.br", role="Voluntaria")
    db.session.add(u)
    db.session.commit()
    aviso = Announcement(tipo="TURNO", conteudo="Oi", autor_id=u.id)
    db.session.add(aviso)
    db.session.commit()
    db.session.add(AnnouncementAck(announcement_id=aviso.id, user_id=u.id))
    db.session.commit()
    _falha_ao_gravar(AnnouncementAck(announcement_id=aviso.id, user_id=u.id))


# ---------------------------------------------------------------- RN03 e RN16 (travas do ORM)

def test_animal_nao_pode_ser_apagado_fisicamente(app):
    a = _animal()
    db.session.add(Vaccination(animal_id=a.id, nome_vacina="V10", data_aplicacao=HOJE))
    db.session.commit()
    db.session.delete(a)
    with pytest.raises(ExclusaoFisicaProibida):
        db.session.commit()
    db.session.rollback()
    assert db.session.get(Animal, a.id) is not None
    assert Vaccination.query.count() == 1


@pytest.mark.parametrize("modelo", ["vacina", "prontuario"])
def test_historico_medico_nao_pode_ser_apagado(app, modelo):
    a = _animal()
    if modelo == "vacina":
        obj = Vaccination(animal_id=a.id, nome_vacina="V10", data_aplicacao=HOJE)
    else:
        obj = MedicalRecord(animal_id=a.id, tipo_evento="Consulta", diagnostico="ok")
    db.session.add(obj)
    db.session.commit()
    db.session.delete(obj)
    with pytest.raises(ExclusaoFisicaProibida):
        db.session.commit()
    db.session.rollback()


def test_exclusao_logica_de_animal_continua_funcionando(app):
    a = _animal()
    a.is_deleted = True
    db.session.commit()
    assert db.session.get(Animal, a.id).is_deleted is True


def test_auditoria_nao_pode_ser_alterada_nem_apagada(app):
    log = AuditLog(acao="TESTE", entidade="Animal")
    db.session.add(log)
    db.session.commit()

    log.detalhes = "adulterado"
    with pytest.raises(AuditoriaImutavel):
        db.session.commit()
    db.session.rollback()

    db.session.delete(log)
    with pytest.raises(AuditoriaImutavel):
        db.session.commit()
    db.session.rollback()
    assert db.session.get(AuditLog, log.id).detalhes is None


def test_constraints_existem_no_sqlite(app):
    """Garante que o create_all dos testes gera os CHECKs com os nomes da migração 0002."""
    sql = db.session.execute(text("select group_concat(sql, ' ') from sqlite_master where type='table'")).scalar()
    for nome in ["ck_animals_status_operacional", "ck_animals_sexo", "ck_animals_porte",
                 "ck_animals_peso_kg_positivo", "ck_users_role", "ck_whitelist_role",
                 "ck_prescriptions_periodo", "ck_vaccinations_reforco_apos_aplicacao",
                 "uq_medication_logs_dose", "uq_announcement_acks_aviso_usuaria"]:
        assert nome in sql


# ---------------------------------------------------------------- R8 (CP-01): FKs no SQLite

def test_sqlite_confere_chave_estrangeira(app):
    """Paridade com o PostgreSQL: vacina de animal inexistente é recusada pelo banco."""
    assert db.session.execute(text("PRAGMA foreign_keys")).scalar() == 1
    _falha_ao_gravar(Vaccination(animal_id=999999, nome_vacina="V10", data_aplicacao=HOJE))
