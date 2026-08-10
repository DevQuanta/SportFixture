from flask import current_app, session
from sqlalchemy import and_, or_, select

from app.database import db
from app.exceptions import (
    InvalidMatchScoreError,
    MatchNotFoundError,
    TournamentNotFoundError,
)
from app.models import Match, MatchStatus, Tournament
from app.services.workflow_service import TournamentStatus
from datetime import datetime, timedelta, timezone


def get_ratio(won, lost):
    if lost == 0:
        return float("inf") if won > 0 else 0.0
    return won / lost


def get_win_rate(won, lost):
    if lost == 0:
        return 100 if won > 0 else 0
    return (won / (lost + won)) * 100


def calculate_standings(tournament_id, players_list, round_id=None):
    stats = {
        player.id: {
            "player": player,
            "rank": rank + 1,
            "player_name": player.name,
            "matches_won": 0,
            "matches_lost": 0,
            "games_won": 0,
            "games_lost": 0,
            "points_won": 0,
            "points_lost": 0,
        }
        for rank, player in enumerate(players_list)
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

    for s in stats.values():
        s["match_points"] = s["matches_won"] * 3

    sorted_stats = sorted(
        stats.values(),
        key=lambda item: (
            item["match_points"],  # 1. Total Points (3 per win)
            item["games_won"] - item["games_lost"],  # 2. Game Differential
            get_ratio(item["games_won"], item["games_lost"]),  # 3. Game Ratio
            item["points_won"] - item["points_lost"],  # 4. Point Differential
            get_ratio(item["points_won"], item["points_lost"]),  # 5. Point Ratio
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


    return tournament


def save_match_details(match_id, payload):
    match = db.session.get(Match, match_id)
    if not match:
        raise MatchNotFoundError("Match not found")

    for game in match.games:
        p1_key = f"game_{game.id}_p1"
        p2_key = f"game_{game.id}_p2"
        if not (payload[p1_key] or payload[p2_key]):
            continue
        elif not (payload[p1_key] and payload[p2_key]) and (
            payload[p1_key] or payload[p2_key]
        ):
            raise InvalidMatchScoreError("Invalid match score entered")

        p1_score = int(payload[p1_key])
        p2_score = int(payload[p2_key])
        current_app.logger.info(f"p1_score: {p1_score}")
        current_app.logger.info(f"p2_score: {p2_score}")

        if not validate_scores(p1_score, p2_score):
            raise InvalidMatchScoreError("Invalid match score entered")

        if p1_key in payload:
            game.p1_score = int(p1_score) if p1_score != "" else None
        if p2_key in payload:
            game.p2_score = int(p2_score) if p2_score != "" else None

    if match.is_completed:
        match.status = MatchStatus.COMPLETE

    db.session.commit()

    return match



def fetch_live_event() -> Tournament | None:
    stmt = (
        select(Tournament)
        .where(
            or_(
                Tournament.status == TournamentStatus.LIVE,
            )
        )
        .order_by(Tournament.tournament_date)
        .limit(1)
    )
    tournament = db.session.execute(stmt).scalar_one_or_none()

    if tournament:
        return tournament


def get_tournament_status(tournament) -> str:
    timezone_offset = 0  # Pacific Standard Time (UTC−08:00)
    tzinfo = timezone(timedelta(hours=timezone_offset))
    today = datetime.now(tzinfo).date()

    if tournament is None:
        return ""


    if tournament.tournament_date == today:
        return "ongoing"
    elif tournament.tournament_date < today:
        return "upcoming"
    else:
        return "none"



def fetch_completed_events():
    stmt = (
        select(Tournament)
        .where(
            or_(
                Tournament.status == TournamentStatus.COMPLETED,
            )
        )
        .order_by(Tournament.tournament_date.desc())
    )
    tournaments = db.session.execute(stmt).scalars().all()

    tournaments = [
        {
            "id": tournament.id,
            "name": tournament.name,
        }
        for tournament in tournaments
    ]

    return tournaments


def validate_scores(p1: int, p2: int) -> bool:
    normal_game = (p1 >= p2 + 2 and p1 == 11) or (p2 >= p1 + 2 and p2 == 11)
    extended_game = (p1 == p2 + 2 and p1 > 11) or (p2 == p1 + 2 and p2 > 11)

    return normal_game or extended_game


def get_standings(tournament_id, scope, player_name="", round_num=None):
    # Calculate standings specifically for this view
    tournament = db.session.get(Tournament, tournament_id)
    if not tournament:
        raise TournamentNotFoundError("Tournament Not found")

    players_list = [tp.player for tp in tournament.player_associations]

    # If scope is 'round', filter by round_num; otherwise pass None for overall
    target_round = round_num if scope == "round" else None
    raw_standings = calculate_standings(tournament_id, players_list, target_round)

    summary = [
        {
            "name": s["player_name"],
            "rank": s["rank"],
            "pts": s["match_points"],
            "matches_won": s["matches_won"],
            "matches_lost": s["matches_lost"],
            "games_won": s["games_won"],
            "games_lost": s["games_lost"],
            "points_won": s["points_won"],
            "points_lost": s["points_lost"],
        }
        for _, s in raw_standings
        if player_name in s["player_name"]
    ]

    return summary


def is_round_completed(tournament_id):

    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise TournamentNotFoundError("Tournament not found")

    current_round = tournament.round_number

    has_incomplete = db.session.scalar(
        select(
            select(Match)
            .where(
                and_(
                    Match.tournament_id == tournament_id,
                    Match.round_number == current_round,
                    ~Match.is_completed,
                )
            )
            .exists()
        )
    )

    return has_incomplete


def search_tournaments(q: str) -> list[Tournament]:
    if q:
        stmt = select(Tournament).where(Tournament.name.ilike(f"%{q}%")).limit(5)
    else:
        stmt = select(Tournament).order_by(Tournament.id.desc()).limit(5)

    matching_tournaments = list(db.session.scalars(stmt).all())

    return matching_tournaments

def create_tournament(tournament_name):
    stmt = select(Tournament).where(Tournament.name == tournament_name)
    tournament = db.session.execute(stmt).scalar_one_or_none()

    if not tournament:
        tournament = Tournament(name=tournament_name)  # type: ignore
        db.session.add(tournament)
        db.session.commit()

    session.pop(f"draft_{tournament.id}", None)
    return tournament.id
