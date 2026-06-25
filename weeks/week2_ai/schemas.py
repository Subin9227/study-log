from pydantic import BaseModel
from typing import Optional

class PostCreate(BaseModel):
    title : str
    description: str

class PostUpdate(BaseModel):
    title : Optional[str] = None
    description : Optional[str] = None

class Post(BaseModel):
    id: int
    title: str
    description: str
    like: int = 0
    ai_comment: Optional[str] = None

    class Config:
        from_attributes = True