# English Learning App

Веб-приложение для изучения английского языка с интеграцией AI (Gemini) для персонализированного обучения.

## Технологии

- **Backend**: FastAPI + SQLAlchemy (async)
- **Frontend**: HTMX + Tailwind CSS
- **AI**: Google Gemini API
- **Database**: SQLite (dev) / PostgreSQL (prod ready)
- **Deploy**: Docker / Uvicorn

## Быстрый старт

### 1. Установка зависимостей

```bash
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt
```

### 2. Настройка окружения

```bash
# Скопировать .env.example в .env
cp .env.example .env

# Открыть .env и добавить Gemini API ключ
# GEMINI_API_KEY="your-actual-api-key-here"
```

**Получить Gemini API ключ**: https://makersuite.google.com/app/apikey

### 3. Запуск приложения

#### Вариант А: Через командную строку

```bash
uvicorn app.main:app --reload
```

Приложение будет доступно на `http://localhost:8000`

#### Вариант Б: Через Docker

```bash
docker-compose up --build
```

## API Документация

После запуска доступна по адресу:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## MVP Функционал

### ✅ Реализовано

1. **Базовая инфраструктура**
   - FastAPI приложение
   - SQLAlchemy модели (User, Grammar, Dictionary, Progress, TestHistory)
   - Async database setup

2. **Аутентификация**
   - Регистрация (POST /api/auth/register)
   - Вход (POST /api/auth/login)
   - JWT токены

3. **AI Сервисы (Gemini)**
   - Генерация объяснений правил на русском
   - Генерация тестов (multiple choice, fill blank, open ended)
   - Анализ ошибок с обратной связью
   - Поиск связанных правил

4. **Test Service**
   - Создание тестов
   - Проверка ответов
   - Сохранение истории

5. **Progress Tracking**
   - Отслеживание прогресса по уровням
   - Подсчет % завершения (80% правил + 80% слов)
   - Проверка готовности к следующему уровню

### 🚧 В разработке (следующие шаги)

1. **Routes (API endpoints)**
   - Grammar routes (список, детали, фильтры)
   - Test routes (старт теста, вопрос, ответ)
   - Progress routes (dashboard, статистика)

2. **Templates (HTML + HTMX)**
   - base.html с Tailwind CSS
   - Страницы: login, register, dashboard
   - Тесты: start, question, result
   - Progress dashboard

3. **Frontend**
   - HTMX интеграция
   - Tailwind стилизация
   - Интерактивные компоненты

4. **Vocabulary (Flashcards)**
   - Spaced repetition система
   - Карточки для изучения слов

## Структура проекта

```
John_english_project/
├── app/
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic (auth, gemini, test, progress)
│   ├── routes/          # FastAPI routes (TODO)
│   ├── templates/       # Jinja2 templates (TODO)
│   ├── config.py        # Settings
│   ├── database.py      # DB connection
│   └── main.py          # FastAPI app
├── english_learning.db  # SQLite database
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Разработка

### Запуск с live reload

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Тестирование API

Используйте Swagger UI: http://localhost:8000/docs

1. Зарегистрировать пользователя: POST /api/auth/register
2. Войти: POST /api/auth/login
3. Использовать токен для защищенных endpoints

## База данных

База данных уже создана и заполнена:
- **1,222** грамматических правил (A1-C2)
- **5,948** слов (a1-c2)

### Схема

- `users` - пользователи
- `grammar` - грамматические правила
- `dictionary` - словарь
- `user_grammar_progress` - прогресс по грамматике
- `user_vocabulary_progress` - прогресс по словарю
- `test_history` - история тестов

## Лицензия

MIT
