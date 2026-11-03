from datetime import date, datetime
from flask import jsonify, request, Response
from flask_login import login_required, current_user
from app.extensions import db
from app.models.animal import Animal
from app.models.health import Vaccination, MedicalRecord, Prescription, MedicationLog
from app.utils.audit import log_audit_event
from . import health_bp


@health_bp.route("/vacinas/<int:animal_id>", methods=["GET", "POST"])
def vaccines(animal_id):
    """Cartão de vacinação digital (RF13)."""
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()

    if request.method == "POST":
        if animal.is_frozen:
            return jsonify({
                "erro": "Ficha congelada",
                "mensagem": "Não é permitido adicionar vacinas a um animal com histórico congelado (RN05)."
            }), 422

        data = request.get_json(silent=True) or request.form.to_dict() or {}
        nome_vacina = data.get("nome_vacina", "").strip()

        if not nome_vacina:
            return jsonify({"erro": "Nome da vacina é obrigatório."}), 400

        data_aplicacao = date.today()
        if data.get("data_aplicacao"):
            try:
                data_aplicacao = date.fromisoformat(data["data_aplicacao"])
            except ValueError:
                pass

        data_reforco = None
        if data.get("data_reforco"):
            try:
                data_reforco = date.fromisoformat(data["data_reforco"])
            except ValueError:
                pass

        user_id = current_user.id if current_user.is_authenticated else None

        vacina = Vaccination(
            animal_id=animal.id,
            nome_vacina=nome_vacina,
            lote=data.get("lote"),
            data_aplicacao=data_aplicacao,
            data_reforco=data_reforco,
            observacoes=data.get("observacoes"),
            aplicado_por_user_id=user_id
        )
        db.session.add(vacina)
        db.session.commit()

        log_audit_event(
            acao="VACINA_REGISTRADA",
            entidade="Vaccination",
            entidade_id=vacina.id,
            detalhes=f"Vacina {vacina.nome_vacina} aplicada ao animal {animal.nome}"
        )

        return jsonify({
            "sucesso": True,
            "mensagem": "Vacina registrada com sucesso.",
            "vacina": vacina.to_dict()
        }), 201

    vacinas = animal.vaccinations.order_by(Vaccination.data_aplicacao.desc()).all()
    return jsonify({
        "animal_id": animal.id,
        "vacinas": [v.to_dict() for v in vacinas]
    }), 200


@health_bp.route("/prontuario/<int:animal_id>", methods=["GET", "POST"])
def medical_records(animal_id):
    """Prontuário de histórico médico, consultas e exames (RF14)."""
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()

    if request.method == "POST":
        if animal.is_frozen:
            return jsonify({
                "erro": "Ficha congelada",
                "mensagem": "Não é permitido adicionar registros médicos a um animal com histórico congelado (RN05)."
            }), 422

        data = request.get_json(silent=True) or request.form.to_dict() or {}
        diagnostico = data.get("diagnostico", "").strip()
        tipo_evento = data.get("tipo_evento", "Consulta").strip()

        if not diagnostico:
            return jsonify({"erro": "Diagnóstico/observação é obrigatório para o prontuário."}), 400

        data_evento = date.today()
        if data.get("data_evento"):
            try:
                data_evento = date.fromisoformat(data["data_evento"])
            except ValueError:
                pass

        user_id = current_user.id if current_user.is_authenticated else None

        record = MedicalRecord(
            animal_id=animal.id,
            tipo_evento=tipo_evento,
            data_evento=data_evento,
            veterinario_responsavel=data.get("veterinario_responsavel"),
            clinica=data.get("clinica"),
            diagnostico=diagnostico,
            procedimentos_realizados=data.get("procedimentos_realizados"),
            cadastrado_por_user_id=user_id
        )
        db.session.add(record)
        db.session.commit()

        log_audit_event(
            acao="PRONTUARIO_REGISTRADO",
            entidade="MedicalRecord",
            entidade_id=record.id,
            detalhes=f"Registro médico do tipo '{record.tipo_evento}' para o animal {animal.nome}"
        )

        return jsonify({
            "sucesso": True,
            "mensagem": "Registro médico adicionado com sucesso.",
            "registro": record.to_dict()
        }), 201

    prontuarios = animal.medical_records.order_by(MedicalRecord.data_evento.desc()).all()
    return jsonify({
        "animal_id": animal.id,
        "prontuarios": [p.to_dict() for p in prontuarios]
    }), 200


