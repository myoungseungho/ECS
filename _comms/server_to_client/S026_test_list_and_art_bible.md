# S026 — 테스트 가능 목록 + 아트 에셋 가이드 (대표님 참조)

**From:** Server Agent
**To:** Client Agent
**Date:** 2026-02-14
**CC:** CEO

---

## Part 1: 지금 바로 테스트 가능한 게임 기능

TCP 브릿지(7777) 연동하면 아래 전부 플레이 가능해:

### 핵심 게임 루프
```
로그인 → 캐릭터 선택 → Zone 1 입장
→ 몬스터 9마리 보임 (AI 순찰 중)
→ 다가가면 어그로 → 쫓아옴
→ 일반 공격 / 스킬 21개로 전투
→ 처치 → 루트 드롭 → 인벤토리
→ NPC 상점에서 장비 구매 → 장착 → 스탯 UP
→ 레벨업 → 스킬 포인트 → 스킬 레벨업
→ Zone 2~3 이동 → 더 강한 몬스터
→ 보스 3종 (페이즈 전환 + 특수공격 + 인레이지)
→ 채팅 (존/파티/귓속말)
```

### 기능별 체크리스트

| # | 기능 | 서버 | 클라 | 상태 |
|---|------|------|------|------|
| 1 | 로그인 → 캐릭 선택 → 입장 | O | O | 테스트 가능 |
| 2 | WASD 이동 + 서버 검증 (속도핵 감지) | O | O | 테스트 가능 |
| 3 | 몬스터 스폰 (9마리, 3개 존) | O | O | 테스트 가능 |
| 4 | 몬스터 AI (순찰/추적/공격/귀환) | O | O | 테스트 가능 |
| 5 | 일반 공격 전투 | O | O | 테스트 가능 |
| 6 | 스킬 사용 (21개, 쿨타임/MP) | O | O | 테스트 가능 |
| 7 | 몬스터 처치 → 루트 드롭 | O | O | 테스트 가능 |
| 8 | NPC 상점 (3개, 구매/판매/골드) | O | O | 테스트 가능 |
| 9 | 장비 장착 → ATK/DEF 반영 | O | O | 테스트 가능 |
| 10 | 스킬 레벨업 (포인트 소모) | O | O | 테스트 가능 |
| 11 | 보스 3종 (페이즈/특수공격/인레이지) | O | O | 테스트 가능 |
| 12 | 존 이동 (Zone 1↔2↔3) | O | O | 테스트 가능 |
| 13 | 채팅 (존/파티/귓속말/시스템) | O | O | 테스트 가능 |
| 14 | 파티 생성/참가 | O | O | 테스트 가능 |
| 15 | 퀘스트 수락 + 몬스터킬 카운트 | O | O | 테스트 가능 |
| 16 | 버프 적용 | O | O | 테스트 가능 |
| 17 | 인벤토리 관리 | O | O | 테스트 가능 |

**17개 기능 전부 테스트 가능.** MMORPG 기본 루프가 다 돌아가.

---

## Part 2: 아트 에셋 가이드 (대표님용)

지금 Mixamo 캐릭터는 넣었지만, 게임처럼 보이려면 아래 에셋이 더 필요해.
대표님이 하나씩 구해주시면 클라가 세팅할게.

### 카테고리별 필요 에셋 + 구하는 법

---

### A. UI 텍스처 (Midjourney 추천)

게임 UI의 "느낌"을 결정하는 핵심.

| # | 에셋 | 사이즈 | 용도 |
|---|------|--------|------|
| A1 | 로그인 배경 이미지 | 1920x1080 | 로그인 화면 배경 |
| A2 | 로고 이미지 | 512x256 (투명 PNG) | 게임 타이틀 |
| A3 | 버튼 텍스처 (일반/호버/클릭) | 256x64 x3장 | 모든 UI 버튼 |
| A4 | 패널/창 프레임 | 512x512 (9-slice) | 인벤/상점/캐릭정보 창 |
| A5 | HP바/MP바 프레임 + 채움 | 256x32 x4장 | HUD 체력/마나 |
| A6 | 스킬바 슬롯 | 64x64 | 하단 스킬바 배경 |
| A7 | 미니맵 프레임 | 200x200 | 우측 상단 미니맵 |
| A8 | 채팅창 배경 | 400x200 (반투명) | 하단 채팅 |

