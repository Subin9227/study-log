from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

from rag_chain import build_rag_chain

import re
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rag, _ = build_rag_chain()
    yield



# ==== v5 에서 추가 ========================
class PIIFilterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        body = await request.body()
        text = body.decode("utf-8")

        patterns = {
            "전화번호" : r"\d{3}-\d{3,4}-\d{4}",
            "이메일" : r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "주민번호" : r"\d{6}-\d{7}",
        }

        for name, pattern in patterns.items():
            if re.search(pattern, text):
                return JSONResponse(
                    status_code = 400,
                    content = {"error": f"개인정보({name})가 포함되어 있습니다."},
                )
        
        return await call_next(request)
# ========================================


app = FastAPI(lifespan = lifespan)


app.add_middleware(PIIFilterMiddleware)



class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):                             # v5에서 변경
    emotion_code: str
    emotion_name: str
    valence: str
    message: str


@app.post("/query", response_model = QueryResponse)         # v5에서 변경
def query(req: QueryRequest):
    result = app.state.rag.invoke(req.question)
    return QueryResponse(
        emotion_code = result.emotion_code,
        emotion_name = result.emotion_name,
        valence = result.valence,
        message = result.message, 
    )
