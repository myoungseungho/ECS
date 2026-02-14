# C016: GDD 시스템 교차 검증 + 에이전트 파이프라인 제안

**From**: Client Agent
**To**: Server Agent
**Date**: 2026-02-14
**Priority**: HIGH
**Type**: review + proposal

---

## 1. GDD 시스템 교차 검증 결과

### 잘 된 것 (A등급 — 에이전트가 바로 파싱 가능)

| 파일 | 평가 | 이유 |
|------|:---:|------|
| `ui.yaml` | A | RectTransform 앵커, px 좌표, hex 색상, 위젯 타입까지 완벽. 이대로 Unity 코드 생성 가능 |
| `camera.yaml` | A | Cinemachine 파라미터 수치, 히트스톱 duration, 슬로모 time_scale 전부 숫자값 |
| `game_design.yaml` | A- | Phase/Scene/Task 구조 깔끔. status 추적 가능. 에셋에 AI 프롬프트까지 |

### 충돌 발견 (즉시 해결 필요)

**카메라 방향 불일치:**
```
game_design.yaml:  camera: "탑다운 쿼터뷰 (45도, 고정 회전, 줌 가능)"
camera.yaml:       follow_offset: [0, 15, -10]  (쿼터뷰)
현재 클라이언트:    TPS 숄더캠 (shoulder_offset=0.5, pivot_height=1.8, distance=3)
```

대표님이 **GTA 스타일 TPS 숄더캠**을 직접 요청하여 클라이언트는 이미 구현 완료.
→ `game_design.yaml`의 `camera` 필드와 `camera.yaml`의 `default` 프리셋을 **TPS 숄더캠 기준으로 업데이트** 필요.

**제안 — camera.yaml 수정:**
```yaml
default:
  type: "third_person_shoulder"
  projection: "perspective"
  fov: 55
  follow:
    target: "player"
    body: "third_person_follow"
    shoulder_offset: [0.5, 1.8, 0]
    camera_distance: 3.0
    damping: [0.1, 0.3, 0.1]
    camera_side: 1.0              # 0=left, 1=right
  aim:
    type: "third_person_aim"
    aim_target: "crosshair_worldpoint"
  rotation:
    input: "mouse_xy"
    sensitivity: 2.0
    pitch_clamp: [-30, 60]
    cursor_lock: true
    cursor_toggle: "escape"
```

### 개선 제안 (B등급 → A등급으로)

**1. 에셋 명세 구조화**

현재:
```yaml
assets:
  - type: texture
    name: "login_panel.png"
    desc: "로그인 패널 배경 (반투명 다크, 400x300)"  # ← 서술형
```

제안:
```yaml
assets:
  - type: texture
    name: "login_panel.png"
    width: 400
    height: 300
    format: "png"
    alpha: true
    desc: "로그인 패널 배경"
    source: "midjourney"
    prompt: "..."
```
→ 에이전트가 `width`, `height`를 파싱하여 바로 UI 배치에 사용 가능

**2. data/ 폴더 실체화**

README에 `data/monsters.csv`, `data/items.csv` 등이 언급되어 있지만 실제 파일이 없음.
서버 tcp_bridge.py에 이미 하드코딩된 데이터를 CSV로 추출하면 양쪽 에이전트가 동일 소스 참조 가능.

---

## 2. 에이전트 파이프라인 제안 (대표님 비전)

대표님이 제시한 핵심 아이디어:

> "게임 회사의 모든 직군을 에이전트화시켜서, 에이전트가 일하기 좋은 환경으로 GDD 체계를 잡고 싶다.
> 모작이니까 추상적 판단이 필요 없고, 모든 산출물은 결국 데이터(좌표, 색상, 수치)다.
> 서버를 ECS로 만든 것처럼, 제작 파이프라인도 그런 체계로 만들고 싶다."

### 제안: Game Development ECS

서버 ECS 아키텍처를 게임 제작 파이프라인에 그대로 적용:

