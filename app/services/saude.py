"""Regras de saúde compartilhadas entre o painel Hoje, a ficha do animal e os lembretes .ics."""
from collections import defaultdict

from sqlalchemy.orm import aliased

from app.extensions import db
from app.models.health import MedicationLog, Prescription, Vaccination


def split_horarios(horarios):
    """'08:00, 20:00' -> ['08:00', '20:00']."""
    return [h.strip() for h in (horarios or "").split(",") if h.strip()]


def is_prescription_active(prescricao, dia):
    """RN09: a medicação é ativa enquanto `dia` estiver entre a data inicial e a final."""
    return prescricao.data_inicio <= dia <= prescricao.data_fim


def prescription_dict(prescricao, dia):
    """`to_dict` da prescrição com `is_active` calculado no dia do abrigo (e não no do servidor)."""
    dados = prescricao.to_dict()
    dados["is_active"] = is_prescription_active(prescricao, dia)
    return dados


def logs_by_prescription(prescription_ids, dia):
    """Baixas do dia agrupadas por prescrição, em uma única consulta."""
    agrupado = defaultdict(list)
    if prescription_ids:
        logs = (MedicationLog.query
                .filter(MedicationLog.prescription_id.in_(prescription_ids), MedicationLog.data_aplicacao == dia)
                .order_by(MedicationLog.id.asc()).all())
        for log in logs:
            agrupado[log.prescription_id].append(log)
    return agrupado


def find_dose_log(prescription_id, dia, horario_previsto):
    """Baixa já registrada para a dose (prescrição + dia + horário previsto), se houver."""
    return (MedicationLog.query
            .filter_by(prescription_id=prescription_id, data_aplicacao=dia, horario_previsto=horario_previsto)
            .order_by(MedicationLog.id.asc()).first())


def _vaccine_key(nome):
    return (nome or "").strip().lower()


def open_booster_filter(dia):
    """Condição SQL: o reforço desta vacina ainda não foi atendido.

    Um reforço deixa de estar em aberto quando o mesmo animal recebe, depois, outra aplicação
    da mesma vacina (mesmo nome, sem diferenciar maiúsculas). Aplicações com data futura são
    agendamentos e não contam como atendimento.
    """
    posterior = aliased(Vaccination)
    return ~(db.session.query(posterior.id)
             .filter(posterior.animal_id == Vaccination.animal_id,
                     posterior.id != Vaccination.id,
                     db.func.lower(db.func.trim(posterior.nome_vacina)) == db.func.lower(db.func.trim(Vaccination.nome_vacina)),
                     posterior.data_aplicacao > Vaccination.data_aplicacao,
                     posterior.data_aplicacao <= dia)
             .exists())


def vaccine_dicts(vacinas, dia):
    """`to_dict` de cada vacina com a situação do reforço (mesma regra de `open_booster_filter`).

    Acrescenta `reforco_pendente` (há reforço previsto e ainda não atendido) e
    `reforco_atrasado` (pendente e com data anterior a `dia`).
    """
    aplicacoes = defaultdict(list)
    for v in vacinas:
        if v.data_aplicacao and v.data_aplicacao <= dia:
            aplicacoes[(v.animal_id, _vaccine_key(v.nome_vacina))].append((v.id, v.data_aplicacao))

    resultado = []
    for v in vacinas:
        atendido = any(outro_id != v.id and data > v.data_aplicacao
                       for outro_id, data in aplicacoes[(v.animal_id, _vaccine_key(v.nome_vacina))])
        pendente = bool(v.data_reforco) and not atendido
        dados = v.to_dict()
        dados["reforco_pendente"] = pendente
        dados["reforco_atrasado"] = pendente and v.data_reforco < dia
        resultado.append(dados)
    return resultado
