from collections import defaultdict

from flask import Blueprint, abort, current_app, make_response, render_template, request
from flask_login.utils import login_required
from jinja2.nodes import Stmt
from sqlalchemy import and_, select

from app.database import db
from app.models import Match, Player, Tournament, TournamentPlayer, TournamentStatus

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home_page():
    return render_template("main.html")


@main_bp.route("/knockouts")
def knockouts_page():
    return render_template("knockouts.html")


@main_bp.route("/admin")
@login_required
def admin_page():

    stmt = select(Tournament)
    tournaments = db.session.execute(stmt).scalars().all()

    selected_id = request.args.get("tournaments")

    step_html = None
    selected_tournament = db.session.get(Tournament, selected_id)
    if selected_tournament:
        # Fetch the actual tournament object from the DB
        step_html = template_router(selected_tournament.status)(selected_tournament.id)

    return render_template(
        "admin.html",
        tournaments=tournaments,
        tournament=selected_tournament,
        step_html=step_html,
        selected_tournament_id=int(selected_id)
        if selected_id and selected_id.isdigit()
        else None,
    )


@main_bp.route("/register-player", methods=["POST"])  # type: ignore
def register_player():
    name = request.form.get("player-name")
    difficulty = request.form.get("player-diff")
    tournament_id = request.form.get("tournament_id")

    stmt = select(Tournament).where(Tournament.id == int(tournament_id))  # type: ignore
    tournament = db.session.execute(stmt).scalar_one_or_none()

    player = Player()

    stmt = select(Player).where(Player.name == name)
    player = db.session.execute(stmt).scalar_one_or_none()

    if not player:
        player = Player(name=name, difficulty=difficulty)  # type: ignore
        db.session.add(player)

    tournament_player = TournamentPlayer(
        player=player,  # type: ignore
        tournament=tournament,  # type: ignore
        group_id=0,  # type: ignore
    )

    db.session.add(tournament_player)  # type: ignore
    db.session.commit()

    return render_template(
        "partials/player_rows.html", players=tournament.player_associations
    )


@main_bp.route("/select-tournament", methods=["POST"])  # type: ignore
def select_tournament():
    tournament_input = request.form.get("tournaments")

    if not tournament_input:
        return "<p class='error-msg'>Please select or type a tournament name.</p>"

    if tournament_input.isdigit():
        # Fetch existing tournament by ID
        stmt = select(Tournament).where(Tournament.id == int(tournament_input))
        tournament = db.session.execute(stmt).scalar_one_or_none()
    else:
        stmt = select(Tournament).where(Tournament.name == tournament_input)
        tournament = db.session.execute(stmt).scalar_one_or_none()

        if not tournament:
            tournament = Tournament(name=tournament_input)  # type: ignore
            db.session.add(tournament)
            db.session.commit()  # Committing generates the tournament.id automatically

    current_status = tournament.status
    response_html = template_router(current_status)(tournament.id)

    response = make_response(response_html)
    response.headers["HX-Push-Url"] = f"/admin?tournaments={tournament.id}"

    return response


def template_router(tournament_status):
    TOURNAMENT_TEMPLATES = {
        TournamentStatus.SETUP: step_1,
        TournamentStatus.REGISTRATION: step_2,
        TournamentStatus.ASSIGNMENT: step_3,
    }

    handler = TOURNAMENT_TEMPLATES.get(tournament_status)

    if not handler:
        raise ValueError("No view handler available")

    return handler


TOURNAMENT_STEPS = [
    TournamentStatus.SETUP,
    TournamentStatus.REGISTRATION,
    TournamentStatus.ASSIGNMENT,
    TournamentStatus.PREVIEW,
    TournamentStatus.LIVE,
    TournamentStatus.COMPLETED,
]


