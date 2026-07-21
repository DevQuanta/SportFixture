from app.database import db
from sqlalchemy import select

from app.models import Player, Tournament, TournamentPlayer

def register_player_to_tournament(tournament_id, name, difficulty) -> Tournament:

    tournament = db.session.get(Tournament, tournament_id)
    if not tournament:
        raise ValueError(f"Tournament {tournament_id} not found")

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

    return tournament

def assign_player_to_group(tournament_id, player_id, group_id) -> bool:
    tournament_player = db.session.get(TournamentPlayer, (player_id, tournament_id))
    tournament_player.group_id = int(group_id)  # type: ignore
    db.session.commit()

    return True

def save_player_details(player_id, name, difficulty):
    player = db.session.get(Player, player_id)

    if not player:
        raise ValueError(f"Player {player_id} not found")

    if name and difficulty:
        player.name = name
        player.difficulty = difficulty

    db.session.commit()

    return player

def delete_player_tournament(player_id, tournament_id):
    player = db.session.get(Player, player_id)
    tournament = db.session.get(Tournament, tournament_id)

    if not player:
        raise ValueError(f"Player {player_id} not found")
    if not tournament:
        raise ValueError(f"Tournament {tournament_id} not found")

    db.session.delete(player)
    db.session.commit()
