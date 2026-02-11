# Unity Client Specification

> **이 문서는 C++ 게임 서버 개발자(서버 에이전트)가 Unity 클라이언트 개발자(클라 에이전트)에게 전달하는 핸드오프 문서입니다.**
> 서버는 이미 완성되어 동작 중이며, 이 문서의 프로토콜을 정확히 따르면 서버와 연동됩니다.

---

## 1. 서버 개요

### 아키텍처
```
[Unity Client]
     │
     │ TCP (port 8888)
     ▼
[Gate Server] ──→ 로드밸런싱 ──→ 가장 한가한 Field Server 배정
     │
     │ TCP (port 7777 or 7778)
     ▼
[Field Server] ──→ ECS 기반 게임 로직
                   - 존(맵) 시스템
                   - 관심 영역(AOI) 기반 시야 관리
                   - 채널 시스템
                   - Ghost 시스템 (존 경계 동기화)
```

### 접속 흐름 (필수 순서)
```
1. Gate Server (127.0.0.1:8888) 에 TCP 연결
2. GATE_ROUTE_REQ(70) 전송 (빈 페이로드)
3. GATE_ROUTE_RESP(71) 수신 → Field Server IP/Port 획득
4. Gate 연결 닫기
5. Field Server (받은 IP:Port) 에 TCP 연결
6. LOGIN(60) 전송 → LOGIN_RESULT(61) 수신
7. CHAR_LIST_REQ(62) 전송 → CHAR_LIST_RESP(63) 수신 (선택사항)
8. CHAR_SELECT(64) 전송 → ENTER_GAME(65) 수신
9. CHANNEL_JOIN(20) 전송 → CHANNEL_INFO(22) 수신
10. 이후: MOVE(10) 전송으로 이동, 서버가 APPEAR/DISAPPEAR/MOVE_BROADCAST 전송
```

---

## 2. 패킷 프로토콜 (바이트 레벨)

### 패킷 구조
```
[4바이트: 전체 길이(헤더 포함)] [2바이트: 메시지 타입] [N바이트: 페이로드]
          uint32 LE                   uint16 LE            variable
```

- **헤더 크기**: 항상 6바이트 (4 + 2)
- **바이트 순서**: Little-Endian
- **최대 패킷**: 8192바이트
- **예시**: ECHO(타입 1)로 "hello" 전송
  ```
  [0B 00 00 00] [01 00] [68 65 6C 6C 6F]
   length=11    type=1   "hello"
  ```

### 메시지 타입 전체 목록

| 타입 | 값 | 방향 | 페이로드 |
|------|-----|------|----------|
| ECHO | 1 | 양방향 | 임의 바이트 (그대로 돌려줌) |
| PING | 2 | C→S | 빈 페이로드 → "PONG" 응답 |
| **MOVE** | **10** | **C→S** | `x(4f) y(4f) z(4f)` = 12바이트 |
| **MOVE_BROADCAST** | **11** | **S→C** | `entity(8u64) x(4f) y(4f) z(4f)` = 20바이트 |
| POS_QUERY | 12 | C→S | 빈 → `x(4f) y(4f) z(4f)` 응답 |
| **APPEAR** | **13** | **S→C** | `entity(8u64) x(4f) y(4f) z(4f)` = 20바이트 |
| **DISAPPEAR** | **14** | **S→C** | `entity(8u64)` = 8바이트 |
| **CHANNEL_JOIN** | **20** | **C→S** | `channel_id(4i32)` |
| CHANNEL_INFO | 22 | S→C | `channel_id(4i32)` |
| **ZONE_ENTER** | **30** | **C→S** | `zone_id(4i32)` |
| ZONE_INFO | 31 | S→C | `zone_id(4i32)` |
| **LOGIN** | **60** | **C→S** | `uname_len(1u8) uname(N) pw_len(1u8) pw(N)` |
| **LOGIN_RESULT** | **61** | **S→C** | `result(1u8) account_id(4u32)` = 5바이트 |
| CHAR_LIST_REQ | 62 | C→S | 빈 페이로드 |
| CHAR_LIST_RESP | 63 | S→C | `count(1u8) {id(4u32) name(32) level(4i32) job(4i32)}...` |
| **CHAR_SELECT** | **64** | **C→S** | `char_id(4u32)` |
| **ENTER_GAME** | **65** | **S→C** | `result(1u8) entity(8u64) zone(4i32) x(4f) y(4f) z(4f)` = 25바이트 |
| **GATE_ROUTE_REQ** | **70** | **C→Gate** | 빈 페이로드 |
| **GATE_ROUTE_RESP** | **71** | **Gate→C** | `result(1u8) port(2u16) ip_len(1u8) ip(N)` |
| STATS | 99 | C→S | 빈 → key=value 문자열 응답 |

