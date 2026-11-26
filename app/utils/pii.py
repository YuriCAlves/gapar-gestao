"""Normalização e validação de dados pessoais (CPF e telefone), decisão D2 do CP-01.

A normalização define o que entra no índice cego: precisa ser exatamente a mesma na gravação e
na busca, senão a RN15 deixa de reconhecer a pessoa. `normalizar_nome` reproduz a comparação que
a RN15 sempre usou (minúsculas e espaços colapsados), para não mudar o resultado da regra.
"""
import re

_NAO_DIGITO = re.compile(r"\D")


def so_digitos(valor) -> str:
    return _NAO_DIGITO.sub("", str(valor)) if valor else ""


def normalizar_cpf(valor) -> str:
    return so_digitos(valor)


def normalizar_telefone(valor) -> str:
    return so_digitos(valor)


def normalizar_nome(valor) -> str:
    return " ".join(str(valor or "").lower().split())


def cpf_valido(valor) -> bool:
    """11 dígitos, não todos iguais e com os dois dígitos verificadores corretos (módulo 11)."""
    d = so_digitos(valor)
    if len(d) != 11 or len(set(d)) == 1:
        return False
    numeros = [int(x) for x in d]
    for n in (9, 10):
        soma = sum(numeros[i] * (n + 1 - i) for i in range(n))
        if (soma * 10) % 11 % 10 != numeros[n]:
            return False
    return True


def telefone_valido(valor) -> bool:
    """10 (fixo) ou 11 (celular, 3º dígito 9) dígitos, com DDD de 11 a 99."""
    d = so_digitos(valor)
    if len(d) not in (10, 11) or not (11 <= int(d[:2]) <= 99):
        return False
    return len(d) == 10 or d[2] == "9"


def formatar_cpf(valor) -> str | None:
    """`00000000000` -> `000.000.000-00`. Valor legado fora do padrão volta como veio."""
    if not valor:
        return None
    d = so_digitos(valor)
    if len(d) != 11:
        return valor
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
