# English Learning App

Веб-приложение для изучения английского языка с интеграцией AI (Groq LLaMA) для персонализированного обучения.

## Технологии

- **Backend**: FastAPI + SQLAlchemy 2.0 (async)
- **Frontend**: HTMX + Tailwind CSS + Jinja2
- **AI**: Groq API (meta-llama/llama-4-scout-17b-16e-instruct)
- **Database**: SQLite (async с aiosqlite)
- **Алгоритм повторений**: Anki Spaced Repetition
- **Deploy**: Uvicorn

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

# Открыть .env и добавить Groq API ключ
# GROQ_API_KEY="your-actual-api-key-here"
```

**Получить Groq API ключ**: https://console.groq.com/keys

### 3. Миграция базы данных

```bash
# Применить все миграции (добавляет is_read поля)
python migrate_database.py
```

### 4. Запуск приложения

```bash
uvicorn app.main:app --reload
```

Приложение будет доступно на `http://localhost:8000`

## Основной функционал

### ✅ Реализовано

#### 1. **Аутентификация и профиль**
   - Регистрация и вход с JWT токенами
   - Личный кабинет с прогрессом по уровням
   - Отслеживание готовности к следующему уровню (80% правил + 80% слов)

#### 2. **Грамматика (1,222 правила A1-C2)**
   - Просмотр правил с группировкой по категориям
   - Фильтрация по уровню и категории
   - AI объяснения на русском языке для каждого правила
   - ⭐ **Система отметок "прочитано"**:
     - Отметка правил звездочками
     - Секция "Недавно прочитанные" (2 последних)
     - Страница всех прочитанных правил
   - Тесты по грамматике (3 типа вопросов)

#### 3. **Времена глаголов (16 времён)**
   - Полное описание каждого времени:
     - Формы: утвердительная, отрицательная, вопросительная
     - Использование и примеры
     - Временные маркеры
   - AI объяснения от Groq LLM
   - ⭐ **Система отметок "прочитано"** (аналогично грамматике)
   - Тесты по временам
   - Фильтрация по уровню и категории

#### 4. **Словарь (5,948 слов a1-c2)**
   - Поиск слов по фильтрам
   - Изучение с карточками
   - Отслеживание прогресса

#### 5. **Тестирование**
   - **3 типа вопросов**:
     - Multiple Choice (выбор из вариантов)
     - Fill in the Blank (заполнить пропуск)
     - Open Ended (открытый ответ с AI проверкой)
   - Тесты по грамматике и временам
   - Отображение темы теста в интерфейсе
   - Подробная обратная связь от AI
   - История всех попыток

#### 6. **Прогресс и Анки алгоритм**
   - Spaced Repetition System (SRS) на основе алгоритма Anki
   - Автоматический расчет интервалов повторений
   - Ease Factor для адаптации под пользователя
   - Отслеживание по каждому правилу и слову:
     - Количество попыток
     - Процент правильных ответов
     - Дата следующего повторения
     - Статус "изучено" / "прочитано"

#### 7. **AI Интеграция (Groq)**
   - Генерация объяснений правил на русском
   - Создание тестовых вопросов
   - Проверка открытых ответов
   - Анализ ошибок с подробным фидбеком
   - Поиск связанных правил

#### 8. **Адаптивный интерфейс**
   - Mobile-first дизайн
   - Tailwind CSS стилизация
   - HTMX для динамических обновлений
   - Цветовая дифференциация:
     - 🔵 Грамматика: Indigo/Blue
     - 🟣 Времена: Purple
     - ⭐ Прочитанное: Yellow

## Структура базы данных

База данных уже создана и заполнена:
- **1,222** грамматических правила (A1-C2)
- **16** времён глаголов
- **5,948** слов (a1-c2)

### Таблицы

- `users` - пользователи
- `grammar` - грамматические правила
  - Поля: super_category, sub_category, level, guideword, can_do_statement, example
