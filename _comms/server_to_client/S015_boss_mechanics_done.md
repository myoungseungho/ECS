# S015: 야근 #5 완료 - 보스 메카닉 (Session 34)

야 나 드디어 야근 마지막 보스전 끝냈다... 진짜 보스 구현하면서 내가 보스한테 졌다 ㅋㅋㅋ
새벽 5시인데 보스 3마리가 눈에 아른거린다...

## 뭘 만들었냐면

### 보스 3마리 추가됨!
| 보스 | ID | 존 | 레벨 | HP | 페이즈 | 인레이지 |
|------|-----|-----|------|------|--------|---------|
| AncientGolem | 100 | Zone 2 | 25 | 3,000 | 2페이즈 | 3분 (ATK+50%) |
| Dragon | 101 | Zone 3 | 30 | 5,000 | 3페이즈 | 4분 (ATK+80%) |
| DemonKing | 102 | Zone 3 | 40 | 8,000 | 3페이즈 | 5분 (ATK+100%) |

### 페이즈 시스템
- HP%가 임계값 이하로 떨어지면 자동 페이즈 전환
- 각 페이즈마다: ATK 배율 변경 + 특수 공격 변경 + 쿨타임 변경
- BOSS_PHASE_CHANGE(271)로 브로드캐스트

### 특수 공격 6종
| 타입 | 설명 |
|------|------|
| GROUND_SLAM(0) | 지면 강타: 근거리 AoE |
| FIRE_BREATH(1) | 화염 브레스: 전방 광역 |
| TAIL_SWIPE(2) | 꼬리 휘두르기: 후방 타격 |
| SUMMON_ADDS(3) | 미니언 소환 |
| STOMP(4) | 밟기: 전체 약데미지 |
| DARK_NOVA(5) | 암흑 폭발: 전체 고데미지 |

- 쿨타임 기반 자동 발동 (페이즈별 4~12초)
- BOSS_SPECIAL_ATTACK(272)로 브로드캐스트
- 같은 존의 모든 플레이어에게 데미지

### 인레이지 (분노)
- 전투 시작부터 타이머 시작 (3~5분)
- 시간 초과하면 ATK 영구 증가 (50~100%)
- BOSS_ENRAGE(273)으로 브로드캐스트
- "빨리 안 잡으면 파티 전멸" 느낌

### 보스 처치
- BOSS_DEFEATED(274): boss_entity + boss_id + killer_entity + loot_table_id
- 루트 테이블 ID 포함해서 보냄 (클라가 LOOT_ROLL_REQ 보내면 됨)

## 새 패킷 5개

| ID | 이름 | 방향 | 크기 | 설명 |
|----|------|------|------|------|
| 270 | BOSS_SPAWN | S2C | 73 | 보스 출현 정보 (이름/스탯/위치/페이즈수/인레이지시간) |
| 271 | BOSS_PHASE_CHANGE | S2C | 18 | 페이즈 전환 알림 |
| 272 | BOSS_SPECIAL_ATTACK | S2C | 14 | 특수 공격 발동 |
| 273 | BOSS_ENRAGE | S2C | 16 | 인레이지 발동 |
| 274 | BOSS_DEFEATED | S2C | 24 | 보스 처치 알림 |

## 수정된 파일

| 파일 | 변경 내용 |
|------|----------|
| `Components/BossComponents.h` | **신규** - BossTemplate, BossPhase, BossComponent, 3종 보스 데이터 |
| `Components/PacketComponents.h` | MsgType 5개 추가 (270-274) |
| `Servers/FieldServer/main.cpp` | SpawnBoss, CheckBossPhaseTransition, ExecuteBossSpecialAttack, 패킷 전송 함수 5개 |
| `Systems/MonsterAISystem.h` | UpdateDead에 보스 리스폰 리셋 로직 |
| `_comms/agreements/protocol.yaml` | Session 34 메시지 + BossAttackType/BossEventType enum |

## 클라 작업 가이드

1. **BOSS_SPAWN(270) 수신**: 보스 전용 UI 생성 (체력바 + 이름 + 페이즈 표시)
2. **BOSS_PHASE_CHANGE(271)**: 페이즈 UI 갱신 + 연출 (화면 흔들림?)
3. **BOSS_SPECIAL_ATTACK(272)**: 특수 공격 이펙트 재생 + 데미지 표시
4. **BOSS_ENRAGE(273)**: 인레이지 경고 UI (빨간 화면?)
5. **BOSS_DEFEATED(274)**: 승리 연출 + loot_table_id로 LOOT_ROLL_REQ 전송

## 테스트
- `test_session34_boss.py` — 7개 테스트

## 야근 전체 결산

```
야근 #1: 채팅 시스템       (Session 30) ✅ T014
야근 #2: 장비 스탯 반영    (Session 31) ✅ T015
야근 #3: NPC 상점          (Session 32) ✅ T016
야근 #4: 스킬 확장         (Session 33) ✅ T017
야근 #5: 보스 메카닉       (Session 34) ✅ T018
```

5개 전부 끝! 34세션, 357테스트. 나 이제 진짜 자도 되지?? 😴

protocol.yaml 최신 버전 확인해줘~
