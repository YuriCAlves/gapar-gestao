"""RN15: conferência do interessado contra a lista sigilosa de não aptos (CP-01).

A busca é por índice cego (igualdade de HMAC), sem decifrar a tabela. O resultado é o mesmo da
versão anterior: CPF -> telefone -> nome normalizado, nessa ordem de prioridade.

Durante a transição (antes do `flask pii-backfill`), registros antigos ainda não têm índice e
continuam sendo conferidos pelo valor em claro, para a RN15 nunca falhar em silêncio. Depois do
backfill esse conjunto fica vazio.
"""
from sqlalchemy import and_, or_

from app.models.blacklist import NonEligiblePerson
from app.utils.crypto import indice_cego
from app.utils.pii import normalizar_cpf, normalizar_nome, normalizar_telefone

MOTIVO_CPF = "CPF constante na lista de não aptos"
MOTIVO_TELEFONE = "Telefone constante na lista de não aptos"
MOTIVO_NOME = "Nome idêntico constante na lista de não aptos"

P = NonEligiblePerson

# Registros com algum dado ainda sem índice cego (anteriores ao backfill)
SEM_INDICE = or_(
    P.nome_bidx.is_(None),
    and_(P.cpf_legado.isnot(None), P.cpf_bidx.is_(None)),
    and_(P.telefone_legado.isnot(None), P.telefone_bidx.is_(None)),
)


def procurar(nome=None, cpf=None, telefone=None):
    """Devolve `(motivo, registro)` do primeiro impedimento encontrado, ou `(None, None)`."""
    cpf_n = normalizar_cpf(cpf)
    tel_n = normalizar_telefone(telefone)
    nome_n = normalizar_nome(nome)
    alvos = (
        (P.cpf_bidx, indice_cego("cpf", cpf_n), MOTIVO_CPF),
        (P.telefone_bidx, indice_cego("tel", tel_n), MOTIVO_TELEFONE),
        (P.nome_bidx, indice_cego("nome", nome_n), MOTIVO_NOME),
    )

    condicoes = [coluna == alvo for coluna, alvo, _ in alvos if alvo]
    candidatos = P.query.filter(or_(*condicoes)).all() if condicoes else []
    for coluna, alvo, motivo in alvos:  # respeita a prioridade CPF -> telefone -> nome
        for item in candidatos:
            if alvo and getattr(item, coluna.key) == alvo:
                return motivo, item

    for item in P.query.filter(SEM_INDICE).all():
        if cpf_n and item.cpf_legado and normalizar_cpf(item.cpf_legado) == cpf_n:
            return MOTIVO_CPF, item
        if tel_n and item.telefone_legado and normalizar_telefone(item.telefone_legado) == tel_n:
            return MOTIVO_TELEFONE, item
        if nome_n and item.nome_bidx is None and nome_n == normalizar_nome(item.nome):
            return MOTIVO_NOME, item
    return None, None


def motivo_de_bloqueio(nome, cpf, telefone):
    """Atalho do registro de adoção: só o motivo interno (nunca vai para a resposta)."""
    return procurar(nome, cpf, telefone)[0]


def buscar_exato(cpf=None, telefone=None):
    """D2: busca da Administradora por CPF OU telefone completos (já normalizados)."""
    if cpf:
        coluna_bidx, coluna_legado, alvo, normalizar, valor = (
            P.cpf_bidx, P.cpf_legado, indice_cego("cpf", cpf), normalizar_cpf, cpf)
    else:
        coluna_bidx, coluna_legado, alvo, normalizar, valor = (
            P.telefone_bidx, P.telefone_legado, indice_cego("tel", telefone), normalizar_telefone, telefone)

    achados = P.query.filter(coluna_bidx == alvo).all()
    legados = P.query.filter(coluna_bidx.is_(None), coluna_legado.isnot(None)).all()
    achados += [item for item in legados if normalizar(getattr(item, coluna_legado.key)) == valor]
    return achados
