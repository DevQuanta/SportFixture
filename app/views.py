from flask import Blueprint, render_template, request, current_app
from flask_login.utils import login_required
from sqlalchemy import select

from app.database import db
from app.models import Player, Tournament, TournamentPlayer

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

    return step_1(tournament.id)

@main_bp.route("/admin/<int:tournament_id>/step-1")
def step_1(tournament_id):
    stmt = select(Tournament).where(Tournament.id == tournament_id)
    tournament = db.session.execute(stmt).scalar_one_or_none()

    return render_template("partials/admin_step_1.html", tournament=tournament)

@main_bp.route("/admin/<int:tournament_id>/step-2")
def step_2(tournament_id):
    stmt = select(Tournament).where(Tournament.id == tournament_id)
    tournament = db.session.execute(stmt).scalar_one_or_none()

    return view_tournament_seeding(tournament.id) # type: ignore

@main_bp.route("/admin/<int:tournament_id>/step-3")
def step_3(tournament_id):
    stmt = select(Tournament).where(Tournament.id == tournament_id)
    tournament = db.session.execute(stmt).scalar_one_or_none()
    return render_template("partials/admin_step_3.html", tournament=tournament)

@main_bp.route("/edit-player/<int:player_id>") # type: ignore
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)

    return render_template("partials/edit_player_row.html", player=player)



@main_bp.route("/save-player/<int:player_id>", methods=["POST"]) # type: ignore
def save_player(player_id):
    player = Player.query.get_or_404(player_id)

    updated_name = request.form.get("player-name")
    updated_diff = request.form.get("player-diff")

    player.name = updated_name
    player.difficulty = updated_diff

    db.session.commit()

    return render_template("partials/single_player_row.html", player=player)


@main_bp.route("/delete-player/<int:player_id>", methods=["DELETE"])
def delete_player(player_id):

    player = Player.query.get_or_404(player_id)

    db.session.delete(player)

    db.session.commit()

    return "", 200

@main_bp.route("/tournament/<int:tournament_id>/seeding") # type: ignore
def view_tournament_seeding(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)

    tournament_players = tournament.player_associations # type:ignore
    grouped_players = {0: []}

    for group_num in range(1, tournament.max_group + 1): # type:ignore
        grouped_players[group_num] = []

    for ticket in tournament_players:
        target_group = ticket.group_id # type:ignore

        player_row = ticket.player

        if target_group is None:
            target_group = 0

        player_card = {
            "id": player_row.id,
            "name": player_row.name,
            "difficult": player_row.difficulty
        }

        grouped_players[target_group].append(player_card)

    return render_template("partials/admin_step_2.html", grouped_players=grouped_players)