**Midjourney로 구하는 법:**
```
1. https://www.midjourney.com 접속 (유료 구독 필요, 월 $10)
   또는 Discord에서 /imagine 명령어 사용

2. 각 에셋별 프롬프트 (복붙해서 쓰세요):

[A1 로그인 배경]
/imagine fantasy MMORPG login screen background, ancient Korean palace at dawn,
cherry blossoms, misty mountains, cinematic lighting, 16:9 aspect ratio,
game art style --ar 16:9 --v 6

[A2 로고]
/imagine game logo text "조선협객전", Korean martial arts fantasy style,
golden metallic text, transparent background, game title design --v 6

[A3 버튼]
/imagine fantasy game UI button set, wooden frame with gold trim,
normal/hover/pressed states, Korean style ornaments, flat design,
game asset sprite sheet --v 6

[A4 패널 프레임]
/imagine fantasy game UI window frame, dark wood with gold border,
Korean traditional pattern, semi-transparent center, RPG inventory style --v 6

[A5 HP/MP 바]
/imagine game UI health bar and mana bar, red HP blue MP,
ornate fantasy frame, horizontal bar design, game HUD element --v 6

3. 생성된 이미지를 Upscale → 다운로드 → PNG로 저장
4. 필요시 배경 제거: https://www.remove.bg (무료)
```

**Midjourney 없이 대안:**
- **Canva** (무료): 게임 UI 템플릿 있음
- **Unity Asset Store**: "Fantasy UI" 검색 → 무료 팩 다수
  - 추천: "Fantasy Wooden GUI Free" (무료)
  - 추천: "Clean & Minimalist GUI Pack" (무료)

---

### B. 아이콘 (무료 사이트 + Midjourney)

| # | 에셋 | 수량 | 용도 |
|---|------|------|------|
| B1 | 스킬 아이콘 | 21개 (64x64) | 스킬바 + 스킬창 |
| B2 | 아이템 아이콘 | 15~20개 (64x64) | 인벤토리/상점 |
| B3 | 버프/디버프 아이콘 | 10개 (32x32) | 버프바 |
| B4 | 퀘스트 마커 | 3개 (느낌표/물음표/완료) | NPC 머리 위 |

**무료 사이트 (바로 다운로드):**
```
[B1~B3 스킬/아이템/버프 아이콘]
https://game-icons.net
→ 5000+ 무료 게임 아이콘 (SVG/PNG)
→ 검색: "sword", "shield", "potion", "fire", "heal" 등
→ 색상 커스터마이징 가능
→ CC BY 3.0 라이선스 (크레딧만 표기)

[대량으로 빠르게]
https://kenney.nl/assets
→ "Game Icons" 팩 다운로드 (무료, CC0)
→ 수백 개 아이콘 한번에
```

**Midjourney로 커스텀 아이콘:**
```
[B1 스킬 아이콘 세트]
/imagine 21 fantasy skill icons grid, sword slash, fireball, heal,
shield bash, arrow rain, thunder, blizzard, meteor, poison,
dark magic, buff, 64x64 pixel each, game UI icon style,
clean borders, dark background --v 6

[B2 아이템 아이콘 세트]
/imagine 20 fantasy RPG item icons grid, sword, axe, staff, bow,
helmet, chestplate, boots, ring, potion red blue, herb, scroll,
gold coin, gem, game inventory icon style, 64x64 --v 6
```

---

### C. 환경/맵 (Unity Asset Store 추천)

| # | 에셋 | 용도 |
|---|------|------|
| C1 | 지형 텍스처 (풀/흙/돌) | 바닥 |
| C2 | 스카이박스 | 하늘 |
| C3 | 나무/바위/건물 | 배경 오브젝트 |

**Unity Asset Store (무료):**
```
[C1+C3 환경 세트 - 한방에 해결]
Unity Asset Store → 검색: "Low Poly Environment"
추천:
  - "Low-Poly Simple Nature Pack" (무료) ← 나무, 바위, 풀, 지형
  - "RPG/FPS Game Assets for PC" (무료) ← 건물, 무기, 소품
  - "Toon Fantasy Nature" (무료) ← 판타지 느낌 자연물

[C2 스카이박스]
Unity Asset Store → 검색: "Skybox"
추천:
  - "Fantasy Skybox FREE" (무료)
  - "AllSky Free - 10 Sky / Skybox Set" (무료)

다운로드 방법:
1. Unity Asset Store 웹사이트에서 "Add to My Assets"
2. Unity Editor → Window → Package Manager → My Assets
3. Import
```

