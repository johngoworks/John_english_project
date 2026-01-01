from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from app.database import get_db, init_db
from app.config import get_settings
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.services import auth_service
from datetime import timedelta

# Import routers
from app.routes import pages, auth, grammar, tests, progress, vocabulary

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    await init_db()
    print("[OK] Database initialized")
    print("Application started!")
    print("Visit: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan
)

templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(pages.router)  # Main pages (dashboard, home, login, register)
app.include_router(auth.router)   # Auth form handlers
app.include_router(grammar.router)  # Grammar routes
app.include_router(vocabulary.router)  # Vocabulary routes
app.include_router(tests.router)  # Test routes
app.include_router(progress.router)  # Progress routes


# Health check for API
@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


# Auth endpoints
@app.post("/api/auth/register", response_model=UserResponse)
async def register(user_create: UserCreate, db: AsyncSession = Depends(get_db)):
    """Регистрация нового пользователя"""
    try:
        user = await auth_service.create_user(db, user_create)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login", response_model=Token)
async def login(user_login: UserLogin, db: AsyncSession = Depends(get_db)):
    """Вход пользователя"""
    user = await auth_service.authenticate_user(db, user_login.username, user_login.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
