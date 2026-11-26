from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user
from app.extensions import db
from app.models.whitelist import Whitelist
from app.models.blacklist import NonEligiblePerson
from app.models.audit import AuditLog
from app.models.base import PERFIS
from app.utils import tempo
from app.utils.decorators import admin_required
from app.services import lista_sigilosa
from app.services.audit import log_audit_event
from app.utils.validation import (
    ApiError, clean_text, get_payload, model_text, parse_bool, parse_cpf, parse_date, parse_email, parse_telefone,
    require_choice,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

AUDITORIA_POR_PAGINA_PADRAO = 100
AUDITORIA_POR_PAGINA_MAXIMO = 200


def _initial_admin_email():
    return (current_app.config.get("INITIAL_ADMIN_EMAIL") or "").strip().lower()


def _proteger_contra_trancamento(entry, ficara_ativo, novo_perfil):
    """Impede que a administração fique sem acesso (RN13, RN14).

    Bloqueia: desativar ou rebaixar a própria entrada, mexer na administradora inicial e deixar
    o sistema sem nenhuma Administradora ativa.
    """
    perde_admin = entry.role == "Administradora" and entry.is_active and (
        not ficara_ativo or novo_perfil != "Administradora")
    if not perde_admin and (ficara_ativo or not entry.is_active):
        return
    email = entry.email.strip().lower()
    if email == _initial_admin_email() and (not ficara_ativo or novo_perfil != "Administradora"):
        raise ApiError("Operação não permitida", 422,
                       "A administradora inicial do sistema não pode ser desativada nem perder o perfil (RN13).")
    if email == (current_user.email or "").strip().lower() and (not ficara_ativo or novo_perfil != "Administradora"):
        raise ApiError("Operação não permitida", 422,
                       "Você não pode desativar nem rebaixar o seu próprio acesso. Peça a outra Administradora.")
    if perde_admin:
        outras = Whitelist.query.filter(Whitelist.id != entry.id, Whitelist.role == "Administradora",
                                        Whitelist.is_active.is_(True)).count()
        if outras == 0:
            raise ApiError("Operação não permitida", 422,
                           "É preciso manter ao menos uma Administradora ativa no sistema.")


@admin_bp.route("/whitelist", methods=["GET", "POST"])
@admin_required
def manage_whitelist():
    """Gestão de e-mails autorizados (RF04, RN12, RN14). Exclusivo da Administradora."""
    if request.method == "POST":
        data = get_payload()
        email = parse_email(data.get("email"))
        role = clean_text(data, "role", default="Voluntaria")

        if Whitelist.query.filter(db.func.lower(Whitelist.email) == email).first():
            return jsonify({
                "erro": "E-mail já cadastrado",
                "mensagem": "Este e-mail já consta na Whitelist."
            }), 400

        entry = Whitelist(email=email, role=role if role in PERFIS else "Voluntaria", is_active=True)
        db.session.add(entry)
        db.session.flush()
        log_audit_event(
            acao="WHITELIST_USUARIA_ADICIONADA",
            entidade="Whitelist",
            entidade_id=entry.id,
            detalhes=f"Inclusão do e-mail {entry.email} na Whitelist (Perfil: {entry.role})",
            commit=False,
        )
        db.session.commit()

        return jsonify({
            "sucesso": True,
            "mensagem": f"E-mail {email} adicionado à Whitelist com sucesso.",
            "usuario": entry.to_dict()
        }), 201

    query = Whitelist.query
    ativo = request.args.get("ativo", "").strip()
    if ativo:
        query = query.filter(Whitelist.is_active.is_(parse_bool(ativo)))
    busca = request.args.get("q", "").strip().lower()
    if busca:
        query = query.filter(db.func.lower(Whitelist.email).contains(busca, autoescape=True))
    entradas = query.order_by(Whitelist.created_at.desc(), Whitelist.id.desc()).all()
    admin_inicial = _initial_admin_email()
    proprio = (current_user.email or "").strip().lower()
    return jsonify({
        "sucesso": True,
        "total": len(entradas),
        "whitelist": [dict(e.to_dict(),
                           is_admin_inicial=e.email.lower() == admin_inicial,
                           is_voce=e.email.lower() == proprio) for e in entradas]
    }), 200


def _alterar_entrada(entry, ficara_ativo, novo_perfil):
    _proteger_contra_trancamento(entry, ficara_ativo, novo_perfil)
    mudancas = []
    if entry.is_active != ficara_ativo:
        mudancas.append("ativo" if ficara_ativo else "inativo")
    if entry.role != novo_perfil:
        mudancas.append(f"perfil {entry.role} -> {novo_perfil}")
    if not mudancas:
        return
    acao = "WHITELIST_PERFIL_ALTERADO"
    if entry.is_active != ficara_ativo:
        acao = "USUARIA_ATIVADA" if ficara_ativo else "USUARIA_DESATIVADA_REVOGADA"
    entry.is_active = ficara_ativo
    entry.role = novo_perfil
    log_audit_event(
        acao=acao,
        entidade="Whitelist",
        entidade_id=entry.id,
        detalhes=f"Whitelist de {entry.email}: {', '.join(mudancas)} (RN14)",
        commit=False,
    )
    db.session.commit()


@admin_bp.route("/whitelist/<int:entry_id>/status", methods=["PATCH", "POST"])
@admin_required
def alterar_status_whitelist(entry_id):
    """Ativação ou desativação na Whitelist (RN14: efeito imediato na próxima requisição)."""
    entry = db.get_or_404(Whitelist, entry_id)
    data = get_payload()
    is_active = parse_bool(data["is_active"]) if "is_active" in data else not entry.is_active

    _alterar_entrada(entry, is_active, entry.role)

    return jsonify({
        "sucesso": True,
        "mensagem": f"Status de {entry.email} alterado com sucesso.",
        "usuario": entry.to_dict()
    }), 200


@admin_bp.route("/whitelist/<int:entry_id>", methods=["PATCH", "PUT"])
@admin_required
def alterar_whitelist(entry_id):
    """Alteração de perfil (`role`) e/ou situação (`is_active`) de uma entrada da Whitelist (RF04)."""
    entry = db.get_or_404(Whitelist, entry_id)
    data = get_payload()
    if "role" not in data and "is_active" not in data:
        raise ApiError("Nada a alterar", 400, "Envie 'role' e/ou 'is_active'.")
    novo_perfil = require_choice(data["role"], "role", PERFIS) if "role" in data else entry.role
    ficara_ativo = parse_bool(data["is_active"]) if "is_active" in data else entry.is_active

    _alterar_entrada(entry, ficara_ativo, novo_perfil)

    return jsonify({
        "sucesso": True,
        "mensagem": f"Cadastro de {entry.email} atualizado com sucesso.",
        "usuario": entry.to_dict()
    }), 200


def _dados_nao_apto(data, parcial=False):
    campos = {}
    if not parcial or "nome" in data:
        campos["nome"] = model_text(data, NonEligiblePerson, "nome", default="")
    if not parcial or "motivo_impedimento" in data:
        campos["motivo_impedimento"] = clean_text(data, "motivo_impedimento", default="")
    if any(v == "" for v in campos.values()):
        raise ApiError("Nome e motivo do impedimento são obrigatórios.", 400,
                       "Informe o nome da pessoa e o motivo do impedimento.")
    # D2: CPF e telefone só completos e válidos; gravados só com dígitos (e cifrados no modelo)
    if not parcial or "cpf" in data:
        campos["cpf"] = parse_cpf(data.get("cpf"), "cpf") or ""
    if not parcial or "telefone" in data:
        campos["telefone"] = parse_telefone(data.get("telefone"), "telefone") or ""
    return campos


@admin_bp.route("/nao-aptos", methods=["GET", "POST"])
@admin_required
def nao_aptos():
    """Lista sigilosa de pessoas não aptas a adotar (RF22, RN15). Exclusivo da Administradora."""
    if request.method == "POST":
        bloqueado = NonEligiblePerson(**_dados_nao_apto(get_payload()), cadastrado_por_user_id=current_user.id)
        db.session.add(bloqueado)
        db.session.flush()
        log_audit_event(
            acao="NAO_APTO_INCLUIDO",
            entidade="NonEligiblePerson",
            entidade_id=bloqueado.id,
            # Sem nome/CPF/telefone: a auditoria é imutável (RN16) e não pode guardar dado pessoal
            detalhes=f"Inclusão do registro #{bloqueado.id} na lista sigilosa de não aptos (RN15)",
            commit=False,
        )
        db.session.commit()

        return jsonify({
            "sucesso": True,
            "mensagem": "Registro incluído na lista sigilosa com sucesso (RN15).",
            "nao_apto": bloqueado.to_dict()
        }), 201

    # Dados pessoais não vão na URL (ficariam nos logs de acesso da hospedagem): a busca é por
    # POST /api/admin/nao-aptos/busca. Filtro na URL é recusado em vez de ignorado.
    if any(request.args.get(campo) for campo in ("q", "cpf", "telefone")):
        raise ApiError("Busca inválida", 400,
                       "A busca na lista sigilosa é feita por POST /api/admin/nao-aptos/busca, "
                       "com o filtro no corpo da requisição (dados pessoais não vão na URL).")
    lista = NonEligiblePerson.query.order_by(NonEligiblePerson.created_at.desc(), NonEligiblePerson.id.desc()).all()
    return _resposta_lista(lista)


def _resposta_lista(lista):
    return jsonify({
        "sucesso": True,
        "total": len(lista),
        "nao_aptos": [item.to_dict() for item in lista]
    }), 200


@admin_bp.route("/nao-aptos/busca", methods=["POST"])
@admin_required
def buscar_nao_aptos():
    """D2: busca na lista sigilosa. Corpo com UM filtro: `q` (nome, parcial), `cpf` ou `telefone` (exatos)."""
    data = get_payload()
    cpf = parse_cpf(data.get("cpf"), "cpf")
    telefone = parse_telefone(data.get("telefone"), "telefone")
    nome = clean_text(data, "q", max_len=150, default="")
    if sum(bool(filtro) for filtro in (cpf, telefone, nome)) != 1:
        raise ApiError("Busca inválida", 400, "Procure por nome, CPF ou telefone, um de cada vez.")
    if cpf or telefone:
        lista = lista_sigilosa.buscar_exato(cpf=cpf, telefone=telefone)
        lista.sort(key=lambda item: (item.created_at, item.id), reverse=True)
    else:
        lista = (NonEligiblePerson.query
                 .filter(db.func.lower(NonEligiblePerson.nome).contains(nome.lower(), autoescape=True))
                 .order_by(NonEligiblePerson.created_at.desc(), NonEligiblePerson.id.desc()).all())
    return _resposta_lista(lista)


@admin_bp.route("/nao-aptos/<int:item_id>", methods=["PATCH", "PUT"])
@admin_required
def alterar_nao_apto(item_id):
    """Correção de um registro da lista sigilosa (RF22, RN15, RN16)."""
    item = db.get_or_404(NonEligiblePerson, item_id)
    campos = _dados_nao_apto(get_payload(), parcial=True)
    alterados = [c for c, v in campos.items() if (getattr(item, c) or "") != v]
    for campo in alterados:
        setattr(item, campo, campos[campo])
    if alterados:
        log_audit_event(
            acao="NAO_APTO_ALTERADO",
            entidade="NonEligiblePerson",
            entidade_id=item.id,
            detalhes=f"Registro sigiloso #{item.id} alterado (campos: {', '.join(alterados)}) (RN15)",
            commit=False,
        )
        db.session.commit()
    return jsonify({"sucesso": True, "mensagem": "Registro atualizado com sucesso.", "nao_apto": item.to_dict()}), 200


@admin_bp.route("/auditoria", methods=["GET"])
@admin_required
def auditoria():
    """Consulta de logs imutáveis da trilha de auditoria (RF24, RN16). Exclusivo da Administradora.

    Parâmetros opcionais: page, per_page (máx. 200), acao, entidade, entidade_id, email,
    data_inicio e data_fim (AAAA-MM-DD, no fuso do abrigo, inclusivas).
    """
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    per_page = min(max(request.args.get("per_page", AUDITORIA_POR_PAGINA_PADRAO, type=int) or 1, 1),
                   AUDITORIA_POR_PAGINA_MAXIMO)

    query = AuditLog.query
    acao = request.args.get("acao", "").strip().upper()
    if acao:
        query = query.filter(AuditLog.acao == acao)
    entidade = request.args.get("entidade", "").strip()
    if entidade:
        query = query.filter(db.func.lower(AuditLog.entidade) == entidade.lower())
    entidade_id = request.args.get("entidade_id", type=int)
    if entidade_id is not None:
        query = query.filter(AuditLog.entidade_id == entidade_id)
    email = request.args.get("email", "").strip().lower()
    if email:
        query = query.filter(db.func.lower(AuditLog.user_email).contains(email, autoescape=True))
    data_inicio = parse_date(request.args.get("data_inicio"), "data_inicio")
    data_fim = parse_date(request.args.get("data_fim"), "data_fim")
    if data_inicio and data_fim and data_fim < data_inicio:
        raise ApiError("Data inválida", 400, "A data final não pode ser anterior à data inicial.")
    if data_inicio:
        query = query.filter(AuditLog.created_at >= tempo.inicio_do_dia_em_utc(data_inicio))
    if data_fim:
        from datetime import timedelta
        query = query.filter(AuditLog.created_at < tempo.inicio_do_dia_em_utc(data_fim + timedelta(days=1)))

    pagination = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    logs = pagination.items
    return jsonify({
        "sucesso": True,
        "total": len(logs),
        "total_registros": pagination.total,
        "pagina_atual": page,
        "por_pagina": per_page,
        "total_paginas": pagination.pages,
        "filtros_aplicados": {
            "acao": acao, "entidade": entidade, "entidade_id": entidade_id, "email": email,
            "data_inicio": data_inicio.isoformat() if data_inicio else "",
            "data_fim": data_fim.isoformat() if data_fim else "",
        },
        "logs": [log.to_dict() for log in logs]
    }), 200


@admin_bp.route("/auditoria/acoes", methods=["GET"])
@admin_required
def auditoria_acoes():
    """Valores distintos de ação e entidade, para os filtros da tela de auditoria."""
    acoes = [a for (a,) in db.session.query(AuditLog.acao).distinct().order_by(AuditLog.acao).all()]
    entidades = [e for (e,) in db.session.query(AuditLog.entidade).distinct().order_by(AuditLog.entidade).all()]
    return jsonify({"sucesso": True, "acoes": acoes, "entidades": entidades}), 200
