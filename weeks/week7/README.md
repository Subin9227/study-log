# Week7 과제 총정리

## 1. 과제 목표
- LangChain 기반 RAG 파이프라인 구축
- FastAPI로 REST API 래핑 및 배포
- LangSmith로 체인 실행 Tracing 및 Dataset 기반 평가

<br>

---

<br>

## 2. 버전별 변경 사항 요약

| 버전 | 핵심 변경 | 결과 |
|---|---|---|
| v1 | 원본 코드 그대로 타이핑하며 코드 분석 + `rag_chain.py`로 LLM 빌드 중복 제거 | 기반 구조 완성 |
| v2 | ChromaDB 인덱싱 캐싱, Google → Ollama 전환 | 매번 인덱싱 문제 해결, but 평가 0점 |
| v3 | 감정 60가지 RAG 데이터, 감정 분류 + 공감 챗봇 구현, judge_llm OpenAI 분리 | 파이프라인 완성, but 분류 정확도 낮음 |
| v4 | 버그 수정, 예시 확충, 임베딩 모델 교체 | contains_keyword 1.00, llm_judge 1.00 달성 |

<br>

---

<br>

## 3. 핵심 개념 정리

### 3-1. RAG 흐름
```
사용자 입력
↓
[RAG] 벡터 검색 → emotion_notes/*.md → Chroma DB (bge-m3 임베딩)
↓
[LLM] 감정 코드 분류 → llama3.2 (classify_chain)
↓
[LLM] 공감/위로 메시지 생성 → llama3.2 (respond_chain)
↓
"당신은 지금 OOO을 느끼고 있습니다. + 메시지"
```

### 3-2. 모델 구성 (최종 v4)
| 역할 | 모델 |
|---|---|
| 임베딩 | Ollama `bge-m3` |
| 감정 분류 + 응답 생성 | Ollama `llama3.2` |
| 평가 judge | OpenAI `gpt-4o-mini` |


### 3-3. 파일 구조 (최종 v4)
| 파일 | 역할 |
|---|---|
| `emotion_notes/*.md` | 60가지 감정 데이터 — 감정별 분류/설명/예시 5개 (RAG 검색 대상) |
| `emotion_map.py` | 감정 코드(E10~E69) ↔ 감정명 매핑, 긍정/부정 집합 정의 |
| `rag_chain.py` | 인덱싱 캐싱, 감정 분류 체인, 응답 생성 체인, FastAPI용 파이프라인 조립 |
| `main.py` | FastAPI 서버 — `/query` 엔드포인트로 사용자 입력 받아 응답 반환 |
| `baseline.py` | LangSmith Dataset 생성 및 평가 실험 (`contains_expected_keyword` + `llm_judge`) |


### 3-4. 실행 흐름 (FastAPI 기준)
```
사용자가 POST /query {"question": "오늘 밥이 맛있었어"} 전송
↓
main.py - query()
↓
rag_chain.py - full_chain(user_input)
↓
rag_chain.py - classify_chain.invoke(user_input) 
    ├── retriever.invoke(user_input) 
    │   nomic-embed-text(follow_alex_v3)/bge-m3(follow_alex_v4)로 질문을 벡터로 변환 
    │   → Chroma DB에서 유사한 감정 청크 k개(5개(v3), 7개(v4 이후)) 검색 
    │   → 검색된 청크를 format_docs()로 텍스트로 변환 
    ├── classify_prompt에 {context: 감정후보, question: 질문} 주입 
    └── llama3.2가 감정 코드 1개 출력 (예: E64)
↓
rag_chain.py - full_chain() 내부 
    ├── re.search()로 E64 파싱 
    ├── emotion_map.py - EMO_MAP["E64"] → "만족스러운" 
    └── POSITIVE 집합으로 긍정/부정 판단
↓
rag_chain.py - respond_chain.invoke({emotion, valence, question}) 
    ├── respond_prompt에 {감정명, 긍정/부정, 질문} 주입 
    └── llama3.2가 공감/위로 메시지 생성 
↓
"당신은 지금 만족스러운을 느끼고 있습니다.\n[메시지]" 반환
↓
main.py - QueryResponse(answer=...) JSON 응답
```

<br>

---

<br>


## 4. 겪었던 문제와 해결

| 문제 | 원인 | 해결 | 파일 |
|---|---|---|---|
| 매번 인덱싱 | 벡터를 RAM에만 저장 | ChromaDB `persist_directory`로 디스크 저장 | `rag_chain.py` - `build_rag_chain()` |
| Google API 429 | 무료 티어 일일 한도 초과 | Ollama로 전환 | `rag_chain.py` - `build_llm()` / `.env` |
| 같은 문장인데 감정이 매번 바뀜 | `temperature=0.8` 기본값 | `temperature=0` 고정 | `rag_chain.py` - `build_llm()` |
| LLM이 코드 대신 문서 내용 출력 | 프롬프트 지시 약함 | `classify_prompt` 강화 (출력 형식 예시 추가) | `rag_chain.py` - `classify_prompt` |
| 감정 분류 정확도 낮음 | `nomic-embed-text` 한국어 취약 | `bge-m3`로 교체 + 예시 1개→5개 확충 | `rag_chain.py` - `embeddings` / `emotion_notes/*.md` |


