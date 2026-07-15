from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import DateTime, String, Table, Column
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.properties import ForeignKey
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import db

tournament_players = Table(
    "tournament_players",
    db.metadata,
    Column("player_id", ForeignKey("player.id"), primary_key=True), # type: ignore
    Column("tournament_id", ForeignKey("tournament.id"), primary_key=True) # type: ignore
)

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

    tournaments: Mapped[list["Tournament"]] = relationship(
        secondary=tournament_players,
        back_populates="players"
    )

class Tournament(db.Model):
    __tablename__ = "tournament"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[String] = mapped_column(String(100), nullable=False)


    players: Mapped[list["Player"]] = relationship(
            secondary=tournament_players,
            back_populates="tournaments"
        )
