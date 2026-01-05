# Add these functions to test_service.py

async def create_tense_test_for_user(
    db: AsyncSession,
    user_id: int,
    tense_id: int,
    question_type: str = "multiple_choice"
) -> Dict:
    """
    Создаёт новый тест по времени для пользователя

    Returns:
        dict: Вопрос с вариантами ответов
    """
    # Get tense
    result = await db.execute(select(Tense).where(Tense.id == tense_id))
    tense = result.scalar_one_or_none()

    if not tense:
        raise ValueError(f"Tense {tense_id} not found")

    # Generate test question using AI
    prompt = f"""You must respond with ONLY valid JSON, no explanations.

Tense: {tense.tense_name}
Level: {tense.level}
Forms: {tense.form_positive}
Examples: {tense.examples}

Create a multiple-choice question testing this tense.

Respond with this exact JSON structure:
{{"question": "Complete sentence here", "options": ["option1", "option2", "option3", "option4"], "correct_answer": "option1"}}"""

    try:
        result_text = await gemini_service.call_llm(prompt, temperature=0.3, max_tokens=500, use_json=True)
        result_text = result_text.strip()

        # Clean JSON response
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        test_data = json.loads(result_text)
    except:
        test_data = {
            "question": f"Form a sentence using {tense.tense_name}",
            "options": ["will do", "did", "doing", "done"],
            "correct_answer": "will do"
        }

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
    """
    Проверяет ответ пользователя на тест по времени

    Returns:
        dict: Результат с AI фидбеком
    """
    # Check if answer is correct
    is_correct = user_answer.strip().lower() == correct_answer.strip().lower()

    # Get tense for AI analysis
    result = await db.execute(select(Tense).where(Tense.id == tense_id))
    tense = result.scalar_one_or_none()

    # Get AI explanation if incorrect
    ai_explanation = ""

    if not is_correct and tense:
        prompt = f"""English teacher. Student made a mistake with {tense.tense_name}.

Question: {question}
Student answer: {user_answer}
Correct answer: {correct_answer}

Explain in Russian (max 100 words):
1. Why the answer is wrong
2. The correct rule
3. A tip to remember

Use markdown (##, **)."""

        try:
            ai_explanation = await gemini_service.call_llm(prompt, temperature=0.5, max_tokens=600)
        except:
            ai_explanation = f"Правильный ответ: {correct_answer}"

    # Update user progress
    progress_result = await db.execute(
        select(UserTenseProgress).where(
            UserTenseProgress.user_id == user_id,
            UserTenseProgress.tense_id == tense_id
        )
    )
    progress = progress_result.scalar_one_or_none()

    if not progress:
        progress = UserTenseProgress(
            user_id=user_id,
            tense_id=tense_id,
            total_attempts=0,
            correct_attempts=0
        )
        db.add(progress)

    progress.total_attempts += 1
    if is_correct:
        progress.correct_attempts += 1

    # Mark as completed if meets threshold
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
