from google import genai
from google.genai import types
import json
from typing import Dict, List, Optional
from app.config import get_settings
from app.models.grammar import Grammar

settings = get_settings()

# Configure Gemini with new API
client = genai.Client(api_key=settings.GEMINI_API_KEY)


async def generate_explanation(grammar_rule: Grammar) -> str:
    """
    Генерирует объяснение грамматического правила на русском языке

    Args:
        grammar_rule: Правило грамматики из БД

    Returns:
        str: Объяснение на русском (2-3 параграфа)
    """
    prompt = f"""
Ты - опытный преподаватель английского языка. Объясни следующее грамматическое правило на русском языке простым и понятным языком.

Правило: {grammar_rule.guideword}
Уровень: {grammar_rule.level}
Категория: {grammar_rule.super_category} - {grammar_rule.sub_category}
Can-do statement: {grammar_rule.can_do_statement}
Примеры: {grammar_rule.example}

Создай объяснение из 2-3 коротких параграфов:
1. Что это за правило и когда оно используется
2. Как его применять с простыми примерами
3. На что обратить внимание / типичные ошибки

Используй простой, разговорный русский язык. Будь кратким и понятным.
"""

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Ошибка при генерации объяснения: {str(e)}"


async def generate_test(grammar_rule: Grammar, question_type: str = "multiple_choice") -> Dict:
    """
    Генерирует тестовый вопрос по грамматическому правилу

    Args:
        grammar_rule: Правило грамматики
        question_type: Тип вопроса (multiple_choice, fill_blank, open_ended)

    Returns:
        dict: {
            "question": str,
            "options": List[str],  # Для multiple_choice
            "correct_answer": str
        }
    """
    if question_type == "multiple_choice":
        prompt = f"""
Создай тестовый вопрос с множественным выбором (4 варианта) для проверки знания следующего грамматического правила:

Правило: {grammar_rule.guideword}
Уровень: {grammar_rule.level}
Описание: {grammar_rule.can_do_statement}
Примеры: {grammar_rule.example[:500]}

Верни ответ ТОЛЬКО в виде JSON с полями:
{{
    "question": "Текст вопроса на английском",
    "options": ["вариант А", "вариант Б", "вариант В", "вариант Г"],
    "correct_answer": "правильный вариант (полный текст)"
}}

Вопрос должен быть практическим - например, выбор правильной формы слова в предложении.
Не добавляй никакого текста кроме JSON.
"""
    elif question_type == "fill_blank":
        prompt = f"""
Создай вопрос с пропуском (fill in the blank) для проверки знания правила:

Правило: {grammar_rule.guideword}
Уровень: {grammar_rule.level}
Описание: {grammar_rule.can_do_statement}

Верни ответ ТОЛЬКО в виде JSON:
{{
    "question": "Предложение с ___ (пропуском)",
    "correct_answer": "правильное слово или фраза"
}}

Не добавляй никакого текста кроме JSON.
"""
    else:  # open_ended
        prompt = f"""
Создай открытый вопрос для проверки понимания правила:

Правило: {grammar_rule.guideword}
Уровень: {grammar_rule.level}

Верни ответ ТОЛЬКО в виде JSON:
{{
    "question": "Вопрос, требующий развернутого ответа",
    "correct_answer": "Примерный правильный ответ"
}}

Не добавляй никакого текста кроме JSON.
"""

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt
        )
        result_text = response.text.strip()

        # Clean JSON response
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        result = json.loads(result_text)
        result["question_type"] = question_type
        return result
    except Exception as e:
        return {
            "question": f"Error generating question: {str(e)}",
            "correct_answer": "",
            "question_type": question_type
        }


