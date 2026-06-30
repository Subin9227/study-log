from typing import TypedDict
from langchain_core.documents import Document

class EmotionState(TypedDict):
    question: str
    context: list[Document]
    raw_code: str
    emotion_code: str
    emotion_name: str
    valence: str
    message: str
    error: str | None