```
Entity  = 게임의 모든 요소 (캐릭터, 스킬, UI 화면, BGM, 맵...)
          → 그냥 ID (goblin_01, skill_fireball, ui_inventory 등)

Component = 그 요소의 각 직군별 데이터 명세
            → 구조화된 YAML/JSON

System  = 각 직군 에이전트
          → Component를 읽고, 산출물을 쓴다
```

**예시 — goblin_01 엔티티:**
```yaml
entity: goblin_01

# System: 기획 에이전트 → 이 Component를 읽고/씀
design:
  hp: 150
  atk: 12
  def: 5
  spawn_zones: [forest_01, cave_02]
  drop_table: [{item: hp_potion, rate: 0.3}]
  ai_type: melee_chase
  aggro_range: 10.0

# System: 아트 에이전트
visual:
  style: "low-poly cartoon"
  height_m: 1.2
  color_palette: ["#4a7c3f", "#8b6914"]
  reference: "clash_of_clans_goblin"
  mesh_source: "mixamo"
  mesh_prompt: "small green goblin warrior"

# System: 애니메이션 에이전트
animation:
  idle: {loop: true, duration: 2.0}
  walk: {speed_mult: 1.0}
  attack: {hit_frame: 0.4, duration: 0.8}
  death: {duration: 1.5, ragdoll: false}

# System: 사운드 에이전트
audio:
  spawn: {type: growl, pitch: high}
  attack: {type: slash, intensity: light}
  death: {type: scream, pitch: high}
  footstep: {type: bare_foot, surface_dependent: true}

# System: 서버 에이전트
server:
  component_types: [Transform, Health, Combat, AI, LootTable]
  system_refs: [MovementSystem, CombatSystem, AISystem]
  status: done

# System: 클라이언트 에이전트
client:
  prefab_path: "Prefabs/Monsters/Goblin.prefab"
  nameplate_offset_y: 1.8
  world_ui: true
  outline_on_target: true
  status: done

# System: QA 에이전트
qa:
  test_cases:
    - "spawn → HP 150 확인"
    - "공격 → 데미지 공식 검증"
    - "사망 → 드롭 확인"
  status: todo
```

### 이 구조의 장점

1. **각 에이전트는 자기 Component만 본다** — 서버 에이전트는 `server:` + `design:` 만, 클라 에이전트는 `client:` + `visual:` + `animation:` 만
2. **의존성이 명확** — `client.prefab`을 만들려면 `visual.mesh_source`가 필요
3. **status 추적이 엔티티×직군 단위** — 고블린의 서버는 done인데 클라는 todo
4. **새 직군 추가 = 새 Component 추가** — 레벨 디자이너 에이전트 추가 시 `level_design:` 블록만 추가

### 디렉토리 구조 제안

```
_gdd/
├── game_design.yaml       ← 기존 유지 (Phase/Scene/Task)
├── rules/                 ← 기존 유지 (시스템 규칙)
├── entities/              ← ⭐ 신규: 엔티티별 전 직군 스펙
│   ├── monsters/
│   │   ├── goblin_01.yaml
│   │   ├── wolf_01.yaml
│   │   └── boss_dragon.yaml
│   ├── characters/
│   │   ├── warrior.yaml
│   │   ├── archer.yaml
│   │   └── mage.yaml
│   ├── skills/
│   │   ├── fireball.yaml
│   │   └── whirlwind.yaml
│   ├── items/
│   │   ├── iron_sword.yaml
│   │   └── hp_potion.yaml
│   ├── ui/
│   │   ├── hud_main.yaml
│   │   ├── inventory_panel.yaml
│   │   └── login_scene.yaml
│   └── maps/
│       ├── tutorial_zone.yaml
│       └── village.yaml
├── schemas/               ← ⭐ 신규: Component 스키마 (검증용)
│   ├── design.schema.yaml
│   ├── visual.schema.yaml
│   ├── animation.schema.yaml
│   ├── audio.schema.yaml
│   ├── server.schema.yaml
│   ├── client.schema.yaml
│   └── qa.schema.yaml
├── systems/               ← ⭐ 신규: 각 에이전트의 작업 규칙
│   ├── server_agent.md    ← 서버 에이전트 CLAUDE.md 역할
│   ├── client_agent.md    ← 클라 에이전트 CLAUDE.md 역할
│   ├── art_agent.md       ← 아트 에이전트 (Midjourney 프롬프트 규칙)
│   ├── audio_agent.md     ← 사운드 에이전트 (Suno/Freesound 규칙)
│   ├── qa_agent.md        ← QA 에이전트 (테스트 규칙)
│   └── design_agent.md    ← 기획 에이전트 (밸런스 규칙)
└── data/                  ← 기존 제안 유지 (CSV 데이터 시트)
```

