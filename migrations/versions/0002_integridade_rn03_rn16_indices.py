"""integridade no banco: dominios, dose unica, RN03, RN16 e indices

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-13 16:30:00

O que esta migração faz (tudo aditivo, sem alterar nem apagar dados):

1. CHECK de domínio fechado e de coerência de datas (RN02, RF05, RF03, RF13, RF15).
2. UNIQUE `uq_medication_logs_dose` (RF16: uma baixa por dose) e UNIQUE das confirmações de aviso.
3. Índices das consultas reais (catálogo, painel Hoje, auditoria) e das chaves estrangeiras.
4. Somente no PostgreSQL:
   - gatilhos que rejeitam DELETE/TRUNCATE em animals, medical_records e vaccinations (RN03);
   - gatilhos que rejeitam UPDATE/DELETE/TRUNCATE em audit_logs (RN16);
   - RLS ligado em todas as tabelas, sem políticas (o Flask conecta como dono das tabelas e não
     é afetado; isso fecha a Data API pública do Supabase). Já estava ligado no banco do projeto,
     mas não constava em nenhuma migração.

As listas de valores ficam copiadas aqui de propósito: uma migração não deve depender dos modelos.

Cuidado ao escrever SQL em `op.execute`: o texto passa por `sqlalchemy.text()`, então dois-pontos
seguidos de nome viram parâmetro e o sinal de porcentagem é tratado pelo driver. Por isso as
funções abaixo não usam nenhum dos dois.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


STATUS = "'em acolhimento', 'em tratamento', 'disponível', 'lar temporário', 'adotado', 'óbito'"
PERFIS = "'Administradora', 'Voluntaria'"

# (tabela, nome, condição)
CHECKS = [
    ("animals", "ck_animals_status_operacional", f"status_operacional IN ({STATUS})"),
    ("animals", "ck_animals_sexo", "sexo IN ('Macho', 'Fêmea')"),
    ("animals", "ck_animals_porte", "porte IN ('Pequeno', 'Médio', 'Grande')"),
    ("animals", "ck_animals_peso_kg_positivo", "peso_kg IS NULL OR peso_kg > 0"),
    ("users", "ck_users_role", f"role IN ({PERFIS})"),
    ("whitelist", "ck_whitelist_role", f"role IN ({PERFIS})"),
    ("prescriptions", "ck_prescriptions_periodo", "data_fim >= data_inicio"),
    ("vaccinations", "ck_vaccinations_reforco_apos_aplicacao",
     "data_reforco IS NULL OR data_reforco >= data_aplicacao"),
]

# (tabela, nome, colunas)
UNIQUES = [
    ("medication_logs", "uq_medication_logs_dose", ["prescription_id", "data_aplicacao", "horario_previsto"]),
    ("announcement_acks", "uq_announcement_acks_aviso_usuaria", ["announcement_id", "user_id"]),
]

# (tabela, nome, colunas)
INDICES = [
    # Consultas reais das rotas
    ("animals", "ix_animals_is_deleted_created_at", ["is_deleted", "created_at"]),      # catálogo paginado
    ("prescriptions", "ix_prescriptions_vigencia", ["data_fim", "data_inicio"]),        # painel Hoje
    ("audit_logs", "ix_audit_logs_acao_created_at", ["acao", "created_at"]),            # auditoria por ação
    # Chaves estrangeiras que não tinham índice
    ("adoptions", "ix_adoptions_cadastrado_por_user_id", ["cadastrado_por_user_id"]),
    ("announcements", "ix_announcements_autor_id", ["autor_id"]),
    ("announcements", "ix_announcements_animal_id", ["animal_id"]),
    ("announcement_acks", "ix_announcement_acks_user_id", ["user_id"]),
    ("medical_records", "ix_medical_records_cadastrado_por_user_id", ["cadastrado_por_user_id"]),
    ("medication_logs", "ix_medication_logs_user_id", ["user_id"]),
    ("non_eligible_people", "ix_non_eligible_people_cadastrado_por_user_id", ["cadastrado_por_user_id"]),
    ("prescriptions", "ix_prescriptions_prescrito_por_user_id", ["prescrito_por_user_id"]),
    ("vaccinations", "ix_vaccinations_aplicado_por_user_id", ["aplicado_por_user_id"]),
]

# RN03: tabelas em que a exclusão física é proibida
TABELAS_SEM_EXCLUSAO = ["animals", "medical_records", "vaccinations"]

TABELAS_RLS = [
    "alembic_version", "animals", "users", "whitelist", "adoptions", "announcements",
    "announcement_acks", "audit_logs", "medical_records", "medication_logs",
    "non_eligible_people", "prescriptions", "vaccinations",
]

# `SET search_path = ''` evita que a função resolva nomes em esquemas controlados por terceiros.
# ERRCODE restrict_violation (23001) chega ao SQLAlchemy como IntegrityError.
FUNCAO_RN03 = """
CREATE OR REPLACE FUNCTION gapar_bloquear_exclusao_fisica()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $gapar$
BEGIN
    RAISE EXCEPTION USING
        ERRCODE = 'restrict_violation',
        MESSAGE = 'RN03: exclusão física proibida na tabela ' || TG_TABLE_NAME || ' (' || TG_OP || ').',
        HINT = 'Animais usam exclusão lógica (is_deleted); prontuários e vacinas nunca são apagados.';
