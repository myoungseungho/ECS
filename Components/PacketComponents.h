#pragma once

#include <cstdint>
#include <cstring>
#include <vector>

// ━━━ 패킷 프로토콜 정의 (Session 2) ━━━
//
// 모든 패킷 구조:
//   [4바이트: 전체 길이(헤더 포함)] [2바이트: 메시지 타입] [N바이트: 페이로드]
//
// 예: "hello"를 ECHO(타입 1)로 보내는 경우
//   길이 = 4(len) + 2(type) + 5(hello) = 11
//   [0B 00 00 00] [01 00] [h e l l o]
//   ^^^^^^^^^^^   ^^^^^^  ^^^^^^^^^^^
//   little-endian  type    payload
//
// OOP였다면: class Packet { int length; short type; byte[] data; }
// ECS에서는: PacketHeader는 순수 데이터 구조, System이 조립/분해

// 패킷 헤더 크기
constexpr int PACKET_HEADER_SIZE = 6;  // 4(length) + 2(type)

// 최대 패킷 크기 (DoS 방지)
constexpr int MAX_PACKET_SIZE = 8192;

// 메시지 타입 정의
enum class MsgType : uint16_t {
    ECHO            = 1,   // 에코: 페이로드 그대로 돌려줌
    PING            = 2,   // 핑: PONG 응답

    // Session 3: 이동 + 브로드캐스트
    MOVE            = 10,  // 클라이언트→서버: 이동 요청 [x(4) y(4) z(4) timestamp(4)]
    MOVE_BROADCAST  = 11,  // 서버→클라이언트: 타인 이동 알림 [entity(8) x(4) y(4) z(4)]
    POS_QUERY       = 12,  // 내 위치 조회 (테스트용)

    // Session 35: 이동 검증 (Model C)
    POSITION_CORRECTION = 15, // S→C: [x(4) y(4) z(4)] 서버가 강제 위치 보정

    // Session 4: AOI (관심 영역)
    APPEAR          = 13,  // 서버→클라이언트: Entity가 시야에 들어옴 [entity(8) x(4) y(4) z(4)]
    DISAPPEAR       = 14,  // 서버→클라이언트: Entity가 시야에서 사라짐 [entity(8)]

    // Session 5: 채널 시스템
    CHANNEL_JOIN    = 20,  // 클라이언트→서버: 채널 입장/변경 [channel_id(4 int)]
    CHANNEL_INFO    = 22,  // 서버→클라이언트: 채널 배정 확인 [channel_id(4 int)]

    // Session 6: 존(맵) 시스템
    ZONE_ENTER      = 30,  // 클라이언트→서버: 맵 진입/이동 [zone_id(4 int)]
    ZONE_INFO       = 31,  // 서버→클라이언트: 맵 배정 확인 [zone_id(4 int)]

    // Session 7: 핸드오프 (서버 간 이동)
    HANDOFF_REQUEST = 40,  // 클라이언트→서버: 핸드오프 요청 (빈 페이로드)
    HANDOFF_DATA    = 41,  // 서버→클라이언트: 직렬화된 Entity 데이터 [serialized bytes]
    HANDOFF_RESTORE = 42,  // 클라이언트→서버: 직렬화 데이터로 Entity 복원 [serialized bytes]
    HANDOFF_RESULT  = 43,  // 서버→클라이언트: 복원 결과 [zone(4) ch(4) x(4) y(4) z(4)]

    // Session 8: Ghost Entity (크로스서버 동기화)
    GHOST_QUERY     = 50,  // 클라이언트→서버: Ghost 수 조회 (빈 페이로드)
    GHOST_INFO      = 51,  // 서버→클라이언트: Ghost 정보 [ghost_count(4 int)]

    // Session 9: Login + Character Select
    LOGIN           = 60,  // 클라이언트→서버: 로그인 [username_len(1) username(N) pw_len(1) pw(N)]
    LOGIN_RESULT    = 61,  // 서버→클라이언트: 로그인 결과 [result(1) account_id(4)]
    CHAR_LIST_REQ   = 62,  // 클라이언트→서버: 캐릭터 목록 요청 (빈 페이로드)
    CHAR_LIST_RESP  = 63,  // 서버→클라이언트: 캐릭터 목록 [count(1) {id(4) name(32) level(4) job(4)}...]
    CHAR_SELECT     = 64,  // 클라이언트→서버: 캐릭터 선택 [char_id(4)]
    ENTER_GAME      = 65,  // 서버→클라이언트: 게임 진입 결과 [result(1) entity(8) zone(4) x(4) y(4) z(4)]

