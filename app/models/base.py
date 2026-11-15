"""Auxiliares compartilhados pelos modelos: relógio UTC, CHECKs de domínio e proteções RN03/RN16.

As regras de integridade são declaradas nos modelos para valerem em qualquer banco
(inclusive no SQLite dos testes, criado com `db.create_all()`). O PostgreSQL recebe ainda
gatilhos equivalentes pela migração `0002`, que protegem também contra SQL direto.
"""
from datetime import datetime, timezone

from sqlalchemy import event
from sqlalchemy.orm import object_session


def utcnow():
    """Data/hora atual em UTC, sem fuso (mesmo valor do antigo `datetime.utcnow()`).

    As colunas continuam `DateTime` sem fuso (timestamp without time zone), guardando UTC.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def sql_in(coluna, valores):
    """Monta a expressão `coluna IN ('a', 'b', ...)` usada nos CHECKs de domínio fechado."""
    lista = ", ".join("'" + str(v).replace("'", "''") + "'" for v in valores)
    return f"{coluna} IN ({lista})"


# Perfis de acesso válidos (RF03, RN13). Usados em `users.role` e `whitelist.role`.
PERFIS = ("Administradora", "Voluntaria")


class ExclusaoFisicaProibida(Exception):
    """RN03: registros de animais, prontuários e vacinas nunca são apagados fisicamente."""


class AuditoriaImutavel(Exception):
    """RN16: a trilha de auditoria não pode ser alterada nem apagada."""


def proibir_exclusao_fisica(modelo):
    """Impede `session.delete()` de registros do modelo (RN03). Use exclusão lógica."""

    @event.listens_for(modelo, "before_delete")
    def _bloquear(mapper, connection, target):
        raise ExclusaoFisicaProibida(
            f"Exclusão física proibida em '{modelo.__tablename__}' (RN03)."
        )

    return modelo


def tornar_imutavel(modelo):
    """Impede alteração e exclusão de registros do modelo depois de gravados (RN16)."""

    @event.listens_for(modelo, "before_update")
    def _bloquear_alteracao(mapper, connection, target):
        sessao = object_session(target)
        if sessao is None or sessao.is_modified(target, include_collections=False):
            raise AuditoriaImutavel(
                f"Registros de '{modelo.__tablename__}' são imutáveis (RN16)."
            )

    @event.listens_for(modelo, "before_delete")
    def _bloquear_exclusao(mapper, connection, target):
        raise AuditoriaImutavel(
            f"Registros de '{modelo.__tablename__}' são imutáveis (RN16)."
        )

    return modelo
