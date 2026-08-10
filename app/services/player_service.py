from app.database import db
from app.exceptions import (
    ExistingTournamentPlayerError,
    PlayerNotFoundError,
    TournamentNotFoundError,
)
from app.models import Player, Tournament, TournamentPlayer


def register_player_to_tournament(tournament_id, player_id):

    tournament = db.session.get(Tournament, tournament_id)
    player = db.session.get(Player, player_id)

    if not player:
        raise PlayerNotFoundError("Player not ofund")

    if not tournament:
        raise TournamentNotFoundError(f"Tournament {tournament_id} not found")

    if db.session.get(TournamentPlayer, (player_id, tournament_id)):
        raise ExistingTournamentPlayerError("Player already added to tournament")

    tournament_player = TournamentPlayer(
        player=player,
        tournament=tournament,
        group_id=0,
    )

    db.session.add(tournament_player)
    db.session.commit()


def assign_player_to_group(tournament_id, player_id, group_id) -> bool:
    tournament_player = db.session.get(TournamentPlayer, (player_id, tournament_id))
    tournament_player.group_id = int(group_id)  # type: ignore
    db.session.commit()

    return True


def save_player_details(player_id, name, difficulty, tournament_id=""):
    player = db.session.get(Player, player_id)

    if not player:
        raise ValueError(f"Player {player_id} not found")

    if name and difficulty:
        player.name = name
        player.difficulty = difficulty

    db.session.commit()

    if tournament_id:
        tp = db.session.get(TournamentPlayer, (player_id, tournament_id))

        return tp

    return player


def delete_player_tournament(player_id, tournament_id):
    player = db.session.get(TournamentPlayer, (player_id, tournament_id))

    if not player:
        raise PlayerNotFoundError("Player not found")

    db.session.delete(player)
    db.session.commit()

    tournament = db.session.get(Tournament, tournament_id)

    if not tournament.player_associations:  # type: ignore
        return (
            """
        <tr id="no-players-row">
            <td colspan="3" class="text-center py-3">
                No players registered yet. Add one to get started!
            </td>
        </tr>
        """,
            200,
        )
    else:
        return "", 200