<br>

---

<br>


## 5. 회고

### 5-1. 과정 서술
*  5주차 transformer 를 통한, 자체 모델부터 만들면서 감정을 추출하는 걸 만들려고 했으나.. (https://colab.research.google.com/drive/1dZ-4qfrg8yjdZpn68FDt4WXDoMBiVHXa?usp=sharing) 쉽지가 않았다. 사실 꾸준히 해보고 싶었으나 교육 과정 진도는 계속 나가고 새로운 과제는 또 올라오고.. 
*  결국 우선순위인 "과제 진행"부터 우선으로 하기로 결정. langchain을 어떻게 진행을 해야하나 고민하다 수업시간에 alex가 보여준 데모를 따라해보기로 결정을 했다.
*  [v1] alex-rag( https://github.com/100-hours-a-week/alex-rag )를 pull 하고, 전체 코드를 그대로 타이핑하며 각 파일과 함수들이 어떻게 상호작용하는지를 우선 파악하였다. 직접 타이핑을 하느라 3시간 걸리고, 오타도 많았지만 오타는 ai가 잘 찾아주어서 금방 고쳤고, 확실히 직접 타이핑을 해서 코드가 머리로 들어오는 느낌이 들었다.
*  [v1] 코드를 직접 타이핑하면서 겹치는 부분이 보이길래 클로드와 함께 대화하며 중복 호출되는 함수는 따로 파일을 생성해서 뺐다.
*  [v2] 수업시간에도 언급이 되었듯이, 인덱싱이 매번 되고 있었기에 우선 이 부분을 먼저 chromaDB로 수정을 하였다.
*  [v2] 처음에는 구글의 gemini-2.5-flash를 사용했으나, 계속 일일 한도 초과가 떠서 제대로 동작하는지 확인을 할 수 없었다. 이전 수업에서 설치를 해놨던 ollama를 사용하는 것으로 변경했다.
*  [v3] 어느정도 파일과 동작이 되는 것을 확인하고, 과제로는 "문장을 입력하면 60가지 감정 중 하나의 감정을 추출하고, 긍정의 감정일 경우 공감 / 부정의 감정일 경우 위로"를 하는 로직을 설계하였다.
*  [v3] 이때, ollama가 답변을 하고 또 스스로 판단하는 것이 마음에 안들어 judge는 google로 변경하였으나 마찬가지로 한도 초과 에러 때문에 openai를 충전하고 연결하였다.
*  [v4] 이후에는 `같은 문장을 입력해도 감정이 매번 바뀌는 문제`, `60가지 외의 감정으로 추출되는 문제` 등의 버그를 개선하고, 과제를 마무리하였다.

### 5-2. 느낀점
*  오픈소스인 ollama도 어떤 임베딩(nomic-embed-text, bge-m3)을 쓰냐에 따라 결과가 확 달라지는데, 내가 colab에서 직접 설계해서 돌려본 걸로는 데이터의 양과 기술이 어림이 없겠다는 생각이 들었다.
*  물론 이전에도 api를 가져다가 langchain, fine-tunig을 해보긴 했지만 '그져 가져다가 쓴거 아니야?"라는 생각이 있었다. 하지만 더 딥하게 공부하고 또 직접 타이핑을 해보니 그게 아니라는 것을 알게 되었다. 결국 어떤 데이터를 주느냐, 뭐를 원하느냐에 따라 나오는 결과는 천차만별이다... 
*  이미 있는 모델로 어떻게 더 최상의 결과를 추출할 수 있을지, 어떻게 더 원하는 출력값을 얻을 수 있을지를 앞으로 더 고민을 해봐야겠다. 
*  그리고 직접 해보면서 prompt의 중요성도 좀 느꼇다. 지금까지는 혼자 생각 다 하고 정말 모르는 부분에 대해서만 질문을 하다보니, ai가 내 질문의 의도와는 다른 이야기를 하는 일이 많아서 오히려 더 원하는 값을 뽑아내는데 답답함을 느꼇는데, 배우면서 ai에게 어떻게 입력을 해야 잘 출력을 얻어낼 수 있는가를 점점 알아가는 느낌이다.
*  역시 AI에게 100을 입력하면 100이 나오고, 1을 입력하면 1이 나온다. 앞으로 100을 입력해서 100을 뽑아낼 수 있는 사람이 되자.