# PROJECT OVERVIEW - GameServerSkeleton

> **이 문서의 목적**: 에이전트(서버/클라이언트)가 새 세션에서 컨텍스트를 빠르게 복구하기 위한 **단일 진입점 문서**.
> 이 문서만 읽으면 프로젝트 전체 구조를 파악할 수 있고, 각 영역의 상세 내용은 링크된 문서를 참조.

---

## 1. 프로젝트 개요

**GameServerSkeleton**은 ECS 기반 MMORPG 개발 프로젝트.
C++ 게임 서버 + Unity 클라이언트를 **두 AI 에이전트**가 자율적으로 협업 개발한다.

| 항목 | 내용 |
|------|------|
| 장르 | MMORPG (로스트아크 스타일, 쿼터뷰 탑다운) |
| 서버 | C++ ECS (Entity-Component-System) |
| 클라이언트 | Unity C# (MonoBehaviour 싱글톤) |
| 에이전트 | 서버 에이전트 + 클라이언트 에이전트 (Hub 2.0이 조율) |
| 통신 | Git 기반 비동기 메시지 (`_comms/` 마크다운 파일) |
| 설계 문서 | GDD (Game Design Document) - AI가 파싱 가능한 YAML 형식 |

---

## 2. 현재 상태 (2026-02-15 기준)

### 마일스톤: GDD 17개 TASK 100% 완료

| 측정 항목 | 서버 | 클라이언트 |
|-----------|------|-----------|
| 테스트 | 142 PASS (100%) | 115 PASS (100%) |
| 핸들러/매니저 | 87 핸들러 | 40 매니저 + 30 UI |
| MsgType | 560개 (0~560) | 131 패킷 연동 |
| 상태 | 완료 | 완료 |

### 대기 중인 결정 (Q002)

`_context/ask_user.yaml`의 Q002가 **pending** 상태.
대표님이 다음 방향을 결정해야 다음 단계 진행 가능:

- **A**: Unity Play 모드 통합 테스트 (서버 최우선 추천)
- **B**: 코드 리팩토링 (NetworkManager 분할)
- **C**: 밸런싱 패스
- **D**: 추가 컨텐츠 (하우징, 낚시 등)
- **E**: 레이드 UI
- **F**: 엔티티 파이프라인 리뷰

---

## 3. 디렉토리 구조

```
GameServerSkeleton/
│
├── PROJECT_OVERVIEW.md          ← 이 문서 (종합 진입점)
├── CONVENTIONS.md               ← 코드 컨벤션 (ECS 규칙)
│
├── Servers/                     ← C++ ECS 서버
│   ├── CLAUDE.md                  서버 에이전트 가이드
│   ├── FieldServer/               게임 서버 (핵심)
│   ├── BridgeServer/              Python TCP 브릿지 (port 7777)
│   ├── BusServer/                 메시지 버스
│   └── GateServer/                게이트웨이
│
├── UnityClient/                 ← Unity 클라이언트
│   └── GameClient/
│       ├── CLAUDE.md              클라이언트 에이전트 가이드
│       └── Assets/Scripts/        C# 스크립트
│
├── Components/                  ← ECS 컴포넌트 (struct only)
├── Systems/                     ← ECS 시스템 (ISystem 상속)
├── Core/                        ← 코어 엔진
├── NetworkEngine/               ← 네트워크 인프라
│
├── _gdd/                        ← 게임 설계 문서 (YAML)
│   ├── README.md                  GDD 시스템 설명
│   ├── game_design.yaml           마스터 설계서 (54KB)
│   ├── rules/                     게임 규칙 (21개 YAML)
│   └── data/                      게임 데이터 (CSV/YAML)
│
├── _comms/                      ← 에이전트 간 통신
│   ├── PROTOCOL.md                통신 프로토콜 명세
│   ├── conversation_journal.json  대화 이력 (81KB)
│   ├── server_to_client/          S001~S058
│   ├── client_to_server/          C001~C038
│   └── agreements/                합의된 스펙
│
├── _context/                    ← 에이전트 상태
│   ├── server_state.yaml          서버 에이전트 영속 상태 (27KB)
│   ├── client_state.yaml          클라이언트 에이전트 영속 상태 (29KB)
│   └── ask_user.yaml              사용자 질의 (Q001 answered, Q002 pending)
│
├── _agent/                      ← AI 허브 시스템
│   ├── hub.py                     Hub 2.0 (이벤트 드리븐 오케스트레이터)
│   ├── agent_loop.py              에이전트 자율 루프
│   ├── hub.log                    실행 로그
│   └── README.md                  에이전트 시스템 문서
│
├── DummyClient/                 ← 테스트용 더미 클라이언트
└── data/                        ← 런타임 게임 데이터
```

