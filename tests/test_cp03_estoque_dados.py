"""CP-03 · Estoque com lotes FEFO, camada de dados (REQ-32, REQ-33 e a parte de banco da REQ-37).

Spec: docs/sdd/CP03_05_FASE2_SPEC.md. O `inventory_service` e as rotas têm testes próprios; aqui
os registros são gravados direto pelo ORM para exercitar CHECK, UNIQUE, RN03, RN19 e os campos
derivados do contrato (`ItemEstoque`, `LoteEstoque`, `MovimentoEstoque`).
"""
import importlib.util
import os
import re
import sqlite3
import subprocess
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import InventoryBatch, InventoryItem, InventoryMovement, User
from app.models.base import AuditoriaImutavel, ExclusaoFisicaProibida, RegistroImutavel

RAIZ = Path(__file__).resolve().parent.parent
MIGRACAO = RAIZ / "migrations" / "versions" / "0005_estoque_insumos.py"
CONTRATOS_TS = RAIZ / "app" / "views" / "src" / "types" / "contratos.ts"
TABELAS = ("inventory_items", "inventory_batches", "inventory_movements")
HOJE = date(2026, 11, 27)


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


def _movimento(lote, tipo="ENTRADA", quantidade="10", saldo_apos="10", motivo="Compra", **extra):
    mov = InventoryMovement(batch_id=lote.id, tipo=tipo, quantidade=Decimal(quantidade),
                            saldo_apos=Decimal(saldo_apos), motivo=motivo, **extra)
    db.session.add(mov)
    db.session.commit()
    return mov


def _falha_integridade(obj):
    db.session.add(obj)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def _campos_da_interface(nome):
    fonte = CONTRATOS_TS.read_text(encoding="utf-8")
    corpo = re.search(r"export interface " + nome + r"\s*\{(.*?)\n\}", fonte, re.S).group(1)
    corpo = re.sub(r"/\*.*?\*/", "", corpo, flags=re.S)
    return set(re.findall(r"^\s*(\w+)\??\s*:", corpo, re.M))


# REQ-32/33 · migração 0005 (subprocesso, SQLite em arquivo) --------------------------------

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


