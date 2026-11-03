from datetime import date
from app.extensions import db
from app.models.animal import Animal


def test_cadastro_animal_em_acolhimento_rn01(client):
    payload = {
        "nome": "Pipoca",
        "sexo": "Fêmea",
        "porte": "Pequeno",
        "raca": "Vira-lata",
        "is_castrado": True
    }
    resp = client.post("/api/animais", json=payload)
    assert resp.status_code == 201
    dados = resp.get_json()
    assert dados["sucesso"] is True
    assert dados["animal"]["nome"] == "Pipoca"
    # RN01: Status obrigatório 'em acolhimento' e data de entrada de hoje
    assert dados["animal"]["status_operacional"] == "em acolhimento"
    assert dados["animal"]["data_entrada"] == date.today().isoformat()


def test_soft_delete_obrigatorio_rn03(client, app):
    # Cria animal
    with app.app_context():
        a = Animal(
            nome="Bidu",
            sexo="Macho",
            porte="Médio",
            status_operacional="em acolhimento",
            data_entrada=date.today()
        )
        db.session.add(a)
        db.session.commit()
        animal_id = a.id

    # Deleta logicamente
    resp = client.delete(f"/api/animais/{animal_id}")
    assert resp.status_code == 200

    # Verifica no banco que o registro ainda existe fisicamente com is_deleted = True (RN03)
    with app.app_context():
        a_banco = db.session.get(Animal, animal_id)
        assert a_banco is not None
        assert a_banco.is_deleted is True

    # Não deve aparecer na listagem
    r_list = client.get("/api/animais")
    animais = r_list.get_json()["animais"]
    assert not any(x["id"] == animal_id for x in animais)


def test_bloqueio_edicao_animal_adotado_rn05(client, app):
    with app.app_context():
        a = Animal(
            nome="Toby",
            sexo="Macho",
            porte="Pequeno",
            status_operacional="adotado",
            data_entrada=date.today()
        )
        db.session.add(a)
        db.session.commit()
        animal_id = a.id

    # Tenta atualizar
    resp = client.patch(f"/api/animais/{animal_id}", json={"nome": "Novo Nome"})
    assert resp.status_code == 422
    dados = resp.get_json()
    assert "Ficha congelada" in dados["erro"]
