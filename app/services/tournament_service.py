from app.database import db
from app.models import Match, Tournament, MatchStatus

from sqlalchemy import select
from flask import session

from app.services.workflow_service import TournamentStatus
from app.exceptions import InvalidMatchScoreError, MatchNotFoundError


def get_ratio(won, lost):
    if lost == 0:
        return float("inf") if won > 0 else 0.0
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
        stmt = stmt.where(Match.round_number == round_id)

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


def get_or_create_tournament(tournament_input: str) -> Tournament:
    if tournament_input.isdigit():
            stmt = select(Tournament).where(Tournament.id == int(tournament_input))
            tournament = db.session.execute(stmt).scalar_one_or_none()
    else:
        stmt = select(Tournament).where(Tournament.name == tournament_input)
        tournament = db.session.execute(stmt).scalar_one_or_none()

        if not tournament:
            tournament = Tournament(name=tournament_input)  # type: ignore
            db.session.add(tournament)
            db.session.commit()  # Committing generates the tournament.id automatically

    if not tournament:
        raise ValueError(f"No tournament found for input: {tournament_input}")

    session.pop(f"draft_{tournament.id}", None)

    return tournament

def save_match_details(match_id, payload):
    match = db.session.get(Match, match_id)
    if not match:
        raise MatchNotFoundError("Match not found")

    for game in match.games:
        p1_key = f"game_{game.id}_p1"
        p2_key = f"game_{game.id}_p2"
        p1_score = int(payload[p1_key])
        p2_score = int(payload[p2_key])


        if not validate_scores(p1_score, p2_score):
            raise InvalidMatchScoreError("Invalid match score entered")

        if p1_key in payload:
            game.p1_score = int(p1_score) if val != "" else None
        if p2_key in payload:
            val = payload[p2_key]
            game.p2_score = int(p2_score) if val != "" else None

    if match.is_completed:
        match.status = MatchStatus.COMPLETE

    db.session.commit()

    return match

def get_round_view_context(tournament_id, round_number=None):
    pass


def get_current_or_latest_event():
    stmt = select(Tournament).where(Tournament.status == TournamentStatus.LIVE).limit(1)
    tournament = db.session.execute(stmt).scalar_one_or_none()

    if not tournament:
        raise ValueError("No active tournaments")

    return tournament

def validate_scores(p1: int, p2: int) -> bool:
    return (p1 == p2 + 2 and p1 >= 11) or (p2 == p1 + 2 and p2 >= 11)
