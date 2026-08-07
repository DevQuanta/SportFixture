from flask import abort, current_app, render_template

from app.database import db
from app.models import Tournament
from app.services.context_service import (
    get_completed_context,
    get_live_context,
    get_step_1_context,
    get_step_2_context,
    get_step_3_context,
    get_step_4_context,
)
from app.services.draft_service import fetch_grouped_players
from app.services.tournament_service import get_standings, get_win_rate
from app.services.workflow_service import TournamentStatus


def get_admin_context(tournament_id) -> tuple[str, dict]:
    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise ValueError(f"Tournament {tournament_id} not found")

    tournament_status = tournament.status
    content_template = ""
    context = {}

    match tournament_status:
        case TournamentStatus.SETUP:
            content_template = "partials/steps/admin_step_1.html"
            context = get_step_1_context(tournament_id)
        case TournamentStatus.REGISTRATION:
            content_template = "partials/steps/admin_step_2.html"
            context = get_step_2_context(tournament_id)
        case TournamentStatus.ASSIGNMENT:
            content_template = "partials/steps/admin_step_3.html"
            context = get_step_3_context(tournament_id)
        case TournamentStatus.PREVIEW:
            content_template = "partials/steps/admin_step_4.html"
            context = get_step_4_context(tournament_id)
        case TournamentStatus.LIVE:
            content_template = "partials/knockouts_live.html"
            context = get_live_context(tournament_id)
        case TournamentStatus.COMPLETED:
            content_template = "partials/summary.html"
            context = get_completed_context(tournament_id)
            current_app.logger.info(f"completed context: {context}")

    return (content_template, context)