END;
$gapar$
"""

FUNCAO_RN16 = """
CREATE OR REPLACE FUNCTION gapar_bloquear_alteracao_auditoria()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $gapar$
BEGIN
    RAISE EXCEPTION USING
        ERRCODE = 'restrict_violation',
        MESSAGE = 'RN16: a trilha de auditoria é imutável (' || TG_OP || ' em ' || TG_TABLE_NAME || ').',
        HINT = 'audit_logs só aceita INSERT. Usuárias com registros de auditoria não podem ser apagadas, apenas desativadas na whitelist.';
END;
$gapar$
"""


def _is_postgres():
    return op.get_context().dialect.name == "postgresql"


def upgrade():
    # 1 e 2. CHECKs e UNIQUEs. `batch_alter_table` recria a tabela no SQLite (que não tem
    # ALTER TABLE ADD CONSTRAINT) e emite ALTER TABLE comum no PostgreSQL.
    tabelas = sorted({t for t, _, _ in CHECKS} | {t for t, _, _ in UNIQUES})
    for tabela in tabelas:
        with op.batch_alter_table(tabela, schema=None) as batch_op:
            for t, nome, condicao in CHECKS:
                if t == tabela:
                    batch_op.create_check_constraint(nome, condicao)
            for t, nome, colunas in UNIQUES:
                if t == tabela:
                    batch_op.create_unique_constraint(nome, colunas)

    # 3. Índices
    for tabela, nome, colunas in INDICES:
        op.create_index(nome, tabela, colunas, unique=False)

    # 4. Proteções exclusivas do PostgreSQL
    if _is_postgres():
        op.execute(FUNCAO_RN03)
        op.execute(FUNCAO_RN16)

        for tabela in TABELAS_SEM_EXCLUSAO:
            op.execute(
                f"CREATE TRIGGER trg_{tabela}_sem_delete BEFORE DELETE ON {tabela} "
                f"FOR EACH ROW EXECUTE FUNCTION gapar_bloquear_exclusao_fisica()"
            )
            op.execute(
                f"CREATE TRIGGER trg_{tabela}_sem_truncate BEFORE TRUNCATE ON {tabela} "
                f"FOR EACH STATEMENT EXECUTE FUNCTION gapar_bloquear_exclusao_fisica()"
            )

        op.execute(
            "CREATE TRIGGER trg_audit_logs_imutavel BEFORE UPDATE OR DELETE ON audit_logs "
            "FOR EACH ROW EXECUTE FUNCTION gapar_bloquear_alteracao_auditoria()"
        )
        op.execute(
            "CREATE TRIGGER trg_audit_logs_sem_truncate BEFORE TRUNCATE ON audit_logs "
            "FOR EACH STATEMENT EXECUTE FUNCTION gapar_bloquear_alteracao_auditoria()"
        )

        for tabela in TABELAS_RLS:
            op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY")


def downgrade():
    # O RLS não é desligado no downgrade: desligá-lo abriria as tabelas na Data API do Supabase.
    if _is_postgres():
        op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_sem_truncate ON audit_logs")
        op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_imutavel ON audit_logs")
        for tabela in TABELAS_SEM_EXCLUSAO:
            op.execute(f"DROP TRIGGER IF EXISTS trg_{tabela}_sem_truncate ON {tabela}")
            op.execute(f"DROP TRIGGER IF EXISTS trg_{tabela}_sem_delete ON {tabela}")
        op.execute("DROP FUNCTION IF EXISTS gapar_bloquear_alteracao_auditoria()")
        op.execute("DROP FUNCTION IF EXISTS gapar_bloquear_exclusao_fisica()")

    for tabela, nome, _ in reversed(INDICES):
        op.drop_index(nome, table_name=tabela)

    tabelas = sorted({t for t, _, _ in CHECKS} | {t for t, _, _ in UNIQUES})
    for tabela in tabelas:
        with op.batch_alter_table(tabela, schema=None) as batch_op:
            for t, nome, _ in UNIQUES:
                if t == tabela:
                    batch_op.drop_constraint(nome, type_="unique")
            for t, nome, _ in CHECKS:
                if t == tabela:
                    batch_op.drop_constraint(nome, type_="check")
