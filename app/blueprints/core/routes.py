from datetime import date, datetime
from flask import jsonify, render_template, abort, request
from flask_login import current_user
from app.extensions import db
from app.models.animal import Animal
from app.models.health import Prescription, MedicationLog, Vaccination
from . import core_bp


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
    """
    hoje = date.today()
    hoje_str = hoje.isoformat()

    # Contadores gerais do abrigo
    animais_ativos = Animal.query.filter_by(is_deleted=False).all()
    total_acolhidos = len([a for a in animais_ativos if a.status_operacional not in (Animal.STATUS_ADOTADO, Animal.STATUS_OBITO)])
    em_tratamento = len([a for a in animais_ativos if a.status_operacional == Animal.STATUS_TRATAMENTO])
    disponiveis_adocao = len([a for a in animais_ativos if a.status_operacional == Animal.STATUS_DISPONIVEL])

    # Consolidação de medicações do dia
    medicacoes_hoje = []
    total_medicacoes_pendentes = 0

    # Busca prescrições vigentes hoje para animais não congelados e não deletados
    prescricoes_ativas = Prescription.query.join(Animal).filter(
        Animal.is_deleted == False,
        Animal.status_operacional.notin_([Animal.STATUS_ADOTADO, Animal.STATUS_OBITO]),
        Prescription.data_inicio <= hoje,
        Prescription.data_fim >= hoje
    ).all()

    for p in prescricoes_ativas:
        horarios_lista = [h.strip() for h in p.horarios.split(",") if h.strip()]
        logs_hoje = {log.horario_previsto: log for log in p.logs.filter_by(data_aplicacao=hoje).all()}

        for horario in horarios_lista:
            aplicado = horario in logs_hoje
            log_item = logs_hoje.get(horario)
            if not aplicado:
                total_medicacoes_pendentes += 1

            medicacoes_hoje.append({
                "prescricao_id": p.id,
                "animal_id": p.animal_id,
                "animal_nome": p.animal.nome,
                "localizacao_baia": p.animal.localizacao_baia or "Geral",
                "medicamento": p.nome_medicamento,
                "dosagem": p.dosagem,
                "horario_previsto": horario,
                "horario_aplicado": log_item.horario_aplicado if log_item else None,
                "aplicado": aplicado,
                "instrucoes": p.instrucoes or ""
            })

    # Ordena medicações pelo horário previsto
    medicacoes_hoje.sort(key=lambda m: m["horario_previsto"])

    # Consolidação de vacinas previstas para hoje ou reforços próximos
    vacinas_hoje = []
    reforcos_query = Vaccination.query.join(Animal).filter(
        Animal.is_deleted == False,
        Animal.status_operacional.notin_([Animal.STATUS_ADOTADO, Animal.STATUS_OBITO]),
        Vaccination.data_reforco <= hoje
    ).order_by(Vaccination.data_reforco.asc()).all()

    for v in reforcos_query:
        vacinas_hoje.append({
            "vacina_id": v.id,
            "animal_id": v.animal_id,
            "animal_nome": v.animal.nome,
            "localizacao_baia": v.animal.localizacao_baia or "Geral",
            "nome_vacina": v.nome_vacina,
            "data_reforco": v.data_reforco.isoformat() if v.data_reforco else None,
            "atrasada": v.data_reforco < hoje if v.data_reforco else False
        })

    return jsonify({
        "data_referencia": hoje_str,
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


@core_bp.route("/animais", methods=["GET"])
def pagina_animais():
    """Página de listagem e catálogo de animais."""
    animais = Animal.query.filter_by(is_deleted=False).order_by(Animal.created_at.desc()).all()
    return render_template("animais.html", animais=[a.to_dict() for a in animais])


@core_bp.route("/animais/novo", methods=["GET"])
def novo_animal():
    """Página com formulário de cadastro de novo resgate."""
    return render_template("animal_formulario.html")


@core_bp.route("/animais/<int:animal_id>", methods=["GET"])
def ficha_animal(animal_id):
    """Página de ficha detalhada do animal conectada ao banco de dados."""
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()
    return render_template("animal_ficha.html", animal=animal.to_dict())


@core_bp.route("/hoje", methods=["GET"])
def pagina_hoje():
    """Painel operacional Hoje."""
    return render_template("hoje.html")


@core_bp.route("/entrar", methods=["GET"])
def pagina_login():
    """Página de login."""
    return render_template("login.html")
