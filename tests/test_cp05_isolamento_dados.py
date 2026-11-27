"""CP-05 · Isolamento sanitário, camada de dados (REQ-41, REQ-43, REQ-44 e a parte de banco da REQ-45).

Spec: docs/sdd/CP03_05_FASE2_SPEC.md. As rotas (REQ-42) e o /api/hoje têm testes próprios; aqui
os isolamentos são gravados direto pelo ORM.
"""
import importlib.util
import os
import re
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import IsolationRecord
from app.models.animal import Animal
from app.models.base import ExclusaoFisicaProibida
from app.models.isolation import carregar_isolamentos_abertos
from app.utils.slug import gerar_slug_publico

RAIZ = Path(__file__).resolve().parent.parent
MIGRACAO = RAIZ / "migrations" / "versions" / "0007_isolamento_sanitario.py"
CONTRATOS_TS = RAIZ / "app" / "views" / "src" / "types" / "contratos.ts"
HOJE = date(2026, 11, 27)


def _animal(nome="Mel", status="disponível", publicado=False, **extra):
    animal = Animal(nome=nome, sexo="Fêmea", porte="Pequeno", status_operacional=status,
                    data_entrada=date.today(), **extra)
    if publicado:
        animal.is_publicado = True
        animal.slug_publico = gerar_slug_publico(nome)
    db.session.add(animal)
    db.session.commit()
    return animal


def _isolar(animal, motivo="Suspeita de cinomose", inicio=HOJE, **extra):
    registro = IsolationRecord(animal_id=animal.id, motivo=motivo, data_inicio=inicio, **extra)
    db.session.add(registro)
    db.session.commit()
    return registro


def _encerrar(registro, quando=None):
    registro.fim_real = quando or datetime(2026, 12, 5, 14, 30)
    db.session.commit()
    return registro


def _campos_da_interface(nome):
    fonte = CONTRATOS_TS.read_text(encoding="utf-8")
    corpo = re.search(r"export interface " + nome + r"\s*\{(.*?)\n\}", fonte, re.S).group(1)
    corpo = re.sub(r"/\*.*?\*/", "", corpo, flags=re.S)
    return set(re.findall(r"^\s*(\w+)\??\s*:", corpo, re.M))


@pytest.fixture
def contar_consultas(app):
    consultas = []

    def _anotar(_conn, _cursor, sql, *_args, **_kwargs):
        consultas.append(sql)

    event.listen(db.engine, "before_cursor_execute", _anotar)
    yield consultas
    event.remove(db.engine, "before_cursor_execute", _anotar)


# REQ-41 · migração 0007 (subprocesso, SQLite em arquivo) -----------------------------------

def _flask_db(banco, *args):
    env = {**os.environ, "FLASK_ENV": "development", "DATABASE_URL": f"sqlite:///{banco.as_posix()}",
           "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, "-m", "flask", "--app", "wsgi", "db", *args, "-d", str(RAIZ / "migrations")],
        cwd=RAIZ, env=env, capture_output=True, text=True, encoding="utf-8", timeout=180,
    )


def _colunas(banco, tabela="isolation_records"):
    with sqlite3.connect(banco) as con:
        return {linha[1] for linha in con.execute(f"PRAGMA table_info({tabela})")}


