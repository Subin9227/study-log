import os
import re

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langsmith import Client
from langsmith.evaluation import evaluate

from graph import build_graph

load_dotenv()


# ---- graph ---------------------------------------------------------

graph = build_graph()



# ---- 데이터셋 ---------------------------------------------------------

DATASET_NAME = "emotion_rag_eval"
client = Client()

EVAL_QUESTIONS = [
    {"question": "아무리 해도 안 되니까 포기하고 싶어",  "answer": "좌절한"},
    {"question": "그 사람 생각만 해도 마음이 따뜻해",   "answer": "사랑하는"},
    {"question": "믿었는데 어떻게 나한테 이럴 수 있어",  "answer": "배신당한"},
]

inputs  = [{"question": ex["question"]} for ex in EVAL_QUESTIONS]
outputs = [{"answer":   ex["answer"]}   for ex in EVAL_QUESTIONS]

existing = list(client.list_datasets(dataset_name=DATASET_NAME))

if existing:
    dataset = existing[0]
    print(f"기존 Dataset 사용: {dataset.id}")
else:
    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="RAG 답변 품질 평가용",
    )
    client.create_examples(
        dataset_id=dataset.id,
        inputs=inputs,
        outputs=outputs,
    )
    print(f"새 Dataset 생성 및 Example {len(EVAL_QUESTIONS)}건 추가 완료")



# ---- 평가 대상 함수 ------------------------------------------------

def target(inputs: dict) -> dict:
    result = graph.invoke({"question": inputs["question"], "error": None})
    return {"answer": result.get("emotion_name", "")}



# ---- 평가 함수 1: 키워드 포함 여부 ------------------------------------------------

def contains_expected_keyword(run, example):
    pred       =    run.outputs.get("answer", "")
    expected   =    example.outputs.get("answer", "")
    keywords   =    [w for w in expected.split() if len(w) >= 2][:2]
    hit        =    all(k in pred for k in keywords)
    return {
        "key":      "contains_expected_keyword",
        "score":    1 if hit else 0,
        "comment":  f"필수 키워드 {keywords} 포함 여부",
    }



# ---- 평가 함수 2: LLM Judge ------------------------------------------------

def build_judge_llm():
    from langchain_anthropic import ChatAnthropic
    from langchain_ollama import ChatOllama

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            llm = ChatAnthropic(
                model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
                api_key=anthropic_key,
                temperature=0,
            )
            print(f"=== Judge LLM: Claude ({llm.model}) ===")
            return llm
        except Exception as e:
            print(f"=== Claude 연결 실패 ({e}), Ollama로 전환 ===")

    model_name = os.getenv("OLLAMA_MODEL", "llama3.2")
    print(f"=== Judge LLM: Ollama ({model_name}) ===")
    return ChatOllama(
        model=model_name,
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    )

judge_llm = build_judge_llm()

JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "당신은 llm의 답변 품질을 평가하는 채점자입니다."
     "아래 기대 답변(reference)과 모델 답변(prediction)을 비교하세요."
     "의미가 일치하면 1, 부분적으로만 일치하면 0.5, 무관하면 0을 점수로 매기세요."
     "응답은 반드시 첫 줄에 0/0.5/1 중 하나의 숫자만, 둘째 줄부터 짧은 이유를 적으세요."),
    ("human",
     "질문: {question}\n\n기대 답변: {reference}\n\n모델 답변: {prediction}"),
])

judge_chain = JUDGE_PROMPT | judge_llm | StrOutputParser()

def llm_judge(run, example):
    prediction = run.outputs.get("answer")
    if not prediction:
        return {"key": "llm_judge_semantic_match", "score": 0, "comment": "target 실패로 답변 없음."}


    reply = judge_chain.invoke({
        "question":     example.inputs["question"],
        "reference":    example.outputs["answer"],
        "prediction":   prediction,
    })
    score_match = re.search(r"\b(1(?:\.0)?|0(?:\.5)?|0(?:\.0)?)\b", reply)
    score = float(score_match.group()) if score_match else 0.0

    return {"key": "llm_judge_semantic_match", "score": score, "comment": reply}




# ---- 실행 ------------------------------------------------

result = evaluate(
    target,
    data = DATASET_NAME,
    evaluators = [contains_expected_keyword, llm_judge],
    experiment_prefix = "v7-langgraph-emotion",
    max_concurrency = 1,
)
print(result)