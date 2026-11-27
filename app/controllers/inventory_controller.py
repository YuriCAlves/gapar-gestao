"""Estoque de insumos com lotes FEFO (CP-03, REQ-35). Flag "estoque" (desligada -> 404).

Rotas exatamente como em app/views/src/types/contratos.ts ("CONTRATOS PREVISTOS DA FASE 2"):
leitura e sugestão FEFO para qualquer perfil logado; criar, editar, dar entrada e ajustar só a
Administradora. Saldo só muda pelo `inventory_service` (RN18/RN19/RN20). A saída de uso
(SAIDA_USO) não entra por aqui: ela nasce do registro de saúde (vacina/medicação), ligada ao
animal. A auditoria guarda só ids, tipo e quantidade (nunca o texto livre do motivo).
"""
from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.extensions import db
from app.models.inventory import InventoryBatch, InventoryItem, InventoryMovement
from app.services import inventory_service
from app.services.audit import log_audit_event
from app.utils import tempo
from app.utils.decorators import admin_required
from app.utils.publico import require_feature
from app.utils.validation import (
    ApiError, get_payload, model_text, parse_bool, parse_date, parse_int, require_choice,
)

inventory_bp = Blueprint("inventory", __name__, url_prefix="/api/estoque")

TIPOS_POR_ROTA = tuple(t for t in InventoryMovement.TIPOS if t != inventory_service.SAIDA_USO)


def _item_ou_404(item_id):
    item = db.session.get(InventoryItem, item_id)
    if item is None or item.is_deleted:
        raise ApiError("Recurso não encontrado", 404, "Item de estoque não encontrado.")
    return item


def _estoque_minimo(valor):
    return inventory_service.parse_quantidade(valor, "estoque_minimo", padrao="0", permitir_zero=True)


def _booleano(data, campo):
    valor = data.get(campo)
    if not isinstance(valor, bool):
        raise ApiError("Valor inválido", 400, f"O campo '{campo}' deve ser verdadeiro ou falso.")
    return valor


def _qtd(valor):
    return f"{valor:.2f}"


@inventory_bp.route("/itens", methods=["GET"])
@require_feature("estoque")
def listar_itens():
    categoria = (request.args.get("categoria") or "").strip()
    if categoria:
        require_choice(categoria, "categoria", InventoryItem.CATEGORIAS)
    inativos = parse_bool(request.args.get("inativos", ""))
    hoje = tempo.hoje()
    itens = InventoryItem.query_listagem(categoria=categoria or None, incluir_inativos=inativos).all()
    return jsonify({"itens": [item.to_dict(hoje) for item in itens]}), 200


@inventory_bp.route("/itens", methods=["POST"])
@require_feature("estoque")
@admin_required
def criar_item():
    data = get_payload()
    nome = model_text(data, InventoryItem, "nome", obrigatorio=True)
    categoria = require_choice(data.get("categoria"), "categoria", InventoryItem.CATEGORIAS)
    unidade = require_choice(data.get("unidade"), "unidade", InventoryItem.UNIDADES)
    item = InventoryItem(nome=nome, categoria=categoria, unidade=unidade,
                         estoque_minimo=_estoque_minimo(data.get("estoque_minimo")))
    db.session.add(item)
    db.session.flush()
    log_audit_event(acao="ESTOQUE_ITEM_CRIADO", entidade="InventoryItem", entidade_id=item.id,
                    detalhes=f"Item de estoque #{item.id} criado (categoria: {categoria})", commit=False)
    db.session.commit()
    return jsonify({"item": item.to_dict()}), 201


