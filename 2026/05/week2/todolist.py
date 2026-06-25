from typing import Optional, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# 📦 할 일 데이터를 임시로 저장해둘 가상의 보관함 (메모리 DB)
todo_db = {}
# 할 일마다 붙여줄 고유한 번호(ID) 카운터
id_counter = 1


# 📋 할 일 데이터의 규칙(양식) 정의
class Todo(BaseModel):
    title: str                      # 할 일 제목 (필수)
    description: Optional[str] = None # 상세 설명 (선택)
    is_done: bool = False           # 완료 여부 (기본값은 안 끝남)


@app.get("/")
def read_root():
    return {"message": "나만의 투두리스트 API 서버에 오신 것을 환영합니다!"}


# 1. 🆕 POST /todos : 새로운 할 일 추가하기
@app.post("/todos")
def create_todo(todo: Todo):
    global id_counter
    
    # 받은 데이터를 보관함에 넣고 번호 매기기
    todo_data = {
        "id": id_counter,
        "title": todo.title,
        "description": todo.description,
        "is_done": todo.is_done
    }
    todo_db[id_counter] = todo_data
    
    # 다음 할 일을 위해 번호 1 증가시키기
    id_counter += 1
    
    return {"message": "할 일이 추가되었습니다!", "data": todo_data}


# 2. 📋 GET /todos : 전체 할 일 목록 보기
@app.get("/todos")
def get_all_todos():
    # 보관함에 있는 내용들을 리스트 형태로 쫘르륵 보여줍니다.
    return list(todo_db.values())


# 3. 🔍 GET /todos/{todo_id} : 특정 할 일 하나만 보기 (단건 조회)
@app.get("/todos/{todo_id}")
def get_one_todo(todo_id: int):
    if todo_id in todo_db:
        return todo_db[todo_id]
    raise HTTPException(status_code=404, detail="해당 번호의 할 일을 찾을 수 없습니다.")


# 4. ✏️ PUT /todos/{todo_id} : 할 일 전체 내용 새 서류로 갈아엎기 (전체 수정)
@app.put("/todos/{todo_id}")
def update_todo_completely(todo_id: int, todo: Todo):
    if todo_id not in todo_db:
        raise HTTPException(status_code=404, detail="수정하려는 할 일이 존재하지 않습니다.")
    
    # 기존 서류를 무시하고 사용자가 새로 보낸 세트로 통째로 교체합니다.
    todo_db[todo_id] = {
        "id": todo_id,
        "title": todo.title,
        "description": todo.description,
        "is_done": todo.is_done
    }
    return {"message": "할 일 전체가 전면 수정되었습니다.", "data": todo_db[todo_id]}


# 5. 🎯 PATCH /todos/{todo_id} : 다른 건 두고 완료 체크박스만 가볍게 클릭 (일부 수정)
@app.patch("/todos/{todo_id}")
def toggle_todo_done(todo_id: int, is_done: bool):
    if todo_id not in todo_db:
        raise HTTPException(status_code=404, detail="할 일을 찾을 수 없습니다.")
    
    # 다른 데이터(제목, 설명)는 그대로 두고, 오직 완료 여부(is_done)만 콕 집어서 바꿉니다.
    todo_db[todo_id]["is_done"] = is_done
    return {"message": "완료 상태가 변경되었습니다.", "data": todo_db[todo_id]}


# 6. ❌ DELETE /todos/{todo_id} : 할 일 지우개로 지우기 (삭제)
@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int):
    if todo_id in todo_db:
        # 보관함에서 해당 번호 삭제
        del todo_db[todo_id]
        return {"message": f"{todo_id}번 할 일이 성공적으로 삭제되었습니다."}
    raise HTTPException(status_code=404, detail="삭제하려는 할 일이 이미 없습니다.")