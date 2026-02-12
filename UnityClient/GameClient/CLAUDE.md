# CLAUDE.md — Unity Client AI Agent Guide

> AI 에이전트가 Unity 클라이언트 코드를 수정/확장할 때 참고하는 가이드.
> 서버(C++ ECS)와 달리 클라이언트는 MonoBehaviour 기반 전통 Unity 아키텍처.

## 프로젝트 구조

```
Assets/
├── Editor/                  # Editor 전용 스크립트 (빌드에 미포함)
│   ├── ProjectSetup.cs      # "ECS Game > Setup All" 원클릭 세팅
│   └── SceneValidator.cs    # "ECS Game > Validate Setup" 검증
├── Materials/               # Material 에셋
│   ├── LocalPlayer.mat      # 파랑 (URP/Lit)
│   └── RemotePlayer.mat     # 초록 (URP/Lit)
├── Prefabs/                 # Prefab 에셋
│   ├── LocalPlayer.prefab   # Capsule + LocalPlayer.cs + 파랑 Material
│   └── RemotePlayer.prefab  # Capsule + RemotePlayer.cs + 초록 Material
├── Scenes/
│   ├── GameScene.unity      # 메인 게임 Scene
│   └── TestScene.unity      # 네트워크 테스트 Scene
├── Scripts/
│   ├── Entity/              # 플레이어/엔티티 행동
│   │   ├── LocalPlayer.cs   # 내 캐릭터 (입력, 카메라, 이동 전송)
│   │   ├── RemotePlayer.cs  # 다른 플레이어 (서버 위치로 보간)
│   │   └── MonsterEntity.cs # 몬스터 (HP 추적 + 위치 보간)
│   ├── Managers/            # 싱글톤 매니저
│   │   ├── EntityManager.cs    # 엔티티 생성/파괴/이동 관리
│   │   ├── GameManager.cs      # 게임 상태 머신 (Login→CharSelect→InGame)
│   │   ├── StatsManager.cs     # 스탯 동기화 (HP/MP/ATK/DEF/Level/EXP)
│   │   ├── CombatManager.cs    # 전투 관리 (공격/사망/부활)
│   │   ├── MonsterManager.cs   # 몬스터 생명주기 (스폰/사망/리스폰)
│   │   ├── SkillManager.cs     # 스킬 시스템 (목록/쿨다운/사용)
│   │   ├── InventoryManager.cs # 인벤토리 (아이템 목록/사용/장착)
│   │   ├── PartyManager.cs     # 파티 시스템 (생성/초대/탈퇴)
│   │   ├── BuffManager.cs      # 버프 시스템 (목록/적용/제거/타이머)
│   │   └── QuestManager.cs     # 퀘스트 시스템 (목록/수락/완료)
│   ├── Network/             # 네트워크 레이어 (namespace: Network)
│   │   ├── NetworkManager.cs     # Gate→Field 연결 + 패킷 디스패치
│   │   ├── TCPClient.cs          # TCP 소켓 + 백그라운드 수신 스레드
│   │   ├── PacketBuilder.cs      # 패킷 직렬화/역직렬화
│   │   └── PacketDefinitions.cs  # MsgType enum + 데이터 클래스
│   ├── Test/
│   │   └── ConnectionTest.cs     # 자동 접속 테스트
│   ├── Utils/
│   │   ├── CoordConverter.cs     # 서버↔Unity 좌표 변환
│   │   └── EntityPool.cs         # 오브젝트 풀 (RemotePlayer)
│   ├── Data/                # (예약) 데이터 정의용
│   ├── UI/                  # UI 스크립트
│   │   ├── HUDManager.cs    # HP/MP/EXP바 + 레벨 표시
│   │   ├── CombatUI.cs      # 데미지 텍스트 팝업 + 타겟 HP바
│   │   ├── DeathUI.cs       # 사망 패널 + 부활 버튼
│   │   ├── SkillBarUI.cs    # 하단 스킬바 (1~4키 + 쿨다운)
│   │   ├── InventoryUI.cs   # 인벤토리 패널 (I키 토글)
│   │   ├── PartyUI.cs       # 파티 패널 (P키 토글)
│   │   ├── BuffUI.cs        # 버프 아이콘 (우상단)
│   │   └── QuestUI.cs       # 퀘스트 패널 (Q키 토글)
│   └── interaction-map.yaml # 매니저 의존성 맵
└── Settings/                # URP 렌더링 설정
```

