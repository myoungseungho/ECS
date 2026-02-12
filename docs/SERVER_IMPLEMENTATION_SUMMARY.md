# 서버 구현 현황 요약서

> **작성일**: 2026-02-11
> **대상**: 클라이언트 개발팀
> **서버 테스트**: 29개 세션 / 321개 테스트 전체 통과

---

## 1. 아키텍처 개요

### ECS (Entity Component System) 기반

```
Entity = uint64_t (고유 ID)
Component = 순수 데이터 구조체 (StatsComponent, InventoryComponent 등)
System = 로직 함수 (매 틱마다 Component를 순회하며 처리)
```

### 패킷 프로토콜

```
모든 패킷 구조 (Little-Endian):
[4바이트: 전체 길이(헤더 포함)] [2바이트: 메시지 타입] [N바이트: 페이로드]

헤더 크기: 6바이트
최대 패킷: 8192바이트
```

### 서버 구성

```
Client ──→ GateServer (포트 8888) ──→ FieldServer (포트 7777, 7778...)
                                          ↕
                                      BusServer (포트 9999, Pub/Sub 메시지 버스)
```

---

## 2. 세션별 구현 내용

### Phase 1: 코어 인프라 (Session 1~8)

| 세션 | 시스템 | 핵심 기능 | 테스트 |
|------|--------|-----------|--------|
| 1 | ECS + IOCP | Entity 생성/삭제, 컴포넌트 부착, 다중 클라이언트 | 12/12 |
| 2 | 패킷 프로토콜 | Echo, Ping/Pong, 분할 전송, 메시지 디스패치 | 14/14 |
| 3 | 이동 + 브로드캐스트 | 위치 이동, 주변 플레이어에 브로드캐스트 | 12/12 |
| 4 | AOI (관심 영역) | 그리드 기반(500 단위), APPEAR/DISAPPEAR 이벤트 | 11/11 |
| 5 | 채널 시스템 | 채널 입장/변경, 채널 격리 | 15/15 |
| 6 | 존(맵) 시스템 | 존 진입, 존 격리, 몬스터 분리 | 16/16 |
| 7 | 핸드오프 | Entity 직렬화, 서버 간 이동, 데이터 복원 | 16/16 |
| 8 | Ghost Entity | 크로스서버 동기화, 타 서버 Entity 투영 | 13/13 |

### Phase 2: 멀티서버 + 인증 (Session 9~13)

| 세션 | 시스템 | 핵심 기능 | 테스트 |
|------|--------|-----------|--------|
| 9 | 로그인 + 캐릭터 선택 | 계정 인증, 캐릭터 목록, 캐릭터 선택 후 게임 진입 | 21/21 |
| 10 | 게이트 서버 | 로드밸런싱, 서버 배정, Field 서버 연결 | 20/20 |
| 11 | 인프라 (이벤트+타이머+설정) | EventBus, Timer, CSV 설정 로딩 | 15/15 |
| 12 | 스탯 시스템 | 레벨/HP/MP/ATK/DEF, 경험치, 레벨업, 데미지/힐 | 12/12 |
| 13 | 전투 시스템 | 공격 요청/결과, 사망/부활, 몬스터 AI, 쿨타임 | 6/6 |

### Phase 3: 고급 시스템 (Session 14~18)

| 세션 | 시스템 | 핵심 기능 | 테스트 |
|------|--------|-----------|--------|
| 14 | 몬스터/NPC | 스폰, 사망/리스폰, 기본 AI (어그로) | 6/6 |
| 15 | 재접속 | 세션 복구, 상태 유지, 타임아웃 | 7/7 |
| 16 | 존 전환 | 맵 이동, 몬스터 격리, 존별 독립 | 7/7 |
| 17 | 동적 로드밸런싱 | CCU 기반 서버 분배, 상태 모니터링 | 7/7 |
| 18 | 메시지 버스 | Pub/Sub, 우선순위 큐, 토픽 기반 구독 | 7/7 |

### Phase 4: 게임 콘텐츠 (Session 19~24)

| 세션 | 시스템 | 핵심 기능 | 테스트 |
|------|--------|-----------|--------|
| 19 | 스킬 시스템 | 스킬 목록, 사용, 쿨타임, MP 소모, 타입별 처리 | 7/7 |
| 20 | 파티 시스템 | 파티 생성/초대/수락/탈퇴/추방, 파티 정보 | 7/7 |
| 21 | 인스턴스 던전 | 생성/입장/퇴장, 격리된 공간, 독립 몬스터 | 7/7 |
| 22 | 매칭 큐 | 매칭 등록/취소/수락, 자동 인스턴스 생성 | 7/7 |
| 23 | 인벤토리/아이템 | 아이템 추가/사용/장착/해제, 슬롯 관리 | 7/7 |
| 24 | 버프/디버프 | 적용/해제/목록, 스택, 지속시간, 다중 타입 | 7/7 |

