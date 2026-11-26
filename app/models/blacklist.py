from sqlalchemy.orm import validates

from app.extensions import db
from app.utils.crypto import indice_cego
from app.utils.pii import formatar_cpf, normalizar_cpf, normalizar_nome, normalizar_telefone
from .base import utcnow
from .pii_mixin import campo_pii


class NonEligiblePerson(db.Model):
    """Lista Sigilosa e Restrita de Pessoas Não Aptas a Adotar (RF22, RN15).
    Acesso restrito exclusiva e unicamente à Administradora.

    CP-01: CPF e telefone ficam cifrados (`*_cifrado`) com índice cego (`*_bidx`) para a busca
    exata da RN15. As colunas físicas antigas `cpf` e `telefone` só guardam registros anteriores
    ao backfill e são removidas na migração `0003b`.
    """
    __tablename__ = "non_eligible_people"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False, index=True)
    nome_bidx = db.Column(db.String(64), nullable=True, index=True)

    # Legado em claro (somente leitura até a 0003b)
    cpf_legado = db.Column("cpf", db.String(20), nullable=True, index=True)
    telefone_legado = db.Column("telefone", db.String(30), nullable=True)

    cpf_cifrado = db.Column(db.Text, nullable=True)
    cpf_bidx = db.Column(db.String(64), nullable=True, index=True)
    telefone_cifrado = db.Column(db.Text, nullable=True)
    telefone_bidx = db.Column(db.String(64), nullable=True, index=True)

    motivo_impedimento = db.Column(db.Text, nullable=False) # Histórico de maus-tratos ou negligência

    # Registrado por quem (auditoria interna)
    cadastrado_por_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    cadastrado_por = db.relationship("User", foreign_keys=[cadastrado_por_user_id])
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    cpf = campo_pii("cpf_legado", "cpf_cifrado", "cpf_bidx", "cpf", normalizar_cpf)
    telefone = campo_pii("telefone_legado", "telefone_cifrado", "telefone_bidx", "tel", normalizar_telefone)

    @validates("nome")
    def _indexar_nome(self, _chave, valor):
        self.nome_bidx = indice_cego("nome", normalizar_nome(valor)) if valor else None
        return valor

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "cpf": formatar_cpf(self.cpf),
            "telefone": self.telefone,
            "motivo_impedimento": self.motivo_impedimento,
            "created_at": self.created_at.isoformat()
        }
