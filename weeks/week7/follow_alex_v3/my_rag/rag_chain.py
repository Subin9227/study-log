from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from dotenv import load_dotenv
from glob import glob
import os 
import re

from langchain_ollama import OllamaEmbeddings
from emotion_map import EMO_MAP, POSITIVE


def build_llm():                                                        # ollama 로 진행
    #provider = os.getenv("LLM_PROVIDER", "google").lower()
    print(f"LLM Provider: ollama")
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model = os.getenv("OLLAMA_MODEL", "llama3.2"),
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    )
    # if provider == "ollama":
    #     from langchain_ollama import ChatOllama
    #     return ChatOllama(
    #         model = os.getenv("OLLAMA_MODEL", "gemma4:e2b-mlx"),
    #         base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    #     )
    # return ChatGoogleGenerativeAI(
    #     model = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
    #     google_api_key = os.getenv("GOOGLE_API_KEY"),
    # )

def build_rag_chain():
    # ---- 1. 인덱싱 --------------------------------------------------------

    PERSIST_DIR = "./chroma_db"

    embeddings = OllamaEmbeddings(
        model = "nomic-embed-text",
    )

    if os.path.exists(PERSIST_DIR):
        print("=== 📚 기존 인덱스 불러오기 ===")                 # 이미 저장된 인덱스가 있으면 그대로 불러오기 (재인덱싱X)
        vectorstore = Chroma(
            persist_directory = PERSIST_DIR,
            embedding_function = embeddings,
        )
    else:                                                   # 없으면 새로 인덱싱하고 디스크에 저장
        print("=== ✅ 1. 문서 로딩 및 인덱싱 시작... ===")

        md_paths = sorted(glob("../emotion_notes/*.md"))    # 감정이 들어있는 노트 폴더
        md_docs = []
        for p in md_paths:
            md_docs.extend(TextLoader(p, encoding="utf-8").load())


        print(f"로딩된 Document 수: {len(md_docs)}")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size = 300,
            chunk_overlap = 30,
        )
        split_docs = splitter.split_documents(md_docs)
        print(f"분할된 chunk 수: {len(split_docs)}")    

        vectorstore = Chroma.from_documents(
            split_docs, 
            embeddings, 
            persist_directory = PERSIST_DIR,
        )
    
        print("=== ✅ 1. 인덱싱 완료 ===\n")
 

    # ---- 2. 감정 분류 체인 --------------------------------------------------------
    print("=== ⭐️ 2. RAG 파이프라인 시작... ===\n")

    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    llm = build_llm()

    classify_prompt = ChatPromptTemplate.from_messages([
        ("system",
        "아래 감정 후보 목록을 참고해서 사용자 문장에 가장 가까운 감정 코드를 하나만 답하세요.\n"
        "반드시 E10~E69 중 하나의 코드만 출력하세요. 다른 말은 하지 마세요.\n\n"
        "감정후보:\n{context}"),

        ("human", 
        "{question}"),
    ])

    def format_docs(ds):
        return "\n".join(d.page_content for d in ds)

    classify_chain = (
        {"context" : retriever | format_docs, "question" : RunnablePassthrough()} | classify_prompt | llm | StrOutputParser()
    )

    # ---- 3. 응답 생성 체인 --------------------------------------------------------
    respond_prompt = ChatPromptTemplate.from_messages([
        ("system",
        "당신은 사용자의 감정에 공감하고 위로해주는 상담사입니다.\n"
        "사용자가 느끼는 감정: {emotion}\n"
        "감정 성격: {valence}\n\n"
        "긍정 감정이면 함께 기뻐하며 공감해주세요.\n"
        "부정 감정이면 따뜻하게 위로해주세요.\n"
        "2~3문장으로 답하세요."),

        ("human",
        "{question}"),
    ])

    respond_chain = respond_prompt | llm | StrOutputParser()

    def full_chain(user_input: str) -> str:
        raw = classify_chain.invoke(user_input).strip()             # 1) 감정 코드 분류
        code = re.search(r"E[1-6]\d", raw)
        if code is None:
            return "감정을 파악하지 못했습니다. 조금 더 자세히 말씀해주세요!"
        code = code.group()
    
        emotion = EMO_MAP[code]
        valence = "긍정" if code in POSITIVE else "부정"

        response = respond_chain.invoke({                           # 2) 응답 생성
            "emotion" : emotion,
            "valence" : valence,
            "question" : user_input,
        })

        return f"당신은 지금 **{emotion}**을 느끼고 있습니다.\n{response}"

    return RunnableLambda(full_chain), llm