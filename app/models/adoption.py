from datetime import datetime, date
from app.extensions import db


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
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
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
            "created_at": self.created_at.isoformat()
        }
