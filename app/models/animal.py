from datetime import date

import sqlalchemy as sa
from sqlalchemy.orm import validates

from app.extensions import db
from app.utils.slug import slug_valido
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
        # CP-02 (REQ-23, RN17): o banco recusa animal publicado fora de 'disponível'.
        # `NOT <booleano>` vale nos dois dialetos (no SQLite o booleano é 0/1).
        db.CheckConstraint(f"NOT is_publicado OR (status_operacional = '{STATUS_DISPONIVEL}' AND NOT is_deleted AND slug_publico IS NOT NULL)",
                           name="ck_animals_publicado_so_disponivel"),
        # CP-02 (REQ-21): vitrine pública e link /adote/<slug>
        db.Index("ix_animals_vitrine", "is_deleted", "is_publicado", "status_operacional", "created_at"),
        db.Index("uq_animals_slug_publico", "slug_publico", unique=True),
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

    # Vitrine pública (CP-02, RN17). Só a Administradora publica (PATCH /api/animais/<id>/vitrine).
    # O slug nasce na primeira publicação e nunca é apagado: republicar mantém o mesmo link.
    is_publicado = db.Column(db.Boolean, default=False, server_default=sa.false(), nullable=False)
    slug_publico = db.Column(db.String(40), nullable=True)
    descricao_publica = db.Column(db.Text, nullable=True)
    pausar_candidaturas = db.Column(db.Boolean, default=False, server_default=sa.false(), nullable=False)

    # Relacionamentos. RN03/RN06: sem cascata de exclusão. O histórico do animal nunca é apagado
    # junto com ele (nem o próprio animal: a exclusão é lógica, por `is_deleted`).
    # `passive_deletes="all"` impede o SQLAlchemy de apagar ou desvincular os filhos.
    vaccinations = db.relationship("Vaccination", backref="animal", lazy="dynamic", passive_deletes="all")
    medical_records = db.relationship("MedicalRecord", backref="animal", lazy="dynamic", passive_deletes="all")
    prescriptions = db.relationship("Prescription", backref="animal", lazy="dynamic", passive_deletes="all")
    adoption = db.relationship("Adoption", backref="animal", uselist=False, passive_deletes="all")

    # RN17 (REQ-22): ao deixar de estar 'disponível' ou ser excluído logicamente, o animal sai da
    # vitrine na mesma transação, qualquer que seja a rota (status, adoção, óbito, exclusão).
    # `@validates` roda em toda atribuição pelo ORM; o CHECK `ck_animals_publicado_so_disponivel`
    # cobre o que escapar disso (SQL direto, UPDATE em massa). O `slug_publico` é mantido.
    @validates("status_operacional")
    def _rn17_status(self, _chave, novo_status):
        if novo_status != self.STATUS_DISPONIVEL and self.is_publicado:
            self.is_publicado = False
        return novo_status

    @validates("is_deleted")
    def _rn17_exclusao(self, _chave, excluido):
        if excluido and self.is_publicado:
            self.is_publicado = False
        return excluido

    @classmethod
    def _filtro_vitrine(cls):
        return (
            cls.is_deleted.is_(False),
            cls.is_publicado.is_(True),
            cls.status_operacional == cls.STATUS_DISPONIVEL,
        )

    @classmethod
    def query_vitrine(cls):
        """Animais da vitrine: publicados, 'disponível', não excluídos; mais recentes primeiro."""
        return cls.query.filter(*cls._filtro_vitrine()).order_by(cls.created_at.desc(), cls.id.desc())

    @classmethod
    def buscar_publicado(cls, slug):
        """Animal da vitrine pelo slug público, ou None (mesmo critério de `query_vitrine`).

        Slug fora de `^[a-z0-9-]{3,40}$` devolve None sem consultar o banco.
        """
        if not slug_valido(slug):
            return None
        return cls.query.filter(cls.slug_publico == slug, *cls._filtro_vitrine()).first()

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

    # Superfície pública (CP-01/CP-02): ÚNICOS atributos que podem sair para visitantes sem login.
    # Origem do resgate, motivo, baia, código interno e cuidados de saúde nunca saem.
    # Qualquer campo novo aqui exige revisão e passa pelo teste canário anti-vazamento.
    PUBLIC_ANIMAL_STRICT_KEYS = (
        "nome", "sexo", "porte", "idade_estimada", "raca", "pelagem", "foto_url",
        "is_castrado", "is_idoso", "slug_publico", "descricao_publica", "pausar_candidaturas",
    )
    # Atributo do modelo -> nome no contrato `AnimalPublico` (app/views/src/types/contratos.ts).
    # Atributos ausentes daqui saem com o próprio nome.
    PUBLIC_ANIMAL_RENOMES = {
        "slug_publico": "slug",
        "pausar_candidaturas": "candidaturas_pausadas",
    }

    def to_public_dict(self):
        """Serialização para visitantes sem login (`AnimalPublico`): só `PUBLIC_ANIMAL_STRICT_KEYS`."""
        return {
            self.PUBLIC_ANIMAL_RENOMES.get(campo, campo): getattr(self, campo)
            for campo in self.PUBLIC_ANIMAL_STRICT_KEYS
        }

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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            # CP-02 (REQ-25, `CamposVitrineDaFicha`)
            "is_publicado": bool(self.is_publicado),
            "slug_publico": self.slug_publico,
            "descricao_publica": self.descricao_publica,
            "pausar_candidaturas": bool(self.pausar_candidaturas),
        }
