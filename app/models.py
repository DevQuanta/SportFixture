from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import DateTime, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash

from .database import db


class Admin(db.Model, UserMixin):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    _password_hash: Mapped[str] = mapped_column(String(256), nullable=False)

    @hybrid_property
    def password(self) -> str:
        raise AttributeError("Password is not a readable attribute.")

    @password.setter
    def set_password(self, value: str) -> None:
        self._password_hash = generate_password_hash(value)

    def check_password(self, value) -> bool:
        return check_password_hash(self._password_hash, value)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