    // Session 10: Gate Server (로드밸런싱)
    GATE_ROUTE_REQ  = 70,  // 클라이언트→게이트: 게임서버 배정 요청 (빈 페이로드)
    GATE_ROUTE_RESP = 71,  // 게이트→클라이언트: 서버 배정 [result(1) port(2) ip_len(1) ip(N)]

    // Session 11: Infrastructure (EventBus + Timer + Config)
    TIMER_ADD       = 80,  // C→S: timer_id(4) duration_ms(4) interval_ms(4)
    TIMER_INFO      = 81,  // S→C: active_timer_count(4) total_events_fired(4)
    CONFIG_QUERY    = 82,  // C→S: table_name_len(1) table_name(N) key_col(1) key(N)
    CONFIG_RESP     = 83,  // S→C: found(1) data_len(2) data(N) (CSV row as "k=v|k=v")
    EVENT_SUB_COUNT = 84,  // S→C: subscriber_count(4) queue_size(4)

    // Session 12: Stats System
    STAT_QUERY      = 90,  // C→S: 빈 페이로드 → 내 스탯 조회
    STAT_SYNC       = 91,  // S→C: level(4) hp(4) max_hp(4) mp(4) max_mp(4) atk(4) def(4) exp(4) exp_next(4) = 36바이트
    STAT_ADD_EXP    = 92,  // C→S: exp_amount(4) → EXP 추가 (테스트용)
    STAT_TAKE_DMG   = 93,  // C→S: raw_damage(4) → 데미지 받기 (테스트용)
    STAT_HEAL       = 94,  // C→S: heal_amount(4) → 힐 (테스트용)

    // Session 13: Combat System
    ATTACK_REQ      = 100, // C→S: [target_entity(8)]
    ATTACK_RESULT   = 101, // S→C: [result(1) attacker(8) target(8) damage(4) target_hp(4) target_max_hp(4)] = 29바이트
    COMBAT_DIED     = 102, // S→C: [dead_entity(8) killer_entity(8)] = 16바이트
    RESPAWN_REQ     = 103, // C→S: 빈 페이로드
    RESPAWN_RESULT  = 104, // S→C: [result(1) hp(4) mp(4) x(4) y(4) z(4)] = 21바이트

    // Session 14: Monster/NPC System
    MONSTER_SPAWN   = 110, // S→C: [entity(8) monster_id(4) level(4) hp(4) max_hp(4) x(4) y(4) z(4)] = 36바이트
    MONSTER_RESPAWN = 113, // S→C: [entity(8) hp(4) max_hp(4) x(4) y(4) z(4)] = 28바이트

    // Session 16: Zone Transfer (존 전환)
    ZONE_TRANSFER_REQ    = 120, // C→S: [target_zone_id(4 int)]
    ZONE_TRANSFER_RESULT = 121, // S→C: [result(1) zone_id(4) x(4) y(4) z(4)] = 17바이트
                                // result: 0=성공, 1=존재하지 않는 맵, 2=이미 같은 맵

    // Session 17: Dynamic Load Balancing (서버 간 프로토콜)
    FIELD_REGISTER      = 130, // Field→Gate: 서버 등록 [port(2) max_ccu(4) name_len(1) name(N)]
    FIELD_HEARTBEAT     = 131, // Field→Gate: 상태 보고 [port(2) ccu(4) max_ccu(4)]
    FIELD_REGISTER_ACK  = 132, // Gate→Field: 등록 확인 [result(1) server_index(4)]
    GATE_SERVER_LIST    = 133, // C→Gate: 서버 목록 요청 (모니터링/테스트용)
    GATE_SERVER_LIST_RESP = 134, // Gate→C: [count(1) {port(2) ccu(4) max_ccu(4) status(1)}...]

    // Session 18: Message Bus (Pub/Sub)
    BUS_REGISTER     = 140, // Server→Bus: 서버 등록 [name_len(1) name(N)]
    BUS_REGISTER_ACK = 141, // Bus→Server: 등록 확인 [result(1) server_id(4)]
    BUS_SUBSCRIBE    = 142, // Server→Bus: 토픽 구독 [topic_len(1) topic(N)]
    BUS_SUB_ACK      = 143, // Bus→Server: 구독 확인 [result(1) topic_len(1) topic(N)]
    BUS_UNSUBSCRIBE  = 144, // Server→Bus: 구독 해제 [topic_len(1) topic(N)]
    BUS_PUBLISH      = 145, // Server→Bus: 메시지 발행 [priority(1) topic_len(1) topic(N) data_len(2) data(N)]
    BUS_MESSAGE      = 146, // Bus→Server: 메시지 전달 [priority(1) sender_id(4) topic_len(1) topic(N) data_len(2) data(N)]

