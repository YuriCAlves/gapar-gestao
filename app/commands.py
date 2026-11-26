import click
from datetime import timedelta
from flask.cli import with_appcontext
from app.extensions import db
from app.models.user import User
from app.models.whitelist import Whitelist
from app.models.animal import Animal
from app.models.health import Vaccination, Prescription, MedicalRecord, MedicationLog
from app.models.adoption import Adoption
from app.models.blacklist import NonEligiblePerson
from app.models.announcement import Announcement

# Só ASCII nas mensagens de progresso: o console do Windows (cp1252) não imprime "✓".
OK = "[ok]"


def _ensure_whitelist(email, role):
    """Garante a entrada ativa na Whitelist (RN12), fonte de verdade da autorização."""
    entry = Whitelist.query.filter(db.func.lower(Whitelist.email) == email.lower()).first()
    if not entry:
        db.session.add(Whitelist(email=email.lower(), role=role, is_active=True))
    else:
        entry.role, entry.is_active = role, True


@click.command("create-admin")
@with_appcontext
def create_admin():
    """Cria a administradora mestre a partir de INITIAL_ADMIN_EMAIL (RN13, RF04)."""
    from flask import current_app
    email = current_app.config.get("INITIAL_ADMIN_EMAIL", "admin@gapar.org.br").strip().lower()
    _ensure_whitelist(email, "Administradora")
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


# ---------------------------------------------------------------------------------------------
# Seed de demonstração
#
# Idempotente: cada registro é procurado por uma chave natural (nome do animal, nome do
# medicamento, nome da vacina, título do aviso...) e só é criado se ainda não existir. Nada é
# apagado nem sobrescrito. As datas são relativas ao dia em que o seed roda, para que o painel
# Hoje sempre tenha doses e reforços do dia.
# ---------------------------------------------------------------------------------------------

def _animal(nome, **campos):
    """Devolve o animal (não excluído) com esse nome, criando-o se não existir."""
    animal = Animal.query.filter_by(nome=nome, is_deleted=False).first()
    if not animal:
        animal = Animal(nome=nome, **campos)
        db.session.add(animal)
        db.session.flush()
    return animal


def _vacina(animal, nome_vacina, **campos):
    vacina = Vaccination.query.filter_by(animal_id=animal.id, nome_vacina=nome_vacina).first()
    if not vacina:
        vacina = Vaccination(animal_id=animal.id, nome_vacina=nome_vacina, **campos)
        db.session.add(vacina)
    return vacina


def _prontuario(animal, diagnostico, **campos):
    registro = MedicalRecord.query.filter_by(animal_id=animal.id, diagnostico=diagnostico).first()
    if not registro:
        registro = MedicalRecord(animal_id=animal.id, diagnostico=diagnostico, **campos)
        db.session.add(registro)
    return registro


def _prescricao(animal, nome_medicamento, **campos):
    prescricao = Prescription.query.filter_by(animal_id=animal.id, nome_medicamento=nome_medicamento).first()
    if not prescricao:
        prescricao = Prescription(animal_id=animal.id, nome_medicamento=nome_medicamento, **campos)
        db.session.add(prescricao)
        db.session.flush()
    return prescricao


def _baixa(prescricao, dia, horario_previsto, horario_aplicado, user):
    """Registra a baixa da dose, se ainda não houver (respeita uq_medication_logs_dose)."""
    if not (prescricao.data_inicio <= dia <= prescricao.data_fim):
        return
    if horario_previsto not in [h.strip() for h in prescricao.horarios.split(",")]:
        return
    existe = MedicationLog.query.filter_by(prescription_id=prescricao.id, data_aplicacao=dia,
                                           horario_previsto=horario_previsto).first()
    if not existe:
        db.session.add(MedicationLog(prescription_id=prescricao.id, user_id=user.id, data_aplicacao=dia,
                                     horario_previsto=horario_previsto, horario_aplicado=horario_aplicado))


def _aviso(titulo, **campos):
    aviso = Announcement.query.filter_by(titulo=titulo).first()
    if not aviso:
        aviso = Announcement(titulo=titulo, **campos)
        db.session.add(aviso)
    return aviso


