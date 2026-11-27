"""cp-05: isolamento sanitario (RN22, RN03, RN17 ampliada)

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-27 18:20:00

CP-05 (docs/sdd/CP03_05_FASE2_SPEC.md, REQ-41). Migração ADITIVA e reversível: só cria a tabela
`isolation_records`, não toca em nenhuma existente.

1. Tabela `isolation_records` (SDD §4.2-5), com CHECK `data_fim_prevista >= data_inicio` e motivo
   preenchido.
2. RN22: índice único PARCIAL `uq_isolation_aberto_por_animal ON (animal_id) WHERE fim_real IS
   NULL`, com `postgresql_where` e `sqlite_where` (sem o segundo, o SQLite criaria um UNIQUE global
   e o animal nunca poderia ser isolado de novo).
3. Índices do histórico (`animal_id, data_inicio`) e das FKs de usuárias.
4. Somente no PostgreSQL:
   - RN03 (sem DELETE/TRUNCATE), reaproveitando `gapar_bloquear_exclusao_fisica()` da 0002;
   - RLS ligado, sem políticas.

A RN17 ampliada (isolado fora da vitrine) é uma condição de consulta (`Animal._filtro_vitrine`),
não uma coluna: nada muda em `animals`.

O downgrade recusa (RuntimeError) se houver qualquer isolamento registrado: o histórico sanitário
só existe nesta tabela.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


TABELA = "isolation_records"

# Tabelas criadas por esta migração (todas com RLS). Lido por tests/test_cp01_migracoes.py.
TABELAS_RLS = [TABELA]

FILTRO_ABERTO = "fim_real IS NULL"

# (nome, colunas)
INDICES = [
    ("ix_isolation_records_animal_inicio", ["animal_id", "data_inicio"]),
    ("ix_isolation_records_aberto_por_user_id", ["aberto_por_user_id"]),
    ("ix_isolation_records_encerrado_por_user_id", ["encerrado_por_user_id"]),
]
INDICE_RN22 = "uq_isolation_aberto_por_animal"


def _is_postgres():
    return op.get_context().dialect.name == "postgresql"


def upgrade():
    op.create_table(
        TABELA,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("animal_id", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.String(length=200), nullable=False),
        sa.Column("protocolo_cuidados", sa.Text(), nullable=True),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim_prevista", sa.Date(), nullable=True),
        sa.Column("fim_real", sa.DateTime(), nullable=True),
        sa.Column("aberto_por_user_id", sa.Integer(), nullable=True),
        sa.Column("encerrado_por_user_id", sa.Integer(), nullable=True),
        sa.Column("observacoes_alta", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("data_fim_prevista IS NULL OR data_fim_prevista >= data_inicio",
                           name="ck_isolation_records_fim_previsto"),
        sa.CheckConstraint("length(ltrim(motivo)) > 0", name="ck_isolation_records_motivo_preenchido"),
        sa.ForeignKeyConstraint(["animal_id"], ["animals.id"]),
        sa.ForeignKeyConstraint(["aberto_por_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["encerrado_por_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(INDICE_RN22, TABELA, ["animal_id"], unique=True,
                    postgresql_where=sa.text(FILTRO_ABERTO), sqlite_where=sa.text(FILTRO_ABERTO))
    for nome, colunas in INDICES:
        op.create_index(nome, TABELA, colunas, unique=False)

    if _is_postgres():
        op.execute(
            f"CREATE TRIGGER trg_{TABELA}_sem_delete BEFORE DELETE ON {TABELA} "
            f"FOR EACH ROW EXECUTE FUNCTION gapar_bloquear_exclusao_fisica()"
        )
        op.execute(
            f"CREATE TRIGGER trg_{TABELA}_sem_truncate BEFORE TRUNCATE ON {TABELA} "
            f"FOR EACH STATEMENT EXECUTE FUNCTION gapar_bloquear_exclusao_fisica()"
        )
        for tabela in TABELAS_RLS:
            op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY")


def downgrade():
    # Recusa em vez de perder dado: o histórico sanitário só existe nesta tabela.
    conexao = op.get_bind()
    linhas = conexao.execute(sa.text(f"SELECT COUNT(*) FROM {TABELA}")).scalar()
    if linhas:
        raise RuntimeError(
            f"Downgrade da 0007 recusado: {linhas} isolamento(s) em {TABELA}. Reverter agora "
            "apagaria o histórico sanitário (RN03). Faça backup e esvazie a tabela de propósito "
            "antes de reverter."
        )

    # A função `gapar_bloquear_exclusao_fisica()` é da 0002 e fica.
    if _is_postgres():
        op.execute(f"DROP TRIGGER IF EXISTS trg_{TABELA}_sem_truncate ON {TABELA}")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{TABELA}_sem_delete ON {TABELA}")

    for nome, _ in reversed(INDICES):
        op.drop_index(nome, table_name=TABELA)
    op.drop_index(INDICE_RN22, table_name=TABELA)

    op.drop_table(TABELA)
