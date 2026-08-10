from datetime import datetime, timedelta, timezone
from itertools import groupby

from flask import session
from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload, selectinload

from app.database import db
from app.exceptions import (
    InsufficientPlayersError,
    MatchNotFoundError,
    TournamentNotFoundError,
)
from app.models import Match, Tournament, TournamentStatus
from app.services.draft_service import fetch_grouped_players, generate_round
from app.services.tournament_service import (
    calculate_standings,
    get_standings,
    get_win_rate,
)
from app.services.workflow_service import regress_tournament_status


def get_step_1_context(tournament_id):
    """Prepares template context for Step 1."""

    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise TournamentNotFoundError(f"Tournament {tournament_id} not found")

    return {"tournament": tournament, "current_step": 1}


def get_step_2_context(tournament_id):
    """Prepares template context for Step 2."""

    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise TournamentNotFoundError(f"Tournament {tournament_id} not found")

    return {"tournament": tournament, "tournament_id": tournament.id, "current_step": 2}


def get_step_3_context(tournament_id):
    """Prepares template context for Step 3 (Draft Preview)."""

    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise TournamentNotFoundError(f"Tournament {tournament_id} not found")

    if not len(tournament.player_associations) >= 2:
        regress_tournament_status(tournament_id)
        raise InsufficientPlayersError("Please add at least 2 players")

    grouped_players = fetch_grouped_players(tournament)

    return {
        "tournament": tournament,
        "grouped_players": grouped_players,
        "current_step": 3,
    }


def get_step_4_context(tournament_id):
    """Prepares template context for Step 4 (Draft Preview)."""
    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise TournamentNotFoundError(f"Tournament {tournament_id} not found")

    session_key = f"draft_{tournament.id}"

    if not session.get(session_key):
        matches_data = generate_round(tournament.id, 1)
        session[session_key] = matches_data

    players_map = {p.player.id: p.player.name for p in tournament.player_associations}

    return {
        "tournament": tournament,
        "current_step": 4,
        "matches_data": session[session_key],
        "players_map": players_map,
    }


def get_leaderboard_context(match: Match, scope, round_num):
    players_list = [tp.player for tp in match.tournament.player_associations]
    standings = calculate_standings(
        match.tournament_id, players_list, match.round_number
    )

    tournament = db.session.get(Tournament, match.tournament_id)

    if not tournament:
        raise TournamentNotFoundError(f"Tournament {match.tournament_id} not found")

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
        for _, _, s in standings
    ]

    context = {
        "standings": summary,
        "tournament_id": tournament.id,
        "current_scope": scope,
        "current_round": round_num or tournament.round_number,
        "tournament": tournament,
    }

    return context


def get_live_context(tournament_id, scope="round", round_num=None):
    tournament = db.session.get(Tournament, tournament_id)
    if not tournament:
        raise TournamentNotFoundError(f"Tournament {tournament_id} not found")

    target_round = round_num if round_num is not None else tournament.round_number

    stmt = (
        select(Match)
        .where(
            Match.tournament_id == tournament_id,
        )
        .options(
            joinedload(Match.player_1),
            joinedload(Match.player_2),
            selectinload(Match.games),
        )
        .order_by(Match.round_number, Match.group_id)
    )

    matches = db.session.execute(stmt).scalars().all()

    rounds = []

    for round_number, round_matches_iter in groupby(
        matches, key=lambda m: m.round_number
    ):
        round_matches = list(round_matches_iter)
        groups = []

        for group_id, group_matches_iter in groupby(
            round_matches, key=lambda m: m.group_id
        ):
            group_matches = []

            for m in group_matches_iter:
                match_dict = {
                    "id": m.id,
                    "player_1": {
                        "id": m.player_1.id,
                        "name": m.player_1.name,
                    }
                    if m.player_1
                    else None,
                    "player_2": {
                        "id": m.player_2.id,
                        "name": m.player_2.name,
                    }
                    if m.player_2
                    else None,
                    "games": [
                        {
                            "id": g.id,
                            "game_number": g.game_number,
                            "p1_score": g.p1_score,
                            "p2_score": g.p2_score,
                        }
                        for g in m.games
                    ],
                }

                group_matches.append(match_dict)

            groups.append(
                {"id": group_id, "label": f"Group {group_id}", "matches": group_matches}
            )

        rounds.append(
            {"number": round_number, "label": f"Round {round_number}", "groups": groups}
        )

    players_list = [tp.player for tp in tournament.player_associations]  # type: ignore

    round_for_standings = target_round if scope == "round" else None
    standings = calculate_standings(tournament_id, players_list, round_for_standings)

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
        for _, _, s in standings
    ]

    context = {
        "active_round": rounds[target_round - 1]
        if rounds and scope != "overall"
        else None,
        "current_round": target_round,  # The round being viewed
        "max_round": tournament.round_number,  # Highest round reached so far
        "all_rounds": [r["number"] for r in rounds],  # e.g. [1, 2, 3]
        "standings": summary,
        "current_scope": scope,
        "tournament": tournament,
    }
    return context


def get_completed_context(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise TournamentNotFoundError(f"Tournament {tournament_id} not found")

    standings = get_standings(tournament_id, "overall")

    stmt = select(Tournament).where(Tournament.status == TournamentStatus.COMPLETED)
    tournaments = db.session.execute(stmt).scalars().all()

    winners = [
        {
            "name": standings[n]["name"],
            "win_rate": get_win_rate(
                standings[n]["matches_won"], standings[n]["matches_lost"]
            ),
        }
        for n in range(min(3, len(standings)))
    ]

    return {
        "tournament": tournament,
        "tournaments": tournaments,
        "standings": standings,
        "winners": winners,
    }


def get_match_context(match_id):
    match = db.session.get(Match, match_id)

    if not match:
        return MatchNotFoundError("Match not found")

    match_dict = {
        "id": match.id,
        "player_1": {
            "id": match.id,
            "name": match.player_1.name,
        }
        if match.player_1
        else None,
        "player_2": {
            "id": match.player_2.id,
            "name": match.player_2.name,
        }
        if match.player_2
        else None,
        "games": [
            {
                "id": g.id,
                "game_number": g.game_number,
                "p1_score": g.p1_score,
                "p2_score": g.p2_score,
            }
            for g in match.games
        ],
    }

    return match_dict


def get_tournament_status(tournament) -> str:
    today = get_today()

    if tournament is None:
        return ""

    if tournament.tournament_date == today:
        return "ongoing"
    elif tournament.tournament_date < today:
        return "upcoming"
    else:
        return "none"


def get_today():
    timezone_offset = 0  # Pacific Standard Time (UTC−08:00)
    tzinfo = timezone(timedelta(hours=timezone_offset))
    today = datetime.now(tzinfo).date()

    return today


def fetch_latest_event(with_context=False) -> dict:
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

    if not tournament:
        return {}

    latest_tournament_id = tournament.id

    if with_context:
        context = get_live_context(latest_tournament_id, "overall")
        return context

    standings = get_standings(latest_tournament_id, "overall")
    status = get_tournament_status(tournament)

    return {"id": latest_tournament_id, "standings": standings, "status": status}
