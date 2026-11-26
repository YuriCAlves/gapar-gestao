import os
import base64
import hashlib
import hmac
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from flask import current_app

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------------------------
# Tokens do Google (RNF08). Inalterado no CP-01: continua na chave derivada de FERNET_KEY ou
# SECRET_KEY, para que os tokens já gravados sigam legíveis (SDD v5.1, R2).
# ---------------------------------------------------------------------------------------------

def get_fernet_instance() -> Fernet:
    """Obtém ou instancia o Fernet com base na chave de configuração ou derivada do SECRET_KEY."""
    custom_key = None
    if current_app:
        custom_key = current_app.config.get("FERNET_KEY") or current_app.config.get("SECRET_KEY")
    if not custom_key:
        custom_key = os.getenv("FERNET_KEY") or os.getenv("SECRET_KEY", "gapar-fallback-secret-key-default-2026")

    # Garante chave url-safe base64 de 32 bytes (256 bits)
    derived_bytes = hashlib.sha256(custom_key.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(derived_bytes)
    return Fernet(fernet_key)


def encrypt_token(raw_token: str | None) -> str | None:
    """Cifra um token antes de salvar no banco de dados (RNF08)."""
    if not raw_token:
        return None
    f = get_fernet_instance()
    return f.encrypt(raw_token.encode("utf-8")).decode("utf-8")


def decrypt_token(cipher_text: str | None) -> str | None:
    """Decifra um token armazenado no banco de dados (RNF08)."""
    if not cipher_text:
        return None
    try:
        f = get_fernet_instance()
        return f.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except Exception:
        # Se falhar (ex: texto antigo não criptografado ou chave alterada)
        return None


# ---------------------------------------------------------------------------------------------
# Dados pessoais (PII): CPF, telefone da lista sigilosa e endereço do adotante (CP-01).
#
# Chaves separadas das dos tokens Google, de propósito: trocar a SECRET_KEY (para derrubar
# sessões) não pode tornar CPFs ilegíveis. Duas peças:
#   - MultiFernet(PII_FERNET_KEYS): cifra reversível. A 1ª chave cifra; as demais só decifram,
#     o que permite rotacionar sem perder dados antigos.
#   - Índice cego HMAC-SHA256(PII_HMAC_KEY): valor determinístico para busca exata (RN15) sem
#     decifrar a tabela inteira. O prefixo de domínio impede cruzar CPF com telefone.
# ---------------------------------------------------------------------------------------------

VERSAO_INDICE = "v1"
DOMINIOS_INDICE = ("cpf", "tel", "nome", "rl")


class ChavePiiInvalida(ValueError):
    """Configuração de chave PII ausente ou em formato inválido."""


def _chave_dev(rotulo: str) -> str:
    """Chave estável derivada da SECRET_KEY, só para desenvolvimento e testes."""
    segredo = (current_app.config.get("SECRET_KEY") if current_app else None) or "gapar-dev"
    return hashlib.sha256(f"gapar-pii-dev:{rotulo}:{segredo}".encode("utf-8")).hexdigest()


def _ambiente_permite_chave_dev() -> bool:
    return bool(current_app and (current_app.config.get("TESTING") or current_app.debug))


def _avisar_chave_dev(nome):
    if not current_app.extensions.get(f"gapar_aviso_{nome}"):
        current_app.extensions[f"gapar_aviso_{nome}"] = True
        current_app.logger.warning("%s não configurada: usando chave derivada (só desenvolvimento).", nome)


def chaves_fernet_pii() -> tuple[str, ...]:
    bruto = (current_app.config.get("PII_FERNET_KEYS") or "").strip() if current_app else ""
    if bruto:
        return tuple(c.strip() for c in bruto.split(",") if c.strip())
    if _ambiente_permite_chave_dev():
        _avisar_chave_dev("PII_FERNET_KEYS")
        return (base64.urlsafe_b64encode(bytes.fromhex(_chave_dev("fernet"))).decode("ascii"),)
    raise ChavePiiInvalida("PII_FERNET_KEYS não configurada.")


def chave_hmac_pii() -> bytes:
    bruto = (current_app.config.get("PII_HMAC_KEY") or "").strip() if current_app else ""
    if bruto:
        return bruto.encode("utf-8")
    if _ambiente_permite_chave_dev():
        _avisar_chave_dev("PII_HMAC_KEY")
        return _chave_dev("hmac").encode("utf-8")
    raise ChavePiiInvalida("PII_HMAC_KEY não configurada.")


@lru_cache(maxsize=8)
def _multifernet(chaves: tuple[str, ...]) -> MultiFernet:
    try:
        return MultiFernet([Fernet(c.encode("ascii")) for c in chaves])
    except (ValueError, TypeError) as exc:
        raise ChavePiiInvalida("PII_FERNET_KEYS contém chave Fernet inválida.") from exc


def problemas_chaves_pii(config) -> list[str]:
    """Validação usada na subida da produção (lá não existe chave derivada de desenvolvimento)."""
    erros = []
    chaves = [c.strip() for c in (config.get("PII_FERNET_KEYS") or "").split(",") if c.strip()]
    if not chaves:
        erros.append("PII_FERNET_KEYS ausente (chave Fernet para cifrar CPF e telefone).")
    else:
        try:
            for chave in chaves:
                Fernet(chave.encode("ascii"))
        except (ValueError, TypeError):
            erros.append("PII_FERNET_KEYS contém chave Fernet inválida.")
    hmac_key = (config.get("PII_HMAC_KEY") or "").strip()
    if len(hmac_key) < 32:
        erros.append("PII_HMAC_KEY ausente ou curta (mínimo de 32 caracteres aleatórios).")
    elif parece_valor_de_exemplo(hmac_key):
        # Com a chave conhecida, um atacante com acesso ao banco recalcula o índice de todos os
        # ~10^9 CPFs possíveis e descobre quem está na lista sigilosa.
        erros.append("PII_HMAC_KEY ainda é o valor de exemplo do .env.example: gere um segredo novo.")
    return erros


# Trechos que só aparecem nos valores de exemplo (.env.example, documentação, testes).
_MARCAS_DE_EXEMPLO = ("substitua", "seu-", "sua-", "exemplo", "example", "changeme", "chave-secreta",
                      "dev-chave", "teste-gapar", "1x0000000000")


def parece_valor_de_exemplo(valor: str | None) -> bool:
    """True para segredos copiados do `.env.example` ou da documentação, que nunca valem em produção."""
    texto = (valor or "").strip().lower()
    return any(marca in texto for marca in _MARCAS_DE_EXEMPLO)


def cifrar_pii(texto: str | None) -> str | None:
    """Cifra um dado pessoal com a chave PII primária. Vazio -> None."""
    if not texto:
        return None
    return _multifernet(chaves_fernet_pii()).encrypt(texto.encode("utf-8")).decode("ascii")


def decifrar_pii(cifra: str | None) -> str | None:
    """Decifra um dado pessoal. Falha (chave perdida ou dado adulterado) -> None, com erro no log."""
    if not cifra:
        return None
    try:
        return _multifernet(chaves_fernet_pii()).decrypt(cifra.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        # Nunca registrar a cifra nem o conteúdo: só o fato.
        _log.error("Falha ao decifrar dado pessoal: chave PII ausente/errada ou dado adulterado.")
        return None


def recifrar_pii(cifra: str | None) -> str | None:
    """Recifra com a chave primária atual (rotação de PII_FERNET_KEYS)."""
    if not cifra:
        return None
    return _multifernet(chaves_fernet_pii()).rotate(cifra.encode("ascii")).decode("ascii")


def indice_cego(dominio: str, valor_normalizado: str | None) -> str | None:
    """HMAC-SHA256 hexadecimal (64 caracteres) de `<dominio>:v1:<valor>`. Vazio -> None."""
    if dominio not in DOMINIOS_INDICE:
        raise ValueError(f"Domínio de índice cego desconhecido: {dominio}")
    if not valor_normalizado:
        return None
    mensagem = f"{dominio}:{VERSAO_INDICE}:{valor_normalizado}".encode("utf-8")
    return hmac.new(chave_hmac_pii(), mensagem, hashlib.sha256).hexdigest()
