# CODEX_ONBOARDING.md — AI 에이전트 개발 시스템 이해 문서

> 이 문서는 OpenAI Codex가 이 프로젝트의 **AI 에이전트 기반 개발 방법론**을 이해하기 위한 온보딩 가이드입니다.
> 게임 콘텐츠가 아니라 **"AI 에이전트가 어떻게 협업하여 게임을 만드는가"**에 초점을 맞춥니다.

---

## 1. 프로젝트 개요

이 프로젝트는 **로스트아크 스타일 MMORPG**를 **인간 오케스트레이터 1명 + AI 에이전트 2대**로 개발하고 있습니다.

```
┌──────────────────────────────────────────────┐
│              인간 (CEO/오케스트레이터)           │
│   역할: 방향 결정, 우선순위, 최종 승인          │
│   도구: Claude Code, OpenAI Codex             │
│   구현: 직접 코딩 안 함 — 순수 오케스트레이션    │
└────────────┬─────────────────┬────────────────┘
             │                 │
     ┌───────▼───────┐ ┌──────▼────────┐
     │ 서버 에이전트   │ │ 클라 에이전트  │
     │ (Claude Code)  │ │ (Claude Code)  │
     │                │ │                │
     │ C++ ECS 서버   │ │ Unity C# 클라  │
     │ Python 브릿지  │ │ 82+ 스크립트   │
     │ GDD 21개 YAML  │ │ 38 매니저      │
     └───────┬────────┘ └───────┬────────┘
             │                  │
             └──── Git 기반 ────┘
              비동기 메시지 교환
```

**핵심 철학**: 인간은 구현에서 완전히 손을 뗐고, AI 에이전트가 코드 작성/검증/통합을 자율적으로 수행합니다. 인간은 "무엇을 만들 것인가"만 결정합니다.

---

## 2. 기술 스택 선택 기준: "AI 에이전트 최적화"

이 프로젝트의 기술 선택은 **인간 편의성이 아닌 AI 에이전트 생산성**을 기준으로 합니다.

### 서버: C++ ECS (Entity Component System)
| 기준 | ECS | 전통 OOP |
|------|-----|---------|
| 구조 | 데이터와 로직 분리 (Component=struct, System=함수) | 상속 계층, 상태 얽힘 |
| AI 적합성 | 규칙이 명확하고 기계적 — AI가 실수할 여지 적음 | 상속 관계 추론 필요 — AI 실수 가능 |
| 인간 러닝커브 | 높음 (패러다임 전환 필요) | 낮음 (직관적) |
| 선택 이유 | **AI가 다루기 쉬움** | 인간이 다루기 쉬움 |

### 클라이언트: Unity (C#)
| 기준 | Unity | Unreal Engine |
|------|-------|---------------|
| 빌드 속도 | 수 초~수 분 | 수십 분 |
| 씬 파일 | YAML (텍스트, AI 읽기 가능) | UASSET (바이너리, AI 불가) |
| 코드로 씬 생성 | ProjectSetup.cs로 완전 가능 | 에디터 의존도 높음 |
| 에러 메시지 | C# — 명확, 1줄 | C++ 템플릿 — 수십 줄 |
| 피드백 루프 | 빠름 (핫리로드) | 느림 |
| 선택 이유 | **AI 반복 작업에 최적** | GUI 의존적 |

### 통신: Git 기반 비동기 메시지
| 기준 | Git 메시지 | 실시간 API |
|------|-----------|-----------|
| AI 호환성 | 마크다운 파일 읽기/쓰기 — AI 네이티브 | API 키/인증/세션 관리 필요 |
| 추적성 | 모든 대화가 Git 히스토리로 보존 | 로그 별도 관리 필요 |
| 비동기 | 자연스러움 (push/pull) | 동기화 복잡성 |

---

## 3. 디렉토리 구조

