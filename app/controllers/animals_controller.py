from flask_login import current_user
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models.animal import Animal
from app.models.health import Vaccination, Prescription, MedicalRecord
from app.models.isolation import carregar_isolamentos_abertos
from app.utils import tempo
from app.services.images import compress_and_save_photo
from app.services.audit import log_audit_event
from app.utils.decorators import admin_required
from app.utils.publico import flag_ativa, require_feature
from app.utils.slug import gerar_slug_publico
from app.services.saude import prescription_dict, vaccine_dicts
from app.utils.validation import (
    ApiError, clean_text, get_payload, model_text, parse_bool, parse_date, parse_float, require_choice,
)

animals_bp = Blueprint("animals", __name__, url_prefix="/api/animais")

RACA_PADRAO = "Sem Raça Definida (SRD)"

# Textos opcionais do cadastro com tamanho limitado pela coluna
CAMPOS_TEXTO_CURTO = ["idade_estimada", "pelagem", "local_resgate", "localizacao_baia", "codigo_identificador"]
# Textos opcionais sem limite de tamanho
CAMPOS_TEXTO_LONGO = ["motivo_resgate", "cuidados_especiais"]
CAMPOS_BOOLEANOS = ["is_castrado", "is_microchipado", "is_idoso"]

_SIM = ("true", "1", "sim")
_NAO = ("false", "0", "nao", "não")


def _numero_microchip(data):
    """CP-04 (REQ-39, RN21): `numero_microchip` do corpo, já validado.

    Devolve `(presente, numero)`: `presente=False` quando o campo não veio (ou veio vazio com a
    flag desligada, que é o que o formulário manda sempre). Vazio/null com a flag ligada limpa o
    número. Número preenchido com a flag "microchip" desligada -> 400 (nunca descartado em
    silêncio). Formato diferente de 15 dígitos -> 400.
    """
    if "numero_microchip" not in data:
        return False, None
    valor = data.get("numero_microchip")
    if valor is not None and not isinstance(valor, str):
        raise ApiError("Microchip inválido", 400, "O número do microchip deve ter exatamente 15 dígitos.")
    numero = (valor or "").strip() or None
    if not flag_ativa("microchip"):
        if numero is None:
            return False, None
        raise ApiError("Microchip desativado", 400,
                       "O módulo de microchip está desativado; o número não pode ser gravado.")
    if numero is not None and not Animal.microchip_valido(numero):
        raise ApiError("Microchip inválido", 400, "O número do microchip deve ter exatamente 15 dígitos.")
    return True, numero


def _conflito_microchip(dono):
    """409 `ConflitoMicrochip`: aponta a ficha que já usa o número (só para usuária logada).

    O UNIQUE vale também para fichas excluídas (D1). Nesse caso a ficha não abre (404), então a
    mensagem diz isso e `animal_excluido=True` deixa a tela esconder o link.
    """
    if dono.is_deleted:
        return ApiError("Microchip já cadastrado", 409,
                        f"Este microchip pertence à ficha excluída de {dono.nome} (#{dono.id}). "
                        "Fale com a administração para liberar o número.",
                        animal_id=dono.id, animal_nome=dono.nome, animal_excluido=True)
    return ApiError("Microchip já cadastrado", 409,
                    f"Este microchip já está cadastrado na ficha de {dono.nome}.",
                    animal_id=dono.id, animal_nome=dono.nome, animal_excluido=False)


def _checar_microchip_livre(numero, animal_id=None):
    if numero is None:
        return
    dono = Animal.buscar_por_microchip(numero, incluir_excluidos=True)
    if dono is not None and dono.id != animal_id:
        raise _conflito_microchip(dono)


