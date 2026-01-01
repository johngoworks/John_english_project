from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, List, Optional
from datetime import datetime

from app.models.grammar import Grammar
from app.models.test_history import TestHistory
from app.models.progress import UserGrammarProgress
from app.services import gemini_service
from app.config import get_settings

settings = get_settings()


async def create_test_for_user(
    db: AsyncSession,
    user_id: int,
    grammar_id: str,
    question_type: str = "multiple_choice"
) -> Dict:
    """
    Создаёт новый тест для пользователя

    Returns:
        dict: Вопрос с вариантами ответов
    """
    # Get grammar rule
    result = await db.execute(select(Grammar).where(Grammar.id == grammar_id))
    grammar_rule = result.scalar_one_or_none()

    if not grammar_rule:
        raise ValueError(f"Grammar rule {grammar_id} not found")

    # Generate test question using Gemini
    test_data = await gemini_service.generate_test(grammar_rule, question_type)

    return {
        "grammar_id": grammar_id,
        "grammar_rule": grammar_rule,
        "question": test_data["question"],
        "options": test_data.get("options"),
        "question_type": question_type,
        "correct_answer_hidden": test_data["correct_answer"]  # Don't send to frontend
    }


async def check_answer(
    db: AsyncSession,
    user_id: int,
    grammar_id: str,
    question: str,
    user_answer: str,
    correct_answer: str,
    question_type: str
) -> Dict:
    """
    Проверяет ответ пользователя и сохраняет в историю

    Returns:
        dict: Результат с AI фидбеком
    """
    # Check if answer is correct
    is_correct = user_answer.strip().lower() == correct_answer.strip().lower()

    # Get grammar rule for AI analysis
    result = await db.execute(select(Grammar).where(Grammar.id == grammar_id))
    grammar_rule = result.scalar_one_or_none()

    # Get AI explanation if incorrect
    ai_explanation = ""
    related_rules = []

    if not is_correct and grammar_rule:
        # Get all grammar rules for finding related ones
        all_rules_result = await db.execute(
            select(Grammar).where(Grammar.level == grammar_rule.level)
        )
        all_rules = all_rules_result.scalars().all()

        analysis = await gemini_service.analyze_error(
            question=question,
            user_answer=user_answer,
            correct_answer=correct_answer,
            grammar_rule=grammar_rule,
            all_grammar_rules=list(all_rules)
        )
        ai_explanation = analysis["explanation"]
        related_rules = analysis["related_rules"]

    # Save to test history
    test_history = TestHistory(
        user_id=user_id,
        grammar_id=grammar_id,
        question_type=question_type,
        question=question,
        user_answer=user_answer,
        correct_answer=correct_answer,
        is_correct=is_correct,
        ai_explanation=ai_explanation,
        related_rules=",".join(related_rules) if related_rules else None
    )
    db.add(test_history)

    # Update user progress
    progress_result = await db.execute(
        select(UserGrammarProgress).where(
            UserGrammarProgress.user_id == user_id,
            UserGrammarProgress.grammar_id == grammar_id
        )
    )
    progress = progress_result.scalar_one_or_none()

    if not progress:
        progress = UserGrammarProgress(
            user_id=user_id,
            grammar_id=grammar_id,
            total_attempts=0,
            correct_attempts=0
        )
        db.add(progress)

    progress.total_attempts += 1
    if is_correct:
        progress.correct_attempts += 1

    # Mark as completed if 3 correct attempts
    if progress.correct_attempts >= settings.REQUIRED_CORRECT_ATTEMPTS:
        progress.completed = True

    progress.last_attempt = datetime.utcnow()

    await db.commit()

    # Get related grammar rules for response
    related_grammar_rules = []
    if related_rules:
        rules_result = await db.execute(
            select(Grammar).where(Grammar.id.in_(related_rules))
        )
        related_grammar_rules = [
            {"id": r.id, "guideword": r.guideword, "level": r.level}
            for r in rules_result.scalars().all()
        ]

    return {
        "is_correct": is_correct,
        "correct_answer": correct_answer,
        "ai_explanation": ai_explanation,
        "related_rules": related_grammar_rules,
        "progress": {
            "total_attempts": progress.total_attempts,
            "correct_attempts": progress.correct_attempts,
            "completed": progress.completed
        }
    }


async def get_test_history(
    db: AsyncSession,
    user_id: int,
    limit: int = 20
) -> List[TestHistory]:
    """Получить историю тестов пользователя"""
    result = await db.execute(
        select(TestHistory)
        .where(TestHistory.user_id == user_id)
        .order_by(TestHistory.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
