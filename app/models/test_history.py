from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text
from datetime import datetime
from typing import Optional
from app.database import Base


class TestHistory(Base):
    __tablename__ = 'test_history'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    grammar_id: Mapped[str] = mapped_column(String, ForeignKey('grammar.id'), nullable=False, index=True)
    question_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # multiple_choice, open_ended, fill_blank
    question: Mapped[str] = mapped_column(Text, nullable=False)
    user_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    correct_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    ai_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    related_rules: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
