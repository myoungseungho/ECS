# Agent Communication Protocol v1.0

> 서버 에이전트와 클라이언트 에이전트가 Git을 통해 비동기 메시지를 교환하는 프로토콜

## 개요

```
서버 에이전트 (Server Agent)          클라 에이전트 (Client Agent)
      │                                      │
      │  _comms/server_to_client/S###_*.md   │
      │  ──────────────────────────────────▶ │
      │                                      │
      │  _comms/client_to_server/C###_*.md   │
      │  ◀────────────────────────────────── │
      │                                      │
      │  _comms/agreements/*.json            │
      │  ◀──────── 합의 ────────▶            │
```

- **통신 매체**: Git (GitHub Repository)
- **전송**: `git add` + `git commit` + `git push`
- **수신**: `git pull` → 새 파일 확인
- **메시지 단위**: 마크다운 파일 1개 = 메시지 1개

---

## 디렉토리 구조

```
_comms/
├── PROTOCOL.md                  # 이 문서 (통신 규약)
├── SERVER_AGENT_GUIDE.md        # 서버 에이전트 운영 가이드
├── CLIENT_AGENT_GUIDE.md        # 클라 에이전트 운영 가이드
├── status_board.json            # 양측 현재 상태 (실시간)
│
├── server_to_client/            # 서버 → 클라 메시지
│   ├── S001_*.md
│   ├── S002_*.md
│   └── ...
│
├── client_to_server/            # 클라 → 서버 메시지
│   ├── C001_*.md
│   ├── C002_*.md
│   └── ...
│
└── agreements/                  # 양측 합의된 스펙
    ├── packet_protocol.json     #   확정 패킷 규격
    ├── test_contract.json       #   E2E 테스트 계약
    └── ...
```

---

## 메시지 포맷

### 파일명 규칙

```
{방향}{번호}_{제목}.md

방향:
  S = Server → Client (서버가 보냄)
  C = Client → Server (클라가 보냄)

번호: 3자리 (001, 002, ...)
제목: snake_case, 영문

예시:
  S001_system_ready.md
  S002_party_system_spec.md
  C001_question_packet_format.md
  C002_test_result_login.md
```

### 프론트매터 (필수)

모든 메시지 파일 상단에 YAML 프론트매터를 포함합니다:

```yaml
---
id: S001                    # 메시지 고유 ID
from: server-agent          # 발신자: server-agent | client-agent
to: client-agent            # 수신자: server-agent | client-agent
type: spec                  # 메시지 유형 (아래 표 참조)
priority: P1                # 우선순위: P0(긴급) P1(높음) P2(보통) P3(낮음)
status: pending             # 상태: pending → read → in-progress → resolved
created: 2026-02-11         # 작성일
references: []              # 관련 메시지 ID (예: ["S002", "C001"])
---
```

### 메시지 유형 (type)

| type | 설명 | 예시 |
|------|------|------|
| `spec` | 새 기능 스펙 전달 | "파티 시스템 만들었어, 패킷 포맷 이래" |
| `question` | 질문 | "이 필드 바이트 순서가 뭐야?" |
| `answer` | 질문에 대한 답변 | "리틀엔디안이야" |
| `bug` | 버그 리포트 | "로그인 패킷 응답이 안 와" |
| `test-result` | 테스트 결과 보고 | "E2E 테스트 7/10 통과" |
| `task` | 작업 요청/할당 | "로그인 UI 만들어줘" |
| `status` | 진행 상황 보고 | "인벤토리 UI 50% 완료" |
| `change` | API/스펙 변경 통보 | "버프 패킷 포맷 바뀌었어" |
| `agreement` | 합의 요청/확인 | "이 프로토콜로 확정할까?" |

### 상태 전이

```
pending → read → in-progress → resolved
                      │
                      └→ blocked (차단됨 - 사유 명시 필요)
```

- **발신자**가 `pending`으로 생성
- **수신자**가 확인하면 `read`로 변경
- **수신자**가 작업 시작하면 `in-progress`
- **양쪽 합의** 후 `resolved`

---

## 상태 보드 (status_board.json)

양쪽 에이전트의 현재 상태를 실시간 추적합니다:

```json
{
  "last_updated": "2026-02-11T15:30:00",
  "server_agent": {
    "status": "working",
    "current_task": "Party system implementation",
    "last_message_sent": "S003",
    "last_message_read": "C002",
    "session_active": true
  },
  "client_agent": {
    "status": "idle",
    "current_task": null,
    "last_message_sent": null,
    "last_message_read": null,
    "session_active": false
  },
  "pending_messages": {
    "server_to_client": ["S001"],
    "client_to_server": []
  },
  "sprint": {
    "goal": "기본 로그인 + 캐릭터 선택 연동",
    "started": "2026-02-11",
    "tasks_total": 0,
    "tasks_done": 0
  }
}
```

---

## 합의 문서 (agreements/)

양쪽이 합의한 스펙은 `agreements/` 폴더에 JSON으로 저장합니다.
한쪽이 일방적으로 수정하지 않습니다. 변경 시 `change` 타입 메시지로 통보 후 합의.

---

## 운영 규칙

### 1. 메시지 수신 확인
- 새 메시지를 읽으면 **반드시** status를 `read`로 업데이트
- 업데이트 후 즉시 push

### 2. 충돌 방지
- 각자 자기 방향 폴더만 write (`server_to_client/` or `client_to_server/`)
- `status_board.json`은 자기 섹션만 수정
- `agreements/`는 합의 후에만 수정

### 3. 긴급 메시지
- `priority: P0`는 즉시 처리
- P0 메시지 발신 후 status_board에도 "urgent_pending" 표시

### 4. 번호 관리
- 각 방향 독립적으로 순번 증가
- S001, S002, S003... / C001, C002, C003...
- 건너뛰기 없음

### 5. Git 커밋 메시지 규칙
```
comms: [방향] 메시지 요약

예시:
comms: [S→C] S003 파티 시스템 스펙 전달
comms: [C→S] C001 로그인 패킷 질문
comms: [sync] 상태 보드 업데이트
comms: [agree] 패킷 프로토콜 v1 확정
```
