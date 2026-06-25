import requests
from sqlalchemy.orm import Session
from models import PostDB
from schemas import PostCreate, PostUpdate
from fastapi import HTTPException

class PostController:
    @staticmethod
    def create_post(db: Session, post_data: PostCreate):
        # --- [AI 모델 서빙 (Ollama 로컬 호출)] ---
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
            ai_response = f"[AI 서빙 일시중단] 실패 원인: {str(e)}"

        # --- [DB 데이터 적재] ---
        new_post = PostDB(
            title=post_data.title,
            description=post_data.description,
            like=0,
            ai_comment=ai_response
        )
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        return new_post

    @staticmethod
    def get_all_posts(db: Session):
        return db.query(PostDB).all()

    @staticmethod
    def update_post(db: Session, post_id: int, update_data: PostUpdate):
        post = db.query(PostDB).filter(PostDB.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
        
        if update_data.title is not None:
            post.title = update_data.title
        if update_data.description is not None:
            post.description = update_data.description
            
        db.commit()
        db.refresh(post)
        return post

    @staticmethod
    def click_like(db: Session, post_id: int):
        post = db.query(PostDB).filter(PostDB.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
        
        post.like += 1
        db.commit()
        db.refresh(post)
        return post

    @staticmethod
    def delete_post(db: Session, post_id: int):
        post = db.query(PostDB).filter(PostDB.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
        
        db.delete(post)
        db.commit()
        return {"message": f"{post_id}번 게시글이 성공적으로 삭제되었습니다."}