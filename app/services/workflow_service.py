from app.models import TournamentStatus, Tournament
from app.database import db

TOURNAMENT_STEPS = [
    TournamentStatus.SETUP,
    TournamentStatus.REGISTRATION,
    TournamentStatus.ASSIGNMENT,
    TournamentStatus.PREVIEW,
    TournamentStatus.LIVE,
    TournamentStatus.COMPLETED,
]

def regress_tournament_status(tournament_id) -> bool:
    tournament = db.session.get(Tournament, tournament_id)
    if not tournament:
        raise ValueError(f"Tournament {tournament_id} not found")

    curr_idx = TOURNAMENT_STEPS.index(tournament.status)

    if curr_idx > 0:
        tournament.status = TOURNAMENT_STEPS[curr_idx - 1]
        db.session.commit()
        return True

    return False

def advance_tournament_status(tournament_id) -> bool:
    tournament = db.session.get(Tournament, tournament_id)
    if not tournament:
        raise ValueError(f"Tournament {tournament_id} not found")

    curr_idx = TOURNAMENT_STEPS.index(tournament.status)

    if curr_idx + 1 < len(TOURNAMENT_STEPS):
        tournament.status = TOURNAMENT_STEPS[curr_idx + 1]
        db.session.commit()
        return True

    return False