def _indices(banco, tabela):
    with sqlite3.connect(banco) as con:
        return {nome: sql for nome, sql in con.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name=?", (tabela,))}


def _carregar_migracao():
    spec = importlib.util.spec_from_file_location("migracao_0005", MIGRACAO)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def banco_0005(tmp_path):
    banco = tmp_path / "cp03.db"
    resultado = _flask_db(banco, "upgrade")
    assert resultado.returncode == 0, resultado.stderr
    return banco


def test_migracao_0005_upgrade_downgrade_upgrade(banco_0005):
    banco = banco_0005
    assert set(TABELAS) <= _tabelas(banco)
    assert "(item_id, data_validade, id)" in _indices(banco, "inventory_batches")["ix_batches_fefo"]

    resultado = _flask_db(banco, "downgrade", "0004")
    assert resultado.returncode == 0, resultado.stderr
    assert not set(TABELAS) & _tabelas(banco)

    resultado = _flask_db(banco, "upgrade")
    assert resultado.returncode == 0, resultado.stderr
    assert set(TABELAS) <= _tabelas(banco)


def test_migracao_0005_colunas_do_modelo_iguais_as_da_migracao(app, banco_0005):
    for tabela in TABELAS:
        assert set(db.metadata.tables[tabela].columns.keys()) == _colunas(banco_0005, tabela), tabela


def test_migracao_0005_indices_do_modelo_iguais_aos_da_migracao(app, banco_0005):
    for tabela in TABELAS:
        do_modelo = {i.name for i in db.metadata.tables[tabela].indexes}
        da_migracao = {n for n in _indices(banco_0005, tabela) if not n.startswith("sqlite_autoindex")}
        assert do_modelo == da_migracao, tabela


def test_migracao_0005_downgrade_recusa_perder_estoque(banco_0005):
    with sqlite3.connect(banco_0005) as con:
        con.execute("INSERT INTO inventory_items (nome, categoria, unidade, estoque_minimo, is_active, is_deleted, "
                    "created_at, updated_at) VALUES ('V10', 'Vacina', 'doses', 0, 1, 0, '2026-11-27', '2026-11-27')")
    resultado = _flask_db(banco_0005, "downgrade", "0004")
    assert resultado.returncode != 0
    assert "recusado" in (resultado.stderr + resultado.stdout)
    assert "inventory_items" in _tabelas(banco_0005)


def test_migracao_0005_checks_no_banco_migrado(banco_0005):
    with sqlite3.connect(banco_0005) as con:
        con.execute("INSERT INTO inventory_items (id, nome, categoria, unidade, estoque_minimo, is_active, is_deleted, "
                    "created_at, updated_at) VALUES (1, 'V10', 'Vacina', 'doses', 0, 1, 0, '2026-11-27', '2026-11-27')")
        con.execute("INSERT INTO inventory_batches (id, item_id, codigo_lote, saldo_atual, created_at) "
                    "VALUES (1, 1, 'L1', 5, '2026-11-27')")
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("UPDATE inventory_batches SET saldo_atual = saldo_atual - 6 WHERE id = 1")  # RN18
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO inventory_batches (item_id, codigo_lote, saldo_atual, created_at) "
                        "VALUES (1, 'L1', 1, '2026-11-27')")  # lote duplicado no item
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO inventory_movements (batch_id, tipo, quantidade, saldo_apos, motivo, created_at) "
                        "VALUES (1, 'ENTRADA', 0, 5, 'x', '2026-11-27')")
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO inventory_items (nome, categoria, unidade, estoque_minimo, is_active, is_deleted, "
                        "created_at, updated_at) VALUES ('X', 'Brinquedo', 'doses', 0, 1, 0, '2026-11-27', '2026-11-27')")


def test_migracao_0005_estrutura_do_arquivo():
    modulo = _carregar_migracao()
    fonte = MIGRACAO.read_text(encoding="utf-8")
    assert modulo.down_revision == "0004"
    assert modulo.TABELAS_RLS == list(TABELAS)
    assert modulo.TABELAS_SEM_EXCLUSAO == ["inventory_items", "inventory_batches"]
    assert modulo.TABELAS_IMUTAVEIS == ["inventory_movements"]
    assert not re.search(r"^\s*(from|import)\s+app(\.|\s|$)", fonte, re.M)
    # Gatilho RN19: mesmo padrão da 0002
    funcao = modulo.FUNCAO_IMUTAVEL
    assert "gapar_bloquear_mutacao_registro_imutavel()" in funcao
    assert "SET search_path = ''" in funcao
    assert "ERRCODE = 'restrict_violation'" in funcao
    # RN03 reaproveita a função da 0002 (que não é recriada nem apagada aqui)
    assert "EXECUTE FUNCTION gapar_bloquear_exclusao_fisica()" in fonte
    assert "DROP FUNCTION IF EXISTS gapar_bloquear_exclusao_fisica" not in fonte
    assert "BEFORE UPDATE OR DELETE" in fonte and "BEFORE TRUNCATE" in fonte
    # O SQL passa por sqlalchemy.text(): nada de porcentagem nem dois-pontos seguidos de nome
    for sql in (funcao,):
        assert "%" not in sql and not re.search(r":\w", sql)
    # O RLS nunca é desligado
    assert "DISABLE ROW LEVEL SECURITY" not in fonte


# REQ-32 · CHECKs e UNIQUE pelo ORM ----------------------------------------------------------

def test_check_saldo_do_lote_nunca_negativo(app):
    item = _item()
    _falha_integridade(InventoryBatch(item_id=item.id, codigo_lote="L1", saldo_atual=Decimal("-0.01")))


def test_check_saldo_negativo_por_update_em_massa(app):
    lote = _lote(_item(), saldo="1")
    with pytest.raises(IntegrityError):
        db.session.execute(text("UPDATE inventory_batches SET saldo_atual = saldo_atual - 2 WHERE id = :id"),
                           {"id": lote.id})
    db.session.rollback()