```
ECS/                              # 프로젝트 루트
├── _gdd/                         # Game Design Document (21 YAML, 9000줄)
│   ├── rules/                    # 권위 있는 게임 설계 규칙
│   │   ├── combat.yaml           # 전투 시스템
│   │   ├── ui.yaml               # UI 레이아웃/좌표/색상 (1438줄)
│   │   ├── art_style.yaml        # 아트 스타일/라이팅/색상 (490줄)
│   │   ├── vfx.yaml              # VFX 정의 (865줄)
│   │   ├── protocol.yaml         # 패킷 프로토콜
│   │   └── ... (21개)
│   └── data/                     # CSV 데이터 (monsters, skills, items, quests, npcs)
│
├── _comms/                       # 에이전트 간 통신 시스템
│   ├── PROTOCOL.md               # 통신 규약
│   ├── server_to_client/         # 서버→클라 메시지 (S001~S044)
│   ├── client_to_server/         # 클라→서버 메시지 (C001~C024)
│   ├── agreements/               # 양측 합의된 스펙 (JSON)
│   ├── conversation_journal.json # Single Source of Truth
│   └── status_board.json         # 양측 현재 상태
│
├── _context/                     # 에이전트 영속 상태
│   ├── server_state.yaml         # 서버 에이전트 세션 간 상태 유지
│   ├── client_state.yaml         # 클라 에이전트 세션 간 상태 유지
│   └── ask_user.yaml             # 인간에게 질문이 필요할 때
│
├── _agent/                       # 에이전트 자동화
│   ├── agent_loop.py             # 자율 실행 루프
│   └── README.md
│
├── Servers/                      # 서버 코드
│   ├── BridgeServer/             # TCP 브릿지 (Python asyncio, 포트 7777)
│   │   ├── tcp_bridge.py         # 메인 브릿지 서버
│   │   ├── test_tcp_bridge.py    # 통합 테스트
│   │   └── _patch_s0XX.py        # 패치 파일들
│   ├── FieldServer/              # 게임 서버 (C++ ECS)
│   ├── GateServer/               # 게이트 서버
│   └── BusServer/                # 메시지 버스
│
├── Components/                   # ECS 컴포넌트 (struct only, 멤버 함수 금지)
├── Systems/                      # ECS 시스템 (ISystem, 상태 금지)
├── Core/                         # 코어 엔진
│
├── UnityClient/GameClient/       # Unity 클라이언트
│   ├── Assets/
│   │   ├── Editor/               # 에디터 스크립트 (씬 생성/검증)
│   │   │   ├── ProjectSetup.cs   # 씬 전체를 코드로 생성 (~1600줄)
│   │   │   ├── EnvironmentSetup.cs # 터레인/환경 프로시저럴 생성
│   │   │   └── SceneValidator.cs # 자동 검증
│   │   ├── Scripts/
│   │   │   ├── Managers/         # 38개 싱글톤 매니저
│   │   │   ├── Entity/           # LocalPlayer, RemotePlayer, MonsterEntity
│   │   │   ├── Network/          # TCP 네트워크 레이어
│   │   │   ├── UI/               # 20+ UI 스크립트
│   │   │   └── interaction-map.yaml # 매니저 의존성 맵 (1400줄)
│   │   └── ...
│   ├── validate_client.py        # 컨벤션 검증
│   ├── unity_build_check.py      # 컴파일 검증
│   └── validate_all.py           # 통합 검증
│
├── CONVENTIONS.md                # 코드 컨벤션 (AI 헌법)
├── interaction-map.yaml          # 루트 레벨 의존성 맵
└── CODEX_ONBOARDING.md           # 이 문서
```

---

## 4. 에이전트 간 통신 프로토콜

### 4.1 기본 구조

서버 에이전트와 클라이언트 에이전트는 **Git을 통해 비동기 메시지**를 교환합니다.

```
서버 에이전트 → _comms/server_to_client/S###_제목.md → git push
클라 에이전트 → git pull → 메시지 읽기 → 작업 → 응답
클라 에이전트 → _comms/client_to_server/C###_제목.md → git push
```

### 4.2 메시지 포맷

```yaml
---
id: S043
from: server-agent
to: client-agent
type: spec          # spec | question | answer | bug | test-result | task | change
priority: P1        # P0(긴급) P1(높음) P2(보통) P3(낮음)
status: pending     # pending → read → in-progress → resolved
created: 2026-02-15
references: ["S042", "C024"]
---

(마크다운 본문 — 스펙, 질문, 결과 등)
```

