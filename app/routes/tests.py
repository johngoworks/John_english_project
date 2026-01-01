from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.database import get_db
from app.models.grammar import Grammar
from app.services import auth_service, test_service

router = APIRouter(prefix="/tests", tags=["tests"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/start", response_class=HTMLResponse)
async def test_start(
    request: Request,
    level: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Страница выбора теста"""
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "Not authenticated"}

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        return {"error": "Not authenticated"}

    # Get available levels
    levels = ["A1", "A2", "B1", "B2", "C1", "C2"]

    return templates.TemplateResponse(
        "tests/start.html",
        {
            "request": request,
            "user": user,
            "levels": levels,
            "selected_level": level or user.current_level
        }
    )


@router.get("/question", response_class=HTMLResponse)
async def get_test_question(
    request: Request,
    level: str,
    question_type: str = "multiple_choice",
    db: AsyncSession = Depends(get_db)
):
    """Получить случайный вопрос по уровню"""
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "Not authenticated"}

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        return {"error": "Not authenticated"}

    # Get random grammar rule for this level
    result = await db.execute(
        select(Grammar)
        .where(Grammar.level == level.upper())
        .order_by(Grammar.id)  # Random would be func.random() but simpler for now
        .limit(1)
    )
    grammar_rule = result.scalar_one_or_none()

    if not grammar_rule:
        raise HTTPException(status_code=404, detail=f"No grammar rules found for level {level}")

    # Generate test
    test_data = await test_service.create_test_for_user(
        db, user.id, grammar_rule.id, question_type
    )

    return templates.TemplateResponse(
        "tests/question.html",
        {
            "request": request,
            "user": user,
            "test": test_data,
            "level": level
        }
    )


@router.post("/answer", response_class=HTMLResponse)
async def submit_answer(
    request: Request,
    grammar_id: str = Form(...),
    question: str = Form(...),
    user_answer: str = Form(...),
    correct_answer: str = Form(...),
    question_type: str = Form(...),
    level: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Проверить ответ и вернуть результат с AI фидбеком"""
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "Not authenticated"}

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        return {"error": "Not authenticated"}

    # Check answer
    result = await test_service.check_answer(
        db=db,
        user_id=user.id,
        grammar_id=grammar_id,
        question=question,
        user_answer=user_answer,
        correct_answer=correct_answer,
        question_type=question_type
    )

    return templates.TemplateResponse(
        "tests/result.html",
        {
            "request": request,
            "user": user,
            "result": result,
            "level": level,
            "grammar_id": grammar_id
        }
    )


@router.get("/history", response_class=HTMLResponse)
async def test_history(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """История тестов пользователя"""
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "Not authenticated"}

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        return {"error": "Not authenticated"}

    history = await test_service.get_test_history(db, user.id)

    return templates.TemplateResponse(
        "tests/history.html",
        {
            "request": request,
            "user": user,
            "history": history
        }
    )