    // Session 19: Skill System
    SKILL_LIST_REQ   = 150, // C→S: 빈 페이로드 → 스킬 목록 조회
    SKILL_LIST_RESP  = 151, // S→C: [count(1) {id(4) name(16) cd_ms(4) dmg(4) mp(4) range(4) type(1)}...]
    SKILL_USE        = 152, // C→S: [skill_id(4) target_entity(8)]
    SKILL_RESULT     = 153, // S→C: [result(1) skill_id(4) caster(8) target(8) damage(4) target_hp(4)]

    // Session 20: Party System
    PARTY_CREATE     = 160, // C→S: 빈 페이로드
    PARTY_INVITE     = 161, // C→S: [target_entity(8)]
    PARTY_ACCEPT     = 162, // C→S: [party_id(4)]
    PARTY_LEAVE      = 163, // C→S: 빈 페이로드
    PARTY_INFO       = 164, // S→C: [result(1) party_id(4) leader(8) count(1) {entity(8) level(4)}...]
    PARTY_KICK       = 165, // C→S: [target_entity(8)]

    // Session 21: Instance Dungeon
    INSTANCE_CREATE  = 170, // C→S: [dungeon_type(4)]
    INSTANCE_ENTER   = 171, // S→C: [result(1) instance_id(4) dungeon_type(4)]
    INSTANCE_LEAVE   = 172, // C→S: 빈 페이로드
    INSTANCE_LEAVE_RESULT = 173, // S→C: [result(1) zone_id(4) x(4) y(4) z(4)]
    INSTANCE_INFO    = 174, // S→C: [instance_id(4) dungeon_type(4) player_count(1) monster_count(1)]

    // Session 22: Matching Queue
    MATCH_ENQUEUE    = 180, // C→S: [dungeon_type(4)]
    MATCH_DEQUEUE    = 181, // C→S: 빈 페이로드
    MATCH_FOUND      = 182, // S→C: [match_id(4) dungeon_type(4) player_count(1)]
    MATCH_ACCEPT     = 183, // C→S: [match_id(4)]
    MATCH_STATUS     = 184, // S→C: [status(1) queue_position(4)]

    // Session 23: Inventory/Item
    INVENTORY_REQ    = 190, // C→S: 빈 페이로드
    INVENTORY_RESP   = 191, // S→C: [count(1) {slot(1) item_id(4) count(2) equipped(1)}...]
    ITEM_ADD         = 192, // C→S: [item_id(4) count(2)] (테스트용)
    ITEM_ADD_RESULT  = 193, // S→C: [result(1) slot(1) item_id(4) count(2)]
    ITEM_USE         = 194, // C→S: [slot(1)]
    ITEM_USE_RESULT  = 195, // S→C: [result(1) slot(1) item_id(4)]
    ITEM_EQUIP       = 196, // C→S: [slot(1)]
    ITEM_UNEQUIP     = 197, // C→S: [slot(1)]
    ITEM_EQUIP_RESULT = 198, // S→C: [result(1) slot(1) item_id(4) equipped(1)]

    // Session 24: Buff/Debuff
    BUFF_LIST_REQ    = 200, // C→S: 빈 페이로드
    BUFF_LIST_RESP   = 201, // S→C: [count(1) {buff_id(4) remaining_ms(4) stacks(1)}...]
    BUFF_APPLY_REQ   = 202, // C→S: [buff_id(4)] (테스트용)
    BUFF_RESULT      = 203, // S→C: [result(1) buff_id(4) stacks(1) duration_ms(4)]
    BUFF_REMOVE_REQ  = 204, // C→S: [buff_id(4)]
    BUFF_REMOVE_RESP = 205, // S→C: [result(1) buff_id(4)]

    // Session 25: Condition Engine
    CONDITION_EVAL   = 210, // C→S: [node_count(1) root(1) {type(1) p1(4) p2(4) left(2) right(2)}...]
    CONDITION_RESULT = 211, // S→C: [result(1)]

    // Session 26: Spatial Query
    SPATIAL_QUERY_REQ  = 215, // C→S: [x(4) y(4) z(4) radius(4) filter(1)] filter: 0=all,1=player,2=monster
    SPATIAL_QUERY_RESP = 216, // S→C: [count(1) {entity(8) dist(4)}...]

