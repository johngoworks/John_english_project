from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from app.database import get_db
from app.schemas.user import UserCreate, UserLogin
from app.services import auth_service
from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


@router.post("/register-form", response_class=HTMLResponse)
async def register_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Регистрация через HTML форму"""
    try:
        user_create = UserCreate(username=username, password=password)
        user = await auth_service.create_user(db, user_create)

        # Auto login after registration
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_service.create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )

        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(key="access_token", value=access_token, httponly=True)
        return response

    except ValueError as e:
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": str(e)}
        )


@router.post("/login-form", response_class=HTMLResponse)
async def login_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Вход через HTML форму"""
    user = await auth_service.authenticate_user(db, username, password)

    if not user:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Неверный логин или пароль"}
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response
