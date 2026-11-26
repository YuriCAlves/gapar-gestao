"""fase 0: colunas de PII cifrada, indices cegos e rate_limit_buckets

Revision ID: 0003a
Revises: 0002
Create Date: 2026-11-26 18:00:00

CP-01 (docs/sdd/CP01_NUCLEO_SPEC.md). Migração ADITIVA e reversível:

1. `non_eligible_people`: cpf_cifrado, cpf_bidx, telefone_cifrado, telefone_bidx, nome_bidx.
2. `adoptions`: adotante_cpf_cifrado, adotante_cpf_bidx, adotante_endereco_cifrado.
3. Tabela `rate_limit_buckets` (limite de requisições das rotas públicas).
4. PostgreSQL: RLS ligado na tabela nova, sem políticas (fecha a Data API do Supabase).

Esta migração NÃO cifra nem apaga nada. A cifragem dos dados existentes é feita pelo comando
`flask pii-backfill`, e a remoção das colunas em claro (`cpf`, `telefone`, `adotante_cpf`,
`adotante_endereco`) fica para a migração `0003b`, aplicada só depois de o backfill ser
conferido em produção e de um backup do banco.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003a'
down_revision = '0002'
branch_labels = None
depends_on = None


# (tabela, coluna, tipo, indexada)
COLUNAS = [
    ("non_eligible_people", "nome_bidx", sa.String(64), True),
    ("non_eligible_people", "cpf_cifrado", sa.Text(), False),
    ("non_eligible_people", "cpf_bidx", sa.String(64), True),
    ("non_eligible_people", "telefone_cifrado", sa.Text(), False),
    ("non_eligible_people", "telefone_bidx", sa.String(64), True),
    ("adoptions", "adotante_cpf_cifrado", sa.Text(), False),
    ("adoptions", "adotante_cpf_bidx", sa.String(64), True),
    ("adoptions", "adotante_endereco_cifrado", sa.Text(), False),
]

# Tabelas criadas por esta migração (todas com RLS). Lido por tests/test_cp01_migracoes.py.
TABELAS_RLS = ["rate_limit_buckets"]


def _is_postgres():
    return op.get_context().dialect.name == "postgresql"


def _nome_indice(tabela, coluna):
    return f"ix_{tabela}_{coluna}"


def upgrade():
    tabelas = sorted({t for t, _, _, _ in COLUNAS})
    for tabela in tabelas:
        with op.batch_alter_table(tabela, schema=None) as batch_op:
            for t, coluna, tipo, _ in COLUNAS:
                if t == tabela:
                    batch_op.add_column(sa.Column(coluna, tipo, nullable=True))

    for tabela, coluna, _, indexada in COLUNAS:
        if indexada:
            op.create_index(_nome_indice(tabela, coluna), tabela, [coluna], unique=False)

    op.create_table(
        "rate_limit_buckets",
        sa.Column("bucket_key", sa.String(length=120), nullable=False),
        sa.Column("window_start", sa.DateTime(), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("bucket_key"),
    )

    if _is_postgres():
        for tabela in TABELAS_RLS:
            op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY")


# (tabela, coluna cifrada, coluna legada em claro): o downgrade só é seguro se toda cifra
# tiver cópia em claro. Registros gravados depois da 0003a existem só cifrados.
PARES_CIFRA_LEGADO = [
    ("non_eligible_people", "cpf_cifrado", "cpf"),
    ("non_eligible_people", "telefone_cifrado", "telefone"),
    ("adoptions", "adotante_cpf_cifrado", "adotante_cpf"),
    ("adoptions", "adotante_endereco_cifrado", "adotante_endereco"),
]


def downgrade():
    # Recusa em vez de perder dado: um CPF gravado depois da 0003a só existe na coluna cifrada.
    conexao = op.get_bind()
    for tabela, cifrado, legado in PARES_CIFRA_LEGADO:
        so_cifrados = conexao.execute(sa.text(
            f"SELECT COUNT(*) FROM {tabela} WHERE {cifrado} IS NOT NULL AND {legado} IS NULL"
        )).scalar()
        if so_cifrados:
            raise RuntimeError(
                f"Downgrade da 0003a recusado: {so_cifrados} registro(s) de {tabela} existem só "
                f"cifrados ({cifrado}). Reverter agora apagaria esses dados."
            )

    op.drop_table("rate_limit_buckets")

    for tabela, coluna, _, indexada in reversed(COLUNAS):
        if indexada:
            op.drop_index(_nome_indice(tabela, coluna), table_name=tabela)

    tabelas = sorted({t for t, _, _, _ in COLUNAS})
    for tabela in tabelas:
        with op.batch_alter_table(tabela, schema=None) as batch_op:
            for t, coluna, _, _ in reversed(COLUNAS):
                if t == tabela:
                    batch_op.drop_column(coluna)
