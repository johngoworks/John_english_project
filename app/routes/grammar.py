from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.database import get_db
from app.models.grammar import Grammar
from app.services import gemini_service, auth_service, progress_service

router = APIRouter(prefix="/grammar", tags=["grammar"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def grammar_list(
    request: Request,
    level: Optional[str] = None,
    category: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Список грамматических правил с фильтрами"""
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "Not authenticated"}

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        return {"error": "Not authenticated"}

    # Build query
    query = select(Grammar)
    if level:
        query = query.where(Grammar.level == level.upper())
    if category:
        query = query.where(Grammar.super_category == category)

    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    grammar_rules = result.scalars().all()

    # Check if there are more items
    count_query = select(func.count(Grammar.id))
    if level:
        count_query = count_query.where(Grammar.level == level.upper())
    if category:
        count_query = count_query.where(Grammar.super_category == category)
    total_count = await db.scalar(count_query)
    has_more = (offset + limit) < total_count

    # If HTMX request, return only the items partial
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "grammar/items_partial.html",
            {
                "request": request,
                "grammar_rules": grammar_rules,
                "offset": offset + limit,
                "has_more": has_more,
                "selected_level": level,
                "selected_category": category
            }
        )

    return templates.TemplateResponse(
        "grammar/list.html",
        {
            "request": request,
            "grammar_rules": grammar_rules,
            "selected_level": level,
            "selected_category": category,
            "user": user,
            "offset": limit,
            "has_more": has_more
        }
    )


@router.get("/{grammar_id}", response_class=HTMLResponse)
async def grammar_detail(
    request: Request,
    grammar_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Детальная страница правила с AI объяснением"""
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "Not authenticated"}

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        return {"error": "Not authenticated"}

    # Get grammar rule
    result = await db.execute(select(Grammar).where(Grammar.id == grammar_id))
    grammar_rule = result.scalar_one_or_none()

    if not grammar_rule:
        raise HTTPException(status_code=404, detail="Grammar rule not found")

    # Generate AI explanation
    ai_explanation = await gemini_service.generate_explanation(grammar_rule)

    return templates.TemplateResponse(
        "grammar/detail.html",
        {
            "request": request,
            "grammar": grammar_rule,
            "ai_explanation": ai_explanation,
            "user": user
        }
    )


@router.post("/{grammar_id}/complete")
async def mark_complete(
    grammar_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Отметить правило как изученное"""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    await progress_service.mark_grammar_completed(db, user.id, grammar_id)

    return {"status": "completed", "grammar_id": grammar_id}
