"""CP-01 · Migrações (REQ-08 e REQ-09, Gate 1).

As migrações rodam em subprocesso (`flask db ...`) sobre um SQLite em arquivo temporário: assim o
`fileConfig` do Alembic não mexe nos loggers da suíte e o teste exercita o caminho real de deploy.
"""
import importlib.util
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from app.extensions import db

RAIZ = Path(__file__).resolve().parent.parent
VERSOES = RAIZ / "migrations" / "versions"


def _carregar(arquivo):
    spec = importlib.util.spec_from_file_location(f"migracao_{arquivo.stem}", arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


# REQ-08 ------------------------------------------------------------------------------------

def test_toda_tabela_tem_rls(app):
    com_rls = set()
    for arquivo in sorted(VERSOES.glob("*.py")):
        com_rls |= set(getattr(_carregar(arquivo), "TABELAS_RLS", []))
    sem_rls = set(db.metadata.tables) - com_rls
    assert not sem_rls, f"Tabelas sem ENABLE ROW LEVEL SECURITY em nenhuma migração: {sorted(sem_rls)}"


# REQ-09 ------------------------------------------------------------------------------------

def _flask_db(banco, *args):
    env = {**os.environ, "FLASK_ENV": "development", "DATABASE_URL": f"sqlite:///{banco.as_posix()}",
           "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, "-m", "flask", "--app", "wsgi", "db", *args, "-d", str(RAIZ / "migrations")],
        cwd=RAIZ, env=env, capture_output=True, text=True, encoding="utf-8", timeout=180,
    )


def _colunas(banco, tabela):
    with sqlite3.connect(banco) as con:
        return {linha[1] for linha in con.execute(f"PRAGMA table_info({tabela})")}


def _tabelas(banco):
    with sqlite3.connect(banco) as con:
        return {linha[0] for linha in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


@pytest.fixture
def banco_migrado(tmp_path):
    banco = tmp_path / "migracao.db"
    resultado = _flask_db(banco, "upgrade")
    assert resultado.returncode == 0, resultado.stderr
    return banco


NOVAS_NAO_APTOS = {"nome_bidx", "cpf_cifrado", "cpf_bidx", "telefone_cifrado", "telefone_bidx"}
NOVAS_ADOCOES = {"adotante_cpf_cifrado", "adotante_cpf_bidx", "adotante_endereco_cifrado"}


def test_upgrade_downgrade_0003a(banco_migrado):
    banco = banco_migrado
    assert NOVAS_NAO_APTOS <= _colunas(banco, "non_eligible_people")
    assert {"cpf", "telefone"} <= _colunas(banco, "non_eligible_people")  # legado preservado
    assert NOVAS_ADOCOES <= _colunas(banco, "adoptions")
    assert "rate_limit_buckets" in _tabelas(banco)

    resultado = _flask_db(banco, "downgrade", "0002")
    assert resultado.returncode == 0, resultado.stderr
    assert not NOVAS_NAO_APTOS & _colunas(banco, "non_eligible_people")
    assert "rate_limit_buckets" not in _tabelas(banco)

    assert _flask_db(banco, "upgrade").returncode == 0


def test_modelo_e_migracao_tem_as_mesmas_colunas(app, banco_migrado):
    for tabela in ("non_eligible_people", "adoptions", "rate_limit_buckets"):
        assert set(db.metadata.tables[tabela].columns.keys()) == _colunas(banco_migrado, tabela), tabela


def test_downgrade_recusa_perder_dado_so_cifrado(banco_migrado):
    with sqlite3.connect(banco_migrado) as con:
        con.execute("INSERT INTO non_eligible_people (nome, motivo_impedimento, cpf_cifrado, created_at) "
                    "VALUES ('X', 'y', 'cifra', '2026-11-26 00:00:00')")
    resultado = _flask_db(banco_migrado, "downgrade", "0002")
    assert resultado.returncode != 0
    assert "recusado" in (resultado.stderr + resultado.stdout)
    assert "cpf_cifrado" in _colunas(banco_migrado, "non_eligible_people")


# Parecer do gatekeeper: PRAGMA foreign_keys desligado durante as migrações no SQLite ----------

MIGRACAO_QUE_RECRIA_ANIMALS = '''"""teste: recria a tabela animals (como faria uma migração futura em batch)

Revision ID: 9999_teste
Revises: {anterior}
"""
from alembic import op
import sqlalchemy as sa

revision = "9999_teste"
down_revision = "{anterior}"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("animals", recreate="always") as batch_op:
        batch_op.alter_column("pelagem", type_=sa.String(60))


def downgrade():
    pass
'''


def _ultima_revisao():
    revisoes = {}
    for arquivo in VERSOES.glob("*.py"):
        modulo = _carregar(arquivo)
        revisoes[modulo.revision] = modulo.down_revision
    anteriores = set(revisoes.values())
    return next(r for r in revisoes if r not in anteriores)


def test_migracao_em_batch_nao_apaga_filhos_no_sqlite(tmp_path):
    """Com FKs ligadas, recriar `animals` zeraria `announcements.animal_id` (ON DELETE SET NULL)."""
    import shutil
    pasta = tmp_path / "migrations"
    shutil.copytree(RAIZ / "migrations", pasta, ignore=shutil.ignore_patterns("__pycache__"))
    anterior = _ultima_revisao()
    (pasta / "versions" / "9999_teste.py").write_text(
        MIGRACAO_QUE_RECRIA_ANIMALS.replace("{anterior}", anterior), encoding="utf-8")

    banco = tmp_path / "fk.db"
    env = {**os.environ, "FLASK_ENV": "development", "DATABASE_URL": f"sqlite:///{banco.as_posix()}",
           "PYTHONIOENCODING": "utf-8"}

    def flask_db(*args):
        return subprocess.run([sys.executable, "-m", "flask", "--app", "wsgi", "db", *args, "-d", str(pasta)],
                              cwd=RAIZ, env=env, capture_output=True, text=True, encoding="utf-8", timeout=180)

    assert flask_db("upgrade", anterior).returncode == 0
    with sqlite3.connect(banco) as con:
        con.execute("INSERT INTO users (id, email, role, is_active, created_at, updated_at) "
                    "VALUES (1, 'a@gapar.org.br', 'Administradora', 1, '2026-01-01', '2026-01-01')")
        con.execute("INSERT INTO animals (id, nome, sexo, raca, porte, data_entrada, is_castrado, is_microchipado, "
                    "is_idoso, status_operacional, is_deleted, created_at, updated_at) VALUES "
                    "(1, 'Rex', 'Macho', 'SRD', 'Médio', '2026-01-01', 0, 0, 0, 'disponível', 0, "
                    "'2026-01-01', '2026-01-01')")
        con.execute("INSERT INTO announcements (tipo, conteudo, categoria, is_urgente, is_fixado, autor_id, "
                    "animal_id, created_at) VALUES ('TURNO', 'c', 'Geral', 0, 0, 1, 1, '2026-01-01')")

    resultado = flask_db("upgrade")
    assert resultado.returncode == 0, resultado.stderr
    with sqlite3.connect(banco) as con:
        assert con.execute("SELECT animal_id FROM announcements").fetchall() == [(1,)]
        assert con.execute("SELECT COUNT(*) FROM animals").fetchone() == (1,)
