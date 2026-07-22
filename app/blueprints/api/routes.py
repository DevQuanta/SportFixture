from flask import request, Blueprint, make_response, render_template, abort

from app.blueprints.admin.renderer import render_admin_step
from app.database import db
from app.models import Player, Match, Tournament

from sqlalchemy import select

from app.services.player_service import register_player_to_tournament, assign_player_to_group, save_player_details, delete_player_tournament
from app.services.tournament_service import get_or_create_tournament, save_match_details, calculate_standings
from app.services.context_service import get_live_context

api = Blueprint("api", __name__)


@api.route("/select-tournament", methods=["GET"])  # type: ignore
def select_tournament():
    tournament_input = request.args.get("tournament")

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
    players_list = [tp.player for tp in match.tournament.player_associations]
    standings = calculate_standings(match.tournament_id, players_list, match.round_number)

    summary = [
        {
            "name": s["player_name"],
            "matches_won": s["matches_won"],
            "matches_lost": s["matches_lost"],
            "games_won": s["games_won"],
            "games_lost": s["games_lost"],
            "points_won": s["points_won"],
            "points_lost": s["points_lost"],
        }
        for _, s in standings
    ]

    context = {
        "standings": summary,
    }

    match_card = render_template("partials/match_card.html", match=match)
    leaderboard_card = render_template("partials/leaderboard.html", **context, oob=True)

    return match_card + leaderboard_card

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

@api.route("/search-players", methods=["GET"])
def search_players():
    query = request.args.get("player-name", "").strip()

    if query:
        stmt = select(Player).where(Player.name.ilike(f"%{query}%")).limit(5)
        matching_players = db.session.scalars(stmt).all()

    else:
        # Search existing global players
        stmt = select(Player).order_by(Player.id.desc()).limit(5)
        matching_players = db.session.scalars(stmt).all()

    return render_template(
        "partials/search_results.html",
        players=matching_players,
        query=query
    )


@api.route("/select-player", methods=["GET"])
def select_player():
    player_id = request.args.get("id")
    new_name = request.args.get("name")

    if player_id:
        player = db.session.get(Player, player_id)
        if not player:
            return "", 404
        return render_template("partials/existing_difficulty.html", player=player)

    if new_name:
        ratings = ["beginner", "intermediate", "advanced"]
        return render_template("partials/new_difficulty.html", new_name=new_name, ratings=ratings)


    return "", 400

@api.route("/search-tournament", methods=["GET"])
def search_tournament():
    query = request.args.get("q")
    if query:
        stmt = select(Tournament).where(Tournament.name.ilike(f"%{query}%")).limit(5)
        matching_tournaments = db.session.scalars(stmt).all()

    else:
        stmt = select(Tournament).order_by(Tournament.id.desc()).limit(5)
        matching_tournaments = db.session.scalars(stmt).all()

    return render_template(
        "partials/tournament_search_results.html",
        matching_tournaments = matching_tournaments,
        query = query
    )

@api.route("/new-player-rating", methods=["GET"])
def new_player_rating():
    name = request.args.get("name", "").strip()
    # Pass options matching your Player.difficulty domain
    ratings = ["beginner", "intermediate", "advanced"]

    return render_template(
        "partials/new_difficulty.html",
        player_name=name,
        ratings=ratings
    )

@api.route("/tournament/<int:tournament_id>/round/<int:round_num>", methods=["GET"])
def view_round(tournament_id, round_num):
    context = get_live_context(tournament_id, round_num)
    return render_template("partials/knockouts_live.html", tournament_id=tournament_id, **context)

@api.route("/tournament/<int:tournament_id>/standings/<string:scope>", methods=["GET"])
def view_standings(tournament_id, scope):
    # Optional round_num passed via query string if scope is 'round'
    round_num = request.args.get("round", type=int)

    # Calculate standings specifically for this view
    tournament = db.session.get(Tournament, tournament_id)
    if not tournament:
        abort(404, "Tournament not found")

    players_list = [tp.player for tp in tournament.player_associations]

    # If scope is 'round', filter by round_num; otherwise pass None for overall
    target_round = round_num if scope == "round" else None
    raw_standings = calculate_standings(tournament_id, players_list, target_round)

    summary = [
            {
                "name": s["player_name"],
                "matches_won": s["matches_won"],
                "matches_lost": s["matches_lost"],
                "games_won": s["games_won"],
                "games_lost": s["games_lost"],
                "points_won": s["points_won"],
                "points_lost": s["points_lost"],
            }
            for _, s in raw_standings
        ]

    return render_template(
        "partials/leaderboard.html",
        standings=summary,
        current_scope=scope,
        current_round=round_num or tournament.round_number,
        tournament_id=tournament_id,
    )
