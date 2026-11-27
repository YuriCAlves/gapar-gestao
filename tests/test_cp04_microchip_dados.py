"""CP-04 · Microchip ISO de 15 dígitos, camada de dados (REQ-38, RN21, D1).

Spec: docs/sdd/CP03_05_FASE2_SPEC.md. As rotas (REQ-39, REQ-40) têm testes próprios.
"""
import importlib.util
import os
import re
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.animal import Animal

RAIZ = Path(__file__).resolve().parent.parent
MIGRACAO = RAIZ / "migrations" / "versions" / "0006_microchip_iso.py"
CONTRATOS_TS = RAIZ / "app" / "views" / "src" / "types" / "contratos.ts"
CHIP = "982000123456789"
CHIP_2 = "076000000000001"


def _animal(nome="Rex", chip=None, **extra):
    animal = Animal(nome=nome, sexo="Macho", porte="Médio", data_entrada=date.today(), **extra)
    if chip is not None:
        animal.numero_microchip = chip
    db.session.add(animal)
    db.session.commit()
    return animal


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


# REQ-38 · migração 0006 (subprocesso, SQLite em arquivo) -----------------------------------

def _flask_db(banco, *args):
    env = {**os.environ, "FLASK_ENV": "development", "DATABASE_URL": f"sqlite:///{banco.as_posix()}",
           "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, "-m", "flask", "--app", "wsgi", "db", *args, "-d", str(RAIZ / "migrations")],
        cwd=RAIZ, env=env, capture_output=True, text=True, encoding="utf-8", timeout=180,
    )


def _colunas(banco, tabela="animals"):
    with sqlite3.connect(banco) as con:
        return {linha[1] for linha in con.execute(f"PRAGMA table_info({tabela})")}


def _sql_animals(banco):
    with sqlite3.connect(banco) as con:
        return con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='animals'").fetchone()[0]