### 4.3 합의 문서

양측이 합의한 스펙은 `_comms/agreements/` 에 JSON으로 저장합니다.
- `packet_protocol.json` — 확정된 패킷 포맷
- `test_contract.json` — E2E 테스트 계약

한쪽이 일방적으로 수정하지 않습니다. 변경 시 `change` 타입 메시지로 통보 후 합의.

### 4.4 현재까지의 대화량

- 서버→클라: S001 ~ S044 (44개 메시지)
- 클라→서버: C001 ~ C024 (24개 메시지)
- 합의 문서: 패킷 프로토콜, 테스트 계약 등

---

## 5. 영속 상태 시스템

AI 에이전트는 세션이 끊기면 컨텍스트를 잃습니다. 이를 방지하기 위해 **영속 상태 파일**을 운영합니다.

### `_context/server_state.yaml` / `client_state.yaml`

```yaml
agent: client
last_session: "2026-02-15T19:35:00"
current_status: "S043 패킷 포맷 동기화 완료"

completed:          # 완료된 작업 목록 (ID + 설명 + 수정 파일)
  - id: A1
    desc: "TPS→쿼터뷰 카메라 전환"
    files: ["Assets/Scripts/Entity/LocalPlayer.cs"]
  # ... A20까지

blocked: []         # 서버/클라 응답 대기 중인 작업

pending_tasks:      # 다음 할 일 (우선순위 + 차단 여부)
  - id: "gdd_task3_auction_ui"
    priority: P1
    blocked: true
    blocked_reason: "서버 TASK 3 구현 대기"

recent_decisions:   # 최근 중요 결정 (컨텍스트 유지)
  - "카메라 탑다운 쿼터뷰 확정 (CEO 직접 지시)"

processed_messages: # 처리 완료된 메시지 목록
  - "S001" ~ "S044"

rules:              # 매 세션 리마인드할 핵심 규칙
  - "Find/FindObjectOfType 런타임 사용 금지"
  - "작업 후 반드시 validate_all.py 실행"
```

**핵심**: 새 세션이 시작되면 이 파일을 읽어서 이전 세션의 맥락을 즉시 복원합니다.

---

## 6. 자동 검증 시스템

### 6.1 검증 파이프라인

모든 코드 작성/수정 후 반드시 실행하는 검증 루프:

```
코드 작성/수정
    ↓
validate_client.py (컨벤션 검사)
    ↓ FAIL이면 수정 후 재실행
unity_build_check.py (컴파일 검사)
    ↓ FAIL이면 수정 후 재실행
전부 PASS → 작업 완료
```

통합 실행: `python validate_all.py --skip-unity`

### 6.2 검증 규칙 (FAIL = 즉시 수정)

| 규칙 | 검증 방법 |
|------|----------|
| 매니저는 interaction-map.yaml에 등록 | yaml 파싱 → 매니저 파일 교차 체크 |
| 매니저에 싱글톤 패턴 존재 | `public static.*Instance` 패턴 검색 |
| OnDestroy에서 이벤트 해제 | `OnDestroy` 메서드 존재 여부 |
| Network 스크립트는 `namespace Network` | 파일 내 namespace 체크 |
| 런타임에 Find/FindObjectOfType 금지 | 코드 내 패턴 검색 |
| ProjectSetup.cs에 매니저 등록 | 매니저 이름 교차 체크 |
| 컴파일 에러 0개 | Unity 빌드 |

### 6.3 현재 검증 결과

```
━━━ 결과: 83 PASS, 0 FAIL, 17 WARN ━━━
```

---

## 7. Code-as-Configuration 패턴

이 프로젝트의 가장 중요한 패턴입니다. **Unity 에디터의 GUI 작업을 전부 C# 코드로 대체**합니다.

### ProjectSetup.cs (~1600줄)

