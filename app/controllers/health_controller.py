from flask import Blueprint, jsonify, request, Response
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models.animal import Animal
from app.models.health import Vaccination, MedicalRecord, Prescription, MedicationLog
from app.services import ics
from app.utils import tempo
from app.services.audit import log_audit_event
from app.services.saude import (
    find_dose_log, is_prescription_active, logs_by_prescription, open_booster_filter,
    prescription_dict, split_horarios, vaccine_dicts,
)
from app.utils.validation import ApiError, clean_text, get_payload, is_horario, model_text, parse_date

health_bp = Blueprint("health", __name__, url_prefix="/api/saude")


def _normalizar_horarios(horarios):
    """Valida horários HH:MM separados por vírgula e devolve no formato '08:00, 20:00'.

    Horários repetidos são unificados e a lista fica em ordem crescente.
    """
    lista = split_horarios(horarios)
    if not lista or any(not is_horario(h) for h in lista):
        raise ApiError("Horários inválidos", 400, "Use o formato HH:MM separado por vírgula, por exemplo '08:00, 20:00'.")
    texto = ", ".join(sorted(set(lista)))
    limite = Prescription.__table__.c.horarios.type.length
    if limite and len(texto) > limite:
        raise ApiError("Horários inválidos", 400, "Há horários demais nesta prescrição.")
    return texto


def _animal_ou_404(animal_id):
    return Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()


def _ficha_congelada(mensagem):
    return jsonify({"erro": "Ficha congelada", "mensagem": mensagem}), 422


def _user_id():
    return current_user.id if current_user.is_authenticated else None


@health_bp.route("/vacinas/<int:animal_id>", methods=["GET", "POST"])
def vaccines(animal_id):
    """Cartão de vacinação digital (RF13)."""
    animal = _animal_ou_404(animal_id)
    hoje = tempo.hoje()

    if request.method == "POST":
        if animal.is_frozen:
            return _ficha_congelada("Não é permitido adicionar vacinas a um animal com histórico congelado (RN05).")

        data = get_payload()
        nome_vacina = model_text(data, Vaccination, "nome_vacina")

        if not nome_vacina:
            return jsonify({"erro": "Nome da vacina é obrigatório."}), 400

        data_aplicacao = parse_date(data.get("data_aplicacao"), "data_aplicacao", default=hoje)
        data_reforco = parse_date(data.get("data_reforco"), "data_reforco")
        if data_reforco and data_reforco < data_aplicacao:
            raise ApiError("Data inválida", 400, "A data de reforço não pode ser anterior à data de aplicação.")

        vacina = Vaccination(
            animal_id=animal.id,
            nome_vacina=nome_vacina,
            lote=model_text(data, Vaccination, "lote"),
            data_aplicacao=data_aplicacao,
            data_reforco=data_reforco,
            observacoes=clean_text(data, "observacoes"),
            aplicado_por_user_id=_user_id()
        )
        db.session.add(vacina)
        db.session.flush()
        log_audit_event(
            acao="VACINA_REGISTRADA",
            entidade="Vaccination",
            entidade_id=vacina.id,
            detalhes=f"Vacina {vacina.nome_vacina} aplicada ao animal {animal.nome}",
            commit=False,
        )
        db.session.commit()

        return jsonify({
            "sucesso": True,
            "mensagem": "Vacina registrada com sucesso.",
            "vacina": vacina.to_dict()
        }), 201

    vacinas = animal.vaccinations.order_by(Vaccination.data_aplicacao.desc()).all()
    return jsonify({
        "animal_id": animal.id,
        "vacinas": vaccine_dicts(vacinas, hoje)
    }), 200