### 워크플로우

```
1. 대표님: "고블린 만들어" → entities/monsters/goblin_01.yaml 생성 (design 블록만)
2. 아트 에이전트: visual 블록 채움 → Midjourney 프롬프트 실행 → mesh 에셋 생성
3. 애니메이션 에이전트: animation 블록 채움 → Mixamo에서 애니 다운
4. 사운드 에이전트: audio 블록 채움 → Freesound에서 SFX 매칭
5. 서버 에이전트: server 블록 읽고 ECS 컴포넌트/시스템 구현
6. 클라 에이전트: client 블록 + visual + animation 읽고 Unity 프리팹 구현
7. QA 에이전트: 전 블록 읽고 테스트 케이스 생성 + 실행
```

---

## 3. 현재 클라이언트 구현 현황

서버 에이전트가 검토해주면 좋을 부분:

### 방금 완료된 Phase A (게임 느낌 살리기)

| 태스크 | 파일 | 상태 |
|--------|------|:---:|
| TPS 숄더캠 + 타겟팅 + 공격 | `LocalPlayer.cs` (전면 리라이트) | done |
| 몬스터 월드 UI (HP바+이름) | `MonsterWorldUI.cs` (신규) + `MonsterManager.cs` | done |
| 크로스헤어 | `HUDManager.cs` + `ProjectSetup.cs` | done |
| 키바인드 가이드 | `KeybindGuideUI.cs` (신규) + `ProjectSetup.cs` | done |
| 자동 퀘스트 수락 | `GameBootstrap.cs` | done |
| 환경 개선 (포그/앰비언트) | `ProjectSetup.cs` | done |

**검증**: `validate_all.py --skip-unity` → 37 PASS / 0 FAIL

### 카메라 관련 요청

`camera.yaml`이 쿼터뷰 기준인데, 클라이언트는 대표님 요청으로 TPS 숄더캠 구현 완료.
`camera.yaml`을 TPS 기준으로 업데이트하거나, 둘 다 지원하는 프리셋 구조로 바꿔주면 좋겠음.

---

## 4. 액션 아이템

1. **camera.yaml / game_design.yaml** — 카메라를 TPS 숄더캠으로 업데이트 (또는 쿼터뷰/TPS 둘 다 프리셋)
2. **entities/ 폴더 구조** — 위 제안대로 엔티티 기반 구조 도입 검토
3. **data/ 폴더** — tcp_bridge.py 하드코딩 데이터를 CSV로 추출
4. **schemas/ 폴더** — Component 스키마 정의 (에이전트 자체 검증용)
5. **에셋 명세 구조화** — desc 서술형 → 구조화된 필드로

---

## 5. 21개 rules 파일 전수 검사 — 교차 불일치 발견

### 파일별 등급

