from flask import jsonify, request
from app.extensions import db
from app.models.animal import Animal
from app.models.health import Vaccination, Prescription, MedicalRecord
from app.utils import tempo
from app.utils.images import compress_and_save_photo
from app.utils.audit import log_audit_event
from app.utils.decorators import admin_required
from app.utils.saude import prescription_dict, vaccine_dicts
from app.utils.validation import (
    ApiError, clean_text, get_payload, model_text, parse_bool, parse_date, parse_float, require_choice,
)
from . import animals_bp

RACA_PADRAO = "Sem Raça Definida (SRD)"

# Textos opcionais do cadastro com tamanho limitado pela coluna
CAMPOS_TEXTO_CURTO = ["idade_estimada", "pelagem", "local_resgate", "localizacao_baia", "codigo_identificador"]
# Textos opcionais sem limite de tamanho
CAMPOS_TEXTO_LONGO = ["motivo_resgate", "cuidados_especiais"]
CAMPOS_BOOLEANOS = ["is_castrado", "is_microchipado", "is_idoso"]

_SIM = ("true", "1", "sim")
_NAO = ("false", "0", "nao", "não")


def _foto_url_informada(data):
    """Endereço de foto enviado como texto (sem upload): aceita apenas URL http(s) ou caminho do site."""
    url = model_text(data, Animal, "foto_url")
    if url and not url.startswith(("http://", "https://", "/")):
        raise ApiError("Valor inválido", 400, "O campo 'foto_url' deve ser um endereço de imagem válido.")
    return url


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
    cuidados_filter = request.args.get("cuidados_especiais", "").strip().lower()
    ativos_filter = request.args.get("ativos", "").strip().lower()

    query = Animal.query.filter_by(is_deleted=False)

    if search_query:
        # Os curingas do LIKE digitados na busca são tratados como texto comum
        termo = search_query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        padrao = f"%{termo}%"
        query = query.filter(
            db.or_(
                Animal.nome.ilike(padrao, escape="\\"),
                Animal.codigo_identificador.ilike(padrao, escape="\\"),
                Animal.raca.ilike(padrao, escape="\\")
            )
        )

    if status_filter:
        query = query.filter_by(status_operacional=status_filter)

    if porte_filter:
        query = query.filter_by(porte=porte_filter)

    if sexo_filter:
        query = query.filter_by(sexo=sexo_filter)

    if castrado_filter in _SIM:
        query = query.filter_by(is_castrado=True)
    elif castrado_filter in _NAO:
        query = query.filter_by(is_castrado=False)

    if idoso_filter in _SIM:
        query = query.filter_by(is_idoso=True)
    elif idoso_filter in _NAO:
        query = query.filter_by(is_idoso=False)

    # RF08/RF11: animais com (ou sem) cuidados especiais anotados
    tem_cuidados = db.and_(Animal.cuidados_especiais.isnot(None), db.func.trim(Animal.cuidados_especiais) != "")
    if cuidados_filter in _SIM:
        query = query.filter(tem_cuidados)
    elif cuidados_filter in _NAO:
        query = query.filter(db.not_(tem_cuidados))

    # ativos=sim: só animais sob os cuidados da ONG; ativos=nao: só adotados e óbitos (histórico)
    status_finais = [Animal.STATUS_ADOTADO, Animal.STATUS_OBITO]
    if ativos_filter in _SIM:
        query = query.filter(Animal.status_operacional.notin_(status_finais))
    elif ativos_filter in _NAO:
        query = query.filter(Animal.status_operacional.in_(status_finais))

    query = query.order_by(Animal.created_at.desc(), Animal.id.desc())
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
            "idoso": idoso_filter,
            "cuidados_especiais": cuidados_filter,
            "ativos": ativos_filter
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
    data = get_payload()

    nome = model_text(data, Animal, "nome", default="")
    sexo = clean_text(data, "sexo", default="")
    porte = clean_text(data, "porte", default="Médio")

    if not nome or not sexo:
        raise ApiError("Dados incompletos", 400, "Nome e sexo são campos obrigatórios para o cadastro.")
    require_choice(sexo, "sexo", Animal.SEXOS)
    require_choice(porte, "porte", Animal.PORTES)
    peso_val = parse_float(data.get("peso_kg"), "peso_kg", minimo=0, positivo=True)

    campos = {campo: model_text(data, Animal, campo) for campo in CAMPOS_TEXTO_CURTO}
    campos.update({campo: clean_text(data, campo) for campo in CAMPOS_TEXTO_LONGO})
    campos.update({campo: parse_bool(data.get(campo)) for campo in CAMPOS_BOOLEANOS})
    raca = model_text(data, Animal, "raca", default=RACA_PADRAO)

    foto_url = _foto_url_informada(data)
    if "foto" in request.files:
        foto_url = compress_and_save_photo(request.files["foto"]) or foto_url

    # Criação da entidade garantindo RN01 (status inicial 'em acolhimento' e data de hoje)
    animal = Animal(
        nome=nome,
        sexo=sexo,
        raca=raca,
        porte=porte,
        peso_kg=peso_val,
        foto_url=foto_url,
        data_entrada=tempo.hoje(), # RN01
        status_operacional=Animal.STATUS_ACOLHIMENTO, # RN01
        **campos
    )

    db.session.add(animal)
    db.session.flush()
    log_audit_event(
        acao="ANIMAL_CADASTRADO",
        entidade="Animal",
        entidade_id=animal.id,
        detalhes=f"Cadastro do animal {animal.nome} (Status inicial: {animal.status_operacional})",
        commit=False,
    )
    db.session.commit()

    return jsonify({
        "sucesso": True,
        "mensagem": "Cão cadastrado com sucesso com estado inicial 'em acolhimento' (RN01).",
        "animal": animal.to_dict()
    }), 201


