from flask import Blueprint, jsonify
from app.extensions import db
from app.models.animal import Animal
from app.models.health import Prescription, Vaccination
from app.utils import tempo
from app.services.saude import logs_by_prescription, open_booster_filter, split_horarios

core_bp = Blueprint("core", __name__)


@core_bp.route("/", methods=["GET"])
def health_check():
    """Health check e informações da API GAPAR Gestão."""
    return jsonify({
        "sistema": "GAPAR Gestão — Plataforma de Controle de Abrigo e Saúde Animal",
        "versao": "4.0 (MVP)",
        "status": "online",
        "endpoints": {
            "hoje": "/api/hoje",
            "animais": "/api/animais",
            "saude": "/api/saude",
            "adocoes": "/api/adocoes",
            "admin": "/api/admin",
            "auth": "/auth/status",
            "avisos": "/api/avisos"
        }
    }), 200


@core_bp.route("/api/hoje", methods=["GET"])
def today_dashboard():
    """Painel operacional consolidado 'Hoje' (RF23).
    Retorna a lista de medicações e vacinas a serem aplicadas na data atual.

    Desempenho (RNF01, RNF04): são sempre quatro consultas, qualquer que seja o número de
    animais: contagem por status, prescrições vigentes, baixas do dia e reforços em aberto.
    """
    agora = tempo.agora()
    hoje = agora.date()
    hora_atual = agora.strftime("%H:%M")
    status_finais = [Animal.STATUS_ADOTADO, Animal.STATUS_OBITO]
    sob_cuidados = (Animal.is_deleted.is_(False), Animal.status_operacional.notin_(status_finais))

    # Contadores gerais do abrigo: uma consulta agregada
    por_status = dict(
        db.session.query(Animal.status_operacional, db.func.count(Animal.id))
        .filter(Animal.is_deleted.is_(False))
        .group_by(Animal.status_operacional).all()
    )
    total_acolhidos = sum(qtd for status, qtd in por_status.items() if status not in status_finais)
    em_tratamento = por_status.get(Animal.STATUS_TRATAMENTO, 0)
    disponiveis_adocao = por_status.get(Animal.STATUS_DISPONIVEL, 0)

    # Prescrições vigentes hoje (RN09), já com os dados do animal, e as baixas do dia de todas elas
    prescricoes = (
        db.session.query(Prescription, Animal.nome, Animal.localizacao_baia, Animal.foto_url)
        .join(Animal, Prescription.animal_id == Animal.id)
        .filter(*sob_cuidados, Prescription.data_inicio <= hoje, Prescription.data_fim >= hoje)
        .all()
    )
    logs_do_dia = logs_by_prescription([p.id for p, *_ in prescricoes], hoje)

    medicacoes_hoje = []
    total_medicacoes_pendentes = 0
    for p, animal_nome, baia, foto_url in prescricoes:
        logs_por_horario = {}
        for log in logs_do_dia[p.id]:
            logs_por_horario.setdefault(log.horario_previsto, log)

        for horario in split_horarios(p.horarios):
            log_item = logs_por_horario.get(horario)
            aplicado = log_item is not None
            if not aplicado:
                total_medicacoes_pendentes += 1

            medicacoes_hoje.append({
                "prescricao_id": p.id,
                "animal_id": p.animal_id,
                "animal_nome": animal_nome,
                "animal_foto_url": foto_url,
                "localizacao_baia": baia or "Geral",
                "medicamento": p.nome_medicamento,
                "dosagem": p.dosagem,
                "horario_previsto": horario,
                "horario_aplicado": log_item.horario_aplicado if log_item else None,
                "aplicado": aplicado,
                "atrasada": not aplicado and horario < hora_atual,
                "instrucoes": p.instrucoes or ""
            })

    # Ordena medicações pelo horário previsto (e por animal, para a ordem ser estável)
    medicacoes_hoje.sort(key=lambda m: (m["horario_previsto"], m["animal_nome"].lower(), m["prescricao_id"]))

    # Reforços de vacina previstos para hoje ou atrasados, que ainda não foram atendidos
    reforcos = (
        db.session.query(Vaccination, Animal.nome, Animal.localizacao_baia, Animal.foto_url)
        .join(Animal, Vaccination.animal_id == Animal.id)
        .filter(*sob_cuidados, Vaccination.data_reforco <= hoje, open_booster_filter(hoje))
        .order_by(Vaccination.data_reforco.asc(), Vaccination.id.asc())
        .all()
    )
    vacinas_hoje = [{
        "vacina_id": v.id,
        "animal_id": v.animal_id,
        "animal_nome": animal_nome,
        "animal_foto_url": foto_url,
        "localizacao_baia": baia or "Geral",
        "nome_vacina": v.nome_vacina,
        "data_reforco": v.data_reforco.isoformat() if v.data_reforco else None,
        "atrasada": v.data_reforco < hoje if v.data_reforco else False
    } for v, animal_nome, baia, foto_url in reforcos]

    return jsonify({
        "data_referencia": hoje.isoformat(),
        "hora_referencia": hora_atual,
        "kpis": {
            "total_acolhidos": total_acolhidos,
            "em_tratamento": em_tratamento,
            "disponiveis_adocao": disponiveis_adocao,
            "total_medicacoes_pendentes": total_medicacoes_pendentes,
            "total_vacinas_pendentes": len(vacinas_hoje)
        },
        "total_medicacoes_pendentes": total_medicacoes_pendentes,
        "total_vacinas_pendentes": len(vacinas_hoje),
        "medicacoes_hoje": medicacoes_hoje,
        "vacinas_hoje": vacinas_hoje
    }), 200
