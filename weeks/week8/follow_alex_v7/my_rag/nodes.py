import os
import re

from dotenv import load_dotenv
from glob import glob
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from emotion_map import EMO_MAP, POSITIVE
from state import EmotionState

load_dotenv()


# ------- LLM ----------------------------------------

def build_llm():
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    from langchain_ollama import ChatOllama

    nvidia_key = os.getenv("NVIDIA_API_KEY")
    if nvidia_key:
        try:
            llm = ChatOpenAI(
                model = os.getenv("NVIDIA_MODEL", "deepseek-ai/deepseek-v4-pro"),
                api_key = nvidia_key,
                base_url = "https://integrate.api.nvidia.com/v1",
                temperature = 0,
            )
            print(f"=== LLM: NVIDIA NIM ({llm.model_name}) ===")
            return llm
        except Exception as e:
            print(f"=== NVIDIA NIM 연결 실패 ({e}), Claude로 전환 ===")

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            llm = ChatAnthropic(
                model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
                api_key=anthropic_key,
                temperature=0,
            )
            print(f"=== LLM: Claude ({llm.model}) ===")
            return llm
        except Exception as e:
            print(f"=== Claude 연결 실패 ({e}), Ollama로 전환 ===")

    model_name = os.getenv("OLLAMA_MODEL", "llama3.2")
    print(f"=== LLM: Ollama ({model_name}) ===")
    return ChatOllama(
        model=model_name,
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
    )



# ------- Retriever ----------------------------------------

def build_retriever():
    PERSIST_DIR = "./chroma_db"
    embeddings = OllamaEmbeddings(model="bge-m3")

    if os.path.exists(PERSIST_DIR):
        print("=== 기존 인덱스 불러오기 ===")
        vectorstore = Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=embeddings,
        )
    else:
        print("=== 문서 로딩 및 인덱싱 시작 ===")
        md_paths = sorted(glob("../../emotion_notes/*.md"))
        docs = []
        for p in md_paths:
            docs.extend(TextLoader(p, encoding="utf-8").load())

        print(f"로딩된 Document 수: {len(docs)}")

        chunks = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=30,
        ).split_documents(docs)

        print(f"분할된 chunk 수: {len(chunks)}")

        vectorstore = Chroma.from_documents(
            chunks,
            embeddings,
            persist_directory=PERSIST_DIR,
        )
        print("=== 인덱싱 완료 ===")

    return vectorstore.as_retriever(search_kwargs={"k": 7})



# ------- 노드 ----------------------------------------

llm = build_llm()
retriever = build_retriever()

classify_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "아래 감정 후보 목록을 참고해서 사용자 문장에 가장 가까운 감정 코드를 하나만 답하세요.\n"
     "반드시 아래 형식으로만 출력하세요: E60\n"
     "예시 출력: E60\n"
     "다른 텍스트는 절대 출력하지 마세요.\n\n"
     "감정 후보: \n{context}"),

    ("human", 
    "{question}"),
])

respond_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "당신은 사용자의 감정에 공감하고 위로해주는 상담사입니다.\n"
     "사용자가 느끼는 감정: {emotion_name}\n"
     "감정 성격: {valence}\n\n"
     "긍정 감정이면 함께 기뻐하며 위로해주세요.\n"
     "부정 감정이면 따뜻하게 위로해주세요.\n"
     "2~3문장으로 답하세요.\n"),

    ("human", 
    "{question}"),
])

def retrieve_node(state: EmotionState) -> dict:
    docs = retriever.invoke(state["question"])
    return {"context": docs}

def classify_node(state: EmotionState) -> dict:
    context_text = "\n".join(d.page_content for d in state["context"])
    raw = (classify_prompt | llm | StrOutputParser()).invoke({
        "context": context_text,
        "question": state["question"],
    })
    return {"raw_code": raw.strip()}

def map_emotion_node(state: EmotionState) -> dict:
    match = re.search(r"E[1-6]\d", state["raw_code"])
    code = match.group()
    return {
        "emotion_code": code,
        "emotion_name": EMO_MAP[code],
        "valence": "긍정" if code in POSITIVE else "부정",
    }

def respond_node(state: EmotionState) -> dict:
    message = (respond_prompt | llm | StrOutputParser()).invoke(state)
    return {"message": message}

def error_node(state: EmotionState) -> dict:
    return {"error": f"감정 코드 추출 실패. raw: {state['raw_code']}"}



# ------- 조건부 엣지 ----------------------------------------

def route_after_classify(state: EmotionState) -> str:
    if re.search(r"E[1-6]\d", state["raw_code"]):
        return "map_emotion"
    return "error"

    