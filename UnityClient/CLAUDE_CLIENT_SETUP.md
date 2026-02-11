# Unity Client Setup Guide (For Claude Code Agent)

> **이 파일은 Unity 클라이언트를 세팅하는 AI 에이전트를 위한 지시서입니다.**
> 이 파일의 내용을 순서대로 실행하세요.

---

## 최종 목표 (데모 비전)

**"200명의 AI 봇이 3D 로우폴리 캐릭터로 돌아다니는 MMO 월드"**

서버 컴퓨터에서 Python 봇 200개를 실행하면:
- 각 봇이 서버에 접속 → 로그인 → 캐릭터 선택 → 존 입장
- 봇들이 자동으로 이동, 존 이동, 채널 전환
- **Unity 클라이언트에서 이 봇들이 3D 캐릭터로 보임**
- 사용자도 직접 Unity 클라이언트로 접속해서 봇들 사이를 걸어다닐 수 있음

이것이 **ECS + IOCP 서버의 성능 데모**입니다.

---

## 프로젝트 개요

이 레포는 **C++ ECS MMORPG 서버 + Unity 클라이언트**가 공존하는 모노레포입니다.

```
ECS/
├── Core/, Components/, Systems/    ← C++ 서버 (완성됨, 건드리지 마세요)
├── Servers/                        ← 서버 실행 코드
├── NetworkEngine/                  ← IOCP 네트워크 엔진
│
└── UnityClient/                    ← 여기서 작업
    ├── UNITY_CLIENT_SPEC.md        ← ⭐ 서버 프로토콜 완전 스펙 (필독)
    ├── CLAUDE_CLIENT_SETUP.md      ← 이 파일 (AI 에이전트 지시서)
    ├── Scripts/Network/            ← 미리 만들어둔 C# 네트워크 코드
    │   ├── PacketDefinitions.cs
    │   ├── PacketBuilder.cs
    │   ├── TCPClient.cs
    │   └── NetworkManager.cs
    │
    └── GameClient/                 ← Unity 프로젝트 (Unity Hub로 생성)
        └── Assets/
```

**서버는 별도 컴퓨터에서 이미 동작 중입니다. 클라이언트만 만드세요.**

---

## Phase 0: 사전 준비

### 0-1. 필독 문서

아래 파일을 **반드시 먼저 읽으세요**:

```
UnityClient/UNITY_CLIENT_SPEC.md
```

이 문서에 서버의 모든 패킷 프로토콜, 바이트 레벨 스펙, 접속 흐름이 있습니다.

### 0-2. 네트워크 코드 배치

미리 만들어둔 C# 4개 파일을 Unity 프로젝트로 복사:

```
복사 원본: UnityClient/Scripts/Network/*.cs
복사 대상: UnityClient/GameClient/Assets/Scripts/Network/
```

4개 파일:
- `PacketDefinitions.cs` — 서버 MsgType enum 미러
- `PacketBuilder.cs` — 패킷 조립/파싱 유틸리티
- `TCPClient.cs` — 스레드 기반 TCP 클라이언트
- `NetworkManager.cs` — Unity MonoBehaviour (Gate->Field->Login 파이프라인)

---

## Phase 1: 접속 테스트 Scene

### 목표
빈 Scene에서 서버 접속 성공 확인 (Console 로그로 검증)

### 만들 것

**1. `Assets/Scripts/Network/` 에 위 4개 파일 배치** (Phase 0에서 완료)

**2. `Assets/Scenes/TestScene.unity` 생성**
- 빈 Scene에 Empty GameObject "NetworkManager" 추가
- `NetworkManager.cs` 컴포넌트 부착
- Inspector에서 GateHost = 서버 IP, GatePort = 8888 설정

**3. `Assets/Scripts/Test/ConnectionTest.cs` 생성**

