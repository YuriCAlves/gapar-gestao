from datetime import date
from app.extensions import db
from app.utils.pii import formatar_cpf, normalizar_cpf
from .base import utcnow
from .pii_mixin import campo_pii


class Adoption(db.Model):
    """Registro Formal e Histórico de Adoção (RF20, RF21, RN04, RN05, RN06).
    Preserva dados completos do adotante e imutabilidade pós-adoção.

    CP-01: CPF e endereço do adotante ficam cifrados (`*_cifrado`); o CPF tem índice cego para
    busca exata. As colunas físicas antigas `adotante_cpf` e `adotante_endereco` só guardam
    registros anteriores ao backfill e são removidas na migração `0003b`.
    """
    __tablename__ = "adoptions"

    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("animals.id"), nullable=False, unique=True, index=True)

    # RN04: Exigência obrigatória de nome, telefone e data
    adotante_nome = db.Column(db.String(150), nullable=False)
    adotante_telefone = db.Column(db.String(30), nullable=False)

    # Legado em claro (somente leitura até a 0003b)
    adotante_cpf_legado = db.Column("adotante_cpf", db.String(20), nullable=True)
    adotante_endereco_legado = db.Column("adotante_endereco", db.String(255), nullable=True)

    adotante_cpf_cifrado = db.Column(db.Text, nullable=True)
    adotante_cpf_bidx = db.Column(db.String(64), nullable=True, index=True)
    adotante_endereco_cifrado = db.Column(db.Text, nullable=True)

    data_adocao = db.Column(db.Date, nullable=False, default=date.today)
    termo_assinado = db.Column(db.Boolean, default=True, nullable=False)
    termo_fisico_assinado = db.Column(db.Boolean, default=False, nullable=False)
    observacoes = db.Column(db.Text, nullable=True)

    # Rastreabilidade da autoria do registro (RF24)
    cadastrado_por_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    cadastrado_por = db.relationship("User", foreign_keys=[cadastrado_por_user_id])

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    adotante_cpf = campo_pii("adotante_cpf_legado", "adotante_cpf_cifrado", "adotante_cpf_bidx", "cpf",
                             normalizar_cpf)
    adotante_endereco = campo_pii("adotante_endereco_legado", "adotante_endereco_cifrado")

    # Dados pessoais do adotante visíveis só para a Administradora (RNF07, LGPD)
    CAMPOS_RESTRITOS = ("adotante_cpf", "adotante_endereco")

    def to_dict(self, completo=False):
        """`completo=False` omite CPF e endereço do adotante (perfil Voluntária)."""
        dados = {
            "id": self.id,
            "animal_id": self.animal_id,
            "adotante_nome": self.adotante_nome,
            "adotante_telefone": self.adotante_telefone,
            "data_adocao": self.data_adocao.isoformat() if self.data_adocao else None,
            "termo_assinado": self.termo_assinado,
            "termo_fisico_assinado": self.termo_fisico_assinado,
            "observacoes": self.observacoes,
            "cadastrado_por_user_id": self.cadastrado_por_user_id,
            "created_at": self.created_at.isoformat()
        }
        if completo:
            # Só decifra quando a Administradora vai de fato ver o dado.
            dados["adotante_cpf"] = formatar_cpf(self.adotante_cpf)
            dados["adotante_endereco"] = self.adotante_endereco
        return dados
