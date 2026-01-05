from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.database import get_db
from app.models.tense import Tense
from app.models.progress import UserTenseProgress
from app.services import auth_service, gemini_service

router = APIRouter(prefix="/tenses", tags=["tenses"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def tenses_list(
    request: Request,
    level: Optional[str] = None,
    category: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Список времён с фильтрами"""
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "Not authenticated"}

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        return {"error": "Not authenticated"}

    # Build query
    query = select(Tense)
    if level:
        query = query.where(Tense.level == level.upper())
    if category:
        query = query.where(Tense.category == category)

    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    tenses = result.scalars().all()

    # Check if there are more items
    count_query = select(func.count(Tense.id))
    if level:
        count_query = count_query.where(Tense.level == level.upper())
    if category:
        count_query = count_query.where(Tense.category == category)
    total_count = await db.scalar(count_query)
    has_more = (offset + limit) < total_count

    # Get unique categories for filter
    categories_result = await db.execute(
        select(Tense.category).distinct()
    )
    categories = sorted(categories_result.scalars().all())

    # If HTMX request, return only the items partial
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "tenses/items_partial.html",
            {
                "request": request,
                "tenses": tenses,
                "offset": offset + limit,
                "has_more": has_more,
                "selected_level": level,
                "selected_category": category
            }
        )

    return templates.TemplateResponse(
        "tenses/list.html",
        {
            "request": request,
            "tenses": tenses,
            "selected_level": level,
            "selected_category": category,
            "categories": categories,
            "user": user,
            "offset": limit,
            "has_more": has_more
        }
    )


@router.get("/{tense_id}", response_class=HTMLResponse)
async def tense_detail(
    request: Request,
    tense_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Детальная страница времени с AI объяснением"""
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "Not authenticated"}

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        return {"error": "Not authenticated"}

    # Get tense
    result = await db.execute(select(Tense).where(Tense.id == tense_id))
    tense = result.scalar_one_or_none()

    if not tense:
        raise HTTPException(status_code=404, detail="Tense not found")

    # Generate AI explanation
    prompt = f"""English teacher. Explain tense in Russian, simple language.

Tense: {tense.tense_name}
Level: {tense.level}
Usage: {tense.usage}
Examples: {tense.examples}

Write 3 short paragraphs (max 150 words):
1. When to use
2. How to form (positive, negative, question)
3. Common mistakes

Use markdown (##, **). Conversational Russian."""

    try:
        ai_explanation = await gemini_service.call_llm(prompt, temperature=0.5, max_tokens=800)
    except:
        ai_explanation = "Не удалось сгенерировать объяснение"

    return templates.TemplateResponse(
        "tenses/detail.html",
        {
            "request": request,
            "tense": tense,
            "ai_explanation": ai_explanation,
            "user": user
        }
    )


@router.post("/{tense_id}/complete")
async def mark_complete(
    tense_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Отметить время как изученное"""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Get or create progress
    result = await db.execute(
        select(UserTenseProgress).where(
            UserTenseProgress.user_id == user.id,
            UserTenseProgress.tense_id == tense_id
        )
    )
    progress = result.scalar_one_or_none()

    if not progress:
        progress = UserTenseProgress(
            user_id=user.id,
            tense_id=tense_id
        )
        db.add(progress)

    progress.completed = True
    await db.commit()

    return {"status": "completed", "tense_id": tense_id}