```csharp
using UnityEngine;
using Network;

public class ConnectionTest : MonoBehaviour
{
    void Start()
    {
        var net = NetworkManager.Instance;

        net.OnLoginResult += (result, accountId) => {
            Debug.Log($"Login: {result}, accountId={accountId}");
            if (result == LoginResult.Success)
                net.SelectCharacter(1);  // Warrior_Kim
        };

        net.OnEnterGame += (result) => {
            if (result.ResultCode == 0)
            {
                Debug.Log($"IN GAME! entity={result.EntityId}, zone={result.ZoneId}, pos=({result.X},{result.Y},{result.Z})");
                net.JoinChannel(1);
            }
        };

        net.OnEntityAppear += (eid, x, y, z) => {
            Debug.Log($"APPEAR: entity={eid} at ({x},{y},{z})");
        };

        net.OnEntityMove += (eid, x, y, z) => {
            Debug.Log($"MOVE: entity={eid} -> ({x},{y},{z})");
        };

        net.OnEntityDisappear += (eid) => {
            Debug.Log($"DISAPPEAR: entity={eid}");
        };

        net.OnError += (msg) => Debug.LogError($"NET ERROR: {msg}");

        // 접속 시작
        Debug.Log("Connecting to Gate...");
        net.ConnectToGate();

        // Gate 응답 후 자동으로 Field 연결됨 -> 그때 Login 호출
        Invoke(nameof(DoLogin), 1.0f);
    }

    void DoLogin()
    {
        Debug.Log("Logging in...");
        NetworkManager.Instance.Login("hero", "pass123");
    }

    void Update()
    {
        // 스페이스바로 이동 테스트
        if (Input.GetKeyDown(KeyCode.Space) &&
            NetworkManager.Instance.State == NetworkManager.ConnectionState.InGame)
        {
            float x = Random.Range(50f, 950f);
            float y = Random.Range(50f, 950f);
            NetworkManager.Instance.SendMove(x, y, 0);
            Debug.Log($"Sent MOVE: ({x},{y})");
        }
    }
}
```

**4. TestScene에 ConnectionTest 부착**
- Empty GameObject "ConnectionTest" 추가
- `ConnectionTest.cs` 컴포넌트 부착

### 성공 기준
Unity Console에 아래 로그가 순서대로 나오면 성공:
```
Connecting to Gate...
[Net] Gate 연결 성공
[Net] Gate -> Field IP:Port
[Net] Field 연결 성공
Logging in...
Login: Success, accountId=1001
IN GAME! entity=..., zone=1, pos=(100,100,0)
```

---

## Phase 2: 3D 월드 + 내 캐릭터 이동

### 목표
로우폴리 3D 환경에서 내 캐릭터가 WASD로 이동, 서버와 동기화

### 만들 것

**1. `Assets/Scripts/Managers/GameManager.cs`**
- 게임 상태 관리 (Login -> CharSelect -> InGame)
- Scene 전환 관리
- 싱글톤

**2. `Assets/Scripts/Managers/EntityManager.cs`**
- 서버 Entity ID -> Unity GameObject 매핑
- `Dictionary<ulong, GameObject>`
- APPEAR -> Instantiate, DISAPPEAR -> Destroy, MOVE_BROADCAST -> 위치 보간

**3. `Assets/Scripts/Entity/LocalPlayer.cs`**
- 내 캐릭터 컨트롤러
- WASD 이동 -> 매 프레임 서버에 MOVE 패킷 전송 (throttle: 0.1초 간격)
- 카메라 추적 대상

**4. `Assets/Scripts/Entity/RemotePlayer.cs`**
- 다른 플레이어 (봇 포함)
- 서버에서 받은 위치로 보간 이동 (Lerp)

**5. GameScene 구성**
- Plane (바닥, 100x100 Unity 유닛 = 서버 1000x1000)
- Directional Light
- Main Camera (LocalPlayer 추적, 3인칭 탑다운 또는 쿼터뷰)

