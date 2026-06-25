# 한 줄 정리

1. HTTP
- 글을 뛰어넘는 글(이미지, 오디오 등)을 전송하는 "규약"

2. HTTP message
- start line + header + empty line + body

3. HTTP request method
- get : 데이터 요청 - 조회 | 게시글 목록
- post : 동작 요청 - 수정, 상태 변경 | 회원가입, 새로운 게시글 작성
- put : 데이터 전체 업데이트 요청 | 프로필 이미지 변경
- patch : 특정 부분만 변경 | 사용자 정보 중 비밀번호만 변경
- delete : 데이터 삭제 | 게시글 삭

4. HTTP Status Code
- 1xx : 정보 메세지
- 2xx : 성공
- 3xx : 리다이렉션
- 4xx : 클라이언트 오류
- 5xx : 서버 오류
[참고] https://developer.mozilla.org/ko/docs/Web/HTTP/Reference/Status

5. HTTP URL
- scheme + Domain + Port + + Path to resource + Parameters





# 그 외 정리

1. RestAPI
- 웹에서 데이터를 주고 받을 때 지켜야 하는 "규약" "규칙"
- http method를 사용해서 CRUD 작업을 수행
- [교재] (내가 만드는) 애플리케이션과 (이미 만들어진) 애플리케이션이 서로 통신할 수 있도록 정의한 "명세서"
- [교재] 대표적인(REpresentational) 상태(State) 전송(Transfer) API

2. FastAPI
- RestAPI를 작성하기 위한 "도구"
- 파이썬 기반의 웹 프레임워크 (다른 종류로는 Express(javascript), Flask(python), Spring Boot(java) 등이 있음)

3. JSON
- 프로그램끼리 데이터를 주고 받기 위해 사용하는 "텍스트 형식"
- 계층적인 트리/객체 형태 : key-value ( <-> csv : 콤마(,)로 구분된 테이블 형태의 텍스트 형식)


