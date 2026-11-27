"""CP-05 · Isolamento sanitário, API (REQ-42, REQ-43 e a parte de API da REQ-44/REQ-45, RN22).

Spec: docs/sdd/CP03_05_FASE2_SPEC.md. Contrato: `IsolamentoRegistro` e `IsolamentoAbertoResumo`
em app/views/src/types/contratos.ts. A camada de dados tem testes próprios
(test_cp05_isolamento_dados.py).
"""
from datetime import date, timedelta

import pytest
from sqlalchemy import event

from app.extensions import db
from app.models import AuditLog, IsolationRecord
from app.models.animal import Animal
from app.utils import tempo
from app.utils.slug import gerar_slug_publico

CHAVES_REGISTRO = {"id", "animal_id", "motivo", "protocolo_cuidados", "data_inicio", "data_fim_prevista",
                   "fim_real", "observacoes_alta", "aberto_por", "encerrado_por", "aberto", "created_at"}


@pytest.fixture
def isolamento(app):
    app.config["FEATURES"] = {**app.config["FEATURES"], "isolamento": True}


def _animal(nome="Rex", status="em tratamento", **extra):
    animal = Animal(nome=nome, sexo="Macho", porte="Médio", status_operacional=status,
                    data_entrada=date.today(), **extra)
    db.session.add(animal)
    db.session.commit()
    return animal


def _abrir(client, animal_id, **corpo):
    return client.post(f"/api/animais/{animal_id}/isolamentos", json={"motivo": "Suspeita de cinomose", **corpo})


# Flag ---------------------------------------------------------------------------------------------

def test_flag_desligada_404(app, vol_client):
    a = _animal()
    assert vol_client.get(f"/api/animais/{a.id}/isolamentos").status_code == 404
    assert _abrir(vol_client, a.id).status_code == 404
    r = IsolationRecord(animal_id=a.id, motivo="x", data_inicio=date.today())
    db.session.add(r)
    db.session.commit()
    assert vol_client.post(f"/api/isolamentos/{r.id}/encerrar", json={}).status_code == 404
    assert IsolationRecord.query.one().fim_real is None


def test_flag_desligada_sem_chave_no_hoje(app, vol_client):
    assert "isolamentos" not in vol_client.get("/api/hoje").get_json()


def test_sem_login_401(app, isolamento, client):
    a = _animal()
    assert client.get(f"/api/animais/{a.id}/isolamentos").status_code == 401
    assert _abrir(client, a.id).status_code == 401
    assert client.post("/api/isolamentos/1/encerrar", json={}).status_code == 401


# Abrir --------------------------------------------------------------------------------------------

def test_voluntaria_abre_isolamento(app, isolamento, vol_client):
    a = _animal()
    fim = (tempo.hoje() + timedelta(days=10)).isoformat()
    r = _abrir(vol_client, a.id, protocolo_cuidados="Luvas e pedilúvio", data_fim_prevista=fim)
    assert r.status_code == 201
    reg = r.get_json()["isolamento"]
    assert set(reg) == CHAVES_REGISTRO
    assert reg["aberto"] is True and reg["fim_real"] is None and reg["aberto_por"] == "Vol"
    assert reg["data_inicio"] == tempo.hoje().isoformat() and reg["data_fim_prevista"] == fim
    ficha = vol_client.get(f"/api/animais/{a.id}").get_json()["animal"]
    assert ficha["isolamento_aberto"] == {"id": reg["id"], "motivo": "Suspeita de cinomose",
                                          "data_inicio": reg["data_inicio"], "data_fim_prevista": fim}


def test_segundo_aberto_409_rn22(app, isolamento, vol_client):
    a = _animal()
    assert _abrir(vol_client, a.id).status_code == 201
    r = _abrir(vol_client, a.id)
    assert r.status_code == 409 and "RN22" in r.get_json()["mensagem"]
    assert IsolationRecord.query.count() == 1


