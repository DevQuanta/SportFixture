class DomainError(Exception):
    """Base class for all business logic and domain rule violations."""
    def __init__(self, message="A domain rule was violated."):
        self.message = message
        super().__init__(self.message)


class InvalidMatchScoreError(DomainError):
    pass

class RoundNotReadyError(DomainError):
    pass

class MatchNotFoundError(DomainError):
    pass

class TournamentNotFoundError(DomainError):
    pass

class GroupNotEmptyError(DomainError):
    pass
