import click
from datetime import date, timedelta
from flask.cli import with_appcontext
from app.extensions import db
from app.models.user import User
from app.models.animal import Animal
from app.models.health import Vaccination, Prescription, MedicalRecord, MedicationLog
from app.models.adoption import Adoption
from app.models.blacklist import NonEligiblePerson
from app.models.announcement import Announcement


@click.command("create-admin")
@with_appcontext
def create_admin():
    """Cria a administradora mestre a partir de INITIAL_ADMIN_EMAIL (RN13, RF04)."""
    from flask import current_app
    email = current_app.config.get("INITIAL_ADMIN_EMAIL", "admin@gapar.org.br").strip().lower()
    existing = User.query.filter(db.func.lower(User.email) == email).first()
    if existing:
        existing.role = "Administradora"
        existing.is_active = True
        db.session.commit()
        click.echo(f"Administradora existente atualizada: {email}")
        return
    user = User(email=email, name="Administradora GAPAR", role="Administradora", is_active=True)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Administradora mestre criada: {email}")


@click.command("seed")
@with_appcontext
def seed_data():
    """Popula o banco de dados com dados de demonstração completos para homologação do MVP."""
    click.echo("Garantindo criação de tabelas no banco de dados...")
    db.create_all()
    click.echo("Iniciando povoamento de dados para o 1º MVP...")
    hoje = date.today()

    # 1. Usuárias na Whitelist (RN12, RN13)
    admin_email = "admin@gapar.org.br"
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        admin = User(email=admin_email, name="Ana Silva (Diretora)", role="Administradora", is_active=True)
        db.session.add(admin)

    volun1_email = "voluntaria1@gapar.org.br"
    volun1 = User.query.filter_by(email=volun1_email).first()
    if not volun1:
        volun1 = User(email=volun1_email, name="Carla Souza", role="Voluntaria", is_active=True)
        db.session.add(volun1)

    volun2_email = "voluntaria2@gapar.org.br"
    volun2 = User.query.filter_by(email=volun2_email).first()
    if not volun2:
        volun2 = User(email=volun2_email, name="Beatriz Lima", role="Voluntaria", is_active=True)
        db.session.add(volun2)

    db.session.commit()
    click.echo("✓ Usuárias da Whitelist configuradas.")

    # 2. Lista Sigilosa de Não Aptos (RN15)
    nao_apto = NonEligiblePerson.query.filter_by(cpf="111.222.333-44").first()
    if not nao_apto:
        nao_apto = NonEligiblePerson(
            nome="João Inapto de Oliveira",
            cpf="111.222.333-44",
            telefone="41988887777",
            motivo_impedimento="Histórico reincidente de negligência e abandono de animais em 2024.",
            cadastrado_por_user_id=admin.id
        )
        db.session.add(nao_apto)
        db.session.commit()
    click.echo("✓ Lista sigilosa de não aptos (RN15) configurada.")

    # 3. Animais com diferentes ciclos de vida (RN01, RN02, RN05, RN07)
    # 3.1. Rex (Em Acolhimento recente)
    rex = Animal.query.filter_by(nome="Rex", is_deleted=False).first()
    if not rex:
        rex = Animal(
            nome="Rex",
            idade_estimada="2 anos",
            sexo="Macho",
            raca="Sem Raça Definida (SRD)",
            porte="Médio",
            pelagem="Curta, marrom com branco",
            peso_kg=14.5,
            local_resgate="Bairro Boqueirão",
            data_entrada=hoje,
            motivo_resgate="Resgatado em situação de rua próximo a ponto de ônibus",
            is_castrado=True,
            is_microchipado=False,
            is_idoso=False,
            localizacao_baia="Canil 01",
            codigo_identificador="#GP-2026-01",
            status_operacional=Animal.STATUS_ACOLHIMENTO
        )
        db.session.add(rex)
        db.session.flush()

        # Vacina
        v_rex = Vaccination(
            animal_id=rex.id,
            nome_vacina="V10 Polivalente",
            lote="V10-2026-A",
            data_aplicacao=hoje,
            data_reforco=hoje + timedelta(days=365),
            aplicado_por_user_id=admin.id
        )
        db.session.add(v_rex)

    # 3.2. Luna (Em Tratamento com medicação ativa hoje para testar baixa de dose)
    luna = Animal.query.filter_by(nome="Luna", is_deleted=False).first()
    if not luna:
        luna = Animal(
            nome="Luna",
            idade_estimada="9 anos",
            sexo="Fêmea",
            raca="Poodle Mix",
            porte="Pequeno",
            pelagem="Longa, branca",
            peso_kg=6.2,
            local_resgate="Centro da cidade",
            data_entrada=hoje - timedelta(days=10),
            motivo_resgate="Entregue por tutor idoso sem condições de custear tratamento",
            is_castrado=False,
            is_microchipado=True,
            is_idoso=True,
            localizacao_baia="Gatil / Quarentena 02",
            codigo_identificador="#GP-2026-02",
            status_operacional=Animal.STATUS_TRATAMENTO,
            cuidados_especiais="Otite crônica em tratamento e alimentação sênior."
        )
        db.session.add(luna)
        db.session.flush()

        # Prescrição ativa
        p_luna = Prescription(
            animal_id=luna.id,
            nome_medicamento="Amoxicilina + Clavulanato",
            dosagem="125 mg (1/2 comprimido)",
            horarios="08:00, 20:00",
            data_inicio=hoje - timedelta(days=2),
            data_fim=hoje + timedelta(days=5),
            instrucoes="Administrar junto com um pouco de sachê úmido.",
            prescrito_por_user_id=admin.id
        )
        db.session.add(p_luna)

        # Prontuário
        pr_luna = MedicalRecord(
            animal_id=luna.id,
            tipo_evento="Consulta",
            data_evento=hoje - timedelta(days=2),
            veterinario_responsavel="Dr. Marcos Veterinário",
            clinica="Clínica Veterinária Esperança",
            diagnostico="Otite externa bacteriana unilateral.",
            procedimentos_realizados="Limpeza auricular e início de antibioticoterapia oral.",
            cadastrado_por_user_id=volun1.id
        )
        db.session.add(pr_luna)

    # 3.3. Thor (Disponível para adoção)
    thor = Animal.query.filter_by(nome="Thor", is_deleted=False).first()
    if not thor:
        thor = Animal(
            nome="Thor",
            idade_estimada="4 anos",
            sexo="Macho",
            raca="Labrador Retrô",
            porte="Grande",
            pelagem="Curta, preta",
            peso_kg=28.0,
            local_resgate="Parque Municipal",
            data_entrada=hoje - timedelta(days=40),
            is_castrado=True,
            is_microchipado=True,
            is_idoso=False,
            localizacao_baia="Canil 04",
            codigo_identificador="#GP-2026-03",
            status_operacional=Animal.STATUS_DISPONIVEL
        )
        db.session.add(thor)
        db.session.flush()

        # Vacina com reforço vencendo hoje para aparecer no Painel Hoje
        v_thor = Vaccination(
            animal_id=thor.id,
            nome_vacina="Antirrábica",
            lote="AR-2025-99",
            data_aplicacao=hoje - timedelta(days=365),
            data_reforco=hoje,
            aplicado_por_user_id=admin.id
        )
        db.session.add(v_thor)

    # 3.4. Mel (Adotada formalmente - Ficha Congelada RN05)
    mel = Animal.query.filter_by(nome="Mel", is_deleted=False).first()
    if not mel:
        mel = Animal(
            nome="Mel",
            idade_estimada="1 ano",
            sexo="Fêmea",
            raca="Vira-lata Caramelo",
            porte="Pequeno",
            pelagem="Curta, caramelo",
            peso_kg=7.5,
            local_resgate="Resgate de ninhada",
            data_entrada=hoje - timedelta(days=60),
            is_castrado=True,
            is_microchipado=True,
            is_idoso=False,
            localizacao_baia="Lar Adotivo",
            codigo_identificador="#GP-2026-04",
            status_operacional=Animal.STATUS_ADOTADO
        )
        db.session.add(mel)
        db.session.flush()

        # Registro de adoção formal
        adocao_mel = Adoption(
            animal_id=mel.id,
            adotante_nome="Fernanda Duarte",
            adotante_telefone="41991234567",
            adotante_cpf="987.654.321-00",
            adotante_endereco="Rua das Flores, 120 - Curitiba/PR",
            data_adocao=hoje - timedelta(days=5),
            termo_assinado=True,
            termo_fisico_assinado=True,
            observacoes="Adotada em feira de adoção responsável. Casa com quintal seguro.",
            cadastrado_por_user_id=admin.id
        )
        db.session.add(adocao_mel)

    # 4. Mural de Avisos do Turno (RF23)
    aviso1 = Announcement.query.filter_by(titulo="Campanha de Vacinação de Sábado").first()
    if not aviso1:
        aviso1 = Announcement(
            tipo="DIRETORIA",
            titulo="Campanha de Vacinação de Sábado",
            conteudo="Convocação de todas as voluntárias disponíveis para a força-tarefa de vacinação neste sábado a partir das 09h.",
            categoria="Procedimento",
            is_urgente=True,
            is_fixado=True,
            autor_id=admin.id
        )
        db.session.add(aviso1)

    db.session.commit()
    click.echo("✓ Animais, prescrições, vacinas, adoção e mural populados com sucesso!")
    click.echo("Seed concluído! O 1º MVP está pronto para testes e demonstração.")