@inventory_bp.route("/itens/<int:item_id>", methods=["PATCH"])
@require_feature("estoque")
@admin_required
def editar_item(item_id):
    item = _item_ou_404(item_id)
    data = get_payload()
    novos = {}
    if "nome" in data:
        novos["nome"] = model_text(data, InventoryItem, "nome", obrigatorio=True)
    if "estoque_minimo" in data:
        novos["estoque_minimo"] = _estoque_minimo(data.get("estoque_minimo"))
    if "is_active" in data:
        novos["is_active"] = _booleano(data, "is_active")
    if not novos:
        raise ApiError("Nada a alterar", 400, "Envie ao menos um campo do item para alterar.")

    alterados = [campo for campo, valor in novos.items() if getattr(item, campo) != valor]
    for campo in alterados:
        setattr(item, campo, novos[campo])
    if alterados:
        log_audit_event(acao="ESTOQUE_ITEM_ATUALIZADO", entidade="InventoryItem", entidade_id=item.id,
                        detalhes=f"Item de estoque #{item.id} alterado (campos: {', '.join(alterados)})",
                        commit=False)
        db.session.commit()
    return jsonify({"item": item.to_dict()}), 200


@inventory_bp.route("/itens/<int:item_id>", methods=["GET"])
@require_feature("estoque")
def detalhe_item(item_id):
    item = _item_ou_404(item_id)
    hoje = tempo.hoje()
    return jsonify({
        "item": item.to_dict(hoje),
        "lotes": [lote.to_dict(hoje) for lote in item.lotes_fefo(hoje)],
        "movimentos": [m.to_dict() for m in InventoryMovement.query_do_item(item.id, limite=50)],
    }), 200


@inventory_bp.route("/itens/<int:item_id>/lotes", methods=["POST"])
@require_feature("estoque")
@admin_required
def criar_lote(item_id):
    item = _item_ou_404(item_id)
    data = get_payload()
    codigo = model_text(data, InventoryBatch, "codigo_lote", obrigatorio=True)
    validade = parse_date(data.get("data_validade"), "data_validade")
    quantidade = inventory_service.parse_quantidade(data.get("quantidade"))
    motivo = model_text(data, InventoryMovement, "motivo", default="Entrada de lote")

    lote, movimento = inventory_service.criar_lote_com_entrada(
        item, codigo, validade, quantidade, motivo, user_id=current_user.id)
    log_audit_event(acao="ESTOQUE_LOTE_CRIADO", entidade="InventoryBatch", entidade_id=lote.id,
                    detalhes=f"Lote #{lote.id} do item #{item.id} criado com entrada de {_qtd(quantidade)}",
                    commit=False)
    db.session.commit()
    return jsonify({"lote": lote.to_dict(), "movimento": movimento.to_dict()}), 201


@inventory_bp.route("/lotes/<int:lote_id>/movimentos", methods=["POST"])
@require_feature("estoque")
@admin_required
def registrar_movimento(lote_id):
    lote = inventory_service.lote_ou_erro(lote_id)
    data = get_payload()
    tipo = data.get("tipo")
    if tipo == inventory_service.SAIDA_USO:
        raise ApiError("Tipo inválido", 400,
                       "A saída de uso é registrada junto com a vacina ou a medicação do animal.",
                       permitidos=list(TIPOS_POR_ROTA))
    require_choice(tipo, "tipo", TIPOS_POR_ROTA)
    quantidade = inventory_service.parse_quantidade(data.get("quantidade"))
    motivo = model_text(data, InventoryMovement, "motivo", obrigatorio=True)

    movimento = inventory_service.movimentar(lote, tipo, quantidade, motivo, user_id=current_user.id)
    log_audit_event(acao="ESTOQUE_MOVIMENTO", entidade="InventoryMovement", entidade_id=movimento.id,
                    detalhes=f"{tipo} de {_qtd(quantidade)} no lote #{lote.id} (saldo após: {_qtd(movimento.saldo_apos)})",
                    commit=False)
    db.session.commit()
    return jsonify({"lote": lote.to_dict(), "movimento": movimento.to_dict()}), 201


@inventory_bp.route("/fefo", methods=["GET"])
@require_feature("estoque")
def sugestao_fefo():
    item_id = parse_int(request.args.get("item_id"), "item_id", minimo=1)
    if item_id is None:
        raise ApiError("Campo obrigatório", 400, "Informe o parâmetro 'item_id'.")
    _item_ou_404(item_id)
    quantidade = inventory_service.parse_quantidade(request.args.get("quantidade"), padrao="1")
    return jsonify(inventory_service.sugestao_fefo(item_id, quantidade)), 200
