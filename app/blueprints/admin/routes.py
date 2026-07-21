from flask import Blueprint, abort, render_template, request, session
from flask_login import login_required
from app.database import db
from app.models import Tournament

from app.services.workflow_service import regress_tournament_status, advance_tournament_status

from app.blueprints.admin.renderer import render_admin_step
from app.services.draft_service import commit_matches_for_group, generate_round, fetch_grouped_players

from sqlalchemy import select

from app.services.workflow_service import TournamentStatus

admin = Blueprint("admin", __name__)

@admin.route("/admin/<int:tournament_id>/advance/", methods=["POST"])
def advance_tournament(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        abort(404, description="Tournament not found")

    advance_tournament_status(tournament_id)
    return render_admin_step(tournament_id)



@admin.route("/admin/<int:tournament_id>/previous/", methods=["POST"])
def previous_tournament(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        abort(404, description="Tournament not found")

    regress_tournament_status(tournament_id)
    return render_admin_step(tournament_id)


@admin.route("/admin")
@login_required
def admin_page():

    stmt = select(Tournament)
    tournaments = db.session.execute(stmt).scalars().all()

    selected_id = request.args.get("tournaments")

    step_html = None
    selected_tournament = db.session.get(Tournament, selected_id)
    if selected_tournament:
        # Fetch the actual tournament object from the DB
        step_html = render_admin_step(selected_id)

    return render_template(
        "admin.html",
        tournaments=tournaments,
        tournament=selected_tournament,
        step_html=step_html,
        selected_tournament_id=int(selected_id)
        if selected_id and selected_id.isdigit()
        else None,
    )


@admin.route("/admin/<int:tournament_id>/publish", methods=["POST"])
def publish_tournament(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        abort(404, "Tournament not found")

    session_key = f"draft_{tournament_id}"
    matches_draft = session.get(session_key)
    if not matches_draft:
        matches_draft = generate_round(tournament_id, 1)

    if not tournament.matches:
        commit_matches_for_group(matches_draft, tournament_id)

        session.pop(f"draft_{tournament.id}", None)

    advance_tournament_status(tournament_id)
    return render_admin_step(tournament_id)

    # return view_live_tournament(tournament_id, current_round)

@admin.route("/tournament/<int:tournament_id>/round/advance")
def next_round(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise ValueError(f"Tournament {tournament_id} not found")

    current_round = tournament.round_number

    matches_draft = generate_round(tournament_id, current_round + 1)

    commit_matches_for_group(matches_draft, tournament_id)