def test_corrida_no_indice_parcial_409(app, isolamento, vol_client, monkeypatch):
    """A checagem prévia não vê o aberto (gravado por outra requisição no meio): o índice único
    parcial recusa o INSERT e a rota devolve 409, e não o erro genérico."""
    a = _animal()
    assert _abrir(vol_client, a.id).status_code == 201
    monkeypatch.setattr(IsolationRecord, "aberto_do_animal", classmethod(lambda cls, animal_id: None))
    r = _abrir(vol_client, a.id)
    assert r.status_code == 409 and "RN22" in r.get_json()["mensagem"]
    assert IsolationRecord.query.count() == 1
    assert AuditLog.query.filter_by(acao="ISOLAMENTO_ABERTO").count() == 1


@pytest.mark.parametrize("status", ["óbito", "adotado"])
def test_animal_congelado_422(app, isolamento, vol_client, status):
    a = _animal(status=status)
    assert _abrir(vol_client, a.id).status_code == 422
    assert IsolationRecord.query.count() == 0


def test_animal_excluido_422_e_inexistente_404(app, isolamento, vol_client):
    a = _animal(is_deleted=True)
    assert _abrir(vol_client, a.id).status_code == 422
    assert _abrir(vol_client, 999).status_code == 404
    assert vol_client.get(f"/api/animais/{a.id}/isolamentos").status_code == 404
    assert IsolationRecord.query.count() == 0


@pytest.mark.parametrize("corpo", [
    {"motivo": ""}, {"motivo": "x" * 201}, {"motivo": "ok", "data_inicio": "ontem"},
    {"motivo": "ok", "data_inicio": "2026-01-10", "data_fim_prevista": "2026-01-09"},
    {"motivo": "ok", "data_inicio": "2999-01-01"},
])
def test_abrir_invalido_400(app, isolamento, vol_client, corpo):
    a = _animal()
    r = vol_client.post(f"/api/animais/{a.id}/isolamentos", json=corpo)
    assert r.status_code == 400
    assert IsolationRecord.query.count() == 0


def test_auditoria_sem_texto_do_motivo(app, isolamento, vol_client):
    a = _animal()
    assert _abrir(vol_client, a.id, motivo="Mordida no tutor João 11987654321").status_code == 201
    detalhes = " ".join(x.detalhes or "" for x in AuditLog.query.all())
    assert "João" not in detalhes and "11987654321" not in detalhes


# Encerrar e reabrir -------------------------------------------------------------------------------

def test_encerrar_reabrir_e_historico(app, isolamento, vol_client, admin_client):
    a = _animal()
    primeiro = _abrir(vol_client, a.id).get_json()["isolamento"]["id"]
    r = admin_client.post(f"/api/isolamentos/{primeiro}/encerrar", json={"observacoes_alta": "Exame negativo"})
    assert r.status_code == 200
    reg = r.get_json()["isolamento"]
    assert reg["aberto"] is False and reg["fim_real"] and reg["encerrado_por"] == "Admin"
    assert reg["observacoes_alta"] == "Exame negativo"
    assert vol_client.get(f"/api/animais/{a.id}").get_json()["animal"]["isolamento_aberto"] is None

    again = vol_client.post(f"/api/isolamentos/{primeiro}/encerrar", json={"observacoes_alta": "outra"})
    assert again.status_code == 409
    db.session.expire_all()
    assert db.session.get(IsolationRecord, primeiro).observacoes_alta == "Exame negativo"

    segundo = _abrir(vol_client, a.id, motivo="Sarna").get_json()["isolamento"]["id"]
    historico = vol_client.get(f"/api/animais/{a.id}/isolamentos").get_json()["isolamentos"]
    assert [h["id"] for h in historico] == [segundo, primeiro]
    assert [h["aberto"] for h in historico] == [True, False]


def test_encerrar_inexistente_404(app, isolamento, vol_client):
    assert vol_client.post("/api/isolamentos/999/encerrar", json={}).status_code == 404


