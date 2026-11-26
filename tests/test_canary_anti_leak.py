"""CP-01 · Teste canário anti-vazamento (REQ-06 e REQ-07).

Preenche toda coluna de texto do banco com honeytokens `CANARY_SECRET_*` e exige que nenhum
deles apareça em resposta pública. Novas colunas e novas rotas públicas entram no teste
automaticamente (introspecção do modelo e do mapa de rotas), sem precisar lembrar de atualizá-lo.
"""
import json
from datetime import date

import pytest
from sqlalchemy import String, Text

from app.extensions import db
from app.models import AuditLog, NonEligiblePerson, User, Whitelist
from app.models.adoption import Adoption
from app.models.animal import Animal

CANARIO = "CANARY_SECRET_"

# Campos que NUNCA podem ir para a allowlist pública
PROIBIDOS_NA_VITRINE = {"id", "local_resgate", "motivo_resgate", "localizacao_baia", "codigo_identificador",
                        "cuidados_especiais", "status_operacional", "is_deleted", "created_at", "updated_at"}


def _colunas_texto(modelo):
    return [c for c in modelo.__table__.columns if isinstance(c.type, (String, Text))]


def _animal_com_canarios(**fixos):
    dados = {"nome": "Rex", "sexo": "Macho", "porte": "Médio", "status_operacional": "disponível"}
    for coluna in _colunas_texto(Animal):
        attr = Animal.__mapper__.get_property_by_column(coluna).key
        if attr not in Animal.PUBLIC_ANIMAL_STRICT_KEYS and attr not in dados:
            limite = getattr(coluna.type, "length", None) or 200
            dados[attr] = (CANARIO + attr)[:limite]
    dados.update(fixos)
    animal = Animal(**dados)
    db.session.add(animal)
    db.session.commit()
    return animal


# REQ-06 ------------------------------------------------------------------------------------

def test_to_public_dict_so_allowlist(app):
    animal = _animal_com_canarios()
    publico = animal.to_public_dict()
    assert set(publico) == set(Animal.PUBLIC_ANIMAL_STRICT_KEYS)
    assert CANARIO not in json.dumps(publico, ensure_ascii=False, default=str)


def test_allowlist_nao_contem_campos_internos():
    assert not PROIBIDOS_NA_VITRINE & set(Animal.PUBLIC_ANIMAL_STRICT_KEYS)


# Lista APROVADA, congelada. Acrescentar um campo público exige mudar esta lista de propósito,
# no mesmo diff, o que obriga a revisão (inclusive de campos que não são texto, como peso/datas).
ALLOWLIST_APROVADA = {"nome", "sexo", "porte", "idade_estimada", "raca", "pelagem", "foto_url",
                      "is_castrado", "is_idoso"}


def test_allowlist_publica_e_exatamente_a_aprovada():
    assert set(Animal.PUBLIC_ANIMAL_STRICT_KEYS) == ALLOWLIST_APROVADA


# REQ-07 ------------------------------------------------------------------------------------

# Dados pessoais plantados no banco, em todos os formatos em que podem sair numa resposta
SEGREDOS_PESSOAIS = (
    "52998224725", "529.982.247-25", "99988877714", "999.888.777-14",
    "41999990000", "(41) 99999-0000", "41988887777", "(41) 98888-7777",
)


@pytest.fixture
def banco_com_canarios(app):
    from app.models import Announcement, MedicalRecord, Prescription, Vaccination

    admin = User(email="canary_secret_admin@gapar.org.br", name=CANARIO + "admin", role="Administradora")
    db.session.add_all([admin, Whitelist(email="canary_secret_admin@gapar.org.br", role="Administradora")])
    db.session.flush()
    animal = _animal_com_canarios()
    # Um segundo animal publicável (disponível), para que listagens públicas tenham o que mostrar
    vitrine = _animal_com_canarios(nome="Mel")
    db.session.add(Adoption(animal_id=animal.id, adotante_nome=CANARIO + "adotante", adotante_telefone="41999990000",
                            adotante_cpf="52998224725", adotante_endereco=CANARIO + "endereco",
                            observacoes=CANARIO + "obs", data_adocao=date.today()))
    db.session.add(NonEligiblePerson(nome=CANARIO + "nao_apto", cpf="99988877714", telefone="41988887777",
                                     motivo_impedimento=CANARIO + "motivo"))
    for alvo in (animal, vitrine):
        db.session.add_all([
            Vaccination(animal_id=alvo.id, nome_vacina=CANARIO + "vacina", lote=CANARIO + "lote",
                        observacoes=CANARIO + "vac_obs", data_aplicacao=date.today()),
            MedicalRecord(animal_id=alvo.id, tipo_evento="Consulta", diagnostico=CANARIO + "diagnostico",
                          data_evento=date.today()),
            Prescription(animal_id=alvo.id, nome_medicamento=CANARIO + "remedio", dosagem=CANARIO + "dose",
                         horarios="08:00", data_inicio=date.today(), data_fim=date.today()),
        ])
    db.session.add(Announcement(tipo="TURNO", titulo=CANARIO + "aviso", conteudo=CANARIO + "conteudo",
                                autor_id=admin.id))
    db.session.add(AuditLog(acao="TESTE", entidade="Teste", detalhes=CANARIO + "auditoria"))
    db.session.commit()
    return {"slug_valido": getattr(vitrine, "slug_publico", None) or "slug-inexistente"}


# Rotas públicas que não são GET sem parâmetro precisam de um caso explícito aqui.
# endpoint -> função(dados_do_banco) que devolve (método, url, json). Vazio no CP-01.
CASOS_PUBLICOS_EXPLICITOS = {}


def _casos_publicos(app, dados):
    casos, sem_caso = [], []
    for regra in app.url_map.iter_rules():
        if not regra.endpoint.startswith("public."):
            continue
        if regra.endpoint in CASOS_PUBLICOS_EXPLICITOS:
            casos.append(CASOS_PUBLICOS_EXPLICITOS[regra.endpoint](dados))
        elif "GET" in regra.methods and not regra.arguments:
            casos.append(("GET", regra.rule, None))
        else:
            sem_caso.append(regra.endpoint)
    return casos, sem_caso


def test_toda_rota_publica_esta_coberta_pelo_canario(app, banco_com_canarios):
    casos, sem_caso = _casos_publicos(app, banco_com_canarios)
    assert casos
    assert not sem_caso, ("Rota pública sem caso no canário (acrescente em CASOS_PUBLICOS_EXPLICITOS): "
                          + ", ".join(sem_caso))


@pytest.mark.parametrize("perfil", ["anonimo", "admin"])
def test_rotas_publicas_sem_honeytoken(app, client, banco_com_canarios, perfil):
    c = client
    if perfil == "admin":
        c = app.test_client()
        assert c.post("/auth/dev-login", json={"email": "canary_secret_admin@gapar.org.br"}).status_code == 200
    casos, _ = _casos_publicos(app, banco_com_canarios)
    for metodo, url, corpo_json in casos:
        corpo = c.open(url, method=metodo, json=corpo_json).get_data(as_text=True)
        assert CANARIO.lower() not in corpo.lower(), f"Vazamento de honeytoken em {metodo} {url}"
        for segredo in SEGREDOS_PESSOAIS:
            assert segredo not in corpo, f"Dado pessoal em {metodo} {url}"
