from datetime import date
from flask import jsonify, request, current_app
from app.extensions import db
from app.models.animal import Animal
from app.models.health import Vaccination, Prescription, MedicalRecord
from app.utils.images import compress_and_save_photo
from app.utils.audit import log_audit_event
from app.utils.decorators import admin_required
from app.utils.validation import ApiError, parse_bool, parse_float, require_choice
from . import animals_bp


@animals_bp.route("", methods=["GET"])
@animals_bp.route("/", methods=["GET"])
def list_animals():
    """Listagem de animais com busca e filtros dinâmicos (RF10, RF11, RNF03)."""
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    per_page = min(max(request.args.get("per_page", 20, type=int) or 20, 1), 100)
    search_query = request.args.get("q", "").strip() or request.args.get("busca", "").strip()
    status_filter = request.args.get("status", "").strip()
    porte_filter = request.args.get("porte", "").strip()
    sexo_filter = request.args.get("sexo", "").strip()
    castrado_filter = request.args.get("castrado", "").strip().lower()
    idoso_filter = request.args.get("idoso", "").strip().lower()

    query = Animal.query.filter_by(is_deleted=False)

    if search_query:
        query = query.filter(
            db.or_(
                Animal.nome.ilike(f"%{search_query}%"),
                Animal.codigo_identificador.ilike(f"%{search_query}%"),
                Animal.raca.ilike(f"%{search_query}%")
            )
        )

    if status_filter:
        query = query.filter_by(status_operacional=status_filter)

    if porte_filter:
        query = query.filter_by(porte=porte_filter)

    if sexo_filter:
        query = query.filter_by(sexo=sexo_filter)

    if castrado_filter in ("true", "1", "sim"):
        query = query.filter_by(is_castrado=True)
    elif castrado_filter in ("false", "0", "nao", "não"):
        query = query.filter_by(is_castrado=False)

    if idoso_filter in ("true", "1", "sim"):
        query = query.filter_by(is_idoso=True)
    elif idoso_filter in ("false", "0", "nao", "não"):
        query = query.filter_by(is_idoso=False)

    query = query.order_by(Animal.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "pagina_atual": page,
        "por_pagina": per_page,
        "total_registros": pagination.total,
        "total_paginas": pagination.pages,
        "filtros_aplicados": {
            "busca": search_query,
            "status": status_filter,
            "porte": porte_filter,
            "sexo": sexo_filter,
            "castrado": castrado_filter,
            "idoso": idoso_filter
        },
        "animais": [animal.to_dict() for animal in pagination.items]
    }), 200


@animals_bp.route("", methods=["POST"])
@animals_bp.route("/", methods=["POST"])
def create_animal():
    """Cadastro básico de cão resgatado (RF05, RF07, RF08, RN01).
    Estado inicial obrigatório: 'em acolhimento' e data de entrada do dia.
    Suporta JSON ou multipart/form-data com upload de foto.
    """
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    nome = (data.get("nome") or "").strip()
    sexo = (data.get("sexo") or "").strip()
    porte = (data.get("porte") or "Médio").strip()

    if not nome or not sexo:
        raise ApiError("Dados incompletos", 400, "Nome e sexo são campos obrigatórios para o cadastro.")
    require_choice(sexo, "sexo", Animal.SEXOS)
    require_choice(porte, "porte", Animal.PORTES)
    peso_val = parse_float(data.get("peso_kg"), "peso_kg", minimo=0)

    foto_url = data.get("foto_url")
    if "foto" in request.files:
        foto_url = compress_and_save_photo(request.files["foto"]) or foto_url

    # Criação da entidade garantindo RN01 (status inicial 'em acolhimento' e data de hoje)
    animal = Animal(
        nome=nome,
        idade_estimada=data.get("idade_estimada"),
        sexo=sexo,
        raca=data.get("raca") or "Sem Raça Definida (SRD)",
        porte=porte,
        pelagem=data.get("pelagem"),
        peso_kg=peso_val,
        foto_url=foto_url,
        local_resgate=data.get("local_resgate"),
        data_entrada=date.today(), # RN01
        motivo_resgate=data.get("motivo_resgate"),
        is_castrado=parse_bool(data.get("is_castrado")),
        is_microchipado=parse_bool(data.get("is_microchipado")),
        is_idoso=parse_bool(data.get("is_idoso")),
        cuidados_especiais=data.get("cuidados_especiais"),
        localizacao_baia=data.get("localizacao_baia"),
        codigo_identificador=data.get("codigo_identificador"),
        status_operacional=Animal.STATUS_ACOLHIMENTO # RN01
    )

    db.session.add(animal)
    db.session.commit()

    log_audit_event(
        acao="ANIMAL_CADASTRADO",
        entidade="Animal",
        entidade_id=animal.id,
        detalhes=f"Cadastro do animal {animal.nome} (Status inicial: {animal.status_operacional})"
    )

    return jsonify({
        "sucesso": True,
        "mensagem": "Cão cadastrado com sucesso com estado inicial 'em acolhimento' (RN01).",
        "animal": animal.to_dict()
    }), 201


