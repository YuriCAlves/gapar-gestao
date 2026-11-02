from datetime import date
from flask import jsonify, render_template, abort
from flask_login import login_required
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
            "auth": "/auth/status"
        }
    }), 200


@core_bp.route("/api/hoje", methods=["GET"])
def today_dashboard():
    """Painel operacional consolidado 'Hoje' (RF23).
    Retorna a lista de medicações e vacinas a serem aplicadas na data atual.
    """
    today_str = date.today().isoformat()
    return jsonify({
        "data_referencia": today_str,
        "total_medicacoes_pendentes": 0,
        "total_vacinas_pendentes": 0,
        "medicacoes_hoje": [],
        "vacinas_hoje": []
    }), 200

    
@core_bp.route("/animais", methods=["GET"])
def pagina_animais():
    return render_template("animais.html")


@core_bp.route("/animais/novo", methods=["GET"])
def novo_animal():
    return render_template("animal_formulario.html")


@core_bp.route("/animais/<int:animal_id>", methods=["GET"])
def ficha_animal(animal_id):
    animais_exemplo = {
        1: {
            "id": 1,
            "nome": "Rex",
            "sexo": "Macho",
            "porte": "Médio",
            "status_operacional": "em acolhimento",
            "is_castrado": True,
            "is_idoso": False,
        },
        2: {
            "id": 2,
            "nome": "Luna",
            "sexo": "Fêmea",
            "porte": "Pequeno",
            "status_operacional": "em tratamento",
            "is_castrado": False,
            "is_idoso": True,
        },
        3: {
            "id": 3,
            "nome": "Thor",
            "sexo": "Macho",
            "porte": "Grande",
            "status_operacional": "disponível",
            "is_castrado": True,
            "is_idoso": True,
        },
    }

    animal = animais_exemplo.get(animal_id)

    if animal is None:
        abort(404)

    return render_template("animal_ficha.html", animal=animal)

@core_bp.route("/hoje", methods=["GET"])
def pagina_hoje():
    return render_template("hoje.html")