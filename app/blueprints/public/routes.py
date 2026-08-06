from flask import Blueprint, abort, render_template, current_app
from app.services.tournament_service import fetch_live_event, get_tournaments, get_standings
from app.services.context_service import get_live_context
from datetime import datetime,  timezone, timedelta

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def home_page():
    tournaments = get_tournaments()
    latest_tournament = fetch_live_event()

    timezone_offset = 0 # Pacific Standard Time (UTC−08:00)
    tzinfo = timezone(timedelta(hours=timezone_offset))
    today = datetime.now(tzinfo).date()

    if not tournaments:
        return render_template("main.html", today = today)

    latest_tournament_id = latest_tournament.id
    standings = get_standings(latest_tournament_id, "overall")

    current_app.logger.info(latest_tournament.status)

    return render_template("main.html", tournament = latest_tournament, tournaments = tournaments, tournament_id = latest_tournament_id, player_name = '', standings = standings, today = today)


@main_bp.route("/knockouts")
def knockouts_page():
    tournament = fetch_live_event()
    if not tournament:
        return render_template("knockouts.html")

    current_app.logger.info("ID--->")
    current_app.logger.info(tournament.id)
    current_app.logger.info("Status--->")
    current_app.logger.info(tournament.status)


    current_round = tournament.round_number
    context = get_live_context(tournament.id, current_round)
    #current_app.logger.info(f"context = {context}")
    current_round = tournament.round_number

    return render_template("knockouts.html", tournament_id = tournament.id, **context)



    # return view_live_tournament(tournament_id, current_round)
