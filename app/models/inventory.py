"""Estoque de insumos com lotes FEFO (CP-03, RN18, RN19, RN20).

Três tabelas (migração `0005_estoque_insumos`):

- `inventory_items`: o insumo (vacina, medicamento, ração...). Exclusão só lógica (RN03).
- `inventory_batches`: o lote, com validade e saldo. O saldo nunca fica negativo (RN18: CHECK no
  banco). Exclusão física proibida (RN03).
- `inventory_movements`: cada entrada, saída ou ajuste. Imutável (RN19): correção entra como novo
  ajuste. No PostgreSQL um gatilho também bloqueia UPDATE/DELETE/TRUNCATE.

Toda alteração de saldo passa pelo `inventory_service` (bloqueio do lote e gravação do movimento
com `saldo_apos`). Aqui ficam só a estrutura, os derivados do contrato (`ItemEstoque`,
`LoteEstoque`, `MovimentoEstoque` em app/views/src/types/contratos.ts) e as consultas FEFO.

"Hoje" é sempre `app.utils.tempo.hoje()` (fuso do abrigo). Lote vencido = validade ANTERIOR a
hoje (RN20): um lote que vence hoje ainda pode ser usado hoje.
"""
from datetime import timedelta
from decimal import Decimal

import sqlalchemy as sa

from app.extensions import db
from app.utils import tempo
from .base import RegistroImutavel, proibir_exclusao_fisica, sql_in, tornar_imutavel, utcnow

CATEGORIAS = ("Vacina", "Medicamento", "Vermífugo", "Antipulgas", "Ração", "Insumo Clínico", "Limpeza")
UNIDADES = ("doses", "comprimidos", "ml", "kg", "unidades")
TIPOS_MOVIMENTO = ("ENTRADA", "SAIDA_USO", "AJUSTE_MAIS", "AJUSTE_MENOS", "DESCARTE_VALIDADE", "PERDA")
# Tipos que aumentam o saldo; os demais diminuem.
TIPOS_QUE_SOMAM = ("ENTRADA", "AJUSTE_MAIS")

ZERO = Decimal("0")


def _numero(valor):
    """NUMERIC(10,2) -> float no JSON (contrato: `number`)."""
    return float(valor) if valor is not None else None


def _hoje(hoje):
    return hoje if hoje is not None else tempo.hoje()