## 아키텍처 규칙

### 싱글톤 패턴
모든 매니저는 동일한 싱글톤 패턴 사용:
```csharp
public static XxxManager Instance { get; private set; }

private void Awake()
{
    if (Instance != null && Instance != this)
    {
        Destroy(gameObject);
        return;
    }
    Instance = this;
    // DontDestroyOnLoad는 필요 시에만
}
```

### 이벤트 기반 통신
- 매니저 간 직접 호출 금지 (싱글톤 접근은 이벤트 구독용으로만)
- `NetworkManager`가 C# event를 발행 → 다른 매니저가 구독
- UI는 매니저의 public 프로퍼티 읽기 + 이벤트 구독으로 통신

### 네임스페이스 규칙
- `Network` 네임스페이스: NetworkManager, TCPClient, PacketBuilder, PacketDefinitions
- 나머지 스크립트: 글로벌 네임스페이스 (default)
- Network 네임스페이스 클래스 참조 시: `using Network;` 또는 `Network.NetworkManager`

## 매니저 수명주기

| 매니저 | DontDestroyOnLoad | 이유 |
|--------|:-:|------|
| NetworkManager | O | TCP 연결을 Scene 전환에도 유지 |
| GameManager | O | 게임 상태를 Scene 전환에도 유지 |
| EntityManager | X | Scene-bound — Scene 로드 시 엔티티 리셋 |
| EntityPool | X | Scene-bound — EntityManager와 같은 수명 |
| StatsManager | X | Scene-bound — Scene 로드 시 스탯 리셋 |
| CombatManager | X | Scene-bound — Scene 로드 시 전투 상태 리셋 |
| MonsterManager | X | Scene-bound — Scene 로드 시 몬스터 리셋 |
| SkillManager | X | Scene-bound — Scene 로드 시 스킬/쿨다운 리셋 |
| InventoryManager | X | Scene-bound — Scene 로드 시 인벤토리 리셋 |
| PartyManager | X | Scene-bound — Scene 로드 시 파티 리셋 |
| BuffManager | X | Scene-bound — Scene 로드 시 버프 리셋 |
| QuestManager | X | Scene-bound — Scene 로드 시 퀘스트 리셋 |

## 데이터 흐름