@animals_bp.route("/<int:animal_id>", methods=["GET"])
def get_animal(animal_id):
    """Consulta ficha completa do cão organizada por módulos (RF12)."""
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()
    hoje = tempo.hoje()

    # Busca registros relacionados
    vacinas = animal.vaccinations.order_by(Vaccination.data_aplicacao.desc()).all()
    prescricoes = animal.prescriptions.order_by(Prescription.data_inicio.desc()).all()
    prontuarios = animal.medical_records.order_by(MedicalRecord.data_evento.desc()).all()
    adocao_info = animal.adoption.to_dict() if animal.adoption else None

    return jsonify({
        "animal": animal.to_dict(),
        "vacinas": vaccine_dicts(vacinas, hoje),
        "prescricoes": [prescription_dict(p, hoje) for p in prescricoes],
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

    data = get_payload()
    novos = {}

    if "nome" in data:
        novos["nome"] = model_text(data, Animal, "nome")
        if not novos["nome"]:
            raise ApiError("Dados incompletos", 400, "O nome do animal não pode ficar vazio.")
    if "sexo" in data:
        novos["sexo"] = require_choice(data["sexo"], "sexo", Animal.SEXOS)
    if "porte" in data:
        novos["porte"] = require_choice(data["porte"], "porte", Animal.PORTES)
    if "raca" in data:
        novos["raca"] = model_text(data, Animal, "raca", default=RACA_PADRAO)
    if "peso_kg" in data:
        novos["peso_kg"] = parse_float(data["peso_kg"], "peso_kg", minimo=0, positivo=True)

    for campo in CAMPOS_TEXTO_CURTO:
        if campo in data:
            novos[campo] = model_text(data, Animal, campo)
    for campo in CAMPOS_TEXTO_LONGO:
        if campo in data:
            novos[campo] = clean_text(data, campo)
    for campo in CAMPOS_BOOLEANOS:
        if campo in data:
            novos[campo] = parse_bool(data[campo])

    # RF07/RF09: a data de entrada nasce como a data do cadastro (RN01), mas pode ser corrigida
    # depois, por exemplo quando o resgate foi registrado no dia seguinte. Nunca no futuro.
    if "data_entrada" in data:
        data_entrada = parse_date(data.get("data_entrada"), "data_entrada")
        if not data_entrada:
            raise ApiError("Data inválida", 400, "A data de entrada não pode ficar vazia.")
        if data_entrada > tempo.hoje():
            raise ApiError("Data inválida", 400, "A data de entrada não pode ser uma data futura.")
        novos["data_entrada"] = data_entrada

    if "foto" in request.files:
        nova_foto = compress_and_save_photo(request.files["foto"])
        if nova_foto:
            novos["foto_url"] = nova_foto
    elif "foto_url" in data:
        novos["foto_url"] = _foto_url_informada(data)

    alterados = [campo for campo, valor in novos.items() if getattr(animal, campo) != valor]
    for campo in alterados:
        setattr(animal, campo, novos[campo])

    if alterados:
        log_audit_event(
            acao="ANIMAL_ATUALIZADO",
            entidade="Animal",
            entidade_id=animal.id,
            detalhes=f"Atualização dos dados cadastrais do animal {animal.nome} (campos: {', '.join(alterados)})",
            commit=False,
        )
        db.session.commit()

    return jsonify({
        "sucesso": True,
        "mensagem": f"Dados do animal {animal.nome} atualizados com sucesso.",
        "animal": animal.to_dict()
    }), 200


@animals_bp.route("/<int:animal_id>/status", methods=["PATCH"])
def update_animal_status(animal_id):
    """Transição da máquina de estados operacionais do animal (RN02)."""
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()
    data = get_payload()
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
    log_audit_event(
        acao="STATUS_ANIMAL_ALTERADO",
        entidade="Animal",
        entidade_id=animal.id,
        detalhes=f"Transição de status operacional do animal {animal.nome}: '{status_anterior}' -> '{novo_status}'",
        commit=False,
    )
    db.session.commit()

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
    log_audit_event(
        acao="ANIMAL_EXCLUIDO_LOGICO",
        entidade="Animal",
        entidade_id=animal.id,
        detalhes=f"Exclusão lógica do animal {animal.nome} (RN03)",
        commit=False,
    )
    db.session.commit()

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
    log_audit_event(
        acao="FOTO_ANIMAL_ATUALIZADA",
        entidade="Animal",
        entidade_id=animal.id,
        detalhes=f"Upload de nova foto com compressão < 300KB para o animal {animal.nome}",
        commit=False,
    )
    db.session.commit()

    return jsonify({
        "sucesso": True,
        "mensagem": "Foto recebida e comprimida com sucesso (< 300 KB).",
        "foto_url": animal.foto_url
    }), 200
