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


# REQ-07 ------------------------------------------------------------------------------------

@pytest.fixture
def banco_com_canarios(app):
    admin = User(email="canary_secret_admin@gapar.org.br", name=CANARIO + "admin", role="Administradora")
    db.session.add_all([admin, Whitelist(email="canary_secret_admin@gapar.org.br", role="Administradora")])
    animal = _animal_com_canarios()
    db.session.add(Adoption(animal_id=animal.id, adotante_nome=CANARIO + "adotante", adotante_telefone="41999990000",
                            adotante_cpf="52998224725", adotante_endereco=CANARIO + "endereco",
                            observacoes=CANARIO + "obs", data_adocao=date.today()))
    db.session.add(NonEligiblePerson(nome=CANARIO + "nao_apto", cpf="99988877714", telefone="41988887777",
                                     motivo_impedimento=CANARIO + "motivo"))
    db.session.add(AuditLog(acao="TESTE", entidade="Teste", detalhes=CANARIO + "auditoria"))
    db.session.commit()


def _rotas_publicas_get(app):
    for regra in app.url_map.iter_rules():
        if regra.endpoint.startswith("public.") and "GET" in regra.methods and not regra.arguments:
            yield regra.rule


@pytest.mark.parametrize("perfil", ["anonimo", "admin"])
def test_rotas_publicas_sem_honeytoken(app, client, banco_com_canarios, perfil):
    c = client
    if perfil == "admin":
        c = app.test_client()
        assert c.post("/auth/dev-login", json={"email": "canary_secret_admin@gapar.org.br"}).status_code == 200
    rotas = list(_rotas_publicas_get(app))
    assert rotas
    for rota in rotas:
        corpo = c.get(rota).get_data(as_text=True)
        assert CANARIO.lower() not in corpo.lower(), f"Vazamento em {rota}"
        assert "52998224725" not in corpo and "99988877714" not in corpo
