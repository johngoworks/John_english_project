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
    prompt = f"""You are an experienced English teacher. Explain the following grammar rule in Russian using simple and clear language.

**Grammar Rule Information:**
- Rule: {grammar_rule.guideword}
- Level: {grammar_rule.level}
- Category: {grammar_rule.super_category} - {grammar_rule.sub_category}
- Can-do statement: {grammar_rule.can_do_statement}
- Examples: {grammar_rule.example}

**Your task:**
Create a clear explanation in Russian with exactly 3 short paragraphs (max 4 sentences each):

1. **Что это?** - What is this rule and when to use it
2. **Как использовать?** - How to apply it with simple examples
3. **На что обратить внимание?** - Common mistakes to avoid

**Requirements:**
- Write in simple, conversational Russian
- Use markdown formatting (bold, lists where appropriate)
- Be concise but complete
- Add 1-2 practical examples in English with Russian explanations
- Total length: 150-250 words

**Example format:**
## Что это за правило?

[Your explanation here]

## Как использовать?

[Your explanation with examples here]

## Типичные ошибки

[Common mistakes here]
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
        prompt = f"""You are an English test creator. Create a multiple-choice question to test knowledge of this grammar rule.

**Grammar Rule:**
- Rule: {grammar_rule.guideword}
- Level: {grammar_rule.level}
- Description: {grammar_rule.can_do_statement}
- Examples: {grammar_rule.example[:500]}

**Task:**
Create a practical test question with 4 answer options.

**Example:**
{{
    "question": "Choose the correct form: She ___ to the store yesterday.",
    "options": ["go", "goes", "went", "going"],
    "correct_answer": "went"
}}

**Requirements:**
- Question must be a complete sentence with a blank or choice scenario
- All 4 options must be grammatically plausible (only 1 correct)
- Options should test understanding of the specific rule
- Difficulty appropriate for {grammar_rule.level} level
- Question and options in English

**Return ONLY valid JSON (no markdown, no explanations):**
{{
    "question": "Complete sentence or question here",
    "options": ["option A", "option B", "option C", "option D"],
    "correct_answer": "exact match of one option"
}}
"""
    elif question_type == "fill_blank":
        prompt = f"""You are an English test creator. Create a fill-in-the-blank question for this grammar rule.

**Grammar Rule:**
- Rule: {grammar_rule.guideword}
- Level: {grammar_rule.level}
- Description: {grammar_rule.can_do_statement}

**Example:**
{{
    "question": "She ___ (go) to Paris last summer.",
    "correct_answer": "went"
}}

**Requirements:**
- Use ___ to mark the blank
- Provide hints in parentheses if needed
- Answer should be 1-3 words
- Appropriate for {grammar_rule.level} level

**Return ONLY valid JSON:**
{{
    "question": "Complete sentence with ___ blank",
    "correct_answer": "short answer"
}}
"""
    else:  # open_ended
        prompt = f"""You are an English test creator. Create an open-ended question for this grammar rule.

**Grammar Rule:**
- Rule: {grammar_rule.guideword}
- Level: {grammar_rule.level}

**Example:**
{{
    "question": "Write a sentence using the past simple tense to describe what you did yesterday.",
    "correct_answer": "I went to the park and played football with my friends."
}}

**Requirements:**
- Question should prompt creative use of the grammar rule
- Expected answer: 1-2 sentences
- Level-appropriate vocabulary

**Return ONLY valid JSON:**
{{
    "question": "Clear instruction for the student",
    "correct_answer": "Example acceptable answer"
}}
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
    prompt = f"""You are a supportive English teacher. A student made a mistake. Help them understand what went wrong.

**Context:**
- Grammar rule: {grammar_rule.guideword}
- Question: {question}
- Student's answer: {user_answer}
- Correct answer: {correct_answer}

**Your task:**
Provide encouraging feedback in Russian with this structure:

## Почему это ошибка?
[Explain in 1-2 sentences why the student's answer is wrong]

## Правильное объяснение
[Re-explain the rule in simpler terms, 2-3 sentences]
[Add 1 example in English with Russian translation]

## Совет на будущее
[One specific tip to avoid this mistake next time]

**Tone:**
- Be kind and encouraging
- Use simple, conversational Russian
- Focus on learning, not the mistake
- Keep total response under 200 words
- Use markdown formatting (##, **, lists)
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
    prompt = f"""You are an experienced English teacher. A student has completed level {level} with {len(completed_rules)} grammar rules studied.

**Your task:**
Ask 2-3 assessment questions in Russian to check if they're ready for the next level.

**Requirements:**
- Write questions in Russian
- Test overall understanding of {level} grammar concepts
- Questions should be specific, not general
- Mix different grammar topics from {level}
- Be friendly and encouraging
- Format with numbered list

**Example:**
## Проверочные вопросы для уровня {level}

Давай проверим, готов ли ты двигаться дальше:

1. [Specific question about grammar topic 1]
2. [Specific question about grammar topic 2]
3. [Specific question about grammar topic 3]

Ответь на эти вопросы, и я пойму, готов ли ты к следующему уровню!
"""

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
    prompt = f"""You are an English vocabulary teacher. Create an explanation and examples for this word.

**Word Information:**
- Word: {word}
- Part of speech: {word_class}
- CEFR Level: {level.upper()}

**Example output:**
{{
    "explanation": "Book (существительное) - это книга, печатное издание с текстом. Также может быть глаголом - бронировать, заказывать.",
    "examples": [
        "I'm reading a book about history.",
        "She books a hotel room online every time she travels.",
        "The library has thousands of books on different topics."
    ]
}}

**Requirements:**
- Explanation: Brief meaning in Russian (1-2 sentences), mention multiple meanings if applicable
- Examples: 3 sentences in English showing different contexts/meanings
- Examples must be appropriate for {level.upper()} level
- Examples should show practical, common usage
- Use natural, everyday English

**Return ONLY valid JSON (no markdown):**
{{
    "explanation": "Russian explanation (1-2 sentences)",
    "examples": [
        "Example sentence 1",
        "Example sentence 2",
        "Example sentence 3"
    ]
}}
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
    prompt = f"""You are an English vocabulary test creator. Generate translation options for a multiple-choice quiz.

**Word Information:**
- English word: {word}
- Part of speech: {word_class}
- CEFR Level: {level.upper()}

**Example for "run":**
{{
    "correct_translation": "бежать, бегать",
    "wrong_translations": ["ходить", "прыгать", "летать"]
}}

**Requirements for translations:**
✓ Correct translation:
- Most common meaning for this level
- Use natural Russian
- Can include 2 meanings if common (e.g. "бежать, работать" for run)

✓ Wrong translations:
- Should be plausible but incorrect
- Same part of speech
- Similar semantic field (e.g., other movement verbs)
- Not random words - should make student think

**Return ONLY valid JSON (no markdown):**
{{
    "correct_translation": "правильный перевод",
    "wrong_translations": ["похожее неправильное 1", "похожее неправильное 2", "похожее неправильное 3"]
}}
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
