from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import DateTime, String, Index, Integer
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.properties import ForeignKey
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import db

# tournament_players = Table(
#     "tournament_players",
#     db.metadata,
#     Column("player_id", ForeignKey("player.id"), primary_key=True), # type: ignore
#     Column("tournament_id", ForeignKey("tournament.id"), primary_key=True) # type: ignore
# )

class Admin(db.Model, UserMixin):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    _password_hash: Mapped[str] = mapped_column(String(256), nullable=False)

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
        default=lambda: datetime.now(timezone.utc)
    )

class Player(db.Model):
    __tablname__ = "player"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[String] = mapped_column(String(100), nullable=False)
    difficulty: Mapped[String] = mapped_column(String(100), nullable=False)

    tournament_associations: Mapped[list["TournamentPlayer"]] = relationship(
            back_populates="player"
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

class Tournament(db.Model):
    __tablename__ = "tournament"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[String] = mapped_column(String(100), nullable=False)

    max_groups: Mapped[int] = mapped_column(default=4, nullable=False)
    max_rounds: Mapped[int] = mapped_column(default=3, nullable=False)

    player_associations: Mapped[list["TournamentPlayer"]] = relationship(
            back_populates="tournament"
        )


    matches: Mapped[list["Match"]] = relationship(back_populates="tournament")


class Match(db.Model):

    __tablename__ = "match"

    id: Mapped[int] = mapped_column(primary_key=True)

    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournament.id"), nullable=False)

    player_1_id: Mapped[int] = mapped_column(ForeignKey("player.id"), nullable=False)
    player_2_id: Mapped[int] = mapped_column(ForeignKey("player.id"), nullable=False)

    player_1: Mapped["Player"] = relationship(foreign_keys=[player_1_id])
    player_2: Mapped["Player"] = relationship(foreign_keys=[player_2_id])
    tournament: Mapped["Tournament"] = relationship(foreign_keys=[tournament_id])

    # needs round and group
    round_number: Mapped[int] = mapped_column(nullable=False)
    group_id: Mapped[int] = mapped_column(nullable=False)

    is_placement_match: Mapped[bool] = mapped_column(default=False)

    games: Mapped[list["GameScore"]] = relationship("GameScore", order_by="GameScore.game_number", back_populates="match")

class GameScore(db.Model):
    __tablename__ = "gamescore"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("match.id"), nullable=False)

    match: Mapped["Match"] = relationship("Match", back_populates="games")

    game_number: Mapped[int] = mapped_column(nullable=False)

    p1_score: Mapped[int | None] = mapped_column(nullable=True)
    p2_score: Mapped[int | None] = mapped_column( nullable=True)

class TournamentPlayer(db.Model):

    __tablename__ = "tournament_player"

    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"), primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournament.id"), primary_key=True)

    group_id: Mapped[int | None] = mapped_column(nullable=True)

    player: Mapped["Player"] = relationship(back_populates="tournament_associations")
    tournament: Mapped["Tournament"] = relationship(back_populates="player_associations")

    __table_args__ = (
            Index("idx_tournament_group", "tournament_id", "group_id"),
        )