@proibir_exclusao_fisica
class InventoryItem(db.Model):
    """Insumo do estoque (CP-03). RN03: nunca é apagado; use `is_deleted`/`is_active`."""
    __tablename__ = "inventory_items"

    CATEGORIA_VACINA = "Vacina"
    CATEGORIAS = CATEGORIAS
    UNIDADES = UNIDADES

    __table_args__ = (
        db.CheckConstraint(sql_in("categoria", CATEGORIAS), name="ck_inventory_items_categoria"),
        db.CheckConstraint(sql_in("unidade", UNIDADES), name="ck_inventory_items_unidade"),
        db.CheckConstraint("estoque_minimo >= 0", name="ck_inventory_items_estoque_minimo"),
        db.CheckConstraint("length(ltrim(nome)) > 0", name="ck_inventory_items_nome_preenchido"),
        # Lista da tela de estoque: WHERE is_deleted = false [AND categoria = ?] ORDER BY nome
        db.Index("ix_inventory_items_listagem", "is_deleted", "categoria", "nome"),
    )

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    categoria = db.Column(db.String(30), nullable=False)
    unidade = db.Column(db.String(20), nullable=False)
    estoque_minimo = db.Column(db.Numeric(10, 2), nullable=False, default=ZERO, server_default="0")
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=sa.true())
    is_deleted = db.Column(db.Boolean, nullable=False, default=False, server_default=sa.false())
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    # `selectin`: a lista de itens carrega todos os lotes numa consulta só (sem N+1 no saldo).
    lotes = db.relationship("InventoryBatch", back_populates="item", lazy="selectin",
                            passive_deletes="all", order_by="InventoryBatch.id")

    @classmethod
    def query_listagem(cls, categoria=None, incluir_inativos=False):
        """Itens não excluídos, por nome (GET /api/estoque/itens)."""
        consulta = cls.query.filter(cls.is_deleted.is_(False))
        if not incluir_inativos:
            consulta = consulta.filter(cls.is_active.is_(True))
        if categoria:
            consulta = consulta.filter(cls.categoria == categoria)
        return consulta.order_by(cls.nome, cls.id)

    # Derivados do contrato `ItemEstoque` ------------------------------------------------------

    def lotes_validos(self, hoje=None):
        """Lotes não vencidos (com ou sem saldo)."""
        dia = _hoje(hoje)
        return [lote for lote in self.lotes if not lote.esta_vencido(dia)]

    def saldo_total(self, hoje=None):
        """Soma dos saldos dos lotes NÃO vencidos (Decimal)."""
        return sum((lote.saldo_atual or ZERO for lote in self.lotes_validos(hoje)), ZERO)

    def abaixo_do_minimo(self, hoje=None):
        """Saldo válido estritamente menor que o estoque mínimo (mínimo 0 nunca alerta)."""
        return self.saldo_total(hoje) < (self.estoque_minimo or ZERO)

    def proxima_validade(self, hoje=None):
        """Validade mais próxima entre os lotes com saldo e não vencidos; None se não houver."""
        datas = [lote.data_validade for lote in self.lotes_validos(hoje)
                 if lote.data_validade is not None and (lote.saldo_atual or ZERO) > 0]
        return min(datas) if datas else None

    def lotes_fefo(self, hoje=None):
        """Lotes na ordem do `DetalheItemEstoque`: validade mais próxima primeiro, sem validade
        depois, vencidos no fim (empate pelo id)."""
        dia = _hoje(hoje)
        return sorted(self.lotes, key=lambda lote: lote.chave_fefo(dia))

    def to_dict(self, hoje=None):
        dia = _hoje(hoje)
        saldo = self.saldo_total(dia)
        validade = self.proxima_validade(dia)
        return {
            "id": self.id,
            "nome": self.nome,
            "categoria": self.categoria,
            "unidade": self.unidade,
            "estoque_minimo": _numero(self.estoque_minimo),
            "saldo_total": _numero(saldo),
            "abaixo_do_minimo": saldo < (self.estoque_minimo or ZERO),
            "proxima_validade": validade.isoformat() if validade else None,
            "is_active": bool(self.is_active),
        }


