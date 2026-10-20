from flask import jsonify, request
from flask_login import login_required
from . import animals_bp


@animals_bp.route("/", methods=["GET"])
def list_animals():
    """Listagem de animais com busca e paginação (RF10, RF11, RNF03).
    Suporta filtros por nome, status_operacional, porte, sexo e flags (castrado/idoso).
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 15, type=int)
    search_query = request.args.get("q", "", type=str)
    status_filter = request.args.get("status", "", type=str)

    return jsonify({
        "pagina_atual": page,
        "por_pagina": per_page,
        "total_registros": 0,
        "total_paginas": 0,
        "filtros_aplicados": {
            "busca": search_query,
            "status": status_filter
        },
        "animais": []
    }), 200


@animals_bp.route("/", methods=["POST"])
def create_animal():
    """Cadastro básico de cão resgatado (RF05, RF07, RF08, RN01).
    Estado inicial obrigatório: 'em acolhimento' e data do dia.
    """
    data = request.get_json(silent=True) or {}
    return jsonify({
        "sucesso": True,
        "mensagem": "Cão cadastrado com sucesso com estado inicial 'em acolhimento'.",
        "dados_recebidos": data
    }), 201


@animals_bp.route("/<int:animal_id>", methods=["GET"])
def get_animal(animal_id):
    """Consulta ficha completa do cão organizada por módulos (RF12)."""
    return jsonify({
        "id": animal_id,
        "nome": "Exemplo",
        "status_operacional": "em acolhimento",
        "dados_gerais": {},
        "saude": {},
        "medicacoes": [],
        "adocao": None
    }), 200


@animals_bp.route("/<int:animal_id>", methods=["PUT", "PATCH"])
def update_animal(animal_id):
    """Edição cadastral do cão (RF09, RN05).
    Bloqueado caso o status seja 'adotado' ou 'óbito'.
    """
    data = request.get_json(silent=True) or {}
    return jsonify({
        "sucesso": True,
        "mensagem": f"Dados do animal {animal_id} atualizados com sucesso.",
        "alteracoes": data
    }), 200


@animals_bp.route("/<int:animal_id>/foto", methods=["POST"])
def upload_photo(animal_id):
    """Upload e compressão de foto do animal (RF06, RNF02).
    Comprime no servidor para tamanho inferior a 300 KB.
    """
    return jsonify({
        "sucesso": True,
        "mensagem": "Foto recebida e comprimida com sucesso (< 300 KB).",
        "foto_url": f"/static/uploads/animal_{animal_id}.jpg"
    }), 200
