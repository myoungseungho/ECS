# GDD System - 에이전트 AI 소비형 게임 디자인 문서

## 개념

대형 게임사(스마일게이트, 블리자드 등)가 수백 페이지짜리 기획서를 작성하듯이,
우리도 동일한 수준의 GDD를 만들되 **에이전트 AI가 직접 파싱하고 실행할 수 있는 형태**로 작성합니다.

```
[game_design.yaml]     → 마스터 설계 문서 (What to build)
       │
       ├─→ 서버 에이전트: server_tasks 필터링 → 구현 → status: done
       ├─→ 클라 에이전트: client_tasks + assets → 구현 → status: done
       └─→ 대표(유저):    status 확인 → 검증 → verified
```

## 구조

```
_gdd/
├── README.md                        ← 이 파일
├── game_design.yaml                 ← 마스터 GDD (씬/태스크/에셋 전체)
├── rules/                           ← 게임 규칙 (공식, 행동, 시스템 로직)
│   ├── combat.yaml                  ← 전투 공식, CC, 어그로, PvP 규칙
│   ├── progression.yaml             ← 레벨/스킬/경험치/도감 규칙
│   ├── economy.yaml                 ← 골드 유입/유출, 거래, 인플레이션 통제
│   ├── enhancement.yaml             ← 강화/보석/각인/초월 규칙
│   ├── items.yaml                   ← 장비 슬롯, 인벤토리, 내구도 규칙
│   ├── ai_behavior.yaml             ← 몬스터/NPC AI 행동 트리
│   ├── (+ 15개 더: animation, art_style, audio, camera, crafting,
│   │     dungeon, flow, monetization, narrative, pvp,
│   │     quests, social, ui, vfx, world)
│   └── 총 21개 규칙 파일
├── data/                            ← 게임 데이터 시트 (수치 테이블)
│   ├── classes.yaml                 ← 직업 기본스탯, 성장, 전직
│   ├── level_exp_table.yaml         ← 경험치 테이블, 마일스톤, 칭호, 도감
│   ├── items_catalog.yaml           ← 아이템등급, 세트, 소모품, 루트, 원소상성
│   ├── enhancement_tables.yaml      ← 강화확률/비용, 보석, 각인, 초월 수치
│   ├── monsters_and_spawns.yaml     ← 공격패턴, 보스기믹, 스폰, 패스파인딩
│   └── shops_and_economy.yaml       ← NPC상점, 보상 수치, 일일 상한
└── assets/                          ← 에셋 소싱 가이드
    ├── prompts.yaml                 ← AI 이미지 생성 프롬프트 모음
    └── sources.yaml                 ← 에셋 소싱처 + URL
```

### rules/ vs data/ 분리 원칙
- **rules/**: 공식, 행동 로직, 시스템 규칙 (How it works)
- **data/**: 구체적 수치 테이블 (What the values are)
- 밸런스 조정 시 data/ 파일만 수정하면 됨
- 각 rules 파일 헤더에 연관 data 파일 명시됨

## 에이전트 사용법

### 서버 에이전트
```
"game_design.yaml에서 P0_S04_S01 태스크 구현해"
→ CHARACTER_LIST/CREATE/DELETE 패킷 추가
→ status: todo → done 으로 변경
```

### 클라 에이전트
```
"game_design.yaml에서 P1_S01 씬 전체 구현해"
→ TutorialZone 씬 + TutorialManager + 카메라 시스템
→ 필요 에셋 목록 확인 → 없으면 생성
→ status: todo → done
```

### 대표 (유저)
```
"현재 진행 상황 보여줘"
→ game_design.yaml에서 status 집계
→ P0: 2/4 done, P1: 0/5, P2: 0/3, HUD: 0/1
```

## GDD 확장 방법

1. **씬 추가**: phases 배열에 새 항목 추가
2. **규칙 추가**: rules/ 폴더에 YAML 파일 추가
3. **데이터 추가**: data/ 폴더에 YAML 파일 추가 (수치 테이블)
4. **에셋 추가**: 해당 씬의 assets 배열에 추가

## rules/ 파일 예시 (향후 확장)

```yaml
# rules/combat.yaml
damage_formula:
  physical: "(ATK * skill_multiplier - DEF * 0.5) * (1 + crit_bonus)"
  magical: "(MATK * skill_multiplier - MDEF * 0.3) * (1 + crit_bonus)"

crit_rate:
  base: 0.05
  per_luck: 0.001
  cap: 0.60

crit_damage:
  base: 1.5
  per_crit_dmg_stat: 0.01
  cap: 4.0
```

이런 규칙 파일을 만들면 서버 에이전트가 그대로 코드에 반영합니다.
