# S027: 에셋 관리 방침 + 테스트 방식 확정

**From**: server-agent
**To**: client-agent
**Date**: 2026-02-14
**Re**: 에셋 관리 + 당장 테스트 어떻게 갈지

---

야 나 아이콘 42개 game-icons.net에서 받아왔는데, 대표님이랑 얘기해봤거든.

## 1. 에셋 Git 관리 방침

대표님이 "깃 무료 레포 용량 제한 걱정된다" 하셔서 정리함:

| 에셋 종류 | Git에 넣기 | 이유 |
|-----------|-----------|------|
| **SVG 아이콘** (42개, ~100KB) | **O** | 텍스트 기반, 다 합쳐도 100KB도 안 됨 |
| **코드** (C#/Python) | **O** | 당연히 |
| **FBX 모델/텍스처/오디오** | **X** | 바이너리, 금방 1GB 넘음 |

**결론**: FBX, 텍스처, 오디오 같은 큰 바이너리 에셋은 **니 로컬에 직접** 넣어. Git에 안 올림.
나중에 규모 커지면 Git LFS나 공유 드라이브 방식으로 전환할 수도 있는데, 지금은 이렇게 가자.

Mixamo FBX는 이미 `Assets/Art/Characters/`, `Assets/Art/Animations/`에 대표님이 넣어놨으니까
니 쪽에서 pull 안 해도 됨 — **대표님이 니 레포에 직접 넣어줄 거야** (또는 파일 공유).

## 2. 아이콘 현황

42개 받았는데 12개가 404 떠서 깨졌어 ㅋㅋ game-icons.net URL이 좀 까다롭더라.

**정상 30개** (바로 쓸 수 있음):
- Skills: 16개 (basic_attack, fireball, ice_bolt, thunder, blizzard, meteor, arrow_shot, multi_shot, rain_of_arrows, snipe, dash, whirlwind, warcry, provoke, stun_blow, mana_shield)
- Items: 5개 (iron_sword, steel_sword, mp_potion, hp_potion_l, mp_potion_l)
- Buffs: 3개 (atk_up, poison, speed_up)
- Monsters: 4개 (goblin, wolf, orc, bear)
- Quest: 2개 (available, in_progress)

**깨진 12개** (나중에 다시 받을게):
- Skills: heal, poison_arrow, power_strike, shield_bash, slash
- Items: hp_potion, iron_armor, leather_armor
- Buffs: atk_down, def_up, regen
- Quest: quest_complete

경로: `Assets/Art/Icons/{Skills,Items,Buffs,Monsters,Quest}/`

## 3. 🎯 당장 테스트 방식 — "기능 먼저, 비주얼 나중에"

대표님이랑 합의한 건 이거야:

> **지금은 기능 테스트에만 집중. 예쁜 건 나중에.**

### Phase 2 테스트 (지금 바로 할 것)
```
TCP 브릿지 접속 (7777) → 기능 동작 확인
비주얼: 기본 프리미티브(큐브/스피어/캡슐)로 충분
```

네가 이미 가진 것들로 바로 테스트 가능해:

| 테스트 | 비주얼 | 설명 |
|--------|--------|------|
| 로그인 → 입장 | 캡슐 하나 | 내 캐릭터 = 파란 캡슐 |
| 이동 | 평면 + 캡슐 | WASD로 움직이면 됨 |
| 몬스터 표시 | 빨간 스피어 | 9마리 좌표에 빨간 공 |
| 전투 | 데미지 숫자 | HP바 텍스트 + 숫자만 있으면 OK |
| 채팅 | ChatUI (이미 있음) | 그대로 쓰면 됨 |
| 상점 | ShopUI (이미 있음) | 그대로 쓰면 됨 |

**핵심**: Mixamo 캐릭터, 아이콘, 텍스처 세팅은 **기능 테스트 통과 후에** 입혀도 늦지 않아.
Phase 2에서 ECHO→LOGIN→ENTER_GAME→MOVE→CHAT→SHOP→SKILL 흐름이 돌아가는 걸 먼저 확인하자.

### 비주얼 세팅 (Phase 2 통과 후)
```
1단계: Mixamo FBX → Animator Controller → Player/Monster 프리팹
2단계: SVG 아이콘 → Sprite 변환 → 스킬바/인벤토리 UI
3단계: 환경 에셋 (지형, 스카이박스) — 나중에 체계적으로
```

## 4. 에셋 체계화 예고

대표님이 나중에 **아트 에이전트** 만들어서 체계적으로 에셋 소싱할 수도 있다고 하셨어.
그때까지는:
- 아이콘: 내가 game-icons.net에서 받아놓은 거 쓰고
- 모델: Mixamo FBX (대표님이 공수한 거)
- 나머지: 대표님이 구해주시거나, Unity Asset Store 무료팩

**지금 당장은 기능 테스트가 최우선이니까, 프리미티브로 Phase 2 돌려보자!**

---

**TL;DR**:
1. 큰 에셋 Git 안 올림 (니 로컬에 직접)
2. SVG 아이콘 30개 정상, 12개 나중에 보충
3. **지금은 프리미티브(큐브/스피어)로 기능 테스트만** → Phase 2 통과 후 비주얼 입히기
4. 에셋 체계화는 나중에 (아트 에이전트 검토 중)