@health_bp.route("/vacinas/item/<int:vaccination_id>", methods=["PATCH", "PUT"])
def update_vaccine(vaccination_id):
    """Correção de um registro de vacina (RF13), por exemplo a data de reforço. Respeita RN05."""
    vacina = db.get_or_404(Vaccination, vaccination_id)
    animal = vacina.animal
    if animal.is_deleted:
        raise ApiError("Recurso não encontrado", 404, "A rota ou registro solicitado não existe.")
    if animal.is_frozen:
        return _ficha_congelada("Não é permitido alterar vacinas de um animal com histórico congelado (RN05).")

    data = get_payload()
    alterados = []

    if "nome_vacina" in data:
        vacina.nome_vacina = model_text(data, Vaccination, "nome_vacina", obrigatorio=True)
        alterados.append("nome_vacina")
    if "lote" in data:
        vacina.lote = model_text(data, Vaccination, "lote")
        alterados.append("lote")
    if "observacoes" in data:
        vacina.observacoes = clean_text(data, "observacoes")
        alterados.append("observacoes")
    if "data_aplicacao" in data:
        nova = parse_date(data.get("data_aplicacao"), "data_aplicacao")
        if not nova:
            raise ApiError("Data inválida", 400, "A data de aplicação não pode ficar vazia.")
        vacina.data_aplicacao = nova
        alterados.append("data_aplicacao")
    if "data_reforco" in data:
        vacina.data_reforco = parse_date(data.get("data_reforco"), "data_reforco")
        alterados.append("data_reforco")

    if vacina.data_reforco and vacina.data_reforco < vacina.data_aplicacao:
        raise ApiError("Data inválida", 400, "A data de reforço não pode ser anterior à data de aplicação.")
    if not alterados:
        raise ApiError("Nada a alterar", 400, "Envie ao menos um campo da vacina para alterar.")

    log_audit_event(
        acao="VACINA_ATUALIZADA",
        entidade="Vaccination",
        entidade_id=vacina.id,
        detalhes=f"Vacina {vacina.nome_vacina} do animal {animal.nome} alterada (campos: {', '.join(alterados)})",
        commit=False,
    )
    db.session.commit()

    return jsonify({
        "sucesso": True,
        "mensagem": "Vacina atualizada com sucesso.",
        "vacina": vacina.to_dict()
    }), 200


@health_bp.route("/prontuario/<int:animal_id>", methods=["GET", "POST"])
def medical_records(animal_id):
    """Prontuário de histórico médico, consultas e exames (RF14)."""
    animal = _animal_ou_404(animal_id)

    if request.method == "POST":
        if animal.is_frozen:
            return _ficha_congelada("Não é permitido adicionar registros médicos a um animal com histórico congelado (RN05).")

        data = get_payload()
        diagnostico = clean_text(data, "diagnostico")
        tipo_evento = model_text(data, MedicalRecord, "tipo_evento", default="Consulta")

        if not diagnostico:
            return jsonify({"erro": "Diagnóstico/observação é obrigatório para o prontuário."}), 400

        data_evento = parse_date(data.get("data_evento"), "data_evento", default=tempo.hoje())

        record = MedicalRecord(
            animal_id=animal.id,
            tipo_evento=tipo_evento,
            data_evento=data_evento,
            veterinario_responsavel=model_text(data, MedicalRecord, "veterinario_responsavel"),
            clinica=model_text(data, MedicalRecord, "clinica"),
            diagnostico=diagnostico,
            procedimentos_realizados=clean_text(data, "procedimentos_realizados"),
            cadastrado_por_user_id=_user_id()
        )
        db.session.add(record)
        db.session.flush()
        log_audit_event(
            acao="PRONTUARIO_REGISTRADO",
            entidade="MedicalRecord",
            entidade_id=record.id,
            detalhes=f"Registro médico do tipo '{record.tipo_evento}' para o animal {animal.nome}",
            commit=False,
        )
        db.session.commit()

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
    animal = _animal_ou_404(animal_id)
    hoje = tempo.hoje()

    if request.method == "POST":
        if animal.is_frozen:
            return _ficha_congelada("Não é permitido prescrever medicações para um animal com histórico congelado (RN05).")

        if animal.status_operacional not in Animal.STATUS_PRESCREVIVEIS:
            raise ApiError("Status não permite prescrição", 422,
                           f"Medicações só podem ser prescritas para animais 'em acolhimento', 'em tratamento' ou 'lar temporário' (status atual: '{animal.status_operacional}') (RN08).")

        data = get_payload()
        nome_medicamento = model_text(data, Prescription, "nome_medicamento")
        dosagem = model_text(data, Prescription, "dosagem")
        horarios = clean_text(data, "horarios")

        if not nome_medicamento or not dosagem or not horarios:
            return jsonify({
                "erro": "Campos obrigatórios ausentes",
                "mensagem": "Nome do medicamento, dosagem e horários são obrigatórios."
            }), 400

        data_inicio = parse_date(data.get("data_inicio"), "data_inicio", default=hoje)
        data_fim = parse_date(data.get("data_fim"), "data_fim", default=data_inicio)
        if data_fim < data_inicio:
            raise ApiError("Data inválida", 400, "A data final não pode ser anterior à data inicial da prescrição.")
        horarios = _normalizar_horarios(horarios)

        prescricao = Prescription(
            animal_id=animal.id,
            nome_medicamento=nome_medicamento,
            dosagem=dosagem,
            horarios=horarios,
            data_inicio=data_inicio,
            data_fim=data_fim,
            instrucoes=clean_text(data, "instrucoes"),
            prescrito_por_user_id=_user_id()
        )
        db.session.add(prescricao)
        db.session.flush()
        log_audit_event(
            acao="PRESCRICAO_CADASTRADA",
            entidade="Prescription",
            entidade_id=prescricao.id,
            detalhes=f"Prescrição de {prescricao.nome_medicamento} ({prescricao.dosagem}) para o animal {animal.nome}",
            commit=False,
        )
        db.session.commit()

        return jsonify({
            "sucesso": True,
            "mensagem": "Prescrição cadastrada com sucesso.",
            "prescricao": prescription_dict(prescricao, hoje)
        }), 201

    prescricoes = animal.prescriptions.order_by(Prescription.data_inicio.desc()).all()

    # Enriquece as prescrições com as baixas de hoje (uma consulta para todas)
    logs = logs_by_prescription([p.id for p in prescricoes], hoje)
    resultado = []
    for p in prescricoes:
        p_dict = prescription_dict(p, hoje)
        p_dict["logs_hoje"] = [log.to_dict() for log in logs[p.id]]
        resultado.append(p_dict)

    return jsonify({
        "animal_id": animal.id,
        "prescricoes": resultado
    }), 200


