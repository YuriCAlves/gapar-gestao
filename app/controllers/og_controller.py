"""Prévia Open Graph para compartilhamento da vitrine no WhatsApp e redes sociais (CP-02 · REQ-29).

Regras de segurança e contrato:
- `og_bp = Blueprint("og", __name__)` com rota `GET /adote/<slug>` e função `preview_animal`
  (endpoint `og.preview_animal`).
- Usa exclusivamente `Animal.buscar_publicado(slug)` e `animal.to_public_dict()` — nunca `to_dict()`.
- Todos os valores interpolados no HTML passam por `markupsafe.escape`.
- `og:url` usa exclusivamente `current_app.config["PUBLIC_BASE_URL"]` (nunca `request.url_root`,
  para evitar envenenamento de cache por Host); se vazia, omite `og:url`.
- Só emite `og:image` quando `foto_url` começar explicitamente com `https://`.
- Fallback institucional (flag desligada ou animal indisponível) responde com `Cache-Control: no-store`.
- Prévia de um animal real usa cache curto de 60 s.
"""
from flask import Blueprint, Response, current_app
from markupsafe import escape

from app.models.animal import Animal
from app.utils.publico import flag_ativa

og_bp = Blueprint("og", __name__)

_TITULO_FALLBACK = "ONG GAPAR — Adoção responsável"
_DESCRICAO_FALLBACK = (
    "Conheça os cães da ONG GAPAR que esperam por um lar cheio de cuidado e respeito."
)
_LIMITE_DESCRICAO = 200


def _url_canonica(slug: str) -> str | None:
    base = (current_app.config.get("PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if not base:
        return None
    slug_limpo = (slug or "").strip().lstrip("/")
    return f"{base}/adote/{slug_limpo}" if slug_limpo else f"{base}/adote"


def _resumir_descricao(dados_publicos: dict) -> str:
    partes = [
        dados_publicos.get("sexo"),
        f"porte {dados_publicos['porte'].lower()}" if dados_publicos.get("porte") else None,
        dados_publicos.get("raca"),
        dados_publicos.get("idade_estimada"),
    ]
    resumo_ficha = " · ".join(str(p).strip() for p in partes if p and str(p).strip())
    historia = (dados_publicos.get("descricao_publica") or "").strip()

    if historia and resumo_ficha:
        texto = f"{resumo_ficha}. {historia}"
    elif historia:
        texto = historia
    elif resumo_ficha:
        texto = f"{resumo_ficha}. Disponível para adoção responsável na ONG GAPAR."
    else:
        texto = _DESCRICAO_FALLBACK

    texto = " ".join(texto.split())
    if len(texto) > _LIMITE_DESCRICAO:
        return texto[: _LIMITE_DESCRICAO - 1].rstrip() + "…"
    return texto


def _renderizar_html_og(
    *,
    titulo: str,
    descricao: str,
    url: str | None = None,
    imagem_https: str | None = None,
    cache_segundos: int | None = None,
) -> Response:
    titulo_esc = escape(titulo)
    descricao_esc = escape(descricao)

    linha_url = ""
    if isinstance(url, str) and url:
        url_esc = escape(url)
        linha_url = f'\n    <meta property="og:url" content="{url_esc}" />'

    linha_imagem = ""
    twitter_card = "summary"
    if isinstance(imagem_https, str) and imagem_https.startswith("https://"):
        imagem_esc = escape(imagem_https)
        linha_imagem = f'\n    <meta property="og:image" content="{imagem_esc}" />'
        twitter_card = "summary_large_image"

    html = f"""<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{titulo_esc}</title>
    <meta name="description" content="{descricao_esc}" />
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="ONG GAPAR" />
    <meta property="og:title" content="{titulo_esc}" />
    <meta property="og:description" content="{descricao_esc}" />{linha_url}{linha_imagem}
    <meta name="twitter:card" content="{twitter_card}" />
  </head>
  <body>
    <main>
      <h1>{titulo_esc}</h1>
      <p>{descricao_esc}</p>
    </main>
  </body>
</html>
"""
    resposta = Response(html, status=200, mimetype="text/html")
    if cache_segundos is not None and cache_segundos > 0:
        resposta.headers["Cache-Control"] = f"public, max-age={cache_segundos}"
        resposta.headers["Vercel-CDN-Cache-Control"] = (
            f"max-age={cache_segundos}, stale-while-revalidate={cache_segundos}"
        )
    else:
        resposta.headers["Cache-Control"] = "no-store"
    return resposta


@og_bp.route("/adote/<slug>", methods=["GET"])
def preview_animal(slug: str):
    """Serve metadados Open Graph mínimos para crawlers de prévia (WhatsApp, redes sociais)."""
    if not flag_ativa("vitrine"):
        return _renderizar_html_og(
            titulo=_TITULO_FALLBACK,
            descricao=_DESCRICAO_FALLBACK,
            url=_url_canonica(""),
            cache_segundos=None,
        )

    animal = Animal.buscar_publicado(slug)
    if animal is None:
        return _renderizar_html_og(
            titulo=_TITULO_FALLBACK,
            descricao=_DESCRICAO_FALLBACK,
            url=_url_canonica(""),
            cache_segundos=None,
        )

    dados = animal.to_public_dict()
    nome = (dados.get("nome") or "Cão para adoção").strip()
    foto_url = dados.get("foto_url")
    imagem_segura = foto_url if isinstance(foto_url, str) and foto_url.startswith("https://") else None

    return _renderizar_html_og(
        titulo=f"{nome} — Adote na ONG GAPAR",
        descricao=_resumir_descricao(dados),
        url=_url_canonica(dados.get("slug") or slug),
        imagem_https=imagem_segura,
        cache_segundos=60,
    )