### Phase 5: 복합 조건 인프라 (Session 25~29)

| 세션 | 시스템 | 핵심 기능 | 테스트 |
|------|--------|-----------|--------|
| 25 | 조건 엔진 | AND/OR/NOT 트리, 레벨/존/아이템/버프/직업 조건 | 18/18 |
| 26 | 공간 쿼리 | 반경 기반 엔티티 검색, 타입 필터(전체/플레이어/몬스터) | 11/11 |
| 27 | 루트/드롭 테이블 | 확률 드롭, 보장 아이템, 가중치 랜덤 | 9/9 |
| 28 | 퀘스트 시스템 | 수락/진행/완료/보상, 선행 퀘스트, 몬스터 킬 추적 | 13/13 |
| 29 | 전체 연동 테스트 | 로그인→퀘스트→전투→보상→인벤→버프→조건→루트→체인퀘 | 11/11 |

---

## 3. 전체 패킷 프로토콜 명세

### 기본 (Session 1~2)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| ECHO | 1 | C↔S | 임의 바이트 (그대로 반환) |
| PING | 2 | C→S | 빈 페이로드 → PONG 응답 |
| STATS | 99 | S→C | 내부 진단용 |

### 이동/AOI (Session 3~4)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| MOVE | 10 | C→S | `x(f32) y(f32) z(f32)` |
| MOVE_BROADCAST | 11 | S→C | `entity(u64) x(f32) y(f32) z(f32)` |
| POS_QUERY | 12 | C→S | 빈 |
| APPEAR | 13 | S→C | `entity(u64) x(f32) y(f32) z(f32)` |
| DISAPPEAR | 14 | S→C | `entity(u64)` |

### 채널/존 (Session 5~6)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| CHANNEL_JOIN | 20 | C→S | `channel_id(i32)` |
| CHANNEL_INFO | 22 | S→C | `channel_id(i32)` |
| ZONE_ENTER | 30 | C→S | `zone_id(i32)` |
| ZONE_INFO | 31 | S→C | `zone_id(i32)` |

### 핸드오프/Ghost (Session 7~8)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| HANDOFF_REQUEST | 40 | C→S | 빈 |
| HANDOFF_DATA | 41 | S→C | `직렬화된 Entity 바이트` |
| HANDOFF_RESTORE | 42 | C→S | `직렬화된 Entity 바이트` |
| HANDOFF_RESULT | 43 | S→C | `zone(i32) ch(i32) x(f32) y(f32) z(f32)` |
| GHOST_QUERY | 50 | C→S | 빈 |
| GHOST_INFO | 51 | S→C | `ghost_count(i32)` |

### 로그인/캐릭터 (Session 9)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| LOGIN | 60 | C→S | `uname_len(u8) uname(N) pw_len(u8) pw(N)` |
| LOGIN_RESULT | 61 | S→C | `result(u8) account_id(u32)` |
| CHAR_LIST_REQ | 62 | C→S | 빈 |
| CHAR_LIST_RESP | 63 | S→C | `count(u8) {id(u32) name(32B) level(u32) job(u32)}...` |
| CHAR_SELECT | 64 | C→S | `char_id(u32)` |
| ENTER_GAME | 65 | S→C | `result(u8) entity(u64) zone(u32) x(f32) y(f32) z(f32)` |

**LOGIN_RESULT result 코드**: 0=성공, 1=계정없음, 2=비밀번호틀림, 3=이미접속중

**ENTER_GAME result 코드**: 0=성공, 1=캐릭터없음, 2=다른계정소유

### 게이트 서버 (Session 10, 17)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| GATE_ROUTE_REQ | 70 | C→Gate | 빈 |
| GATE_ROUTE_RESP | 71 | Gate→C | `result(u8) port(u16) ip_len(u8) ip(N)` |
| FIELD_REGISTER | 130 | Field→Gate | `port(u16) max_ccu(u32) name_len(u8) name(N)` |
| FIELD_HEARTBEAT | 131 | Field→Gate | `port(u16) ccu(u32) max_ccu(u32)` |
| GATE_SERVER_LIST | 133 | C→Gate | 빈 |
| GATE_SERVER_LIST_RESP | 134 | Gate→C | `count(u8) {port(u16) ccu(u32) max_ccu(u32) status(u8)}...` |

