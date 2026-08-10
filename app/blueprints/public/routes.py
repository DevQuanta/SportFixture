from flask import Blueprint, current_app, render_template

from app.services.context_service import fetch_latest_event, get_today
from app.services.tournament_service import (
    fetch_completed_events,
)

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home_page():
    completed_tournaments = fetch_completed_events()
    latest_tournament = fetch_latest_event()
    today = get_today()

    return render_template(
        "main.html",
        past_tournaments=completed_tournaments,
        latest_tournament=latest_tournament,
        today=today
    )


@main_bp.route("/knockouts")
def knockouts_page():
    context = fetch_latest_event(with_context=True)

    return render_template("knockouts.html", **context)
