from app.services.workflow_service import TournamentStatus
from flask import render_template, current_app, abort

from app.services.context_service import get_step_3_context, get_live_context
from app.services.tournament_service import get_standings, get_win_rate
from app.services.draft_service import fetch_grouped_players

from app.database import db
from app.models import Tournament

def render_admin_step(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise ValueError(f"Tournament {tournament_id} not found")

    tournament_status = tournament.status

    current_app.logger.info(f"Status -> {tournament_status}")

    match tournament_status:
        case TournamentStatus.SETUP:
            return render_template("partials/admin_step_0.html", current_step = 1, tournament=tournament)
        case TournamentStatus.REGISTRATION:
            return render_template("partials/admin_step_1.html", current_step = 2, tournament = tournament)
        case TournamentStatus.ASSIGNMENT:
            grouped_players = fetch_grouped_players(tournament)

            return render_template(
                "partials/admin_step_2.html",
                grouped_players=grouped_players,
                tournament=tournament,
                current_step = 3,
            )

        case TournamentStatus.PREVIEW:
            context = get_step_3_context(tournament)
            #current_app.logger.info(context)
            return render_template("partials/admin_step_3.html", current_step = 4, **context)

        case TournamentStatus.LIVE:
            current_round = tournament.round_number
            context = get_live_context(tournament_id, current_round)
            #current_app.logger.error(f"context = {context}")
            return render_template("partials/knockouts_live.html", tournament_id = tournament_id, **context)

        case TournamentStatus.COMPLETED:

            current_app.logger.info("ending tournament")
            standings =  get_standings(tournament_id, "overall")

            winners = [{
                "name": standings[n]['name'],
                "win_rate": get_win_rate(standings[n]['matches_won'], standings[n]['matches_lost'])
            } for n in range(3)]

            current_app.logger.info("standings calculated")
            current_app.logger.info(f"winners: {winners}")


            return render_template("partials/summary.html", winners = winners, standings = standings)