### 존 전환 (Session 16)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| ZONE_TRANSFER_REQ | 120 | C→S | `target_zone_id(i32)` |
| ZONE_TRANSFER_RESULT | 121 | S→C | `result(u8) zone_id(u32) x(f32) y(f32) z(f32)` |

**result 코드**: 0=성공, 1=존재하지 않는 맵, 2=이미 같은 맵

### 인프라 (Session 11)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| TIMER_ADD | 80 | C→S | `timer_id(u32) duration_ms(u32) interval_ms(u32)` |
| TIMER_INFO | 81 | S→C | `active_timer_count(u32) total_events_fired(u32)` |
| CONFIG_QUERY | 82 | C→S | `table_name_len(u8) table_name(N) key_col(u8) key(N)` |
| CONFIG_RESP | 83 | S→C | `found(u8) data_len(u16) data(N)` |

### 스탯 (Session 12)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| STAT_QUERY | 90 | C→S | 빈 |
| STAT_SYNC | 91 | S→C | `level(i32) hp(i32) max_hp(i32) mp(i32) max_mp(i32) atk(i32) def(i32) exp(i32) exp_next(i32)` = 36바이트 |
| STAT_ADD_EXP | 92 | C→S | `exp_amount(i32)` |
| STAT_TAKE_DMG | 93 | C→S | `raw_damage(i32)` |
| STAT_HEAL | 94 | C→S | `heal_amount(i32)` |

### 전투 (Session 13)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| ATTACK_REQ | 100 | C→S | `target_entity(u64)` |
| ATTACK_RESULT | 101 | S→C | `result(u8) attacker(u64) target(u64) damage(i32) target_hp(i32) target_max_hp(i32)` = 29바이트 |
| COMBAT_DIED | 102 | S→C | `dead_entity(u64) killer_entity(u64)` = 16바이트 |
| RESPAWN_REQ | 103 | C→S | 빈 |
| RESPAWN_RESULT | 104 | S→C | `result(u8) hp(i32) mp(i32) x(f32) y(f32) z(f32)` = 21바이트 |

**AttackResult 코드**: 0=성공, 1=대상없음, 2=대상사망, 3=사거리초과, 4=쿨타임, 5=본인사망, 6=자기공격

### 몬스터 (Session 14)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| MONSTER_SPAWN | 110 | S→C | `entity(u64) monster_id(u32) level(u32) hp(i32) max_hp(i32) x(f32) y(f32) z(f32)` = 36바이트 |
| MONSTER_RESPAWN | 113 | S→C | `entity(u64) hp(i32) max_hp(i32) x(f32) y(f32) z(f32)` = 28바이트 |

### 스킬 (Session 19)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| SKILL_LIST_REQ | 150 | C→S | 빈 |
| SKILL_LIST_RESP | 151 | S→C | `count(u8) {id(u32) name(16B) cd_ms(u32) dmg(u32) mp(u32) range(u32) type(u8)}...` |
| SKILL_USE | 152 | C→S | `skill_id(u32) target_entity(u64)` |
| SKILL_RESULT | 153 | S→C | `result(u8) skill_id(u32) caster(u64) target(u64) damage(i32) target_hp(i32)` |

### 파티 (Session 20)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| PARTY_CREATE | 160 | C→S | 빈 |
| PARTY_INVITE | 161 | C→S | `target_entity(u64)` |
| PARTY_ACCEPT | 162 | C→S | `party_id(u32)` |
| PARTY_LEAVE | 163 | C→S | 빈 |
| PARTY_INFO | 164 | S→C | `result(u8) party_id(u32) leader(u64) count(u8) {entity(u64) level(u32)}...` |
| PARTY_KICK | 165 | C→S | `target_entity(u64)` |

### 인스턴스 던전 (Session 21)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| INSTANCE_CREATE | 170 | C→S | `dungeon_type(u32)` |
| INSTANCE_ENTER | 171 | S→C | `result(u8) instance_id(u32) dungeon_type(u32)` |
| INSTANCE_LEAVE | 172 | C→S | 빈 |
| INSTANCE_LEAVE_RESULT | 173 | S→C | `result(u8) zone_id(u32) x(f32) y(f32) z(f32)` |
| INSTANCE_INFO | 174 | S→C | `instance_id(u32) dungeon_type(u32) player_count(u8) monster_count(u8)` |

