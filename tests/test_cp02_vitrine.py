"""CP-02 · Vitrine pública, camada de dados (REQ-21, 22, 23, 25, 26 e apoio da REQ-29).

Spec: docs/sdd/CP02_VITRINE_SPEC.md. As rotas (REQ-24, 27, 28) têm testes próprios; aqui os
animais são publicados atribuindo os campos direto no modelo.
"""
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

from app.extensions import db
from app.models.animal import Animal
from app.utils.slug import SLUG_PUBLICO_RE, gerar_slug_publico, normalizar_para_slug, slug_valido

RAIZ = Path(__file__).resolve().parent.parent
CONTRATOS_TS = RAIZ / "app" / "views" / "src" / "types" / "contratos.ts"
COLUNAS_VITRINE = {"is_publicado", "slug_publico", "descricao_publica", "pausar_candidaturas"}


def _animal(nome="Mel", status="disponível", publicado=False, slug=None, **extra):
    animal = Animal(nome=nome, sexo="Fêmea", porte="Pequeno", status_operacional=status,
                    data_entrada=date.today(), **extra)
    if publicado:
        animal.is_publicado = True
        animal.slug_publico = slug or gerar_slug_publico(nome)
    db.session.add(animal)
    db.session.commit()
    return animal


def _recarregar(animal_id):
    db.session.expire_all()
    return db.session.get(Animal, animal_id)


# REQ-21 · migração 0004 (subprocesso, SQLite em arquivo) ------------------------------------

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


def _sql_animals(banco):
    with sqlite3.connect(banco) as con:
        return con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='animals'").fetchone()[0]