@health_bp.route("/prescricoes/item/<int:prescription_id>", methods=["PATCH", "PUT"])
def update_prescription(prescription_id):
    """Alteração de uma prescrição (RF15, RN10): dosagem, horários, período ou instruções.

    Para encerrar um tratamento antes do previsto, basta antecipar `data_fim`.
    """
    prescricao = db.get_or_404(Prescription, prescription_id)
    animal = prescricao.animal
    if animal.is_deleted:
        raise ApiError("Recurso não encontrado", 404, "A rota ou registro solicitado não existe.")
    if animal.is_frozen:
        return _ficha_congelada("Não é permitido alterar medicações de um animal com histórico congelado (RN05).")

    data = get_payload()
    hoje = tempo.hoje()
    fim_anterior = prescricao.data_fim
    alterados = []

    for campo in ("nome_medicamento", "dosagem"):
        if campo in data:
            setattr(prescricao, campo, model_text(data, Prescription, campo, obrigatorio=True))
            alterados.append(campo)
    if "horarios" in data:
        prescricao.horarios = _normalizar_horarios(clean_text(data, "horarios", obrigatorio=True))
        alterados.append("horarios")
    if "instrucoes" in data:
        prescricao.instrucoes = clean_text(data, "instrucoes")
        alterados.append("instrucoes")
    for campo in ("data_inicio", "data_fim"):
        if campo in data:
            nova = parse_date(data.get(campo), campo)
            if not nova:
                raise ApiError("Data inválida", 400, f"O campo '{campo}' não pode ficar vazio.")
            setattr(prescricao, campo, nova)
            alterados.append(campo)

    if prescricao.data_fim < prescricao.data_inicio:
        raise ApiError("Data inválida", 400, "A data final não pode ser anterior à data inicial da prescrição.")
    if not alterados:
        raise ApiError("Nada a alterar", 400, "Envie ao menos um campo da prescrição para alterar.")

    # RN08: fora dos status que permitem prescrição só é possível manter ou encurtar o tratamento
    if animal.status_operacional not in Animal.STATUS_PRESCREVIVEIS and prescricao.data_fim > fim_anterior:
        raise ApiError("Status não permite prescrição", 422,
                       f"Não é possível prolongar a medicação de um animal com status '{animal.status_operacional}' (RN08).")

    log_audit_event(
        acao="PRESCRICAO_ATUALIZADA",
        entidade="Prescription",
        entidade_id=prescricao.id,
        detalhes=f"Prescrição de {prescricao.nome_medicamento} do animal {animal.nome} alterada (campos: {', '.join(alterados)})",
        commit=False,
    )
    db.session.commit()

    return jsonify({
        "sucesso": True,
        "mensagem": "Prescrição atualizada com sucesso.",
        "prescricao": prescription_dict(prescricao, hoje)
    }), 200


