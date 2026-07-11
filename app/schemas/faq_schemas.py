from pydantic import BaseModel


class FAQItem(BaseModel):
    id: int
    question: str
    answer: str