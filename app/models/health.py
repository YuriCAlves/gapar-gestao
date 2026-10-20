from datetime import datetime, date
from app.extensions import db


class Vaccination(db.Model):
    """Cartão de Vacinação Digital (RF13)."""
    __tablename__ = "vaccinations"

    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("animals.id"), nullable=False, index=True)
    
    nome_vacina = db.Column(db.String(100), nullable=False)
    lote = db.Column(db.String(50), nullable=True)
    data_aplicacao = db.Column(db.Date, nullable=False, default=date.today)
    data_reforco = db.Column(db.Date, nullable=True, index=True)
    observacoes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "animal_id": self.animal_id,
            "nome_vacina": self.nome_vacina,
            "lote": self.lote,
            "data_aplicacao": self.data_aplicacao.isoformat() if self.data_aplicacao else None,
            "data_reforco": self.data_reforco.isoformat() if self.data_reforco else None,
            "observacoes": self.observacoes
        }


class MedicalRecord(db.Model):
    """Prontuário de Histórico Médico (RF14)."""
    __tablename__ = "medical_records"

    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("animals.id"), nullable=False, index=True)
    
    tipo_evento = db.Column(db.String(50), nullable=False) # 'Consulta', 'Exame', 'Cirurgia', 'Procedimento'
    data_evento = db.Column(db.Date, nullable=False, default=date.today)
    veterinario_responsavel = db.Column(db.String(120), nullable=True)
    clinica = db.Column(db.String(120), nullable=True)
    diagnostico = db.Column(db.Text, nullable=False)
    procedimentos_realizados = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "animal_id": self.animal_id,
            "tipo_evento": self.tipo_evento,
            "data_evento": self.data_evento.isoformat() if self.data_evento else None,
            "veterinario_responsavel": self.veterinario_responsavel,
            "clinica": self.clinica,
            "diagnostico": self.diagnostico,
            "procedimentos_realizados": self.procedimentos_realizados
        }


class Prescription(db.Model):
    """Prescrição de Medicações (RF15, RN08, RN09, RN10)."""
    __tablename__ = "prescriptions"

    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("animals.id"), nullable=False, index=True)
    
    nome_medicamento = db.Column(db.String(100), nullable=False)
    dosagem = db.Column(db.String(100), nullable=False)
    horarios = db.Column(db.String(150), nullable=False) # Ex: "08:00, 20:00"
    data_inicio = db.Column(db.Date, nullable=False, default=date.today)
    data_fim = db.Column(db.Date, nullable=False)
    instrucoes = db.Column(db.Text, nullable=True)
    
    # Sincronização Google Agenda (RF17, RN10)
    google_event_id = db.Column(db.String(150), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Baixas diárias
    logs = db.relationship("MedicationLog", backref="prescription", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def is_active(self):
        """RN09: Ativa enquanto data atual estiver entre data_inicio e data_fim."""
        today = date.today()
        return self.data_inicio <= today <= self.data_fim

    def to_dict(self):
        return {
            "id": self.id,
            "animal_id": self.animal_id,
            "nome_medicamento": self.nome_medicamento,
            "dosagem": self.dosagem,
            "horarios": self.horarios,
            "data_inicio": self.data_inicio.isoformat() if self.data_inicio else None,
            "data_fim": self.data_fim.isoformat() if self.data_fim else None,
            "instrucoes": self.instrucoes,
            "is_active": self.is_active,
            "google_event_id": self.google_event_id
        }


class MedicationLog(db.Model):
    """Registro diário de cumprimento de medicação (RF16)."""
    __tablename__ = "medication_logs"

    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey("prescriptions.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    
    data_aplicacao = db.Column(db.Date, nullable=False, default=date.today, index=True)
    horario_aplicado = db.Column(db.String(10), nullable=False) # Ex: "08:15"
    observacoes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "prescription_id": self.prescription_id,
            "user_id": self.user_id,
            "data_aplicacao": self.data_aplicacao.isoformat() if self.data_aplicacao else None,
            "horario_aplicado": self.horario_aplicado,
            "observacoes": self.observacoes,
            "created_at": self.created_at.isoformat()
        }
