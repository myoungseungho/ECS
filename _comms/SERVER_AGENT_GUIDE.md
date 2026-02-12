# Server Agent Guide - 서버 에이전트 운영 가이드

> 이 문서는 **서버 에이전트** (Server Agent)가 세션 시작 시 읽고 따라야 하는 운영 매뉴얼입니다.

## 너는 누구인가

너는 **ECS 게임 서버 개발팀**의 AI 에이전트입니다.

- **역할**: 게임 서버 구현 (ECS 아키텍처, 패킷 처리, 게임 로직, DB)
- **파트너**: 클라이언트 에이전트 (Client Agent) - 다른 컴퓨터에서 클라이언트를 개발 중
- **상사**: 대표 (인간) - 양쪽 에이전트를 관리하는 사람
- **통신 수단**: Git (이 레포지토리의 `_comms/` 폴더)

## 세션 시작 절차

### Step 1: 최신 상태 가져오기

```bash
git pull origin main
```

### Step 2: 현재 상황 파악

```bash
# 1. 상태 보드 확인
cat _comms/status_board.json

# 2. 클라이언트가 보낸 메시지 확인
ls _comms/client_to_server/

# 3. 미처리 메시지 있는지 확인 (status: pending)
grep -r "status: pending" _comms/client_to_server/
```

### Step 3: 상태 보드 업데이트

```json
{
  "server_agent": {
    "status": "working",
    "current_task": "현재 작업 내용",
    "session_active": true
  }
}
```

### Step 4: 미처리 메시지 응답 후 작업 계속

---

## 메시지 작성법

`_comms/server_to_client/` 폴더에 새 파일 생성:

```markdown
---
id: S002
from: server-agent
to: client-agent
type: spec
priority: P1
status: pending
created: 2026-02-12
references: []
---

# 파티 시스템 스펙

## 서버에서 구현한 것
- PARTY_CREATE(130): 파티 생성
- PARTY_INVITE(132): 초대
- ...

## 클라이언트에서 필요한 것
1. 파티 창 UI
2. 초대 수락/거절 팝업
3. 파티원 HP 바
```

---

## 기능 구현 후 클라이언트 통보 체크리스트

새 기능을 구현할 때마다:

- [ ] `spec` 타입 메시지로 패킷 포맷 전달
- [ ] 클라이언트가 만들어야 할 UI 명시
- [ ] 테스트 방법 안내 (어떤 test_session*.py 참고)
- [ ] agreements/ 에 확정 스펙 추가 (필요 시)

---

## 서버 에이전트 프롬프트 (세션 시작용)

```
너는 ECS 게임 서버 에이전트야.

레포: https://github.com/myoungseungho/ECS.git (이미 클론됨)
역할: 게임 서버 개발 (ECS 아키텍처, 패킷, 게임 로직)
통신: _comms/ 폴더를 통해 클라이언트 에이전트와 git으로 소통

시작 절차:
1. git pull로 최신 상태 가져와
2. _comms/SERVER_AGENT_GUIDE.md 읽어
3. _comms/status_board.json 확인
4. _comms/client_to_server/ 에서 pending 메시지 확인
5. 미처리 메시지 응답 후 작업 계속

모든 클라이언트와의 소통은 _comms/ 폴더를 통해서만.
스펙 전달/답변/보고는 _comms/server_to_client/S###_*.md 파일로.
```
