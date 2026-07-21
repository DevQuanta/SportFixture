from flask import request, Blueprint, session, make_response, render_template, abort

from sqlalchemy import select

from app.blueprints.admin.renderer import render_admin_step
from app.database import db
from app.models import Tournament, Player, Match

from app.services.player_service import register_player_to_tournament, assign_player_to_group, save_player_details, delete_player_tournament
from app.services.tournament_service import get_or_create_tournament, save_match_details

api = Blueprint("api", __name__)


@api.route("/select-tournament", methods=["POST"])  # type: ignore
def select_tournament():
    tournament_input = request.form.get("tournaments")

    if not tournament_input:
        return "<p class='error-msg'>Please select or type a tournament name.</p>"

    tournament = get_or_create_tournament(tournament_input)
    response_html = render_admin_step(tournament.id)

    response = make_response(response_html)
    response.headers["HX-Push-Url"] = f"/admin?tournaments={tournament.id}"

    return response


@api.route("/matches/<int:match_id>/edit")
def edit_match(match_id):
    match = db.session.get(Match, match_id)

    return render_template("partials/edit_match_card.html", match=match)


@api.route("/edit-player/<int:player_id>")  # type: ignore
def edit_player(player_id):
    player = db.session.get(Player, player_id)

    return render_template("partials/edit_player_row.html", player=player)


@api.route("/save-player/<int:player_id>", methods=["POST"])  # type: ignore
def save_player(player_id):
    updated_name = request.form.get("player-name")
    updated_diff = request.form.get("player-diff")

    player = save_player_details(player_id, updated_name, updated_diff)
    return render_template("partials/single_player_row.html", player=player)


@api.route("/delete-player/<int:player_id>", methods=["DELETE"])
def delete_player(player_id, tournament_id):

    delete_player_tournament(player_id, tournament_id)

    return "", 200

@api.route("/matches/<int:match_id>/save", methods=["POST"])
def save_match(match_id):
    payload = request.get_json()

    match = save_match_details(match_id, payload)
    return render_template("partials/match_card.html", match=match)


@api.route("/<int:tournament_id>/players/<int:player_id>/assign", methods=["POST"])  # type:ignore
def assign_player(tournament_id, player_id):
    updated_group_id = request.form.get("group_id")

    assign_player_to_group(tournament_id, player_id, updated_group_id)
    return render_admin_step(tournament_id)


@api.route("/register-player", methods=["POST"])  # type: ignore
def register_player():
    name = request.form.get("player-name")
    difficulty = request.form.get("player-diff")
    tournament_id = request.form.get("tournament_id")

    tournament = register_player_to_tournament(tournament_id, name, difficulty)
    return render_template(
        "partials/player_rows.html", players=tournament.player_associations
    )