def test_saldo_zero_e_aceito(app):
    assert _lote(_item(), saldo="0").saldo_atual == 0


@pytest.mark.parametrize("quantidade", ["0", "-1"])
def test_check_quantidade_do_movimento_positiva(app, quantidade):
    lote = _lote(_item())
    _falha_integridade(InventoryMovement(batch_id=lote.id, tipo="ENTRADA", quantidade=Decimal(quantidade),
                                         saldo_apos=Decimal("10"), motivo="x"))


def test_check_saldo_apos_nao_negativo(app):
    lote = _lote(_item())
    _falha_integridade(InventoryMovement(batch_id=lote.id, tipo="PERDA", quantidade=Decimal("1"),
                                         saldo_apos=Decimal("-1"), motivo="x"))


def test_check_tipo_do_movimento(app):
    lote = _lote(_item())
    _falha_integridade(InventoryMovement(batch_id=lote.id, tipo="ROUBO", quantidade=Decimal("1"),
                                         saldo_apos=Decimal("9"), motivo="x"))


@pytest.mark.parametrize("motivo", ["", "   "])
def test_check_motivo_preenchido(app, motivo):
    lote = _lote(_item())
    _falha_integridade(InventoryMovement(batch_id=lote.id, tipo="PERDA", quantidade=Decimal("1"),
                                         saldo_apos=Decimal("9"), motivo=motivo))


@pytest.mark.parametrize("campo,valor", [("categoria", "Brinquedo"), ("categoria", "vacina"),
                                         ("unidade", "litros"), ("estoque_minimo", Decimal("-1"))])
def test_check_item(app, campo, valor):
    dados = {"nome": "X", "categoria": "Vacina", "unidade": "doses", "estoque_minimo": Decimal("0"), campo: valor}
    _falha_integridade(InventoryItem(**dados))


def test_todas_as_categorias_e_unidades_do_contrato_sao_aceitas(app):
    fonte = CONTRATOS_TS.read_text(encoding="utf-8")
    categorias = re.findall(r'"([^"]+)"', re.search(r"type CategoriaInsumo =(.*?);", fonte, re.S).group(1))
    unidades = re.findall(r'"([^"]+)"', re.search(r"type UnidadeInsumo =(.*?);", fonte, re.S).group(1))
    tipos = re.findall(r'"([^"]+)"', re.search(r"type TipoMovimento =(.*?);", fonte, re.S).group(1))
    assert tuple(categorias) == InventoryItem.CATEGORIAS
    assert tuple(unidades) == InventoryItem.UNIDADES
    assert tuple(tipos) == InventoryMovement.TIPOS
    for i, categoria in enumerate(categorias):
        _item(nome=f"Item {i}", categoria=categoria, unidade=unidades[i % len(unidades)])
    lote = _lote(InventoryItem.query.first())
    for tipo in tipos:
        _movimento(lote, tipo=tipo, quantidade="1", saldo_apos="5")


def test_unique_lote_duplicado_no_mesmo_item(app):
    item = _item()
    _lote(item, codigo="ABC")
    _falha_integridade(InventoryBatch(item_id=item.id, codigo_lote="ABC", saldo_atual=Decimal("1")))


def test_mesmo_codigo_de_lote_em_itens_diferentes(app):
    _lote(_item(nome="V8"), codigo="ABC")
    _lote(_item(nome="V10"), codigo="ABC")
    assert InventoryBatch.query.count() == 2


def test_lote_exige_item_existente(app):
    _falha_integridade(InventoryBatch(item_id=999, codigo_lote="L1", saldo_atual=Decimal("1")))


def test_numeric_guarda_duas_casas(app):
    lote = _lote(_item(), saldo="2.75")
    db.session.expire_all()
    assert db.session.get(InventoryBatch, lote.id).saldo_atual == Decimal("2.75")


