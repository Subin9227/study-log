import re

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from rag_chain import build_rag_chain

load_dotenv()


# ---- Middleware ---------------------------------------------------------

class PIIFilterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        body = await request.body()
        text = body.decode("utf-8")

        patterns = {
            "전화번호": r"\d{3}-\d{3,4}-\d{4}",
            "이메일": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "주민번호": r"\d{6}-\d{7}",
        }

        for name, pattern in patterns.items():
            if re.search(pattern, text):
                return JSONResponse(
                    status_code = 400,
                    content = {"error": f"개인정보({name})가 포함되어 있습니다."},
                )

        return await call_next(request)


# ---- APP ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rag, _ = build_rag_chain()
    yield

app = FastAPI(lifespan = lifespan)
app.add_middleware(PIIFilterMiddleware)


# ---- Schema ---------------------------------------------------------

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    emotion_code: str
    emotion_name: str
    valence: str
    message: str


# ---- Endpoint ---------------------------------------------------------

@app.post("/query", response_model = QueryResponse)
def query(req: QueryRequest):
    try:
        result = app.state.rag.invoke(req.question)
    except ValueError as e:
        raise HTTPException(status_code = 422, detail = str(e))

    return QueryResponse(
        emotion_code = result.emotion_code,
        emotion_name = result.emotion_name,
        valence = result.valence,
        message = result.message,
    )

