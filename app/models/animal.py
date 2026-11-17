from datetime import date
from app.extensions import db
from .base import utcnow, sql_in, proibir_exclusao_fisica


@proibir_exclusao_fisica
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

    SEXOS = ["Macho", "Fêmea"]
    PORTES = ["Pequeno", "Médio", "Grande"]

    # Status em que o animal está sob cuidados e pode receber prescrições (RN08)
    STATUS_PRESCREVIVEIS = [STATUS_ACOLHIMENTO, STATUS_TRATAMENTO, STATUS_LAR_TEMPORARIO]
    # Status dos quais é possível formalizar a adoção (RF20, RN04, RN07)
    STATUS_ADOTAVEIS = [STATUS_DISPONIVEL, STATUS_LAR_TEMPORARIO]

    # Integridade no banco: domínios fechados (RN02, RF05) e índice do catálogo (RF10, RNF03)
    __table_args__ = (
        db.CheckConstraint(sql_in("status_operacional", VALID_STATUSES), name="ck_animals_status_operacional"),
        db.CheckConstraint(sql_in("sexo", SEXOS), name="ck_animals_sexo"),
        db.CheckConstraint(sql_in("porte", PORTES), name="ck_animals_porte"),
        db.CheckConstraint("peso_kg IS NULL OR peso_kg > 0", name="ck_animals_peso_kg_positivo"),
        # Catálogo: WHERE is_deleted = false ORDER BY created_at DESC (paginado)
        db.Index("ix_animals_is_deleted_created_at", "is_deleted", "created_at"),
    )

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
    
    # RN03: Proibição de exclusão física (Soft Delete). No PostgreSQL um gatilho também bloqueia DELETE.
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    # Relacionamentos. RN03/RN06: sem cascata de exclusão. O histórico do animal nunca é apagado
    # junto com ele (nem o próprio animal: a exclusão é lógica, por `is_deleted`).
    # `passive_deletes="all"` impede o SQLAlchemy de apagar ou desvincular os filhos.
    vaccinations = db.relationship("Vaccination", backref="animal", lazy="dynamic", passive_deletes="all")
    medical_records = db.relationship("MedicalRecord", backref="animal", lazy="dynamic", passive_deletes="all")
    prescriptions = db.relationship("Prescription", backref="animal", lazy="dynamic", passive_deletes="all")
    adoption = db.relationship("Adoption", backref="animal", uselist=False, passive_deletes="all")

    @classmethod
    def can_transition(cls, atual, novo):
        """Máquina de estados (RN02).

        Entre os status ativos qualquer troca é permitida, e 'óbito' é possível a partir de qualquer
        um deles. 'adotado' só é alcançado pelo registro formal de adoção (RN04), e 'adotado' e
        'óbito' são finais (RN05).
        """
        if atual in (cls.STATUS_ADOTADO, cls.STATUS_OBITO) or novo == atual:
            return False
        if novo == cls.STATUS_ADOTADO:
            return False
        return novo in cls.VALID_STATUSES

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
            "is_microchipado": self.is_microchipado,
            "is_idoso": self.is_idoso,
            "cuidados_especiais": self.cuidados_especiais,
            "localizacao_baia": self.localizacao_baia,
            "codigo_identificador": self.codigo_identificador,
            "status_operacional": self.status_operacional,
            "congelado": self.is_frozen,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
