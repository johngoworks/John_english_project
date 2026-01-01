from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer
from typing import Optional
from app.database import Base


class Dictionary(Base):
    __tablename__ = 'dictionary'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String, nullable=False, index=True)
    class_: Mapped[Optional[str]] = mapped_column('class', String, nullable=True)
    level: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
