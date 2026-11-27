"""cp-02: vitrine publica em animals (RN17)

Revision ID: 0004
Revises: 0003a
Create Date: 2026-11-27 10:00:00

CP-02 (docs/sdd/CP02_VITRINE_SPEC.md, REQ-21 e REQ-23). Migração ADITIVA e reversível, só em
`animals`:

1. Colunas `is_publicado` (NOT NULL, default false), `slug_publico` (VARCHAR(40), nulo),
   `descricao_publica` (TEXT, nulo) e `pausar_candidaturas` (NOT NULL, default false).
   O `server_default` preenche as linhas antigas: nenhum animal nasce publicado.
2. CHECK `ck_animals_publicado_so_disponivel`: publicado só com status 'disponível', não excluído e com slug (RN17).
3. Índice único `uq_animals_slug_publico` (vários NULL são permitidos nos dois bancos) e índice
   `ix_animals_vitrine (is_deleted, is_publicado, status_operacional, created_at)`.

Nenhuma tabela nova, então não há RLS novo (o de `animals` vem da 0002).

O downgrade recusa (RuntimeError) se algum animal tiver dado de vitrine: o slug é o link já
divulgado e a descrição é texto escrito pela Administradora, que só existem nestas colunas.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003a'
branch_labels = None
depends_on = None


STATUS_DISPONIVEL = "disponível"

# (coluna, tipo, nullable, server_default)
COLUNAS = [
    ("is_publicado", sa.Boolean(), False, sa.false()),
    ("slug_publico", sa.String(length=40), True, None),
    ("descricao_publica", sa.Text(), True, None),
    ("pausar_candidaturas", sa.Boolean(), False, sa.false()),
]

CHECK_NOME = "ck_animals_publicado_so_disponivel"
# `NOT <booleano>` vale no PostgreSQL e no SQLite (onde o booleano é 0/1).
CHECK_CONDICAO = f"NOT is_publicado OR (status_operacional = '{STATUS_DISPONIVEL}' AND NOT is_deleted AND slug_publico IS NOT NULL)"

# (nome, colunas, único)
INDICES = [
    ("uq_animals_slug_publico", ["slug_publico"], True),
    ("ix_animals_vitrine", ["is_deleted", "is_publicado", "status_operacional", "created_at"], False),
]

# Sem tabela nova nesta migração. Lido por tests/test_cp01_migracoes.py::test_toda_tabela_tem_rls.
TABELAS_RLS = []


def upgrade():
    # `batch_alter_table` recria a tabela no SQLite (que não tem ALTER TABLE ADD CONSTRAINT) e
    # emite ALTER TABLE comum no PostgreSQL. As colunas entram antes do CHECK que as usa.
    with op.batch_alter_table("animals", schema=None) as batch_op:
        for coluna, tipo, nulo, padrao in COLUNAS:
            batch_op.add_column(sa.Column(coluna, tipo, nullable=nulo, server_default=padrao))

    with op.batch_alter_table("animals", schema=None) as batch_op:
        batch_op.create_check_constraint(CHECK_NOME, CHECK_CONDICAO)

    for nome, colunas, unico in INDICES:
        op.create_index(nome, "animals", colunas, unique=unico)


def downgrade():
    # Recusa em vez de perder dado: slug (link divulgado), descrição e flags só existem aqui.
    conexao = op.get_bind()
    com_dados = conexao.execute(sa.text(
        "SELECT COUNT(*) FROM animals WHERE is_publicado = true OR pausar_candidaturas = true "
        "OR slug_publico IS NOT NULL OR descricao_publica IS NOT NULL"
    )).scalar()
    if com_dados:
        raise RuntimeError(
            f"Downgrade da 0004 recusado: {com_dados} animal(is) com dados da vitrine pública "
            "(is_publicado, slug_publico, descricao_publica ou pausar_candidaturas). Reverter agora "
            "apagaria esses dados. Faça backup e limpe as colunas de propósito antes de reverter."
        )

    for nome, _, _ in reversed(INDICES):
        op.drop_index(nome, table_name="animals")

    with op.batch_alter_table("animals", schema=None) as batch_op:
        batch_op.drop_constraint(CHECK_NOME, type_="check")

    with op.batch_alter_table("animals", schema=None) as batch_op:
        for coluna, _, _, _ in reversed(COLUNAS):
            batch_op.drop_column(coluna)
