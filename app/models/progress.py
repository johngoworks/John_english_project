from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from datetime import datetime
from typing import Optional
from app.database import Base


class UserGrammarProgress(Base):
    __tablename__ = 'user_grammar_progress'
    __table_args__ = (
        UniqueConstraint('user_id', 'grammar_id', name='uix_user_grammar'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    grammar_id: Mapped[str] = mapped_column(String, ForeignKey('grammar.id'), nullable=False, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    total_attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class UserVocabularyProgress(Base):
    __tablename__ = 'user_vocabulary_progress'
    __table_args__ = (
        UniqueConstraint('user_id', 'word_id', name='uix_user_word'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    word_id: Mapped[int] = mapped_column(Integer, ForeignKey('dictionary.id'), nullable=False, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)  # Количество правильных ответов подряд
    last_review: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_review: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    interval: Mapped[int] = mapped_column(Integer, default=1)  # Интервал повторения в днях
    ease_factor: Mapped[float] = mapped_column(Integer, default=2.5)  # Фактор легкости (Anki)