# RN19 · movimento imutável pelo ORM -----------------------------------------------------------

def test_rn19_movimento_nao_pode_ser_alterado(app):
    mov = _movimento(_lote(_item()))
    mov.quantidade = Decimal("99")
    with pytest.raises(RegistroImutavel, match="RN19"):
        db.session.commit()
    db.session.rollback()
    db.session.expire_all()
    assert db.session.get(InventoryMovement, mov.id).quantidade == Decimal("10")


def test_rn19_movimento_nao_pode_ser_apagado(app):
    mov = _movimento(_lote(_item()))
    db.session.delete(mov)
    with pytest.raises(RegistroImutavel):
        db.session.commit()
    db.session.rollback()
    assert InventoryMovement.query.count() == 1


def test_rn19_excecao_cai_no_tratador_da_auditoria():
    assert issubclass(RegistroImutavel, AuditoriaImutavel)


def test_rn16_auditoria_continua_imutavel(app):
    from app.models import AuditLog
    log = AuditLog(acao="TESTE", entidade="Teste")
    db.session.add(log)
    db.session.commit()
    log.acao = "OUTRA"
    with pytest.raises(AuditoriaImutavel, match="RN16"):
        db.session.commit()
    db.session.rollback()


# RN03 · item e lote sem exclusão física pelo ORM ------------------------------------------------

def test_rn03_item_nao_e_apagado(app):
    item = _item()
    db.session.delete(item)
    with pytest.raises(ExclusaoFisicaProibida):
        db.session.commit()
    db.session.rollback()
    assert InventoryItem.query.count() == 1


def test_rn03_lote_nao_e_apagado(app):
    lote = _lote(_item())
    db.session.delete(lote)
    with pytest.raises(ExclusaoFisicaProibida):
        db.session.commit()
    db.session.rollback()
    assert InventoryBatch.query.count() == 1


def test_item_com_lote_pode_ser_editado(app):
    item = _item()
    _lote(item)
    item.nome = "V10 Plus"
    item.is_active = False
    db.session.commit()
    assert db.session.get(InventoryItem, item.id).nome == "V10 Plus"


# Derivados do contrato (ItemEstoque, LoteEstoque, MovimentoEstoque) ---------------------------

def test_saldo_total_ignora_lotes_vencidos(app):
    item = _item()
    _lote(item, "VENCIDO", "5", HOJE - timedelta(days=1))
    _lote(item, "HOJE", "2", HOJE)            # vence hoje: ainda vale hoje (RN20)
    _lote(item, "FUTURO", "3.5", HOJE + timedelta(days=10))
    _lote(item, "SEM", "1")
    assert item.saldo_total(HOJE) == Decimal("6.5")
    assert item.to_dict(HOJE)["saldo_total"] == 6.5


def test_saldo_total_sem_lotes_e_zero(app):
    dados = _item().to_dict(HOJE)
    assert dados["saldo_total"] == 0.0
    assert dados["proxima_validade"] is None


@pytest.mark.parametrize("minimo,esperado", [("10", True), ("6.5", False), ("6", False), ("0", False)])
def test_abaixo_do_minimo(app, minimo, esperado):
    item = _item(minimo=minimo)
    _lote(item, "A", "6.5", HOJE + timedelta(days=5))
    _lote(item, "VENCIDO", "100", HOJE - timedelta(days=5))  # não conta
    assert item.to_dict(HOJE)["abaixo_do_minimo"] is esperado
    assert item.abaixo_do_minimo(HOJE) is esperado


def test_proxima_validade_so_lotes_com_saldo_e_nao_vencidos(app):
    item = _item()
    _lote(item, "VENCIDO", "5", HOJE - timedelta(days=1))
    _lote(item, "ZERADO", "0", HOJE + timedelta(days=1))
    _lote(item, "PROXIMO", "1", HOJE + timedelta(days=3))
    _lote(item, "LONGE", "1", HOJE + timedelta(days=30))
    _lote(item, "SEM", "1")
    assert item.to_dict(HOJE)["proxima_validade"] == (HOJE + timedelta(days=3)).isoformat()


