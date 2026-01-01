from fastapi import APIRouter, Request, Depends, Query, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.database import get_db
from app.models.dictionary import Dictionary
from app.services import auth_service, gemini_service, progress_service, vocabulary_service

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def vocabulary_list(
    request: Request,
    level: Optional[str] = None,
    word_class: Optional[str] = None,
    starts_with: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Список слов с фильтрами"""
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "Not authenticated"}

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        return {"error": "Not authenticated"}

    # Build query
    query = select(Dictionary)
    if level:
        query = query.where(Dictionary.level == level.lower())
    if word_class:
        query = query.where(Dictionary.class_ == word_class)
    if starts_with:
        query = query.where(Dictionary.word.like(f"{starts_with}%"))

    query = query.order_by(Dictionary.word).offset(offset).limit(limit)

    result = await db.execute(query)
    words = result.scalars().all()

    # Check if there are more items
    count_query = select(func.count(Dictionary.id))
    if level:
        count_query = count_query.where(Dictionary.level == level.lower())
    if word_class:
        count_query = count_query.where(Dictionary.class_ == word_class)
    if starts_with:
        count_query = count_query.where(Dictionary.word.like(f"{starts_with}%"))
    total_count = await db.scalar(count_query)
    has_more = (offset + limit) < total_count

    # Get unique word classes for filter
    classes_result = await db.execute(
        select(Dictionary.class_).distinct().where(Dictionary.class_.isnot(None))
    )
    word_classes = sorted([c for c in classes_result.scalars().all() if c])

    # If HTMX request, return only the items partial
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "vocabulary/items_partial.html",
            {
                "request": request,
                "words": words,
                "offset": offset + limit,
                "has_more": has_more,
                "selected_level": level,
                "selected_class": word_class
            }
        )

    return templates.TemplateResponse(
        "vocabulary/list.html",
        {
            "request": request,
            "words": words,
            "selected_level": level,
            "selected_class": word_class,
            "word_classes": word_classes,
            "user": user,
            "offset": limit,
            "has_more": has_more
        }
    )


@router.get("/practice", response_class=HTMLResponse)
async def practice_start(
    request: Request,
    level: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Начало практики слов (Anki-style)"""
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "Not authenticated"}

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        return {"error": "Not authenticated"}

    return templates.TemplateResponse(
        "vocabulary/practice_start.html",
        {
            "request": request,
            "user": user,
            "level": level or user.current_level
        }
    )


@router.post("/practice/card", response_class=HTMLResponse)
async def practice_card(
    request: Request,
    level: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Получение карточки со словом и вариантами перевода (с Anki prefetch)"""
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "Not authenticated"}

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        return {"error": "Not authenticated"}

    # Get next 10 words using Anki algorithm
    words = await vocabulary_service.get_practice_words(db, user.id, level, count=10)

    if not words:
        return templates.TemplateResponse(
            "vocabulary/no_words.html",
            {"request": request, "level": level}
        )

    # Take first word from the queue
    word = words[0]
    remaining_count = len(words) - 1

    # Generate translation options using Gemini
    translations = await gemini_service.generate_word_translations(
        word.word,
        word.class_ or "unknown",
        word.level
    )

    return templates.TemplateResponse(
        "vocabulary/practice_card.html",
        {
            "request": request,
            "word": word,
            "options": translations["options"],
            "correct_translation": translations["correct_translation"],
            "level": level,
            "remaining_in_queue": remaining_count
        }
    )


@router.post("/practice/answer", response_class=HTMLResponse)
async def practice_answer(
    request: Request,
    word_id: int = Form(...),
    selected_answer: str = Form(...),
    correct_answer: str = Form(...),
    level: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Проверка ответа на карточку с обновлением Anki прогресса"""
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "Not authenticated"}

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        return {"error": "Not authenticated"}

    # Get word
    word_result = await db.execute(select(Dictionary).where(Dictionary.id == word_id))
    word = word_result.scalar_one_or_none()

    is_correct = selected_answer == correct_answer

    # Update progress using Anki algorithm
    await vocabulary_service.update_word_progress(db, user.id, word_id, is_correct)

    return templates.TemplateResponse(
        "vocabulary/practice_result.html",
        {
            "request": request,
            "word": word,
            "selected_answer": selected_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "level": level
        }
    )


@router.get("/{word_id}", response_class=HTMLResponse)
async def word_detail(
    request: Request,
    word_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Детальная страница слова с AI примерами"""
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "Not authenticated"}

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        return {"error": "Not authenticated"}

    # Get word
    result = await db.execute(select(Dictionary).where(Dictionary.id == word_id))
    word = result.scalar_one_or_none()

    if not word:
        return {"error": "Word not found"}

    # Generate AI examples and explanation
    ai_content = await gemini_service.generate_word_examples(
        word.word,
        word.class_ or "unknown",
        word.level
    )

    return templates.TemplateResponse(
        "vocabulary/detail.html",
        {
            "request": request,
            "word": word,
            "ai_examples": ai_content.get("examples", []),
            "ai_explanation": ai_content.get("explanation", ""),
            "user": user
        }
    )
