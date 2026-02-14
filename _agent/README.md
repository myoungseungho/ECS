# Agent Autonomous Loop System

## Overview

Client/Server 에이전트가 각자 컴퓨터에서 독립적으로 작업하고,
**git push/pull**을 통해 메시지를 교환하는 자율 시스템.

```
[Client PC]                    [GitHub]                    [Server PC]
agent_loop.py --role client  ←→  repo  ←→  agent_loop.py --role server
     ↓                                           ↓
 Claude CLI                                  Claude CLI
     ↓                                           ↓
 _comms/client_to_server/  ────push────→  inbox로 감지
 inbox로 감지  ←────push────  _comms/server_to_client/
```

## Architecture

### Context Preservation (핵심)

매 Claude 실행 시 **반드시** 다음 파일을 프롬프트에 강제 주입:

1. `_context/{role}_state.yaml` — 영속 상태 (이전 세션의 모든 기억)
2. `{role}/CLAUDE.md` — 프로젝트 코딩 규칙
3. `_gdd/README.md` — GDD 시스템 개요
4. 새 메시지 파일 전문

**컨텍스트가 절대 유실되지 않도록** state 파일을 매 세션 종료 시 업데이트.

### Message Bus

```
_comms/
  client_to_server/   ← 클라이언트가 쓰고, 서버가 읽음
    C016_gdd_review.md
    C017_camera_update.md
  server_to_client/   ← 서버가 쓰고, 클라이언트가 읽음
    S028_login_fix.md
    S030_gdd_complete.md
```

- 파일명 규칙: `{PREFIX}{번호}_{설명}.md`
- Client prefix: `C`, Server prefix: `S`
- 번호는 순차 증가

### State File (`_context/{role}_state.yaml`)

```yaml
agent: client  # or server
last_session: "2026-02-14T19:30:00"
current_status: "한 줄 상태 요약"

completed:
  - id: A1
    desc: "완료한 작업 설명"
    files: ["변경한 파일 목록"]

blocked:
  - reason: "블록 사유"
    waiting_for: "무엇을 기다리는지"

pending_tasks:
  - id: "task_id"
    desc: "할 일 설명"
    priority: P1  # P0(긴급) P1(높음) P2(보통) P3(낮음)
    blocked: false
    blocked_reason: ""  # blocked: true일 때만

recent_decisions:
  - "중요 결정 기록"

processed_messages:
  - "S028"
  - "S029"

rules:
  - "매 세션 리마인드할 핵심 규칙"
```

### Ask User (`_context/ask_user.yaml`)

대표님의 결정이 필요할 때 사용:

```yaml
questions:
  - id: Q001
    from: client
    timestamp: "2026-02-14T20:00:00"
    question: "카메라 방향을 TPS 숄더캠으로 유지할까요, 쿼터뷰로 변경할까요?"
    options:
      - "TPS 숄더캠 유지"
      - "쿼터뷰 변경"
    status: pending  # pending → answered
    answer: ""
    answered_at: ""
```

## Setup Guide

### Prerequisites

- Python 3.8+
- Git (CLI)
- Claude CLI (`claude` command available in PATH)
  - Install: `npm install -g @anthropic-ai/claude-code`
  - Or: https://docs.anthropic.com/claude-code

### Client Setup (Windows)

```powershell
# 1. 프로젝트 루트에서 실행
cd C:\Users\명승호\Desktop\ECS

# 2. 한 번만 실행 (테스트)
python _agent/agent_loop.py --role client --once

# 3. 데몬 모드 (백그라운드 상시 실행)
python _agent/agent_loop.py --role client

# 4. 백그라운드로 실행 (터미널 닫아도 유지)
start /B python _agent/agent_loop.py --role client > _agent/daemon.log 2>&1
```

### Server Setup (Linux/Mac/Windows)

```bash
# 1. repo clone
git clone <repo-url>
cd ECS

# 2. _context/server_state.yaml 생성 (아래 템플릿 참고)
# 이미 _context/server_state_template.yaml이 있으면 복사:
cp _context/server_state_template.yaml _context/server_state.yaml

# 3. 한 번만 실행 (테스트)
python _agent/agent_loop.py --role server --once

# 4. 데몬 모드
python _agent/agent_loop.py --role server

# 5. 백그라운드 (Linux/Mac)
nohup python _agent/agent_loop.py --role server > _agent/daemon.log 2>&1 &
```

## Configuration

`agent_loop.py` 상단 상수:

| 상수 | 기본값 | 설명 |
|------|--------|------|
| `POLL_INTERVAL` | 30 | git pull 주기 (초) |
| `IDLE_WORK_INTERVAL` | 300 | 메시지 없어도 자체 작업 진행 주기 (초) |
| `MAX_CLAUDE_TIMEOUT` | 900 | Claude 실행 최대 시간 (초, 15분) |

Role별 설정 (`ROLES` dict):

| 키 | Client | Server |
|----|--------|--------|
| `inbox` | `_comms/server_to_client` | `_comms/client_to_server` |
| `outbox` | `_comms/client_to_server` | `_comms/server_to_client` |
| `state_file` | `_context/client_state.yaml` | `_context/server_state.yaml` |
| `claude_md` | `UnityClient/GameClient/CLAUDE.md` | `Servers/CLAUDE.md` |

## How It Works (Loop Detail)

```
1. git pull --rebase
   └─ 충돌 시 rebase abort → 일반 pull 재시도

2. inbox 스캔 → processed_messages와 비교 → 새 메시지 찾기

3. 새 메시지 있으면 (또는 IDLE_WORK_INTERVAL 경과 시):
   └─ 프롬프트 생성 (컨텍스트 파일 강제 읽기 지시 포함)
   └─ claude -p <prompt> --allowedTools Read,Write,Edit,Bash,Glob,Grep,Task
   └─ Claude가 작업 수행 + state 파일 업데이트

4. Claude 성공 시:
   └─ git add -A → commit → push
   └─ 실패 시 pull 후 재시도

5. _context/ask_user.yaml 체크 → 유저 결정 필요 시 알림

6. POLL_INTERVAL 대기 → 1로 돌아감
```

## Logs

- `_agent/last_run.log` — 마지막 Claude 실행 결과 (stdout/stderr/exit code/duration)
- `_agent/daemon.log` — 데몬 모드 실행 시 전체 루프 로그 (start 명령 사용 시)

## Troubleshooting

| 증상 | 원인 | 해결 |
|------|------|------|
| `claude CLI를 찾을 수 없습니다` | Claude CLI 미설치 | `npm install -g @anthropic-ai/claude-code` |
| `git pull 실패` 반복 | 충돌 미해결 | 수동으로 `git status` 확인 후 충돌 해결 |
| Claude 타임아웃 (900초) | 작업이 너무 큼 | state에서 pending_tasks를 더 작게 분할 |
| 메시지 중복 처리 | state 파일 미업데이트 | `processed_messages`에 ID 추가 확인 |
| 컨텍스트 유실 | state 파일 손상 | 마지막 정상 커밋에서 state 파일 복원 |