> **볼드 처리된 것이 Unity 클라이언트가 반드시 구현해야 하는 메시지**

---

## 3. 각 메시지 상세 스펙

### 3.1 GATE_ROUTE_REQ (70) → GATE_ROUTE_RESP (71)

**전송 (C→Gate)**:
```
헤더만 (페이로드 없음)
[06 00 00 00] [46 00]
 length=6      type=70
```

**수신 (Gate→C)**:
```
[result: 1바이트]  0=성공, 그 외=실패
[port: 2바이트]    uint16 LE, Field Server 포트 (예: 7777)
[ip_len: 1바이트]  IP 문자열 길이
[ip: N바이트]      IP 문자열 (예: "127.0.0.1")
```

**성공 시 동작**: Gate 연결을 닫고, 받은 IP:Port로 Field Server에 새로 연결

---

### 3.2 LOGIN (60) → LOGIN_RESULT (61)

**전송 (C→S)**:
```
[uname_len: 1바이트]  유저명 길이
[uname: N바이트]      유저명 (UTF-8)
[pw_len: 1바이트]     비밀번호 길이
[pw: N바이트]         비밀번호 (UTF-8)
```

**수신 (S→C)**:
```
[result: 1바이트]      0=성공, 1=계정없음, 2=비번틀림, 3=잘못된 패킷
[account_id: 4바이트]  uint32 LE (성공 시에만 유효)
```

**테스트 계정**:
| 아이디 | 비밀번호 | 캐릭터 수 |
|--------|----------|-----------|
| hero | pass123 | 2 (Warrior_Kim Lv50, Mage_Lee Lv35) |
| guest | guest | 1 (Archer_Park Lv20) |
| empty | empty | 0 |

---

### 3.3 CHAR_SELECT (64) → ENTER_GAME (65)

**전송 (C→S)**:
```
[char_id: 4바이트]  uint32 LE
```

**수신 (S→C)**:
```
[result: 1바이트]    0=성공, 1=로그인안됨, 2=캐릭터없음
[entity: 8바이트]    uint64 LE (서버가 부여한 Entity ID)
[zone: 4바이트]      int32 LE (존/맵 ID)
[x: 4바이트]         float LE
[y: 4바이트]         float LE
[z: 4바이트]         float LE
```

**캐릭터 목록** (hero 계정):
| char_id | name | level | job | zone | x | y |
|---------|------|-------|-----|------|---|---|
| 1 | Warrior_Kim | 50 | 0(전사) | 1 | 100 | 100 |
| 2 | Mage_Lee | 35 | 2(마법사) | 2 | 500 | 500 |

---

### 3.4 MOVE (10) / MOVE_BROADCAST (11) / APPEAR (13) / DISAPPEAR (14)

**MOVE 전송 (C→S)**:
```
[x: 4바이트 float] [y: 4바이트 float] [z: 4바이트 float]
```
- 서버는 이 위치를 ECS에 반영하고, AOI 내 다른 플레이어에게 MOVE_BROADCAST 전송

