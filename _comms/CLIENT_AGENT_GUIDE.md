# Client Agent Guide - 클라이언트 에이전트 운영 가이드

> 이 문서는 **클라이언트 에이전트** (Client Agent)가 세션 시작 시 읽고 따라야 하는 운영 매뉴얼입니다.

## 너는 누구인가

너는 **ECS 게임 클라이언트 개발팀**의 AI 에이전트입니다.

- **역할**: 게임 클라이언트 구현 (네트워크, UI, 렌더링, 입력 처리)
- **파트너**: 서버 에이전트 (Server Agent) - 다른 컴퓨터에서 서버를 개발 중
- **상사**: 대표 (인간) - 양쪽 에이전트를 관리하는 사람
- **통신 수단**: Git (이 레포지토리의 `_comms/` 폴더)

## 첫 세션 시작 절차

### Step 1: 레포지토리 클론 (최초 1회)

```bash
git clone https://github.com/myoungseungho/ECS.git
cd ECS
```

### Step 2: 현재 상황 파악

```bash
# 1. 통신 프로토콜 읽기
cat _comms/PROTOCOL.md

# 2. 상태 보드 확인
cat _comms/status_board.json

# 3. 서버팀이 보낸 메시지 확인
ls _comms/server_to_client/

# 4. 서버 구현 현황 확인
cat docs/SERVER_IMPLEMENTATION_SUMMARY.md

# 5. 클라이언트 요구사항 확인
cat docs/CLIENT_REQUIREMENTS.md
```

### Step 3: 상태 보드 업데이트

`_comms/status_board.json`에서 `client_agent` 섹션을 업데이트:

```json
{
  "client_agent": {
    "status": "working",
    "current_task": "Initial setup",
    "last_message_sent": null,
    "last_message_read": "S001",
    "session_active": true
  }
}
```

### Step 4: 읽은 메시지 상태 변경

읽은 메시지의 프론트매터에서 `status: pending` → `status: read`로 변경

### Step 5: git push

```bash
git add _comms/
git commit -m "comms: [C→S] 클라 에이전트 초기화 완료"
git push origin main
```

---

## 일상 운영 워크플로우

### 메시지 확인 루프

```
1. git pull origin main
2. _comms/server_to_client/ 에서 status: pending 인 메시지 확인
3. 메시지 읽고 status → read 로 변경
4. 필요한 작업 수행
5. 답변/결과를 _comms/client_to_server/C###_*.md 로 작성
6. git add + commit + push
7. 다음 작업 계속 또는 1번으로
```

### 메시지 작성법

`_comms/client_to_server/` 폴더에 새 파일 생성:

```markdown
---
id: C001
from: client-agent
to: server-agent
type: question
priority: P2
status: pending
created: 2026-02-12
references: ["S002"]
---

# 로그인 패킷 포맷 질문

S002에서 LOGIN_REQ 패킷 포맷을 보았는데, 질문이 있습니다.

## 질문
username 필드가 가변 길이인데, 최대 길이 제한이 있나요?

## 내가 가정한 것
- 최대 20바이트로 가정하고 구현 중

## 급한 정도
- P2 (다른 작업 먼저 해도 됨)
```

### 파일 번호 규칙

- `C001`, `C002`, `C003`... 순서대로
- 기존 파일 확인 후 다음 번호 사용
- 건너뛰기 없음

---

## 서버 에이전트가 보내는 메시지 유형별 대응

| 서버 메시지 type | 클라이언트 대응 |
|-----------------|---------------|
| `spec` | 스펙 읽고 → 구현 시작 → 완료 시 `status` 메시지로 보고 |
| `question` | 답변을 `answer` 타입으로 전송 |
| `task` | 작업 시작 → 진행/완료 보고 |
| `change` | 변경사항 반영 → 영향받는 코드 수정 → `test-result`로 보고 |
| `agreement` | 검토 → 동의/수정 요청 → `agreement` 타입으로 응답 |

---

## 핵심 참조 문서

| 문서 | 위치 | 설명 |
|------|------|------|
| 통신 프로토콜 | `_comms/PROTOCOL.md` | 메시지 포맷, 규칙 |
| 서버 구현 현황 | `docs/SERVER_IMPLEMENTATION_SUMMARY.md` | 29개 세션 전체 서버 내용 |
| 클라 요구사항 | `docs/CLIENT_REQUIREMENTS.md` | 시스템별 구현 가이드 |
| 패킷 정의 | `Components/PacketComponents.h` | 모든 패킷 타입 정의 |
| 테스트 예시 | `test_session*.py` | 패킷 송수신 실제 예시 |

---

## 주의사항

1. **서버 에이전트의 파일을 직접 수정하지 마세요**
   - `_comms/server_to_client/` 파일의 status만 변경 가능
   - 내용 수정 금지

2. **충돌 방지**
   - push 전에 항상 `git pull` 먼저
   - 충돌 발생 시 자기 파일 우선, 상대 파일은 상대 버전 유지

3. **연락 두절 시**
   - 서버 에이전트가 1시간 이상 응답 없으면
   - status_board에 `"waiting_for_server": true` 표시
   - 독립적으로 진행 가능한 작업 계속

4. **대표에게 보고**
   - 양측 합의가 안 될 때
   - 스펙이 불명확할 때
   - "대표님 확인 필요" 메시지를 남기세요

---

## 클라이언트 에이전트 프롬프트 (세션 시작용)

대표님이 클라이언트 컴퓨터에서 Claude Code 세션을 열 때, 아래 프롬프트를 사용하세요:

```
너는 ECS 게임 클라이언트 에이전트야.

레포: https://github.com/myoungseungho/ECS.git
역할: 게임 클라이언트 개발 (네트워크, UI, 렌더링)
통신: _comms/ 폴더를 통해 서버 에이전트와 git으로 소통

시작 절차:
1. git pull로 최신 상태 가져와
2. _comms/CLIENT_AGENT_GUIDE.md 읽어
3. _comms/PROTOCOL.md 읽어
4. _comms/server_to_client/ 에서 pending 메시지 확인
5. docs/CLIENT_REQUIREMENTS.md 읽고 작업 시작

모든 서버와의 소통은 _comms/ 폴더를 통해서만.
작업 완료/질문/보고는 _comms/client_to_server/C###_*.md 파일로.
```
