from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

from rag_chain import build_rag_chain

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rag = build_rag_chain()
    yield


app = FastAPI(lifespan = lifespan)

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str


@app.post("/query", response_model = QueryResponse)
def query(req: QueryRequest):
    answer = app.state.rag.invoke(req.question)
    return QueryResponse(answer = answer)