---

## 4. 핵심 아키텍처

### 4.1 듀얼 에이전트 시스템

```
┌──────────────┐     Git push/pull      ┌──────────────┐
│ Server Agent │ ◀──── _comms/ ────▶    │ Client Agent │
│ (C++ ECS)    │     마크다운 메시지      │ (Unity C#)   │
└──────┬───────┘                        └──────┬───────┘
       │                                       │
       │            ┌──────────┐               │
       └────────────│ Hub 2.0  │───────────────┘
                    │ (hub.py) │
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │ ask_user │ ← 대표님 결정 필요 시
                    │  .yaml   │
                    └──────────┘
```

**Hub 2.0 동작 모드:**

| 모드 | 트리거 | 동작 |
|------|--------|------|
| RESPOND | 새 메시지 수신 | 즉시 응답 |
| WORK | pending task 존재 | 작업 실행 |
| DECOMPOSE | task 부족 + GDD 미완 | GDD 분해 → 신규 task |
| IDEATE | GDD 100% 완료 | 새 아이디어 생성 |
| COLLAB | 5세션마다 | 서버↔클라 협업 라운드 |

### 4.2 서버 아키텍처 (C++ ECS)

**엄격한 규칙** (`validate_project.py`가 강제):
- **Component** = `struct` only (멤버 함수 금지, 생성자/소멸자만 허용)
- **System** = `ISystem` 상속, 무상태 (멤버 변수 금지)
- 싱글톤 금지, 시스템 간 직접 호출 금지
- 메시지 기반 통신 (DSM_*, DCM_*, CM_*)

**TCP 브릿지** (`BridgeServer/tcp_bridge.py`):
- Python asyncio, 포트 7777
- Unity ↔ C++ ECS 연결
- 패킷 포맷: `[4B 길이][2B MsgType][Payload]`

### 4.3 클라이언트 아키텍처 (Unity)

- **싱글톤 매니저** 패턴 (40개)
- `NetworkManager` (DontDestroyOnLoad) - TCP + 패킷 디스패치
- `GameManager` (DontDestroyOnLoad) - 상태 머신 (Login→CharSelect→InGame)
- 나머지 매니저는 Scene-bound (씬 전환 시 정리)
- 이벤트 드리븐 통신 (`NetworkManager` → `event Action<>`)
- Old Input System 사용

---

## 5. 프로토콜 (패킷)

### 패킷 형식

```
[4바이트 길이 (Little Endian)][2바이트 MsgType (Little Endian)][Payload]
```

### MsgType 범위

| 범위 | 카테고리 | 예시 |
|------|---------|------|
| 0-199 | 코어 (로그인, 이동, 채팅) | CM_LOGIN, SM_MOVE |
| 200-289 | 전투/파티/인벤토리 | CM_ATTACK, SM_PARTY_INFO |
| 290-318 | 길드/거래/우편 | CM_GUILD_CREATE |
| 320-560 | GDD Tasks (17개) | 캐릭터~멘토 시스템 |

**총 560개 MsgType 정의 완료.**

---

## 6. GDD (게임 설계 문서) 시스템

AI가 파싱 가능한 YAML 기반 설계 문서.

### 구성

| 폴더/파일 | 내용 | 개수 |
|-----------|------|------|
| `game_design.yaml` | 마스터 설계서 (Phase, Scene, Task 정의) | 1 (54KB) |
| `rules/*.yaml` | 게임 규칙 (전투, 경제, 진행 등) | 21개 |
| `data/*.csv` | 게임 데이터 (몬스터, 스킬, 아이템 등) | 6개 |

### 완료된 17개 주요 TASK

| Phase | TASK | 내용 |
|-------|------|------|
| P0-P1 | 기반 | 로그인, 캐릭터 CRUD, 튜토리얼, NPC, 강화 |
| P2-P3 | 핵심 | 필드몬스터, 던전매칭, PvP아레나, 레이드 |
| T2-T3 | 제작/경매 | 제작/채집/요리/마법부여, 경매장 |
| T4-T5 | 퀘스트/소셜 | 일일/주간퀘, 친구, 파티파인더 |
| T6-T10 | 심화 | 전장, 칭호, 보석, 내구도, 보조화폐 |
| T11-T14 | 폴리시 | 캐시샵, 날씨, 출석, 스토리 |
| T15-T18 | 엔드게임 | 비급, 현상금, 비경탐험, 사제 |

**상세**: `_gdd/README.md`

---

## 7. 에이전트 통신

### 통신 방식

Git push/pull로 `_comms/` 폴더의 마크다운 파일을 교환.

