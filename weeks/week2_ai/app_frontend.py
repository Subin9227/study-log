import streamlit as st
import requests

# FastAPI 백엔드 서버 주소 수정 (/posts 엔드포인트 포함)
BACKEND_URL = "http://127.0.0.1:8000/posts"

st.set_page_config(page_title="AI 커뮤니티 서비스", layout="centered")

st.title("🤖 AI 로컬 댓글 커뮤니티")
st.write("FastAPI 백엔드와 Ollama 로컬 AI 모델이 연동된 커뮤니티 공간입니다.")

# ==========================================
# ➕ 글 작성 섹션
# ==========================================
st.subheader("📝 새 게시글 작성하기")
with st.form("post_form", clear_on_submit=True):
    title = st.text_input("제목", placeholder="글 제목을 입력하세요.")
    description = st.text_area("내용", placeholder="내용을 작성하면 AI가 댓글을 달아줍니다.")
    submit_button = st.form_submit_button("게시글 등록")

if submit_button:
    if not title or not description:
        st.warning("제목과 내용을 모두 입력해 주세요.")
    else:
        payload = {"title": title, "description": description}
        with st.spinner("AI가 게시글을 읽고 댓글을 작성 중입니다..."):
            try:
                response = requests.post(BACKEND_URL, json=payload)
                if response.status_code == 200:
                    st.success("게시글이 성공적으로 등록되었습니다!")
                    st.rerun()
                else:
                    st.error(f"등록 실패: {response.text}")
            except Exception as e:
                st.error(f"백엔드 서버 연결 실패: {str(e)}")

st.markdown("---")

# ==========================================
# 🔍 글 목록 및 피드 섹션
# ==========================================
st.subheader("📌 전체 게시글 목록")

try:
    response = requests.get(BACKEND_URL)
    if response.status_code == 200:
        posts = response.json()
        
        if not posts:
            st.info("아직 작성된 게시글이 없습니다. 첫 번째 글을 남겨보세요!")
            
        for post in reversed(posts):
            with st.container():
                st.markdown(f"### 📄 {post['title']}")
                st.write(post['description'])
                
                # 기능 버튼 구조 (좋아요, 삭제, 수정 버튼 배치)
                col1, col2, col3 = st.columns([1, 1, 4])
                with col1:
                    if st.button(f"❤️ {post['like']}", key=f"like_{post['id']}"):
                        requests.patch(f"{BACKEND_URL}/{post['id']}/like")
                        st.rerun()
                with col2:
                    if st.button("🗑️ 삭제", key=f"del_{post['id']}"):
                        requests.delete(f"{BACKEND_URL}/{post['id']}")
                        st.rerun()
                with col3:
                    if st.button("✏️ 수정", key=f"edit_btn_{post['id']}"):
                        st.session_state[f"editing_{post['id']}"] = True
                
                # 수정 폼 활성화 시 입력창 노출
                if st.session_state.get(f"editing_{post['id']}", False):
                    with st.form(key=f"edit_form_{post['id']}"):
                        new_title = st.text_input("새 제목", value=post['title'])
                        new_desc = st.text_area("새 내용", value=post['description'])
                        
                        col_sub1, col_sub2 = st.columns(2)
                        with col_sub1:
                            submit_edit = st.form_submit_button("변경 저장")
                        with col_sub2:
                            cancel_edit = st.form_submit_button("취소")
                            
                        if submit_edit:
                            update_payload = {"title": new_title, "description": new_desc}
                            res = requests.put(f"{BACKEND_URL}/{post['id']}", json=update_payload)
                            if res.status_code == 200:
                                st.success("글이 성공적으로 수정되었습니다!")
                                st.session_state[f"editing_{post['id']}"] = False
                                st.rerun()
                            else:
                                st.error("수정에 실패했습니다.")
                                
                        if cancel_edit:
                            st.session_state[f"editing_{post['id']}"] = False
                            st.rerun()

                # AI 댓글 영역 디자인
                if post.get('ai_comment'):
                    st.chat_message("assistant").write(f"**AI봇:** {post['ai_comment']}")
                
                st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.error("데이터를 가져오는 데 실패했습니다.")
except Exception as e:
    st.error(f"백엔드 서버와 연결할 수 없습니다. 서버가 켜져 있는지 확인하세요. ({str(e)})")