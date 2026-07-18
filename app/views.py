from flask import Blueprint, render_template, request, current_app
from flask_login.utils import login_required
from sqlalchemy import select, and_
from collections import defaultdict

from app.database import db
from app.models import Player, Tournament, TournamentPlayer, Match

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


    return render_template("admin.html", tournaments=tournaments)


@main_bp.route("/register-player", methods=["POST"])  # type: ignore
def register_player():
    name = request.form.get("player-name")
    difficulty = request.form.get("player-diff")
    tournament_id = request.form.get("tournament_id")

    stmt = select(Tournament).where(Tournament.id == int(tournament_id)) # type: ignore
    tournament = db.session.execute(stmt).scalar_one_or_none()

    player = Player()

    stmt = select(Player).where(Player.name == name)
    player = db.session.execute(stmt).scalar_one_or_none()

    if not player:
        player = Player(name = name,difficulty = difficulty) # type: ignore
        db.session.add(player)


    tournament_player = TournamentPlayer(
        player = player, # type: ignore
        tournament = tournament, # type: ignore
        group_id = 0 # type: ignore
    )


    db.session.add(tournament_player)#type: ignore
    db.session.commit()


    return render_template("partials/player_rows.html", players=tournament.player_associations)

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
            tournament = Tournament(name=tournament_input) # type: ignore
            db.session.add(tournament)
            db.session.commit()  # Commit   ting generates the tournament.id automatically

    return step_1(tournament.id)

@main_bp.route("/admin/<int:tournament_id>/step-1")
def step_1(tournament_id):
    stmt = select(Tournament).where(Tournament.id == tournament_id)
    tournament = db.session.execute(stmt).scalar_one_or_none()

    return render_template("partials/admin_step_1.html", tournament=tournament)

@main_bp.route("/admin/<int:tournament_id>/step-2")
def step_2(tournament_id):
    stmt = select(Tournament).where(Tournament.id == tournament_id)
    tournament = db.session.execute(stmt).scalar_one_or_none()

    return view_tournament_seeding(tournament.id) # type: ignore

@main_bp.route("/admin/<int:tournament_id>/step-3")
def step_3(tournament_id):
    stmt = select(Tournament).where(Tournament.id == tournament_id)
    tournament = db.session.execute(stmt).scalar_one_or_none()
    return render_template("partials/admin_step_3.html", tournament=tournament)

@main_bp.route("/edit-player/<int:player_id>") # type: ignore
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)

    return render_template("partials/edit_player_row.html", player=player)



@main_bp.route("/save-player/<int:player_id>", methods=["POST"]) # type: ignore
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

@main_bp.route("/tournament/<int:tournament_id>/seeding") # type: ignore
def view_tournament_seeding(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)

    tournament_players = tournament.player_associations # type:ignore
    grouped_players = {0: []}

    for group_num in range(1, tournament.max_groups + 1): # type:ignore
        grouped_players[group_num] = []

    for ticket in tournament_players:
        target_group = ticket.group_id # type:ignore

        player_row = ticket.player

        if target_group is None:
            target_group = 0

        player_card = {
            "id": player_row.id,
            "name": player_row.name,
            "difficulty": player_row.difficulty
        }

        grouped_players[target_group].append(player_card)

    return render_template("partials/admin_step_2.html", grouped_players=grouped_players, tournament=tournament)


@main_bp.route("/<int:tournament_id>/players/<int:player_id>/assign", methods=["POST"]) # type:ignore
def assign_player(tournament_id, player_id):
    tournament_player = db.session.get(TournamentPlayer, (player_id, tournament_id))

    tournament = db.session.get(Tournament, tournament_id)
    updated_group_id = request.form.get("group_id")

    tournament_player.group_id = int(updated_group_id) # type: ignore

    db.session.commit()

    return view_tournament_seeding(tournament_id)

@main_bp.route("/tournaments/<int:tournament_id>/rounds/<int:round_number>/generate")
def generate_round(tournament_id, round_id):
    group_ids = defaultdict(list)
    tournament = db.session.get(Tournament, tournament_id) # type: ignore
    tournament_players = tournament.player_associations # type: ignore

    if round_id == 1:
        for tp in tournament_players:
            group_ids[tp.group_id].append(tp.player)

        for group_id in group_ids:
            pass

    else:
        group_index = 0
        direction = 1
        num_groups = tournament.max_groups # type: ignore

        groups = [[] for _ in range(num_groups)]

        players_list = [tp.player for tp in tournament.player_associations] # type: ignore

        standings = calculate_standings(tournament_id, players_list, round_id)

        for curr_player in standings:
            player_id = curr_player[0]
            groups[group_index].append(player_id)

            group_index += direction

            if group_index == num_groups:
                direction = -1
                group_index = num_groups - 1

            elif group_index == -1:
                direction = 1
                group_index = 0

        for i in range(1, num_groups + 1):
            create_matches_for_group(groups[i], tournament_id, round_id) # type: ignore

def create_matches_for_group(player_ids, tournament_id, round_number, group_id, is_placement=False):
    if is_placement:
        pass

    if len(player_ids) % 2 != 0:
        player_ids.append(None)

    N = len(player_ids)

    for _ in range(0, N - 1):
        H = N // 2

        top_row = player_ids[:H]
        bottom_row = player_ids[H:][::-1]

        for j in range(H):
            if not all([top_row[j], bottom_row[j]]):
                continue

            pair = (top_row[j], bottom_row[j])
            print(pair)

        player_ids = [player_ids[0]] + [player_ids[-1]] + player_ids[1:-1]





def get_ratio(won, lost):
    if lost == 0:
        return float('inf') + won
    return won / lost

def calculate_standings(tournament_id, players_list, group_id = None, round_id = None):
    stats = {
        player.id: {
            "player_name": player.player.name,
            "matches_won": 0,
            "matches_lost": 0,
            "games_won": 0,
            "games_lost": 0,
            "points_won": 0,
            "points_lost": 0
        } for player in players_list
    }

    matches = select(Match).where(Match.tournament_id == tournament_id)

    if round_id:
        matches = matches.where(Match.round_number < round_id)

    for match in matches: # type: ignore
        p1_games = 0
        p2_games = 0

        for game in match.games:
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

    standings = sorted(
        stats.items(),
        key=lambda item: (
            get_ratio(item[1]["matches_won"], item[1]["matches_lost"]),
            get_ratio(item[1]["games_won"], item[1]["games_lost"]),
            get_ratio(item[1]["points_won"], item[1]["points_lost"]),
            item[1]["player_name"]
        ),
        reverse=True
    )

    return standings
