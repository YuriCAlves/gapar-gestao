from datetime import date, timedelta
from app.extensions import db
from app.models.animal import Animal
from app.models.health import Prescription, Vaccination, MedicationLog


def test_baixa_medicacao_e_prevencao_duplicidade_rf16(client, app):
    hoje = date.today()
    with app.app_context():
        animal = Animal(
            nome="Bob",
            sexo="Macho",
            porte="Médio",
            status_operacional="em tratamento",
            data_entrada=hoje
        )
        db.session.add(animal)
        db.session.commit()

        prescricao = Prescription(
            animal_id=animal.id,
            nome_medicamento="Dipirona",
            dosagem="5 gotas",
            horarios="08:00, 16:00, 23:00",
            data_inicio=hoje,
            data_fim=hoje + timedelta(days=3)
        )
        db.session.add(prescricao)
        db.session.commit()
        p_id = prescricao.id

    # Dá baixa na dose das 08:00
    resp = client.post(f"/api/saude/medicacao/baixa/{p_id}", json={"horario_previsto": "08:00"})
    assert resp.status_code == 200
    dados = resp.get_json()
    assert dados["sucesso"] is True
    assert dados["log"]["horario_previsto"] == "08:00"

    # Tenta dar baixa novamente no mesmo horário (deve acusar que já foi baixado)
    resp2 = client.post(f"/api/saude/medicacao/baixa/{p_id}", json={"horario_previsto": "08:00"})
    assert resp2.status_code == 200
    dados2 = resp2.get_json()
    assert dados2["ja_baixado"] is True


def test_vacina_reforco_e_bloqueio_apos_congelamento(client, app):
    hoje = date.today()
    with app.app_context():
        animal = Animal(
            nome="Princesa",
            sexo="Fêmea",
            porte="Pequeno",
            status_operacional="em acolhimento",
            data_entrada=hoje
        )
        db.session.add(animal)
        db.session.commit()
        animal_id = animal.id

    # Cadastra vacina
    payload = {
        "nome_vacina": "GiardiaVax",
        "lote": "GV-2026",
        "data_aplicacao": hoje.isoformat(),
        "data_reforco": (hoje + timedelta(days=30)).isoformat()
    }
    r = client.post(f"/api/saude/vacinas/{animal_id}", json=payload)
    assert r.status_code == 201

    # Altera status para adotado via API oficial
    r_status = client.patch(f"/api/animais/{animal_id}/status", json={"status_operacional": "adotado"})
    assert r_status.status_code == 200

    # Nova tentativa de vacina deve ser bloqueada (RN05)
    r2 = client.post(f"/api/saude/vacinas/{animal_id}", json=payload)
    assert r2.status_code == 422
    dados_erro = r2.get_json()
    assert "Ficha congelada" in dados_erro["erro"]
