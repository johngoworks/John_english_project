from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict

from app.models.user import User
from app.models.grammar import Grammar
from app.models.dictionary import Dictionary
from app.models.progress import UserGrammarProgress, UserVocabularyProgress
from app.config import get_settings

settings = get_settings()

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]


async def get_level_progress(db: AsyncSession, user_id: int, level: str) -> Dict:
    """
    Получить прогресс по конкретному уровню

    Returns:
        dict: Статистика прогресса по уровню
    """
    # Total grammar for level
    total_grammar_result = await db.execute(
        select(func.count(Grammar.id)).where(Grammar.level == level.upper())
    )
    total_grammar = total_grammar_result.scalar() or 0

    # Completed grammar for user
    completed_grammar_result = await db.execute(
        select(func.count(UserGrammarProgress.id))
        .join(Grammar, Grammar.id == UserGrammarProgress.grammar_id)
        .where(
            UserGrammarProgress.user_id == user_id,
            UserGrammarProgress.completed == True,
            Grammar.level == level.upper()
        )
    )
    completed_grammar = completed_grammar_result.scalar() or 0

    # Total words for level
    total_words_result = await db.execute(
        select(func.count(Dictionary.id)).where(Dictionary.level == level.lower())
    )
    total_words = total_words_result.scalar() or 0

    # Completed words for user
    completed_words_result = await db.execute(
        select(func.count(UserVocabularyProgress.id))
        .join(Dictionary, Dictionary.id == UserVocabularyProgress.word_id)
        .where(
            UserVocabularyProgress.user_id == user_id,
            UserVocabularyProgress.completed == True,
            Dictionary.level == level.lower()
        )
    )
    completed_words = completed_words_result.scalar() or 0

    # Calculate percentages
    grammar_pct = (completed_grammar / total_grammar * 100) if total_grammar > 0 else 0
    vocab_pct = (completed_words / total_words * 100) if total_words > 0 else 0

    # Check if can advance
    can_advance = (
        grammar_pct >= settings.GRAMMAR_COMPLETION_THRESHOLD and
        vocab_pct >= settings.VOCAB_COMPLETION_THRESHOLD
    )

    # Get next level
    next_level = None
    if can_advance:
        current_index = LEVELS.index(level.upper())
        if current_index < len(LEVELS) - 1:
            next_level = LEVELS[current_index + 1]

    return {
        "level": level.upper(),
        "total_grammar": total_grammar,
        "completed_grammar": completed_grammar,
        "total_words": total_words,
        "completed_words": completed_words,
        "grammar_completion_pct": round(grammar_pct, 1),
        "vocab_completion_pct": round(vocab_pct, 1),
        "can_advance": can_advance,
        "next_level": next_level
    }


async def get_overall_progress(db: AsyncSession, user_id: int) -> Dict:
    """Получить общий прогресс по всем уровням"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise ValueError(f"User {user_id} not found")

    levels_progress = {}
    for level in LEVELS:
        levels_progress[level] = await get_level_progress(db, user_id, level)

    return {
        "current_level": user.current_level,
        "levels": levels_progress
    }


async def mark_grammar_completed(
    db: AsyncSession,
    user_id: int,
    grammar_id: str
) -> None:
    """Отметить правило как изученное вручную"""
    result = await db.execute(
        select(UserGrammarProgress).where(
            UserGrammarProgress.user_id == user_id,
            UserGrammarProgress.grammar_id == grammar_id
        )
    )
    progress = result.scalar_one_or_none()

    if not progress:
        progress = UserGrammarProgress(
            user_id=user_id,
            grammar_id=grammar_id
        )
        db.add(progress)

    progress.completed = True
    await db.commit()


async def mark_word_completed(
    db: AsyncSession,
    user_id: int,
    word_id: int
) -> None:
    """Отметить слово как выученное"""
    result = await db.execute(
        select(UserVocabularyProgress).where(
            UserVocabularyProgress.user_id == user_id,
            UserVocabularyProgress.word_id == word_id
        )
    )
    progress = result.scalar_one_or_none()

    if not progress:
        progress = UserVocabularyProgress(
            user_id=user_id,
            word_id=word_id,
            attempts=1,
            completed=True
        )
        db.add(progress)
    else:
        progress.attempts += 1
        progress.completed = True

    await db.commit()
