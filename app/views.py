from flask import Blueprint, render_template, request, current_app
from flask_login.utils import login_required
from sqlalchemy import select

from app.database import db
from app.models import Player, Tournament

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home_page():
    return render_template("main.html")


@main_bp.route("/knockouts")
def knockouts_page():
    return render_template("knockouts.html")


@main_bp.route("/admin")
@login_required
def admin_page():

    stmt = select(Tournament)
    tournaments = db.session.execute(stmt).scalars().all()


    return render_template("admin.html", tournaments=tournaments)


@main_bp.route("/register-player", methods=["POST"])  # type: ignore
def register_player():
    name = request.form.get("player-name")
    difficulty = request.form.get("player-diff")
    tournament_id = request.form.get("tournament_id")

    stmt = select(Tournament).where(Tournament.id == int(tournament_id)) # type: ignore
    tournament = db.session.execute(stmt).scalar_one_or_none()

    player = Player()

    stmt = select(Player).where(Player.name == name)
    player = db.session.execute(stmt).scalar_one_or_none()

    if not player:
        player = Player()
        player.name = name # type: ignore
        player.difficulty = difficulty # type: ignore


        db.session.add(player)


    player.tournaments.append(tournament) #type: ignore
    db.session.commit()


    return render_template("partials/player_rows.html", tournament=tournament)

@main_bp.route("/select-tournament", methods=["POST"])  # type: ignore
def select_tournament():
    tournament_input = request.form.get("tournaments")

    if not tournament_input:
        return "<p class='error-msg'>Please select or type a tournament name.</p>"

    if tournament_input.isdigit():
        # Fetch existing tournament by ID
        stmt = select(Tournament).where(Tournament.id == int(tournament_input))
        tournament = db.session.execute(stmt).scalar_one_or_none()
    else:
        stmt = select(Tournament).where(Tournament.name == tournament_input)
        tournament = db.session.execute(stmt).scalar_one_or_none()

        if not tournament:
            tournament = Tournament(name=tournament_input) # type: ignore
            db.session.add(tournament)
            db.session.commit()  # Commit   ting generates the tournament.id automatically

    return render_template("partials/player_manager.html", tournament=tournament)
