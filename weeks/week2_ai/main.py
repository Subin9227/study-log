from fastapi import FastAPI
from database import engine, Base
import routers

# 애플리케이션 시작 시 DB 테이블 로드
Base.metadata.create_all(bind=engine)

app = FastAPI()

# 설계한 라우터 구조 연결
app.include_router(routers.router)