from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, select, or_, func
from typing import Optional, List


class Base(DeclarativeBase):
    pass


class Grammar(Base):
    __tablename__ = 'grammar'

    id: Mapped[str] = mapped_column(String, primary_key=True)
    super_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sub_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    level: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lexical_range: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    guideword: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    can_do_statement: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    example: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Dictionary(Base):
    __tablename__ = 'dictionary'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String, nullable=False)
    class_: Mapped[Optional[str]] = mapped_column('class', String, nullable=True)
    level: Mapped[Optional[str]] = mapped_column(String, nullable=True)


# Создание асинхронного движка
DATABASE_URL = "sqlite+aiosqlite:///english_learning.db"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    """Получение асинхронной сессии"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_grammar_list(
    level: Optional[str] = None,
    super_category: Optional[str] = None,
    sub_category: Optional[str] = None,
    limit: Optional[int] = None,
    random_order: bool = False
) -> List[dict]:
    """
    Получение списка грамматических правил с фильтрами

    Args:
        level: Фильтр по уровню (A1, A2, B1, B2, C1, C2)
        super_category: Фильтр по супер-категории
        sub_category: Фильтр по под-категории
        limit: Ограничение количества результатов
        random_order: Случайная сортировка

    Returns:
        List[dict]: Список грамматических правил в виде словарей
    """
    async with AsyncSessionLocal() as session:
        query = select(Grammar)

        # Применение фильтров
        if level:
            query = query.where(Grammar.level == level)
        if super_category:
            query = query.where(Grammar.super_category == super_category)
        if sub_category:
            query = query.where(Grammar.sub_category == sub_category)

        # Случайная сортировка
        if random_order:
            query = query.order_by(func.random())

        # Лимит
        if limit:
            query = query.limit(limit)

        result = await session.execute(query)
        grammar_items = result.scalars().all()

        # Конвертация в список словарей
        return [
            {
                'id': item.id,
                'super_category': item.super_category,
                'sub_category': item.sub_category,
                'level': item.level,
                'lexical_range': item.lexical_range,
                'guideword': item.guideword,
                'can_do_statement': item.can_do_statement,
                'example': item.example
            }
            for item in grammar_items
        ]


async def search_grammar_text(
    search_text: str,
    search_in: Optional[List[str]] = None,
    level: Optional[str] = None,
    limit: Optional[int] = None
) -> List[dict]:
    """
    Поиск по тексту в грамматических правилах

    Args:
        search_text: Текст для поиска
        search_in: Список полей для поиска ['guideword', 'can_do_statement', 'example']
                   По умолчанию ищет во всех текстовых полях
        level: Фильтр по уровню
        limit: Ограничение количества результатов

    Returns:
        List[dict]: Список найденных грамматических правил
    """
    async with AsyncSessionLocal() as session:
        # Определение полей для поиска
        if search_in is None:
            search_in = ['guideword', 'can_do_statement', 'example', 'super_category', 'sub_category']

        # Построение условий поиска
        search_conditions = []
        search_pattern = f"%{search_text}%"

        if 'guideword' in search_in:
            search_conditions.append(Grammar.guideword.like(search_pattern))
        if 'can_do_statement' in search_in:
            search_conditions.append(Grammar.can_do_statement.like(search_pattern))
        if 'example' in search_in:
            search_conditions.append(Grammar.example.like(search_pattern))
        if 'super_category' in search_in:
            search_conditions.append(Grammar.super_category.like(search_pattern))
        if 'sub_category' in search_in:
            search_conditions.append(Grammar.sub_category.like(search_pattern))

        query = select(Grammar).where(or_(*search_conditions))

        # Дополнительные фильтры
        if level:
            query = query.where(Grammar.level == level)

        if limit:
            query = query.limit(limit)

        result = await session.execute(query)
        grammar_items = result.scalars().all()

        return [
            {
                'id': item.id,
                'super_category': item.super_category,
                'sub_category': item.sub_category,
                'level': item.level,
                'lexical_range': item.lexical_range,
                'guideword': item.guideword,
                'can_do_statement': item.can_do_statement,
                'example': item.example
            }
            for item in grammar_items
        ]


async def get_dictionary_list(
    level: Optional[str] = None,
    word_class: Optional[str] = None,
    starts_with: Optional[str] = None,
    limit: Optional[int] = None,
    random_order: bool = False
) -> List[dict]:
    """
    Получение списка слов из словаря с фильтрами

    Args:
        level: Фильтр по уровню (a1, a2, b1, b2, c1, c2)
        word_class: Фильтр по части речи (noun, verb, adjective и т.д.)
        starts_with: Фильтр слов, начинающихся с определенной буквы/букв
        limit: Ограничение количества результатов
        random_order: Случайная сортировка

    Returns:
        List[dict]: Список слов в виде словарей
    """
    async with AsyncSessionLocal() as session:
        query = select(Dictionary)

        # Применение фильтров
        if level:
            query = query.where(Dictionary.level == level.lower())
        if word_class:
            query = query.where(Dictionary.class_ == word_class)
        if starts_with:
            query = query.where(Dictionary.word.like(f"{starts_with}%"))

        # Случайная сортировка
        if random_order:
            query = query.order_by(func.random())
        else:
            query = query.order_by(Dictionary.word)

        # Лимит
        if limit:
            query = query.limit(limit)

        result = await session.execute(query)
        dictionary_items = result.scalars().all()

        # Конвертация в список словарей
        return [
            {
                'id': item.id,
                'word': item.word,
                'class': item.class_,
                'level': item.level
            }
            for item in dictionary_items
        ]


async def search_dictionary_text(
    search_text: str,
    level: Optional[str] = None,
    word_class: Optional[str] = None,
    limit: Optional[int] = None
) -> List[dict]:
    """
    Поиск слов в словаре

    Args:
        search_text: Текст для поиска (поиск по слову)
        level: Фильтр по уровню
        word_class: Фильтр по части речи
        limit: Ограничение количества результатов

    Returns:
        List[dict]: Список найденных слов
    """
    async with AsyncSessionLocal() as session:
        search_pattern = f"%{search_text}%"
        query = select(Dictionary).where(Dictionary.word.like(search_pattern))

        # Дополнительные фильтры
        if level:
            query = query.where(Dictionary.level == level.lower())
        if word_class:
            query = query.where(Dictionary.class_ == word_class)

        if limit:
            query = query.limit(limit)

        result = await session.execute(query)
        dictionary_items = result.scalars().all()

        return [
            {
                'id': item.id,
                'word': item.word,
                'class': item.class_,
                'level': item.level
            }
            for item in dictionary_items
        ]


async def get_grammar_by_id(grammar_id: str) -> Optional[dict]:
    """Получение грамматического правила по ID"""
    async with AsyncSessionLocal() as session:
        query = select(Grammar).where(Grammar.id == grammar_id)
        result = await session.execute(query)
        item = result.scalar_one_or_none()

        if item:
            return {
                'id': item.id,
                'super_category': item.super_category,
                'sub_category': item.sub_category,
                'level': item.level,
                'lexical_range': item.lexical_range,
                'guideword': item.guideword,
                'can_do_statement': item.can_do_statement,
                'example': item.example
            }
        return None


async def get_word_by_id(word_id: int) -> Optional[dict]:
    """Получение слова по ID"""
    async with AsyncSessionLocal() as session:
        query = select(Dictionary).where(Dictionary.id == word_id)
        result = await session.execute(query)
        item = result.scalar_one_or_none()

        if item:
            return {
                'id': item.id,
                'word': item.word,
                'class': item.class_,
                'level': item.level
            }
        return None


# Пример использования
async def main():
    # Пример 1: Получить 5 случайных грамматических правил уровня A1


    print("\n=== 10 случайных слов уровня a1 ===")
    words_a1 = await get_dictionary_list(level="a1", limit=100, random_order=True)
    for item in words_a1:
        print(f"{item['word']} ({item['class']}) - {item['level']}")



if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
