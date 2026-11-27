"""cp-03: estoque de insumos com lotes FEFO (RN18, RN19, RN20)

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-27 18:00:00

CP-03 (docs/sdd/CP03_05_FASE2_SPEC.md, REQ-32 e REQ-33). Migração ADITIVA e reversível: só cria
tabelas novas, não toca em nenhuma existente.

1. `inventory_items`: insumo. CHECK de categoria, unidade, `estoque_minimo >= 0` e nome preenchido.
2. `inventory_batches`: lote. `saldo_atual NUMERIC(10,2) CHECK >= 0` (RN18), `UNIQUE(item_id,
   codigo_lote)` e índice FEFO `ix_batches_fefo (item_id, data_validade, id)`.
3. `inventory_movements`: movimento imutável (RN19). CHECK de tipo, `quantidade > 0`,
   `saldo_apos >= 0` e motivo preenchido. FKs opcionais para animals, vaccinations e
   medication_logs; `user_id ON DELETE SET NULL`.
4. Somente no PostgreSQL:
   - RN03 (sem DELETE/TRUNCATE) em inventory_items e inventory_batches, reaproveitando a função
     `gapar_bloquear_exclusao_fisica()` da 0002;
   - RN19 (sem UPDATE/DELETE/TRUNCATE) em inventory_movements, com a função nova
     `gapar_bloquear_mutacao_registro_imutavel()`;
   - RLS ligado nas três tabelas, sem políticas (fecha a Data API do Supabase).

As listas de valores ficam copiadas aqui de propósito: uma migração não depende dos modelos.
SQL em `op.execute` sem dois-pontos seguidos de nome e sem sinal de porcentagem (passa por
`sqlalchemy.text()`).

O downgrade recusa (RuntimeError) se houver qualquer linha nas tabelas novas: itens, lotes, saldos
e movimentos só existem aqui. O RLS não é desligado (as tabelas somem no downgrade).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


CATEGORIAS = "'Vacina', 'Medicamento', 'Vermífugo', 'Antipulgas', 'Ração', 'Insumo Clínico', 'Limpeza'"
UNIDADES = "'doses', 'comprimidos', 'ml', 'kg', 'unidades'"
TIPOS = "'ENTRADA', 'SAIDA_USO', 'AJUSTE_MAIS', 'AJUSTE_MENOS', 'DESCARTE_VALIDADE', 'PERDA'"

# Tabelas criadas por esta migração (todas com RLS). Lido por tests/test_cp01_migracoes.py.
# Ordem de criação (o downgrade apaga na ordem inversa, filhos primeiro).
TABELAS_RLS = ["inventory_items", "inventory_batches", "inventory_movements"]

# RN03 no PostgreSQL (função da 0002)
TABELAS_SEM_EXCLUSAO = ["inventory_items", "inventory_batches"]
# RN19 no PostgreSQL (função nova)
TABELAS_IMUTAVEIS = ["inventory_movements"]

# (tabela, nome, colunas)
INDICES = [
    ("inventory_items", "ix_inventory_items_listagem", ["is_deleted", "categoria", "nome"]),
    ("inventory_batches", "ix_batches_fefo", ["item_id", "data_validade", "id"]),
    ("inventory_movements", "ix_inventory_movements_batch_created", ["batch_id", "created_at"]),
    ("inventory_movements", "ix_inventory_movements_animal_id", ["animal_id"]),
    ("inventory_movements", "ix_inventory_movements_vaccination_id", ["vaccination_id"]),
    ("inventory_movements", "ix_inventory_movements_medication_log_id", ["medication_log_id"]),
    ("inventory_movements", "ix_inventory_movements_user_id", ["user_id"]),
]

# Mesmo padrão das funções da 0002: `SET search_path = ''` e ERRCODE restrict_violation (23001),
# que chega ao SQLAlchemy como IntegrityError e o app converte em 422.
FUNCAO_IMUTAVEL = """
CREATE OR REPLACE FUNCTION gapar_bloquear_mutacao_registro_imutavel()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $gapar$
BEGIN
    RAISE EXCEPTION USING
        ERRCODE = 'restrict_violation',
        MESSAGE = 'RN19: registro imutável na tabela ' || TG_TABLE_NAME || ' (' || TG_OP || ').',
        HINT = 'Movimentos de estoque só aceitam INSERT. Correções entram como um novo ajuste.';