@click.command("seed")
@with_appcontext
def seed_data():
    """Popula o banco com dados de demonstração (idempotente; não apaga nem altera dados existentes)."""
    from flask import current_app
    from app.utils import tempo

    # O esquema do PostgreSQL vem das migrações (flask db upgrade). O create_all fica só para o
    # SQLite local de desenvolvimento, que pode não ter passado pelas migrações.
    if db.engine.dialect.name == "sqlite":
        db.create_all()

    click.echo("Iniciando povoamento de dados de demonstração...")
    hoje = tempo.hoje()
    dias = lambda n: hoje + timedelta(days=n)  # noqa: E731

    # 1. Usuárias na Whitelist (RN12, RN13)
    admin_email = current_app.config.get("INITIAL_ADMIN_EMAIL", "admin@gapar.org.br").strip().lower()
    admin = User.query.filter(db.func.lower(User.email) == admin_email).first()
    if not admin:
        admin = User(email=admin_email, name="Administradora Mestre", role="Administradora", is_active=True)
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

    _ensure_whitelist(admin_email, "Administradora")
    _ensure_whitelist(volun1_email, "Voluntaria")
    _ensure_whitelist(volun2_email, "Voluntaria")
    db.session.commit()
    click.echo(f"{OK} Usuárias da Whitelist configuradas.")

    # 2. Lista Sigilosa de Não Aptos (RN15)
    if not NonEligiblePerson.query.filter_by(nome="João Inapto de Oliveira").first():
        db.session.add(NonEligiblePerson(
            nome="João Inapto de Oliveira",
            cpf="111.222.333-96",
            telefone="41988887777",
            motivo_impedimento="Histórico reincidente de negligência e abandono de animais em 2024.",
            cadastrado_por_user_id=admin.id,
        ))
        db.session.commit()
    click.echo(f"{OK} Lista sigilosa de não aptos (RN15) configurada.")

    # 3. Animais: um em cada status (RN02), idosos (RN07) e com cuidados especiais (RF08)
    rex = _animal(
        "Rex", idade_estimada="2 anos", sexo="Macho", raca="Sem Raça Definida (SRD)", porte="Médio",
        pelagem="Curta, marrom com branco", peso_kg=14.5, local_resgate="Bairro Boqueirão",
        data_entrada=hoje, motivo_resgate="Resgatado em situação de rua próximo a ponto de ônibus",
        is_castrado=True, localizacao_baia="Canil 01", codigo_identificador="#GP-2026-01",
        status_operacional=Animal.STATUS_ACOLHIMENTO,
    )
    luna = _animal(
        "Luna", idade_estimada="9 anos", sexo="Fêmea", raca="Poodle Mix", porte="Pequeno",
        pelagem="Longa, branca", peso_kg=6.2, local_resgate="Centro da cidade", data_entrada=dias(-10),
        motivo_resgate="Entregue por tutor idoso sem condições de custear tratamento",
        is_microchipado=True, is_idoso=True, localizacao_baia="Gatil / Quarentena 02",
        codigo_identificador="#GP-2026-02", status_operacional=Animal.STATUS_TRATAMENTO,
        cuidados_especiais="Otite crônica em tratamento e alimentação sênior.",
    )
    thor = _animal(
        "Thor", idade_estimada="4 anos", sexo="Macho", raca="Labrador Retrô", porte="Grande",
        pelagem="Curta, preta", peso_kg=28.0, local_resgate="Parque Municipal", data_entrada=dias(-40),
        is_castrado=True, is_microchipado=True, localizacao_baia="Canil 04",
        codigo_identificador="#GP-2026-03", status_operacional=Animal.STATUS_DISPONIVEL,
    )
    mel = _animal(
        "Mel", idade_estimada="1 ano", sexo="Fêmea", raca="Vira-lata Caramelo", porte="Pequeno",
        pelagem="Curta, caramelo", peso_kg=7.5, local_resgate="Resgate de ninhada", data_entrada=dias(-60),
        is_castrado=True, is_microchipado=True, localizacao_baia="Lar Adotivo",
        codigo_identificador="#GP-2026-04", status_operacional=Animal.STATUS_ADOTADO,
    )
    nina = _animal(
        "Nina", idade_estimada="3 anos", sexo="Fêmea", raca="Sem Raça Definida (SRD)", porte="Médio",
        pelagem="Tricolor", peso_kg=12.0, local_resgate="Rodovia BR-277", data_entrada=dias(-25),
        motivo_resgate="Atropelamento com fratura na pata traseira esquerda",
        is_castrado=True, localizacao_baia="Lar temporário - Família Prado",
        codigo_identificador="#GP-2026-05", status_operacional=Animal.STATUS_LAR_TEMPORARIO,
        cuidados_especiais="Pós-operatório ortopédico: repouso e passeios curtos na guia.",
    )
    bento = _animal(
        "Bento", idade_estimada="11 anos", sexo="Macho", raca="Beagle", porte="Médio",
        pelagem="Curta, tricolor", peso_kg=13.8, local_resgate="Abandonado em clínica parceira",
        data_entrada=dias(-90), is_castrado=True, is_microchipado=True, is_idoso=True,
        localizacao_baia="Canil 06", codigo_identificador="#GP-2026-06",
        status_operacional=Animal.STATUS_DISPONIVEL,
        cuidados_especiais="Cardiopata leve: evitar exercícios intensos.",
    )
    bob = _animal(
        "Bob", idade_estimada="13 anos", sexo="Macho", raca="Pastor Alemão", porte="Grande",
        pelagem="Longa, preta e castanha", peso_kg=30.5, local_resgate="Chácara no bairro Umbará",
        data_entrada=dias(-120), motivo_resgate="Encontrado acorrentado e desnutrido",
        is_idoso=True, localizacao_baia="Canil 02", codigo_identificador="#GP-2026-07",
        status_operacional=Animal.STATUS_OBITO,
        cuidados_especiais="Insuficiência renal crônica.",
    )
    db.session.commit()

    # 3.1 Adoção formal da Mel (RF20, RN04)
    if not Adoption.query.filter_by(animal_id=mel.id).first():
        db.session.add(Adoption(
            animal_id=mel.id, adotante_nome="Fernanda Duarte", adotante_telefone="41991234567",
            adotante_cpf="98765432100", adotante_endereco="Rua das Flores, 120 - Curitiba/PR",
            data_adocao=dias(-5), termo_assinado=True, termo_fisico_assinado=True,
            observacoes="Adotada em feira de adoção responsável. Casa com quintal seguro.",
            cadastrado_por_user_id=admin.id,
        ))

    # 3.2 Vacinas (RF13): reforço hoje (Thor), reforço atrasado (Nina e Bento), próximos (Rex)
    _vacina(rex, "V10 Polivalente", lote="V10-2026-A", data_aplicacao=hoje,
            data_reforco=dias(365), aplicado_por_user_id=admin.id)
    _vacina(thor, "Antirrábica", lote="AR-2025-99", data_aplicacao=dias(-365),
            data_reforco=hoje, aplicado_por_user_id=admin.id)
    _vacina(nina, "V10 Polivalente", lote="V10-2025-K", data_aplicacao=dias(-372),
            data_reforco=dias(-7), aplicado_por_user_id=volun1.id,
            observacoes="Reforço atrasado: aguardando liberação ortopédica.")
    _vacina(bento, "Gripe Canina (Tosse dos Canis)", lote="GC-2025-12", data_aplicacao=dias(-380),
            data_reforco=dias(-15), aplicado_por_user_id=volun2.id)
    # Reforço do dia: procurado também pela data de reforço, para que cada execução do seed garanta
    # um reforço "hoje" no painel (os de execuções anteriores passam a aparecer como atrasados ou,
    # pela regra de open_booster_filter, como atendidos pela aplicação mais nova).
    if not Vaccination.query.filter_by(animal_id=bento.id, nome_vacina="Giardia", data_reforco=hoje).first():
        db.session.add(Vaccination(animal_id=bento.id, nome_vacina="Giardia", lote="GI-2026-07",
                                   data_aplicacao=dias(-21), data_reforco=hoje, aplicado_por_user_id=volun1.id,
                                   observacoes="Segunda dose do protocolo."))
    _vacina(luna, "Antirrábica", lote="AR-2026-03", data_aplicacao=dias(-9),
            data_reforco=dias(356), aplicado_por_user_id=volun1.id)
    _vacina(mel, "V10 Polivalente", lote="V10-2026-B", data_aplicacao=dias(-40),
            data_reforco=dias(325), aplicado_por_user_id=admin.id)

    # 3.3 Prontuários (RF14)
    _prontuario(luna, "Otite externa bacteriana unilateral.", tipo_evento="Consulta", data_evento=dias(-2),
                veterinario_responsavel="Dr. Marcos Veterinário", clinica="Clínica Veterinária Esperança",
                procedimentos_realizados="Limpeza auricular e início de antibioticoterapia oral.",
                cadastrado_por_user_id=volun1.id)
    _prontuario(rex, "Avaliação de entrada: bom estado geral, leve desidratação.", tipo_evento="Consulta",
                data_evento=hoje, veterinario_responsavel="Dra. Paula Ramos", clinica="Clínica Parceira GAPAR",
                procedimentos_realizados="Hidratação subcutânea e vermifugação.", cadastrado_por_user_id=volun2.id)
    _prontuario(nina, "Fratura de fêmur esquerdo.", tipo_evento="Cirurgia", data_evento=dias(-20),
                veterinario_responsavel="Dr. André Lima", clinica="Hospital Veterinário Central",
                procedimentos_realizados="Osteossíntese com placa e parafusos.", cadastrado_por_user_id=admin.id)
    _prontuario(nina, "Raio-X de controle: consolidação óssea em andamento.", tipo_evento="Exame",
                data_evento=dias(-3), clinica="Hospital Veterinário Central", cadastrado_por_user_id=volun1.id)
    _prontuario(bento, "Ecocardiograma: degeneração mixomatosa de válvula mitral, estágio B1.",
                tipo_evento="Exame", data_evento=dias(-30), veterinario_responsavel="Dra. Paula Ramos",
                clinica="Clínica Parceira GAPAR", cadastrado_por_user_id=admin.id)
    _prontuario(bob, "Óbito por complicações de insuficiência renal crônica.", tipo_evento="Procedimento",
                data_evento=dias(-4), veterinario_responsavel="Dr. Marcos Veterinário",
                clinica="Clínica Veterinária Esperança", cadastrado_por_user_id=admin.id)

    # 3.4 Prescrições vigentes hoje com vários horários (RF15, RN08, RN09)
    p_luna = _prescricao(luna, "Amoxicilina + Clavulanato", dosagem="125 mg (1/2 comprimido)",
                         horarios="08:00, 20:00", data_inicio=dias(-2), data_fim=dias(5),
                         instrucoes="Administrar junto com um pouco de sachê úmido.", prescrito_por_user_id=admin.id)
    p_luna2 = _prescricao(luna, "Otomax (gotas otológicas)", dosagem="4 gotas no ouvido direito",
                          horarios="09:00, 15:00, 21:00", data_inicio=dias(-2), data_fim=dias(8),
                          instrucoes="Massagear a base da orelha após aplicar.", prescrito_por_user_id=volun1.id)
    p_nina = _prescricao(nina, "Meloxicam", dosagem="0,1 mg/kg (1,2 ml)", horarios="07:00, 19:00",
                         data_inicio=dias(-5), data_fim=dias(2), instrucoes="Dar após a refeição.",
                         prescrito_por_user_id=admin.id)
    _prescricao(rex, "Simparic 10-20 kg", dosagem="1 comprimido", horarios="10:00",
                        data_inicio=hoje, data_fim=hoje, instrucoes="Dose única contra pulgas e carrapatos.",
                        prescrito_por_user_id=volun2.id)
    # Prescrição encerrada (fora da vigência), para o histórico
    _prescricao(nina, "Tramadol", dosagem="2 mg/kg", horarios="08:00, 16:00, 00:00",
                data_inicio=dias(-20), data_fim=dias(-13), instrucoes="Analgesia pós-cirúrgica.",
                prescrito_por_user_id=admin.id)
    db.session.flush()

    # 3.5 Algumas doses de hoje já baixadas (RF16); as demais ficam pendentes no painel Hoje
    _baixa(p_luna, hoje, "08:00", "08:10", volun1)
    _baixa(p_luna2, hoje, "09:00", "09:05", volun1)
    _baixa(p_nina, hoje, "07:00", "07:20", volun2)
    _baixa(p_luna, dias(-1), "08:00", "08:02", volun1)
    _baixa(p_luna, dias(-1), "20:00", "20:15", volun2)

    # 4. Mural de avisos
    _aviso("Campanha de Vacinação de Sábado", tipo="DIRETORIA",
           conteudo="Convocação de todas as voluntárias disponíveis para a força-tarefa de vacinação neste sábado a partir das 09h.",
           categoria="Procedimento", is_urgente=True, is_fixado=True, autor_id=admin.id)
    _aviso("Passagem de turno - manhã", tipo="TURNO",
           conteudo="Nina comeu bem e tomou o Meloxicam das 07h. Luna ainda com a orelha sensível.",
           categoria="Geral", autor_id=volun2.id, animal_id=luna.id)
    _aviso("Doação de ração recebida", tipo="DIRETORIA",
           conteudo="Recebemos 60 kg de ração sênior. Armazenada no depósito 2.",
           categoria="Geral", autor_id=admin.id)

    db.session.commit()
    click.echo(f"{OK} Animais, vacinas, prontuários, prescrições, baixas, adoção e mural populados.")
    click.echo("Seed concluído.")