def _resposta_ja_baixado(log, horario_previsto):
    return jsonify({
        "sucesso": True,
        "mensagem": f"A dose das {horario_previsto} já foi baixada anteriormente.",
        "ja_baixado": True,
        "log": log.to_dict()
    }), 200


@health_bp.route("/medicacao/baixa/<int:prescription_id>", methods=["POST"])
def log_medication_dose(prescription_id):
    """Baixa diária de medicação diretamente na API (RF16).
    Registra a aplicação e impede duplicidade de baixa no mesmo horário programado no dia.
    """
    prescricao = db.get_or_404(Prescription, prescription_id)
    animal = prescricao.animal

    if animal.is_deleted:
        raise ApiError("Recurso não encontrado", 404, "A rota ou registro solicitado não existe.")

    if animal.is_frozen:
        return _ficha_congelada("Não é permitido dar baixa em medicação de animal congelado (RN05).")

    hoje = tempo.hoje()
    if not is_prescription_active(prescricao, hoje):
        raise ApiError("Prescrição fora da validade", 422,
                       "Esta prescrição não está vigente hoje, não é possível dar baixa (RN09).")

    data = get_payload()
    horarios_prescritos = split_horarios(prescricao.horarios)
    horario_previsto = clean_text(data, "horario_previsto", default="")
    if not horario_previsto and len(horarios_prescritos) == 1:
        horario_previsto = horarios_prescritos[0]
    if horario_previsto not in horarios_prescritos:
        raise ApiError("Horário inválido", 400,
                       "Informe 'horario_previsto' com um dos horários prescritos.", horarios=horarios_prescritos)

    horario_aplicado = clean_text(data, "horario_aplicado") or tempo.agora().strftime("%H:%M")
    if not is_horario(horario_aplicado):
        raise ApiError("Horário inválido", 400, "O campo 'horario_aplicado' deve estar no formato HH:MM.")

    # RF16: impede baixa duplicada do mesmo horário no mesmo dia
    existente = find_dose_log(prescricao.id, hoje, horario_previsto)
    if existente:
        return _resposta_ja_baixado(existente, horario_previsto)

    # Guardados antes de gravar: se a gravação falhar, o rollback invalida os objetos da sessão
    prescricao_id, nome_medicamento, nome_animal = prescricao.id, prescricao.nome_medicamento, animal.nome

    med_log = MedicationLog(
        prescription_id=prescricao_id,
        user_id=_user_id(),
        data_aplicacao=hoje,
        horario_previsto=horario_previsto,
        horario_aplicado=horario_aplicado,
        observacoes=clean_text(data, "observacoes")
    )
    try:
        db.session.add(med_log)
        db.session.flush()
        log_audit_event(
            acao="BAIXA_MEDICACAO",
            entidade="MedicationLog",
            entidade_id=med_log.id,
            detalhes=f"Baixa da dose {horario_previsto} de {nome_medicamento} para o animal {nome_animal}",
            commit=False,
        )
        db.session.commit()
    except IntegrityError:
        # Duas baixas simultâneas da mesma dose: a restrição única do banco (prescrição + dia +
        # horário previsto) deixa passar só a primeira. Quem perdeu a corrida recebe a mesma
        # resposta de "já baixado", e não um erro.
        db.session.rollback()
        existente = find_dose_log(prescricao_id, hoje, horario_previsto)
        if existente:
            return _resposta_ja_baixado(existente, horario_previsto)
        raise

    return jsonify({
        "sucesso": True,
        "mensagem": "Baixa de medicação realizada com sucesso para o dia de hoje (RF16).",
        "prescricao_id": prescription_id,
        "log": med_log.to_dict()
    }), 200


# ---------------------------------------------------------------------------
# Lembretes em arquivo .ics (RF18, RN11)
# ---------------------------------------------------------------------------

