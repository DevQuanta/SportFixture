from datetime import date

from flask import Blueprint, current_app, make_response, render_template, request
from sqlalchemy import and_, select

from app.blueprints.admin.renderer import get_admin_context
from app.database import db
from app.exceptions import (
    GroupNotEmptyError,
    MatchNotFoundError,
    TournamentNotFoundError,
)
from app.models import Match, Player, Tournament, TournamentPlayer
from app.services.context_service import get_live_context, get_match
from app.services.player_service import (
    assign_player_to_group,
    delete_player_tournament,
    register_player_to_tournament,
    save_player_details,
)
from app.services.tournament_service import (
    calculate_standings,
    get_or_create_tournament,
    get_standings,
    get_tournaments,
    save_match_details,
)
from app.services.workflow_service import advance_tournament_status

api = Blueprint("api", __name__)


@api.route("/matches/<int:match_id>/edit")
def edit_match(match_id):
    match = db.session.get(Match, match_id)

    return render_template("partials/edit_match_card.html", match=match)


@api.route("/edit-player/<int:player_id>")  # type: ignore
def edit_player(player_id):
    tournament_id = request.args.get("tournament_id", "")
    tournament = db.session.get(Tournament, tournament_id)
    player = db.session.get(Player, player_id)
    return render_template(
        "partials/edit_player_row.html", player=player, tournament=tournament
    )


@api.route("/save-player/<int:player_id>", methods=["POST"])  # type: ignore
def save_player(player_id):
    updated_name = request.form.get("player-name")
    updated_diff = request.form.get("player-diff")

    tournament_id = request.args.get("tournament_id", "")
    tournament = db.session.get(Tournament, tournament_id)

    player = save_player_details(player_id, updated_name, updated_diff)
    return render_template(
        "partials/single_player_row.html", player=player, tournament=tournament
    )


@api.route("/delete-player/<int:player_id>", methods=["DELETE"])
def delete_player(player_id):
    tournament_id = request.args.get("tournament_id", "")

    if tournament_id:
        current_app.logger.info("deleting")
        delete_player_tournament(player_id, tournament_id)

    return "", 200


@api.route("/matches/<int:match_id>/save", methods=["POST"])
def save_match(match_id):
    payload = request.get_json()

    match = save_match_details(match_id, payload)
    players_list = [tp.player for tp in match.tournament.player_associations]
    standings = calculate_standings(
        match.tournament_id, players_list, match.round_number
    )

    tournament = db.session.get(Tournament, match.tournament_id)

    if not tournament:
        raise TournamentNotFoundError("Tournament not found")

    scope = request.args.get("current_scope", "round")
    round_num = request.args.get("current_round")

    current_app.logger.info(payload)

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
    leaderboard_card = render_template(
        "partials/leaderboard.html",
        current_scope=scope,
        current_round=round_num or tournament.round_number,
        tournament_id=tournament.id,
        **context,
        oob=True,
    )

    return match_card + leaderboard_card


@api.route("/<int:tournament_id>/players/<int:player_id>/assign", methods=["POST"])  # type:ignore
def assign_player(tournament_id, player_id):
    updated_group_id = request.form.get("group_id")

    assign_player_to_group(tournament_id, player_id, updated_group_id)
    (template, context) = get_admin_context(tournament_id)

    return render_template(template, **context)


def register_player():
    difficulty = request.form.get("player-diff")




@api.route("/players", methods=["GET", "POST"])
def search_players():

    if request.method == "GET":
        player_id = request.args.get("id", "")
        if player_id:
            player = db.session.get(Player, player_id)
            if not player:
                return "", 404
            return render_template("partials/existing_difficulty.html", player=player)

        if "new-player" in request.args:
            ratings = ["beginner", "intermediate", "advanced"]
            return render_template("partials/new_difficulty.html", ratings=ratings)

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
            "partials/single_player_row.html",
            player=player,
            tournament=tournament,
        )

    return "", 400


@api.route("/tournament/<int:tournament_id>/round/<int:round_num>", methods=["GET"])
def view_round(tournament_id, round_num):
    context = get_live_context(tournament_id, round_num)
    return render_template(
        "partials/knockouts_live.html", tournament_id=tournament_id, **context
    )


@api.route("/tournament/<int:tournament_id>/standings/<string:scope>", methods=["GET"])
def view_standings(tournament_id, scope, player_name=""):
    round_num = request.args.get("round", type=int)
    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise TournamentNotFoundError("Tournament not found")

    summary = get_standings(tournament_id, scope, player_name, round_num)

    return render_template(
        "partials/leaderboard.html",
        standings=summary,
        current_scope=scope,
        current_round=round_num or tournament.round_number,
        tournament_id=tournament_id,
    )


@api.route("/match/view/<int:match_id>", methods=["GET"])
def view_match(match_id):
    match = db.session.get(Match, match_id)
    if not match:
        raise MatchNotFoundError("Match not found")

    match = get_match(match_id)
    return render_template("partials/match_card.html", match=match)


@api.route("/leaderboard/filter", methods=["GET"])
def filter_leaderboard():
    tournament_id = request.args.get("tournament_id")
    player_name = request.args.get("player_name", "")
    tournaments = get_tournaments()

    # returning standings
    #
    standings = get_standings(tournament_id, "overall", player_name)
    tournament = db.session.get(Tournament, tournament_id)
    current_app.logger.info(standings)
    # current_app.logger.info(tournament_id, player_name)

    return render_template(
        "partials/_leaderboard_main.html",
        tournament_id=int(tournament_id) if tournament_id else None,
        tournament=tournament,
        player_name=player_name,
        standings=standings,
        tournaments=tournaments,
    )


@api.route("/tournament/<int:tournament_id>/end", methods=["POST"])
def end_tournament(tournament_id: int):
    advance_tournament_status(tournament_id)

    (template, context) = get_admin_context(tournament_id)
    return render_template(template, **context)

@api.route("/tournament/<int:tournament_id>/setup", methods=["POST"])
def setup_tournament(tournament_id):
    tournament_name = request.form.get("tournament-name", "")
    max_groups = request.form.get("group-number", "")
    max_rounds = request.form.get("round-number", "")

    date_str = request.form.get("date")

    current_app.logger.info(tournament_name, max_groups, max_rounds)

    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise TournamentNotFoundError("Tournament not found")

    if tournament_name:
        tournament.name = tournament_name
    if max_groups:
        tournament.max_groups = int(max_groups)
    if max_rounds:
        tournament.max_rounds = int(max_rounds)
    if date_str:
        # Convert string to a Python date object
        tournament_date = date.fromisoformat(date_str)
        tournament.tournament_date = tournament_date

    db.session.commit()

    advance_tournament_status(tournament_id)

    (template, context) = get_admin_context(tournament_id)
    return render_template(template, **context)


@api.route(
    "/tournament/<int:tournament_id>/group/<int:group_number>/remove", methods=["POST"]
)
def remove_group(tournament_id, group_number):
    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        return TournamentNotFoundError("Tournament not found")

    has_players = db.session.scalar(
        select(
            select(TournamentPlayer)
            .where(
                and_(
                    TournamentPlayer.tournament_id == tournament_id,
                    TournamentPlayer.group_id == group_number,
                )
            )
            .exists()
        )
    )

    if has_players:
        raise GroupNotEmptyError("Group has existing players, please move them")

    tournament.max_groups -= 1
    db.session.commit()

    (template, context) = get_admin_context(tournament_id)
    return render_template(template, **context)
