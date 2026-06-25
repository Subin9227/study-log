from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from schemas import Post, PostCreate, PostUpdate
from controllers import PostController

router = APIRouter(prefix="/posts", tags=["Posts"])

@router.post("", response_model=Post)
def create_post(post_data: PostCreate, db: Session = Depends(get_db)):
    return PostController.create_post(db, post_data)

@router.get("", response_model=List[Post])
def get_all_posts(db: Session = Depends(get_db)):
    return PostController.get_all_posts(db)

@router.put("/{post_id}", response_model=Post)
def update_post(post_id: int, update_data: PostUpdate, db: Session = Depends(get_db)):
    return PostController.update_post(db, post_id, update_data)

@router.patch("/{post_id}/like", response_model=Post)
def click_like(post_id: int, db: Session = Depends(get_db)):
    return PostController.click_like(db, post_id)

@router.delete("/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db)):
    return PostController.delete_post(db, post_id)