### 좌표 매핑 (중요!)
```csharp
// 서버 좌표 (0~1000, 2D) -> Unity 좌표 (3D)
Vector3 ServerToUnity(float sx, float sy) {
    return new Vector3(sx * 0.1f, 0f, sy * 0.1f);  // 100x100 Unity 유닛
}

// Unity -> 서버
(float x, float y) UnityToServer(Vector3 pos) {
    return (pos.x * 10f, pos.z * 10f);
}
```

### 성공 기준
- WASD로 캐릭터 이동 -> 서버에 MOVE 전송 -> 캐릭터가 3D 공간에서 움직임
- 카메라가 캐릭터를 추적

---

## Phase 3: 다른 플레이어 보기 (멀티플레이어)

### 목표
서버가 보내는 APPEAR/DISAPPEAR/MOVE_BROADCAST로 다른 플레이어를 3D로 렌더링

### 핵심 로직

```csharp
// EntityManager.cs 핵심 코드

NetworkManager.Instance.OnEntityAppear += (entityId, x, y, z) => {
    if (entityId == myEntityId) return;  // 나 자신은 무시

    var go = Instantiate(remotePlayerPrefab);
    go.transform.position = ServerToUnity(x, y);
    entityMap[entityId] = go;
};

NetworkManager.Instance.OnEntityDisappear += (entityId) => {
    if (entityMap.TryGetValue(entityId, out var go)) {
        Destroy(go);
        entityMap.Remove(entityId);
    }
};

NetworkManager.Instance.OnEntityMove += (entityId, x, y, z) => {
    if (entityMap.TryGetValue(entityId, out var go)) {
        // 보간 이동 (갑자기 워프하지 않게)
        var remote = go.GetComponent<RemotePlayer>();
        remote.SetTargetPosition(ServerToUnity(x, y));
    }
};
```

### RemotePlayer 보간

```csharp
// RemotePlayer.cs
public class RemotePlayer : MonoBehaviour
{
    Vector3 targetPos;
    float lerpSpeed = 10f;

    public void SetTargetPosition(Vector3 pos) {
        targetPos = pos;
    }

    void Update() {
        transform.position = Vector3.Lerp(
            transform.position, targetPos, Time.deltaTime * lerpSpeed);

        // 이동 방향으로 회전
        Vector3 dir = targetPos - transform.position;
        if (dir.magnitude > 0.01f)
            transform.rotation = Quaternion.LookRotation(dir);
    }
}
```

### 성공 기준
- 2개 Unity 클라이언트를 동시 실행 (hero, guest)
- 한쪽에서 이동하면 다른쪽에서 캐릭터가 움직이는 것이 보임

---

## Phase 4: AI 봇 200개 시각화 (핵심 데모!)

### 목표
서버 컴퓨터에서 Python 봇 200개 실행 -> Unity에서 200개 3D 캐릭터가 돌아다님

### 봇 동작 원리 (서버 측, 이미 구현됨)

서버 컴퓨터에서 `stress_test.py` 또는 `visual_stress_test.py` 실행:
```bash
python stress_test.py --bots 200 --host 127.0.0.1 --gate-port 8888
```

각 봇은:
1. Gate -> Field 접속
2. Login (자동 생성 계정: bot_001 ~ bot_200)
3. 캐릭터 선택
4. 채널 1 입장
5. 주기적으로 랜덤 이동 (MOVE 패킷)

### Unity 측 처리 (당신이 만들 것)

봇은 서버에서 보면 일반 플레이어와 동일합니다.
**Unity 클라이언트가 해야 할 것은 Phase 3과 완전히 동일합니다:**

- 봇이 접속하면 서버가 Unity에 APPEAR 전송 -> 3D 캐릭터 생성
- 봇이 이동하면 서버가 MOVE_BROADCAST 전송 -> 위치 보간
- 봇이 시야에서 나가면 DISAPPEAR -> 3D 캐릭터 제거
- AOI(관심 영역) 덕분에 시야 밖의 봇은 자동 필터링

### 성능 최적화 (200개 동시 렌더링)

200개 캐릭터를 동시에 렌더링하려면 최적화가 필요합니다:

