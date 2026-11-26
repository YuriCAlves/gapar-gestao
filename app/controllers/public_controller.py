"""Superfície pública da API (`/api/public/*`), sem login (CP-01).

Regras para QUALQUER rota deste arquivo (verificadas por `tests/test_canary_anti_leak.py`):
- nunca serializar modelo com `to_dict()`: só `to_public_dict()` ou campos montados à mão;
- nunca ler `current_user` nem a sessão (a resposta precisa ser igual para todos e cacheável);
- leituras com `@cache_publico`; escritas com Turnstile + `rate_limit_service` (CPs seguintes).
"""
from flask import Blueprint, current_app, jsonify

from app.utils.publico import BLUEPRINT_PUBLICO, cache_publico, flags_publicas

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
