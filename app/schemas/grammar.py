from pydantic import BaseModel
from typing import Optional


class GrammarBase(BaseModel):
    id: str
    super_category: Optional[str] = None
    sub_category: Optional[str] = None
    level: Optional[str] = None
    lexical_range: Optional[str] = None
    guideword: Optional[str] = None
    can_do_statement: Optional[str] = None
    example: Optional[str] = None

    class Config:
        from_attributes = True


class GrammarWithAI(GrammarBase):
    ai_explanation: Optional[str] = None
