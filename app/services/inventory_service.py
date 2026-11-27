"""Estoque de insumos (CP-03, RN18, RN19, RN20): ÚNICA porta de alteração de saldo.

Nenhuma rota escreve `InventoryBatch.saldo_atual` direto: tudo passa por `movimentar`, que
altera o saldo e grava o `InventoryMovement` (com `saldo_apos`) na mesma transação. O commit
fica com quem chamou (a rota), para que a baixa de estoque e o registro de saúde sejam gravados
juntos ou nenhum deles (REQ-36).

Concorrência (RN18): a saída é UM `UPDATE` condicional atômico,

    UPDATE inventory_batches SET saldo_atual = saldo_atual - :q
    WHERE id = :id AND saldo_atual >= :q

e `rowcount == 0` significa saldo insuficiente (409). Vale igual no SQLite e no PostgreSQL e
dispensa `SELECT ... FOR UPDATE`: no PostgreSQL (READ COMMITTED) o UPDATE trava a linha; uma
segunda transação concorrente espera o commit da primeira e reavalia o `WHERE` sobre a versão
nova da linha, então só uma das duas consegue consumir o último saldo. No SQLite a escrita é
serializada pelo bloqueio do arquivo. O CHECK `saldo_atual >= 0` do banco é a última barreira.

`saldo_apos` é lido DEPOIS do UPDATE, na mesma transação (já com o bloqueio da linha), e por
isso reflete exatamente o saldo que este movimento deixou.
"""
from decimal import Decimal, InvalidOperation

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import contains_eager

from app.extensions import db
from app.models.inventory import InventoryBatch, InventoryItem, InventoryMovement
from app.utils import tempo
from app.utils.validation import ApiError

SAIDA_USO = "SAIDA_USO"
CENTAVO = Decimal("0.01")
# NUMERIC(10,2): até 99.999.999,99
QUANTIDADE_MAXIMA = Decimal("99999999.99")

_Q = sa.bindparam("q", type_=sa.Numeric(10, 2))
_ID = sa.bindparam("id", type_=sa.Integer)

# `round(..., 2)`: no SQLite o NUMERIC vira REAL; o arredondamento evita resíduo de ponto
# flutuante (0,30 - 0,10 - 0,10 - 0,10 = -0,0000000000000000277). No PostgreSQL é exato.
# A soma também é condicional: NUMERIC(10,2) não comporta mais que 99.999.999,99 (no SQLite o
# valor passaria em silêncio; no PostgreSQL viraria DataError).
_SQL_SOMAR = sa.text(
    "UPDATE inventory_batches SET saldo_atual = round(saldo_atual + :q, 2) "
    "WHERE id = :id AND saldo_atual + :q <= 99999999.99"
).bindparams(_Q, _ID)
_SQL_SUBTRAIR = sa.text(
    "UPDATE inventory_batches SET saldo_atual = round(saldo_atual - :q, 2) "
    "WHERE id = :id AND saldo_atual >= :q"
).bindparams(_Q, _ID)


