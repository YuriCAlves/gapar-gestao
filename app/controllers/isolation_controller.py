"""Isolamento sanitário (CP-05, REQ-42, RN22). Flag "isolamento" (desligada -> 404).

Arquivo próprio (e não dentro de animals/health) para que a flag e a regra RN22 fiquem num
lugar só; as URLs seguem o contrato (`/api/animais/:id/isolamentos` e
`/api/isolamentos/:id/encerrar`). Qualquer perfil logado abre e encerra.

- Abrir: 409 se já houver isolamento aberto (checagem + índice único parcial na corrida);
  422 se o animal estiver congelado (RN05) ou excluído.
- Encerrar: UPDATE condicional `WHERE fim_real IS NULL`; 409 se já estiver encerrado (inclusive
  na corrida de dois encerramentos). Encerrar é permitido mesmo com a ficha congelada: um animal
  que foi a óbito isolado precisa sair da lista de isolamentos abertos do painel.
- RN17 ampliada: abrir não mexe em `is_publicado` (ver app/models/isolation.py).
A auditoria guarda só os ids (o motivo é texto livre e fica fora dela).
"""
import sqlalchemy as sa
from flask import Blueprint, jsonify
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.animal import Animal
from app.models.base import utcnow
from app.models.isolation import IsolationRecord
from app.services.audit import log_audit_event
from app.utils import tempo
from app.utils.publico import require_feature
from app.utils.validation import ApiError, clean_text, get_payload, model_text, parse_date

isolation_bp = Blueprint("isolation", __name__)


def _ja_aberto():
    return ApiError("Isolamento já aberto", 409,
                    "Este animal já está em isolamento; encerre o atual antes de abrir outro (RN22).")


@isolation_bp.route("/api/animais/<int:animal_id>/isolamentos", methods=["GET"])
@require_feature("isolamento")
def listar_isolamentos(animal_id):
    Animal.query.filter_by(id=animal_id, is_deleted=False).first_or_404()
    registros = IsolationRecord.query_do_animal(animal_id).all()
    return jsonify({"isolamentos": [r.to_dict() for r in registros]}), 200


@isolation_bp.route("/api/animais/<int:animal_id>/isolamentos", methods=["POST"])
@require_feature("isolamento")
def abrir_isolamento(animal_id):
    animal = db.get_or_404(Animal, animal_id)
    if animal.is_deleted:
        raise ApiError("Animal excluído", 422, "Não é possível isolar um animal excluído.")
    if animal.is_frozen:
        raise ApiError("Ficha congelada", 422,
                       f"O animal está com status '{animal.status_operacional}'; a ficha não pode ser alterada (RN05).")

    data = get_payload()
    motivo = model_text(data, IsolationRecord, "motivo", obrigatorio=True)
    protocolo = clean_text(data, "protocolo_cuidados")
    hoje = tempo.hoje()
    data_inicio = parse_date(data.get("data_inicio"), "data_inicio", default=hoje)
    if data_inicio > hoje:
        raise ApiError("Data inválida", 400, "A data de início do isolamento não pode ser futura.")
    data_fim_prevista = parse_date(data.get("data_fim_prevista"), "data_fim_prevista")
    if data_fim_prevista and data_fim_prevista < data_inicio:
        raise ApiError("Data inválida", 400, "A data prevista de fim não pode ser anterior ao início.")

    if IsolationRecord.aberto_do_animal(animal.id) is not None:
        raise _ja_aberto()

    registro = IsolationRecord(
        animal_id=animal.id, motivo=motivo, protocolo_cuidados=protocolo,
        data_inicio=data_inicio, data_fim_prevista=data_fim_prevista,
        aberto_por_user_id=current_user.id,
    )
    try:
        with db.session.begin_nested():
            db.session.add(registro)
            db.session.flush()
    except IntegrityError:
        # Corrida: outra requisição abriu entre a checagem e o INSERT; o índice único parcial
        # `uq_isolation_aberto_por_animal` recusou o segundo aberto (RN22).
        raise _ja_aberto()

    log_audit_event(acao="ISOLAMENTO_ABERTO", entidade="IsolationRecord", entidade_id=registro.id,
                    detalhes=f"Isolamento #{registro.id} aberto para o animal #{animal.id}", commit=False)
    db.session.commit()
    # O commit expira o animal; `isolamento_aberto_registro` é recarregado na próxima leitura.
    return jsonify({"isolamento": registro.to_dict()}), 201


@isolation_bp.route("/api/isolamentos/<int:isolamento_id>/encerrar", methods=["POST"])
@require_feature("isolamento")
def encerrar_isolamento(isolamento_id):
    registro = db.get_or_404(IsolationRecord, isolamento_id)
    if registro.animal is None or registro.animal.is_deleted:
        raise ApiError("Recurso não encontrado", 404, "A rota ou registro solicitado não existe.")
    data = get_payload()
    observacoes = clean_text(data, "observacoes_alta")

    resultado = db.session.execute(
        sa.update(IsolationRecord)
        .where(IsolationRecord.id == registro.id, IsolationRecord.fim_real.is_(None))
        .values(fim_real=utcnow(), encerrado_por_user_id=current_user.id, observacoes_alta=observacoes)
        .execution_options(synchronize_session=False)
    )
    if resultado.rowcount != 1:
        raise ApiError("Isolamento já encerrado", 409, "Este isolamento já foi encerrado.")

    log_audit_event(acao="ISOLAMENTO_ENCERRADO", entidade="IsolationRecord", entidade_id=registro.id,
                    detalhes=f"Isolamento #{registro.id} do animal #{registro.animal_id} encerrado", commit=False)
    db.session.commit()
    db.session.refresh(registro)
    return jsonify({"isolamento": registro.to_dict()}), 200
