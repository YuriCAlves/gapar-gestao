"""cp-04: microchip ISO de 15 digitos em animals (RN21)

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-27 18:10:00

CP-04 (docs/sdd/CP03_05_FASE2_SPEC.md, REQ-38). Migração ADITIVA e reversível, só em `animals`:

1. Coluna `numero_microchip VARCHAR(15) NULL`. As linhas antigas ficam com NULL: o legado
   `is_microchipado = true` sem número continua válido até o número ser lido.
2. CHECK `ck_animals_numero_microchip_formato` em SQL ANSI (sem regex proprietária, igual nos
   dois bancos): NULL ou exatamente 15 dígitos ASCII.
3. Índice único simples `uq_animals_numero_microchip` (D1: o cão devolvido é o mesmo registro, então
   não existe "outro ciclo" do mesmo animal disputando o número). Vários NULL são permitidos nos
   dois bancos. Também serve à busca do leitor USB.

Nenhuma tabela nova, então não há RLS novo (o de `animals` vem da 0002).

O downgrade recusa (RuntimeError) se algum animal tiver número de microchip: ele só existe nesta
coluna (o booleano `is_microchipado` não guarda o número).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


COLUNA = "numero_microchip"
CHECK_NOME = "ck_animals_numero_microchip_formato"
CHECK_CONDICAO = (
    "numero_microchip IS NULL OR (length(numero_microchip) = 15 "
    "AND ltrim(numero_microchip, '0123456789') = '')"
)
INDICE_UNICO = "uq_animals_numero_microchip"

# Sem tabela nova nesta migração. Lido por tests/test_cp01_migracoes.py::test_toda_tabela_tem_rls.
TABELAS_RLS = []


def upgrade():
    # A coluna entra antes do CHECK que a usa. `batch_alter_table` recria a tabela no SQLite
    # (que não tem ALTER TABLE ADD CONSTRAINT) e emite ALTER TABLE comum no PostgreSQL.
    with op.batch_alter_table("animals", schema=None) as batch_op:
        batch_op.add_column(sa.Column(COLUNA, sa.String(length=15), nullable=True))

    with op.batch_alter_table("animals", schema=None) as batch_op:
        batch_op.create_check_constraint(CHECK_NOME, CHECK_CONDICAO)

    op.create_index(INDICE_UNICO, "animals", [COLUNA], unique=True)


def downgrade():
    # Recusa em vez de perder dado: o número do microchip só existe nesta coluna.
    conexao = op.get_bind()
    com_numero = conexao.execute(sa.text(
        "SELECT COUNT(*) FROM animals WHERE numero_microchip IS NOT NULL"
    )).scalar()
    if com_numero:
        raise RuntimeError(
            f"Downgrade da 0006 recusado: {com_numero} animal(is) com numero_microchip preenchido. "
            "Reverter agora apagaria esses números. Faça backup e limpe a coluna de propósito "
            "antes de reverter."
        )

    op.drop_index(INDICE_UNICO, table_name="animals")

    with op.batch_alter_table("animals", schema=None) as batch_op:
        batch_op.drop_constraint(CHECK_NOME, type_="check")

    with op.batch_alter_table("animals", schema=None) as batch_op:
        batch_op.drop_column(COLUNA)
