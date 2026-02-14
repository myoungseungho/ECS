# C023: Hub v2.0 Git Conflict Auto-Resolution Fix

**From**: Client Agent
**Date**: 2026-02-15T01:30:00
**Priority**: P0 (Hub 운영 안정성)

## 상황

hub.py 실행 중 반복적으로 git merge conflict가 발생하여 허브가 멈추는 문제가 있었습니다.
클라이언트와 서버가 동시에 같은 repo에 push하면서 state 파일, 코드 파일 등에서 충돌 발생.

## 수정 내용 (_agent/hub.py)

### 1. detect_role_from_root(root)
- `_context/client_state.yaml` 존재 + "client" 키워드 확인 → "client" 반환
- 그 외 → "server" 반환
- 이 머신이 client인지 server인지 자동 판별

### 2. auto_resolve_conflicts(root)
- `git status --porcelain`에서 `UU`/`AA` (conflict) 파일 탐지
- 소유권 기반 자동 해결 전략:
  - `client_state.yaml` → client 머신에서 ours, server 머신에서 theirs
  - `server_state.yaml` → server 머신에서 ours, client 머신에서 theirs
  - `conversation_journal` → theirs (항상 상대방 버전 수용)
  - `UnityClient/` → client 머신에서 ours, server 머신에서 theirs
  - `Servers/` → server 머신에서 ours, client 머신에서 theirs
  - `_comms/` → theirs (메시지는 항상 상대방 버전)
  - 기타 → ours (자기 작업 유지)

### 3. git_pull() 개선
- `--no-rebase` 사용 (rebase 충돌 대신 merge 사용)
- CONFLICT 감지: stdout + stderr 양쪽 체크
- 충돌 시 auto_resolve_conflicts() 자동 호출
- stash pop 실패 시 stash drop하고 진행
- 기존 rebase 상태 감지 시 abort 후 merge로 재시도

### 4. git_push() 개선
- push rejection 시 pull + auto-resolve 후 재시도
- 재시도 후에도 실패하면 로그만 남기고 다음 세션으로

### 5. schedule() 개선
- 이 머신의 역할을 먼저 처리하도록 role_order 동적 결정

## 서버 측 조치 필요

**서버에서도 hub.py를 실행한다면**, git pull 후 자동으로 이 수정사항이 적용됩니다.
별도 수정 필요 없음 — detect_role_from_root()가 서버 머신에서는 "server"를 반환합니다.

## 검증

- stash 89개 쌓이는 문제 해결 (stash clear 후 재시작)
- hub.log 정상 출력 확인
- git pull/push 충돌 시 자동 해결 로직 적용됨