### 매칭 큐 (Session 22)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| MATCH_ENQUEUE | 180 | C→S | `dungeon_type(u32)` |
| MATCH_DEQUEUE | 181 | C→S | 빈 |
| MATCH_FOUND | 182 | S→C | `match_id(u32) dungeon_type(u32) player_count(u8)` |
| MATCH_ACCEPT | 183 | C→S | `match_id(u32)` |
| MATCH_STATUS | 184 | S→C | `status(u8) queue_position(u32)` |

### 인벤토리/아이템 (Session 23)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| INVENTORY_REQ | 190 | C→S | 빈 |
| INVENTORY_RESP | 191 | S→C | `count(u8) {slot(u8) item_id(u32) count(u16) equipped(u8)}...` = 엔트리당 8바이트 |
| ITEM_ADD | 192 | C→S | `item_id(u32) count(u16)` |
| ITEM_ADD_RESULT | 193 | S→C | `result(u8) slot(u8) item_id(u32) count(u16)` |
| ITEM_USE | 194 | C→S | `slot(u8)` |
| ITEM_USE_RESULT | 195 | S→C | `result(u8) slot(u8) item_id(u32)` |
| ITEM_EQUIP | 196 | C→S | `slot(u8)` |
| ITEM_UNEQUIP | 197 | C→S | `slot(u8)` |
| ITEM_EQUIP_RESULT | 198 | S→C | `result(u8) slot(u8) item_id(u32) equipped(u8)` |

**ItemResult 코드**: 0=성공, 1=인벤토리꽉참, 2=빈슬롯, 3=이미장착, 4=장착안됨

### 버프/디버프 (Session 24)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| BUFF_LIST_REQ | 200 | C→S | 빈 |
| BUFF_LIST_RESP | 201 | S→C | `count(u8) {buff_id(u32) remaining_ms(u32) stacks(u8)}...` = 엔트리당 9바이트 |
| BUFF_APPLY_REQ | 202 | C→S | `buff_id(u32)` |
| BUFF_RESULT | 203 | S→C | `result(u8) buff_id(u32) stacks(u8) duration_ms(u32)` = 10바이트 |
| BUFF_REMOVE_REQ | 204 | C→S | `buff_id(u32)` |
| BUFF_REMOVE_RESP | 205 | S→C | `result(u8) buff_id(u32)` |

**BuffResult 코드**: 0=성공, 1=버프없음, 2=슬롯없음, 3=비활성

### 조건 엔진 (Session 25)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| CONDITION_EVAL | 210 | C→S | `node_count(u8) root(u8) {type(u8) p1(i32) p2(i32) left(u16) right(u16)}...` = 노드당 13바이트 |
| CONDITION_RESULT | 211 | S→C | `result(u8)` (0=false, 1=true) |

**ConditionType**: 0=ALWAYS_TRUE, 1=ALWAYS_FALSE, 10=AND, 11=OR, 12=NOT, 20=LEVEL_GE, 30=HAS_ITEM, 31=HAS_BUFF, 40=IN_ZONE, 60=CLASS_EQ

### 공간 쿼리 (Session 26)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| SPATIAL_QUERY_REQ | 215 | C→S | `x(f32) y(f32) z(f32) radius(f32) filter(u8)` |
| SPATIAL_QUERY_RESP | 216 | S→C | `count(u8) {entity(u64) dist(f32)}...` = 엔트리당 12바이트 |

**filter**: 0=전체, 1=플레이어만, 2=몬스터만

### 루트/드롭 (Session 27)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| LOOT_ROLL_REQ | 220 | C→S | `table_id(u32)` |
| LOOT_RESULT | 221 | S→C | `count(u8) {item_id(u32) count(u16)}...` = 엔트리당 6바이트 |

### 퀘스트 (Session 28)

| 타입 | ID | 방향 | 페이로드 |
|------|----|------|----------|
| QUEST_LIST_REQ | 230 | C→S | 빈 |
| QUEST_LIST_RESP | 231 | S→C | `count(u8) {quest_id(u32) state(u8) progress(u32) target(u32)}...` = 엔트리당 13바이트 |
| QUEST_ACCEPT | 232 | C→S | `quest_id(u32)` |
| QUEST_ACCEPT_RESULT | 233 | S→C | `result(u8) quest_id(u32)` |
| QUEST_PROGRESS | 234 | C→S | `quest_id(u32)` |
| QUEST_COMPLETE | 235 | C→S | `quest_id(u32)` |
| QUEST_COMPLETE_RESULT | 236 | S→C | `result(u8) quest_id(u32) reward_exp(u32) reward_item_id(u32) reward_item_count(u16)` |

**QuestState**: 0=NONE, 1=ACCEPTED, 2=IN_PROGRESS, 3=COMPLETE, 4=REWARDED

