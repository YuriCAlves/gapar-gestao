"""Slug público da vitrine (CP-02, REQ-24/REQ-28).

O slug identifica o animal na URL pública (`/adote/<slug>`). Ele nunca contém o `id` interno:
é o nome normalizado mais um sufixo aleatório de `secrets`, o que impede enumerar a vitrine.
"""
import re
import secrets
import string
import unicodedata

# Formato aceito nas rotas públicas. Fora dele, o slug é recusado sem consultar o banco.
SLUG_PUBLICO_RE = re.compile(r"^[a-z0-9-]{3,40}$")

TAMANHO_MAXIMO_BASE = 24
TAMANHO_SUFIXO = 6
_ALFABETO_SUFIXO = string.ascii_lowercase + string.digits
_BASE_PADRAO = "cao"


def slug_valido(slug) -> bool:
    """True se `slug` é uma string no formato `^[a-z0-9-]{3,40}$`."""
    return isinstance(slug, str) and SLUG_PUBLICO_RE.fullmatch(slug) is not None


def normalizar_para_slug(nome) -> str:
    """Nome em minúsculas, sem acento, só `a-z0-9-`, até 24 caracteres (sem hífen nas pontas)."""
    texto = unicodedata.normalize("NFKD", str(nome or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
    return texto[:TAMANHO_MAXIMO_BASE].strip("-")


def gerar_slug_publico(nome) -> str:
    """`<nome-normalizado>-<6 caracteres aleatórios>`, por exemplo `mel-k3x9qa`.

    A unicidade é garantida pelo índice único `uq_animals_slug_publico`; quem grava deve tentar
    de novo em caso de colisão (36^6 combinações por nome tornam isso raríssimo).
    """
    base = normalizar_para_slug(nome) or _BASE_PADRAO
    sufixo = "".join(secrets.choice(_ALFABETO_SUFIXO) for _ in range(TAMANHO_SUFIXO))
    return f"{base}-{sufixo}"
