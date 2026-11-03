import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models.user import User


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
