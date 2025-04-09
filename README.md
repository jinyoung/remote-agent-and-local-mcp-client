
# Remote Agent and Local MCP

이 프로젝트는 클라우드에서 실행되는 에이전트(MCP 호스트)와 로컬에서 실행되는 MCP 클라이언트 간의 통신을 구현합니다.

## 프로젝트 구조

```
.
├── remote-agent/         # 클라우드 에이전트 (Python/FastAPI)
│   ├── main.py          # FastAPI 서버 구현
│   └── requirements.txt  # Python 의존성
└── local-mcp/           # 로컬 MCP 클라이언트 (TypeScript)
    ├── src/             # 소스 코드
    │   └── index.ts     # MCP 클라이언트 구현
    ├── package.json     # Node.js 의존성
    └── tsconfig.json    # TypeScript 설정
```

## 설치 및 실행

### 1. 클라우드 에이전트 (Remote Agent) 설정

```bash
# 디렉토리 생성 및 이동
cd remote-agent

# Python 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python main.py
```

서버가 성공적으로 시작되면 `http://localhost:8000`에서 실행됩니다.

### 2. 로컬 MCP 클라이언트 설정

```bash
# 새 터미널에서
cd local-mcp

# Node.js 의존성 설치
npm install

# TypeScript 컴파일 및 실행
npm start
```

## 테스트

1. **연결 테스트**

클라이언트가 시작되면 자동으로 서버에 SSE 연결을 시도합니다. 성공적인 연결 시 다음 메시지가 표시됩니다:
```
Connecting to http://127.0.0.1:8000/connect/test-client-1
SSE connection established successfully
```

2. **명령 전송 테스트**

새 터미널에서 다음 명령을 실행하여 테스트 명령을 전송할 수 있습니다:

```bash
curl -X POST http://127.0.0.1:8000/test/send_command/test-client-1 \
  -H "Content-Type: application/json" \
  -d '{"id": "test123", "tool": "test", "params": {"message": "Hello from server"}}' \
  -v
```

3. **Playwright 브라우저 테스트**

Playwright를 사용하여 브라우저를 제어하는 명령을 전송할 수 있습니다:

```bash
# 브라우저 설치 (필요한 경우)
curl -X POST http://127.0.0.1:8000/test/send_command/test-client-1 \
  -H "Content-Type: application/json" \
  -d '{"id": "install1", "tool": "mcp_playwright_browser_install", "params": {"random_string": "install"}}' \
  -v

# 웹사이트 탐색
curl -X POST http://127.0.0.1:8000/test/send_command/test-client-1 \
  -H "Content-Type: application/json" \
  -d '{"id": "browser1", "tool": "playwright__navigate", "params": {"url": "https://www.naver.com"}}' \
  -v
```

## 문제 해결

1. **SSE 연결 문제**
   - 서버가 실행 중인지 확인
   - 클라이언트의 CLOUD_HOST 설정이 올바른지 확인
   - 방화벽 설정 확인

2. **도구 실행 실패**
   - 클라이언트 로그에서 사용 가능한 도구 목록 확인
   - 정확한 도구 이름 사용
   - Playwright 브라우저가 설치되어 있는지 확인

3. **로그 확인**
   - 클라우드 에이전트: 디버그 모드로 실행 (`--log-level debug`)
   - 로컬 MCP 클라이언트: 콘솔 로그 확인

## 주요 엔드포인트

- `GET /connect/{client_id}`: SSE 연결 엔드포인트
- `POST /test/send_command/{client_id}`: 테스트 명령 전송
- `POST /result/{client_id}`: 명령 실행 결과 수신

## 참고 사항

- 클라이언트 ID는 기본값으로 "test-client-1"을 사용
- 모든 명령은 JSON 형식으로 전송
- SSE 연결은 자동으로 재연결을 시도함
- Playwright 도구는 브라우저 자동화에 사용됨
