import questionary
from rich.console import Console
from app.models import Admin, Tournament
from app.database import db
from app import create_app

app = create_app()

console = Console()

def admin_register():
    console.print("[red bold]Admin Registration[/red bold]")
    console.print(":: Use this application to register admins\n")

    email = questionary.text("Email Adress").ask()
    password = questionary.password("Password").ask()

    console.print("[yellow]Creating new admin[/yellow]")

    with app.app_context():
        admin = Admin(
            email = email,
        )
        admin.password = password

        db.session.add(admin)

        db.session.commit()

        console.print("[green]Admin creation success![/green]")

def destroy_db():
    console.print("[red bold]Destroy DB[/red bold]")
    console.print(":: Use this application to destroy DB contents\n")

    confirm = questionary.confirm("Really delete?").ask()

    if confirm:
        with app.app_context():

            db.drop_all()
            db.create_all()

            console.print("[green]Deletion success![/green]")

def new_tournament():
    console.print("[red bold]Tournament creation[/red bold]")
    console.print(":: Use this application to create tournaments\n")

    name = questionary.text("Tournament name: ").ask()

    console.print("[yellow]Creating new tournament[/yellow]")

    with app.app_context():
        tournament = Tournament()
        tournament.name = name

        db.session.add(tournament)

        db.session.commit()

        console.print("[green]Tournament creation success![/green]")


option = questionary.select("Manage: ", choices = ["admins", "tournaments", "players", "delete"]).ask()

match option:
    case "admins":
        admin_register()
    case "tournaments":
        new_tournament()
    case "delete":
        destroy_db()
    case _:
        console.log("[error]Invalid option[/error]")