def _eventos_de_medicacao(prescricao, animal_nome, baia):
    """Um evento diário recorrente por horário prescrito, cobrindo todo o período da prescrição."""
    resumo = f"Medicação: {prescricao.nome_medicamento} ({animal_nome})"
    dias = (prescricao.data_fim - prescricao.data_inicio).days + 1
    detalhes = [f"Animal: {animal_nome}", f"Dosagem: {prescricao.dosagem}", f"Horários: {prescricao.horarios}"]
    if baia:
        detalhes.insert(1, f"Local: {baia}")
    if prescricao.instrucoes:
        detalhes.append(f"Instruções: {prescricao.instrucoes}")
    descricao = "\n".join(detalhes)

    horarios = [h for h in split_horarios(prescricao.horarios) if is_horario(h)]
    if not horarios:
        # Prescrição antiga com horário fora do padrão: vira lembrete de dia inteiro
        return [ics.all_day_event(f"prescricao-{prescricao.id}", resumo, descricao, prescricao.data_inicio, alarme=None)]
    return [
        ics.daily_event(f"prescricao-{prescricao.id}-{h.replace(':', '')}", resumo, descricao,
                        prescricao.data_inicio, h, dias)
        for h in horarios
    ]


def _evento_de_reforco(vacina, animal_nome):
    detalhes = [f"Animal: {animal_nome}", f"Vacina: {vacina.nome_vacina}", f"Lote anterior: {vacina.lote or 'não informado'}"]
    if vacina.observacoes:
        detalhes.append(f"Observações: {vacina.observacoes}")
    return ics.all_day_event(f"vacina-{vacina.id}", f"Reforço de Vacina: {vacina.nome_vacina} ({animal_nome})",
                             "\n".join(detalhes), vacina.data_reforco)


def _eventos_de_lembrete(animal_id=None):
    """Lembretes que ainda fazem sentido: prescrições não encerradas e reforços de hoje em diante,
    somente de animais sob os cuidados da ONG (ficha não congelada)."""
    hoje = tempo.hoje()
    sob_cuidados = [
        Animal.is_deleted.is_(False),
        Animal.status_operacional.notin_([Animal.STATUS_ADOTADO, Animal.STATUS_OBITO]),
    ]
    if animal_id is not None:
        sob_cuidados.append(Animal.id == animal_id)

    eventos = []
    prescricoes = (db.session.query(Prescription, Animal.nome, Animal.localizacao_baia)
                   .join(Animal, Prescription.animal_id == Animal.id)
                   .filter(*sob_cuidados, Prescription.data_fim >= hoje)
                   .order_by(Prescription.data_inicio.asc(), Prescription.id.asc()).all())
    for prescricao, animal_nome, baia in prescricoes:
        eventos += _eventos_de_medicacao(prescricao, animal_nome, baia)

    reforcos = (db.session.query(Vaccination, Animal.nome)
                .join(Animal, Vaccination.animal_id == Animal.id)
                .filter(*sob_cuidados, Vaccination.data_reforco >= hoje, open_booster_filter(hoje))
                .order_by(Vaccination.data_reforco.asc(), Vaccination.id.asc()).all())
    for vacina, animal_nome in reforcos:
        eventos.append(_evento_de_reforco(vacina, animal_nome))
    return eventos


def _resposta_ics(nome_calendario, eventos, arquivo):
    return Response(
        ics.build_calendar(nome_calendario, eventos, gerado_em=tempo.agora_utc()),
        mimetype="text/calendar",
        headers={
            "Content-Disposition": f"attachment; filename={arquivo}",
            "Cache-Control": "no-store",
            "X-Total-Lembretes": str(len(eventos)),
        }
    )


@health_bp.route("/lembretes/<int:animal_id>.ics", methods=["GET"])
def export_ics(animal_id):
    """Exportação de lembretes em arquivo universal .ics (RF18, RN11)."""
    animal = _animal_ou_404(animal_id)
    return _resposta_ics(f"Lembretes de Saúde - {animal.nome}", _eventos_de_lembrete(animal.id),
                         f"lembretes_animal_{animal.id}.ics")


@health_bp.route("/lembretes.ics", methods=["GET"])
def export_ics_all():
    """Lembretes de todos os animais sob os cuidados da ONG em um único arquivo .ics (RF18, RN11)."""
    return _resposta_ics("Lembretes de Saúde - GAPAR", _eventos_de_lembrete(), "lembretes_gapar.ics")