def test_lote_vencido_e_vence_em_dias(app):
    item = _item()
    vencido = _lote(item, "V", "1", HOJE - timedelta(days=4)).to_dict(HOJE)
    hoje = _lote(item, "H", "1", HOJE).to_dict(HOJE)
    futuro = _lote(item, "F", "1", HOJE + timedelta(days=7)).to_dict(HOJE)
    sem = _lote(item, "S", "1").to_dict(HOJE)
    assert (vencido["vencido"], vencido["vence_em_dias"]) == (True, -4)
    assert (hoje["vencido"], hoje["vence_em_dias"]) == (False, 0)
    assert (futuro["vencido"], futuro["vence_em_dias"]) == (False, 7)
    assert (sem["vencido"], sem["vence_em_dias"], sem["data_validade"]) == (False, None, None)


def test_derivados_usam_tempo_hoje(app, monkeypatch):
    from app.utils import tempo
    item = _item()
    lote = _lote(item, "L", "3", date(2030, 1, 10))
    monkeypatch.setattr(tempo, "hoje", lambda: date(2030, 1, 10))
    assert lote.to_dict()["vencido"] is False and item.to_dict()["saldo_total"] == 3.0
    monkeypatch.setattr(tempo, "hoje", lambda: date(2030, 1, 11))
    assert lote.to_dict()["vencido"] is True and lote.to_dict()["vence_em_dias"] == -1
    assert item.to_dict()["saldo_total"] == 0.0


def _ordem_fefo():
    """Lotes criados fora de ordem de propósito (o id não pode decidir sozinho)."""
    item = _item()
    sem_1 = _lote(item, "SEM-1", "1")
    longe = _lote(item, "LONGE", "1", HOJE + timedelta(days=60))
    vencido_antigo = _lote(item, "VENC-ANTIGO", "1", HOJE - timedelta(days=30))
    perto = _lote(item, "PERTO", "1", HOJE + timedelta(days=2))
    empate_a = _lote(item, "EMPATE-A", "1", HOJE + timedelta(days=10))
    empate_b = _lote(item, "EMPATE-B", "1", HOJE + timedelta(days=10))
    zerado = _lote(item, "ZERADO", "0", HOJE + timedelta(days=1))
    vencido_recente = _lote(item, "VENC-RECENTE", "1", HOJE - timedelta(days=1))
    sem_2 = _lote(item, "SEM-2", "1")
    hoje = _lote(item, "HOJE", "1", HOJE)
    return item, locals()


def test_fefo_ordem_do_detalhe(app):
    item, l = _ordem_fefo()
    esperado = ["HOJE", "ZERADO", "PERTO", "EMPATE-A", "EMPATE-B", "LONGE", "SEM-1", "SEM-2",
                "VENC-ANTIGO", "VENC-RECENTE"]
    assert [lote.codigo_lote for lote in item.lotes_fefo(HOJE)] == esperado


def test_fefo_utilizaveis_sem_vencidos_nem_zerados(app):
    item, _ = _ordem_fefo()
    lotes = InventoryBatch.query_fefo_utilizaveis(item.id, HOJE).all()
    assert [lote.codigo_lote for lote in lotes] == ["HOJE", "PERTO", "EMPATE-A", "EMPATE-B", "LONGE",
                                                     "SEM-1", "SEM-2"]


def test_fefo_utilizaveis_so_do_item(app):
    item, _ = _ordem_fefo()
    outro = _item(nome="Outro")
    _lote(outro, "X", "5", HOJE + timedelta(days=1))
    assert all(lote.item_id == item.id for lote in InventoryBatch.query_fefo_utilizaveis(item.id, HOJE))


