from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

load_dotenv()

# 인덱싱
print("문서 로딩 및 인덱싱 시작...")
from glob import glob

md_paths = sorted(glob("../alex-notes/*.md"))
md_docs = []
for p in md_paths:
    md_docs.extend(TextLoader(p, encoding="utf-8").load())

docs = md_docs
print(f"로딩된 Document 수: {len(docs)}")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)
split_docs = splitter.split_documents(docs)
print(f"분할된 chunk 수: {len(split_docs)}")

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)
vectorstore = Chroma.from_documents(split_docs, embeddings)

print("인덱싱 완료")

# RAG
print("RAG 파이프라인 시작...")
# Retriever를 통해 관련 문서를 검색하고, LLM을 통해 답변을 생성하는 RAG 파이프라인 구성
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# Augmented Generation을 위한 Prompt 구성
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "다음 문서를 근거로 사용자 질문에 답하세요. "
     "근거가 부족하면 '주어진 자료에서는 확인할 수 없습니다.'라고 답하세요.\n\n"
     "{context}"),
    ("human", "{question}"),
])

def build_llm():
    provider = os.getenv("LLM_PROVIDER", "google").lower()
    print(f"LLM Provider: {provider}")
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "gemma4:e2b-mlx"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
    return ChatGoogleGenerativeAI(
        model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )


llm = build_llm()

def format_docs(ds):
    return "\n\n".join(d.page_content for d in ds)

rag = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

print(rag.invoke("행렬의 곱은 함수의 무엇인가요?"))

print("RAG 파이프라인 완료")

# 평가
from langsmith.evaluation import evaluate
from langsmith import Client

DATASET_NAME = "alex-notes-rag-eval"

client = Client()

EVAL_QUESTIONS = [
    {
        "question": "행렬의 곱은 함수의 무엇인가요?",
        "answer":   "행렬의 곱은 두 개의 행렬을 입력으로 받아 새로운 행렬을 출력하는 함수입니다.",
    },
    {
        "question": "실수는 어떻게 구성하나요?",
        "answer":   "실수는 유리수와 무리수를 포함하는 수 체계로, 수직선 위의 모든 점을 나타낼 수 있습니다.",
    },
    {
        "question": "확률 분포는 무엇인가요?",
        "answer":   "확률 분포는 랜덤 변수가 특정 값을 가질 확률을 나타내는 함수입니다.",
    },
    {
        "question": "라돈-니코딤 정리는 무엇인가요?",
        "answer":   "라돈-니코딤 정리는 함수 공간에서의 수렴성에 관한 정리로, 특정 조건 하에 함수열이 수렴함을 보장합니다.",
    },
    {
        "question": "리만 적분 가능한 함수는 어떤 특징을 가지나요?",
        "answer":   "리만 적분 가능한 함수는 구간 내에서 유한 개의 불연속점을 가진 함수로, 리만 합을 통해 적분값을 정의할 수 있습니다.",
    },
]
print(f"검증 질문 수: {len(EVAL_QUESTIONS)}")

existing = [d for d in client.list_datasets(dataset_name=DATASET_NAME)]

inputs  = [{"question": ex["question"]} for ex in EVAL_QUESTIONS]
outputs = [{"answer":   ex["answer"]}   for ex in EVAL_QUESTIONS]

if existing:
    dataset = existing[0]
    print(f"기존 Dataset 사용: {dataset.id}")
else:
    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="어댑터즈 RAG 답변 품질 평가용",
    )
    print(f"새 Dataset 생성: {dataset.id}")
    client.create_examples(
        dataset_id=dataset.id,
        inputs=inputs,
        outputs=outputs,
    )
    print(f"Example {len(EVAL_QUESTIONS)}건 추가 완료")

loaded = client.read_dataset(dataset_name=DATASET_NAME)

examples = list(client.list_examples(dataset_id=loaded.id))
print(f"총 Example 수: {len(examples)}")

for ex in examples[:3]:
    print("Q:", ex.inputs["question"])
    print("A:", ex.outputs["answer"] if ex.outputs else "(없음)")
    print()

def target(inputs):
    return {"answer": rag.invoke(inputs["question"])}

def contains_expected_keyword(run, example):
    pred = run.outputs.get("answer", "")
    expected = example.outputs.get("answer", "")

    # === 기대 답변에서 명사로 보이는 단어 한두 개를 키워드로 사용 ===
    keywords = [w for w in expected.split() if len(w) >= 2][:2]
    hit = all(k in pred for k in keywords)

    return {
        "key": "contains_expected_keyword",
        "score": 1 if hit else 0,
        "comment": f"필수 키워드 {keywords} 포함 여부",
    }

JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "당신은 답변 품질을 평가하는 채점자입니다.\n"
     "아래 기대 답변(reference)과 모델 답변(prediction)을 비교하고,\n"
     "의미가 일치하면 1, 부분적으로만 일치하면 0.5, 무관하면 0을 점수로 매기세요.\n"
     "응답은 반드시 첫 줄에 0/0.5/1 중 하나의 숫자만, 둘째 줄부터 짧은 이유를 적으세요."),
    ("human",
     "질문: {question}\n\n"
     "기대 답변: {reference}\n\n"
     "모델 답변: {prediction}"),
])

judge_chain = JUDGE_PROMPT | llm | StrOutputParser()

def llm_judge(run, example):
    reply = judge_chain.invoke({
        "question": example.inputs["question"],
        "reference": example.outputs["answer"],
        "prediction": run.outputs["answer"],
    })
    # === 첫 줄의 숫자만 점수로 사용 ===
    first_line = reply.strip().splitlines()[0].strip()
    try:
        score = float(first_line)
    except ValueError:
        score = 0
    return {
        "key": "llm_judge_semantic_match",
        "score": score,
        "comment": reply,
    }

result = evaluate(
    target,
    data=DATASET_NAME,
    evaluators=[contains_expected_keyword, llm_judge],
    experiment_prefix="v1-baseline",
)

print(result)
# def main():
#     print("Hello from rag-project!")


# if __name__ == "__main__":
#     main()
