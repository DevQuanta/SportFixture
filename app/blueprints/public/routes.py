from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, render_template

from app.services.context_service import get_live_context
from app.services.tournament_service import (
    fetch_completed_events,
    fetch_live_event,
    get_standings,
    get_tournament_status,
)

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home_page():
    tournaments = fetch_completed_events()
    latest_tournament = fetch_live_event()
    status = get_tournament_status(latest_tournament)
    timezone_offset = 0  # Pacific Standard Time (UTC−08:00)
    tzinfo = timezone(timedelta(hours=timezone_offset))
    today = datetime.now(tzinfo).date()

    if latest_tournament:
        latest_tournament_id = latest_tournament.id
        standings = get_standings(latest_tournament_id, "overall")

        return render_template(
            "main.html",
            past_tournaments=tournaments,
            latest_tournament=latest_tournament,
            player_name="",
            standings=standings,
            status=status,
            today=today,
        )
    else:
        latest_tournament_id = tournaments[0]["id"]
        standings = get_standings(latest_tournament_id, "overall")
        return render_template(
            "main.html",
            past_tournaments=tournaments,
            player_name="",
            status=status,
            today=today,
            standings = standings
        )


@main_bp.route("/knockouts")
def knockouts_page():
    tournament = fetch_live_event()
    current_app.logger.info(tournament)
    if not tournament:
        return render_template("knockouts.html")

    context = get_live_context(tournament.id, "overall")
    current_app.logger.info(f"context = {context}")

    return render_template("knockouts.html", **context)