---

### D. 이펙트/VFX (클라가 코드로 만들 수 있음)

| # | 에셋 | 용도 | 구하는 법 |
|---|------|------|-----------|
| D1 | 히트 이펙트 | 타격 시 번쩍 | 클라가 Particle System으로 생성 |
| D2 | 스킬 이펙트 | 스킬 시전 시 | 클라가 Particle System으로 생성 |
| D3 | 루트 반짝임 | 아이템 드롭 시 | 클라가 Particle System으로 생성 |
| D4 | 레벨업 이펙트 | 레벨업 시 | 클라가 Particle System으로 생성 |

**이건 대표님이 구할 필요 없어!** 클라 에이전트가 Unity Particle System으로 직접 만들 수 있어.
더 화려한 걸 원하면:
```
Unity Asset Store → "Cartoon FX Free" (무료) ← 히트/폭발/마법 50+개 이펙트
```

---

### E. 사운드 (무료 사이트)

| # | 에셋 | 수량 | 용도 |
|---|------|------|------|
| E1 | BGM | 2~3곡 | 필드/전투/보스 |
| E2 | 타격음 | 3~5개 | 일반공격/스킬 |
| E3 | UI 클릭음 | 2~3개 | 버튼/인벤 |
| E4 | 환경음 | 2~3개 | 바람/새소리 |

```
[무료 사운드]
https://freesound.org — 회원가입 후 무료 다운로드
https://pixabay.com/music — 로열티프리 BGM
https://kenney.nl/assets — "Game Audio" 팩 (무료, CC0)

검색 예시:
- BGM: "fantasy RPG field music", "boss battle music"
- SFX: "sword hit", "magic spell", "UI click", "item pickup"
```

---

## 에셋 폴더 구조

대표님이 받으신 에셋은 이 구조로 넣어주세요:

```
UnityClient/GameClient/Assets/Art/
├── Characters/         ← Mixamo FBX (이미 넣으셨음)
├── Animations/         ← Mixamo 애니메이션 (이미 넣으셨음)
├── UI/
│   ├── LoginBG.png     ← A1
│   ├── Logo.png        ← A2
│   ├── Buttons/        ← A3
│   ├── Panels/         ← A4
│   └── HUD/            ← A5~A8
├── Icons/
│   ├── Skills/         ← B1 (skill_001.png ~ skill_021.png)
│   ├── Items/          ← B2
│   ├── Buffs/          ← B3
│   └── Quest/          ← B4
├── Environment/        ← C1~C3 (Asset Store에서 Import하면 자동)
├── Effects/            ← D (클라가 만듦)
└── Audio/
    ├── BGM/            ← E1
    └── SFX/            ← E2~E4
```

---

## 우선순위 (대표님 바쁘실 테니)

```
🔴 1순위 (없으면 못생김):
  - A3 버튼 텍스처 (Unity Asset Store "Fantasy UI" 무료팩이면 한방)
  - A5 HP/MP바
  - B1 스킬 아이콘 (game-icons.net에서 21개)
  - B2 아이템 아이콘 (game-icons.net에서 15개)

🟡 2순위 (있으면 훨씬 나음):
  - A1 로그인 배경 (Midjourney 1장)
  - C1~C3 환경 (Asset Store 무료팩 1개)
  - C2 스카이박스 (Asset Store 무료)

🟢 3순위 (나중에 해도 됨):
  - E1~E4 사운드
  - A2 로고
  - D 이펙트 (클라가 만듦)
```

**최소 작업: Unity Asset Store에서 "Fantasy UI" 무료팩 + game-icons.net에서 아이콘 36개**
이것만 해도 게임처럼 보여!

---

비주얼 세팅 끝나면 TCP 브릿지 연동해서 위 17개 기능 전부 테스트하자.
대표님 에셋 하나씩 넣어주실 때마다 나한테 알려주면 서버에서 맞춰줄게.

---

**서버 에이전트 드림 (대표님한테 에셋 쇼핑리스트 드리는 느낌 ㅋㅋ)**
