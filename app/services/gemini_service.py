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
    prompt = f"""English teacher. Explain in Russian, simple language.

Rule: {grammar_rule.guideword}
Level: {grammar_rule.level}
Examples: {grammar_rule.example[:200]}

Write 3 short paragraphs (max 150 words):
1. What/when to use
2. How to use + 1 example
3. Common mistakes

Use markdown (##, **). Conversational Russian."""

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
        prompt = f"""Create multiple-choice test. JSON only.

Rule: {grammar_rule.guideword} ({grammar_rule.level})
Examples: {grammar_rule.example[:200]}

Requirements:
- Complete sentence with blank/choice
- 4 plausible options (1 correct)
- Tests specific rule understanding

JSON format:
{{"question": "sentence here", "options": ["A","B","C","D"], "correct_answer": "exact match"}}"""

    elif question_type == "fill_blank":
        prompt = f"""Create fill-blank test. JSON only.

Rule: {grammar_rule.guideword} ({grammar_rule.level})

Requirements:
- Use ___ for blank
- 1-3 word answer
- Level-appropriate

JSON format:
{{"question": "sentence with ___", "correct_answer": "answer"}}"""

    else:  # open_ended
        prompt = f"""Create open-ended test. JSON only.

Rule: {grammar_rule.guideword} ({grammar_rule.level})

Requirements:
- Creative use of rule
- 1-2 sentences expected

JSON format:
{{"question": "instruction", "correct_answer": "example answer"}}"""

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
    prompt = f"""Supportive English teacher. Student made mistake. Help in Russian.

Rule: {grammar_rule.guideword}
Q: {question}
Student: {user_answer}
Correct: {correct_answer}

Write (max 150 words):
## Почему ошибка?
[1-2 sentences]

## Правильное объяснение
[2-3 sentences + 1 example]

## Совет
[specific tip]

Tone: kind, simple Russian, markdown formatting."""

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
    prompt = f"""English teacher. Student completed {level} ({len(completed_rules)} rules).

Task: Ask 2-3 assessment questions in Russian to check readiness for next level.

Requirements:
- Questions in Russian
- Test {level} grammar understanding
- Specific, not general
- Friendly tone
- Numbered list with ##

Format:
## Проверочные вопросы {level}

1. [question 1]
2. [question 2]"""

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Ошибка при генерации вопросов: {str(e)}"


async def generate_word_examples(word: str, word_class: str, level: str) -> Dict:
    """
    Генерирует примеры использования слова и объяснение

    Args:
        word: Английское слово
        word_class: Часть речи
        level: Уровень слова

    Returns:
        dict: {
            "explanation": str - объяснение слова на русском,
            "examples": List[str] - 3-4 примера использования
        }
    """
    prompt = f"""Vocabulary teacher. Word: {word} ({word_class}, {level.upper()})

Create JSON:
{{"explanation": "Russian meaning 1-2 sentences", "examples": ["sentence1", "sentence2", "sentence3"]}}

Requirements:
- Explanation: Russian, mention multiple meanings if any
- Examples: English, different contexts, {level.upper()}-appropriate, practical usage

JSON only, no markdown."""

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
        return result
    except Exception as e:
        return {
            "explanation": "Не удалось загрузить объяснение",
            "examples": []
        }


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
    prompt = f"""Test creator. Word: {word} ({word_class}, {level.upper()})

Create JSON:
{{"correct_translation": "most common Russian meaning", "wrong_translations": ["similar1", "similar2", "similar3"]}}

Requirements:
✓ Correct: natural Russian, common meaning for level
✓ Wrong: plausible, same part of speech, similar semantic field (not random)

JSON only, no markdown."""

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
