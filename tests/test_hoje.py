from datetime import date, timedelta
from app.extensions import db
from app.models.animal import Animal
from app.models.health import Prescription, Vaccination


def test_painel_hoje_consolida_doses_e_vacinas_rf23(client, app):
    hoje = date.today()
    with app.app_context():
        # Animal em tratamento
        a1 = Animal(
            nome="Dara",
            sexo="Fêmea",
            porte="Médio",
            status_operacional="em tratamento",
            data_entrada=hoje
        )
        db.session.add(a1)
        db.session.commit()

        p = Prescription(
            animal_id=a1.id,
            nome_medicamento="Cefalexina",
            dosagem="500mg",
            horarios="12:00, 22:00",
            data_inicio=hoje,
            data_fim=hoje + timedelta(days=2)
        )
        db.session.add(p)

        # Vacina com reforço hoje
        v = Vaccination(
            animal_id=a1.id,
            nome_vacina="Raiva",
            data_aplicacao=hoje - timedelta(days=365),
            data_reforco=hoje
        )
        db.session.add(v)
        db.session.commit()

    resp = client.get("/api/hoje")
    assert resp.status_code == 200
    dados = resp.get_json()
    assert dados["kpis"]["em_tratamento"] >= 1
    assert any(m["animal_nome"] == "Dara" for m in dados["medicacoes_hoje"])
    assert any(v["animal_nome"] == "Dara" for v in dados["vacinas_hoje"])
