from flask import current_app, render_template, request
from sqlalchemy import select

from app.blueprints.admin.renderer import get_admin_context
from app.database import db
from app.models import Player, Tournament
from app.services.player_service import (
    assign_player_to_group,
    delete_player_tournament,
    register_player_to_tournament,
    save_player_details,
)

from . import api


@api.route("/player/<int:player_id>/assign", methods=["POST"])  # type:ignore
def assign_player(player_id):
    tournament_id = request.args.get("tournament_id", "")
    updated_group_id = request.form.get("group_id", "")

    assign_player_to_group(tournament_id, player_id, updated_group_id)
    (template, context) = get_admin_context(tournament_id)

    return render_template(template, **context)


@api.route("/player/edit")  # type: ignore
def edit_player():
    player_id = request.args.get("id", "")
    tournament_id = request.args.get("tournament_id", "")

    player = db.session.get(Player, player_id)
    return render_template(
        "partials/players/edit_player_row.html",
        player=player,
        tournament=tournament_id,
    )


@api.route("/player/save", methods=["POST"])  # type: ignore
def save_player():
    updated_name = request.form.get("player-name")
    updated_diff = request.form.get("player-diff")
    tournament_id = request.form.get("tournament_id")

    player_id = request.args.get("id", "")

    player = save_player_details(player_id, updated_name, updated_diff)

    return render_template(
        "partials/players/single_player_row.html",
        player=player,
        tournament_id=tournament_id,
    )


@api.route("/player/delete", methods=["DELETE"])
def delete_player():
    player_id = request.args.get("id", "")
    tournament_id = request.args.get("tournament_id", "")

    if tournament_id:
        current_app.logger.info("deleting")
        return delete_player_tournament(player_id, tournament_id)

    return "", 200


@api.route("/players", methods=["GET", "POST"])
def search_players():

    if request.method == "GET":
        player_id = request.args.get("id", "")
        if player_id:
            player = db.session.get(Player, player_id)
            if not player:
                return "", 404
            return render_template(
                "partials/players/existing_difficulty.html", player=player
            )

        if "new-player" in request.args:
            ratings = ["beginner", "intermediate", "advanced"]
            return render_template(
                "partials/players/new_difficulty.html", ratings=ratings
            )

        if "player-name" in request.args:
            query = request.args.get("player-name", "")
            stmt = select(Player).where(Player.name.ilike(f"%{query}%")).limit(5)
            matching_players = db.session.scalars(stmt).all()

            return render_template(
                "partials/results/player_search_results.html", players=matching_players
            )

    elif request.method == "POST":
        player_id = request.form.get("player-id", "")
        player_name = request.form.get("player-name", "")
        difficulty = request.form.get("player-diff", "")
        tournament_id = request.form.get("tournament_id")

        if player_name and not player_id:
            player = Player(
                name=player_name,
                difficulty=difficulty,
            )

            db.session.add(player)
            db.session.flush()

            player_id = player.id

        register_player_to_tournament(tournament_id, player_id)

        player = db.session.get(Player, player_id)
        tournament = db.session.get(Tournament, tournament_id)
        db.session.commit()

        return render_template(
            "partials/players/single_player_row.html",
            player=player,
            tournament=tournament,
        )

    return "", 400
