# Codex 첫 프롬프트

> Codex에게 작업을 맡길 때 아래 내용을 복사해서 첫 프롬프트로 보내세요.
> [작업 지시] 부분만 매번 바꾸면 됩니다.

---

## 복사용 프롬프트

```
이 프로젝트는 인간 오케스트레이터 1명 + AI 에이전트 2대(서버/클라이언트)가
협업하여 로스트아크 스타일 MMORPG를 개발하는 프로젝트입니다.

인간은 코드를 직접 쓰지 않고, AI 에이전트가 전부 구현합니다.
너도 이 에이전트 중 하나로 참여합니다.

## 컨텍스트 복원 (반드시 순서대로 읽을 것)

1. `CODEX_ONBOARDING.md` (프로젝트 루트)
   — 프로젝트 구조, AI 에이전트 개발 방법론, 기술 스택 선택 기준, 통신 프로토콜,
     검증 시스템, Code-as-Configuration 패턴 전체 설명

2. `_context/handoff.md`
   — 직전 에이전트(Claude Code)가 남긴 인수인계.
     마지막으로 뭘 했는지, 지금 뭘 해야 하는지, 주의사항

3. `_context/client_state.yaml` (클라이언트 작업 시)
   또는 `_context/server_state.yaml` (서버 작업 시)
   — 전체 진행 상황: 완료 목록, 대기 태스크, 핵심 규칙, 최근 결정사항

4. `CONVENTIONS.md` (프로젝트 루트)
   — 코드 컨벤션 (위반 시 자동 검증에서 FAIL)

## 작업 지시

[여기에 구체적인 작업 내용을 적으세요]

## 작업 후 필수 체크리스트

1. `python validate_all.py --skip-unity` 실행 → 0 FAIL 확인
2. `_context/handoff.md` 업데이트
   — 마지막 작업 에이전트, 시간, 한 작업, 다음 작업, 주의사항
3. `_context/client_state.yaml` 또는 `server_state.yaml` 업데이트
   — completed에 작업 추가, current_status 갱신
4. 서버-클라 간 작업이면 `_comms/` 에 메시지 작성

## 핵심 원칙

- 에이전트는 교체 가능한 부품이고, 시스템이 주인입니다
- 너 이전에 Claude Code가 작업했고, 너 이후에 다른 에이전트가 이어받을 수 있습니다
- 그래서 handoff.md와 state.yaml 업데이트가 코드 작성만큼 중요합니다
- 모든 작업은 검증(validate)을 통과해야만 완료입니다
```

---

## 사용 예시

### 예시 1: 클라이언트 기능 구현

```
[작업 지시 부분을 아래로 교체]

레이드 전용 UI를 구현해줘.
- RaidUI.cs 신규 생성 (Assets/Scripts/UI/)
- RaidManager 이벤트 구독 (OnBossSpawned, OnPhaseChanged, OnMechanicStarted 등)
- ProjectSetup.cs에 UI 패널 추가
- SceneValidator.cs에 검증 항목 추가
- interaction-map.yaml 업데이트
- _context/client_state.yaml의 pending_tasks에서 phase3_raid_ui 참조
```

### 예시 2: 서버 작업

```
[작업 지시 부분을 아래로 교체]

서버 TASK 3 (거래소 시스템)을 구현해줘.
- _context/server_state.yaml의 pending_tasks에서 economy_sub01~06 참조
- MsgType 390-397 핸들러 구현
- tcp_bridge.py 수정 시 _patch_s0XX.py 파일로 패치
- 테스트 작성 후 전체 PASS 확인
```

### 예시 3: 토큰 소진으로 이어받기

```
[작업 지시 부분을 아래로 교체]

이전 에이전트(Claude Code)가 토큰 소진으로 작업 중 중단되었습니다.
_context/handoff.md를 읽고 중단된 작업을 이어서 완료해줘.
```
