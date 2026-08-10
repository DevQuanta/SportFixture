from datetime import date

from flask import current_app, render_template, request
from sqlalchemy import and_, select

from app.blueprints.admin.renderer import get_admin_context
from app.database import db
from app.exceptions import (
    GroupNotEmptyError,
    TournamentNotFoundError,
)
from app.models import Tournament, TournamentPlayer
from app.services.context_service import get_live_context
from app.services.tournament_service import (
    fetch_completed_events,
    get_standings,
)
from app.services.workflow_service import advance_tournament_status

from . import api


@api.route(
    "/admin/tournament/<int:tournament_id>/round/<int:round_num>", methods=["GET"]
)
def view_round(tournament_id, round_num):
    context = get_live_context(tournament_id, round_num)
    return render_template("partials/knockouts_live.html", **context)


@api.route(
    "/admin/tournament/<int:tournament_id>/standings/<string:scope>", methods=["GET"]
)
def view_standings(tournament_id, scope):
    context = get_live_context(tournament_id, scope)
    return render_template("partials/knockouts_live.html", **context)


@api.route("/tournament/<int:tournament_id>/round/<int:round_num>", methods=["GET"])
def view_public_round(tournament_id, round_num):
    context = get_live_context(tournament_id, round_num)
    return render_template("partials/knockouts_public.html", **context)


@api.route("/tournament/<int:tournament_id>/standings/<string:scope>", methods=["GET"])
def view_public_standings(tournament_id, scope):
    context = get_live_context(tournament_id, scope)
    return render_template("partials/knockouts_public.html", **context)


@api.route("/leaderboard/filter", methods=["GET"])
def filter_leaderboard():
    tournament_id = request.args.get("tournament_id")
    player_name = request.args.get("player_name", "")
    tournaments = fetch_completed_events()

    standings = get_standings(tournament_id, "overall", player_name)
    tournament = db.session.get(Tournament, tournament_id)

    results = get_standings(tournament_id, "overall")
    oob = False

    if "change" in request.args:
        oob = True

    return render_template(
        "partials/results/leaderboard_search_results.html",
        tournament_id=int(tournament_id) if tournament_id else None,
        tournament=tournament,
        player_name=player_name,
        results=results,
        standings=standings,
        tournaments=tournaments,
        oob = oob
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