@main_bp.route("/admin/<int:tournament_id>/advance/", methods=["POST"])
def advance_tournament(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        abort(404, description="Tournament not found")

    current_app.logger.info(
        f"ADVANCE TRIGGERED. CURRENT STATUS IN DB: {tournament.status}"
    )

    curr_idx = TOURNAMENT_STEPS.index(tournament.status)

    if curr_idx + 1 < len(TOURNAMENT_STEPS):
        tournament.status = TOURNAMENT_STEPS[curr_idx + 1]
        db.session.commit()

    return template_router(tournament.status)(tournament.id)


@main_bp.route("/admin/<int:tournament_id>/previous/", methods=["POST"])
def previous_tournament(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        abort(404, description="Tournament not found")

    current_app.logger.info(
        f"ADVANCE TRIGGERED. CURRENT STATUS IN DB: {tournament.status}"
    )

    curr_idx = TOURNAMENT_STEPS.index(tournament.status)

    if curr_idx > 0:
        tournament.status = TOURNAMENT_STEPS[curr_idx - 1]
        db.session.commit()

    return template_router(tournament.status)(tournament_id)


@main_bp.route("/admin/<int:tournament_id>/step-1")
def step_1(tournament_id):
    stmt = select(Tournament).where(Tournament.id == tournament_id)
    tournament = db.session.execute(stmt).scalar_one_or_none()

    return render_template("partials/admin_step_1.html", tournament=tournament)


@main_bp.route("/admin/<int:tournament_id>/step-2")
def step_2(tournament_id):
    stmt = select(Tournament).where(Tournament.id == tournament_id)

    return view_tournament_seeding(tournament_id)  # type: ignore


@main_bp.route("/admin/<int:tournament_id>/step-3")
def step_3(tournament_id):
    stmt = select(Tournament).where(Tournament.id == tournament_id)
    tournament = db.session.execute(stmt).scalar_one_or_none()

    generate_round(tournament_id, 1)

    return render_template("partials/admin_step_3.html", tournament=tournament)


@main_bp.route("/edit-player/<int:player_id>")  # type: ignore
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)

    return render_template("partials/edit_player_row.html", player=player)


@main_bp.route("/save-player/<int:player_id>", methods=["POST"])  # type: ignore
def save_player(player_id):
    player = Player.query.get_or_404(player_id)

    updated_name = request.form.get("player-name")
    updated_diff = request.form.get("player-diff")

    player.name = updated_name
    player.difficulty = updated_diff

    db.session.commit()

    return render_template("partials/single_player_row.html", player=player)


@main_bp.route("/delete-player/<int:player_id>", methods=["DELETE"])
def delete_player(player_id):

    player = Player.query.get_or_404(player_id)

    db.session.delete(player)

    db.session.commit()

    return "", 200


@main_bp.route("/tournament/<int:tournament_id>/seeding")  # type: ignore
def view_tournament_seeding(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)

    tournament_players = tournament.player_associations  # type:ignore
    grouped_players = {0: []}

    for group_num in range(1, tournament.max_groups + 1):  # type:ignore
        grouped_players[group_num] = []

    for ticket in tournament_players:
        target_group = ticket.group_id  # type:ignore

        player_row = ticket.player

        if target_group is None:
            target_group = 0

        player_card = {
            "id": player_row.id,
            "name": player_row.name,
            "difficulty": player_row.difficulty,
        }

        grouped_players[target_group].append(player_card)

    return render_template(
        "partials/admin_step_2.html",
        grouped_players=grouped_players,
        tournament=tournament,
    )


@main_bp.route("/<int:tournament_id>/players/<int:player_id>/assign", methods=["POST"])  # type:ignore
def assign_player(tournament_id, player_id):
    tournament_player = db.session.get(TournamentPlayer, (player_id, tournament_id))

    tournament = db.session.get(Tournament, tournament_id)
    updated_group_id = request.form.get("group_id")

    tournament_player.group_id = int(updated_group_id)  # type: ignore

    db.session.commit()

    return view_tournament_seeding(tournament_id)


def group_pairings(round_id, tournament_id):
    tournament = db.session.get(Tournament, tournament_id)  # type: ignore
    num_groups = tournament.max_groups  # type: ignore
    current_app.logger.info(f"num groups is {num_groups}")

    groups = [[] for _ in range(num_groups)]
    tournament_players = tournament.player_associations  # type: ignore

    if round_id == 1:
        for tp in tournament_players:
            if tp.group_id is not None:
                groups[tp.group_id - 1].append(tp.player)  # type: ignore

    else:
        group_index = 0
        direction = 1

        players_list = [tp.player for tp in tournament.player_associations]  # type: ignore

        standings = calculate_standings(tournament_id, players_list, round_id - 1)

        for curr_player in standings:
            player = curr_player[0]
            groups[group_index].append(player)

            group_index += direction

            if group_index == num_groups:
                direction = -1
                group_index = num_groups - 1

            elif group_index == -1:
                direction = 1
                group_index = 0

    return groups


def generate_round(tournament_id, round_id, preview=True):
    tournament = db.session.get(Tournament, tournament_id)  # type: ignore

    num_groups = tournament.max_groups  # type: ignore
    current_app.logger.info(f"num groups is {num_groups}")

    groups = group_pairings(tournament_id, round_id)
    matches_data = []

    stmt = select(Match).filter_by(
        tournament_id=tournament_id,
        round_number=round_id
    )
    existing_matches = db.session.scalars(stmt).all()

    if existing_matches:
        matches_data = [
            {
                "id": match.id,
                "player_1_id": match.player_1_id,
                "player_2_id": match.player_2_id,
                "group_id": match.group_id,
                "round_number": match.round_number,
                "tournament_id": match.tournament_id,
            }
            for match in existing_matches
        ]

        current_app.logger.info(matches_data)

    else:
        for i in range(0, num_groups):
            current_app.logger.info(f"i is {i}")
            group_matches = draft_matches_for_group(groups[i], i + 1, tournament_id, round_id)
            matches_data.extend(group_matches) # type: ignore

    return matches_data


def draft_matches_for_group(
    player_ids, group_id, tournament_id, round_number, is_placement=False
):
    matches = []
    players = list(player_ids)

    if is_placement:
        pass

    if len(players) % 2 != 0:
        players.append(None)

    N = len(players)

    for _ in range(0, N - 1):
        H = N // 2

        top_row = players[:H]
        bottom_row = players[H:][::-1]

        for j in range(H):
            if not all([top_row[j], bottom_row[j]]):
                continue

            pair = (top_row[j], bottom_row[j])
            match = {
                "player_1_id": pair[0].id,
                "player_2_id": pair[1].id,
                "group_id": group_id,
                "round_number": round_number,
                "tournament_id": tournament_id,
            }

            matches.append(match)

        players = [players[0]] + [players[-1]] + players[1:-1]

    return matches


def commit_matches_for_group(matches_draft, tournament_id, is_placement=False):
    tournament = db.session.get(Tournament, tournament_id)
    if not tournament:
        abort(404, "Tournament not found")

    for match_draft in matches_draft:
        match = Match(
            tournament_id=match_draft["tournament_id"],
            player_1_id=match_draft["player_1_id"],
            player_2_id=match_draft["player_2_id"]  ,
            round_number=match_draft["round_number"],
            group_id=match_draft["group_id"],
        )

        tournament.matches.append(match)

    db.session.commit()


def get_ratio(won, lost):
    if lost == 0:
        return float("inf") + won
    return won / lost


def calculate_standings(tournament_id, players_list, round_id=None):
    stats = {
        player.id: {
            "player": player,
            "player_name": player.name,
            "matches_won": 0,
            "matches_lost": 0,
            "games_won": 0,
            "games_lost": 0,
            "points_won": 0,
            "points_lost": 0,
        }
        for player in players_list
    }

    stmt = select(Match).where(Match.tournament_id == tournament_id)

    if round_id:
        stmt = stmt.where(Match.round_number < round_id)

    matches = db.session.execute(stmt).scalars()

    for match in matches:  # type: ignore
        p1_games = 0
        p2_games = 0

        for game in match.games:
            if game.p1_score is None or game.p2_score is None:
                continue

            stats[match.player_1_id]["points_won"] += game.p1_score
            stats[match.player_1_id]["points_lost"] += game.p2_score

            stats[match.player_2_id]["points_won"] += game.p2_score
            stats[match.player_2_id]["points_lost"] += game.p1_score

            if game.p1_score > game.p2_score and game.p1_score >= 11:
                stats[match.player_1_id]["games_won"] += 1
                p1_games += 1

                stats[match.player_2_id]["games_lost"] += 1
            elif game.p2_score > game.p1_score and game.p2_score >= 11:
                stats[match.player_2_id]["games_won"] += 1
                p2_games += 1

                stats[match.player_1_id]["games_lost"] += 1

        if p1_games >= 3:
            stats[match.player_1_id]["matches_won"] += 1
            stats[match.player_2_id]["matches_lost"] += 1

        elif p2_games >= 3:
            stats[match.player_2_id]["matches_won"] += 1
            stats[match.player_1_id]["matches_lost"] += 1

    sorted_stats = sorted(
        stats.values(),
        key=lambda item: (
            get_ratio(item["matches_won"], item["matches_lost"]),
            get_ratio(item["games_won"], item["games_lost"]),
            get_ratio(item["points_won"], item["points_lost"]),
            item["player_name"],
        ),
        reverse=True,
    )

    standings = [(s["player"], s) for s in sorted_stats]

    return standings
