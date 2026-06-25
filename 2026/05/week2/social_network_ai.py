from __future__ import annotations
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends  # Depends 추가
from pydantic import BaseModel
import requests  # 2번 AI 호출을 위해 추가

# --- [3번 데이터베이스 적용을 위한 SQLAlchemy 임포트] ---
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# ==========================================
# 3. SQLite 데이터베이스 설정
# ==========================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./community.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# DB에 실제로 저장될 테이블 설계 (기존 Post 클래스의 구조를 반영)
class PostDB(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, index=True)
    description = Column(String)
    like = Column(Integer, default=0)
    ai_comment = Column(String, nullable=True)  # 2번 과제용: AI 댓글 컬럼 추가

# 서버 시작 시 자동으로 DB 파일과 테이블을 생성합니다.
Base.metadata.create_all(bind=engine)

# 각 API에서 DB에 접근할 수 있게 도와주는 주입 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 기존 Pydantic 스키마 (변경 없음 / ai_comment만 추가 선택)
# ==========================================
class PostCreate(BaseModel):
    title : str
    description: str

class PostUpdate(BaseModel):
    title : Optional[str] = None
    description : Optional[str] = None

# 응답 모델에 AI 댓글 필드를 추가하여 유저가 볼 수 있게 합니다.
class Post(BaseModel):
    id: int
    title: str
    description: str
    like: int = 0
    ai_comment: Optional[str] = None  # AI 댓글 필드 추가

    class Config:
        from_attributes = True  # SQLAlchemy 객체를 Pydantic으로 자동 변환해주는 옵션

app = FastAPI()

# (기존 post_db 리스트와 id_counter는 DB를 쓰므로 이제 사용하지 않지만, 기존 코드 유지 원칙으로 지우지 않고 둡니다.)
post_db: List[Post] = []
id_counter = 1

# ➕ [CREATE] 게시글 등록 + AI 모델 서빙 적용
@app.post("/posts", response_model=Post)
def create_post(post_data: PostCreate, db: Session = Depends(get_db)):
    
    # --- [2번: AI 모델 서빙 (Ollama 로컬 호출)] ---
    ollama_url = "http://localhost:11434/api/generate"
    prompt_text = (
        f"너는 친절한 커뮤니티 유저야. 다음 게시글에 어울리는 짧은 대댓글을 한 줄로 달아줘.\n"
        f"제목: {post_data.title}\n내용: {post_data.description}"
    )
    
    payload = {
        "model": "llama3.2", 
        "prompt": prompt_text,
        "stream": False,
    }

    try:
        response = requests.post(ollama_url, json=payload, timeout=10)
        response.raise_for_status()
        ai_response = response.json().get("response", "AI 응답을 생성하지 못했습니다.").strip()
    except Exception as e:
        # Ollama가 안 켜져 있어도 서버가 멈추지 않게 예외 처리
        ai_response = f"[AI 서빙 일시중단] 실패 원인: {str(e)}"

    # --- [3번: 데이터베이스 적용 (SQLite에 저장)] ---
    new_post = PostDB(
        title=post_data.title,
        description=post_data.description,
        like=0,
        ai_comment=ai_response  # 생성한 AI 답변 저장
    )
    
    db.add(new_post)
    db.commit()      # DB에 최종 저장
    db.refresh(new_post)  # 데이터베이스가 자동으로 생성해준 id값을 받아옴
    
    return new_post

# 🔍 [READ] 게시글 전체 조회 (메모리 리스트가 아닌 DB에서 읽어옴)
@app.get("/posts", response_model=List[Post])
def get_all_posts(db: Session = Depends(get_db)):
    return db.query(PostDB).all()

# ✏️ [UPDATE] 게시글 수정 (DB 데이터 수정)
@app.put("/posts/{post_id}", response_model=Post)
def update_post(post_id: int, update_data: PostUpdate, db: Session = Depends(get_db)):
    post = db.query(PostDB).filter(PostDB.id == post_id).first()
    
    if post:
        if update_data.title is not None:
            post.title = update_data.title
        if update_data.description is not None:
            post.description = update_data.description
        
        db.commit()
        db.refresh(post)
        return post
            
    raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

# ❤️ [UPDATE] 좋아요 버튼 클릭 (DB 데이터 수정)
@app.patch("/posts/{post_id}/like", response_model=Post)
def click_like(post_id: int, db: Session = Depends(get_db)):
    post = db.query(PostDB).filter(PostDB.id == post_id).first()
    
    if post:
        post.like += 1
        db.commit()
        db.refresh(post)
        return post
            
    raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

# ❌ [DELETE] 게시글 삭제 (DB 데이터 삭제)
@app.delete("/posts/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(PostDB).filter(PostDB.id == post_id).first()
    
    if post:
        db.delete(post)
        db.commit()
        return {"message": f"{post_id}번 게시글이 성공적으로 삭제되었습니다."}
            
    raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
