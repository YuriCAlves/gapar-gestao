"""Isolamento sanitário (CP-05, RN22, RN17 ampliada). Migração `0007_isolamento_sanitario`.

- RN22: no máximo UM isolamento aberto (`fim_real IS NULL`) por animal, garantido pelo índice
  único parcial `uq_isolation_aberto_por_animal` nos dois bancos (PostgreSQL e SQLite).
- RN03: o histórico de isolamentos nunca é apagado (ORM aqui e gatilho no PostgreSQL).
- RN17 ampliada: animal com isolamento aberto não aparece na vitrine (`Animal._filtro_vitrine`).
  Abrir o isolamento NÃO mexe em `is_publicado`: ao encerrar, o animal volta sozinho para a
  vitrine se continuar publicado e disponível (o isolamento é temporário e não deve exigir
  republicação).

Contrato: `IsolamentoRegistro` e `IsolamentoAbertoResumo` (app/views/src/types/contratos.ts).
"""
import sqlalchemy as sa
from sqlalchemy.orm import contains_eager, joinedload
from sqlalchemy.orm.attributes import set_committed_value

from app.extensions import db
from .base import proibir_exclusao_fisica, utcnow

FILTRO_ABERTO = "fim_real IS NULL"


@proibir_exclusao_fisica
class IsolationRecord(db.Model):
    """Período de isolamento sanitário de um animal. Encerrar = preencher `fim_real`."""
    __tablename__ = "isolation_records"
    __table_args__ = (
        db.CheckConstraint("data_fim_prevista IS NULL OR data_fim_prevista >= data_inicio",
                           name="ck_isolation_records_fim_previsto"),
        db.CheckConstraint("length(ltrim(motivo)) > 0", name="ck_isolation_records_motivo_preenchido"),
        # RN22: um aberto por animal. `sqlite_where` é obrigatório: sem ele o SQLite criaria um
        # UNIQUE global e o animal nunca poderia ser isolado de novo depois de encerrar.
        db.Index("uq_isolation_aberto_por_animal", "animal_id", unique=True,
                 postgresql_where=sa.text(FILTRO_ABERTO), sqlite_where=sa.text(FILTRO_ABERTO)),
        # Histórico da ficha: WHERE animal_id = ? ORDER BY data_inicio DESC
        db.Index("ix_isolation_records_animal_inicio", "animal_id", "data_inicio"),
    )

    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("animals.id"), nullable=False)
    motivo = db.Column(db.String(200), nullable=False)
    protocolo_cuidados = db.Column(db.Text, nullable=True)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim_prevista = db.Column(db.Date, nullable=True)
    fim_real = db.Column(db.DateTime, nullable=True)
    aberto_por_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
                                   nullable=True, index=True)
    encerrado_por_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
                                      nullable=True, index=True)
    observacoes_alta = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    animal = db.relationship(
        "Animal",
        backref=db.backref("isolamentos", lazy="dynamic", passive_deletes="all"),
    )
    aberto_por = db.relationship("User", foreign_keys=[aberto_por_user_id])
    encerrado_por = db.relationship("User", foreign_keys=[encerrado_por_user_id])

    @property
    def aberto(self):
        return self.fim_real is None

    @classmethod
    def query_do_animal(cls, animal_id):
        """Histórico do animal, mais recentes primeiro (GET /api/animais/:id/isolamentos)."""
        return (cls.query.options(joinedload(cls.aberto_por), joinedload(cls.encerrado_por))
                .filter(cls.animal_id == animal_id)
                .order_by(cls.data_inicio.desc(), cls.id.desc()))

    @classmethod
    def aberto_do_animal(cls, animal_id):
        """Isolamento aberto do animal, ou None (RN22 garante no máximo um)."""
        return cls.query.filter(cls.animal_id == animal_id, cls.fim_real.is_(None)).first()

    @classmethod
    def query_abertos(cls):
        """Todos os abertos de animais não excluídos, com animal e usuárias numa consulta só
        (bloco `isolamentos` do /api/hoje). Mais antigos primeiro."""
        from .animal import Animal
        return (cls.query.join(Animal, cls.animal_id == Animal.id)
                .options(contains_eager(cls.animal), joinedload(cls.aberto_por), joinedload(cls.encerrado_por))
                .filter(cls.fim_real.is_(None), Animal.is_deleted.is_(False))
                .order_by(cls.data_inicio, cls.id))

    def to_resumo(self):
        """`IsolamentoAbertoResumo` (ficha e lista de animais)."""
        return {
            "id": self.id,
            "motivo": self.motivo,
            "data_inicio": self.data_inicio.isoformat() if self.data_inicio else None,
            "data_fim_prevista": self.data_fim_prevista.isoformat() if self.data_fim_prevista else None,
        }

    def to_dict(self):
        """`IsolamentoRegistro`."""
        def _nome(usuaria):
            return (usuaria.name or usuaria.email) if usuaria else None

        return {
            **self.to_resumo(),
            "animal_id": self.animal_id,
            "protocolo_cuidados": self.protocolo_cuidados,
            "fim_real": self.fim_real.isoformat() if self.fim_real else None,
            "observacoes_alta": self.observacoes_alta,
            "aberto_por": _nome(self.aberto_por),
            "encerrado_por": _nome(self.encerrado_por),
            "aberto": self.aberto,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def carregar_isolamentos_abertos(animais):
    """Preenche `Animal.isolamento_aberto_registro` de uma página inteira com UMA consulta.

    Use antes de `[a.to_dict() for a in animais]` em GET /api/animais (REQ-43, sem N+1).
    Equivale a `.options(selectinload(Animal.isolamento_aberto_registro))` na consulta original.
    """
    animais = [a for a in animais if a is not None]
    if not animais:
        return animais
    ids = {a.id for a in animais}
    abertos = {r.animal_id: r for r in IsolationRecord.query.filter(
        IsolationRecord.animal_id.in_(ids), IsolationRecord.fim_real.is_(None))}
    for animal in animais:
        set_committed_value(animal, "isolamento_aberto_registro", abertos.get(animal.id))
    return animais