**QuestResult**: 0=성공, 1=퀘스트없음, 2=이미수락, 3=퀘스트꽉참, 4=선행퀘스트미완, 5=레벨부족, 6=미완료

---

## 4. 서버에 등록된 게임 데이터

### 기본 계정 (테스트용)

| 계정 | 비밀번호 | acc_id | 캐릭터 |
|------|----------|--------|--------|
| hero | pass123 | 1001 | char_id=1 "Warrior_Kim" Lv50 전사, char_id=2 "Mage_Lee" Lv35 마법사 |
| guest | guest | 1002 | char_id=3 "Archer_Park" Lv20 궁수 |
| empty | empty | 1003 | 캐릭터 없음 |

### 존(맵) 데이터

| zone_id | 이름 | 스폰 위치 |
|---------|------|-----------|
| 1 | 초보자 마을 | (500, 500, 0) |
| 2 | 숲 | (1000, 1000, 0) |
| 3 | 던전 입구 | (200, 200, 0) |

### 몬스터 스폰 (Zone 1)

| monster_id | 이름 | 위치 | HP | ATK | DEF | 경험치 |
|-----------|------|------|----|-----|-----|--------|
| 1 | Goblin_A | (200, 200) | 100 | 15 | 5 | 30 |
| 2 | Goblin_B | (400, 300) | 100 | 15 | 5 | 30 |
| 3 | Goblin_C | (300, 500) | 100 | 15 | 5 | 30 |
| 4 | Wolf_A | (100, 400) | 200 | 25 | 10 | 50 |
| 5 | Wolf_B | (500, 100) | 200 | 25 | 10 | 50 |

### 스킬 데이터

| skill_id | 이름 | 쿨타임 | 데미지 | MP소모 | 사거리 | 타입 |
|----------|------|--------|--------|--------|--------|------|
| 1 | Slash | 1000ms | 120 | 10 | 150 | MELEE |
| 2 | Fireball | 3000ms | 200 | 30 | 500 | RANGED |
| 3 | Heal | 5000ms | -150 (회복) | 40 | 300 | HEAL |
| 4 | PowerStrike | 8000ms | 350 | 50 | 150 | MELEE |

### 버프 데이터

| buff_id | 이름 | 타입 | 수치 | 지속시간 | 틱 | 최대스택 |
|---------|------|------|------|----------|-----|----------|
| 1 | Strength | ATK_UP | +15 | 10s | - | 1 |
| 2 | IronSkin | DEF_UP | +20 | 15s | - | 1 |
| 3 | Regeneration | REGEN | +10 | 20s | 2s | 1 |
| 4 | Haste | SPEED_UP | +5 | 12s | - | 1 |
| 5 | Poison | POISON | -8 | 6s | 1s | 3 |
| 6 | Weakness | ATK_DOWN | -10 | 8s | - | 1 |

### 루트 테이블

| table_id | 이름 | 드롭 항목 |
|----------|------|-----------|
| 1 | BasicMonster | HP Potion(60%), MP Potion(30%), Iron Ore(10%) |
| 2 | EliteMonster | HP Potion(40%), Steel Sword(20%), Leather Armor(15%), Skill Scroll(5%) |
| 3 | BossMonster | HP Potion(50%), Rare Sword(30%), Diamond(10%), **Gold Ring(보장)** |
| 4 | TreasureChest | Gold Coin(70%), Gem(20%), Rare Scroll(10%) |

### 퀘스트 데이터

| quest_id | 이름 | 타입 | 목표 | 보상 | 선행퀘스트 |
|----------|------|------|------|------|------------|
| 1 | Beginner Hunt | KILL | 아무 몬스터 3마리 | 100 EXP + HP Potion x3 | 없음 |
| 2 | Wolf Slayer | KILL | Wolf 2마리 | 200 EXP + Iron Ore x2 | 없음 |
| 3 | Item Collector | COLLECT | Iron Ore 5개 | 150 EXP + Leather Armor x1 | 없음 |
| 4 | Explorer | VISIT | Zone 3 방문 | 100 EXP | 없음 |
| 5 | Advanced Hunt | KILL | 아무 몬스터 5마리 | 300 EXP + Steel Sword x1 | **퀘스트 1 완료** |

---

## 5. 전투 공식

```
기본 데미지 = attacker.ATK - target.DEF
최소 데미지 = 1 (0 이하면 1로 보정)

레벨업 필요 경험치 = level * 100
레벨업 시: HP += 20, MP += 10, ATK += 3, DEF += 2

공격 쿨타임: 2.0초
공격 사거리: 200.0 유닛
```
