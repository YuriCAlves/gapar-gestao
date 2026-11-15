from flask import jsonify
from flask_login import current_user
from app.extensions import db
from app.models.animal import Animal
from app.models.adoption import Adoption
from app.models.blacklist import NonEligiblePerson
from app.utils import tempo
from app.utils.audit import log_audit_event
from app.utils.validation import ApiError, clean_text, get_payload, model_text, only_digits, parse_bool, parse_date
from . import adoptions_bp


def _motivo_de_bloqueio(nome, cpf, telefone):
    """RN15: confere o interessado contra a lista sigilosa. Devolve o motivo interno ou None.

    O motivo vai apenas para a trilha de auditoria (visível só à Administradora), nunca para a resposta.
    """
    cpf_limpo = only_digits(cpf)
    tel_limpo = only_digits(telefone)
    nome_normalizado = " ".join(nome.lower().split())

    registros = db.session.query(NonEligiblePerson.nome, NonEligiblePerson.cpf, NonEligiblePerson.telefone).all()
    for item_nome, item_cpf, item_telefone in registros:
        if cpf_limpo and item_cpf and only_digits(item_cpf) == cpf_limpo:
            return "CPF constante na lista de não aptos"
        if tel_limpo and item_telefone and only_digits(item_telefone) == tel_limpo:
            return "Telefone constante na lista de não aptos"
        if nome_normalizado == " ".join((item_nome or "").lower().split()):
            return "Nome idêntico constante na lista de não aptos"
    return None


@adoptions_bp.route("/registrar/<int:animal_id>", methods=["POST"])
@adoptions_bp.route("/<int:animal_id>", methods=["POST"])
def register_adoption(animal_id):
    """Registro formal obrigatório de adoção e congelamento do histórico (RF20, RF21, RN04, RN05, RN15).
    Exige obrigatoriamente nome, telefone e data do adotante (RN04).
    Valida contra a lista sigilosa de pessoas não aptas (RN15).
    """
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()

    if animal.status_operacional == Animal.STATUS_ADOTADO:
        raise ApiError("Animal já adotado", 400, "Este animal já possui registro de adoção formalizado.")

    if animal.status_operacional not in Animal.STATUS_ADOTAVEIS:
        raise ApiError("Animal não disponível para adoção", 422,
                       f"Só é possível adotar animais 'disponível' ou em 'lar temporário' (status atual: '{animal.status_operacional}').")

    data = get_payload()

    adotante_nome = model_text(data, Adoption, "adotante_nome", default="")
    adotante_telefone = model_text(data, Adoption, "adotante_telefone", default="")
    adotante_cpf = model_text(data, Adoption, "adotante_cpf", default="")
    adotante_endereco = model_text(data, Adoption, "adotante_endereco", default="")
    observacoes = clean_text(data, "observacoes", default="")
    termo_fisico = parse_bool(data.get("termo_fisico_assinado")) or parse_bool(data.get("termo_assinado"))

    # Validação RN04: Exigência obrigatória de nome, telefone e data
    if not adotante_nome or not adotante_telefone:
        raise ApiError("Campos obrigatórios ausentes", 400,
                       "Nome e telefone/contato do adotante são estritamente obrigatórios (RN04).")

    hoje = tempo.hoje()
    data_adocao = parse_date(data.get("data_adocao"), "data_adocao", default=hoje)
    if data_adocao > hoje:
        raise ApiError("Data inválida", 400, "A data da adoção não pode ser uma data futura.")

    # Validação RN15: Checagem contra a Lista Sigilosa de Não Aptos
    motivo_bloqueio = _motivo_de_bloqueio(adotante_nome, adotante_cpf, adotante_telefone)
    if motivo_bloqueio:
        log_audit_event(
            acao="TENTATIVA_ADOCAO_BLOQUEADA_NAO_APTO",
            entidade="Adoption",
            entidade_id=animal.id,
            detalhes=f"Tentativa de adoção do cão {animal.nome} bloqueada para '{adotante_nome}'. Motivo: {motivo_bloqueio} (RN15)"
        )
        raise ApiError("Adoção não autorizada", 422,
                       "Não é possível prosseguir com o registro de adoção para este interessado. Por favor, verifique com a Administradora da ONG (RN15).")

    user_id = current_user.id if current_user.is_authenticated else None

    # Cria registro formal de adoção
    adocao = Adoption(
        animal_id=animal.id,
        adotante_nome=adotante_nome,
        adotante_telefone=adotante_telefone,
        adotante_cpf=adotante_cpf,
        adotante_endereco=adotante_endereco,
        data_adocao=data_adocao,
        termo_assinado=True,
        termo_fisico_assinado=termo_fisico,
        observacoes=observacoes,
        cadastrado_por_user_id=user_id
    )
    db.session.add(adocao)

    # Transição do status e congelamento imediato do animal (RN05), na mesma transação da
    # adoção e do registro de auditoria: ou tudo é gravado, ou nada.
    animal.status_operacional = Animal.STATUS_ADOTADO
    db.session.flush()
    log_audit_event(
        acao="ADOCAO_FORMALIZADA",
        entidade="Adoption",
        entidade_id=adocao.id,
        detalhes=f"Adoção formalizada: Cão {animal.nome} adotado por {adotante_nome}. Status alterado para 'adotado' e histórico congelado (RN05).",
        commit=False,
    )
    db.session.commit()

    return jsonify({
        "sucesso": True,
        "mensagem": "Adoção registrada com sucesso. Status alterado para 'adotado' e histórico do cão congelado para edições (RN05).",
        "animal_id": animal.id,
        "adocao": adocao.to_dict(completo=current_user.is_admin),
        "animal": animal.to_dict()
    }), 201


@adoptions_bp.route("/historico/<int:animal_id>", methods=["GET"])
@adoptions_bp.route("/<int:animal_id>", methods=["GET"])
def get_adoption_record(animal_id):
    """Consulta os dados formais da adoção preservados indefinidamente (RN06)."""
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()

    return jsonify({
        "animal_id": animal.id,
        "status": animal.status_operacional,
        "congelado": animal.is_frozen,
        "adocao": animal.adoption.to_dict(completo=current_user.is_admin) if animal.adoption else None
    }), 200
