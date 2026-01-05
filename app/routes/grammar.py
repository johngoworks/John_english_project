from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.database import get_db
from app.models.grammar import Grammar
from app.models.progress import UserGrammarProgress
from app.services import gemini_service, auth_service, progress_service

router = APIRouter(prefix="/grammar", tags=["grammar"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def grammar_list(
    request: Request,
    level: Optional[str] = None,
    category: Optional[str] = None,
    offset: int = 0,
    limit: int = 100,
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

    query = query.order_by(Grammar.super_category, Grammar.sub_category)

    result = await db.execute(query)
    grammar_rules = list(result.scalars().all())

    # Get user's read progress
    progress_result = await db.execute(
        select(UserGrammarProgress).where(
            UserGrammarProgress.user_id == user.id,
            UserGrammarProgress.is_read == True
        )
    )
    read_rules = {p.grammar_id for p in progress_result.scalars().all()}

    # Get read rules with full grammar info (for "Recently Read" section)
    read_grammar_result = await db.execute(
        select(Grammar)
        .join(UserGrammarProgress, Grammar.id == UserGrammarProgress.grammar_id)
        .where(
            UserGrammarProgress.user_id == user.id,
            UserGrammarProgress.is_read == True
        )
        .order_by(UserGrammarProgress.last_attempt.desc())
        .limit(2)  # Show only 2 recent
    )
    read_grammar_rules = list(read_grammar_result.scalars().all())

    # Add is_read flag to all grammar rules
    for rule in grammar_rules:
        rule.is_read = rule.id in read_rules

    # Add is_read flag to read rules too
    for rule in read_grammar_rules:
        rule.is_read = True

    # Get unique categories for filter
    categories_result = await db.execute(
        select(Grammar.super_category).distinct().order_by(Grammar.super_category)
    )
    categories = [c for c in categories_result.scalars().all() if c]

    # Group by category
    from collections import defaultdict
    grouped_rules = defaultdict(list)
    for rule in grammar_rules:
        if rule.super_category:
            grouped_rules[rule.super_category].append(rule)

    return templates.TemplateResponse(
        "grammar/list.html",
        {
            "request": request,
            "grouped_rules": grouped_rules,
            "read_rules": read_grammar_rules,
            "categories": categories,
            "selected_level": level,
            "selected_category": category,
            "user": user
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

    # Check if user has read this rule
    progress_result = await db.execute(
        select(UserGrammarProgress).where(
            UserGrammarProgress.user_id == user.id,
            UserGrammarProgress.grammar_id == grammar_id
        )
    )
    progress = progress_result.scalar_one_or_none()
    is_read = progress.is_read if progress else False

    # Generate AI explanation
    ai_explanation = await gemini_service.generate_explanation(grammar_rule)

    return templates.TemplateResponse(
        "grammar/detail.html",
        {
            "request": request,
            "grammar": grammar_rule,
            "ai_explanation": ai_explanation,
            "is_read": is_read,
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


@router.get("/read/all", response_class=HTMLResponse)
async def all_read_rules(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Страница со всеми прочитанными правилами"""
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "Not authenticated"}

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        return {"error": "Not authenticated"}

    # Get all read rules
    read_grammar_result = await db.execute(
        select(Grammar)
        .join(UserGrammarProgress, Grammar.id == UserGrammarProgress.grammar_id)
        .where(
            UserGrammarProgress.user_id == user.id,
            UserGrammarProgress.is_read == True
        )
        .order_by(UserGrammarProgress.last_attempt.desc())
    )
    read_rules = list(read_grammar_result.scalars().all())

    # Add is_read flag
    for rule in read_rules:
        rule.is_read = True

    return templates.TemplateResponse(
        "grammar/read_all.html",
        {
            "request": request,
            "read_rules": read_rules,
            "user": user
        }
    )


@router.post("/{grammar_id}/read")
async def mark_as_read(
    grammar_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Отметить правило как прочитанное"""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    await progress_service.mark_grammar_as_read(db, user.id, grammar_id)

    return {"status": "read", "grammar_id": grammar_id}
