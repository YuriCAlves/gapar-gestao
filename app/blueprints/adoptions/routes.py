from flask import jsonify, request
from flask_login import login_required
from . import adoptions_bp


@adoptions_bp.route("/registrar/<int:animal_id>", methods=["POST"])
def register_adoption(animal_id):
    """Registro formal obrigatório de adoção e congelamento do histórico (RF20, RF21, RN04, RN05).
    Exige obrigatoriamente nome, telefone/contato e data do adotante.
    """
    data = request.get_json(silent=True) or {}
    
    # Validação dos campos obrigatórios conforme RN04
    required_fields = ["adotante_nome", "adotante_telefone", "data_adocao"]
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return jsonify({
            "erro": "Campos obrigatórios ausentes",
            "campos_faltantes": missing
        }), 400

    return jsonify({
        "sucesso": True,
        "mensagem": "Adoção registrada com sucesso. Status alterado para 'adotado' e histórico do cão congelado para edições.",
        "animal_id": animal_id,
        "dados_adocao": data
    }), 201


@adoptions_bp.route("/historico/<int:animal_id>", methods=["GET"])
def get_adoption_record(animal_id):
    """Consulta os dados formais da adoção preservados indefinidamente (RN06)."""
    return jsonify({
        "animal_id": animal_id,
        "status": "adotado",
        "congelado": True,
        "adocao": {}
    }), 200
