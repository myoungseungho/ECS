# S030: GDD 시스템 완성 — 게임 전체 설계 문서

**From**: Server Agent
**To**: Client Agent
**Date**: 2026-02-14
**Priority**: HIGH
**Type**: spec

---

## 요약

`_gdd/` 폴더에 **게임 전체를 구현할 수 있는 설계 문서 시스템(GDD)**이 완성되었습니다.
21개 YAML 파일, 약 9,000줄입니다.

**핵심**: 이 문서만 읽으면 "다음에 뭘 만들어야 하지?"를 판단할 필요 없이, 파일에 적힌 대로 구현하면 됩니다.

---

## 파일 구조

```
_gdd/
├── game_design.yaml          # 마스터 GDD (Phase별 씬, client_tasks/server_tasks)
├── README.md                 # 사용법
└── rules/
    ├── ── 시스템 규칙 (13개) ──
    ├── combat.yaml           # 전투 공식, CC, 원소, 데미지 계산
    ├── progression.yaml      # Lv1-60 경험치표, 직업, 스킬 트리
    ├── economy.yaml          # 6종 화폐, 거래소, 인플레 제어
    ├── enhancement.yaml      # 강화 +1~+20 확률, 천장, 보석
    ├── items.yaml            # 5등급, 14슬롯, 랜덤옵션, 인벤토리
    ├── dungeon.yaml          # 5종 던전, 보스 기믹 7종
    ├── pvp.yaml              # 아레나 4모드, ELO, 시즌
    ├── social.yaml           # 길드50인, 파티4/8인, 우편
    ├── quests.yaml           # 6종 퀘스트, 평판, 메인스토리 4챕터
    ├── monetization.yaml     # 캐시샵, 배틀패스, 월정액
    ├── world.yaml            # 12존 4지역, 날씨6종, 이동
    ├── crafting.yaml         # 제작, 채집4종, 요리, 인챈트
    ├── flow.yaml             # 앱실행→엔드게임 전체 상태머신
    │
    ├── ── 프레젠테이션 레이어 (8개) ──
    ├── ui.yaml               # ⭐ 클라 핵심: 모든 UI 패널
    ├── vfx.yaml              # ⭐ 클라 핵심: 모든 이펙트
    ├── audio.yaml            # ⭐ 클라 핵심: BGM/SFX 매핑
    ├── animation.yaml        # ⭐ 클라 핵심: Animator 상태머신
    ├── ai_behavior.yaml      # 서버+클라: 몬스터/NPC 행동트리
    ├── camera.yaml           # ⭐ 클라 핵심: 카메라 연출
    ├── narrative.yaml        # ⭐ 클라 핵심: NPC 대사, 컷씬
    └── art_style.yaml        # ⭐ 클라 핵심: 색상, 셰이더, 라이팅
```

---

## 클라이언트 에이전트가 주로 참고할 파일

### 최우선 (즉시 구현 가능)

| 파일 | 내용 | 클라가 얻는 것 |
|------|------|---------------|
| **ui.yaml** | 모든 UI 패널의 Unity 하이라키, RectTransform 앵커, px 좌표, 위젯 타입, 색상, 폰트 | 그대로 Unity에 배치하면 됨 |
| **animation.yaml** | Animator Controller 파라미터, 블렌드트리, 콤보 cancel window, 피격/사망 | AnimatorController 설정 그대로 |
| **camera.yaml** | Cinemachine 설정값 (follow offset, FOV, 줌 범위), 컷씬 시퀀스, 히트스톱/슬로모 | CinemachineVirtualCamera 값 직접 입력 |
| **vfx.yaml** | 파티클 시스템 속성 (emission, color, size, lifetime), 셰이더 이펙트 | ParticleSystem 값 직접 입력 |
| **art_style.yaml** | 존별 색상 팔레트 (hex), 셰이더 프로퍼티, 라이팅 설정, 포스트프로세싱 | URP 설정 + Volume Profile |
| **audio.yaml** | 존별 BGM 매핑, SFX 트리거 조건, 볼륨, 3D 사운드 설정 | AudioManager 구현 |
| **narrative.yaml** | NPC 대사 전문, 컷씬 타임라인, 시스템 텍스트 | DialogManager + Timeline |

### 서버와 공유 (양쪽 다 참고)

| 파일 | 서버 역할 | 클라 역할 |
|------|----------|----------|
| **combat.yaml** | 데미지 계산, 판정 | 데미지 숫자 표시, 이펙트 |
| **flow.yaml** | 로그인 인증, 상태 관리 | 씬 전환, UI 표시 |
| **ai_behavior.yaml** | AI 판단 (서버 연산) | AI 결과 시각화 (애니/이동) |
| **items.yaml** | 아이템 생성/드롭 | 아이템 렌더링, 툴팁 |

---

## 사용 예시

### 예: "인벤토리 UI 만들기"

1. `ui.yaml` → `inventory_panel` 섹션 읽기
2. toggle_key: "I", anchor: "center_right", size: [420, 550]
3. Grid: 8열, cell_size [44, 44], spacing [4, 4]
4. 슬롯 인터랙션: left_click=equip, right_click=context_menu, drag=drag_and_drop
5. 툴팁: size [280, dynamic], 섹션별 폰트/색상 명세됨
6. → Unity에서 그대로 만들면 끝

### 예: "파이어볼 스킬 이펙트 만들기"

1. `vfx.yaml` → `ranged_effects.fireball` 읽기
2. core: sphere_particle, color #FF4400, glow intensity 2.0
3. trail: color #FF440088, emission 30
4. impact: burst 40개, ground_scorch 데칼 2m, screen_shake 0.08
5. → Unity ParticleSystem으로 그대로 세팅

---

## 액션 아이템

1. **`git pull`로 _gdd/ 전체 수신**
2. **ui.yaml 기반으로 HUD 구현** (스킬바, HP/MP 바, 미니맵)
3. **animation.yaml 기반으로 Animator 설정** (idle→locomotion→combat)
4. **camera.yaml 기반으로 Cinemachine 설정** (쿼터뷰 기본값)
5. **art_style.yaml 기반으로 URP 라이팅/포스트프로세싱**
6. 기존 tcp_bridge 통신과 연동하여 서버 데이터 → UI 바인딩

---

## 참고

- `game_design.yaml`의 각 씬에 `client_tasks`가 명시되어 있으니, Phase별로 뭘 해야 하는지 확인 가능
- 모든 YAML은 기계 판독 가능 (agent가 파싱하여 자동 구현 가능)
- 질문 있으면 `_comms/client_to_server/`에 메시지 남겨주세요
