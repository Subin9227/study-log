import os
import re
from glob import glob

from dotenv import load_dotenv
from langchain_chroma import Chroma 
from langchain_community.document_loaders import TextLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel

from emotion_map import EMO_MAP, POSITIVE

load_dotenv()

# ------- Structured Output 모델 ----------------------------------------

class EmotionResult(BaseModel):
    emotion_code: str 
    emotion_name: str
    valence: str
    message: str


# ------- LLM ----------------------------------------

def build_llm():
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    from langchain_ollama import ChatOllama

    nvidia_key = os.getenv("NVIDIA_API_KEY")
    if nvidia_key:
        try:
            llm = ChatOpenAI(
                model=os.getenv("NVIDIA_MODEL", "deepseek-ai/deepseek-v4-pro"),
                api_key=nvidia_key,
                base_url="https://integrate.api.nvidia.com/v1",
                temperature=0,
            )
            llm.invoke("ping")
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
            llm.invoke("ping")
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


# ------- RAG 체인 ----------------------------------------

def build_rag_chain():

    # 1. indexing
    PERSIST_DIR = "./chroma_db"
    embeddings = OllamaEmbeddings(model = "bge-m3")

    if os.path.exists(PERSIST_DIR):
        print("=== 기존 인덱스가 존재합니다 ===")
        print("=== 📚 1. 기존 인덱스 불러오기 ===")
        vectorstore = Chroma(
            persist_directory = PERSIST_DIR,
            embedding_function = embeddings,
        )
    else:
        print("=== 기존 인덱스가 존재하지 않습니다 ===")
        print("=== ✅ 1. 문서 로딩 및 인덱싱 시작 ===")
        md_paths = sorted(glob("../../emotion_notes/*.md"))
        docs = []
        for p in md_paths:
            docs.extend(TextLoader(p, encoding = 'utf-8').load())

        print(f"1-1. 로딩된 Document 수: {len(docs)}")

        chunks = RecursiveCharacterTextSplitter(
            chunk_size = 500,
            chunk_overlap = 30,
        ).split_documents(docs)

        print(f"1-2. 분할된 chunk 수: {len(chunks)}")

        vectorstore = Chroma.from_documents(
            chunks,
            embeddings,
            persist_directory = PERSIST_DIR,
        )
        print("=== 인덱싱이 완료 되었습니다 ===\n")


    # 2. 감정 분류 체인
    print("=== ⭐️ 2. RAG 파이프라인 시작.. ===")

    retriever = vectorstore.as_retriever(search_kwargs = {"k":7})
    llm = build_llm()

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

    classify_chain = (
        {"context": retriever | (lambda ds: "\n".join(d.page_content for d in ds)),
        "question": RunnablePassthrough()}
        | classify_prompt
        | llm
        | StrOutputParser()
    )

    # 3. 응답 생성 체인
    respond_prompt = ChatPromptTemplate.from_messages([
        ("system",
        "당신은 사용자의 감정에 공감하고 위로해주는 상담사입니다.\n"
        "사용자가 느끼는 감정: {emotion}"
        "감정 성격: {valence}\n\n"
        "긍정 감정이면 함께 기뻐하며 위로해주세요.\n"
        "부정 감정이면 따뜻하게 위로해주세요.\n"
        "2~3문장으로 답하세요.\n"),

        ("human",
        "{question}"),
    ])

    respond_chain = respond_prompt | llm | StrOutputParser()

    # 4. 전체 체인
    def full_chain(user_input: str) -> EmotionResult:
        raw = classify_chain.invoke(user_input).strip()

        code_match = re.search(r"E[1-6]\d", raw)
        if code_match is None:
            raise ValueError(f"감정 코드를 추출하지 못했습니다. raw: {raw}")
        code = code_match.group()

        emotion = EMO_MAP[code]
        valence = "긍정" if code in POSITIVE else "부정"

        message = respond_chain.invoke({
            "emotion": emotion,
            "valence": valence,
            "question": user_input,
        })

        return EmotionResult(
            emotion_code = code,
            emotion_name = emotion,
            valence = valence,
            message = message,
        )
    
    return RunnableLambda(full_chain), llm
