"""Erros de API padronizados e validadores de entrada (Checkpoint 3)."""
import re
from datetime import date

from flask import request


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


def get_payload():
    """Corpo da requisição como dicionário (JSON ou formulário). Qualquer outra forma gera 400."""
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict()
    if not isinstance(data, dict):
        raise ApiError("Requisição inválida", 400, "Envie os dados como um objeto JSON.")
    return data


def column_length(model, campo):
    """Tamanho máximo da coluna de texto no modelo, ou None quando não há limite."""
    return getattr(model.__table__.c[campo].type, "length", None)


def clean_text(data, campo, max_len=None, obrigatorio=False, default=None):
    """Texto sem espaços nas pontas. Vazio -> default; acima do limite -> 400.

    O PostgreSQL recusa texto maior que a coluna; validar aqui evita que isso vire erro 500.
    """
    valor = data.get(campo)
    if isinstance(valor, (dict, list)):
        raise ApiError("Valor inválido", 400, f"O campo '{campo}' deve ser um texto.")
    texto = "" if valor is None else str(valor).strip()
    if not texto:
        if obrigatorio:
            raise ApiError("Campo obrigatório", 400, f"O campo '{campo}' é obrigatório.")
        return default
    if max_len and len(texto) > max_len:
        raise ApiError("Texto muito longo", 400, f"O campo '{campo}' aceita no máximo {max_len} caracteres.")
    return texto


def model_text(data, model, campo, **kwargs):
    """`clean_text` usando como limite o tamanho da coluna `campo` do modelo."""
    return clean_text(data, campo, max_len=column_length(model, campo), **kwargs)


def parse_date(value, campo, default=None):
    """Converte 'AAAA-MM-DD' em date. Vazio -> default; formato inválido -> 400 (nunca ignora em silêncio)."""
    if value in (None, ""):
        return default
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ApiError("Data inválida", 400, f"O campo '{campo}' deve estar no formato AAAA-MM-DD.")


def parse_float(value, campo, minimo=None, positivo=False):
    """Número opcional (aceita vírgula decimal). `positivo=True` recusa também o zero."""
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "."))
    except ValueError:
        raise ApiError("Número inválido", 400, f"O campo '{campo}' deve ser numérico.")
    if number != number or number in (float("inf"), float("-inf")):
        raise ApiError("Número inválido", 400, f"O campo '{campo}' deve ser numérico.")
    if minimo is not None and number < minimo:
        raise ApiError("Número inválido", 400, f"O campo '{campo}' deve ser maior que {minimo}.")
    if positivo and number <= 0:
        raise ApiError("Número inválido", 400, f"O campo '{campo}' deve ser maior que zero.")
    return number


def parse_int(value, campo, minimo=None):
    """Inteiro opcional. Vazio -> None; texto não numérico ou booleano -> 400."""
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ApiError("Número inválido", 400, f"O campo '{campo}' deve ser um número inteiro.")
    try:
        number = int(str(value).strip())
    except ValueError:
        raise ApiError("Número inválido", 400, f"O campo '{campo}' deve ser um número inteiro.")
    if minimo is not None and number < minimo:
        raise ApiError("Número inválido", 400, f"O campo '{campo}' deve ser no mínimo {minimo}.")
    return number


def parse_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "sim", "on", "yes")


def require_choice(value, campo, opcoes):
    if value not in opcoes:
        raise ApiError("Valor inválido", 400, f"O campo '{campo}' deve ser um de: {', '.join(opcoes)}.", permitidos=list(opcoes))
    return value


_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?)+$")


def parse_email(value, campo="email", max_len=120):
    """E-mail obrigatório, em minúsculas, com formato válido (usuario@dominio.tld)."""
    email = "" if value is None or isinstance(value, (dict, list)) else str(value).strip().lower()
    if not email:
        raise ApiError("E-mail válido é obrigatório.", 400, f"Informe o e-mail no campo '{campo}'.")
    if len(email) > max_len or ".." in email or not _EMAIL_RE.match(email):
        raise ApiError("E-mail válido é obrigatório.", 400,
                       "O e-mail informado não tem um formato válido (exemplo: nome@gmail.com).")
    return email


_HORARIO_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def is_horario(value):
    """True se o valor for um horário no formato HH:MM (24 horas)."""
    return isinstance(value, str) and bool(_HORARIO_RE.match(value))


def only_digits(value):
    """Somente os dígitos do valor (para comparar CPF e telefone sem pontuação)."""
    return re.sub(r"\D", "", str(value)) if value else ""


def _texto_simples(value, campo):
    if value is None:
        return ""
    if isinstance(value, (dict, list, bool)):
        raise ApiError("Valor inválido", 400, f"O campo '{campo}' deve ser um texto.")
    return str(value).strip()


def parse_cpf(value, campo="cpf", obrigatorio=False):
    """D2: CPF com 11 dígitos e dígito verificador válido. Devolve só os dígitos (ou None se vazio)."""
    from app.utils.pii import cpf_valido, so_digitos

    texto = _texto_simples(value, campo)
    if not texto:
        if obrigatorio:
            raise ApiError("Campo obrigatório", 400, f"O campo '{campo}' é obrigatório.")
        return None
    if re.search(r"[^\d.\-\s]", texto) or len(texto) > 20:
        raise ApiError("CPF inválido", 400, "O CPF deve conter só números (11 dígitos).")
    digitos = so_digitos(texto)
    if len(digitos) != 11:
        raise ApiError("CPF inválido", 400, "O CPF deve ter 11 dígitos.")
    if not cpf_valido(digitos):
        raise ApiError("CPF inválido", 400, "Este CPF não é válido. Confira os números.")
    return digitos


def parse_telefone(value, campo="telefone", obrigatorio=False):
    """D2: telefone com DDD, 10 (fixo) ou 11 (celular) dígitos. Devolve só os dígitos (ou None)."""
    from app.utils.pii import so_digitos, telefone_valido

    texto = _texto_simples(value, campo)
    if not texto:
        if obrigatorio:
            raise ApiError("Campo obrigatório", 400, f"O campo '{campo}' é obrigatório.")
        return None
    if re.search(r"[^\d()\-\s+]", texto) or len(texto) > 20:
        raise ApiError("Telefone inválido", 400, "O telefone deve conter só números, com DDD.")
    if not telefone_valido(so_digitos(texto)):
        raise ApiError("Telefone inválido", 400, "Informe o DDD e o número (10 ou 11 números).")
    return so_digitos(texto)
