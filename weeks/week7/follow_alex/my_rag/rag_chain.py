from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from glob import glob
import os 


def build_llm():
    provider = os.getenv("LLM_PROVIDER", "google").lower()
    print(f"LLM Provider: {provider}")
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model = os.getenv("OLLAMA_MODEL", "gemma4:e2b-mlx"),
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
    return ChatGoogleGenerativeAI(
        model = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
        google_api_key = os.getenv("GOOGLE_API_KEY"),
    )

def build_rag_chain():
    # ---- 1. 인덱싱 --------------------------------------------------------
    print("=== ✅ 1. 문서 로딩 및 인덱싱 시작... ===")

    md_paths = sorted(glob("../alex_notes/*.md"))
    md_docs = []
    for p in md_paths:
        md_docs.extend(TextLoader(p, encoding="utf-8").load())


    docs = md_docs
    print(f"로딩된 Document 수: {len(docs)}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 500,
        chunk_overlap = 50,
    )
    split_docs = splitter.split_documents(docs)
    print(f"분할된 chunk 수: {len(split_docs)}")    

    embeddings = GoogleGenerativeAIEmbeddings(
        model = "models/gemini-embedding-001",
        google_api_key = os.getenv("GOOGLE_API_KEY")
    )
    vectorstore = Chroma.from_documents(split_docs, embeddings)
    print("=== ✅ 1. 인덱싱 완료 ===\n\n")

    # ---- 2. RAG 파이프라인 --------------------------------------------------------
    print("=== ⭐️ 2. RAG 파이프라인 시작... ===\n")

    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    prompt = ChatPromptTemplate.from_messages([
        ("system", "다음 문서를 근거로 사용자 질문에 답하시오." "근거가 부족하면 '주어진 자료에서는 확인할 수 없습니다.'라고 답하시오. \n\n" "{context}"),
        ("human", "{question}")
    ])

    llm = build_llm()

    def format_docs(ds):
        return "\n\n".join(d.page_content for d in ds)

    rag = (
        {"context": retriever | format_docs, "question" : RunnablePassthrough()} | prompt | llm | StrOutputParser()
    )

    return rag