**1. Object Pooling**
```csharp
// 매번 Instantiate/Destroy 대신 풀링
public class EntityPool : MonoBehaviour
{
    Queue<GameObject> pool = new Queue<GameObject>();

    public GameObject Get() {
        if (pool.Count > 0) {
            var go = pool.Dequeue();
            go.SetActive(true);
            return go;
        }
        return Instantiate(prefab);
    }

    public void Return(GameObject go) {
        go.SetActive(false);
        pool.Enqueue(go);
    }
}
```

**2. LOD (Level of Detail)**
- 가까운 캐릭터: 풀 모델 + 애니메이션
- 먼 캐릭터: 단순 캡슐/큐브 + 색깔만 다르게
- 매우 먼 캐릭터: Billboard 스프라이트

**3. GPU Instancing**
- 동일 머티리얼 캐릭터 200개는 Instancing으로 1 draw call

**4. 이름표 최적화**
- 가까운 캐릭터만 이름표(WorldSpace Canvas) 표시
- 먼 캐릭터는 이름표 숨김

### 데모 시나리오

1. 서버 컴퓨터: FieldServer x2, GateServer x1 기동
2. 서버 컴퓨터: `python stress_test.py --bots 200` 실행
3. Unity 컴퓨터: 클라이언트 실행 -> hero 계정 로그인
4. Unity 화면: **200개의 3D 캐릭터가 돌아다니는 것이 보임**
5. 사용자가 WASD로 직접 걸어다니며 봇 사이를 구경

### 성공 기준
- Unity에서 50+ 캐릭터가 동시에 움직이며 30fps 유지
- 봇이 시야에 들어오면 3D 캐릭터가 나타남
- 봇이 시야에서 나가면 사라짐
- 사용자가 직접 걸어다니면서 봇을 볼 수 있음

---

## Phase 5: UI

### 만들 것
- `LoginUI.cs` — ID/PW 입력 + 로그인 버튼
- `CharSelectUI.cs` — 캐릭터 목록 + 선택 버튼
- `GameHUD.cs` — 존 정보, 채널, 좌표, 접속자 수, FPS
- `MiniMap.cs` — 미니맵에 모든 visible entity 표시 (봇 데모에 필수!)

### MiniMap 구현 힌트

```csharp
// 서버 좌표 (0~1000) -> 미니맵 UI 좌표 (200x200 px)
Vector2 WorldToMiniMap(float sx, float sy) {
    return new Vector2(sx * 0.2f, sy * 0.2f);
}
```

- EntityManager의 entityMap 순회 -> 미니맵에 점 표시
- 내 캐릭터: 흰색 점 (크게)
- 다른 플레이어/봇: 초록색 점 (작게)

---

## Phase 6: 비주얼 업그레이드

### 만들 것
- 로우폴리 3D 캐릭터 모델 (Meshy/Tripo3D AI 생성 또는 에셋 스토어)
- Mixamo 애니메이션 (Idle, Walk, Run)
- 간단한 지형 (Terrain 또는 ProBuilder)
- 파티클 이펙트 (존 이동 시 텔레포트)
- 스카이박스 + 포그

### 캐릭터 프리팹 구조
```
RemotePlayerPrefab
├── Model (로우폴리 3D 모델)
├── Animator (Idle/Walk 전환)
├── NameTag (WorldSpace Canvas)
│   └── Text "bot_042"
└── RemotePlayer.cs (보간 이동 스크립트)
```

### 애니메이션 전환
```csharp
// 이동 속도에 따라 Idle <-> Walk
float speed = (targetPos - transform.position).magnitude;
animator.SetBool("IsMoving", speed > 0.1f);
```

---

## 설계 원칙: AI 에이전트 친화적 구조

### 반복 패턴 (새 기능 추가 시 복붙)

**패턴 A: 새 Manager 추가**
```
1. Assets/Scripts/Managers/XXXManager.cs 생성 (싱글톤)
2. NetworkManager.cs의 HandleFieldPacket()에 case 추가
3. 필요 시 PacketDefinitions.cs에 MsgType 추가
4. 필요 시 PacketBuilder.cs에 Build/Parse 메서드 추가
```

