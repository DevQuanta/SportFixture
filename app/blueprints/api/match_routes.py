from flask import current_app, render_template, request

from app.database import db
from app.exceptions import MatchNotFoundError
from app.models import Match, Tournament
from app.services.context_service import get_leaderboard_context, get_match_context
from app.services.tournament_service import calculate_standings, save_match_details

from . import api


@api.route("/matches/<int:match_id>/edit")
def edit_match(match_id):
    match = db.session.get(Match, match_id)

    return render_template("partials/matches/edit_match_card.html", match=match)


@api.route("/matches/<int:match_id>/save", methods=["POST"])
def save_match(match_id):
    payload = request.get_json()

    match = save_match_details(match_id, payload)

    scope = request.args.get("current_scope", "round")
    round_num = request.args.get("current_round")

    context = get_leaderboard_context(match, scope, round_num)

    match_card = render_template("partials/matches/match_card.html", match=match)
    leaderboard_card = render_template(
        "partials/leaderboard_table.html",
        **context,
        oob=True,
    )

    return match_card + leaderboard_card

@api.route("/match/view/<int:match_id>", methods=["GET"])
def view_match(match_id):
    match = db.session.get(Match, match_id)
    if not match:
        raise MatchNotFoundError("Match not found")

    match = get_match_context(match_id)
    return render_template("partials/matches/match_card.html", match=match)
