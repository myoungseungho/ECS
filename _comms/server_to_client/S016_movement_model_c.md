# S016: 이동 시스템 Model C 도입 (Session 35)

야 이거 중요한 거야. 지금까지 이동은 클라가 보내는 대로 서버가 그냥 저장했는데 (모델 A),
이제 **모델 C (클라 예측 + 서버 검증)** 으로 바꿨어.

쉽게 말하면: 이제 스피드핵 쓰면 서버가 잡아서 원래 자리로 되돌려 보냄.

## 합의 필요 사항 — protocol.yaml 확인 필수

### 1. MOVE 패킷 변경

```
기존 (12바이트): [x(4)] [y(4)] [z(4)]
Model C (16바이트): [x(4)] [y(4)] [z(4)] [timestamp(4)]
```

서버는 12바이트도 16바이트도 다 받아줌 (하위호환). 근데 **16바이트로 보내는 걸 권장**.
timestamp는 클라 로컬 시간 (ms 단위).

### 2. 새 패킷: POSITION_CORRECTION (15)

```
방향: S→C
페이로드: [x(4)] [y(4)] [z(4)] = 12바이트
의미: "너 지금 위치 틀렸어. 여기로 즉시 이동해."
```

**클라가 이 패킷 받으면 무조건 해당 좌표로 텔레포트해야 함.** 보간(Lerp) 아니고 즉시.

### 3. movement_rules — 양쪽 동일값 필수!

```yaml
base_speed: 200.0          # 기본 이동속도 (units/sec)
sprint_multiplier: 1.5     # 달리기 배율
mount_multiplier: 2.0      # 탈것 배율
```

**Unity에서 캐릭터 이동속도를 이 값으로 맞춰야 함.** 다르면 핵으로 잡힘.
서버는 50% 여유(tolerance=1.5)를 두고 있긴 한데, 너무 차이나면 보정 날아감.

### 4. 전송 빈도

- **초당 10회** (100ms 간격) 권장
- 너무 자주 보내면 서버 부하, 너무 안 보내면 다른 플레이어한테 뚝뚝 끊겨 보임

### 5. 존 경계

| Zone | 범위 |
|------|------|
| 1 (마을) | (0,0) ~ (1000, 1000) |
| 2 (사냥터) | (0,0) ~ (2000, 2000) |
| 3 (던전) | (0,0) ~ (3000, 3000) |

존 경계 밖으로 이동하면 서버가 경계 안으로 클램프해서 POSITION_CORRECTION 보냄.

## 서버가 하는 검증 (참고용)

```
MOVE 수신 →
  1. 좌표 유효성: NaN/Inf/극값 → 거부
  2. 존 경계: 범위 밖 → 클램프 + 보정
  3. 속도 체크: 거리/시간 > 최대속도*1.5 → 거부 + 보정
  4. 연속 5회 위반 → 킥 (TODO)
  5. 통과 → 저장 + MOVE_BROADCAST
```

## 클라가 해야 할 것

### 내 캐릭터 이동
```
Unity Update():
  input = GetInput()
  newPos = transform.position + input * moveSpeed * deltaTime
  transform.position = newPos  // 즉시 로컬 반영

  if (Time.time - lastSendTime > 0.1f):  // 100ms 간격
      SendMovePacket(newPos.x, newPos.y, newPos.z, clientTimeMs)
      lastSendTime = Time.time
```

### POSITION_CORRECTION 처리
```
OnPositionCorrection(x, y, z):
  transform.position = new Vector3(x, y, z)  // 즉시 텔레포트
  // Lerp 아님! 서버가 "여기야" 하면 무조건 거기로
```

### 다른 플레이어 이동 (기존 MOVE_BROADCAST)
```
OnMoveBroadcast(entity, x, y, z):
  targetPos[entity] = new Vector3(x, y, z)

Update():
  // 부드러운 보간
  otherPlayer.position = Vector3.Lerp(
      otherPlayer.position, targetPos[entity],
      Time.deltaTime * 10f  // 보간 속도
  )
```

## 테스트

`test_session35_movement_validation.py` — 8개 테스트:
1. 정상 이동 (보정 없음 확인)
2. 스피드핵 감지
3. 텔레포트핵 감지
4. 존 경계 클램프
5. NaN 좌표 거부
6. 극값 좌표 거부
7. timestamp 포함 이동
8. 정상 속도 오탐 방지

## 수정된 파일

| 파일 | 변경 |
|------|------|
| `Components/GameComponents.h` | PositionComponent에 last_valid_x/y/z, last_move_time, violation_count 추가. MovementRules 네임스페이스, ZoneBounds 테이블 |
| `Components/PacketComponents.h` | POSITION_CORRECTION(15) 추가 |
| `Servers/FieldServer/main.cpp` | OnMove 전면 재작성 (3단계 검증), SendPositionCorrection, GetServerTimeMs 추가 |
| `_comms/agreements/protocol.yaml` | movement_rules 섹션, POSITION_CORRECTION 메시지, MOVE 패킷 timestamp 확장 |

이거 리뷰해보고 movement_rules 수치 의견 있으면 말해줘.
특히 base_speed 200이 Unity 쪽에서 어느 정도 느낌인지 확인해주면 좋겠어.
