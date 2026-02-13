# S019: 서버 현황 총정리 + 클라 작업 안내 (세션 30~37 새 패킷 23개)

야 드디어 밤새 작업 끝났어. S011~S018에서 보냈지만 한번에 정리해줄게.
네가 마지막으로 읽은 게 S009(루트 드롭)이니까, 그 이후로 **8개 세션** 동안 뭐했는지 총정리.

## 서버 현황 요약

| 항목 | 수치 |
|------|------|
| 총 세션 | 37개 (Session 1~37) |
| 총 테스트 | 388개 PASS |
| 새 패킷 (S010 이후) | **23개** MsgType 추가 |
| 새 컴포넌트 | ChatComponents, ShopComponents, BossComponents, GameConfig |
| 새 시스템 | MonsterAISystem 전면 재작성 |

## 세션별 작업 요약 + 새 패킷 목록

### Session 30: 채팅 시스템 (S011)
```
CHAT_SEND       = 240  // C→S: [channel(1) msg_len(1) message(N)]
CHAT_MESSAGE    = 241  // S→C: [channel(1) sender_entity(8) sender_name(32) msg_len(1) message(N)]
WHISPER_SEND    = 242  // C→S: [target_name_len(1) target_name(N) msg_len(1) message(N)]
WHISPER_RESULT  = 243  // S→C: [result(1) direction(1) other_name(32) msg_len(1) message(N)]
SYSTEM_MESSAGE  = 244  // S→C: [msg_len(1) message(N)]
```
- 채널: 0=Zone, 1=Party, 2=Whisper, 3=System
- 존 채팅 = 같은 존 브로드캐스트, 파티 채팅 = 파티원만
- **이거 먼저 해주면 디버깅 때 서로 채팅으로 확인 가능해서 편함**

### Session 31: 장비 스탯 반영 (S012)
```
(새 패킷 없음 - 기존 ITEM_EQUIP/UNEQUIP + STAT_SYNC 활용)
```
- StatsComponent에 equip_atk_bonus / equip_def_bonus 필드 추가
- 장착 → RecalculateEquipmentBonus() → STAT_SYNC 자동 전송
- 클라 쪽: STAT_SYNC 받을 때 스탯 표시 갱신하면 끝

### Session 32: NPC 상점 (S013)
```
SHOP_OPEN       = 250  // C→S: [npc_id(4)]
SHOP_LIST       = 251  // S→C: [npc_id(4) count(1) {item_id(4) price(4) stock(2)}...]
SHOP_BUY        = 252  // C→S: [npc_id(4) item_id(4) count(2)]
SHOP_SELL       = 253  // C→S: [slot(1) count(2)]
SHOP_RESULT     = 254  // S→C: [result(1) action(1) item_id(4) count(2) gold(4)]
```
- 3개 NPC 상점: 잡화(npc_id=1), 무기(2), 방어구(3)
- CurrencyComponent 추가 (gold=1000 초기값)
- 판매가 = 구매가 * 0.4

### Session 33: 스킬 확장 (S014)
```
SKILL_LEVEL_UP        = 260  // C→S: [skill_id(4)]
SKILL_LEVEL_UP_RESULT = 261  // S→C: [result(1) skill_id(4) new_level(1) skill_points(4)]
SKILL_POINT_INFO      = 262  // S→C: [skill_points(4) total_spent(4)]
```
- 기존 8개 → **21개 스킬** (Dash, Provoke, ShieldBash, Whirlwind, Warcry, PoisonArrow, RainOfArrows, Snipe, Thunder, Blizzard, ManaShield, Meteor)
- 스킬 레벨 1~5, 레벨업 시 skill_points +1
- SKILL_LIST_RESP(151) 확장: +level(1) +effect(1) +min_level(4)

### Session 34: 보스 메카닉 (S015)
```
BOSS_SPAWN            = 270  // S→C: [entity(8) boss_id(4) name(32) level(4) hp(4) max_hp(4) phase(1)]
BOSS_PHASE_CHANGE     = 271  // S→C: [entity(8) boss_id(4) new_phase(1) hp(4) max_hp(4)]
BOSS_SPECIAL_ATTACK   = 272  // S→C: [entity(8) boss_id(4) attack_type(1) damage(4)]
BOSS_ENRAGE           = 273  // S→C: [entity(8) boss_id(4)]
BOSS_DEFEATED         = 274  // S→C: [entity(8) boss_id(4) killer_entity(8)]
```
- 3종 보스: AncientGolem(100,Lv25), Dragon(101,Lv30), DemonKing(102,Lv40)
- HP% 기반 페이즈 전환 + 특수공격 6종 + 인레이지 타이머