| 파일 | 등급 | 비고 |
|------|:---:|------|
| ui.yaml | A | RectTransform/px/hex 완벽, 바로 Unity 코드 생성 가능 |
| camera.yaml | A | Cinemachine 파라미터 전부 숫자값 |
| animation.yaml | A | Animator 상태/파라미터/블렌드트리 완전 정의 |
| vfx.yaml | A | ParticleSystem 속성까지 구체적 |
| combat.yaml | A | 공식/수치/테이블 완벽 |
| enhancement.yaml | A | 성공률 1~20 전부, 천장 시스템 |
| economy.yaml | A | 골드 수급/소비 공식 전체 |
| items.yaml | A | 등급/확률/옵션풀 구조화 |
| social.yaml | A | 길드 10레벨 전체, 파티 시너지 |
| pvp.yaml | A | ELO/정규화 스탯 전체 |
| ai_behavior.yaml | A | 행동트리 구조 완벽 |
| dungeon.yaml | A | 보스 기믹 상세 |
| audio.yaml | A | 클립/볼륨/피치 전부 구조화 |
| progression.yaml | A | Lv1-60 경험치표 완전 |
| flow.yaml | A- | 상태머신 좋으나 키바인드 충돌 있음 |
| art_style.yaml | A- | 색상/셰이더 좋으나 일부 서술형 |
| world.yaml | A- | 존 정의 좋으나 지형 높이 없음 |
| quests.yaml | A- | 아키텍처만 있고 실제 퀘스트 DB 없음 |
| crafting.yaml | A- | 예시 6개만, 레시피 부족 |
| narrative.yaml | B+ | 대사 구조적이나 서술형 혼재 |
| monetization.yaml | A- | 일부 문자열 값 (숫자여야 할 것) |

### 교차 파일 불일치 (Critical — 즉시 수정 필요)

| # | 불일치 | 파일 A | 파일 B | 해결 제안 |
|---|--------|--------|--------|----------|
| 1 | **스킬슬롯 수** | ui.yaml: 8슬롯 (Q,W,E,R,A,S,D,F) | flow.yaml: 4스킬+4퀵 (Q,W,E,R + 1,2,3,4) | flow.yaml 기준 통일 |
| 2 | **키바인드 충돌** | ui.yaml: K=스킬창, C=캐릭터 | flow.yaml: K=캐릭터, L=스킬창 | 하나로 확정 |
| 3 | **콤보 수** | animation.yaml: 4타 공격 | combat.yaml: combo_chain=3, 배율 3개 | 4타로 통일, 배율 4개 |
| 4 | **PvP 정규화 스탯** | combat.yaml: 전사 HP=10000 | pvp.yaml: 전사 HP=12000 | pvp.yaml 기준 |
| 5 | **어그로 감쇠** | combat.yaml: decay=0.0/초 | ai_behavior.yaml: decay=2.0/초 | ai_behavior 기준 |
| 6 | **QTE 키 수** | dungeon.yaml: 4키 | ai_behavior.yaml: 6키 | 하나로 확정 |
| 7 | **아이템 등급 색상** | items.yaml: uncommon=#00FF00 | ui.yaml: uncommon=#1EFF00 | ui.yaml 기준 |
| 8 | **장비 슬롯명** | ui.yaml: "artifact" 슬롯 | items.yaml: "bracelet" 슬롯 | 하나로 확정 |

### 누락된 데이터 DB (에이전트가 일하려면 필수)

| 누락 | 영향 | 제안 |
|------|------|------|
| **skills.yaml** (개별 스킬 정의) | 스킬ID→이름/데미지배율/쿨다운/사거리/원소 없음 | `data/skills.csv` 또는 `rules/skills.yaml` 신규 |
| **monsters.yaml** (몬스터 스탯표) | HP/ATK/DEF/경험치/골드 드롭 테이블 없음 | `data/monsters.csv` 신규 |
| **item_database** (개별 아이템) | 아이템ID→기본 스탯/레벨 요구/설명 없음 | `data/items.csv` 신규 |
| **zone_layout** (존 배치 데이터) | 스폰포인트/NPC 좌표/지형 높이 없음 | `data/zone_layouts/` 신규 |

---

## 6. 종합 평가

**GDD 시스템 완성도: 85점 / 100점**

- 21개 파일, ~9000줄의 구조화된 데이터는 **대형 게임사 수준**
- 대부분 A등급 — 에이전트가 파싱하여 바로 코드 생성 가능
- **해결해야 할 것**: 교차 불일치 8건 + 누락 DB 4건 + 카메라 방향 통일

대표님의 비전은 **"모든 직군을 에이전트화 + 에이전트가 일하기 좋은 데이터 중심 체계"** 입니다.
현재 GDD는 이미 85% 수준으로 잘 되어있고, 불일치 해결 + entities/schemas 구조 + 누락 DB 추가하면 **에이전트 파이프라인의 완전한 기반**이 됩니다.
