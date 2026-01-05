from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, List, Optional
from datetime import datetime

from app.models.grammar import Grammar
from app.models.tense import Tense
from app.models.test_history import TestHistory
from app.models.progress import UserGrammarProgress, UserTenseProgress
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


async def create_tense_test_for_user(
    db: AsyncSession,
    user_id: int,
    tense_id: int,
    question_type: str = "multiple_choice"
) -> Dict:
    """Создаёт тест по времени"""
    import json

    result = await db.execute(select(Tense).where(Tense.id == tense_id))
    tense = result.scalar_one_or_none()

    if not tense:
        raise ValueError(f"Tense {tense_id} not found")

    prompt = f"""You must respond with ONLY valid JSON.

Tense: {tense.tense_name}
Level: {tense.level}
Usage: {tense.usage}
Examples: {tense.examples}

Create a multiple-choice question.

JSON structure:
{{"question": "sentence", "options": ["opt1", "opt2", "opt3", "opt4"], "correct_answer": "opt1"}}"""

    try:
        result_text = await gemini_service.call_llm(prompt, temperature=0.3, max_tokens=500, use_json=True)
        result_text = result_text.strip().replace("```json", "").replace("```", "").strip()
        test_data = json.loads(result_text)
    except:
        test_data = {"question": f"Use {tense.tense_name}", "options": ["will", "did", "doing", "done"], "correct_answer": "will"}

    return {
        "tense_id": tense_id,
        "tense": tense,
        "question": test_data["question"],
        "options": test_data.get("options"),
        "question_type": question_type,
        "correct_answer_hidden": test_data["correct_answer"]
    }


async def check_tense_answer(
    db: AsyncSession,
    user_id: int,
    tense_id: int,
    question: str,
    user_answer: str,
    correct_answer: str,
    question_type: str
) -> Dict:
    """Проверяет ответ на тест по времени"""
    is_correct = user_answer.strip().lower() == correct_answer.strip().lower()

    result = await db.execute(select(Tense).where(Tense.id == tense_id))
    tense = result.scalar_one_or_none()

    ai_explanation = ""
    if not is_correct and tense:
        prompt = f"""Student mistake with {tense.tense_name}.
Question: {question}
Wrong: {user_answer}
Correct: {correct_answer}

Explain in Russian (100 words):
1. Why wrong
2. Correct rule
3. Tip"""

        try:
            ai_explanation = await gemini_service.call_llm(prompt, temperature=0.5, max_tokens=600)
        except:
            ai_explanation = f"Правильный ответ: {correct_answer}"

    progress_result = await db.execute(
        select(UserTenseProgress).where(
            UserTenseProgress.user_id == user_id,
            UserTenseProgress.tense_id == tense_id
        )
    )
    progress = progress_result.scalar_one_or_none()

    if not progress:
        progress = UserTenseProgress(user_id=user_id, tense_id=tense_id, total_attempts=0, correct_attempts=0)
        db.add(progress)

    progress.total_attempts += 1
    if is_correct:
        progress.correct_attempts += 1

    if progress.correct_attempts >= settings.REQUIRED_CORRECT_ATTEMPTS:
        progress.completed = True

    progress.last_attempt = datetime.utcnow()
    await db.commit()

    return {
        "is_correct": is_correct,
        "correct_answer": correct_answer,
        "ai_explanation": ai_explanation,
        "progress": {
            "total_attempts": progress.total_attempts,
            "correct_attempts": progress.correct_attempts,
            "completed": progress.completed
        }
    }
