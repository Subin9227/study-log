from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os

from rag_chain import build_llm, build_rag_chain

load_dotenv()

# ---- 2. RAG 파이프라인 --------------------------------------------------------
print("============= ⭐️ llm 호출하기 =============")
rag, llm = build_rag_chain()                            # 파이프라인 조립 : rag_chain.py로 가서 조립

print(rag.invoke("while은 언제 사용하나요?"))               # invoke를 하며 ollama에 질문 보내기


# ---- 3. 평가 --------------------------------------------------------
from langsmith.evaluation import evaluate
from langsmith import Client

DATASET_NAME = "alex_notes_rag_eval"
client = Client()

EVAL_QUESTION = [
    {"question" : "int는 무엇인가요?"   ,  "answer" : "소수점이 없는 정수 데이터를 저장하는 자료형입니다."},
    {"question" : "float은 무엇인가요?" ,  "answer" : "실수를 컴퓨터 메모리에 저장하고 연산하는 데이터 타입입니다."},
    {"question" : "sum은 언제 쓰나요?"  ,  "answer" : "숫자로 이루어진 시퀀스의 총합을 구하는 데 사용됩니"}
]
print(f"검증 질문 수: {len(EVAL_QUESTION)}")

existing = [d for d in client.list_datasets(dataset_name = DATASET_NAME)]
inputs = [{"question" : ex["question"]} for ex in EVAL_QUESTION]
outputs = [{"answer"  : ex["answer"]}   for ex in EVAL_QUESTION]

if existing:
    dataset = existing[0]
    print(f"기존 Dataset 사용: {dataset.id}")
else:
    dataset = client.create_dataset(
        dataset_name = DATASET_NAME,
        description = "RAG 답변 품질 평가용",
    )
    print(f"새 Dataset 생성: {dataset.id}")
    client.create_examples(
        dataset_id = dataset.id,
        inputs = inputs,
        outputs = outputs,
    )
    print(f"Example {len(EVAL_QUESTION)}건 추가 완료")

loaded = client.read_dataset(dataset_name = DATASET_NAME)
examples = list(client.list_examples(dataset_id = loaded.id))
print(f"총 Example 수: {len(examples)}")

for ex in examples[:3]:
    print(">>> Q:", ex.inputs["question"])
    print(">>> A:", ex.outputs["answer"] if ex.outputs else "(없음)")
    print()

def target(inputs):
    return {"answer" : rag.invoke(inputs["question"])}

def contains_expected_keyword(run, example):
    pred = run.outputs.get("answer", "")
    expected = example.outputs.get("answer", "")
    keywords = [w for w in expected.split() if len(w) >= 2][:2]
    hit = all(k in pred for k in keywords)
    return {
        "key"     : "contains_expected_keyword",
        "score"   : 1 if hit else 0,
        "comment" : f"필수 키워드 {keywords} 포함 여부",  
    }

JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "당신은 llm의 답변 품질을 평가하는 채점자입니다.\n 아래 기대 답변(reference)과 모델 답변(prediction)을 비교하고, \n 의미가 일치하면 1, 부분적으로만 일치하면 0.5, 무관하면 0을 점수로 매기세요.\n 응답은 반드시 첫 줄에 0/0.5/1 중 하나의 숫자만, 둘째 줄부터 짧은 이유를 적으세요."),
    ("human", "질문: {question}\n\n 기대 답변: {reference}\n\n 모델 답변: {prediction}"),
])

judge_chain = JUDGE_PROMPT | llm | StrOutputParser()

def llm_judge(run, example):

    prediction = run.outputs.get("answer")                  # target 함수가 실패했을 때 answer 키가 없는 경우
    if prediction is None:
        return {"key" : "llm_judge_semantic_match", "score" : 0, "comment" : "target 실패로 답변 없음"}

    reply = judge_chain.invoke({
        "question"   :  example.inputs["question"],
        "reference"  :  example.outputs["answer"],
        "prediction" :  prediction,
    })
    first_line = reply.strip().splitlines()[0].strip()
    try:
        score = float(first_line)
    except ValueError:
        score = 0
    return {"key" : "llm_judge_semantic_match", "score" : score, "comment" : reply,}

result = evaluate(
    target,
    data = DATASET_NAME,
    evaluators =[contains_expected_keyword, llm_judge],
    experiment_prefix = "v2-baseline",
)
print(result)