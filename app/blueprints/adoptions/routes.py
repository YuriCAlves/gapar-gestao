import re
from datetime import date
from flask import jsonify, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.animal import Animal
from app.models.adoption import Adoption
from app.models.blacklist import NonEligiblePerson
from app.utils.audit import log_audit_event
from . import adoptions_bp


def _limpar_numeros(valor):
    if not valor:
        return ""
    return re.sub(r"\D", "", str(valor))


@adoptions_bp.route("/registrar/<int:animal_id>", methods=["POST"])
@adoptions_bp.route("/<int:animal_id>", methods=["POST"])
def register_adoption(animal_id):
    """Registro formal obrigatório de adoção e congelamento do histórico (RF20, RF21, RN04, RN05, RN15).
    Exige obrigatoriamente nome, telefone e data do adotante (RN04).
    Valida contra a lista sigilosa de pessoas não aptas (RN15).
    """
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()

    if animal.status_operacional == Animal.STATUS_ADOTADO:
        return jsonify({
            "erro": "Animal já adotado",
            "mensagem": "Este animal já possui registro de adoção formalizado."
        }), 400

    data = request.get_json(silent=True) or request.form.to_dict() or {}

    adotante_nome = data.get("adotante_nome", "").strip()
    adotante_telefone = data.get("adotante_telefone", "").strip()
    adotante_cpf = data.get("adotante_cpf", "").strip()
    adotante_endereco = data.get("adotante_endereco", "").strip()
    observacoes = data.get("observacoes", "").strip()
    termo_fisico = bool(data.get("termo_fisico_assinado") or data.get("termo_assinado"))

    # Validação RN04: Exigência obrigatória de nome, telefone e data
    if not adotante_nome or not adotante_telefone:
        return jsonify({
            "erro": "Campos obrigatórios ausentes",
            "mensagem": "Nome e telefone/contato do adotante são estritamente obrigatórios (RN04)."
        }), 400

    data_adocao = date.today()
    if data.get("data_adocao"):
        try:
            data_adocao = date.fromisoformat(data["data_adocao"])
        except ValueError:
            pass

    # Validação RN15: Checagem contra a Lista Sigilosa de Não Aptos
    cpf_limpo = _limpar_numeros(adotante_cpf)
    tel_limpo = _limpar_numeros(adotante_telefone)

    bloqueado = False
    motivo_bloqueio = ""

    # Busca registros na lista de não aptos
    registros_bloqueados = NonEligiblePerson.query.all()
    for item in registros_bloqueados:
        if cpf_limpo and item.cpf and _limpar_numeros(item.cpf) == cpf_limpo:
            bloqueado = True
            motivo_bloqueio = "CPF constante na lista de não aptos"
            break
        if tel_limpo and item.telefone and _limpar_numeros(item.telefone) == tel_limpo:
            bloqueado = True
            motivo_bloqueio = "Telefone constante na lista de não aptos"
            break
        if adotante_nome.lower() == item.nome.strip().lower():
            bloqueado = True
            motivo_bloqueio = "Nome idêntico constante na lista de não aptos"
            break

    if bloqueado:
        log_audit_event(
            acao="TENTATIVA_ADOCAO_BLOQUEADA_NAO_APTO",
            entidade="Adoption",
            entidade_id=animal.id,
            detalhes=f"Tentativa de adoção do cão {animal.nome} bloqueada para '{adotante_nome}'. Motivo: {motivo_bloqueio} (RN15)"
        )
        return jsonify({
            "erro": "Adoção não autorizada",
            "mensagem": "Não é possível prosseguir com o registro de adoção para este interessado. Por favor, verifique com a Administradora da ONG (RN15)."
        }), 422

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

    # Transição do status e congelamento imediato do animal (RN05)
    animal.status_operacional = Animal.STATUS_ADOTADO
    db.session.commit()

    log_audit_event(
        acao="ADOCAO_FORMALIZADA",
        entidade="Adoption",
        entidade_id=adocao.id,
        detalhes=f"Adoção formalizada: Cão {animal.nome} adotado por {adotante_nome}. Status alterado para 'adotado' e histórico congelado (RN05)."
    )

    return jsonify({
        "sucesso": True,
        "mensagem": "Adoção registrada com sucesso. Status alterado para 'adotado' e histórico do cão congelado para edições (RN05).",
        "animal_id": animal.id,
        "adocao": adocao.to_dict(),
        "animal": animal.to_dict()
    }), 201


@adoptions_bp.route("/historico/<int:animal_id>", methods=["GET"])
@adoptions_bp.route("/<int:animal_id>", methods=["GET"])
def get_adoption_record(animal_id):
    """Consulta os dados formais da adoção preservados indefinidamente (RN06)."""
    animal = Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()
    
    if not animal.adoption:
        return jsonify({
            "animal_id": animal.id,
            "status": animal.status_operacional,
            "congelado": animal.is_frozen,
            "adocao": None
        }), 200

    return jsonify({
        "animal_id": animal.id,
        "status": animal.status_operacional,
        "congelado": animal.is_frozen,
        "adocao": animal.adoption.to_dict()
    }), 200