# --------------------------------------------------------------------------------------------
# CP-01: cifragem dos dados pessoais já existentes (ver docs/sdd/CP01_NUCLEO_SPEC.md, REQ-17)
# --------------------------------------------------------------------------------------------

def _campos_backfill():
    from app.utils.pii import normalizar_cpf, normalizar_telefone
    return (
        (NonEligiblePerson, "cpf_legado", "cpf_cifrado", "cpf_bidx", "cpf", normalizar_cpf),
        (NonEligiblePerson, "telefone_legado", "telefone_cifrado", "telefone_bidx", "tel", normalizar_telefone),
        (Adoption, "adotante_cpf_legado", "adotante_cpf_cifrado", "adotante_cpf_bidx", "cpf", normalizar_cpf),
        (Adoption, "adotante_endereco_legado", "adotante_endereco_cifrado", None, None, None),
    )


@click.command("pii-backfill")
@click.option("--dry-run", is_flag=True, help="Só conta o que seria cifrado, sem gravar nada.")
@with_appcontext
def pii_backfill(dry_run):
    """Cifra CPF, telefone e endereço legados SEM apagar o valor em claro.

    Idempotente: registros já cifrados são ignorados. Depois de gravar, decifra tudo de novo e
    confere com o valor em claro; qualquer divergência aborta com erro (nada fica pela metade).
    A remoção das colunas em claro é feita depois, pela migração 0003b.
    """
    from app.models.pii_mixin import preencher_pii_de_legado
    from app.services.audit import log_audit_event
    from app.utils.crypto import decifrar_pii, indice_cego
    from app.utils.pii import normalizar_nome

    contagens = {}
    for modelo, legado, cifrado, bidx, dominio, normalizar in _campos_backfill():
        rotulo = f"{modelo.__tablename__}.{legado}"
        pendentes = modelo.query.filter(getattr(modelo, legado).isnot(None),
                                        getattr(modelo, cifrado).is_(None)).all()
        contagens[rotulo] = 0
        for obj in pendentes:
            if dry_run or preencher_pii_de_legado(obj, legado, cifrado, bidx, dominio, normalizar):
                contagens[rotulo] += 1

    sem_nome_bidx = NonEligiblePerson.query.filter(NonEligiblePerson.nome_bidx.is_(None)).all()
    contagens["non_eligible_people.nome_bidx"] = len(sem_nome_bidx)
    if not dry_run:
        for pessoa in sem_nome_bidx:
            pessoa.nome_bidx = indice_cego("nome", normalizar_nome(pessoa.nome))

    for rotulo, total in contagens.items():
        click.echo(f"{'[simulacao]' if dry_run else OK} {rotulo}: {total} registro(s)")
    if dry_run:
        db.session.rollback()
        return

    db.session.flush()
    divergencias = 0
    for modelo, legado, cifrado, _bidx, _dominio, normalizar in _campos_backfill():
        for obj in modelo.query.filter(getattr(modelo, legado).isnot(None)).all():
            esperado = normalizar(getattr(obj, legado)) if normalizar else str(getattr(obj, legado)).strip()
            if esperado and decifrar_pii(getattr(obj, cifrado)) != esperado:
                divergencias += 1
    if divergencias:
        db.session.rollback()
        raise click.ClickException(f"{divergencias} registro(s) não conferem após cifrar. Nada foi gravado.")

    log_audit_event(acao="PII_BACKFILL", entidade="Sistema",
                    detalhes="Cifragem de dados pessoais legados: " +
                             ", ".join(f"{k}={v}" for k, v in contagens.items()),
                    commit=False)
    db.session.commit()
    click.echo(f"{OK} Conferência concluída: todos os valores cifrados decifram igual ao original.")
