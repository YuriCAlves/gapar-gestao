from flask import Blueprint, jsonify
from flask_login import current_user
from app.extensions import db
from app.models.animal import Animal
from app.models.adoption import Adoption
from app.utils import tempo
from app.services.audit import log_audit_event
from app.services.lista_sigilosa import procurar as procurar_na_lista_sigilosa
from app.utils.validation import (
    ApiError, clean_text, get_payload, model_text, parse_bool, parse_cpf, parse_date, parse_telefone,
)

adoptions_bp = Blueprint("adoptions", __name__, url_prefix="/api/adocoes")


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
    # D2: telefone com DDD e CPF com dígito verificador; gravados só com dígitos
    adotante_telefone = parse_telefone(data.get("adotante_telefone"), "adotante_telefone") or ""
    adotante_cpf = parse_cpf(data.get("adotante_cpf"), "adotante_cpf") or ""
    adotante_endereco = clean_text(data, "adotante_endereco", max_len=255, default="")
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
    motivo_bloqueio, registro = procurar_na_lista_sigilosa(adotante_nome, adotante_cpf, adotante_telefone)
    if motivo_bloqueio:
        # Sem o nome do interessado: a auditoria é imutável (RN16) e não guarda dado pessoal.
        # A Administradora chega à pessoa pelo número do registro na lista sigilosa.
        log_audit_event(
            acao="TENTATIVA_ADOCAO_BLOQUEADA_NAO_APTO",
            entidade="Adoption",
            entidade_id=animal.id,
            detalhes=(f"Tentativa de adoção do cão {animal.nome} (#{animal.id}) bloqueada. "
                      f"Motivo: {motivo_bloqueio}; registro sigiloso #{registro.id} (RN15)")
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
        detalhes=f"Adoção #{adocao.id} formalizada: cão {animal.nome} (#{animal.id}). Status alterado para 'adotado' e histórico congelado (RN05).",
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
