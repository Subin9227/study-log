from __future__ import annotations
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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

app = FastAPI()

post_db: List[Post] = []
id_counter = 1

# ➕ [CREATE] 게시글 등록
@app.post("/posts", response_model=Post)
def create_post(post_data: PostCreate):
    global id_counter
    
    # 사용자가 보낸 제목과 내용에 id와 초기 like(0)를 조합하여 저장
    new_post = Post(
        id=id_counter,
        title=post_data.title,
        description=post_data.description,
        like=0
    )
    post_db.append(new_post)
    id_counter += 1  # 다음 글을 위해 ID 증가
    return new_post

# 🔍 [READ] 게시글 전체 조회 (테스트 편의용)
@app.get("/posts", response_model=List[Post])
def get_all_posts():
    return post_db

# ✏️ [UPDATE] 게시글 수정
@app.put("/posts/{post_id}", response_model=Post)
def update_post(post_id: int, update_data: PostUpdate):
    for post in post_db:
        if post.id == post_id:
            # 값이 들어온 필드만 골라서 수정 (선택적 수정 가능)
            if update_data.title is not None:
                post.title = update_data.title
            if update_data.description is not None:
                post.description = update_data.description
            return post
            
    raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

# ❤️ [UPDATE] 좋아요 버튼 클릭 (숫자 1 증가)
@app.patch("/posts/{post_id}/like", response_model=Post)
def click_like(post_id: int):
    for post in post_db:
        if post.id == post_id:
            post.like += 1  # 좋아요 수 1 증가
            return post
            
    raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

# ❌ [DELETE] 게시글 삭제
@app.delete("/posts/{post_id}")
def delete_post(post_id: int):
    for post in post_db:
        if post.id == post_id:
            post_db.remove(post)
            return {"message": f"{post_id}번 게시글이 성공적으로 삭제되었습니다."}
            
    raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")