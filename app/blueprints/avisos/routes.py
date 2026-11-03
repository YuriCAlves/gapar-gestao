from flask import jsonify, request
from flask_login import login_required, current_user
from app.models import Announcement, AnnouncementAck
from app.extensions import db
from . import avisos_bp


@avisos_bp.route("", methods=["GET"])
@login_required
def list_avisos():
    fixados = Announcement.query.filter_by(is_fixado=True).order_by(Announcement.created_at.desc()).all()
    recentes = Announcement.query.filter_by(is_fixado=False).order_by(Announcement.created_at.desc()).limit(50).all()
    items = [a.to_dict() for a in fixados + recentes]
    return jsonify({"avisos": items}), 200


@avisos_bp.route("", methods=["POST"])
@login_required
def create_aviso():
    data = request.get_json(silent=True) or {}
    tipo = data.get("tipo", "TURNO")
    conteudo = data.get("conteudo")
    if not conteudo:
        return jsonify({"erro": "conteudo obrigatorio"}), 400
    if tipo == "DIRETORIA" and not current_user.is_admin:
        return jsonify({"erro": "Apenas administradora pode publicar comunicado da diretoria"}), 403
    ann = Announcement(
        tipo=tipo,
        titulo=data.get("titulo"),
        conteudo=conteudo,
        categoria=data.get("categoria", "Geral"),
        is_urgente=bool(data.get("is_urgente", False)),
        is_fixado=bool(data.get("is_fixado", False)),
        autor_id=current_user.id,
        animal_id=data.get("animal_id"),
    )
    db.session.add(ann)
    db.session.commit()
    return jsonify({"sucesso": True, "aviso": ann.to_dict()}), 201


@avisos_bp.route("/<int:aviso_id>/confirmar", methods=["POST"])
@login_required
def confirmar_aviso(aviso_id):
    ann = Announcement.query.get_or_404(aviso_id)
    data = request.get_json(silent=True) or {}
    tipo_confirmacao = data.get("tipo_confirmacao", "CIENTE")
    existing = AnnouncementAck.query.filter_by(announcement_id=aviso_id, user_id=current_user.id).first()
    if existing:
        return jsonify({"sucesso": True, "ja_confirmado": True}), 200
    ack = AnnouncementAck(
        announcement_id=aviso_id,
        user_id=current_user.id,
        tipo_confirmacao=tipo_confirmacao,
    )
    db.session.add(ack)
    db.session.commit()
    return jsonify({"sucesso": True, "confirmacao": ack.to_dict()}), 201