@animals_bp.route("/<int:animal_id>", methods=["GET"])
def get_animal(animal_id):
    """Consulta ficha completa do cão organizada por módulos (RF12)."""
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()

    # Busca registros relacionados
    vacinas = animal.vaccinations.order_by(Vaccination.data_aplicacao.desc()).all()
    prescricoes = animal.prescriptions.order_by(Prescription.data_inicio.desc()).all()
    prontuarios = animal.medical_records.order_by(MedicalRecord.data_evento.desc()).all()
    adocao_info = animal.adoption.to_dict() if animal.adoption else None

    return jsonify({
        "animal": animal.to_dict(),
        "vacinas": [v.to_dict() for v in vacinas],
        "prescricoes": [p.to_dict() for p in prescricoes],
        "prontuarios": [m.to_dict() for m in prontuarios],
        "adocao": adocao_info,
        "congelado": animal.is_frozen
    }), 200


@animals_bp.route("/<int:animal_id>", methods=["PUT", "PATCH"])
def update_animal(animal_id):
    """Edição cadastral do cão (RF09, RN05).
    Bloqueado caso o status seja 'adotado' ou 'óbito' (RN05).
    """
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()

    if animal.is_frozen:
        return jsonify({
            "erro": "Ficha congelada",
            "mensagem": f"O animal encontra-se com status '{animal.status_operacional}'. Cadastros e fichas de animais adotados ou com óbito são estritamente congelados para alterações (RN05)."
        }), 422

    data = request.get_json(silent=True) or request.form.to_dict() or {}

    if "nome" in data and not str(data["nome"]).strip():
        raise ApiError("Dados incompletos", 400, "O nome do animal não pode ficar vazio.")
    if "sexo" in data:
        require_choice(data["sexo"], "sexo", Animal.SEXOS)
    if "porte" in data:
        require_choice(data["porte"], "porte", Animal.PORTES)
    peso = parse_float(data["peso_kg"], "peso_kg", minimo=0) if "peso_kg" in data else None

    for field in ["nome", "idade_estimada", "sexo", "raca", "porte", "pelagem",
                  "local_resgate", "motivo_resgate", "cuidados_especiais",
                  "localizacao_baia", "codigo_identificador"]:
        if field in data:
            setattr(animal, field, data[field])

    if "peso_kg" in data:
        animal.peso_kg = peso

    for bool_field in ["is_castrado", "is_microchipado", "is_idoso"]:
        if bool_field in data:
            setattr(animal, bool_field, parse_bool(data[bool_field]))

    if "foto" in request.files:
        animal.foto_url = compress_and_save_photo(request.files["foto"]) or animal.foto_url
    elif "foto_url" in data:
        animal.foto_url = data["foto_url"]

    db.session.commit()

    log_audit_event(
        acao="ANIMAL_ATUALIZADO",
        entidade="Animal",
        entidade_id=animal.id,
        detalhes=f"Atualização dos dados cadastrais do animal {animal.nome}"
    )

    return jsonify({
        "sucesso": True,
        "mensagem": f"Dados do animal {animal.nome} atualizados com sucesso.",
        "animal": animal.to_dict()
    }), 200