```
[Server]
   │
   ▼ TCP (byte[])
[TCPClient]  ← 백그라운드 스레드에서 수신, ConcurrentQueue에 적재
   │
   ▼ Update() — 메인 스레드에서 DequeueAll()
[NetworkManager]  ← 패킷 파싱 → C# event 발행
   │
   ├──▶ [GameManager]     ← OnLoginResult, OnEnterGame, OnDisconnected
   │       상태 전이: Login → CharSelect → InGame
   │
   ├──▶ [EntityManager]   ← OnEnterGame, OnEntityAppear/Disappear/Move
   │       엔티티 생성/파괴/위치 업데이트
   │       └──▶ [EntityPool]  ← Get()/Return() — RemotePlayer 오브젝트 풀링
   │
   ├──▶ [StatsManager]    ← OnStatSync, OnEnterGame
   │       스탯 데이터 저장 + OnStatsChanged 발행
   │       └──▶ [HUDManager]  ← OnStatsChanged — HP/MP/EXP/Level 표시
   │
   ├──▶ [CombatManager]   ← OnAttackResult, OnCombatDied, OnRespawnResult
   │       전투 상태 관리 + 이벤트 중계
   │       ├──▶ [CombatUI]  ← OnAttackFeedback — 데미지 텍스트 + 타겟 HP바
   │       └──▶ [DeathUI]   ← OnEntityDied, OnRespawnComplete — 사망/부활 UI
   │
   ├──▶ [MonsterManager]  ← OnMonsterSpawn, OnMonsterRespawn, OnCombatDied, OnEntityMove, OnAttackResult
   │       몬스터 생명주기 관리 + HP 갱신
   │       └──▶ [MonsterEntity]  ← Initialize(), SetTargetPosition()
   │
   ├──▶ [SkillManager]    ← OnSkillList, OnSkillResult, OnEnterGame
   │       스킬 목록/쿨다운 관리 (자동 SKILL_LIST_REQ)
   │       └──▶ [SkillBarUI]  ← OnSkillListChanged — 1~4키 스킬바 + 쿨다운
   │
   ├──▶ [InventoryManager] ← OnInventoryResp, OnItemAddResult, OnItemUseResult, OnItemEquipResult, OnEnterGame
   │       인벤토리 관리 (자동 INVENTORY_REQ)
   │       └──▶ [InventoryUI]  ← OnInventoryChanged — I키 토글 인벤토리 패널
   │
   ├──▶ [PartyManager]    ← OnPartyInfo
   │       파티 상태 관리
   │       └──▶ [PartyUI]  ← OnPartyChanged — P키 토글 파티 패널
   │
   ├──▶ [BuffManager]     ← OnBuffList, OnBuffResult, OnBuffRemoveResp, OnEnterGame
   │       버프 목록/타이머 관리 (자동 BUFF_LIST_REQ)
   │       └──▶ [BuffUI]  ← OnBuffListChanged — 우상단 버프 아이콘
   │
   └──▶ [QuestManager]    ← OnQuestList, OnQuestAcceptResult, OnQuestCompleteResult, OnEnterGame
           퀘스트 상태 관리 (자동 QUEST_LIST_REQ)
           └──▶ [QuestUI]  ← OnQuestListChanged — Q키 토글 퀘스트 패널

[LocalPlayer]
   │ Update() — WASD 입력
   ▼
[NetworkManager.Instance.SendMove()]  → 서버 전송
```

### 좌표 변환 파이프라인
```
서버 좌표 (0~1000, 2D: x, y)
        │
        ▼  CoordConverter.ServerToUnity(sx, sy)
        │  return Vector3(sx * 0.1, 0, sy * 0.1)
        ▼
Unity 좌표 (0~100, 3D: x=서버x*0.1, y=0, z=서버y*0.1)
        │
        ▼  CoordConverter.UnityToServer(pos)
        │  return (pos.x * 10, pos.z * 10)
        ▼
서버 좌표
```

### 접속 파이프라인
```
방법 A: Gate 경유
  ConnectToGate() → GATE_ROUTE_REQ
    → GATE_ROUTE_RESP (Field IP:Port)
    → ConnectToField()

방법 B: 직접 연결
  ConnectDirect(host, port) → ConnectToField()

이후 공통:
  → Login(id, pw)
  → LOGIN_RESULT
  → RequestCharList() / SelectCharacter()
  → ENTER_GAME
    → StatsManager: 자동 STAT_QUERY → STAT_SYNC
  → JoinChannel()
  → InGame (MOVE, APPEAR, DISAPPEAR, MOVE_BROADCAST)
  → 전투: ATTACK_REQ → ATTACK_RESULT, COMBAT_DIED, RESPAWN_REQ → RESPAWN_RESULT
```

## How-To 레시피

### 새 패킷 추가
1. `PacketDefinitions.cs`: `MsgType` enum에 새 값 추가
2. `PacketDefinitions.cs`: 필요 시 응답 데이터 클래스 추가
3. `PacketBuilder.cs`: 직렬화 메서드 추가 (Build 호출)
4. `PacketBuilder.cs`: 역직렬화 Parse 메서드 추가
5. `NetworkManager.cs`: `HandleFieldPacket()`에 case 추가, 이벤트 발행
6. `interaction-map.yaml` 업데이트

