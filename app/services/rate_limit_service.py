"""Limite de requisições por janela fixa, guardado no banco (CP-01).

Usado nas rotas públicas de escrita (candidatura, aceite de termo). Complementa o Firewall da
Vercel e o Turnstile; não substitui nenhum dos dois.

- Atômico: um único `INSERT ... ON CONFLICT DO UPDATE ... RETURNING` (PostgreSQL e SQLite >= 3.35),
  sem janela de corrida entre ler e gravar o contador.
- LGPD: o identificador (ex.: IP) entra só como HMAC, nunca em claro.
- Faz commit: chame no início da requisição, antes de qualquer outra alteração na sessão.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import case

from app.extensions import db
from app.models.rate_limit import RateLimitBucket
from app.utils.crypto import indice_cego


def _insert_do_dialeto():
    if db.engine.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    return insert


def _inicio_da_janela(agora: datetime, janela_segundos: int) -> datetime:
    epoca = datetime(1970, 1, 1)
    decorridos = int((agora - epoca).total_seconds())
    return epoca + timedelta(seconds=decorridos - decorridos % janela_segundos)


def chave(acao: str, identificador: str) -> str:
    return f"{acao[:50]}:{indice_cego('rl', str(identificador or '-'))}"


def consumir(acao: str, identificador: str, limite: int, janela_segundos: int, agora=None) -> bool:
    """Conta uma requisição. True = dentro do limite; False = bloquear (responder 429)."""
    agora = agora or datetime.now(timezone.utc).replace(tzinfo=None)
    inicio = _inicio_da_janela(agora, janela_segundos)
    tabela = RateLimitBucket.__table__
    insert = _insert_do_dialeto()

    stmt = insert(tabela).values(bucket_key=chave(acao, identificador), window_start=inicio, hit_count=1)
    stmt = stmt.on_conflict_do_update(
        index_elements=[tabela.c.bucket_key],
        set_={
            "hit_count": case(
                (tabela.c.window_start == stmt.excluded.window_start, tabela.c.hit_count + 1),
                else_=1,
            ),
            "window_start": stmt.excluded.window_start,
        },
    ).returning(tabela.c.hit_count)

    contagem = db.session.execute(stmt).scalar_one()
    db.session.commit()
    return contagem <= limite