    // Session 27: Loot/Drop Table
    LOOT_ROLL_REQ    = 220, // C→S: [table_id(4)]
    LOOT_RESULT      = 221, // S→C: [count(1) {item_id(4) count(2)}...]

    // Session 28: Quest System
    QUEST_LIST_REQ       = 230, // C→S: empty
    QUEST_LIST_RESP      = 231, // S→C: [count(1) {quest_id(4) state(1) progress(4) target(4)}...]
    QUEST_ACCEPT         = 232, // C→S: [quest_id(4)]
    QUEST_ACCEPT_RESULT  = 233, // S→C: [result(1) quest_id(4)]
    QUEST_PROGRESS       = 234, // C→S: [quest_id(4)] (check/update progress)
    QUEST_COMPLETE       = 235, // C→S: [quest_id(4)]
    QUEST_COMPLETE_RESULT = 236, // S→C: [result(1) quest_id(4) reward_exp(4) reward_item_id(4) reward_item_count(2)]

    // Session 30: Chat System
    CHAT_SEND       = 240, // C→S: [channel(1) msg_len(1) message(N)]
    CHAT_MESSAGE    = 241, // S→C: [channel(1) sender_entity(8) sender_name(32) msg_len(1) message(N)]
    WHISPER_SEND    = 242, // C→S: [target_name_len(1) target_name(N) msg_len(1) message(N)]
    WHISPER_RESULT  = 243, // S→C: [result(1) direction(1) other_name(32) msg_len(1) message(N)]
    SYSTEM_MESSAGE  = 244, // S→C: [msg_len(1) message(N)]

    // Session 32: NPC Shop
    SHOP_OPEN       = 250, // C→S: [npc_id(4)]
    SHOP_LIST       = 251, // S→C: [npc_id(4) count(1) {item_id(4) price(4) stock(2)}...]
    SHOP_BUY        = 252, // C→S: [npc_id(4) item_id(4) count(2)]
    SHOP_SELL       = 253, // C→S: [slot(1) count(2)]
    SHOP_RESULT     = 254, // S→C: [result(1) action(1) item_id(4) count(2) gold(4)]

    // Session 33: Skill Expansion
    SKILL_LEVEL_UP        = 260, // C→S: [skill_id(4)]
    SKILL_LEVEL_UP_RESULT = 261, // S→C: [result(1) skill_id(4) new_level(1) skill_points(4)]
    SKILL_POINT_INFO      = 262, // S→C: [skill_points(4) total_spent(4)]

    // Session 34: Boss Mechanics
    BOSS_SPAWN            = 270, // S→C: [entity(8) boss_id(4) name(32) level(4) hp(4) max_hp(4) phase(1)]
    BOSS_PHASE_CHANGE     = 271, // S→C: [entity(8) boss_id(4) new_phase(1) hp(4) max_hp(4)]
    BOSS_SPECIAL_ATTACK   = 272, // S→C: [entity(8) boss_id(4) attack_type(1) damage(4)]
    BOSS_ENRAGE           = 273, // S→C: [entity(8) boss_id(4)]
    BOSS_DEFEATED         = 274, // S→C: [entity(8) boss_id(4) killer_entity(8)]

    STATS       = 99,  // 내부 진단
};

// 패킷 헤더 (네트워크 바이트 → 구조체로 파싱)
#pragma pack(push, 1)
struct PacketHeader {
    uint32_t length;    // 전체 패킷 크기 (헤더 포함)
    uint16_t msg_type;  // MsgType
};
#pragma pack(pop)

// ━━━ 패킷 빌드 유틸리티 ━━━

// 헤더 + 페이로드를 하나의 버퍼로 조립
inline std::vector<char> BuildPacket(MsgType type, const char* payload, int payload_len) {
    uint32_t total_len = PACKET_HEADER_SIZE + payload_len;
    std::vector<char> buf(total_len);

    // 헤더 쓰기 (little-endian)
    std::memcpy(buf.data(), &total_len, 4);
    uint16_t t = static_cast<uint16_t>(type);
    std::memcpy(buf.data() + 4, &t, 2);

    // 페이로드 쓰기
    if (payload_len > 0) {
        std::memcpy(buf.data() + PACKET_HEADER_SIZE, payload, payload_len);
    }

    return buf;
}

// 오버로드: string 버전
inline std::vector<char> BuildPacket(MsgType type, const std::vector<char>& payload) {
    return BuildPacket(type, payload.data(), static_cast<int>(payload.size()));
}

// 빈 페이로드 패킷
inline std::vector<char> BuildPacket(MsgType type) {
    return BuildPacket(type, nullptr, 0);
}
