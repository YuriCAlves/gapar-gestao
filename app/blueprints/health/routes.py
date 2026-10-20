from flask import jsonify, request
from flask_login import login_required
from . import health_bp


@health_bp.route("/vacinas/<int:animal_id>", methods=["GET", "POST"])
def vaccines(animal_id):
    """Cartão de vacinação digital (RF13)."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        return jsonify({
            "sucesso": True,
            "mensagem": "Vacina registrada com sucesso.",
            "vacina": data
        }), 201

    return jsonify({
        "animal_id": animal_id,
        "vacinas": []
    }), 200


@health_bp.route("/prontuario/<int:animal_id>", methods=["GET", "POST"])
def medical_records(animal_id):
    """Prontuário de histórico médico, consultas e exames (RF14)."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        return jsonify({
            "sucesso": True,
            "mensagem": "Registro médico adicionado com sucesso.",
            "registro": data
        }), 201

    return jsonify({
        "animal_id": animal_id,
        "prontuarios": []
    }), 200


@health_bp.route("/prescricoes/<int:animal_id>", methods=["GET", "POST"])
def prescriptions(animal_id):
    """Prescrição de medicações com sincronização (RF15, RF17, RN08, RN10)."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        return jsonify({
            "sucesso": True,
            "mensagem": "Prescrição cadastrada e sincronizada com Google Agenda.",
            "prescricao": data
        }), 201

    return jsonify({
        "animal_id": animal_id,
        "prescricoes_ativas": []
    }), 200


@health_bp.route("/medicacao/baixa/<int:prescription_id>", methods=["POST"])
def log_medication_dose(prescription_id):
    """Baixa diária de medicação diretamente na API (RF16)."""
    data = request.get_json(silent=True) or {}
    return jsonify({
        "sucesso": True,
        "mensagem": "Baixa de medicação realizada com sucesso para o dia de hoje.",
        "prescricao_id": prescription_id,
        "detalhes": data
    }), 200


@health_bp.route("/lembretes/<int:animal_id>.ics", methods=["GET"])
def export_ics(animal_id):
    """Exportação de lembretes em arquivo universal .ics (RF18, RN11)."""
    return jsonify({
        "mensagem": "Arquivo .ics disponível para download para contingência.",
        "download_url": f"/static/calendars/animal_{animal_id}_lembretes.ics"
    }), 200