async def analyze_error(
    question: str,
    user_answer: str,
    correct_answer: str,
    grammar_rule: Grammar,
    all_grammar_rules: Optional[List[Grammar]] = None
) -> Dict:
    """
    Анализирует ошибку пользователя и предоставляет AI фидбек

    Args:
        question: Вопрос
        user_answer: Ответ пользователя
        correct_answer: Правильный ответ
        grammar_rule: Правило, к которому относился вопрос
        all_grammar_rules: Все правила для поиска связанных (опционально)

    Returns:
        dict: {
            "explanation": str - объяснение ошибки,
            "alternative_explanation": str - другое объяснение правила,
            "related_rules": List[str] - ID связанных правил
        }
    """
    prompt = f"""
Ты - преподаватель английского языка. Ученик допустил ошибку. Помоги ему понять, где он ошибся.

Правило: {grammar_rule.guideword}
Вопрос: {question}
Ответ ученика: {user_answer}
Правильный ответ: {correct_answer}

Напиши ответ на русском языке, включающий:
1. Почему ответ ученика неправильный (1-2 предложения)
2. Объяснение правила другими словами, чтобы было понятнее (2-3 предложения)
3. Совет, как не ошибиться в следующий раз

Будь добрым и поддерживающим. Используй простой язык.
"""

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt
        )
        explanation = response.text

        # Try to find related rules (simplified)
        related_rules = []
        if grammar_rule.sub_category and all_grammar_rules:
            related_rules = [
                r.id for r in all_grammar_rules
                if r.sub_category == grammar_rule.sub_category and r.id != grammar_rule.id
            ][:3]  # Max 3 related rules

        return {
            "explanation": explanation,
            "related_rules": related_rules
        }
    except Exception as e:
        return {
            "explanation": f"Не удалось проанализировать ошибку: {str(e)}",
            "related_rules": []
        }


async def chat_progress_check(user_id: int, level: str, completed_rules: List[str]) -> str:
    """
    AI чат для проверки готовности двигаться дальше

    Args:
        user_id: ID пользователя
        level: Текущий уровень
        completed_rules: Список пройденных правил

    Returns:
        str: Вопросы и оценка от AI
    """
    prompt = f"""
Ты - преподаватель английского языка. Ученик завершил изучение уровня {level}.
Он прошел {len(completed_rules)} грамматических правил.

Задай ему 2-3 вопроса на русском языке, чтобы проверить, действительно ли он готов двигаться дальше.
Вопросы должны проверять общее понимание грамматики уровня {level}.

Будь кратким и дружелюбным.
"""

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Ошибка при генерации вопросов: {str(e)}"


async def generate_word_translations(word: str, word_class: str, level: str) -> Dict:
    """
    Генерирует варианты перевода слова (1 правильный + 3 неправильных)

    Args:
        word: Английское слово
        word_class: Часть речи
        level: Уровень слова

    Returns:
        dict: {
            "correct_translation": str,
            "options": List[str] - 4 варианта в случайном порядке
        }
    """
    prompt = f"""
Ты - преподаватель английского языка. Создай варианты перевода слова для теста.

Слово: {word}
Часть речи: {word_class}
Уровень: {level.upper()}

Верни ответ ТОЛЬКО в виде JSON:
{{
    "correct_translation": "правильный перевод на русский",
    "wrong_translations": ["неправильный вариант 1", "неправильный вариант 2", "неправильный вариант 3"]
}}

Требования:
- Правильный перевод должен быть самым подходящим для этого уровня
- Неправильные варианты должны быть похожи, но не верны
- Все варианты должны быть на русском языке
- Не добавляй никакого текста кроме JSON
"""

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt
        )
        result_text = response.text.strip()

        # Clean JSON response
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        result = json.loads(result_text)

        # Combine and shuffle options
        import random
        options = [result["correct_translation"]] + result["wrong_translations"]
        random.shuffle(options)

        return {
            "correct_translation": result["correct_translation"],
            "options": options
        }
    except Exception as e:
        # Fallback in case of error
        return {
            "correct_translation": "перевод",
            "options": ["перевод", "вариант 1", "вариант 2", "вариант 3"]
        }
