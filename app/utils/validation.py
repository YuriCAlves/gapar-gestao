"""Erros de API padronizados e validadores de entrada (Checkpoint 3)."""
from datetime import date


class ApiError(Exception):
    """Erro de regra de negócio/validação convertido em JSON `{"erro", "codigo", "mensagem"}`."""

    def __init__(self, erro, status=400, mensagem=None, **extra):
        super().__init__(erro)
        self.erro = erro
        self.status = status
        self.mensagem = mensagem
        self.extra = extra

    def to_response(self):
        body = {"erro": self.erro, "codigo": self.status}
        if self.mensagem:
            body["mensagem"] = self.mensagem
        body.update(self.extra)
        return body, self.status


def parse_date(value, campo, default=None):
    """Converte 'AAAA-MM-DD' em date. Vazio -> default; formato inválido -> 400 (nunca ignora em silêncio)."""
    if value in (None, ""):
        return default
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ApiError("Data inválida", 400, f"O campo '{campo}' deve estar no formato AAAA-MM-DD.")


def parse_float(value, campo, minimo=None):
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "."))
    except ValueError:
        raise ApiError("Número inválido", 400, f"O campo '{campo}' deve ser numérico.")
    if minimo is not None and number < minimo:
        raise ApiError("Número inválido", 400, f"O campo '{campo}' deve ser maior que {minimo}.")
    return number


def parse_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "sim", "on", "yes")


def require_choice(value, campo, opcoes):
    if value not in opcoes:
        raise ApiError("Valor inválido", 400, f"O campo '{campo}' deve ser um de: {', '.join(opcoes)}.", permitidos=list(opcoes))
    return value
