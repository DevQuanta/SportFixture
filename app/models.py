from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import DateTime, String, Index
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.properties import ForeignKey
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import db, Base
from enum import Enum as PyEnum
from sqlalchemy import Enum as SQLEnum

# tournament_players = Table(
#     "tournament_players",
#     db.metadata,
#     Column("player_id", ForeignKey("player.id"), primary_key=True), # type: ignore
#     Column("tournament_id", ForeignKey("tournament.id"), primary_key=True) # type: ignore
# )

class Admin(Base, UserMixin):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    email: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    _password_hash: Mapped[str] = mapped_column(String(256), nullable=False, init=False)

    @hybrid_property
    def password(self) -> str: # type: ignore
        raise AttributeError("Password is not a readable attribute.")

    @password.setter
    def password(self, value: str) -> None:
        self._password_hash = generate_password_hash(value)

    def check_password(self, value) -> bool:
        return check_password_hash(self._password_hash, value)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        init=False
    )

class Player(Base):
    __tablename__ = "player"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[String] = mapped_column(String(100), nullable=False)
    difficulty: Mapped[String] = mapped_column(String(100), nullable=False)

    tournament_associations: Mapped[list["TournamentPlayer"]] = relationship(
            back_populates="player",
            init = False
        )

    @hybrid_property
    def colour(self):
        """Checks the difficulty column and returns the exact hex code."""
        # Mapping rules centralized in one place
        mapping = {
            "beginner": "#22c55e",      # Green
            "intermediate": "#eab308",  # Yellow
            "advanced": "#ef4444"         # Red
        }
        # fallback (like gray) if difficulty is missing/mismatched
        return mapping.get(self.difficulty, "#9ca3af") # type: ignore

class TournamentStatus(PyEnum):
    SETUP = "setup"
    REGISTRATION = "registration"
    ASSIGNMENT = "assignment"
    PREVIEW = "preview"
    LIVE = "live"
    COMPLETED = "completed"

class Tournament(Base):
    __tablename__ = "tournament"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[String] = mapped_column(String(100), nullable=False)

    max_groups: Mapped[int] = mapped_column(default=4, nullable=False)
    max_rounds: Mapped[int] = mapped_column(default=3, nullable=False)

    status: Mapped[TournamentStatus] = mapped_column(SQLEnum(TournamentStatus, values_callable=lambda x: [e.value for e in x]), default=TournamentStatus.SETUP, nullable = False)

    player_associations: Mapped[list["TournamentPlayer"]] = relationship(
            back_populates="tournament",
            init = False
        )


    matches: Mapped[list["Match"]] = relationship(back_populates="tournament", init=False)


class Match(Base):

    __tablename__ = "match"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournament.id"), nullable=False)

    player_1_id: Mapped[int] = mapped_column(ForeignKey("player.id"), nullable=False)
    player_2_id: Mapped[int] = mapped_column(ForeignKey("player.id"), nullable=False)

    games: Mapped[list["GameScore"]] = relationship("GameScore", order_by="GameScore.game_number", back_populates="match", init=False)


    player_1: Mapped["Player"] = relationship(foreign_keys=[player_1_id], init=False)
    player_2: Mapped["Player"] = relationship(foreign_keys=[player_2_id], init=False)
    tournament: Mapped["Tournament"] = relationship(foreign_keys=[tournament_id], init=False)

    # needs round and group
    round_number: Mapped[int] = mapped_column(nullable=False)
    group_id: Mapped[int] = mapped_column(nullable=False)

    is_placement_match: Mapped[bool] = mapped_column(default=False, nullable=False)


class GameScore(Base):
    __tablename__ = "gamescore"

    id: Mapped[int] = mapped_column(primary_key=True, init = False)
    match_id: Mapped[int] = mapped_column(ForeignKey("match.id"), nullable=False)

    match: Mapped["Match"] = relationship("Match", back_populates="games", init = False)

    game_number: Mapped[int] = mapped_column(nullable=False)

    p1_score: Mapped[int | None] = mapped_column(nullable=True)
    p2_score: Mapped[int | None] = mapped_column( nullable=True)

class TournamentPlayer(Base):

    __tablename__ = "tournament_player"

    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"), primary_key=True, init = False)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournament.id"), primary_key=True, init = False)

    group_id: Mapped[int | None] = mapped_column(nullable=True)

    player: Mapped["Player"] = relationship(back_populates="tournament_associations")
    tournament: Mapped["Tournament"] = relationship(back_populates="player_associations")

    __table_args__ = (
            Index("idx_tournament_group", "tournament_id", "group_id"),
        )