```
Unity 에디터 메뉴: "ECS Game > Setup All" 또는 "Rebuild GameScene (Force)"
    ↓
ProjectSetup.cs 실행
    ↓
자동 생성되는 것들:
  - Material 2개 (LocalPlayer, RemotePlayer)
  - Prefab 3개 (LocalPlayer, RemotePlayer, Monster)
  - Scene 2개 (GameScene, TestScene)
  - GameScene 내부:
    - 38개 매니저 GameObject (싱글톤 컴포넌트 부착)
    - Canvas + 13개 UI 패널 (HUD, 스킬바, 미니맵, 채팅, 보스HP...)
    - 조명, 포그, 포스트프로세싱
    - 터레인, 환경 오브젝트
  - SerializedObject로 [SerializeField] 참조 자동 바인딩
  - Build Settings 자동 등록
```

**이것이 AI 에이전트에 최적화된 이유**:
- AI는 GUI를 클릭할 수 없지만 코드는 완벽하게 작성 가능
- 씬 전체가 코드로 정의되므로 재현 가능하고 버전 관리됨
- 씬이 깨져도 "Rebuild (Force)" 한 번이면 완전 복구

### interaction-map.yaml (~1400줄)

38개 매니저의 의존성을 YAML로 명시적으로 정의:

```yaml
managers:
  - name: CombatManager
    singleton: true
    fires_events:
      - OnAttackFeedback(AttackResultData)
      - OnEntityDied(CombatDiedData)
    subscribes_to:
      - NetworkManager.OnAttackResult
      - NetworkManager.OnCombatDied
    public_api:
      - SelectTarget(ulong)
      - Attack(ulong)
```

**AI가 이 파일을 읽으면** 매니저 간 관계를 즉시 파악할 수 있습니다. 코드를 하나하나 읽을 필요 없이요.

---

## 8. 에이전트 작업 워크플로우

### 8.1 일반 작업 (기능 구현)

```
1. 인간이 지시 ("스킬바를 12슬롯으로 확장해")
2. AI 에이전트가 관련 파일 탐색
   - interaction-map.yaml로 의존성 파악
   - GDD yaml로 스펙 확인
   - 기존 코드 읽기
3. 코드 작성/수정
4. validate_all.py 실행 → PASS 확인
5. _context/client_state.yaml 업데이트
6. git commit + push
```

### 8.2 서버-클라 협업 작업 (패킷 연동)

```
1. 서버 에이전트가 새 패킷 구현
2. _comms/server_to_client/S0XX_*.md 메시지 작성 → push
3. 클라 에이전트가 pull → 메시지 읽기
4. PacketDefinitions.cs에 MsgType 추가
5. PacketBuilder.cs에 직렬화/역직렬화 추가
6. NetworkManager.cs에 핸들러 + 이벤트 추가
7. Manager + UI 구현
8. ProjectSetup.cs에 매니저 등록
9. SceneValidator.cs에 검증 추가
10. interaction-map.yaml 업데이트
11. validate_all.py 실행 → PASS
12. _comms/client_to_server/C0XX_*.md 응답 → push
```

### 8.3 비주얼/환경 작업

```
1. art_style.yaml / ui.yaml / vfx.yaml에서 스펙 확인
2. ProjectSetup.cs 또는 EnvironmentSetup.cs 수정
3. 서버 변경 불필요 (순수 클라이언트 작업)
4. validate_all.py 실행 → PASS
```

---

## 9. GDD (Game Design Document) 시스템

21개 YAML 파일, 9000줄 이상의 게임 설계 문서가 권위 있는 소스입니다.

### 권위 기준 (크로스파일 충돌 시)

| 데이터 | 권위 파일 |
|--------|---------|
| 키바인딩 | flow.yaml |
| PvP 수치 | pvp.yaml |
| 어그로 | ai_behavior.yaml |
| 콤보 | animation.yaml |
| 아이템 | items.yaml |
| UI 좌표/색상 | ui.yaml |
| 아트 스타일/라이팅 | art_style.yaml |
| VFX | vfx.yaml |

### 데이터 CSV

