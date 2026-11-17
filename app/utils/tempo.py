"""Data e hora no fuso do abrigo.

O servidor de produção roda em UTC. Sem este módulo, o "dia atual" do painel Hoje, da vigência
das prescrições (RN09) e da baixa de medicação (RF16) viraria às 21h do horário de Brasília.
`APP_TIMEZONE` define o fuso (padrão America/Sao_Paulo); vazio significa "relógio do servidor",
que é o que os testes automatizados usam.
"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app

# O Brasil não adota horário de verão desde 2019: UTC-3 é um substituto seguro se a base de
# fusos (pacote tzdata) não estiver instalada no servidor.
_FUSO_RESERVA = timezone(timedelta(hours=-3))


def fuso():
    """Fuso configurado, ou None para usar o relógio local do servidor."""
    nome = (current_app.config.get("APP_TIMEZONE") or "").strip()
    if not nome:
        return None
    try:
        return ZoneInfo(nome)
    except (ZoneInfoNotFoundError, ValueError):
        current_app.logger.warning("Fuso horário '%s' indisponível; usando UTC-3.", nome)
        return _FUSO_RESERVA


def agora() -> datetime:
    """Data e hora atuais no fuso do abrigo."""
    return datetime.now(fuso())


def hoje() -> date:
    """Dia atual no fuso do abrigo (RF23, RN09)."""
    return agora().date()


def agora_utc() -> datetime:
    """Instante atual em UTC, com fuso explícito."""
    return datetime.now(timezone.utc)


def utc_para_local(momento: datetime | None) -> datetime | None:
    """Converte um `created_at` (UTC sem tzinfo) para o fuso do abrigo, com o deslocamento explícito."""
    if momento is None:
        return None
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(fuso())


def inicio_do_dia_em_utc(dia: date) -> datetime:
    """Meia-noite de `dia` no fuso do abrigo, convertida para UTC sem tzinfo.

    Serve para filtrar colunas `created_at`, que são gravadas em UTC sem fuso.
    """
    meia_noite = datetime.combine(dia, time.min)
    tz = fuso()
    local = meia_noite.replace(tzinfo=tz) if tz else meia_noite.astimezone()
    return local.astimezone(timezone.utc).replace(tzinfo=None)