END;
$gapar$
"""


def _is_postgres():
    return op.get_context().dialect.name == "postgresql"


def upgrade():
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("categoria", sa.String(length=30), nullable=False),
        sa.Column("unidade", sa.String(length=20), nullable=False),
        sa.Column("estoque_minimo", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(f"categoria IN ({CATEGORIAS})", name="ck_inventory_items_categoria"),
        sa.CheckConstraint(f"unidade IN ({UNIDADES})", name="ck_inventory_items_unidade"),
        sa.CheckConstraint("estoque_minimo >= 0", name="ck_inventory_items_estoque_minimo"),
        sa.CheckConstraint("length(ltrim(nome)) > 0", name="ck_inventory_items_nome_preenchido"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "inventory_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("codigo_lote", sa.String(length=60), nullable=False),
        sa.Column("data_validade", sa.Date(), nullable=True),
        sa.Column("saldo_atual", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("saldo_atual >= 0", name="ck_inventory_batches_saldo_nao_negativo"),
        sa.CheckConstraint("length(ltrim(codigo_lote)) > 0", name="ck_inventory_batches_codigo_preenchido"),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("item_id", "codigo_lote", name="uq_inventory_batches_item_lote"),
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("quantidade", sa.Numeric(10, 2), nullable=False),
        sa.Column("saldo_apos", sa.Numeric(10, 2), nullable=False),
        sa.Column("motivo", sa.String(length=255), nullable=False),
        sa.Column("animal_id", sa.Integer(), nullable=True),
        sa.Column("vaccination_id", sa.Integer(), nullable=True),
        sa.Column("medication_log_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(f"tipo IN ({TIPOS})", name="ck_inventory_movements_tipo"),
        sa.CheckConstraint("quantidade > 0", name="ck_inventory_movements_quantidade_positiva"),
        sa.CheckConstraint("saldo_apos >= 0", name="ck_inventory_movements_saldo_apos"),
        sa.CheckConstraint("length(ltrim(motivo)) > 0", name="ck_inventory_movements_motivo_preenchido"),
        sa.ForeignKeyConstraint(["batch_id"], ["inventory_batches.id"]),
        sa.ForeignKeyConstraint(["animal_id"], ["animals.id"]),
        sa.ForeignKeyConstraint(["vaccination_id"], ["vaccinations.id"]),
        sa.ForeignKeyConstraint(["medication_log_id"], ["medication_logs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    for tabela, nome, colunas in INDICES:
        op.create_index(nome, tabela, colunas, unique=False)

    if _is_postgres():
        op.execute(FUNCAO_IMUTAVEL)

        for tabela in TABELAS_SEM_EXCLUSAO:
            op.execute(
                f"CREATE TRIGGER trg_{tabela}_sem_delete BEFORE DELETE ON {tabela} "
                f"FOR EACH ROW EXECUTE FUNCTION gapar_bloquear_exclusao_fisica()"
            )
            op.execute(
                f"CREATE TRIGGER trg_{tabela}_sem_truncate BEFORE TRUNCATE ON {tabela} "
                f"FOR EACH STATEMENT EXECUTE FUNCTION gapar_bloquear_exclusao_fisica()"
            )

        for tabela in TABELAS_IMUTAVEIS:
            op.execute(
                f"CREATE TRIGGER trg_{tabela}_imutavel BEFORE UPDATE OR DELETE ON {tabela} "
                f"FOR EACH ROW EXECUTE FUNCTION gapar_bloquear_mutacao_registro_imutavel()"
            )
            op.execute(
                f"CREATE TRIGGER trg_{tabela}_sem_truncate BEFORE TRUNCATE ON {tabela} "
                f"FOR EACH STATEMENT EXECUTE FUNCTION gapar_bloquear_mutacao_registro_imutavel()"
            )

        for tabela in TABELAS_RLS:
            op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY")


def downgrade():
    # Recusa em vez de perder dado: itens, lotes, saldos e movimentos só existem nestas tabelas.
    conexao = op.get_bind()
    for tabela in TABELAS_RLS:
        linhas = conexao.execute(sa.text(f"SELECT COUNT(*) FROM {tabela}")).scalar()
        if linhas:
            raise RuntimeError(
                f"Downgrade da 0005 recusado: {linhas} registro(s) em {tabela}. Reverter agora "
                "apagaria o estoque e o histórico imutável de movimentos (RN19). Faça backup e "
                "esvazie as tabelas de propósito antes de reverter."
            )

    # As tabelas estão vazias e vão ser apagadas: os gatilhos saem antes (o de TRUNCATE/DELETE
    # não dispara em DROP TABLE, mas tirá-los deixa o downgrade simétrico ao upgrade).
    # A função `gapar_bloquear_exclusao_fisica()` é da 0002 e fica.
    if _is_postgres():
        for tabela in TABELAS_IMUTAVEIS:
            op.execute(f"DROP TRIGGER IF EXISTS trg_{tabela}_sem_truncate ON {tabela}")
            op.execute(f"DROP TRIGGER IF EXISTS trg_{tabela}_imutavel ON {tabela}")
        for tabela in TABELAS_SEM_EXCLUSAO:
            op.execute(f"DROP TRIGGER IF EXISTS trg_{tabela}_sem_truncate ON {tabela}")
            op.execute(f"DROP TRIGGER IF EXISTS trg_{tabela}_sem_delete ON {tabela}")
        op.execute("DROP FUNCTION IF EXISTS gapar_bloquear_mutacao_registro_imutavel()")

    for tabela, nome, _ in reversed(INDICES):
        op.drop_index(nome, table_name=tabela)

    for tabela in reversed(TABELAS_RLS):
        op.drop_table(tabela)