def _indices_animals(banco):
    with sqlite3.connect(banco) as con:
        return {nome: sql for nome, sql in con.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='animals'")}


INSERIR_ANIMAL_0003A = (
    "INSERT INTO animals (id, nome, sexo, raca, porte, data_entrada, is_castrado, is_microchipado, is_idoso, "
    "status_operacional, is_deleted, created_at, updated_at) VALUES (1, 'Rex', 'Macho', 'SRD', 'Médio', "
    "'2026-01-01', 0, 0, 0, 'disponível', 0, '2026-01-01', '2026-01-01')"
)


@pytest.fixture
def banco_0004(tmp_path):
    banco = tmp_path / "cp02.db"
    resultado = _flask_db(banco, "upgrade")
    assert resultado.returncode == 0, resultado.stderr
    return banco


def test_migracao_0004_upgrade_downgrade_upgrade(banco_0004):
    banco = banco_0004
    assert COLUNAS_VITRINE <= _colunas(banco, "animals")
    assert "ck_animals_publicado_so_disponivel" in _sql_animals(banco)
    indices = _indices_animals(banco)
    assert "UNIQUE" in indices["uq_animals_slug_publico"]
    assert "(is_deleted, is_publicado, status_operacional, created_at)" in indices["ix_animals_vitrine"]

    resultado = _flask_db(banco, "downgrade", "0003a")
    assert resultado.returncode == 0, resultado.stderr
    assert not COLUNAS_VITRINE & _colunas(banco, "animals")
    assert "ck_animals_publicado_so_disponivel" not in _sql_animals(banco)
    assert not {"uq_animals_slug_publico", "ix_animals_vitrine"} & set(_indices_animals(banco))

    resultado = _flask_db(banco, "upgrade")
    assert resultado.returncode == 0, resultado.stderr
    assert COLUNAS_VITRINE <= _colunas(banco, "animals")


def test_migracao_0004_colunas_do_modelo_iguais_as_da_migracao(app, banco_0004):
    assert set(db.metadata.tables["animals"].columns.keys()) == _colunas(banco_0004, "animals")


def test_migracao_0004_mantem_checks_anteriores(banco_0004):
    sql = _sql_animals(banco_0004)
    for nome in ("ck_animals_status_operacional", "ck_animals_sexo", "ck_animals_porte",
                 "ck_animals_peso_kg_positivo"):
        assert nome in sql, nome


def test_migracao_0004_linhas_antigas_ficam_despublicadas(tmp_path):
    banco = tmp_path / "antigo.db"
    assert _flask_db(banco, "upgrade", "0003a").returncode == 0
    with sqlite3.connect(banco) as con:
        con.execute(INSERIR_ANIMAL_0003A)
    resultado = _flask_db(banco, "upgrade")
    assert resultado.returncode == 0, resultado.stderr
    with sqlite3.connect(banco) as con:
        assert con.execute("SELECT is_publicado, pausar_candidaturas, slug_publico, descricao_publica "
                           "FROM animals").fetchall() == [(0, 0, None, None)]


def test_migracao_0004_check_no_banco_migrado(banco_0004):
    with sqlite3.connect(banco_0004) as con:
        con.execute(INSERIR_ANIMAL_0003A)
        con.execute("UPDATE animals SET is_publicado = 1, slug_publico = 'rex-abc123'")
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("UPDATE animals SET status_operacional = 'em tratamento'")


def test_migracao_0004_downgrade_recusa_perder_dado_da_vitrine(banco_0004):
    with sqlite3.connect(banco_0004) as con:
        con.execute(INSERIR_ANIMAL_0003A)
        con.execute("UPDATE animals SET slug_publico = 'rex-abc123'")  # despublicado, mas com link
    resultado = _flask_db(banco_0004, "downgrade", "0003a")
    assert resultado.returncode != 0
    assert "recusado" in (resultado.stderr + resultado.stdout)
    assert COLUNAS_VITRINE <= _colunas(banco_0004, "animals")


def test_migracao_0004_sem_tabela_nova():
    import importlib.util
    arquivo = RAIZ / "migrations" / "versions" / "0004_vitrine_publica.py"
    spec = importlib.util.spec_from_file_location("migracao_0004", arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    assert modulo.down_revision == "0003a"
    assert modulo.TABELAS_RLS == []
    assert not re.search(r"^\s*(from|import)\s+app(\.|\s|$)", arquivo.read_text(encoding="utf-8"), re.M)


# REQ-22 · RN17: sai da vitrine sozinho, por qualquer caminho -----------------------------------

def test_rn17_sai_da_vitrine_direto_no_modelo(app):
    animal = _animal(publicado=True)
    slug = animal.slug_publico

    animal.status_operacional = Animal.STATUS_TRATAMENTO
    assert animal.is_publicado is False  # na mesma transação, antes do commit
    db.session.commit()
    animal = _recarregar(animal.id)
    assert animal.is_publicado is False
    assert animal.slug_publico == slug  # o link é mantido

    # Volta a ficar disponível: não se republica sozinho; republicado, o link é o mesmo
    animal.status_operacional = Animal.STATUS_DISPONIVEL
    db.session.commit()
    assert _recarregar(animal.id).is_publicado is False
    animal.is_publicado = True
    db.session.commit()
    assert Animal.buscar_publicado(slug).id == animal.id


def test_rn17_sai_da_vitrine_exclusao_logica_no_modelo(app):
    animal = _animal(publicado=True)
    animal.is_deleted = True
    assert animal.is_publicado is False
    db.session.commit()
    assert _recarregar(animal.id).is_publicado is False


def test_rn17_disponivel_para_disponivel_mantem_publicado(app):
    animal = _animal(publicado=True)
    animal.status_operacional = Animal.STATUS_DISPONIVEL
    animal.is_deleted = False
    db.session.commit()
    assert _recarregar(animal.id).is_publicado is True


@pytest.mark.parametrize("novo_status", ["em tratamento", "óbito", "lar temporário", "em acolhimento"])
def test_rn17_sai_da_vitrine_patch_status(app, vol_client, novo_status):
    animal = _animal(publicado=True)
    animal_id, slug = animal.id, animal.slug_publico
    resposta = vol_client.patch(f"/api/animais/{animal_id}/status", json={"status_operacional": novo_status})
    assert resposta.status_code == 200, resposta.get_json()
    assert resposta.get_json()["animal"]["is_publicado"] is False
    animal = _recarregar(animal_id)
    assert (animal.status_operacional, animal.is_publicado, animal.slug_publico) == (novo_status, False, slug)
    assert Animal.buscar_publicado(slug) is None


def test_rn17_sai_da_vitrine_adocao(app, vol_client):
    animal = _animal(publicado=True)
    animal_id = animal.id
    resposta = vol_client.post(f"/api/adocoes/{animal_id}", json={
        "adotante_nome": "Carlos Adotante", "adotante_telefone": "41987654321",
        "adotante_cpf": "123.456.789-09", "data_adocao": date.today().isoformat(), "termo_assinado": True,
    })
    assert resposta.status_code == 201, resposta.get_json()
    animal = _recarregar(animal_id)
    assert (animal.status_operacional, animal.is_publicado) == ("adotado", False)
    assert animal.slug_publico is not None


def test_rn17_sai_da_vitrine_exclusao_logica(app, admin_client):
    animal = _animal(publicado=True)
    animal_id = animal.id
    assert admin_client.delete(f"/api/animais/{animal_id}").status_code == 200
    animal = _recarregar(animal_id)
    assert (animal.is_deleted, animal.is_publicado) == (True, False)


def test_rn17_edicao_cadastral_nao_despublica(app, vol_client):
    animal = _animal(publicado=True)
    resposta = vol_client.patch(f"/api/animais/{animal.id}", json={"pelagem": "Caramelo"})
    assert resposta.status_code == 200
    assert _recarregar(animal.id).is_publicado is True


def test_rn17_edicao_nao_publica_pelo_corpo(app, vol_client):
    """A edição cadastral ignora os campos da vitrine: publicar é só pela rota própria (REQ-24)."""
    animal = _animal()
    vol_client.patch(f"/api/animais/{animal.id}", json={"is_publicado": True, "slug_publico": "x-abcdef",
                                                        "pelagem": "Preta"})
    animal = _recarregar(animal.id)
    assert (animal.is_publicado, animal.slug_publico) == (False, None)


# REQ-23 · CHECK no banco ---------------------------------------------------------------------

def test_check_publicado_so_disponivel(app):
    animal = _animal(status="em tratamento")
    animal.is_publicado = True  # o hook RN17 não reage a is_publicado: só o banco segura
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_check_publicado_so_disponivel_sql_direto(app):
    animal = _animal(publicado=True)
    with pytest.raises(IntegrityError):
        db.session.execute(text("UPDATE animals SET status_operacional = 'óbito' WHERE id = :id"),
                           {"id": animal.id})
        db.session.flush()
    db.session.rollback()


def test_check_aceita_despublicado_fora_de_disponivel(app):
    for status in Animal.VALID_STATUSES:
        _animal(nome=f"A {status}", status=status)
    assert Animal.query.count() == len(Animal.VALID_STATUSES)


# Slug ----------------------------------------------------------------------------------------

def test_slug_formato_e_sem_id(app):
    animal = _animal(nome="Mel")
    for _ in range(50):
        slug = gerar_slug_publico(animal.nome)
        assert SLUG_PUBLICO_RE.fullmatch(slug)
        assert re.fullmatch(r"mel-[a-z0-9]{6}", slug)
        assert str(animal.id) not in slug.split("-")[0]


@pytest.mark.parametrize("nome, base", [
    ("João Pé-de-Feijão!!", "joao-pe-de-feijao"),
    ("  ÇAÇÁ  da Silva ", "caca-da-silva"),
    ("Nome Muito Comprido Demais Para a URL", "nome-muito-comprido-dema"),
    ("Abcdefghijklmnopqrstuvw xyz", "abcdefghijklmnopqrstuvw"),  # sem hífen sobrando no corte
    ("🐶🐶", ""),
    ("", ""),
    (None, ""),
])
def test_slug_normalizacao(nome, base):
    assert normalizar_para_slug(nome) == base
    slug = gerar_slug_publico(nome)
    assert slug_valido(slug)
    assert slug.rsplit("-", 1)[0] == (base or "cao")
    assert len(slug) <= 31


def test_slug_aleatorio():
    assert len({gerar_slug_publico("Mel") for _ in range(200)}) == 200


def test_slug_unico_no_banco(app):
    _animal(nome="Mel", publicado=True, slug="mel-abc123")
    with pytest.raises(IntegrityError):
        _animal(nome="Mel 2", publicado=True, slug="mel-abc123")
    db.session.rollback()
    # Vários animais sem slug convivem (o índice único aceita vários NULL)
    _animal(nome="Sem 1")
    _animal(nome="Sem 2")


@pytest.mark.parametrize("slug", [None, "", "ab", "a" * 41, "Mel-abc123", "mel_abc123", "mel abc", "../etc",
                                  "mel-ábc123", 123, "mel-abc123\n"])
def test_slug_valido_recusa_fora_do_formato(slug):
    assert slug_valido(slug) is False


# REQ-29 (apoio) · buscar_publicado e query_vitrine -------------------------------------------

@pytest.fixture
def contar_consultas(app):
    consultas = []

    def _anotar(*_args, **_kwargs):
        consultas.append(1)

    event.listen(db.engine, "before_cursor_execute", _anotar)
    yield consultas
    event.remove(db.engine, "before_cursor_execute", _anotar)


def test_buscar_publicado(app):
    publicado = _animal(nome="Mel", publicado=True)
    assert Animal.buscar_publicado(publicado.slug_publico).id == publicado.id

    despublicado = _animal(nome="Bob", publicado=True)
    despublicado.is_publicado = False
    fora = _animal(nome="Tom", publicado=True)
    fora.status_operacional = Animal.STATUS_TRATAMENTO
    excluido = _animal(nome="Lua", publicado=True)
    excluido.is_deleted = True
    db.session.commit()
    for animal in (despublicado, fora, excluido):
        assert animal.slug_publico
        assert Animal.buscar_publicado(animal.slug_publico) is None
    assert Animal.buscar_publicado("nao-existe-123") is None


@pytest.mark.parametrize("slug", [None, "", "ab", "../x", "Mel-ABC123", "x" * 41, 7])
def test_buscar_publicado_fora_do_formato_nao_consulta(app, contar_consultas, slug):
    assert Animal.buscar_publicado(slug) is None
    assert contar_consultas == []


def test_query_vitrine_filtro_e_ordem(app):
    base = datetime(2026, 11, 1, 12, 0, 0)
    antigo = _animal(nome="Antigo", publicado=True, created_at=base)
    novo = _animal(nome="Novo", publicado=True, created_at=base + timedelta(days=2))
    empate_1 = _animal(nome="Empate Um", publicado=True, created_at=base + timedelta(days=1))
    empate_2 = _animal(nome="Empate Dois", publicado=True, created_at=base + timedelta(days=1))
    _animal(nome="Nao publicado", created_at=base + timedelta(days=3))
    fora = _animal(nome="Fora", publicado=True, created_at=base + timedelta(days=3))
    fora.status_operacional = Animal.STATUS_ADOTADO
    excluido = _animal(nome="Excluido", publicado=True, created_at=base + timedelta(days=3))
    excluido.is_deleted = True
    db.session.commit()

    ids = [a.id for a in Animal.query_vitrine().all()]
    assert ids == [novo.id, empate_2.id, empate_1.id, antigo.id]


def test_query_vitrine_usa_indice(app):
    plano = db.session.execute(text(
        "EXPLAIN QUERY PLAN SELECT id FROM animals WHERE is_deleted = 0 AND is_publicado = 1 "
        "AND status_operacional = 'disponível' ORDER BY created_at DESC")).fetchall()
    assert "ix_animals_vitrine" in " ".join(str(linha) for linha in plano)


# REQ-25 e REQ-26 · contrato com o front (app/views/src/types/contratos.ts) ---------------------

def _campos_da_interface(nome):
    fonte = CONTRATOS_TS.read_text(encoding="utf-8")
    corpo = re.search(r"export interface " + nome + r"\s*\{(.*?)\n\}", fonte, re.S).group(1)
    corpo = re.sub(r"/\*.*?\*/", "", corpo, flags=re.S)
    return set(re.findall(r"^\s*(\w+)\??\s*:", corpo, re.M))


def test_to_dict_tem_campos_vitrine_da_ficha(app):
    campos = _campos_da_interface("CamposVitrineDaFicha")
    assert campos == COLUNAS_VITRINE
    animal = _animal(publicado=True, descricao_publica="Dócil e brincalhona.")
    ficha = animal.to_dict()
    assert campos <= set(ficha)
    assert ficha["is_publicado"] is True
    assert ficha["pausar_candidaturas"] is False
    assert ficha["slug_publico"] == animal.slug_publico
    assert ficha["descricao_publica"] == "Dócil e brincalhona."


def test_to_public_dict_e_exatamente_animal_publico(app):
    campos = _campos_da_interface("AnimalPublico")
    animal = _animal(publicado=True, descricao_publica="Dócil.", pausar_candidaturas=True,
                     local_resgate="Rua Secreta", motivo_resgate="interno")
    publico = animal.to_public_dict()
    assert set(publico) == campos
    assert publico["slug"] == animal.slug_publico
    assert publico["candidaturas_pausadas"] is True
    assert publico["descricao_publica"] == "Dócil."
    assert "id" not in publico and "slug_publico" not in publico and "pausar_candidaturas" not in publico