def test_query_vencendo(app):
    item = _item()
    _lote(item, "VENCIDO", "1", HOJE - timedelta(days=3))
    _lote(item, "30D", "1", HOJE + timedelta(days=30))
    _lote(item, "31D", "1", HOJE + timedelta(days=31))
    _lote(item, "ZERADO", "0", HOJE + timedelta(days=5))
    _lote(item, "SEM", "1")
    inativo = _item(nome="Inativo", is_active=False)
    _lote(inativo, "INATIVO", "1", HOJE + timedelta(days=1))
    assert [lote.codigo_lote for lote in InventoryBatch.query_vencendo(HOJE)] == ["VENCIDO", "30D"]


def test_query_listagem(app):
    _item(nome="B", categoria="Ração", unidade="kg")
    _item(nome="A")
    _item(nome="Inativo", is_active=False)
    _item(nome="Excluido", is_deleted=True)
    assert [i.nome for i in InventoryItem.query_listagem()] == ["A", "B"]
    assert [i.nome for i in InventoryItem.query_listagem(incluir_inativos=True)] == ["A", "B", "Inativo"]
    assert [i.nome for i in InventoryItem.query_listagem(categoria="Ração")] == ["B"]


def test_to_dict_do_item_igual_ao_contrato(app):
    dados = _item(minimo="2.5").to_dict(HOJE)
    assert set(dados) == _campos_da_interface("ItemEstoque")
    assert dados["estoque_minimo"] == 2.5 and isinstance(dados["estoque_minimo"], float)
    assert dados["is_active"] is True


def test_to_dict_do_lote_igual_ao_contrato(app):
    dados = _lote(_item(), saldo="4.25", validade=HOJE).to_dict(HOJE)
    assert set(dados) == _campos_da_interface("LoteEstoque")
    assert dados["saldo_atual"] == 4.25 and isinstance(dados["saldo_atual"], float)
    assert dados["data_validade"] == HOJE.isoformat()


def test_to_dict_do_movimento_igual_ao_contrato(app, admin_user):
    from app.models import Animal
    animal = Animal(nome="Rex", sexo="Macho", porte="Médio", data_entrada=HOJE)
    db.session.add(animal)
    db.session.commit()
    mov = _movimento(_lote(_item()), tipo="SAIDA_USO", quantidade="1.5", saldo_apos="8.5", motivo="Vacina aplicada",
                     animal_id=animal.id, user_id=admin_user.id)
    dados = mov.to_dict()
    assert set(dados) == _campos_da_interface("MovimentoEstoque")
    assert dados["quantidade"] == 1.5 and dados["saldo_apos"] == 8.5
    assert dados["registrado_por"] == "Admin"
    assert dados["animal_id"] == animal.id
    assert _movimento(_lote(_item(nome="Y"), codigo="Z")).to_dict()["registrado_por"] is None


def test_movimento_com_usuaria_apagada_fica_sem_autoria(app):
    usuaria = User(email="tmp@gapar.org.br", name="Tmp", role="Voluntaria")
    db.session.add(usuaria)
    db.session.commit()
    mov = _movimento(_lote(_item()), user_id=usuaria.id)
    # ON DELETE SET NULL no banco, sem o ORM reescrever o movimento (seria UPDATE em registro
    # imutável). No PostgreSQL esse SET NULL é um UPDATE e o gatilho RN19 o recusa, como acontece
    # com audit_logs (RN16): usuárias nunca são apagadas, só desativadas na whitelist (RN14).
    db.session.execute(text("DELETE FROM users WHERE id = :id"), {"id": usuaria.id})
    db.session.commit()
    db.session.expire_all()
    assert db.session.get(InventoryMovement, mov.id).user_id is None


def test_movimentos_do_item_mais_recentes_primeiro(app):
    item = _item()
    lote_a, lote_b = _lote(item, "A"), _lote(item, "B")
    ids = [_movimento(lote_a).id, _movimento(lote_b).id, _movimento(lote_a).id]
    _movimento(_lote(_item(nome="Outro"), "C"))
    assert [m.id for m in InventoryMovement.query_do_item(item.id)] == list(reversed(ids))
    assert len(InventoryMovement.query_do_item(item.id, limite=2).all()) == 2
