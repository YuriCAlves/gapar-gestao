"""Superfície pública da API (`/api/public/*`), sem login (CP-01).

Regras para QUALQUER rota deste arquivo (verificadas por `tests/test_canary_anti_leak.py`):
- nunca serializar modelo com `to_dict()`: só `to_public_dict()` ou campos montados à mão;
- nunca ler `current_user` nem a sessão (a resposta precisa ser igual para todos e cacheável);
- leituras com `@cache_publico`; escritas com Turnstile + `rate_limit_service` (CPs seguintes).
"""
from flask import Blueprint, current_app, jsonify, request

from app.models.animal import Animal
from app.utils.publico import BLUEPRINT_PUBLICO, cache_publico, flags_publicas, require_feature

public_bp = Blueprint(BLUEPRINT_PUBLICO, __name__, url_prefix="/api/public")


@public_bp.route("/config", methods=["GET"])
@cache_publico(segundos=60, revalidar=300, navegador=30)
def config_publica():
    """Configuração do site público: módulos liberados, chave do Turnstile e WhatsApp da ONG."""
    whatsapp = "".join(ch for ch in (current_app.config.get("PUBLIC_WHATSAPP_ADOCAO") or "") if ch.isdigit())
    return jsonify({
        "flags": flags_publicas(),
        "turnstile_site_key": (current_app.config.get("TURNSTILE_SITE_KEY") or "").strip() or None,
        "whatsapp_adocao": whatsapp or None,
    })


# Vitrine (CP-02, REQ-27/REQ-28, RN17) -------------------------------------------------------

POR_PAGINA_VITRINE = 12
PAGINA_MAXIMA_VITRINE = 500


def _nao_encontrado():
    """404 único da vitrine: o mesmo corpo para slug inexistente, despublicado ou indisponível.

    `@cache_publico` marca a resposta com `no-store`, então ela nunca fica no cache da CDN.
    """
    return jsonify({"erro": "Recurso não encontrado", "codigo": 404,
                    "mensagem": "A rota ou registro solicitado não existe."}), 404


def _pagina_da_query():
    """`?pagina=N` com N de 1 a 500 (só dígitos ASCII); ausente = 1; qualquer outra coisa = None."""
    bruto = request.args.get("pagina")
    if bruto is None:
        return 1
    if not (bruto.isascii() and bruto.isdigit()) or len(bruto) > 3:
        return None
    pagina = int(bruto)
    return pagina if 1 <= pagina <= PAGINA_MAXIMA_VITRINE else None


# RN17 x cache de CDN: um cão que sai de "disponível" some do banco na hora, mas a CDN pode
# servir a cópia antiga até expirar. Janelas curtas limitam isso a ~2 min (lista) e ~1 min
# (detalhe), ainda absorvendo picos de acesso. O 404 nunca é cacheado.
@public_bp.route("/animais", methods=["GET"])
@cache_publico(segundos=120, revalidar=60)
@require_feature("vitrine")
def vitrine():
    """Lista da vitrine (`PaginaVitrine`): 12 por página, mais recentes primeiro.

    Duas consultas por requisição (a página e o total), sem relacionamentos: sem N+1.
    """
    pagina = _pagina_da_query()
    if pagina is None:
        return jsonify({"erro": "Requisição inválida", "codigo": 400,
                        "mensagem": f"O parâmetro 'pagina' deve ser um número de 1 a {PAGINA_MAXIMA_VITRINE}."}), 400
    inicio = (pagina - 1) * POR_PAGINA_VITRINE
    animais = Animal.query_vitrine().offset(inicio).limit(POR_PAGINA_VITRINE).all()
    total = Animal.query_vitrine().order_by(None).count()
    return jsonify({
        "animais": [animal.to_public_dict() for animal in animais],
        "pagina": pagina,
        "por_pagina": POR_PAGINA_VITRINE,
        "total": total,
        "tem_mais": inicio + len(animais) < total,
    })


@public_bp.route("/animais/<slug>", methods=["GET"])
@cache_publico(segundos=60, revalidar=60)
@require_feature("vitrine")
def animal_publico(slug):
    """Animal da vitrine pelo slug (`RespostaAnimalPublico`), ou o 404 único da vitrine.

    Slug fora de `^[a-z0-9-]{3,40}$` nem chega ao banco (`Animal.buscar_publicado`).
    """
    animal = Animal.buscar_publicado(slug)
    if animal is None:
        return _nao_encontrado()
    return jsonify({"animal": animal.to_public_dict()})