def parse_quantidade(valor, campo="quantidade", padrao=None, permitir_zero=False):
    """Quantidade > 0 (ou >= 0 com `permitir_zero`) com até 2 casas decimais (aceita vírgula).
    Vazio -> `padrao` (sem padrão -> 400)."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if padrao is None:
            raise ApiError("Campo obrigatório", 400, f"O campo '{campo}' é obrigatório.")
        return Decimal(padrao)
    if isinstance(valor, (bool, dict, list)):
        raise ApiError("Quantidade inválida", 400, f"O campo '{campo}' deve ser numérico.")
    try:
        numero = Decimal(str(valor).strip().replace(",", "."))
    except InvalidOperation:
        raise ApiError("Quantidade inválida", 400, f"O campo '{campo}' deve ser numérico.")
    if not numero.is_finite() or numero < 0 or (numero == 0 and not permitir_zero):
        raise ApiError("Quantidade inválida", 400, f"O campo '{campo}' deve ser maior que zero.")
    if numero != numero.quantize(CENTAVO, rounding="ROUND_DOWN"):
        raise ApiError("Quantidade inválida", 400, f"O campo '{campo}' aceita no máximo 2 casas decimais.")
    if numero > QUANTIDADE_MAXIMA:
        raise ApiError("Quantidade inválida", 400, f"O campo '{campo}' é grande demais.")
    return numero.quantize(CENTAVO)


def lote_ou_erro(lote_id, status_inexistente=404):
    lote = db.session.get(InventoryBatch, lote_id) if lote_id is not None else None
    if lote is None or lote.item is None or lote.item.is_deleted:
        if status_inexistente == 404:
            raise ApiError("Recurso não encontrado", 404, "Lote de estoque não encontrado.")
        raise ApiError("Lote inválido", 400, "O lote de estoque informado não existe.")
    return lote


def movimentar(lote, tipo, quantidade, motivo, *, user_id=None, animal_id=None,
               vaccination_id=None, medication_log_id=None, hoje=None):
    """Aplica o movimento ao saldo do lote e grava o `InventoryMovement`. Não faz commit.

    - ENTRADA/AJUSTE_MAIS somam;
    - os demais tipos subtraem pelo UPDATE condicional: saldo insuficiente -> 409 (RN18);
    - SAIDA_USO de lote vencido (validade anterior a hoje) -> 422 (RN20).
    Devolve o movimento gravado (flush feito); o saldo do lote é recarregado do banco.
    """
    if tipo not in InventoryMovement.TIPOS:
        raise ApiError("Tipo inválido", 400, "Tipo de movimento inválido.",
                       permitidos=list(InventoryMovement.TIPOS))
    quantidade = parse_quantidade(quantidade)
    motivo = (motivo or "").strip()
    if not motivo:
        raise ApiError("Campo obrigatório", 400, "O campo 'motivo' é obrigatório.")

    dia = hoje if hoje is not None else tempo.hoje()
    if tipo == SAIDA_USO and lote.esta_vencido(dia):
        raise ApiError("Lote vencido", 422,
                       "Este lote está vencido e não pode ser usado (RN20). Registre o descarte.")

    db.session.flush()  # pendências da sessão vão antes do UPDATE direto
    parametros = {"q": quantidade, "id": lote.id}
    if tipo in InventoryMovement.TIPOS_QUE_SOMAM:
        resultado = db.session.execute(_SQL_SOMAR, parametros)
    else:
        resultado = db.session.execute(_SQL_SUBTRAIR, parametros)
    if resultado.rowcount != 1 and tipo in InventoryMovement.TIPOS_QUE_SOMAM:
        raise ApiError("Saldo máximo excedido", 400,
                       "O saldo do lote não pode passar de 99.999.999,99. Confira a quantidade.")
    if resultado.rowcount != 1:
        raise ApiError("Saldo insuficiente", 409,
                       "O saldo deste lote não é suficiente para esta saída; o saldo nunca fica negativo (RN18).")

    saldo_apos = db.session.execute(
        sa.select(InventoryBatch.saldo_atual).where(InventoryBatch.id == lote.id)
    ).scalar_one()
    db.session.expire(lote, ["saldo_atual"])

    movimento = InventoryMovement(
        batch_id=lote.id, tipo=tipo, quantidade=quantidade,
        saldo_apos=Decimal(str(saldo_apos)).quantize(CENTAVO), motivo=motivo[:255],
        animal_id=animal_id, vaccination_id=vaccination_id,
        medication_log_id=medication_log_id, user_id=user_id,
    )
    db.session.add(movimento)
    db.session.flush()
    return movimento


def baixar_uso(lote_id, quantidade, motivo, *, categoria_exigida=None, user_id=None, animal_id=None,
               vaccination_id=None, medication_log_id=None):
    """Saída de uso (SAIDA_USO) ligada a um registro de saúde. Não faz commit.

    `lote_id` inexistente -> 400 (a rota é de saúde; 404 confundiria com o animal);
    item de outra categoria que não `categoria_exigida` -> 400; vencido -> 422; saldo -> 409.
    """
    lote = lote_ou_erro(lote_id, status_inexistente=400)
    if categoria_exigida and lote.item.categoria != categoria_exigida:
        raise ApiError("Lote inválido", 400,
                       f"O lote informado não é de um item da categoria '{categoria_exigida}'.")
    return movimentar(lote, SAIDA_USO, quantidade, motivo, user_id=user_id, animal_id=animal_id,
                      vaccination_id=vaccination_id, medication_log_id=medication_log_id)


def criar_lote_com_entrada(item, codigo_lote, data_validade, quantidade, motivo, *, user_id=None):
    """Cria o lote com saldo zero e dá a ENTRADA inicial pelo `movimentar`. Não faz commit.

    Código de lote repetido no mesmo item -> 409 (inclusive na corrida, pelo UNIQUE do banco).
    """
    if InventoryBatch.query.filter_by(item_id=item.id, codigo_lote=codigo_lote).first() is not None:
        raise _lote_duplicado()
    lote = InventoryBatch(item_id=item.id, codigo_lote=codigo_lote, data_validade=data_validade,
                          saldo_atual=Decimal("0"))
    try:
        with db.session.begin_nested():
            db.session.add(lote)
            db.session.flush()
    except IntegrityError:
        raise _lote_duplicado()
    movimento = movimentar(lote, "ENTRADA", quantidade, motivo, user_id=user_id)
    return lote, movimento


def _lote_duplicado():
    return ApiError("Lote duplicado", 409,
                    "Já existe um lote com este código neste item. Use a opção de ajustar saldo.")


def sugestao_fefo(item_id, quantidade, hoje=None):
    """`SugestaoFefo`: lotes utilizáveis em ordem FEFO e o 1º com saldo suficiente."""
    dia = hoje if hoje is not None else tempo.hoje()
    lotes = InventoryBatch.query_fefo_utilizaveis(item_id, dia).all()
    sugerido = next((lote.id for lote in lotes if lote.saldo_atual >= quantidade), None)
    return {"lotes": [lote.to_dict(dia) for lote in lotes], "sugerido_id": sugerido}


def alertas_hoje(hoje=None):
    """`AlertasEstoqueHoje` do painel Hoje (só Administradora; quem chama confere o perfil)."""
    dia = hoje if hoje is not None else tempo.hoje()
    itens = InventoryItem.query_listagem().all()  # lotes por `selectin`: 2 consultas no total
    acabando = [item.to_dict(dia) for item in itens if item.abaixo_do_minimo(dia)]
    vencendo = []
    for lote in (InventoryBatch.query_vencendo(dia)
                 .options(contains_eager(InventoryBatch.item)).all()):
        vencendo.append({**lote.to_dict(dia), "item_nome": lote.item.nome})
    return {"acabando": acabando, "vencendo": vencendo}