`_gdd/data/` 에 5개 CSV:
- `monsters.csv` — 몬스터 20종 (ID, 이름, 레벨, HP, ATK, DEF, 드롭)
- `skills.csv` — 스킬 30개 (ID, 이름, 쿨다운, 데미지, 타입)
- `items.csv` — 아이템 50+ (ID, 이름, 등급, 효과)
- `quests.csv` — 퀘스트 25개
- `npcs.csv` — NPC 18명

---

## 10. 핵심 컨벤션 요약

### 서버 (C++ ECS)
- Component = struct, **멤버 함수 금지**
- System = ISystem 상속, **상태(멤버 변수) 금지**
- System 간 직접 호출 금지, 싱글턴 금지
- 모듈 폴더에 MANIFEST.yaml 필수

### 클라이언트 (Unity C#)
- 모든 매니저는 싱글톤 패턴 (Awake에서 Instance 설정)
- 이벤트 기반 통신 (매니저 간 직접 호출 금지)
- Network 네임스페이스: NetworkManager, TCPClient, PacketBuilder, PacketDefinitions
- Find/FindObjectOfType 런타임 사용 금지
- Old Input System API만 사용
- 작업 후 반드시 validate_all.py 실행

### 공통
- interaction-map.yaml 동기화 필수
- 대표님 결정 필요 시 `_context/ask_user.yaml` 사용
- conversation_style: 동료 개발자처럼 자연스럽게

---

## 11. 현재 프로젝트 규모

### 서버
- TCP 브릿지: 80+ 테스트 ALL PASS
- 패킷 타입: MsgType 0 ~ 560 (100+ 핸들러)
- GDD 태스크: TASK 1~18, 80+ 서브태스크

### 클라이언트
- C# 스크립트: 82+
- 싱글톤 매니저: 38개
- UI 스크립트: 20+
- 패킷 핸들러: 100+ (NetworkManager.cs 1907줄)
- 검증: 83 PASS, 0 FAIL

### 통신
- 서버→클라 메시지: 44개
- 클라→서버 메시지: 24개
- 합의 문서: 다수

---

## 12. 이 시스템의 본질

이 프로젝트가 증명하려는 것:

1. **AI 에이전트는 "도구"가 아니라 "동료 개발자"**
   - 서버 에이전트와 클라 에이전트가 독립적으로 코드를 작성하고, 메시지로 협업합니다.
   - 인간은 코드를 한 줄도 쓰지 않습니다.

2. **기술 선택 기준이 "인간 편의성"에서 "AI 생산성"으로 전환**
   - ECS는 인간에게 어렵지만 AI에게 쉬움 → 채택
   - Unity는 코드로 모든 걸 할 수 있음 → 채택
   - Git 메시지는 AI가 자연스럽게 다룸 → 채택

3. **Code-as-Configuration으로 GUI 의존성 제거**
   - ProjectSetup.cs로 씬 전체를 코드로 생성
   - interaction-map.yaml로 아키텍처를 명시적으로 문서화
   - validate_all.py로 자동 검증

4. **영속 상태로 세션 간 컨텍스트 유지**
   - state.yaml로 "어디까지 했는지" 기억
   - conversation_journal.json으로 대화 히스토리 보존

---

## 13. Codex가 이 프로젝트에 참여할 때

### 반드시 먼저 읽어야 할 파일

1. `_context/client_state.yaml` 또는 `_context/server_state.yaml` — 현재 상태
2. `CONVENTIONS.md` — 코드 규칙
3. `_comms/PROTOCOL.md` — 통신 규약
4. 작업 대상의 `interaction-map.yaml` — 의존성 파악

### 작업 후 반드시 해야 할 것

1. `python validate_all.py --skip-unity` 실행 → 0 FAIL 확인
2. `_context/*_state.yaml` 업데이트 (completed, pending_tasks, current_status)
3. 서버/클라 간 작업이면 `_comms/` 에 메시지 작성

### 절대 하면 안 되는 것

- interaction-map.yaml 업데이트 없이 매니저 추가
- validate 실행 없이 작업 완료 선언
- 상대 에이전트의 통신 폴더에 파일 작성 (서버는 server_to_client만, 클라는 client_to_server만)
- `_context/state.yaml` 업데이트 없이 세션 종료