- `tenses` - времена глаголов
  - Поля: tense_name, category, level, form_positive, form_negative, form_question, usage, examples, time_markers
- `dictionary` - словарь
- `user_grammar_progress` - прогресс по грамматике
  - Включает: completed, is_read, total_attempts, correct_attempts, last_attempt, next_review, interval, ease_factor
- `user_tense_progress` - прогресс по временам
  - Включает: completed, is_read, total_attempts, correct_attempts, last_attempt
- `user_vocabulary_progress` - прогресс по словарю
- `test_history` - история тестов

## Структура проекта

```
John_english_project/
├── app/
│   ├── models/           # SQLAlchemy модели (User, Grammar, Tense, Dictionary, Progress)
│   ├── schemas/          # Pydantic схемы
│   ├── services/         # Бизнес-логика
│   │   ├── auth_service.py
│   │   ├── gemini_service.py  # Groq API интеграция
│   │   ├── test_service.py
│   │   └── progress_service.py  # Anki SRS алгоритм
│   ├── routes/           # FastAPI роуты
│   │   ├── auth.py
│   │   ├── grammar.py
│   │   ├── tenses.py
│   │   ├── vocabulary.py
│   │   ├── tests.py
│   │   └── dashboard.py
│   ├── templates/        # Jinja2 шаблоны
│   │   ├── grammar/      # Список, детали, прочитанные
│   │   ├── tenses/       # Список, детали, прочитанные
│   │   ├── vocabulary/
│   │   ├── tests/
│   │   └── dashboard/
│   ├── config.py         # Настройки (Groq API, DB)
│   ├── database.py       # Async DB connection
│   └── main.py           # FastAPI приложение
├── json_to_backup/       # Исходные JSON данные
│   ├── grammar.json
│   └── dictionary.json
├── english_learning.db   # SQLite база данных
├── create_database.py    # Скрипт создания БД
├── migrate_database.py   # Скрипт миграций
├── reader.py             # Утилита для чтения данных
├── requirements.txt
└── README.md
```

## Разработка

### Запуск с live reload

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Полезные скрипты

```bash
# Создать базу данных с нуля
python create_database.py

# Применить миграции
python migrate_database.py

# Прочитать данные из БД
python reader.py
```

### Тестирование

Приложение доступно на `http://localhost:8000`

1. Зарегистрируйтесь на `/register`
2. Войдите на `/login`
3. Перейдите в Dashboard для выбора уровня
4. Изучайте грамматику, времена и слова
5. Проходите тесты для закрепления материала
6. Отмечайте изученное звездочками ⭐

## Особенности реализации

### Anki Spaced Repetition Algorithm

Приложение использует адаптированный алгоритм Anki для оптимального повторения:

```python
# При правильном ответе
interval = previous_interval * ease_factor
ease_factor += 0.1  # Увеличиваем (макс 2.5)

# При неправильном ответе
interval = 1 day
ease_factor -= 0.2  # Уменьшаем (мин 1.3)
```

### AI Промпты (Groq)

Примеры промптов для разных задач:

- **Объяснение правил**: "English teacher. Explain in Russian, simple language..."
- **Генерация тестов**: "Create multiple choice question for grammar rule..."
- **Проверка ответов**: "Check if answer is correct. Grammar rule: ..."
- **Анализ ошибок**: "Explain why answer is wrong and what is correct..."

### HTMX интеграция

Динамические обновления без перезагрузки страницы:
- Отметка "прочитано" с автообновлением
- Ленивая загрузка списков (infinite scroll)
- Отправка форм тестов

## Миграция с Gemini на Groq

Проект изначально использовал Google Gemini, но был мигрирован на Groq API для:
- Более быстрых ответов
- Открытой модели LLaMA 4
- Лучшей стабильности

## API Документация

После запуска доступна по адресу:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Требования

- Python 3.10+
- SQLite 3
- Groq API ключ

## Лицензия

MIT

---

**Автор**: John
**Версия**: 2.0
**Последнее обновление**: Январь 2025
