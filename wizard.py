import questionary
from rich.console import Console
from app.models import Admin
from app.database import db
from app import create_app

app = create_app()

console = Console()

console.print("[red bold]Admin Registration[/red bold]")
console.print(":: Use this application to register admins\n")

email = questionary.text("Email Adress").ask()
password = questionary.password("Password").ask()

console.print("[yellow]Creating new admin[/yellow]")

with app.app_context():
    admin = Admin()
    admin.email = email
    admin.password = password

    db.session.add(admin)

    db.session.commit()

    console.print("[green]Admin creation success![/green]")