@health_bp.route("/prescricoes/<int:animal_id>", methods=["GET", "POST"])
def prescriptions(animal_id):
    """Prescrição de medicações (RF15, RN08, RN09, RN10)."""
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()

    if request.method == "POST":
        if animal.is_frozen:
            return jsonify({
                "erro": "Ficha congelada",
                "mensagem": "Não é permitido prescrever medicações para um animal com histórico congelado (RN05)."
            }), 422

        data = request.get_json(silent=True) or request.form.to_dict() or {}
        nome_medicamento = data.get("nome_medicamento", "").strip()
        dosagem = data.get("dosagem", "").strip()
        horarios = data.get("horarios", "").strip()

        if not nome_medicamento or not dosagem or not horarios:
            return jsonify({
                "erro": "Campos obrigatórios ausentes",
                "mensagem": "Nome do medicamento, dosagem e horários são obrigatórios."
            }), 400

        data_inicio = date.today()
        if data.get("data_inicio"):
            try:
                data_inicio = date.fromisoformat(data["data_inicio"])
            except ValueError:
                pass

        data_fim = data_inicio
        if data.get("data_fim"):
            try:
                data_fim = date.fromisoformat(data["data_fim"])
            except ValueError:
                pass

        user_id = current_user.id if current_user.is_authenticated else None

        prescricao = Prescription(
            animal_id=animal.id,
            nome_medicamento=nome_medicamento,
            dosagem=dosagem,
            horarios=horarios,
            data_inicio=data_inicio,
            data_fim=data_fim,
            instrucoes=data.get("instrucoes"),
            prescrito_por_user_id=user_id
        )
        db.session.add(prescricao)
        db.session.commit()

        log_audit_event(
            acao="PRESCRICAO_CADASTRADA",
            entidade="Prescription",
            entidade_id=prescricao.id,
            detalhes=f"Prescrição de {prescricao.nome_medicamento} ({prescricao.dosagem}) para o animal {animal.nome}"
        )

        return jsonify({
            "sucesso": True,
            "mensagem": "Prescrição cadastrada com sucesso.",
            "prescricao": prescricao.to_dict()
        }), 201

    prescricoes = animal.prescriptions.order_by(Prescription.data_inicio.desc()).all()
    
    # Enriquece as prescrições com os logs de aplicação de hoje
    hoje = date.today()
    resultado = []
    for p in prescricoes:
        p_dict = p.to_dict()
        logs_hoje = [log.to_dict() for log in p.logs.filter_by(data_aplicacao=hoje).all()]
        p_dict["logs_hoje"] = logs_hoje
        resultado.append(p_dict)

    return jsonify({
        "animal_id": animal.id,
        "prescricoes": resultado
    }), 200


@health_bp.route("/medicacao/baixa/<int:prescription_id>", methods=["POST"])
def log_medication_dose(prescription_id):
    """Baixa diária de medicação diretamente na API (RF16).
    Registra a aplicação e impede duplicidade de baixa no mesmo horário programado no dia.
    """
    prescricao = Prescription.query.get_or_404(prescription_id)
    animal = prescricao.animal

    if animal.is_frozen:
        return jsonify({
            "erro": "Ficha congelada",
            "mensagem": "Não é permitido dar baixa em medicação de animal congelado (RN05)."
        }), 422

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    horario_previsto = data.get("horario_previsto")
    horario_aplicado = data.get("horario_aplicado") or datetime.now().strftime("%H:%M")
    hoje = date.today()

    # Prevenção de duplicidade: checa se já houve baixa para este mesmo horário previsto hoje
    if horario_previsto:
        existente = MedicationLog.query.filter_by(
            prescription_id=prescricao.id,
            data_aplicacao=hoje,
            horario_previsto=horario_previsto
        ).first()

        if existente:
            return jsonify({
                "sucesso": True,
                "mensagem": f"A dose das {horario_previsto} já foi baixada anteriormente.",
                "ja_baixado": True,
                "log": existente.to_dict()
            }), 200

    user_id = current_user.id if current_user.is_authenticated else None

    med_log = MedicationLog(
        prescription_id=prescricao.id,
        user_id=user_id,
        data_aplicacao=hoje,
        horario_previsto=horario_previsto,
        horario_aplicado=horario_aplicado,
        observacoes=data.get("observacoes")
    )
    db.session.add(med_log)
    db.session.commit()

    log_audit_event(
        acao="BAIXA_MEDICACAO",
        entidade="MedicationLog",
        entidade_id=med_log.id,
        detalhes=f"Baixa da dose {horario_previsto or ''} de {prescricao.nome_medicamento} para o animal {animal.nome}"
    )

    return jsonify({
        "sucesso": True,
        "mensagem": "Baixa de medicação realizada com sucesso para o dia de hoje (RF16).",
        "prescricao_id": prescription_id,
        "log": med_log.to_dict()
    }), 200


@health_bp.route("/lembretes/<int:animal_id>.ics", methods=["GET"])
def export_ics(animal_id):
    """Exportação de lembretes em arquivo universal .ics (RF18, RN11)."""
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()
    
    linhas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//GAPAR Gestao//Saude Animal//PT-BR",
        f"X-WR-CALNAME:Lembretes de Saude - {animal.nome}"
    ]

    # Eventos de Vacinação
    for v in animal.vaccinations:
        if v.data_reforco:
            dt_str = v.data_reforco.strftime("%Y%m%d")
            linhas.extend([
                "BEGIN:VEVENT",
                f"SUMMARY:Reforço de Vacina: {v.nome_vacina} ({animal.nome})",
                f"DESCRIPTION:Animal: {animal.nome}\\nLote: {v.lote or 'N/I'}\\nObservações: {v.observacoes or 'N/A'}",
                f"DTSTART;VALUE=DATE:{dt_str}",
                f"DTEND;VALUE=DATE:{dt_str}",
                f"UID:vacina-{v.id}-{animal.id}@gapargestao.ong",
                "END:VEVENT"
            ])

    # Eventos de Prescrição
    for p in animal.prescriptions:
        if p.is_active:
            dt_start = p.data_inicio.strftime("%Y%m%d")
            dt_end = p.data_fim.strftime("%Y%m%d")
            linhas.extend([
                "BEGIN:VEVENT",
                f"SUMMARY:Medicação: {p.nome_medicamento} ({animal.nome})",
                f"DESCRIPTION:Dosagem: {p.dosagem}\\nHorários: {p.horarios}\\nInstruções: {p.instrucoes or ''}",
                f"DTSTART;VALUE=DATE:{dt_start}",
                f"DTEND;VALUE=DATE:{dt_end}",
                f"UID:prescricao-{p.id}-{animal.id}@gapargestao.ong",
                "END:VEVENT"
            ])

    linhas.append("END:VCALENDAR")
    conteudo_ics = "\r\n".join(linhas)

    return Response(
        conteudo_ics,
        mimetype="text/calendar",
        headers={"Content-Disposition": f"attachment; filename=lembretes_animal_{animal.id}.ics"}
    )
