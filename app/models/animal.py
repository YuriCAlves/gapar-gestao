from datetime import datetime, date
from app.extensions import db


class Animal(db.Model):
    """Modelo de Cão Resgatado (RF05-RF11, RF19, RN01, RN02, RN03, RN05, RN07)."""
    __tablename__ = "animals"

    # Status operacionais válidos no sistema (RN02)
    STATUS_ACOLHIMENTO = "em acolhimento"
    STATUS_TRATAMENTO = "em tratamento"
    STATUS_DISPONIVEL = "disponível"
    STATUS_LAR_TEMPORARIO = "lar temporário"
    STATUS_ADOTADO = "adotado"
    STATUS_OBITO = "óbito"

    VALID_STATUSES = [
        STATUS_ACOLHIMENTO,
        STATUS_TRATAMENTO,
        STATUS_DISPONIVEL,
        STATUS_LAR_TEMPORARIO,
        STATUS_ADOTADO,
        STATUS_OBITO,
    ]

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, index=True)
    idade_estimada = db.Column(db.String(50), nullable=True)
    sexo = db.Column(db.String(10), nullable=False) # 'Macho' ou 'Fêmea'
    raca = db.Column(db.String(100), default="Sem Raça Definida (SRD)", nullable=False)
    porte = db.Column(db.String(20), nullable=False) # 'Pequeno', 'Médio', 'Grande'
    pelagem = db.Column(db.String(50), nullable=True)
    peso_kg = db.Column(db.Float, nullable=True)
    
    # Foto com compressão otimizada (RF06, RNF02)
    foto_url = db.Column(db.String(255), nullable=True)
    
    # Origem e Resgate (RF07)
    local_resgate = db.Column(db.String(200), nullable=True)
    data_entrada = db.Column(db.Date, default=date.today, nullable=False) # RN01: data do dia
    motivo_resgate = db.Column(db.Text, nullable=True)
    
    # Flags operacionais especiais (RF08, RN07)
    is_castrado = db.Column(db.Boolean, default=False, nullable=False)
    is_microchipado = db.Column(db.Boolean, default=False, nullable=False)
    is_idoso = db.Column(db.Boolean, default=False, nullable=False)
    cuidados_especiais = db.Column(db.Text, nullable=True)

    # Localização e identificação (protótipos)
    localizacao_baia = db.Column(db.String(100), nullable=True)
    codigo_identificador = db.Column(db.String(50), nullable=True, index=True)
    
    # Status Operacional (RN01: inicial obrigatório 'em acolhimento')
    status_operacional = db.Column(
        db.String(30),
        default=STATUS_ACOLHIMENTO,
        nullable=False,
        index=True
    )
    
    # RN03: Proibição de exclusão física (Soft Delete)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relacionamentos
    vaccinations = db.relationship("Vaccination", backref="animal", lazy="dynamic", cascade="all, delete-orphan")
    medical_records = db.relationship("MedicalRecord", backref="animal", lazy="dynamic", cascade="all, delete-orphan")
    prescriptions = db.relationship("Prescription", backref="animal", lazy="dynamic", cascade="all, delete-orphan")
    adoption = db.relationship("Adoption", backref="animal", uselist=False, cascade="all, delete-orphan")

    @property
    def is_frozen(self):
        """RN05: Animais adotados ou óbito têm cadastros congelados."""
        return self.status_operacional in (self.STATUS_ADOTADO, self.STATUS_OBITO)

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "idade_estimada": self.idade_estimada,
            "sexo": self.sexo,
            "raca": self.raca,
            "porte": self.porte,
            "pelagem": self.pelagem,
            "peso_kg": self.peso_kg,
            "foto_url": self.foto_url,
            "local_resgate": self.local_resgate,
            "data_entrada": self.data_entrada.isoformat() if self.data_entrada else None,
            "motivo_resgate": self.motivo_resgate,
            "is_castrado": self.is_castrado,
            "is_idoso": self.is_idoso,
            "cuidados_especiais": self.cuidados_especiais,
            "status_operacional": self.status_operacional,
            "congelado": self.is_frozen,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
