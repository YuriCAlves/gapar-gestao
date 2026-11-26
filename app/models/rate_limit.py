from app.extensions import db


class RateLimitBucket(db.Model):
    """Contador de requisições por janela fixa para as rotas públicas (CP-01).

    `bucket_key` = "<ação>:<HMAC do identificador>": o IP nunca é guardado em claro.
    Atualizado só por `rate_limit_service.consumir` (upsert atômico).
    """
    __tablename__ = "rate_limit_buckets"

    bucket_key = db.Column(db.String(120), primary_key=True)
    window_start = db.Column(db.DateTime, nullable=False)
    hit_count = db.Column(db.Integer, nullable=False, default=0)
