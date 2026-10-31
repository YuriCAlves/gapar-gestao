from datetime import date
from flask import jsonify, render_template
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