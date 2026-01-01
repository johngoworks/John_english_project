"""
Vocabulary practice service with Anki spaced repetition algorithm
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime, timedelta
from typing import List, Dict
import random

from app.models.dictionary import Dictionary
from app.models.progress import UserVocabularyProgress


async def get_practice_words(
    db: AsyncSession,
    user_id: int,
    level: str,
    count: int = 10
) -> List[Dictionary]:
    """
    Get next words for practice using Anki algorithm

    Priority:
    1. Words due for review (next_review <= now)
    2. New words (never practiced)
    3. Random words from level

    Args:
        db: Database session
        user_id: User ID
        level: CEFR level
        count: Number of words to fetch

    Returns:
        List of Dictionary objects
    """
    now = datetime.utcnow()
    words = []

    # 1. Get words due for review
    due_query = (
        select(Dictionary)
        .join(
            UserVocabularyProgress,
            and_(
                UserVocabularyProgress.word_id == Dictionary.id,
                UserVocabularyProgress.user_id == user_id
            )
        )
        .where(
            Dictionary.level == level.lower(),
            UserVocabularyProgress.next_review <= now
        )
        .order_by(UserVocabularyProgress.next_review)
        .limit(count)
    )
    result = await db.execute(due_query)
    due_words = list(result.scalars().all())
    words.extend(due_words)

    # 2. If not enough, get new words (never practiced)
    if len(words) < count:
        remaining = count - len(words)

        # Get IDs of already practiced words
        practiced_query = select(UserVocabularyProgress.word_id).where(
            UserVocabularyProgress.user_id == user_id
        )
        practiced_result = await db.execute(practiced_query)
        practiced_ids = [row[0] for row in practiced_result.fetchall()]

        # Get new words
        new_query = (
            select(Dictionary)
            .where(
                Dictionary.level == level.lower(),
                Dictionary.id.notin_(practiced_ids) if practiced_ids else True
            )
            .order_by(Dictionary.word)
            .limit(remaining)
        )
        result = await db.execute(new_query)
        new_words = list(result.scalars().all())
        words.extend(new_words)

    # 3. If still not enough, get random words
    if len(words) < count:
        remaining = count - len(words)
        existing_ids = [w.id for w in words]

        random_query = (
            select(Dictionary)
            .where(
                Dictionary.level == level.lower(),
                Dictionary.id.notin_(existing_ids) if existing_ids else True
            )
            .order_by(Dictionary.word)
            .limit(remaining * 2)  # Get more to randomize
        )
        result = await db.execute(random_query)
        random_words = list(result.scalars().all())
        random.shuffle(random_words)
        words.extend(random_words[:remaining])

    return words[:count]


async def update_word_progress(
    db: AsyncSession,
    user_id: int,
    word_id: int,
    is_correct: bool
) -> None:
    """
    Update word progress using simplified Anki SM-2 algorithm

    Args:
        db: Database session
        user_id: User ID
        word_id: Word ID
        is_correct: Whether the answer was correct
    """
    now = datetime.utcnow()

    # Get or create progress
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
            attempts=0,
            correct_count=0,
            interval=1,
            ease_factor=2.5
        )
        db.add(progress)

    # Update attempts
    progress.attempts += 1
    progress.last_review = now

    if is_correct:
        # Increase correct count
        progress.correct_count += 1

        # SM-2 Algorithm (simplified)
        if progress.correct_count == 1:
            progress.interval = 1
        elif progress.correct_count == 2:
            progress.interval = 6
        else:
            progress.interval = int(progress.interval * progress.ease_factor)

        # Update ease factor (make easier)
        progress.ease_factor = min(2.5, progress.ease_factor + 0.1)

        # Mark as completed after reaching threshold
        from app.config import get_settings
        settings = get_settings()
        if progress.correct_count >= settings.REQUIRED_CORRECT_ATTEMPTS:
            progress.completed = True

    else:
        # Reset on incorrect answer
        progress.correct_count = 0
        progress.interval = 1
        progress.completed = False

        # Update ease factor (make harder)
        progress.ease_factor = max(1.3, progress.ease_factor - 0.2)

    # Calculate next review date
    progress.next_review = now + timedelta(days=progress.interval)

    await db.commit()
