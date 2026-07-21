from flask import Blueprint, abort, render_template, current_app

from app.database import db
from app.models import Tournament

from app.services.workflow_service import TournamentStatus

from sqlalchemy import select

from app.services.tournament_service import get_current_or_latest_event
from app.services.context_service import get_live_context

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def home_page():
    return render_template("main.html")


@main_bp.route("/knockouts")
def knockouts_page():
    tournament = get_current_or_latest_event()

    current_app.logger.info("ID--->")
    current_app.logger.info(tournament.id)
    current_app.logger.info("Status--->")
    current_app.logger.info(tournament.status)

    if not tournament:
        abort(404, "No active tournaments")

    current_round = tournament.round_number
    context = get_live_context(tournament.id, current_round)

    return render_template("knockouts.html", **context)


    # return view_live_tournament(tournament_id, current_round)