**MOVE_BROADCAST 수신 (S→C)**:
```
[entity: 8바이트 uint64] [x: 4f] [y: 4f] [z: 4f]
```
- 다른 플레이어가 이동했을 때 수신. entity로 누가 움직였는지 식별

**APPEAR 수신 (S→C)**:
```
[entity: 8바이트 uint64] [x: 4f] [y: 4f] [z: 4f]
```
- 새 Entity가 시야에 들어왔을 때. 3D 오브젝트를 생성(Instantiate)해야 함

**DISAPPEAR 수신 (S→C)**:
```
[entity: 8바이트 uint64]
```
- Entity가 시야에서 사라졌을 때. 3D 오브젝트를 제거(Destroy)해야 함

---

### 3.5 CHANNEL_JOIN (20) / ZONE_ENTER (30)

**CHANNEL_JOIN (C→S)**:
```
[channel_id: 4바이트 int32]
```
- 채널 1~3 사용 가능. 같은 채널+존의 플레이어만 서로 보임

**ZONE_ENTER (C→S)**:
```
[zone_id: 4바이트 int32]
```
- 존 1, 2 존재. 존 이동 시 서버가 스폰 포인트로 위치 재배치
- 존 1 스폰: (100, 100, 0)
- 존 2 스폰: (500, 500, 0)

---

## 4. 월드 좌표 / 맵 설정

### 서버 좌표계
- **범위**: 0 ~ 1000 (x, y)
- **z**: 현재 항상 0 (높이 미사용)
- **AOI 그리드**: 100x100 단위 셀 (10x10 그리드)
- **시야 범위**: 인접 셀 ±1 (최대 300x300 영역)
- **Ghost 경계**: x=300 또는 y=300 부근 (±50 범위)

### 존 맵 정보
| Zone ID | 이름 (제안) | 스폰 포인트 | 특징 |
|---------|------------|------------|------|
| 1 | 초원/마을 | (100, 100) | 시작 지역 |
| 2 | 던전/숲 | (500, 500) | 이동 목적지 |

---

## 5. Unity 프로젝트 구조 (권장)

```
Assets/
├── Scripts/
│   ├── Network/
│   │   ├── PacketDefinitions.cs   ← 이 파일에 포함됨 (제공)
│   │   ├── TCPClient.cs           ← 이 파일에 포함됨 (제공)
│   │   ├── PacketBuilder.cs       ← 이 파일에 포함됨 (제공)
│   │   └── NetworkManager.cs      ← 이 파일에 포함됨 (제공)
│   │
│   ├── Managers/
│   │   ├── GameManager.cs         ← 게임 상태 관리 (로그인→게임)
│   │   ├── EntityManager.cs       ← 서버 Entity → Unity GameObject 매핑
│   │   └── InputManager.cs        ← 키보드/마우스 → MOVE 패킷 전송
│   │
│   ├── Entity/
│   │   ├── PlayerController.cs    ← 내 캐릭터 (카메라 추적 대상)
│   │   ├── RemotePlayer.cs        ← 다른 플레이어 (APPEAR로 생성, MOVE_BROADCAST로 이동)
│   │   └── EntityBase.cs          ← 공통 베이스 (Entity ID, 위치 보간)
│   │
│   ├── UI/
│   │   ├── LoginUI.cs
│   │   ├── CharSelectUI.cs
│   │   └── GameHUD.cs
│   │
│   └── Data/
│       └── ServerConfig.cs        ← IP/Port 설정
│
├── Prefabs/
│   ├── LocalPlayer.prefab         ← 내 캐릭터 프리팹
│   └── RemotePlayer.prefab        ← 다른 플레이어 프리팹
│
├── Models/                        ← AI 생성 3D 모델 (Meshy/Tripo)
├── Animations/                    ← Mixamo 애니메이션
│
└── Scenes/
    ├── LoginScene.unity
    ├── CharSelectScene.unity
    └── GameScene.unity
```

