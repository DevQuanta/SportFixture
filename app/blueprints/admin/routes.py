from flask import (
    Blueprint,
    abort,
    current_app,
    make_response,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import login_required

from app.blueprints.admin.renderer import (
    get_admin_context,
)
from app.database import db
from app.exceptions import TournamentNotFoundError
from app.models import Tournament
from app.services.draft_service import (
    commit_matches_for_group,
    generate_round,
    get_next_round,
)
from app.services.tournament_service import create_tournament, search_tournaments
from app.services.workflow_service import (
    advance_tournament_status,
    regress_tournament_status,
)

admin = Blueprint("admin", __name__)


@admin.route("/admin/<int:tournament_id>/advance/", methods=["POST"])
def advance_tournament(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise TournamentNotFoundError("Tournament not found")

    advance_tournament_status(tournament_id)
    (template, context) = get_admin_context(tournament_id)

    return render_template(template, **context)


@admin.route("/admin/<int:tournament_id>/previous/", methods=["POST"])
def previous_tournament(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise TournamentNotFoundError("Tournament not found")

    regress_tournament_status(tournament_id)
    (template, context) = get_admin_context(tournament_id)

    return render_template(template, **context)


@admin.route("/admin", methods=["GET", "POST"])
@login_required
def admin_page():
    is_htmx = request.headers.get("HX-Request") == "true"
    tournament_id = request.args.get("id", "")

    if request.method == "GET":

        if is_htmx and tournament_id:
            current_app.logger.info("htmx and tournament id")
            (template, step_context) = get_admin_context(tournament_id)
            return render_template(template, **step_context)

        elif is_htmx and "query" in request.args:
            current_app.logger.info("query and htmx")
            query = request.args.get("query", "")
            matching_tournaments = search_tournaments(query)
            current_app.logger.info(matching_tournaments)

            return render_template(
                "partials/results/tournament_search_results.html",
                matching_tournaments=matching_tournaments,
                query = query
            )

        if tournament_id:
            current_app.logger.info("only tournament id")
            (template, step_context) = get_admin_context(tournament_id)
            current_app.logger.info(step_context)
            return render_template(
                "admin.html", content_template=template, **step_context
            )

    elif request.method == "POST":
        if is_htmx and "query" in request.form:
            name = request.form.get("query", "")
            tournament_id = create_tournament(name)

            (template, step_context) = get_admin_context(tournament_id)

            response = make_response(render_template(template, **step_context))

            response.headers["HX-Push-Url"] = url_for(
                "admin.admin_page",
                id=tournament_id,
            )

            return response

    return render_template("admin.html")


@admin.route("/admin/<int:tournament_id>/publish/", methods=["POST"])
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
    (template, context) = get_admin_context(tournament_id)

    return render_template(template, **context)


# return view_live_tournament(tournament_id, current_round)
@admin.route("/tournament/<int:tournament_id>/round/advance", methods=["POST"])
def next_round(tournament_id):
    is_placement_round = request.args.get("placement", False)

    get_next_round(tournament_id, bool(is_placement_round))

    (template, context) = get_admin_context(tournament_id)
    return render_template(template, **context)