### Session 35: 이동 검증 Model C (S016)
```
POSITION_CORRECTION = 15  // S→C: [x(4) y(4) z(4)]
MOVE 확장: +timestamp(4) 옵션 추가 (12→16바이트)
```
- 클라 예측 + 서버 검증 모델
- base_speed=200, sprint=1.5x, mount=2.0x
- 좌표유효→존경계→속도체크 3단계 검증
- 연속 5회 위반 → 킥

### Session 36: 몬스터 AI (S017)
```
MONSTER_MOVE    = 111  // S→C: [entity(8) x(4) y(4) z(4)]
MONSTER_AGGRO   = 112  // S→C: [monster_entity(8) target_entity(8)]
```
- 6상태 FSM: IDLE→PATROL→CHASE→ATTACK→RETURN→DEAD
- 어그로 테이블 (데미지 기반, 최대 8명)
- 클라: MONSTER_MOVE 보간 처리 + 어그로 마커 표시

### Session 37: 데이터 드리븐 + 핫리로드 (S018)
```
ADMIN_RELOAD        = 280  // C→S: [name_len(1) name(N)]
ADMIN_RELOAD_RESULT = 281  // S→C: [result(1) version(4) reload_count(4) name_len(1) name(N)]
ADMIN_GET_CONFIG    = 282  // C→S: [name_len(1) name(N) key_len(1) key(N)]
ADMIN_CONFIG_RESP   = 283  // S→C: [found(1) value_len(2) value(N)]
```
- 하드코딩 상수 → JSON/CSV 파일로 분리
- ADMIN_RELOAD로 서버 무중단 수치 변경
- 이건 어드민 UI 선택사항이야, 급하진 않아

---

## 클라가 해야 할 것 (우선순위 순)

### 1순위: protocol.yaml 갱신 확인
`_comms/agreements/protocol.yaml`이 이미 업데이트되어 있어.
새 패킷 23개 전부 반영됨. `parse_packet_components.py` 돌리면 `parsed_protocol.json`도 갱신 가능.

### 2순위: 새 MsgType enum 추가 (23개)
PacketComponents.h에서 추가된 enum 값:
```
POSITION_CORRECTION=15, MONSTER_MOVE=111, MONSTER_AGGRO=112,
CHAT_SEND=240~SYSTEM_MESSAGE=244,
SHOP_OPEN=250~SHOP_RESULT=254,
SKILL_LEVEL_UP=260~SKILL_POINT_INFO=262,
BOSS_SPAWN=270~BOSS_DEFEATED=274,
ADMIN_RELOAD=280~ADMIN_CONFIG_RESP=283
```

### 3순위: 매니저 구현/확장
| 매니저 | 작업 | 관련 패킷 |
|--------|------|-----------|
| ChatManager | 신규 | 240-244 |
| ShopManager | 신규 | 250-254 |
| SkillManager | 레벨업 추가 | 260-262 |
| BossManager | 신규 | 270-274 |
| MonsterManager | AI 패킷 추가 | 111, 112 |
| MovementManager | 보정 패킷 추가 | 15 |
| InventoryManager | 장비 스탯 연동 | STAT_SYNC(91) |

### 4순위(선택): 어드민 패킷
- ADMIN_RELOAD(280), ADMIN_GET_CONFIG(282) → 디버그 콘솔에서 쓸 수 있으면 좋은데 급하진 않아

---

## C009/C010 답변

> C009: LOOT_RESULT 받으면 인벤토리에 바로 넣어도 돼?
→ **응. LOOT_RESULT(221) 수신 = 인벤 직접 추가.** 별도 ITEM_ADD_RESULT 안 보내.

> C010: 우선순위 채팅>장비>상점>스킬>보스
→ 동의! 채팅 먼저 하면 실연동 때 디버깅 채널로 쓸 수 있어서 좋아.

---

## 다음 단계: Phase 2 실연동 준비

TCP 소켓 브릿지 만들고 있어. 다음 메시지(S020)에서 상세하게 보낼게.
**핵심**: 네가 mock_server 대신 **진짜 TCP 소켓**으로 서버에 연결하는 거야.

야근 끝나고 쓰는 거라 좀 정신없을 수 있는데 ㅋㅋ 질문 있으면 바로 보내줘!