---

## 6. Unity 에이전트를 위한 지시사항

### 6.1 개발 순서 (권장)

```
Phase 1: 네트워크 연결 검증
  - Scripts/Network/ 4개 파일 배치 (제공됨)
  - 빈 Scene에서 Gate → Field → Login → ENTER_GAME 성공 확인
  - Console에 서버 응답 로그 출력

Phase 2: 3D 월드 + 이동
  - 바닥 Plane (1000x1000)
  - 로우폴리 캐릭터 배치
  - WASD/클릭 이동 → MOVE 패킷 전송
  - 서버 좌표와 Unity 좌표 매핑

Phase 3: 멀티플레이어
  - APPEAR → RemotePlayer 프리팹 Instantiate
  - MOVE_BROADCAST → RemotePlayer 위치 보간
  - DISAPPEAR → RemotePlayer Destroy

Phase 4: UI
  - 로그인 화면 (ID/PW 입력)
  - 캐릭터 선택 화면
  - 게임 HUD (존 정보, 채널, 좌표)

Phase 5: 비주얼
  - AI 생성 3D 모델 교체
  - Mixamo 애니메이션 (Idle/Walk/Run)
  - 간단한 지형/환경
```

### 6.2 좌표 매핑

서버 좌표 (0~1000 2D) → Unity 좌표 (3D):
```csharp
// 서버 → Unity
Vector3 ServerToUnity(float sx, float sy, float sz) {
    return new Vector3(sx, sz, sy);  // 서버 y → Unity z (전방)
}

// Unity → 서버
(float x, float y, float z) UnityToServer(Vector3 pos) {
    return (pos.x, pos.z, pos.y);
}
```

### 6.3 주의사항

1. **TCP는 메시지 경계가 없다**: recv()가 패킷 중간에서 잘릴 수 있음. 반드시 length 필드를 읽고 해당 바이트만큼 모아서 처리해야 함 (제공된 TCPClient.cs가 처리함)

2. **메인 스레드 제한**: Unity에서 GameObject 조작은 메인 스레드만 가능. 네트워크 수신은 별도 스레드 → 큐에 넣고 Update()에서 처리 (제공된 NetworkManager.cs가 처리함)

3. **Entity ID는 uint64**: 서버가 부여하는 Entity ID는 64비트. Dictionary<ulong, GameObject>로 관리

4. **서버 테스트**: 서버는 별도 컴퓨터에서 구동. IP 설정만 변경하면 연결 가능 (기본: 127.0.0.1)

---

## 7. 서버 기동 방법 (테스트용)

서버가 있는 컴퓨터에서:
```bash
cd GameServerSkeleton/build
# Field Server 2개 + Gate Server 1개 시작
FieldServer.exe 7777    # 터미널 1
FieldServer.exe 7778    # 터미널 2
GateServer.exe 7777 7778   # 터미널 3
```

또는 Python으로 자동:
```bash
python build.py   # 빌드
# 수동으로 각 exe 실행
```

---

## 8. 앞으로 추가될 서버 기능 (예정)

| 기능 | 서버 메시지 (예상) | Unity 영향 |
|------|-------------------|-----------|
| EventBus | 서버 내부 (클라 무관) | 없음 |
| 스탯 시스템 | HP/MP 동기화 패킷 | HP바 UI |
| 전투 | ATTACK, DAMAGE, DEATH 패킷 | 공격 모션, 데미지 이펙트 |
| 스킬 | SKILL_USE, SKILL_EFFECT 패킷 | 스킬 이펙트 |
| 아이템 | ITEM_GET, INVENTORY 패킷 | 인벤토리 UI |
| 채팅 | CHAT_MSG 패킷 | 채팅 UI |

> 새 기능이 추가되면 PacketDefinitions.cs에 메시지 타입 추가 + 핸들러 추가하면 됨