**패턴 B: 새 UI 추가**
```
1. Assets/Scripts/UI/XXXUI.cs 생성
2. Canvas 아래에 UI 요소 배치
3. Manager의 이벤트 구독하여 데이터 표시
```

**패턴 C: 새 Entity 타입 추가**
```
1. Assets/Scripts/Entity/XXXController.cs 생성
2. Assets/Prefabs/XXX.prefab 생성
3. EntityManager에서 APPEAR 시 타입 분기하여 Instantiate
```

### ScriptableObject 데이터 드리븐

게임 데이터는 코드에 하드코딩하지 말고 ScriptableObject로:

```csharp
[CreateAssetMenu(fileName = "MonsterData", menuName = "Data/Monster")]
public class MonsterData : ScriptableObject
{
    public int id;
    public string displayName;
    public int hp;
    public int attack;
    public GameObject prefab;
}
```

### 폴더 규칙

```
Assets/Scripts/
├── Network/       ← 서버 통신 (건드리지 않음)
├── Managers/      ← 싱글톤 매니저 (기능당 1개)
├── Entity/        ← 게임 오브젝트 컨트롤러
├── UI/            ← UI 스크립트
├── Data/          ← ScriptableObject 정의
└── Utils/         ← 유틸리티 (좌표 변환, 오브젝트 풀 등)
```

---

## 서버 테스트 계정

| ID | PW | 캐릭터 |
|----|-----|--------|
| hero | pass123 | Warrior_Kim(Lv50), Mage_Lee(Lv35) |
| guest | guest | Archer_Park(Lv20) |
| empty | empty | (없음) |

봇 계정 (stress_test.py가 자동 생성):
| ID | PW | 캐릭터 |
|----|-----|--------|
| bot_001 ~ bot_200 | bot | Bot_001(Lv1) ~ Bot_200(Lv1) |

---

## 서버 IP 설정

- **같은 PC**: 127.0.0.1 (Gate: 8888)
- **다른 PC**: 서버 컴퓨터의 IP로 변경
- NetworkManager Inspector의 GateHost 필드에서 변경 가능

---

## 앞으로 추가될 서버 기능 (예정)

서버에 새 기능이 추가되면 이 문서가 업데이트됩니다.
각 기능은 새 패킷 타입 + Unity 측 핸들러 추가로 연동합니다.

| 기능 | 서버 패킷 | Unity 영향 |
|------|----------|-----------|
| 스탯 시스템 | STAT_QUERY(90), STAT_SYNC(91) | HP바 UI, 레벨 표시 |
| 전투 | ATTACK, DAMAGE, DEATH | 공격 모션, 데미지 이펙트 |
| 스킬 | SKILL_USE, SKILL_EFFECT | 스킬 이펙트 |
| 아이템 | ITEM_GET, INVENTORY | 인벤토리 UI |
| 채팅 | CHAT_MSG | 채팅 UI, 말풍선 |

> 새 기능이 추가되면 PacketDefinitions.cs에 MsgType 추가 + 핸들러 추가하면 됨

---

## Phase별 우선순위 요약

| Phase | 핵심 | 의존성 | 난이도 |
|-------|------|--------|--------|
| 0 | 네트워크 코드 배치 | 없음 | 쉬움 |
| 1 | 접속 테스트 | Phase 0 | 쉬움 |
| 2 | 3D 월드 + 내 캐릭터 | Phase 1 | 보통 |
| 3 | 멀티플레이어 | Phase 2 | 보통 |
| **4** | **AI 봇 200개 시각화** | **Phase 3** | **보통 (핵심!)** |
| 5 | UI | Phase 2 | 보통 |
| 6 | 비주얼 업그레이드 | Phase 3 | 자유 |

**Phase 4가 최종 데모 목표입니다. Phase 1~3을 최대한 빠르게 마치고 4에 집중하세요.**
