from groq import Groq
import json
from typing import Dict, List, Optional
from app.config import get_settings
from app.models.grammar import Grammar

settings = get_settings()

# Configure Groq client
client = Groq(api_key=settings.GROQ_API_KEY)


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
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=800
        )
        return response.choices[0].message.content
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
        prompt = f"""You must respond with ONLY valid JSON, no explanations.

Grammar rule: {grammar_rule.guideword}
Level: {grammar_rule.level}
Example: {grammar_rule.example[:200]}

Create a multiple-choice question testing this grammar rule.

Respond with this exact JSON structure:
{{"question": "Complete sentence here", "options": ["option1", "option2", "option3", "option4"], "correct_answer": "option1"}}"""

    elif question_type == "fill_blank":
        prompt = f"""You must respond with ONLY valid JSON, no explanations.

Grammar rule: {grammar_rule.guideword}
Level: {grammar_rule.level}

Create a fill-in-the-blank question. Use ___ for the blank.

Respond with this exact JSON structure:
{{"question": "Sentence with ___ blank", "correct_answer": "answer"}}"""

    else:  # open_ended
        prompt = f"""You must respond with ONLY valid JSON, no explanations.

Grammar rule: {grammar_rule.guideword}
Level: {grammar_rule.level}

Create an open-ended question testing this grammar rule.

Respond with this exact JSON structure:
{{"question": "instruction here", "correct_answer": "example answer"}}"""

    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        result_text = response.choices[0].message.content.strip()

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
    except json.JSONDecodeError as e:
        return {
            "question": f"Error: Invalid JSON from AI. Please try again.",
            "correct_answer": "",
            "question_type": question_type
        }
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
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=800
        )
        explanation = response.choices[0].message.content

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
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=600
        )
        return response.choices[0].message.content
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
    prompt = f"""You must respond with ONLY valid JSON, no explanations or markdown.

Word: {word}
Part of speech: {word_class}
Level: {level.upper()}

Task: Create explanation in Russian and 3 example sentences in English.

Respond with this exact JSON structure:
{{"explanation": "Краткое объяснение на русском (1-2 предложения)", "examples": ["First English example sentence", "Second English example sentence", "Third English example sentence"]}}"""

    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=500
        )
        result_text = response.choices[0].message.content.strip()

        # Clean JSON response
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        result = json.loads(result_text)

        # Validate structure
        if "explanation" not in result or "examples" not in result:
            raise ValueError("Missing required fields")

        return result
    except Exception as e:
        return {
            "explanation": f"Слово: {word} ({word_class})",
            "examples": [
                f"I need to learn the word '{word}'.",
                f"The word '{word}' is important.",
                f"Can you use '{word}' in a sentence?"
            ]
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
    prompt = f"""You must respond with ONLY valid JSON, no explanations or markdown.

English word: {word}
Part of speech: {word_class}
Level: {level.upper()}

Task: Provide 1 correct Russian translation and 3 plausible wrong translations (same part of speech, similar meaning but incorrect).

Respond with this exact JSON structure:
{{"correct_translation": "правильный перевод", "wrong_translations": ["неправильный1", "неправильный2", "неправильный3"]}}"""

    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )
        result_text = response.choices[0].message.content.strip()

        # Clean JSON response
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        result = json.loads(result_text)

        # Validate structure
        if "correct_translation" not in result or "wrong_translations" not in result:
            raise ValueError("Missing required fields")

        if len(result["wrong_translations"]) < 3:
            raise ValueError("Not enough wrong translations")

        # Combine and shuffle options
        import random
        options = [result["correct_translation"]] + result["wrong_translations"][:3]
        random.shuffle(options)

        return {
            "correct_translation": result["correct_translation"],
            "options": options
        }
    except Exception as e:
        # Fallback with generic translations
        import random
        generic_wrong = ["значение", "смысл", "понятие", "термин", "выражение", "слово"]
        random.shuffle(generic_wrong)

        return {
            "correct_translation": f"[{word}]",
            "options": [f"[{word}]"] + generic_wrong[:3]
        }