```
server_to_client/S###_*.md   (서버 → 클라이언트)
client_to_server/C###_*.md   (클라이언트 → 서버)
agreements/*.json             (양측 합의 스펙)
```

### 메시지 종류

`spec`, `question`, `answer`, `bug`, `test-result`, `task`, `status`, `change`, `agreement`

### 현재 메시지 현황

- S001~S058 (서버 발신 58건)
- C001~C038 (클라이언트 발신 38건)
- 마지막 교환: S058/C039 — GDD 100% 축하 + 다음 단계 논의

**상세**: `_comms/PROTOCOL.md`

---

## 8. 상태 관리

### 영속 상태 파일

| 파일 | 역할 | 크기 |
|------|------|------|
| `_context/server_state.yaml` | 서버 에이전트의 완료 작업, pending task, 처리된 메시지 | 27KB |
| `_context/client_state.yaml` | 클라이언트 에이전트의 완료 작업, pending task, 처리된 메시지 | 29KB |
| `_context/ask_user.yaml` | 사용자 결정 요청 (Q001 answered, Q002 pending) | 2KB |

### 에이전트 컨텍스트 복구 절차

새 세션에서 에이전트가 복구할 때:

1. **이 문서** (`PROJECT_OVERVIEW.md`) 읽기 → 전체 구조 파악
2. **자신의 state 파일** 읽기 → 어디까지 했는지 확인
3. **ask_user.yaml** 읽기 → pending 질문이 있으면 대기
4. **최신 _comms/** 확인 → 미처리 메시지 있으면 RESPOND
5. 필요 시 **역할별 CLAUDE.md** 읽기 → 상세 규칙 확인

---

## 9. 핵심 규칙 & 결정 사항

### 디자인 결정

| ID | 결정 | 근거 |
|----|------|------|
| D009 | 카메라: 쿼터뷰 탑다운 (로스트아크) | 대표님 직접 지시 (TPS 아님) |
| D010 | GDD 파일 간 권한: 전문 파일 우선 | flow.yaml=키바인드, pvp.yaml=PvP 스탯 |
| D012 | 서버 코드 수정은 `_patch.py` 방식 | OneDrive 동기화가 Edit 도구 변경 되돌림 |
| D015 | 브레인스톰 → 4개 신규 시스템 추가 | 비급, 현상금, 비경, 사제 |

### 코드 컨벤션 (CONVENTIONS.md)

- Component = struct, 멤버함수 없음
- System = ISystem 상속, 상태 없음
- MANIFEST.yaml 필수 (모든 모듈)
- 싱글톤 사용 금지 (서버)

### 테스트

- 서버: Python TCP 테스트 142개
- 클라: Python 검증 115개 + Unity validate 스크립트
- 전체 통과율: 100%

---

## 10. 문서 맵 (Deep Dive 링크)

| 알고 싶은 것 | 읽을 문서 |
|-------------|----------|
| **전체 구조 (이 문서)** | `PROJECT_OVERVIEW.md` |
| **코드 컨벤션** | `CONVENTIONS.md` |
| **서버 개발 규칙** | `Servers/CLAUDE.md` |
| **클라이언트 개발 규칙** | `UnityClient/GameClient/CLAUDE.md` |
| **GDD 시스템** | `_gdd/README.md` |
| **에이전트 통신 프로토콜** | `_comms/PROTOCOL.md` |
| **에이전트 시스템 (Hub)** | `_agent/README.md` |
| **서버 현재 상태** | `_context/server_state.yaml` |
| **클라 현재 상태** | `_context/client_state.yaml` |
| **사용자 질의** | `_context/ask_user.yaml` |
| **대화 이력** | `_comms/conversation_journal.json` |
| **마스터 설계서** | `_gdd/game_design.yaml` |

---

## 11. 빠른 참조

### 주요 포트

| 서비스 | 포트 |
|--------|------|
| TCP 브릿지 | 7777 |

### 주요 파일 크기 (컨텍스트 비용 참고)

| 파일 | 크기 | 비고 |
|------|------|------|
| `game_design.yaml` | 54KB | 전체 읽지 않고 필요 섹션만 |
| `conversation_journal.json` | 81KB | 최신 10건만 참조 권장 |
| `server_state.yaml` | 27KB | 전체 읽기 필요 |
| `client_state.yaml` | 29KB | 전체 읽기 필요 |
| `hub.py` | 35KB | Hub 수정 시에만 |

### Hub 2.0 실행

```bash
cd GameServerSkeleton/_agent
python hub.py
```

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-02-15 | 초기 작성. GDD 100% 마일스톤 달성 시점. |
