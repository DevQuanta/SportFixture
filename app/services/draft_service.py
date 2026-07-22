from app.database import db
from app.exceptions import RoundNotReadyError, TournamentNotFoundError
from app.models import Match, Tournament, GameScore

from sqlalchemy import select, and_
from flask import current_app

from app.services.tournament_service import calculate_standings



def commit_matches_for_group(
    matches_draft, tournament_id, games_per_match=5, is_placement=False
):
    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise ValueError(f"Tournament {tournament_id} does not exist")

    for match_draft in matches_draft:
        match = Match(
            tournament_id=match_draft["tournament_id"],
            player_1_id=match_draft["player_1_id"],
            player_2_id=match_draft["player_2_id"],
            round_number=match_draft["round_number"],
            group_id=match_draft["group_id"],
        )

        for game_num in range(1, games_per_match + 1):
            match.games.append(
                GameScore(
                    match_id=match.id,
                    game_number=game_num,
                    p1_score=0,
                    p2_score=0,
                )
            )

        tournament.matches.append(match)

    db.session.commit()


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


def generate_round(tournament_id, round_id, preview=True):
    tournament = db.session.get(Tournament, tournament_id)  # type: ignore

    num_groups = tournament.max_groups  # type: ignore

    groups = group_pairings(tournament_id, round_id)
    matches_data = []

    stmt = select(Match).filter_by(tournament_id=tournament_id, round_number=round_id)
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



    else:
        for i, group_players in enumerate(groups, start=1):
            group_matches = draft_matches_for_group(
                group_players, i, tournament_id, round_id
            )
            matches_data.extend(group_matches)  # type: ignore

    current_app.logger.info(matches_data)
    return matches_data


def group_pairings(tournament_id, round_id):
    tournament = db.session.get(Tournament, tournament_id)

    if not tournament:
        raise ValueError(f"Tournament {tournament_id} not found")

    active_groups = {tp.group_id for tp in tournament.player_associations if tp.group_id}

    num_groups = max(active_groups) if active_groups else tournament.max_groups

    groups = [[] for _ in range(num_groups)]
    tournament_players = tournament.player_associations

    if round_id == 1:
        for tp in tournament_players:
            if tp.group_id is not None and tp.group_id > 0:
                groups[tp.group_id - 1].append(tp.player)

    else:
        group_index = 0
        direction = 1

        players_list = [tp.player for tp in tournament.player_associations]

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

def fetch_grouped_players(tournament):
    tournament_players = tournament.player_associations
    grouped_players = {0: []}

    for group_num in range(1, tournament.max_groups + 1):
        grouped_players[group_num] = []

    for ticket in tournament_players:
        target_group = ticket.group_id

        player_row = ticket.player

        if target_group is None:
            target_group = 0

        player_card = {
            "id": player_row.id,
            "name": player_row.name,
            "difficulty": player_row.difficulty,
        }

        grouped_players[target_group].append(player_card)

    return grouped_players


def get_next_round(tournament_id):
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

    if has_incomplete:
        raise RoundNotReadyError("Current round has incomplete matches")

    matches_draft = generate_round(tournament_id, current_round + 1)
    commit_matches_for_group(matches_draft, tournament_id)

    tournament.round_number += 1
    db.session.commit()

    return True