def _tabelas(banco):
    with sqlite3.connect(banco) as con:
        return {linha[0] for linha in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _indices(banco):
    with sqlite3.connect(banco) as con:
        return {nome: sql for nome, sql in con.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='isolation_records'")}


INSERIR_ANIMAL = (
    "INSERT INTO animals (id, nome, sexo, raca, porte, data_entrada, is_castrado, is_microchipado, is_idoso, "
    "status_operacional, is_deleted, created_at, updated_at, is_publicado, pausar_candidaturas) VALUES "
    "(1, 'Rex', 'Macho', 'SRD', 'Médio', '2026-01-01', 0, 0, 0, 'em acolhimento', 0, '2026-01-01', "
    "'2026-01-01', 0, 0)"
)
INSERIR_ISOLAMENTO = ("INSERT INTO isolation_records (animal_id, motivo, data_inicio, created_at, fim_real) "
                      "VALUES (1, 'Sarna', '2026-11-27', '2026-11-27', ?)")


@pytest.fixture
def banco_0007(tmp_path):
    banco = tmp_path / "cp05.db"
    resultado = _flask_db(banco, "upgrade")
    assert resultado.returncode == 0, resultado.stderr
    return banco


def test_migracao_0007_upgrade_downgrade_upgrade(banco_0007):
    banco = banco_0007
    assert "isolation_records" in _tabelas(banco)
    assert _indices(banco)["uq_isolation_aberto_por_animal"] == (
        "CREATE UNIQUE INDEX uq_isolation_aberto_por_animal ON isolation_records (animal_id) WHERE fim_real IS NULL")

    resultado = _flask_db(banco, "downgrade", "0006")
    assert resultado.returncode == 0, resultado.stderr
    assert "isolation_records" not in _tabelas(banco)

    resultado = _flask_db(banco, "upgrade")
    assert resultado.returncode == 0, resultado.stderr
    assert "isolation_records" in _tabelas(banco)


def test_migracao_0007_colunas_e_indices_do_modelo_iguais_aos_da_migracao(app, banco_0007):
    tabela = db.metadata.tables["isolation_records"]
    assert set(tabela.columns.keys()) == _colunas(banco_0007)
    assert {i.name for i in tabela.indexes} == set(_indices(banco_0007))


def test_migracao_0007_rn22_no_banco_migrado(banco_0007):
    with sqlite3.connect(banco_0007) as con:
        con.execute(INSERIR_ANIMAL)
        con.execute(INSERIR_ISOLAMENTO, ("2026-11-28 10:00:00",))   # encerrado
        con.execute(INSERIR_ISOLAMENTO, (None,))                    # aberto
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(INSERIR_ISOLAMENTO, (None,))                # segundo aberto (RN22)
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO isolation_records (animal_id, motivo, data_inicio, data_fim_prevista, "
                        "created_at) VALUES (1, 'x', '2026-11-27', '2026-11-26', '2026-11-27')")


def test_migracao_0007_downgrade_recusa_perder_historico(banco_0007):
    with sqlite3.connect(banco_0007) as con:
        con.execute(INSERIR_ANIMAL)
        con.execute(INSERIR_ISOLAMENTO, ("2026-11-28 10:00:00",))
    resultado = _flask_db(banco_0007, "downgrade", "0006")
    assert resultado.returncode != 0
    assert "recusado" in (resultado.stderr + resultado.stdout)
    assert "isolation_records" in _tabelas(banco_0007)


def test_migracao_0007_estrutura_do_arquivo():
    spec = importlib.util.spec_from_file_location("migracao_0007", MIGRACAO)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    fonte = MIGRACAO.read_text(encoding="utf-8")
    assert modulo.down_revision == "0006"
    assert modulo.TABELAS_RLS == ["isolation_records"]
    assert not re.search(r"^\s*(from|import)\s+app(\.|\s|$)", fonte, re.M)
    assert "postgresql_where=sa.text(FILTRO_ABERTO), sqlite_where=sa.text(FILTRO_ABERTO)" in fonte
    assert "EXECUTE FUNCTION gapar_bloquear_exclusao_fisica()" in fonte
    assert "DROP FUNCTION" not in fonte
    assert "DISABLE ROW LEVEL SECURITY" not in fonte


# REQ-41 · RN22, CHECK e RN03 pelo ORM ---------------------------------------------------------

def test_rn22_dois_isolamentos_abertos_no_mesmo_animal(app):
    animal = _animal()
    _isolar(animal)
    with pytest.raises(IntegrityError):
        _isolar(animal, motivo="Outro")
    db.session.rollback()
    assert IsolationRecord.query.count() == 1


def test_rn22_abrir_encerrar_e_reabrir(app):
    animal = _animal()
    primeiro = _encerrar(_isolar(animal))
    segundo = _isolar(animal, motivo="Recaída", inicio=HOJE + timedelta(days=20))
    assert primeiro.aberto is False and segundo.aberto is True
    _encerrar(segundo, datetime(2027, 1, 1))
    terceiro = _isolar(animal, motivo="Nova suspeita", inicio=HOJE + timedelta(days=60))
    assert IsolationRecord.aberto_do_animal(animal.id).id == terceiro.id
    assert animal.isolamentos.count() == 3


def test_rn22_vale_por_animal(app):
    _isolar(_animal(nome="A"))
    _isolar(_animal(nome="B"))
    assert IsolationRecord.query.filter(IsolationRecord.fim_real.is_(None)).count() == 2


def test_rn22_reabrir_encerrado_conflita_com_aberto(app):
    animal = _animal()
    antigo = _encerrar(_isolar(animal))
    _isolar(animal, motivo="Atual")
    antigo.fim_real = None
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_check_fim_previsto_antes_do_inicio(app):
    animal = _animal()
    db.session.add(IsolationRecord(animal_id=animal.id, motivo="x", data_inicio=HOJE,
                                   data_fim_prevista=HOJE - timedelta(days=1)))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_fim_previsto_no_mesmo_dia_e_aceito(app):
    assert _isolar(_animal(), data_fim_prevista=HOJE).data_fim_prevista == HOJE


@pytest.mark.parametrize("motivo", ["", "   "])
def test_check_motivo_preenchido(app, motivo):
    db.session.add(IsolationRecord(animal_id=_animal().id, motivo=motivo, data_inicio=HOJE))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_isolamento_exige_animal_existente(app):
    db.session.add(IsolationRecord(animal_id=999, motivo="x", data_inicio=HOJE))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_rn03_isolamento_nao_e_apagado(app):
    registro = _isolar(_animal())
    db.session.delete(registro)
    with pytest.raises(ExclusaoFisicaProibida):
        db.session.commit()
    db.session.rollback()
    assert IsolationRecord.query.count() == 1


# REQ-44 · RN17 ampliada: vitrine esconde o animal isolado ---------------------------------------

def test_vitrine_esconde_isolado_e_volta_ao_encerrar(app):
    isolado = _animal(nome="Isolada", publicado=True)
    livre = _animal(nome="Livre", publicado=True)
    registro = _isolar(isolado)

    assert [a.id for a in Animal.query_vitrine()] == [livre.id]
    assert Animal.buscar_publicado(isolado.slug_publico) is None
    assert db.session.get(Animal, isolado.id).is_publicado is True  # não despublica

    _encerrar(registro)
    assert {a.id for a in Animal.query_vitrine()} == {isolado.id, livre.id}
    assert Animal.buscar_publicado(isolado.slug_publico).id == isolado.id
    assert Animal.query_vitrine().order_by(None).count() == 2


def test_vitrine_isolamento_encerrado_nao_esconde(app):
    animal = _animal(publicado=True)
    _encerrar(_isolar(animal))
    _encerrar(_isolar(animal, inicio=HOJE + timedelta(days=30)), datetime(2027, 1, 30))
    assert Animal.buscar_publicado(animal.slug_publico).id == animal.id


def test_vitrine_rota_publica_esconde_isolado(app, client):
    app.config["FEATURES"] = {**app.config["FEATURES"], "vitrine": True}
    animal = _animal(publicado=True)
    slug = animal.slug_publico
    registro = _isolar(animal)
    assert client.get(f"/api/public/animais/{slug}").status_code == 404
    assert client.get("/api/public/animais").get_json()["animais"] == []
    _encerrar(registro)
    assert client.get(f"/api/public/animais/{slug}").status_code == 200


# REQ-43 · isolamento_aberto no to_dict, sem N+1 -------------------------------------------------

def test_to_dict_isolamento_aberto(app):
    animal = _animal()
    assert animal.to_dict()["isolamento_aberto"] is None
    registro = _isolar(animal, data_fim_prevista=HOJE + timedelta(days=10))
    resumo = db.session.get(Animal, animal.id).to_dict()["isolamento_aberto"]
    assert set(resumo) == _campos_da_interface("IsolamentoAbertoResumo")
    assert resumo == {"id": registro.id, "motivo": "Suspeita de cinomose", "data_inicio": HOJE.isoformat(),
                      "data_fim_prevista": (HOJE + timedelta(days=10)).isoformat()}
    _encerrar(registro)
    assert db.session.get(Animal, animal.id).to_dict()["isolamento_aberto"] is None


def test_to_dict_do_registro_igual_ao_contrato(app, admin_user, volunteer_user):
    registro = _isolar(_animal(), aberto_por_user_id=volunteer_user.id, protocolo_cuidados="Luvas")
    dados = registro.to_dict()
    assert set(dados) == _campos_da_interface("IsolamentoRegistro")
    assert (dados["aberto"], dados["fim_real"], dados["aberto_por"], dados["encerrado_por"]) == (True, None, "Vol", None)
    registro.encerrado_por_user_id = admin_user.id
    registro.observacoes_alta = "Recuperada"
    _encerrar(registro)
    db.session.expire_all()
    dados = db.session.get(IsolationRecord, registro.id).to_dict()
    assert dados["aberto"] is False
    assert dados["fim_real"] == "2026-12-05T14:30:00"
    assert dados["encerrado_por"] == "Admin"
    assert dados["observacoes_alta"] == "Recuperada"


def _pagina_com_isolados():
    animais = [_animal(nome=f"A{i}") for i in range(6)]
    _isolar(animais[1])
    _encerrar(_isolar(animais[2]))
    _isolar(animais[4], motivo="Sarna")
    return animais


def test_carregador_em_lote_sem_n_mais_1(app, contar_consultas):
    ids = [a.id for a in _pagina_com_isolados()]
    db.session.expire_all()
    pagina = Animal.query.filter(Animal.id.in_(ids)).order_by(Animal.id).all()
    contar_consultas.clear()

    carregar_isolamentos_abertos(pagina)
    assert len(contar_consultas) == 1
    contar_consultas.clear()

    fichas = [a.to_dict() for a in pagina]
    assert contar_consultas == []  # nenhuma consulta por animal
    assert [f["isolamento_aberto"]["motivo"] if f["isolamento_aberto"] else None for f in fichas] == \
        [None, "Suspeita de cinomose", None, None, "Sarna", None]


def test_selectinload_tambem_sem_n_mais_1(app, contar_consultas):
    ids = [a.id for a in _pagina_com_isolados()]
    db.session.expire_all()
    contar_consultas.clear()
    pagina = (Animal.query.options(selectinload(Animal.isolamento_aberto_registro))
              .filter(Animal.id.in_(ids)).order_by(Animal.id).all())
    fichas = [a.to_dict() for a in pagina]
    assert len(contar_consultas) == 2  # animais + isolamentos abertos da página
    assert sum(1 for f in fichas if f["isolamento_aberto"]) == 2


def test_carregador_lista_vazia(app, contar_consultas):
    assert carregar_isolamentos_abertos([]) == []
    assert contar_consultas == []


def test_sem_carregador_cada_ficha_consulta(app, contar_consultas):
    """Controle do teste de N+1: sem o carregador, cada `to_dict` faz a própria consulta."""
    ids = [a.id for a in _pagina_com_isolados()]
    db.session.expire_all()
    pagina = Animal.query.filter(Animal.id.in_(ids)).all()
    contar_consultas.clear()
    [a.to_dict() for a in pagina]
    assert len(contar_consultas) == len(pagina)


def test_query_abertos_e_historico(app, contar_consultas):
    a, b, excluido = _animal(nome="A"), _animal(nome="B"), _animal(nome="Excluido")
    _isolar(b, inicio=HOJE - timedelta(days=3))
    _isolar(a, inicio=HOJE)
    _isolar(excluido)
    excluido.is_deleted = True
    db.session.commit()
    _encerrar(_isolar(_animal(nome="C")))
    db.session.expire_all()
    contar_consultas.clear()
    abertos = IsolationRecord.query_abertos().all()
    nomes = [r.animal.nome for r in abertos]
    [r.to_dict() for r in abertos]
    assert nomes == ["B", "A"]
    assert len(contar_consultas) == 1

    _encerrar(IsolationRecord.aberto_do_animal(a.id))
    _isolar(a, motivo="Segundo", inicio=HOJE + timedelta(days=5))
    assert [r.motivo for r in IsolationRecord.query_do_animal(a.id)] == ["Segundo", "Suspeita de cinomose"]
