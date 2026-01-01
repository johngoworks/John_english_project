from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import auth_service, progress_service

router = APIRouter(prefix="/progress", tags=["progress"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def progress_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Дашборд с прогрессом по всем уровням"""
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "Not authenticated"}

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        return {"error": "Not authenticated"}

    # Get overall progress
    overall_progress = await progress_service.get_overall_progress(db, user.id)

    return templates.TemplateResponse(
        "progress/stats.html",
        {
            "request": request,
            "user": user,
            "progress": overall_progress
        }
    )


@router.get("/level/{level}", response_class=HTMLResponse)
async def level_progress(
    request: Request,
    level: str,
    db: AsyncSession = Depends(get_db)
):
    """Прогресс по конкретному уровню (для HTMX partial update)"""
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "Not authenticated"}

    user = await auth_service.get_current_user_from_token(token, db)
    if not user:
        return {"error": "Not authenticated"}

    level_prog = await progress_service.get_level_progress(db, user.id, level)

    # Return partial HTML for HTMX
    return f"""
    <div class="progress-card" id="level-{level}">
        <h3 class="text-xl font-bold">{level}</h3>
        <div class="mt-2">
            <p>Грамматика: {level_prog['grammar_completion_pct']}%</p>
            <div class="bg-gray-200 rounded-full h-2 mt-1">
                <div class="bg-blue-600 h-2 rounded-full" style="width: {level_prog['grammar_completion_pct']}%"></div>
            </div>
        </div>
        <div class="mt-2">
            <p>Словарь: {level_prog['vocab_completion_pct']}%</p>
            <div class="bg-gray-200 rounded-full h-2 mt-1">
                <div class="bg-green-600 h-2 rounded-full" style="width: {level_prog['vocab_completion_pct']}%"></div>
            </div>
        </div>
        {"<p class='mt-2 text-green-600 font-bold'>✓ Готов к " + level_prog['next_level'] + "</p>" if level_prog['can_advance'] else ""}
    </div>
    """