def _indices_animals(banco):
    with sqlite3.connect(banco) as con:
        return {nome: sql for nome, sql in con.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='animals'")}


INSERIR_ANIMAL_LEGADO = (
    "INSERT INTO animals (id, nome, sexo, raca, porte, data_entrada, is_castrado, is_microchipado, is_idoso, "
    "status_operacional, is_deleted, created_at, updated_at, is_publicado, pausar_candidaturas) VALUES "
    "({id}, 'Rex', 'Macho', 'SRD', 'Médio', '2026-01-01', 0, 1, 0, 'em acolhimento', 0, '2026-01-01', "
    "'2026-01-01', 0, 0)"
)


@pytest.fixture
def banco_0006(tmp_path):
    banco = tmp_path / "cp04.db"
    resultado = _flask_db(banco, "upgrade")
    assert resultado.returncode == 0, resultado.stderr
    return banco


def test_migracao_0006_upgrade_downgrade_upgrade(banco_0006):
    banco = banco_0006
    assert "numero_microchip" in _colunas(banco)
    assert "ck_animals_numero_microchip_formato" in _sql_animals(banco)
    assert "CREATE UNIQUE INDEX uq_animals_numero_microchip ON animals (numero_microchip)" == \
        _indices_animals(banco)["uq_animals_numero_microchip"]  # D1: UNIQUE simples, sem WHERE

    resultado = _flask_db(banco, "downgrade", "0005")
    assert resultado.returncode == 0, resultado.stderr
    assert "numero_microchip" not in _colunas(banco)
    assert "ck_animals_numero_microchip_formato" not in _sql_animals(banco)
    assert "uq_animals_numero_microchip" not in _indices_animals(banco)
    # Os CHECKs anteriores sobrevivem às recriações da tabela em batch
    for nome in ("ck_animals_status_operacional", "ck_animals_publicado_so_disponivel"):
        assert nome in _sql_animals(banco), nome

    resultado = _flask_db(banco, "upgrade")
    assert resultado.returncode == 0, resultado.stderr
    assert "numero_microchip" in _colunas(banco)


def test_migracao_0006_colunas_do_modelo_iguais_as_da_migracao(app, banco_0006):
    assert set(db.metadata.tables["animals"].columns.keys()) == _colunas(banco_0006)


def test_migracao_0006_preserva_legado(tmp_path):
    banco = tmp_path / "legado.db"
    assert _flask_db(banco, "upgrade", "0005").returncode == 0
    with sqlite3.connect(banco) as con:
        con.execute(INSERIR_ANIMAL_LEGADO.format(id=1))
    resultado = _flask_db(banco, "upgrade")
    assert resultado.returncode == 0, resultado.stderr
    with sqlite3.connect(banco) as con:
        assert con.execute("SELECT is_microchipado, numero_microchip FROM animals").fetchall() == [(1, None)]


@pytest.mark.parametrize("numero", ["98200012345678", "9820001234567890", "98200012345678A", " 82000123456789",
                                    "", "٩٨٢٠٠٠١٢٣٤٥٦٧٨٩"])
def test_migracao_0006_check_no_banco_migrado(banco_0006, numero):
    with sqlite3.connect(banco_0006) as con:
        con.execute(INSERIR_ANIMAL_LEGADO.format(id=1))
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("UPDATE animals SET numero_microchip = ? WHERE id = 1", (numero,))


def test_migracao_0006_unique_no_banco_migrado(banco_0006):
    with sqlite3.connect(banco_0006) as con:
        con.execute(INSERIR_ANIMAL_LEGADO.format(id=1))
        con.execute(INSERIR_ANIMAL_LEGADO.format(id=2))
        con.execute("UPDATE animals SET numero_microchip = ? WHERE id = 1", (CHIP,))
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("UPDATE animals SET numero_microchip = ? WHERE id = 2", (CHIP,))


def test_migracao_0006_downgrade_recusa_perder_numero(banco_0006):
    with sqlite3.connect(banco_0006) as con:
        con.execute(INSERIR_ANIMAL_LEGADO.format(id=1))
        con.execute("UPDATE animals SET numero_microchip = ?", (CHIP,))
    resultado = _flask_db(banco_0006, "downgrade", "0005")
    assert resultado.returncode != 0
    assert "recusado" in (resultado.stderr + resultado.stdout)
    assert "numero_microchip" in _colunas(banco_0006)


def test_migracao_0006_estrutura_do_arquivo():
    spec = importlib.util.spec_from_file_location("migracao_0006", MIGRACAO)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    fonte = MIGRACAO.read_text(encoding="utf-8")
    assert modulo.down_revision == "0005"
    assert modulo.TABELAS_RLS == []
    assert not re.search(r"^\s*(from|import)\s+app(\.|\s|$)", fonte, re.M)
    # SQL ANSI: sem regex proprietária (`~` do PostgreSQL, REGEXP, GLOB)
    assert "length(numero_microchip) = 15" in modulo.CHECK_CONDICAO
    assert "ltrim(numero_microchip, '0123456789') = ''" in modulo.CHECK_CONDICAO
    assert not re.search(r"~|REGEXP|GLOB|SIMILAR", modulo.CHECK_CONDICAO, re.I)


# REQ-38 · CHECK, UNIQUE e hook pelo ORM -------------------------------------------------------

@pytest.mark.parametrize("numero", ["98200012345678", "9820001234567890", "98200012345678A", "982-00012345678",
                                    "٩٨٢٠٠٠١٢٣٤٥٦٧٨٩"])
def test_check_formato_pelo_orm(app, numero):
    animal = _animal()
    animal.numero_microchip = numero
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_check_formato_por_sql_direto(app):
    animal = _animal()
    with pytest.raises(IntegrityError):
        db.session.execute(text("UPDATE animals SET numero_microchip = 'abcdefghijklmno' WHERE id = :id"),
                           {"id": animal.id})
    db.session.rollback()


def test_microchip_valido_e_gravado(app):
    animal = _animal(chip=CHIP)
    db.session.expire_all()
    assert db.session.get(Animal, animal.id).numero_microchip == CHIP


def test_unique_microchip_duplicado(app):
    _animal(chip=CHIP)
    with pytest.raises(IntegrityError):
        _animal(nome="Outro", chip=CHIP)
    db.session.rollback()


def test_unique_vale_tambem_para_excluido_e_adotado(app):
    """D1: UNIQUE simples. O número de um animal excluído ou adotado não pode ir para outro."""
    excluido = _animal(nome="Excluido", chip=CHIP, is_deleted=True)
    adotado = _animal(nome="Adotado", chip=CHIP_2, status_operacional=Animal.STATUS_ADOTADO)
    assert excluido.id and adotado.id
    for chip in (CHIP, CHIP_2):
        with pytest.raises(IntegrityError):
            _animal(nome="Novo", chip=chip)
        db.session.rollback()


def test_varios_animais_sem_microchip(app):
    for i in range(3):
        _animal(nome=f"Sem {i}")
    assert Animal.query.filter(Animal.numero_microchip.is_(None)).count() == 3


def test_preencher_numero_liga_is_microchipado(app):
    animal = _animal()
    assert animal.is_microchipado is False
    animal.numero_microchip = CHIP
    assert animal.is_microchipado is True
    db.session.commit()
    # Limpar o número não desliga o booleano (o chip continua no animal)
    animal.numero_microchip = None
    db.session.commit()
    db.session.expire_all()
    animal = db.session.get(Animal, animal.id)
    assert (animal.numero_microchip, animal.is_microchipado) == (None, True)


def test_numero_no_construtor_liga_is_microchipado(app):
    animal = Animal(nome="Rex", sexo="Macho", porte="Médio", numero_microchip=CHIP)
    assert animal.is_microchipado is True


@pytest.mark.parametrize("vazio", ["", "   "])
def test_vazio_vira_nulo(app, vazio):
    animal = _animal()
    animal.numero_microchip = vazio
    db.session.commit()
    assert animal.numero_microchip is None
    assert animal.is_microchipado is False


def test_legado_microchipado_sem_numero_e_aceito(app):
    animal = _animal(is_microchipado=True)
    db.session.expire_all()
    animal = db.session.get(Animal, animal.id)
    assert (animal.is_microchipado, animal.numero_microchip) == (True, None)


@pytest.mark.parametrize("numero,valido", [(CHIP, True), ("98200012345678", False), ("98200012345678A", False),
                                           ("٩٨٢٠٠٠١٢٣٤٥٦٧٨٩", False), (None, False), (982000123456789, False),
                                           (CHIP + "\n", False)])
def test_microchip_valido(numero, valido):
    assert Animal.microchip_valido(numero) is valido


def test_buscar_por_microchip(app):
    animal = _animal(chip=CHIP)
    _animal(nome="Excluido", chip=CHIP_2, is_deleted=True)
    assert Animal.buscar_por_microchip(CHIP).id == animal.id
    assert Animal.buscar_por_microchip(CHIP_2) is None
    assert Animal.buscar_por_microchip(CHIP_2, incluir_excluidos=True).nome == "Excluido"
    assert Animal.buscar_por_microchip("999999999999999") is None


@pytest.mark.parametrize("numero", ["123", "98200012345678A", "' OR 1=1 --", "", None])
def test_buscar_por_microchip_fora_do_formato_nao_consulta(app, contar_consultas, numero):
    assert Animal.buscar_por_microchip(numero) is None
    assert contar_consultas == []


def test_busca_por_microchip_usa_indice(app):
    plano = db.session.execute(text(
        "EXPLAIN QUERY PLAN SELECT id FROM animals WHERE numero_microchip = '982000123456789'")).fetchall()
    assert "uq_animals_numero_microchip" in " ".join(str(linha) for linha in plano)


# Contrato e superfície pública -----------------------------------------------------------------

def test_to_dict_tem_numero_microchip(app):
    assert _animal(chip=CHIP).to_dict()["numero_microchip"] == CHIP
    assert _animal(nome="Sem").to_dict()["numero_microchip"] is None


def test_resumo_microchip_igual_ao_contrato(app):
    animal = _animal(chip=CHIP, localizacao_baia="Baia 3")
    resumo = animal.to_resumo_microchip()
    assert set(resumo) == _campos_da_interface("ResumoMicrochip")
    assert resumo["localizacao_baia"] == "Baia 3"


def test_microchip_fora_da_vitrine(app):
    assert "numero_microchip" not in Animal.PUBLIC_ANIMAL_STRICT_KEYS
    animal = _animal(chip=CHIP, status_operacional=Animal.STATUS_DISPONIVEL)
    assert CHIP not in str(animal.to_public_dict())
