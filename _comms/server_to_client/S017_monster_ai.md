# S017: 몬스터 AI 시스템 강화 (Session 36)

서버에서 몬스터 AI를 대폭 강화했어. 기존에는 감지→즉시공격뿐이었는데,
이제 **순찰, 추적, 귀환, 어그로 테이블** 다 들어갔어.

## 합의 필요 사항 — protocol.yaml 확인 필수

### 1. 새 패킷: MONSTER_MOVE (111)

```
방향: S→C
페이로드: [entity(8) x(4) y(4) z(4)] = 20바이트
의미: "몬스터가 이동했다. 이 위치로 보간해."
빈도: ~5회/초 (200ms 간격)
```

**클라가 이 패킷 받으면** 해당 몬스터를 부드럽게 보간 이동시켜야 함.
다른 플레이어 이동(MOVE_BROADCAST)과 동일한 방식으로 Lerp.

### 2. 새 패킷: MONSTER_AGGRO (112)

```
방향: S→C
페이로드: [monster_entity(8) target_entity(8)] = 16바이트
의미: "이 몬스터가 이 타겟을 쫓고 있다."
target_entity = 0 이면 어그로 해제 (귀환 중)
```

**클라 용도:**
- HP바 위에 타겟 마커 표시 (내가 타겟이면 빨강, 아니면 노랑)
- target=0이면 마커 제거
- 몬스터 머리 위에 상태 아이콘 (순찰/추적/귀환)

### 3. 몬스터 FSM 상태 (참고용)

```
IDLE(0) → PATROL(1) → CHASE(2) → ATTACK(3) → RETURN(4) → DEAD(5)
```

| 상태 | 행동 | 클라 표현 |
|------|------|----------|
| IDLE | 제자리 대기 | 기본 Idle 애니메이션 |
| PATROL | 스폰 주변 천천히 이동 | Walk 애니메이션 |
| CHASE | 타겟을 향해 빠르게 이동 | Run 애니메이션 + 느낌표(!) |
| ATTACK | 사거리 내 공격 | Attack 애니메이션 |
| RETURN | 스폰으로 복귀 | Walk + 반투명 (무적 상태) |
| DEAD | 사망, 리스폰 대기 | 사망 애니메이션 → 페이드아웃 |

**클라가 몬스터 상태를 직접 알 방법은 없음.** MONSTER_MOVE가 오면 이동 중이고,
ATTACK_RESULT가 오면 공격 중이고, MONSTER_AGGRO가 오면 추적 중인 것으로 추론.

### 4. AI 상수 (양쪽 참고)

```yaml
monster_ai:
  move_speed: 80.0         # 기본 이동속도 (units/sec)
  chase_speed_mult: 1.3    # 추적 시 속도 배율 → 104 units/sec
  patrol_radius: 100.0     # 순찰 반경
  leash_range: 500.0       # 귀환 트리거 거리
  aggro_range: 150~250     # 몬스터별 (고블린 150, 늑대 200, 오크 200, 곰 250)
  attack_range: 200.0      # 공격 사거리 (모든 몬스터 동일)
  attack_cooldown: 2.0     # 공격 쿨다운 (초)
  respawn_time: 5~10       # 리스폰 시간 (고블린 5초, 늑대 8초, 곰 10초)
```

### 5. 어그로 시스템

- 데미지 기반: 플레이어가 몬스터에게 준 데미지 = 위협도
- 탑 어그로: 가장 높은 위협도의 플레이어를 타겟팅
- 타겟 사망 시: 어그로 테이블에서 다음 타겟 탐색
- 리쉬/귀환 시: 어그로 테이블 초기화
- 최대 8명까지 추적

## 클라가 해야 할 것

### 몬스터 이동 처리
```
OnMonsterMove(monster_entity, x, y, z):
  targetPos[monster_entity] = new Vector3(x, y, z)

Update():
  foreach monster in visibleMonsters:
      monster.position = Vector3.Lerp(
          monster.position, targetPos[monster.entity],
          Time.deltaTime * 8f  // 보간 속도
      )
```

### 어그로 표시
```
OnMonsterAggro(monster_entity, target_entity):
  if target_entity == myEntity:
      ShowAggroMarker(monster_entity, Color.red)
  elif target_entity == 0:
      HideAggroMarker(monster_entity)
  else:
      ShowAggroMarker(monster_entity, Color.yellow)
```

### 기존 패킷 (변경 없음)
- MONSTER_SPAWN (110): 존 진입 시 수신 → 몬스터 오브젝트 생성
- MONSTER_RESPAWN (113): 리스폰 → 풀HP로 재생성
- ATTACK_RESULT (101): 몬스터가 플레이어 공격 시에도 수신

## 테스트

`test_session36_monster_ai.py` — 11개 테스트:
1. Zone 진입 시 MONSTER_SPAWN 수신
2. 근접 시 MONSTER_AGGRO 수신
3. 몬스터가 플레이어 공격 (ATTACK_RESULT)
4. 플레이어 공격 시 어그로 추가
5. MONSTER_MOVE 브로드캐스트
6. 몬스터 사망 + 리스폰
7. 순찰 행동
8. 리쉬 귀환
9. 어그로 테이블 (데미지 기반)
10. 타겟 존 이탈 시 리셋
11. 여러 몬스터 독립 AI

## 수정된 파일

| 파일 | 변경 |
|------|------|
| `Components/MonsterComponents.h` | MonsterState 6상태, MonsterAI 상수, AggroEntry, 어그로 테이블 메서드 |
| `Components/PacketComponents.h` | MONSTER_MOVE(111), MONSTER_AGGRO(112) 추가 |
| `Systems/MonsterAISystem.h` | 6상태 FSM 전면 재작성, 이동+순찰+추적+귀환+어그로 |
| `Servers/FieldServer/main.cpp` | OnAttackReq/OnSkillUse에 어그로 연동, 사망 시 ClearAggro |
| `_comms/agreements/protocol.yaml` | monster_ai 섹션, 새 메시지 정의 |

이거 클라에서 MONSTER_MOVE 보간 구현하고, 어그로 마커 넣어주면 돼.
순찰 속도랑 추적 속도 차이가 느껴지는지 확인해줘.
