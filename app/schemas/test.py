from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TestQuestion(BaseModel):
    question: str
    question_type: str  # multiple_choice, fill_blank, open_ended
    options: Optional[List[str]] = None  # For multiple choice
    correct_answer: str


class TestAnswer(BaseModel):
    test_history_id: Optional[int] = None
    user_answer: str


class TestResult(BaseModel):
    is_correct: bool
    correct_answer: str
    ai_explanation: str
    related_rules: List[dict]  # List of related grammar rules


class TestHistoryResponse(BaseModel):
    id: int
    grammar_id: str
    question: str
    user_answer: Optional[str]
    is_correct: Optional[bool]
    ai_explanation: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
