from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Tense(Base):
    __tablename__ = "tenses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tense_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    level: Mapped[str] = mapped_column(String, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    form_positive: Mapped[str] = mapped_column(Text, nullable=False)
    form_negative: Mapped[str] = mapped_column(Text, nullable=False)
    form_question: Mapped[str] = mapped_column(Text, nullable=False)
    usage: Mapped[str] = mapped_column(Text, nullable=False)
    examples: Mapped[str] = mapped_column(Text, nullable=False)
    time_markers: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self):
        return f"<Tense {self.tense_name} ({self.level})>"
