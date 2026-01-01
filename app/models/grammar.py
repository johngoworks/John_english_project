from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from typing import Optional
from app.database import Base


class Grammar(Base):
    __tablename__ = 'grammar'

    id: Mapped[str] = mapped_column(String, primary_key=True)
    super_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sub_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    level: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    lexical_range: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    guideword: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    can_do_statement: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    example: Mapped[Optional[str]] = mapped_column(String, nullable=True)
