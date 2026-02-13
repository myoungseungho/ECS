# S018: 데이터 드리븐 + 핫리로드 시스템 (Session 37)

서버에서 하드코딩 상수들을 전부 데이터 파일로 뺐어.
JSON/CSV에서 로드하고, **서버 재시작 없이 런타임에 값 바꿀 수 있는 뼈대** 완성.

## 합의 필요 사항 — protocol.yaml 확인 필수

### 1. 새 패킷: ADMIN_RELOAD (280)

```
방향: C→S
페이로드: [name_len(1) name(N)]
의미: "이 설정을 파일에서 다시 읽어줘"
name_len=0 이면 전체 리로드
```

### 2. 새 패킷: ADMIN_RELOAD_RESULT (281)

```
방향: S→C
페이로드: [result(1) version(4) reload_count(4) name_len(1) name(N)]
result: 1=성공, 0=실패
version: ConfigLoader 내부 버전 (리로드마다 증가)
reload_count: 총 리로드 횟수
```

### 3. 새 패킷: ADMIN_GET_CONFIG (282)

```
방향: C→S
페이로드: [name_len(1) name(N) key_len(1) key(N)]
의미: "이 설정의 이 키 값 알려줘"
예: name="monster_ai", key="leash_range" → "500"
```

### 4. 새 패킷: ADMIN_CONFIG_RESP (283)

```
방향: S→C
페이로드: [found(1) value_len(2) value(N)]
found: 1=찾음, 0=못찾음
value: 문자열 값 (예: "500", "1.3", "200.0")
```

### 5. 데이터 파일 구조

```
data/
├── monster_ai.json        # 몬스터 AI 상수 (leash_range, chase_speed_mult 등)
├── movement_rules.json    # 이동 검증 상수 (base_speed, tolerance 등)
├── monster_spawns.csv     # 몬스터 스폰 테이블 (9마리)
├── zone_bounds.csv        # 존 경계 데이터 (3개 존)
└── server.json            # 서버 설정 (tick_rate, max_players 등)
```

### 6. GameConfig 구조 (서버 내부)

```
GameConfig (런타임 캐시)
├── monster_ai
│   ├── move_speed: 80.0
│   ├── patrol_radius: 100.0
│   ├── leash_range: 500.0        ← data/monster_ai.json에서 로드
│   ├── chase_speed_mult: 1.3     ← 핫리로드 가능
│   ├── return_heal_rate: 0.1
│   ├── attack_range: 200.0
│   └── ...
├── movement
│   ├── base_speed: 200.0
│   ├── sprint_multiplier: 1.5
│   ├── tolerance: 1.5
│   └── ...
├── version: (리로드마다 증가)
└── reload_count: (총 리로드 횟수)
```

### 7. 핫리로드 흐름

```
1. 기획자가 data/monster_ai.json 수정 (예: leash_range: 500 → 300)
2. 클라/어드민 툴에서 ADMIN_RELOAD 패킷 전송 (name="monster_ai")
3. 서버: 파일 다시 읽기 → GameConfig 갱신 → version++
4. 다음 틱부터 새 값 적용 (몬스터가 300 거리에서 귀환)
5. ADMIN_RELOAD_RESULT로 성공/실패 응답
```

## 클라가 해야 할 것

### 어드민 UI (선택)
- 설정 조회: ADMIN_GET_CONFIG("monster_ai", "leash_range") → 현재 값 표시
- 설정 리로드: ADMIN_RELOAD("monster_ai") → 결과 확인

### 기존 패킷 (변경 없음)
- CONFIG_QUERY(82) / CONFIG_RESP(83): 기존 설정 조회 (그대로 동작)

## 테스트

`test_session37_data_driven.py` — 12개 테스트:
1. CONFIG_QUERY로 monster_ai 조회
2. ADMIN_GET_CONFIG으로 chase_speed_mult 조회
3. ADMIN_GET_CONFIG으로 movement base_speed 조회
4. 존재하지 않는 키 조회 → found=0
5. ADMIN_RELOAD 단일 설정 리로드
6. ADMIN_RELOAD 전체 리로드
7. 핫리로드: JSON 수정 → 리로드 → 값 변경 확인
8. 존재하지 않는 설정 리로드 실패
9. 리로드마다 version 증가 확인
10. monster_spawns.csv 로드 확인
11. zone_bounds.csv 로드 확인
12. movement_rules 핫리로드

## 수정된 파일

| 파일 | 변경 |
|------|------|
| `Core/ConfigLoader.h` | Session 37: Reload(), ReloadAll(), 소스 추적, 버전 카운터 |
| `Core/GameConfig.h` | 신규: 런타임 설정 캐시 (MonsterAIConfig, MovementConfig) |
| `Components/PacketComponents.h` | ADMIN_RELOAD(280)~ADMIN_CONFIG_RESP(283) 추가 |
| `Systems/MonsterAISystem.h` | MonsterAI:: → GetAIConfig(). 전환 (데이터 드리븐) |
| `Servers/FieldServer/main.cpp` | 파일 기반 config 로드 + ADMIN 핸들러 + GameConfig 초기화 |
| `data/*.json, data/*.csv` | 5개 데이터 파일 신규 |
| `_comms/agreements/protocol.yaml` | admin 섹션 + 새 메시지 정의 |

이제 기획자가 CSV/JSON 수정 → ADMIN_RELOAD → 서버 무중단 밸런싱 가능해.
클라에서 어드민 도구 만들면 편해지겠지만, 필수는 아니야.