def _commit_com_microchip(numero, animal_id=None):
    """Commit que traduz a corrida no UNIQUE do microchip em 409 `ConflitoMicrochip`."""
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        _checar_microchip_livre(numero, animal_id)
        raise


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
        # CP-05 (REQ-43): `isolamento_aberto` da página inteira numa consulta só (sem N+1)
        "animais": [animal.to_dict() for animal in carregar_isolamentos_abertos(pagination.items)]
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
    _, numero_microchip = _numero_microchip(data)
    _checar_microchip_livre(numero_microchip)

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
    if numero_microchip:
        animal.numero_microchip = numero_microchip  # liga `is_microchipado` (RN21)

    db.session.add(animal)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        _checar_microchip_livre(numero_microchip)  # corrida no UNIQUE do microchip -> 409
        raise
    animal_id = animal.id
    log_audit_event(
        acao="ANIMAL_CADASTRADO",
        entidade="Animal",
        entidade_id=animal.id,
        detalhes=f"Cadastro do animal {animal.nome} (Status inicial: {animal.status_operacional})",
        commit=False,
    )
    _commit_com_microchip(numero_microchip, animal_id)

    return jsonify({
        "sucesso": True,
        "mensagem": "Cão cadastrado com sucesso com estado inicial 'em acolhimento' (RN01).",
        "animal": animal.to_dict()
    }), 201


@animals_bp.route("/microchip/<string:numero>", methods=["GET"])
@require_feature("microchip")
def buscar_por_microchip(numero):
    """Busca rápida pelo leitor USB HID (CP-04, REQ-40): `{animal: ResumoMicrochip}` ou 404.

    Número fora do formato devolve 404 sem consultar o banco (`Animal.buscar_por_microchip`).
    """
    animal = Animal.buscar_por_microchip(numero)
    if animal is None:
        raise ApiError("Recurso não encontrado", 404, "Nenhum animal com este microchip.")
    return jsonify({"animal": animal.to_resumo_microchip()}), 200


@animals_bp.route("/<int:animal_id>", methods=["GET"])
def get_animal(animal_id):
    """Consulta ficha completa do cão organizada por módulos (RF12)."""
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()
    hoje = tempo.hoje()

    # Busca registros relacionados
    vacinas = animal.vaccinations.order_by(Vaccination.data_aplicacao.desc()).all()
    prescricoes = animal.prescriptions.order_by(Prescription.data_inicio.desc()).all()
    prontuarios = animal.medical_records.order_by(MedicalRecord.data_evento.desc()).all()
    adocao_info = animal.adoption.to_dict(completo=current_user.is_admin) if animal.adoption else None

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

    microchip_presente, numero_microchip = _numero_microchip(data)
    if microchip_presente:
        _checar_microchip_livre(numero_microchip, animal.id)
        novos["numero_microchip"] = numero_microchip

    if "foto" in request.files:
        nova_foto = compress_and_save_photo(request.files["foto"])
        if nova_foto:
            novos["foto_url"] = nova_foto
    elif "foto_url" in data:
        novos["foto_url"] = _foto_url_informada(data)

    alterados = [campo for campo, valor in novos.items() if getattr(animal, campo) != valor]
    # O número do microchip por último: o validador liga `is_microchipado` (RN21) e não pode ser
    # desfeito por um `is_microchipado=false` do mesmo corpo.
    alterados.sort(key=lambda campo: campo == "numero_microchip")
    for campo in alterados:
        setattr(animal, campo, novos[campo])

    # RN21: com número de microchip gravado, o animal é microchipado. Desmarcar exige apagar o número.
    if animal.numero_microchip and not animal.is_microchipado:
        raise ApiError("Microchip inconsistente", 400,
                       "Este animal tem número de microchip. Para marcá-lo como sem microchip, apague o número antes.")

    if alterados:
        log_audit_event(
            acao="ANIMAL_ATUALIZADO",
            entidade="Animal",
            entidade_id=animal.id,
            detalhes=f"Atualização dos dados cadastrais do animal {animal.nome} (campos: {', '.join(alterados)})",
            commit=False,
        )
        _commit_com_microchip(novos.get("numero_microchip"), animal.id)

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


