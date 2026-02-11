# Unity Client Setup Guide (For Claude Code Agent)

> **이 파일은 Unity 클라이언트를 세팅하는 AI 에이전트를 위한 지시서입니다.**
> 이 파일의 내용을 순서대로 실행하세요.

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
    ├── Scripts/Network/            ← 미리 만들어둔 C# 네트워크 코드
    │   ├── PacketDefinitions.cs
    │   ├── PacketBuilder.cs
    │   ├── TCPClient.cs
    │   └── NetworkManager.cs
    │
    └── GameClient/                 ← Unity 프로젝트 (Unity Hub로 생성됨)
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
- `NetworkManager.cs` — Unity MonoBehaviour (Gate→Field→Login 파이프라인)

---

## Phase 1: 접속 테스트 Scene

### 목표
빈 Scene에서 서버 접속 성공 확인 (Console 로그로 검증)

### 만들 것

**1. `Assets/Scripts/Network/` 에 위 4개 파일 배치** (Phase 0에서 완료)

**2. `Assets/Scenes/TestScene.unity` 생성**
- 빈 Scene에 Empty GameObject "NetworkManager" 추가
- `NetworkManager.cs` 컴포넌트 부착
- Inspector에서 GateHost = "127.0.0.1", GatePort = 8888 설정

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

        // Gate 응답 후 자동으로 Field 연결됨 → 그때 Login 호출
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
[Net] Gate 연결 성공 (127.0.0.1:8888)
[Net] Gate → Field 127.0.0.1:7777
[Net] Field 연결 성공 (127.0.0.1:7777)
Logging in...
[Net] Login result: Success, accountId: 1001
[Net] Enter game: entity=..., zone=1, pos=(100,100,0)
IN GAME! entity=..., zone=1, pos=(100,100,0)
```

---

## Phase 2: 3D 월드 + 캐릭터 이동

### 목표
로우폴리 3D 환경에서 캐릭터가 WASD로 이동, 서버와 동기화

### 만들 것

**1. `Assets/Scripts/Managers/GameManager.cs`**
- 게임 상태 관리 (Login → CharSelect → InGame)
- Scene 전환 관리
- 싱글톤

**2. `Assets/Scripts/Managers/EntityManager.cs`**
- 서버 Entity ID → Unity GameObject 매핑
- `Dictionary<ulong, GameObject>`
- APPEAR → Instantiate, DISAPPEAR → Destroy, MOVE_BROADCAST → 위치 보간

**3. `Assets/Scripts/Entity/LocalPlayer.cs`**
- 내 캐릭터 컨트롤러
- WASD 이동 → 매 프레임 서버에 MOVE 패킷 전송 (throttle: 0.1초 간격)
- 카메라 추적 대상

**4. `Assets/Scripts/Entity/RemotePlayer.cs`**
- 다른 플레이어
- 서버에서 받은 위치로 보간 이동 (Lerp)

**5. GameScene 구성**
- Plane (1000x1000 → Unity 스케일로 변환)
- Directional Light
- Main Camera (LocalPlayer 추적)

### 좌표 매핑 (중요!)
```csharp
// 서버 좌표 (0~1000, 2D) → Unity 좌표 (3D)
Vector3 ServerToUnity(float sx, float sy) {
    return new Vector3(sx * 0.1f, 0f, sy * 0.1f);  // 100x100 Unity 유닛
}

// Unity → 서버
(float x, float y) UnityToServer(Vector3 pos) {
    return (pos.x * 10f, pos.z * 10f);
}
```

---

## Phase 3: UI

### 만들 것
- `LoginUI.cs` — ID/PW 입력 + 로그인 버튼
- `CharSelectUI.cs` — 캐릭터 목록 + 선택 버튼
- `GameHUD.cs` — 존 정보, 채널, 좌표, 접속자 수

---

## Phase 4: 비주얼

### 만들 것
- AI 생성 로우폴리 3D 모델 (Meshy/Tripo3D)
- Mixamo 애니메이션 (Idle, Walk, Run)
- 간단한 지형 (Terrain 또는 ProBuilder)
- 파티클 이펙트 (존 이동 시)

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
└── Utils/         ← 유틸리티 (좌표 변환 등)
```

---

## 서버 테스트 계정

| ID | PW | 캐릭터 |
|----|-----|--------|
| hero | pass123 | Warrior_Kim(Lv50), Mage_Lee(Lv35) |
| guest | guest | Archer_Park(Lv20) |
| empty | empty | (없음) |

---

## 서버 IP 설정

- **같은 PC**: 127.0.0.1 (Gate: 8888)
- **다른 PC**: 서버 컴퓨터의 IP로 변경
- NetworkManager Inspector의 GateHost 필드에서 변경 가능