def test_encerrar_com_ficha_congelada_e_permitido(app, isolamento, vol_client):
    """Animal que foi a óbito isolado precisa sair da lista de abertos do painel."""
    a = _animal()
    reg = _abrir(vol_client, a.id).get_json()["isolamento"]["id"]
    a.status_operacional = Animal.STATUS_OBITO
    db.session.commit()
    assert vol_client.post(f"/api/isolamentos/{reg}/encerrar", json={}).status_code == 200


# Lista de animais sem N+1 (REQ-43) ----------------------------------------------------------------

def _consultas_da_lista(client):
    contagem = {"n": 0}

    def contar(*_):
        contagem["n"] += 1

    event.listen(db.engine, "before_cursor_execute", contar)
    try:
        r = client.get("/api/animais?per_page=100")
    finally:
        event.remove(db.engine, "before_cursor_execute", contar)
    assert r.status_code == 200
    return r.get_json()["animais"], contagem["n"]


def test_lista_de_animais_sem_n_mais_1(app, isolamento, vol_client):
    def popular(qtd, inicio):
        for i in range(qtd):
            a = _animal(f"Cão {inicio + i}")
            if i % 2 == 0:
                db.session.add(IsolationRecord(animal_id=a.id, motivo="Gripe", data_inicio=date.today()))
        db.session.commit()

    popular(3, 0)
    vol_client.get("/api/animais")  # aquece a sessão de login
    db.session.expire_all()
    animais, poucas = _consultas_da_lista(vol_client)
    assert len(animais) == 3
    popular(12, 3)
    db.session.expire_all()
    animais, muitas = _consultas_da_lista(vol_client)
    assert len(animais) == 15
    assert muitas == poucas, f"consultas cresceram com a página: {poucas} -> {muitas}"
    isolados = [a for a in animais if a["isolamento_aberto"]]
    assert len(isolados) == 2 + 6
    assert set(isolados[0]["isolamento_aberto"]) == {"id", "motivo", "data_inicio", "data_fim_prevista"}


# /api/hoje (REQ-43) -------------------------------------------------------------------------------

@pytest.mark.parametrize("perfil", ["vol", "admin"])
def test_hoje_lista_isolamentos_abertos(app, isolamento, vol_client, admin_client, perfil):
    c = vol_client if perfil == "vol" else admin_client
    a, b = _animal("Thor"), _animal("Luna")
    aberto = _abrir(c, a.id).get_json()["isolamento"]["id"]
    encerrado = _abrir(c, b.id).get_json()["isolamento"]["id"]
    c.post(f"/api/isolamentos/{encerrado}/encerrar", json={})
    _animal("Fantasma", is_deleted=True)
    dados = c.get("/api/hoje").get_json()
    assert [(i["id"], i["animal_nome"]) for i in dados["isolamentos"]] == [(aberto, "Thor")]
    assert CHAVES_REGISTRO <= set(dados["isolamentos"][0])
    assert "estoque" not in dados  # flag de estoque desligada


# Vitrine (RN17 ampliada, REQ-44) ------------------------------------------------------------------

def test_isolado_sai_da_vitrine_e_volta_ao_encerrar(app, isolamento, vol_client, client):
    app.config["FEATURES"] = {**app.config["FEATURES"], "vitrine": True}
    a = _animal("Mel", status="disponível")
    a.is_publicado = True
    a.slug_publico = gerar_slug_publico("Mel")
    db.session.commit()
    slug = a.slug_publico
    nomes = lambda: [x["nome"] for x in client.get("/api/public/animais").get_json()["animais"]]
    assert nomes() == ["Mel"]

    reg = _abrir(vol_client, a.id).get_json()["isolamento"]["id"]
    assert nomes() == []
    assert client.get(f"/api/public/animais/{slug}").status_code == 404
    db.session.expire_all()
    assert db.session.get(Animal, a.id).is_publicado is True  # isolamento não despublica

    assert vol_client.post(f"/api/isolamentos/{reg}/encerrar", json={}).status_code == 200
    assert nomes() == ["Mel"]
    assert client.get(f"/api/public/animais/{slug}").status_code == 200
