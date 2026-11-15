from flask import jsonify, request
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from app.models import Animal, Announcement, AnnouncementAck
from app.extensions import db
from app.utils.audit import log_audit_event
from app.utils.validation import ApiError, clean_text, get_payload, model_text, parse_bool, parse_int, require_choice
from . import avisos_bp

TIPOS = ["TURNO", "DIRETORIA"]


@avisos_bp.route("", methods=["GET"])
@login_required
def list_avisos():
    """Mural: avisos fixados primeiro e os 50 mais recentes. Filtros opcionais: tipo, animal_id."""
    query = Announcement.query
    tipo = request.args.get("tipo", "").strip().upper()
    if tipo:
        query = query.filter(Announcement.tipo == require_choice(tipo, "tipo", TIPOS))
    animal_id = request.args.get("animal_id", type=int)
    if animal_id is not None:
        query = query.filter(Announcement.animal_id == animal_id)

    ordem = (Announcement.created_at.desc(), Announcement.id.desc())
    fixados = query.filter(Announcement.is_fixado.is_(True)).order_by(*ordem).all()
    recentes = query.filter(Announcement.is_fixado.is_(False)).order_by(*ordem).limit(50).all()
    avisos = fixados + recentes

    confirmados = set()
    if avisos:
        confirmados = {aid for (aid,) in db.session.query(AnnouncementAck.announcement_id).filter(
            AnnouncementAck.user_id == current_user.id,
            AnnouncementAck.announcement_id.in_([a.id for a in avisos])).all()}
    items = [dict(a.to_dict(), confirmado_por_mim=a.id in confirmados) for a in avisos]
    return jsonify({"avisos": items}), 200


@avisos_bp.route("", methods=["POST"])
@login_required
def create_aviso():
    data = get_payload()
    tipo = require_choice(clean_text(data, "tipo", default="TURNO").upper(), "tipo", TIPOS)
    conteudo = clean_text(data, "conteudo")
    if not conteudo:
        return jsonify({"erro": "conteudo obrigatorio", "mensagem": "Escreva o conteúdo do aviso."}), 400
    if tipo == "DIRETORIA" and not current_user.is_admin:
        return jsonify({"erro": "Apenas administradora pode publicar comunicado da diretoria"}), 403

    animal_id = parse_int(data.get("animal_id"), "animal_id", minimo=1)
    if animal_id is not None and not Animal.query.filter_by(id=animal_id, is_deleted=False).first():
        raise ApiError("Animal não encontrado", 400, "O animal indicado no aviso não existe.")

    ann = Announcement(
        tipo=tipo,
        titulo=model_text(data, Announcement, "titulo"),
        conteudo=conteudo,
        categoria=model_text(data, Announcement, "categoria", default="Geral"),
        is_urgente=parse_bool(data.get("is_urgente", False)),
        is_fixado=parse_bool(data.get("is_fixado", False)),
        autor_id=current_user.id,
        animal_id=animal_id,
    )
    db.session.add(ann)
    db.session.flush()
    log_audit_event(
        acao="AVISO_PUBLICADO",
        entidade="Announcement",
        entidade_id=ann.id,
        detalhes=f"Aviso {tipo} publicado: {(ann.titulo or conteudo)[:80]}",
        commit=False,
    )
    db.session.commit()
    return jsonify({"sucesso": True, "aviso": ann.to_dict()}), 201


@avisos_bp.route("/<int:aviso_id>/confirmar", methods=["POST"])
@login_required
def confirmar_aviso(aviso_id):
    ann = db.get_or_404(Announcement, aviso_id)
    data = get_payload()
    tipo_confirmacao = (model_text(data, AnnouncementAck, "tipo_confirmacao", default="CIENTE")).upper()
    existing = AnnouncementAck.query.filter_by(announcement_id=aviso_id, user_id=current_user.id).first()
    if existing:
        return jsonify({"sucesso": True, "ja_confirmado": True}), 200
    ack = AnnouncementAck(announcement_id=ann.id, user_id=current_user.id, tipo_confirmacao=tipo_confirmacao)
    try:
        db.session.add(ack)
        db.session.flush()
        log_audit_event(
            acao="AVISO_CONFIRMADO",
            entidade="AnnouncementAck",
            entidade_id=ack.id,
            detalhes=f"Confirmação '{tipo_confirmacao}' no aviso {aviso_id}",
            commit=False,
        )
        db.session.commit()
    except IntegrityError:
        # Duas confirmações simultâneas: a UNIQUE (aviso, usuária) deixa passar só a primeira
        db.session.rollback()
        return jsonify({"sucesso": True, "ja_confirmado": True}), 200
    return jsonify({"sucesso": True, "confirmacao": ack.to_dict()}), 201
