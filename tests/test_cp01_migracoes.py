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