# Vitrine pública (CP-02, REQ-24, RN17) -------------------------------------------------------

DESCRICAO_PUBLICA_MAX = 600
TENTATIVAS_SLUG = 3


def _booleano_estrito(data, campo):
    """Booleano JSON de verdade (`true`/`false`); qualquer outra coisa gera 400."""
    valor = data.get(campo)
    if not isinstance(valor, bool):
        raise ApiError("Valor inválido", 400, f"O campo '{campo}' deve ser verdadeiro ou falso.")
    return valor


def _gravar_slug_publico(animal):
    """Primeira publicação: gera o slug e tenta de novo se colidir com o índice único.

    Cada tentativa roda num SAVEPOINT, para que a colisão não desfaça a transação inteira.
    Roda antes de qualquer outra alteração no animal: o rollback do SAVEPOINT recarrega o objeto.
    """
    for _ in range(TENTATIVAS_SLUG):
        try:
            with db.session.begin_nested():
                animal.slug_publico = gerar_slug_publico(animal.nome)
                db.session.flush()
            return
        except IntegrityError:
            continue
    raise ApiError("Conflito de dados", 409,
                   "Não foi possível gerar o link público agora. Tente publicar novamente.")


@animals_bp.route("/<int:animal_id>/vitrine", methods=["PATCH"])
@admin_required
def update_vitrine(animal_id):
    """Publica ou retira o animal da vitrine pública (REQ-24). Exclusiva da Administradora.

    Corpo: {publicar: bool, descricao_publica?: str|null (até 600), pausar_candidaturas?: bool}.
    Só animal 'disponível' pode ser publicado (RN17). O slug nasce na primeira publicação e é
    mantido ao despublicar, para que republicar devolva o mesmo link.
    """
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()
    data = get_payload()

    if "publicar" not in data:
        raise ApiError("Campo obrigatório", 400, "O campo 'publicar' é obrigatório.")
    novos = {"is_publicado": _booleano_estrito(data, "publicar")}
    if "descricao_publica" in data:
        novos["descricao_publica"] = clean_text(data, "descricao_publica", max_len=DESCRICAO_PUBLICA_MAX)
    if "pausar_candidaturas" in data:
        novos["pausar_candidaturas"] = _booleano_estrito(data, "pausar_candidaturas")

    if novos["is_publicado"] and animal.status_operacional != Animal.STATUS_DISPONIVEL:
        raise ApiError("Animal indisponível para a vitrine", 422,
                       f"Só é possível publicar na vitrine um animal com status 'disponível'. "
                       f"Este animal está com status '{animal.status_operacional}' (RN17).")

    alterados = [campo for campo, valor in novos.items() if getattr(animal, campo) != valor]
    if alterados and animal.is_frozen:
        raise ApiError("Ficha congelada", 422,
                       f"O animal encontra-se com status '{animal.status_operacional}'; a ficha não pode ser alterada (RN05).")

    if novos["is_publicado"] and not animal.slug_publico:
        _gravar_slug_publico(animal)
        alterados.append("slug_publico")

    for campo in alterados:
        if campo in novos:
            setattr(animal, campo, novos[campo])

    if alterados:
        # Auditoria só com o id e os nomes dos campos: o texto da descrição nunca entra aqui.
        resumo = ", ".join(
            f"{campo}={'sim' if novos[campo] else 'não'}" if isinstance(novos.get(campo), bool) else campo
            for campo in alterados
        )
        log_audit_event(
            acao="VITRINE_ATUALIZADA",
            entidade="Animal",
            entidade_id=animal.id,
            detalhes=f"Vitrine do animal #{animal.id} (campos: {resumo})",
            commit=False,
        )
        db.session.commit()

    return jsonify({
        "sucesso": True,
        "mensagem": "Vitrine atualizada." if alterados else "Nada mudou na vitrine.",
        "animal": animal.to_dict(),
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