@animals_bp.route("/<int:animal_id>/status", methods=["PATCH"])
def update_animal_status(animal_id):
    """Transição da máquina de estados operacionais do animal (RN02)."""
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()
    data = request.get_json(silent=True) or {}
    novo_status = data.get("status_operacional")

    if novo_status not in Animal.VALID_STATUSES:
        raise ApiError("Status inválido", 400, "Informe um status operacional válido.", status_permitidos=Animal.VALID_STATUSES)

    if animal.is_frozen:
        raise ApiError("Ficha congelada", 422,
                       f"Animais com status '{animal.status_operacional}' não podem mudar de situação (RN05).")

    if novo_status == Animal.STATUS_ADOTADO:
        raise ApiError("Adoção exige registro formal", 422,
                       "Para marcar como adotado, registre a adoção com nome, telefone e data do adotante (RN04, RF20).")

    if not Animal.can_transition(animal.status_operacional, novo_status):
        raise ApiError("Transição de status inválida", 422,
                       f"Não é possível mudar de '{animal.status_operacional}' para '{novo_status}' (RN02).")

    status_anterior = animal.status_operacional
    animal.status_operacional = novo_status
    db.session.commit()

    log_audit_event(
        acao="STATUS_ANIMAL_ALTERADO",
        entidade="Animal",
        entidade_id=animal.id,
        detalhes=f"Transição de status operacional: '{status_anterior}' -> '{novo_status}'"
    )

    return jsonify({
        "sucesso": True,
        "mensagem": f"Status operacional alterado para '{novo_status}'.",
        "animal": animal.to_dict()
    }), 200


@animals_bp.route("/<int:animal_id>", methods=["DELETE"])
@admin_required
def delete_animal(animal_id):
    """Exclusão lógica de registro de animal (RN03). Exclusiva da Administradora; proibida exclusão física."""
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()

    if animal.is_frozen:
        raise ApiError("Ficha congelada", 422,
                       "O histórico de animais adotados ou com óbito é preservado indefinidamente (RN05, RN06).")

    animal.is_deleted = True # RN03: Soft Delete
    db.session.commit()

    log_audit_event(
        acao="ANIMAL_EXCLUIDO_LOGICO",
        entidade="Animal",
        entidade_id=animal.id,
        detalhes=f"Exclusão lógica do animal {animal.nome} (RN03)"
    )

    return jsonify({
        "sucesso": True,
        "mensagem": "Registro de animal excluído logicamente com sucesso (RN03)."
    }), 200


@animals_bp.route("/<int:animal_id>/foto", methods=["POST"])
def upload_photo(animal_id):
    """Upload e compressão de foto do animal (RF06, RNF02).
    Comprime no servidor para tamanho inferior a 300 KB.
    """
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()

    if animal.is_frozen:
        raise ApiError("Ficha congelada", 422, "Não é possível alterar a foto de um animal com ficha congelada (RN05).")

    if "foto" not in request.files:
        raise ApiError("Arquivo ausente", 400, "Envie a imagem no campo 'foto'.")

    compressed_url = compress_and_save_photo(request.files["foto"])
    if not compressed_url:
        raise ApiError("Imagem inválida", 400, "Não foi possível processar a imagem fornecida.")

    animal.foto_url = compressed_url
    db.session.commit()

    log_audit_event(
        acao="FOTO_ANIMAL_ATUALIZADA",
        entidade="Animal",
        entidade_id=animal.id,
        detalhes=f"Upload de nova foto com compressão < 300KB para o animal {animal.nome}"
    )

    return jsonify({
        "sucesso": True,
        "mensagem": "Foto recebida e comprimida com sucesso (< 300 KB).",
        "foto_url": animal.foto_url
    }), 200
