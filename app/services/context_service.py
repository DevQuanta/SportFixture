from itertools import groupby

from flask import session
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.database import db
from app.exceptions import MatchNotFoundError
from app.models import Match, Tournament
from app.services.draft_service import fetch_grouped_players
from app.services.tournament_service import (
    calculate_standings,
    get_standings,
    get_win_rate,
)


def get_step_1_context(tournament_id):
    """Prepares template context for Step 1."""

    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise ValueError(f"Tournament {tournament_id} not found")

    return {"tournament": tournament, "current_step": 1}


def get_step_2_context(tournament_id):
    """Prepares template context for Step 2."""

    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise ValueError(f"Tournament {tournament_id} not found")

    return {"tournament": tournament, "current_step": 2}


def get_step_3_context(tournament_id):
    """Prepares template context for Step 3 (Draft Preview)."""

    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise ValueError(f"Tournament {tournament_id} not found")

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
        raise ValueError(f"Tournament {tournament_id} not found")

    return {
        "tournament": tournament,
    }


def get_live_context(tournament_id, scope="round"):
    tournament = db.session.get(Tournament, tournament_id)
    if not tournament:
        raise ValueError(f"Tournament {tournament_id} not found")

    target_round = tournament.round_number

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
            "matches_won": s["matches_won"],
            "matches_lost": s["matches_lost"],
            "games_won": s["games_won"],
            "games_lost": s["games_lost"],
            "points_won": s["points_won"],
            "points_lost": s["points_lost"],
        }
        for _, s in standings
    ]

    context = {
        "active_round": rounds[target_round - 1] if rounds else None,
        "current_round": target_round,  # The round being viewed
        "max_round": tournament.round_number,  # Highest round reached so far
        "all_rounds": [r["number"] for r in rounds],  # e.g. [1, 2, 3]
        "standings": summary,
        "current_scope": scope,
    }
    return context


def get_completed_context(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)
    if not tournament:
        raise ValueError(f"Tournament {tournament_id} not found")

    standings = get_standings(tournament_id, "overall")

    winners = [
        {
            "name": standings[n]["name"],
            "win_rate": get_win_rate(
                standings[n]["matches_won"], standings[n]["matches_lost"]
            ),
        }
        for n in range(min(3, len(standings)))
    ]

    return {"tournament": tournament, "standings": standings, "winners": winners}


def get_match(match_id):
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
