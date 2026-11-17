"""Armazenamento das fotos dos animais (RF06).

Com `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` configurados, o arquivo vai para o bucket público
do Supabase Storage. Sem eles, fica no disco local (`UPLOAD_FOLDER`), como no desenvolvimento.
Quem chama recebe apenas a URL da foto; falhas viram `ApiError`, nunca um erro 500 cru.
"""
import os

import requests
from flask import current_app

from app.utils.validation import ApiError

TEMPO_LIMITE_UPLOAD = 15  # segundos


def _supabase_config():
    base = (current_app.config.get("SUPABASE_URL") or "").strip().rstrip("/")
    chave = (current_app.config.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    bucket = (current_app.config.get("SUPABASE_STORAGE_BUCKET") or "animais").strip()
    return base, chave, bucket


def uses_supabase_storage():
    """True quando as fotos vão para o Supabase Storage."""
    base, chave, _ = _supabase_config()
    return bool(base and chave)


def save_photo(conteudo: bytes, filename: str, content_type: str = "image/jpeg") -> str:
    """Grava a foto já comprimida e devolve a URL a guardar em `foto_url`."""
    if uses_supabase_storage():
        return _save_to_supabase(conteudo, filename, content_type)
    if current_app.config.get("REQUIRE_REMOTE_STORAGE"):
        # Na Vercel o disco é temporário e /static não chega ao Flask: a foto se perderia.
        current_app.logger.error("Envio de foto recusado: Supabase Storage não configurado em produção.")
        raise ApiError("Armazenamento de fotos indisponível", 503,
                       "O envio de fotos ainda não foi configurado neste ambiente. Avise a administração.")
    return _save_to_disk(conteudo, filename)


def _save_to_supabase(conteudo, filename, content_type):
    base, chave, bucket = _supabase_config()
    try:
        resposta = requests.post(
            f"{base}/storage/v1/object/{bucket}/{filename}",
            data=conteudo,
            headers={
                "Authorization": f"Bearer {chave}",
                "apikey": chave,
                "Content-Type": content_type,
                "Cache-Control": "max-age=31536000",
                "x-upsert": "false",
            },
            timeout=TEMPO_LIMITE_UPLOAD,
        )
    except requests.RequestException as exc:
        # Só o tipo da falha vai para o log: a mensagem da exceção pode conter a URL completa.
        current_app.logger.error("Supabase Storage inacessível ao enviar foto (%s).", type(exc).__name__)
        raise ApiError("Falha ao salvar a foto", 502,
                       "Não foi possível enviar a foto para o armazenamento. Tente novamente em instantes.")

    if not 200 <= resposta.status_code < 300:
        current_app.logger.error("Supabase Storage recusou o envio da foto: HTTP %s - %s",
                                 resposta.status_code, (resposta.text or "")[:300])
        raise ApiError("Falha ao salvar a foto", 502,
                       "O armazenamento de fotos recusou o envio. Tente novamente e, se persistir, avise a administração.")

    return f"{base}/storage/v1/object/public/{bucket}/{filename}"


def _save_to_disk(conteudo, filename):
    pasta = current_app.config.get("UPLOAD_FOLDER") or os.path.join(current_app.root_path, "static", "uploads")
    try:
        os.makedirs(pasta, exist_ok=True)
        with open(os.path.join(pasta, filename), "wb") as arquivo:
            arquivo.write(conteudo)
    except OSError:
        current_app.logger.exception("Falha ao gravar a foto no disco local.")
        raise ApiError("Falha ao salvar a foto", 500,
                       "Não foi possível gravar a foto no servidor. Tente novamente e, se persistir, avise a administração.")
    return f"/static/uploads/{filename}"
