from datetime import date
from app.extensions import db
from .base import utcnow


class Adoption(db.Model):
    """Registro Formal e Histórico de Adoção (RF20, RF21, RN04, RN05, RN06).
    Preserva dados completos do adotante e imutabilidade pós-adoção.
    """
    __tablename__ = "adoptions"

    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("animals.id"), nullable=False, unique=True, index=True)
    
    # RN04: Exigência obrigatória de nome, telefone e data
    adotante_nome = db.Column(db.String(150), nullable=False)
    adotante_telefone = db.Column(db.String(30), nullable=False)
    adotante_cpf = db.Column(db.String(20), nullable=True) # LGPD compliance (RNF07)
    adotante_endereco = db.Column(db.String(255), nullable=True)
    
    data_adocao = db.Column(db.Date, nullable=False, default=date.today)
    termo_assinado = db.Column(db.Boolean, default=True, nullable=False)
    termo_fisico_assinado = db.Column(db.Boolean, default=False, nullable=False)
    observacoes = db.Column(db.Text, nullable=True)
    
    # Rastreabilidade da autoria do registro (RF24)
    cadastrado_por_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    cadastrado_por = db.relationship("User", foreign_keys=[cadastrado_por_user_id])
    
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    # Dados pessoais do adotante visíveis só para a Administradora (RNF07, LGPD)
    CAMPOS_RESTRITOS = ("adotante_cpf", "adotante_endereco")

    def to_dict(self, completo=False):
        """`completo=False` omite CPF e endereço do adotante (perfil Voluntária)."""
        dados = {
            "id": self.id,
            "animal_id": self.animal_id,
            "adotante_nome": self.adotante_nome,
            "adotante_telefone": self.adotante_telefone,
            "adotante_cpf": self.adotante_cpf,
            "adotante_endereco": self.adotante_endereco,
            "data_adocao": self.data_adocao.isoformat() if self.data_adocao else None,
            "termo_assinado": self.termo_assinado,
            "termo_fisico_assinado": self.termo_fisico_assinado,
            "observacoes": self.observacoes,
            "cadastrado_por_user_id": self.cadastrado_por_user_id,
            "created_at": self.created_at.isoformat()
        }
        if not completo:
            for campo in self.CAMPOS_RESTRITOS:
                dados.pop(campo)
        return dados
