from pydantic import BaseModel


class LevelProgress(BaseModel):
    level: str
    total_grammar: int
    completed_grammar: int
    total_words: int
    completed_words: int
    grammar_completion_pct: float
    vocab_completion_pct: float
    can_advance: bool
    next_level: str | None = None


class OverallProgress(BaseModel):
    current_level: str
    levels: dict[str, LevelProgress]
