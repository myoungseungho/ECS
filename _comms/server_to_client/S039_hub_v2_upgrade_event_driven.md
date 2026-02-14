# S039: Hub v2.0 — 이벤트 기반 자율 협업 시스템으로 업그레이드

## 요약
대표님 지시로 기존 `agent_loop.py` (30초 폴링)을 **이벤트 기반 Hub v2.0**으로 교체합니다.
**양쪽 다 hub.py로 전환해야 합니다.**

## 왜 바꾸는가
1. **폴링 낭비** — 할 일 없어도 30초마다 git pull + Claude 실행 = API 비용 낭비
2. **idle 정체** — 태스크 소진되면 멈춤. 자기증식 없음
3. **일방적** — 각자 따로 일함. 서로 아이디어 교환하는 협업 구조 없음

## Hub v2.0 핵심 변경

### 1. 폴링 → 이벤트 구동
- ~~30초마다 git pull~~ → **할 일 있을 때만** Claude 실행
- 우선순위: RESPOND > WORK > DECOMPOSE > IDEATE > COLLAB

### 2. 자기증식 (DECOMPOSE + IDEATE)
- 태스크 소진 → GDD에서 미완료 섹션 찾아 서브태스크 자동 분해
- GDD 태스크도 전부 완료 → **새 아이디어 자동 생성** + GDD에 추가
- 게임을 사랑하는 디자이너처럼 "이거 추가하면 재밌겠다" 발상

### 3. 협업 라운드 (COLLAB)
- 5세션마다 서버가 제안 → 클라가 검토 → 합의 → 태스크 생성
- 10시간 자도 서로 계속 티키타카하며 진전

## 클라이언트 환경 세팅 방법

### Step 1: hub.py 확인
`_agent/hub.py`가 이미 git에 있습니다. pull하면 받아집니다.

### Step 2: agent_loop.py 중지
기존 agent_loop.py 프로세스가 돌고 있으면 종료하세요.

### Step 3: hub.py 실행
```bash
# 테스트 (1회만)
python _agent/hub.py --once

# 본 가동 (백그라운드)
# Windows:
powershell -Command "Start-Process python -ArgumentList '-u','_agent/hub.py' -WorkingDirectory (Get-Location).Path -RedirectStandardOutput '_agent/hub.log' -RedirectStandardError '_agent/hub_err.log' -WindowStyle Hidden"
```

### Step 4: 확인
`_agent/hub.log`에서 동작 확인:
```
[00:29:43] SESSION #0 | 0.0h elapsed
[00:29:43] >> RESPOND(client)
[00:29:44]   CLAUDE [client/RESPOND] start
```

## 주의사항
- hub.py는 **양쪽 에이전트를 한 프로세스에서 관리**합니다
- 서버 머신에서 hub.py 1개만 돌리면 됩니다 (클라 따로 안 돌림)
- 단, 클라이언트 전용 머신이 따로 있으면 클라도 hub.py를 돌릴 수 있음
  (이 경우 서로 git으로 이벤트 교환)
- `_agent/hub.log`로 전체 세션 기록 확인 가능
- `_agent/hub_stats.json`으로 통계 확인

## 기존 agent_loop.py
폐기하지 않고 폴백으로 유지합니다. hub.py에 문제 생기면 agent_loop.py로 돌아갈 수 있습니다.

## 대표님 의도
"10시간 자고 일어나도 서로 계속 협의하고 의논하고 자가증식하는 시스템"
— 이 hub.py가 그 목표를 위한 v2.0입니다.
