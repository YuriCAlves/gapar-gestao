from datetime import date
from app.extensions import db
from app.models.animal import Animal
from app.models.blacklist import NonEligiblePerson


def test_adocao_sucesso_e_congelamento_rn04_rn05(client, app):
    with app.app_context():
        animal = Animal(
            nome="Max",
            sexo="Macho",
            porte="Médio",
            status_operacional="disponível",
            data_entrada=date.today()
        )
        db.session.add(animal)
        db.session.commit()
        animal_id = animal.id

    # 1. Tenta adoção sem campos obrigatórios (RN04)
    r_invalido = client.post(f"/api/adocoes/{animal_id}", json={"adotante_nome": "Carlos"})
    assert r_invalido.status_code == 400

    # 2. Adoção regular completa
    payload = {
        "adotante_nome": "Carlos Adotante",
        "adotante_telefone": "41987654321",
        "adotante_cpf": "123.456.789-00",
        "data_adocao": date.today().isoformat(),
        "termo_assinado": True
    }
    resp = client.post(f"/api/adocoes/{animal_id}", json=payload)
    assert resp.status_code == 201
    dados = resp.get_json()
    assert dados["sucesso"] is True
    assert dados["animal"]["status_operacional"] == "adotado"

    # Confere congelamento no banco (RN05)
    with app.app_context():
        a = db.session.get(Animal, animal_id)
        assert a.is_frozen is True


def test_bloqueio_adocao_pessoa_nao_apta_rn15(client, app):
    with app.app_context():
        # Cria pessoa na lista sigilosa
        bloqueado = NonEligiblePerson(
            nome="Marcio Inapto",
            cpf="999.888.777-66",
            telefone="41999998888",
            motivo_impedimento="Maus tratos"
        )
        db.session.add(bloqueado)

        animal = Animal(
            nome="Pingo",
            sexo="Macho",
            porte="Pequeno",
            status_operacional="disponível",
            data_entrada=date.today()
        )
        db.session.add(animal)
        db.session.commit()
        animal_id = animal.id

    # Tentativa de adoção com o mesmo CPF bloqueado (RN15)
    payload = {
        "adotante_nome": "Marcio Qualquer",
        "adotante_telefone": "41911112222",
        "adotante_cpf": "999.888.777-66",
        "data_adocao": date.today().isoformat()
    }
    resp = client.post(f"/api/adocoes/{animal_id}", json=payload)
    assert resp.status_code == 422
    dados = resp.get_json()
    assert "Adoção não autorizada" in dados["erro"]
