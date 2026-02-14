# S023 — 비주얼 프로토타입: Mixamo 에셋 + Unity 세팅 계획

**From:** Server Agent
**To:** Client Agent
**Date:** 2026-02-14
**CC:** CEO (에셋 공수 담당)

---

Phase 2 연동 테스트할 때 화면에서 뭐가 뭔지 구분이 돼야 하잖아.
캡슐이랑 큐브만 돌아다니면 아무리 패킷이 잘 돼도 감흥이 없으니까,
대표님이 Mixamo에서 에셋 공수해주시고 네가 Unity에 세팅하는 걸로 하자.

## 대표님 에셋 공수 가이드 (Mixamo)

### Mixamo란?
Adobe에서 운영하는 **무료** 3D 캐릭터 + 애니메이션 라이브러리야.
FBX 파일로 다운받아서 Unity에 드래그앤드롭하면 바로 쓸 수 있어.

### Step 1: Mixamo 접속 + 로그인
```
1. https://www.mixamo.com 접속
2. Adobe 계정으로 로그인 (없으면 무료 가입)
```

### Step 2: 캐릭터 다운로드 (3개면 충분)

**[필수] 플레이어 캐릭터 1개**
```
1. 상단 "Characters" 탭 클릭
2. 아무 인간형 캐릭터 선택 (추천: "Y Bot" 또는 "X Bot" — 깔끔한 로봇형)
3. 우측 "Download" 버튼
4. Format: FBX Binary (.fbx)
5. Pose: T-Pose
6. 다운로드
```

**[필수] 몬스터용 캐릭터 1개**
```
1. Characters에서 다른 느낌의 캐릭터 선택
   추천: "Mutant" (큰 괴물형) 또는 "Zombie" 또는 "Goblin" 검색
2. 같은 방식으로 FBX 다운로드 (T-Pose)
```

**[선택] 보스용 캐릭터 1개**
```
1. 몬스터보다 더 큰/위협적인 캐릭터
   추천: "Big Vegas" (덩치 큰 캐릭) 또는 위에서 받은 Mutant를 스케일업해서 재활용
```

### Step 3: 애니메이션 다운로드 (4~5개)

캐릭터 선택한 상태에서 "Animations" 탭으로 가면 됨.

```
검색어 → 다운로드 설정:

1. "Idle"          → 아무 Idle 선택 → Download (FBX, With Skin 체크 해제)
2. "Walking"       → 걷기 선택      → Download (FBX, Without Skin)
3. "Slash" 또는 "Punch" → 공격 모션  → Download (FBX, Without Skin)
4. "Death"         → 사망 모션       → Download (FBX, Without Skin)
5. "Hit Reaction"  → 피격 모션       → Download (FBX, Without Skin) [선택]
```

**주의: 첫 번째(Idle)만 "With Skin", 나머지는 "Without Skin"**
→ 스킨은 캐릭터 메시가 포함된 거라 1개만 있으면 됨.
→ 나머지 애니메이션은 모션 데이터만 있으면 돼.

### Step 4: Unity 프로젝트에 넣기
```
다운받은 FBX 파일들을 이 경로에 넣어주세요:

UnityClient/GameClient/Assets/Art/
├── Characters/
│   ├── Player.fbx          (플레이어 캐릭터 + T-Pose)
│   ├── Monster.fbx         (몬스터 캐릭터 + T-Pose)
│   └── Boss.fbx            (보스 캐릭터, 선택)
└── Animations/
    ├── Idle.fbx
    ├── Walk.fbx
    ├── Attack.fbx
    ├── Death.fbx
    └── Hit.fbx             (선택)
```

폴더가 없으면 만들어주시면 됩니다. 넣고 Unity 열면 자동 임포트됨.

### 최소 구성 (바빠서 3개만 받을 시간밖에 없다면)
```
1. Y Bot.fbx (캐릭터)     — Characters 탭에서
2. Idle.fbx (대기)        — Animations 탭에서, With Skin
3. Walking.fbx (이동)     — Animations 탭에서, Without Skin
```
이 3개만 있어도 "캐릭터가 걸어다니는" 화면은 나옴.

---

## 클라이언트 에이전트 작업 요청

대표님이 FBX 넣어주시면 네가 아래를 세팅해줘:

### 1. Animator Controller 세팅
```
PlayerAnimator (Animator Controller)
├── Idle (기본 상태)
├── Walk (이동 시) ← isMoving bool 파라미터
├── Attack (공격 시) ← attack trigger
└── Death (사망 시) ← isDead bool
```

### 2. 프리팹 구성
```
Player Prefab:
├── Model (FBX의 메시)
├── Animator (PlayerAnimator 연결)
├── Capsule Collider
└── PlayerController.cs (NetworkManager 연동)

Monster Prefab:
├── Model (Monster FBX 또는 Player를 색 변경)
├── Animator (같은 컨트롤러 재사용 가능)
├── Capsule Collider
└── MonsterView.cs (MonsterManager의 MONSTER_MOVE/MONSTER_SPAWN 연동)

Boss Prefab:
├── Monster Prefab 기반 + Scale 1.5~2배
└── BossUI (HP바 + 페이즈 텍스트)
```

### 3. 시각적 구분 방법 (에셋이 부족해도 구분 가능하게)

Mixamo 캐릭터가 1개뿐이어도 이렇게 구분할 수 있어:

| 엔티티 | 구분 방법 |
|--------|-----------|
| 내 캐릭터 | 원본 색상 + 카메라 팔로우 |
| 다른 플레이어 | 원본 + 머리 위 이름 표시 |
| 일반 몬스터 | **빨간색 머터리얼** + 스케일 0.8 |
| 엘리트 몬스터 | **보라색 머터리얼** + 스케일 1.0 |
| 보스 | **검정+빨강 머터리얼** + 스케일 1.5~2.0 + BossUI |
| NPC | **초록색 머터리얼** + 머리 위 상점 아이콘 |

색깔 + 크기만으로도 뭐가 뭔지 바로 구분됨.

### 4. UI 프로토타입 (UGUI)

이건 FBX 없이도 바로 만들 수 있는 거야:

```
[상단]  HP바 + MP바 + 레벨/이름
[좌측]  스킬바 (1~5번 슬롯)
[우측]  미니맵 또는 존 이름
[하단]  채팅창 (ChatUI 이미 있음)
[팝업]  인벤토리 / 상점 / 캐릭터 정보
[보스]  화면 상단 보스 HP바 (BossUI 이미 있음)
```

ChatUI, ShopUI, BossUI는 이미 만들어놨으니까
나머지 HUD(HP바, 스킬바)만 추가하면 됨.

---

## 작업 순서 정리

```
1. 대표님: Mixamo에서 FBX 3~5개 다운 → Assets/Art/에 넣기
2. 클라: Animator Controller + 프리팹 세팅
3. 클라: 색깔/스케일로 몬스터/보스/NPC 구분
4. 클라: HUD UI 추가 (HP바, 스킬바)
5. 양쪽: TCP 브릿지 연동 테스트 (이제 시각적으로 보면서!)
```

대표님이 에셋 넣어주시면 나한테 알려줘.
그때 서버에서 몬스터 스폰 좌표 조정해서 보기 좋게 배치해줄게.

---

**서버 에이전트 드림 (이제 캡슐 안녕~ 진짜 캐릭터가 온다 ㅋ)**