### 새 매니저 추가
1. `Assets/Scripts/Managers/` 에 `XxxManager.cs` 생성
2. 싱글톤 패턴 적용 (위 템플릿 참조)
3. DontDestroyOnLoad 여부 결정
4. `Start()`에서 NetworkManager 이벤트 구독
5. `OnDestroy()`에서 이벤트 해제
6. `ProjectSetup.cs`의 GameScene 생성 로직에 오브젝트 추가
7. `SceneValidator.cs`에 검증 항목 추가
8. `interaction-map.yaml` 업데이트

### 새 Entity 타입 추가
1. `Assets/Scripts/Entity/` 에 `XxxEntity.cs` 생성
2. MonoBehaviour 상속, EntityId 프로퍼티 추가
3. Material 생성 (Assets/Materials/)
4. Prefab 생성 (Assets/Prefabs/) — 메시 + 컴포넌트 + Material
5. `EntityManager.cs`에서 타입별 분기 로직 추가
6. `ProjectSetup.cs`에 Material/Prefab 생성 로직 추가

### UI 추가
1. `Assets/Scripts/UI/` 에 UI 스크립트 생성
2. 매니저 이벤트 구독으로 데이터 수신
3. 매니저 public API 호출로 액션 전송
4. Canvas/Panel은 ProjectSetup.cs에서 코드로 생성

## AI 작업 워크플로우 (필수)

코드 작성/수정 후 반드시 아래 검증 루프를 실행한다:

```
1. 코드 작성/수정
2. python validate_client.py 실행 — 컨벤션 검사
3. FAIL 있으면 수정 후 2번 반복
4. python unity_build_check.py 실행 — 컴파일 검사
5. FAIL 있으면 수정 후 2번부터 반복
6. 전부 PASS 시에만 작업 완료로 간주
```

**통합 실행:** `python validate_all.py` (컨벤션 → 컴파일 순차 실행)
- `--skip-unity`: Unity 없이 컨벤션 검사만 실행
- `--unity-path "..."`: Unity.exe 경로 수동 지정

**검증 결과:** `_validation/evidence/` 폴더에 JSON으로 자동 저장

### 검증 규칙 요약

| 수준 | 규칙 | 위반 시 |
|------|------|---------|
| FAIL | Manager는 interaction-map.yaml에 등록 | 즉시 수정 |
| FAIL | Manager에 싱글톤 패턴 (`public static ... Instance`) | 즉시 수정 |
| FAIL | Manager에 OnDestroy 이벤트 해제 | 즉시 수정 |
| FAIL | Network 스크립트는 `namespace Network` | 즉시 수정 |
| FAIL | 런타임에 Find/FindObjectOfType 금지 | 즉시 수정 |
| FAIL | ProjectSetup.cs에 매니저 등록 | 즉시 수정 |
| FAIL | 컴파일 에러 0개 | 즉시 수정 |
| WARN | public 필드 대신 [SerializeField] private | 권장 |
| WARN | 파일 500줄 미만 | 권장 |

## Do's & Don'ts

### Do's
- NetworkManager 이벤트를 통해 통신할 것
- CoordConverter를 통해 좌표 변환할 것 (직접 * 0.1 금지)
- private [SerializeField]로 Inspector 연결, public 필드 최소화
- OnDestroy()에서 이벤트 구독 해제
- EntityPool을 통해 RemotePlayer 재사용
- 패킷 헤더는 6바이트 고정: [4B Length LE][2B MsgType LE][Payload]

### Don'ts
- 매니저 간 직접 메서드 호출 금지 (이벤트 사용)
- 메인 스레드 외에서 Unity API 호출 금지 (TCPClient는 큐 사용)
- NetworkManager 밖에서 TCPClient 직접 접근 금지
- Find/FindObjectOfType 런타임 사용 금지 (싱글톤 Instance 사용)
- Update()에서 매 프레임 패킷 전송 금지 (sendInterval 준수)
- 좌표 변환 시 Y축과 Z축 혼동 주의 (서버 Y → Unity Z)