@proibir_exclusao_fisica
class InventoryBatch(db.Model):
    """Lote de um insumo (CP-03). RN18: saldo nunca negativo. RN03: nunca é apagado."""
    __tablename__ = "inventory_batches"
    __table_args__ = (
        db.CheckConstraint("saldo_atual >= 0", name="ck_inventory_batches_saldo_nao_negativo"),
        db.CheckConstraint("length(ltrim(codigo_lote)) > 0", name="ck_inventory_batches_codigo_preenchido"),
        db.UniqueConstraint("item_id", "codigo_lote", name="uq_inventory_batches_item_lote"),
        # FEFO: WHERE item_id = ? ORDER BY data_validade, id
        db.Index("ix_batches_fefo", "item_id", "data_validade", "id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("inventory_items.id"), nullable=False)
    codigo_lote = db.Column(db.String(60), nullable=False)
    data_validade = db.Column(db.Date, nullable=True)
    saldo_atual = db.Column(db.Numeric(10, 2), nullable=False, default=ZERO, server_default="0")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    item = db.relationship("InventoryItem", back_populates="lotes")
    movimentos = db.relationship("InventoryMovement", back_populates="lote", lazy="dynamic",
                                 passive_deletes="all")

    def esta_vencido(self, hoje=None):
        """RN20: vencido = validade anterior a hoje. Sem validade nunca vence."""
        return self.data_validade is not None and self.data_validade < _hoje(hoje)

    def dias_para_vencer(self, hoje=None):
        """Dias até a validade (negativo = vencido há N dias); None sem validade."""
        if self.data_validade is None:
            return None
        return (self.data_validade - _hoje(hoje)).days

    def chave_fefo(self, hoje=None):
        dia = _hoje(hoje)
        return (self.esta_vencido(dia), self.data_validade is None,
                self.data_validade or dia, self.id or 0)

    @classmethod
    def ordem_fefo(cls):
        """ORDER BY FEFO portável: sem validade por último nos dois bancos (o SQLite põe NULL
        primeiro em ASC e o PostgreSQL por último), empate pelo id."""
        return (sa.case((cls.data_validade.is_(None), 1), else_=0), cls.data_validade, cls.id)

    @classmethod
    def query_fefo_utilizaveis(cls, item_id, hoje=None):
        """Lotes do item que podem ser usados hoje: com saldo e não vencidos, em ordem FEFO
        (base da `SugestaoFefo` e da baixa automática)."""
        dia = _hoje(hoje)
        return cls.query.filter(
            cls.item_id == item_id,
            cls.saldo_atual > 0,
            sa.or_(cls.data_validade.is_(None), cls.data_validade >= dia),
        ).order_by(*cls.ordem_fefo())

    @classmethod
    def query_vencendo(cls, hoje=None, dias=30):
        """Lotes com saldo de itens ativos que vencem até `hoje + dias`, incluindo os já
        vencidos (precisam de descarte), validade mais próxima primeiro (alerta do /api/hoje)."""
        dia = _hoje(hoje)
        return (cls.query.join(InventoryItem, cls.item_id == InventoryItem.id)
                .filter(InventoryItem.is_deleted.is_(False), InventoryItem.is_active.is_(True),
                        cls.saldo_atual > 0, cls.data_validade.isnot(None),
                        cls.data_validade <= dia + timedelta(days=dias))
                .order_by(cls.data_validade, cls.id))

    def to_dict(self, hoje=None):
        dia = _hoje(hoje)
        return {
            "id": self.id,
            "item_id": self.item_id,
            "codigo_lote": self.codigo_lote,
            "data_validade": self.data_validade.isoformat() if self.data_validade else None,
            "saldo_atual": _numero(self.saldo_atual),
            "vencido": self.esta_vencido(dia),
            "vence_em_dias": self.dias_para_vencer(dia),
        }


@tornar_imutavel(regra="RN19", excecao=RegistroImutavel)
class InventoryMovement(db.Model):
    """Movimento de estoque (CP-03). RN19: imutável; correção entra como AJUSTE_MAIS/MENOS."""
    __tablename__ = "inventory_movements"

    TIPOS = TIPOS_MOVIMENTO
    TIPOS_QUE_SOMAM = TIPOS_QUE_SOMAM

    __table_args__ = (
        db.CheckConstraint(sql_in("tipo", TIPOS_MOVIMENTO), name="ck_inventory_movements_tipo"),
        db.CheckConstraint("quantidade > 0", name="ck_inventory_movements_quantidade_positiva"),
        db.CheckConstraint("saldo_apos >= 0", name="ck_inventory_movements_saldo_apos"),
        db.CheckConstraint("length(ltrim(motivo)) > 0", name="ck_inventory_movements_motivo_preenchido"),
        # Detalhe do item: últimos movimentos de cada lote, mais recentes primeiro
        db.Index("ix_inventory_movements_batch_created", "batch_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("inventory_batches.id"), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    quantidade = db.Column(db.Numeric(10, 2), nullable=False)
    saldo_apos = db.Column(db.Numeric(10, 2), nullable=False)
    motivo = db.Column(db.String(255), nullable=False)
    animal_id = db.Column(db.Integer, db.ForeignKey("animals.id"), nullable=True, index=True)
    vaccination_id = db.Column(db.Integer, db.ForeignKey("vaccinations.id"), nullable=True, index=True)
    medication_log_id = db.Column(db.Integer, db.ForeignKey("medication_logs.id"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    lote = db.relationship("InventoryBatch", back_populates="movimentos")
    # `joined`: a lista de movimentos já traz o nome de quem registrou (sem N+1).
    usuario = db.relationship("User", foreign_keys=[user_id], lazy="joined")

    @classmethod
    def query_do_item(cls, item_id, limite=50):
        """Últimos movimentos de todos os lotes do item, mais recentes primeiro."""
        return (cls.query.join(InventoryBatch, cls.batch_id == InventoryBatch.id)
                .filter(InventoryBatch.item_id == item_id)
                .order_by(cls.created_at.desc(), cls.id.desc())
                .limit(limite))

    def to_dict(self):
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "tipo": self.tipo,
            "quantidade": _numero(self.quantidade),
            "saldo_apos": _numero(self.saldo_apos),
            "motivo": self.motivo,
            "animal_id": self.animal_id,
            "registrado_por": (self.usuario.name or self.usuario.email) if self.usuario else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
