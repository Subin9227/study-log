from sqlalchemy import Column, Integer, String
from database import Base

class PostDB(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, index=True)
    description = Column(String)
    like = Column(Integer, default=0)
    ai_comment = Column(String, nullable=True)