// ━━━ PacketDefinitions.cs ━━━
// 서버 PacketComponents.h의 C# 미러
// 서버와 100% 동일한 메시지 타입 + 페이로드 구조

namespace Network
{
    /// <summary>
    /// 서버 메시지 타입 (uint16, Little-Endian)
    /// 서버 C++ enum class MsgType과 1:1 대응
    /// </summary>
    public enum MsgType : ushort
    {
        ECHO            = 1,
        PING            = 2,

        // 이동
        MOVE            = 10,   // C→S: x(4f) y(4f) z(4f)
        MOVE_BROADCAST  = 11,   // S→C: entity(8u64) x(4f) y(4f) z(4f)
        POS_QUERY       = 12,

        // AOI
        APPEAR          = 13,   // S→C: entity(8u64) x(4f) y(4f) z(4f)
        DISAPPEAR       = 14,   // S→C: entity(8u64)

        // 채널
        CHANNEL_JOIN    = 20,   // C→S: channel_id(4i32)
        CHANNEL_INFO    = 22,   // S→C: channel_id(4i32)

        // 존
        ZONE_ENTER      = 30,   // C→S: zone_id(4i32)
        ZONE_INFO       = 31,   // S→C: zone_id(4i32)

        // 핸드오프
        HANDOFF_REQUEST = 40,
        HANDOFF_DATA    = 41,
        HANDOFF_RESTORE = 42,
        HANDOFF_RESULT  = 43,

        // Ghost
        GHOST_QUERY     = 50,
        GHOST_INFO      = 51,

        // 로그인
        LOGIN           = 60,   // C→S: uname_len(1) uname(N) pw_len(1) pw(N)
        LOGIN_RESULT    = 61,   // S→C: result(1) account_id(4)
        CHAR_LIST_REQ   = 62,   // C→S: empty
        CHAR_LIST_RESP  = 63,   // S→C: count(1) {id(4) name(32) level(4) job(4)}...
        CHAR_SELECT     = 64,   // C→S: char_id(4)
        ENTER_GAME      = 65,   // S→C: result(1) entity(8) zone(4) x(4) y(4) z(4)

        // 게이트
        GATE_ROUTE_REQ  = 70,   // C→Gate: empty
        GATE_ROUTE_RESP = 71,   // Gate→C: result(1) port(2) ip_len(1) ip(N)

        // 스탯
        STAT_QUERY      = 90,   // C→S: 빈 페이로드
        STAT_SYNC       = 91,   // S→C: level(4i) hp(4i) max_hp(4i) mp(4i) max_mp(4i) atk(4i) def(4i) exp(4i) exp_next(4i)

        // 전투
        ATTACK_REQ      = 100,  // C→S: target_entity(8u64)
        ATTACK_RESULT   = 101,  // S→C: result(1) attacker(8u64) target(8u64) damage(4i) target_hp(4i) target_max_hp(4i)
        COMBAT_DIED     = 102,  // S→C: dead_entity(8u64) killer_entity(8u64)
        RESPAWN_REQ     = 103,  // C→S: 빈 페이로드
        RESPAWN_RESULT  = 104,  // S→C: result(1) hp(4i) mp(4i) x(4f) y(4f) z(4f)

        // 몬스터 (세션 14)
        MONSTER_SPAWN   = 110,  // S→C: entity(8u64) monster_id(4u32) level(4u32) hp(4i) max_hp(4i) x(4f) y(4f) z(4f) = 36B
        MONSTER_RESPAWN = 113,  // S→C: entity(8u64) hp(4i) max_hp(4i) x(4f) y(4f) z(4f) = 28B

        // 존 이동 (세션 16)
        ZONE_TRANSFER_REQ    = 120,  // C→S: target_zone_id(4i32)
        ZONE_TRANSFER_RESULT = 121,  // S→C: result(1) zone_id(4u32) x(4f) y(4f) z(4f) = 17B

        // 게이트 서버 목록 (세션 17)
        FIELD_REGISTER       = 130,  // S2S
        FIELD_HEARTBEAT      = 131,  // S2S
        GATE_SERVER_LIST     = 133,  // C→S: empty
        GATE_SERVER_LIST_RESP = 134, // S→C: count(1) {port(2) ccu(4) max_ccu(4) status(1)}*N

        // 스킬 (세션 19)
        SKILL_LIST_REQ  = 150,  // C→S: empty
        SKILL_LIST_RESP = 151,  // S→C: count(1) {id(4) name(16) cd_ms(4) dmg(4) mp(4) range(4) type(1)}*N = 37B/entry
        SKILL_USE       = 152,  // C→S: skill_id(4u32) target_entity(8u64) = 12B
        SKILL_RESULT    = 153,  // S→C: result(1) skill_id(4) caster(8) target(8) damage(4i) target_hp(4i) = 29B

        // 파티 (세션 20)
        PARTY_CREATE    = 160,  // C→S: empty
        PARTY_INVITE    = 161,  // C→S: target_entity(8u64)
        PARTY_ACCEPT    = 162,  // C→S: party_id(4u32)
        PARTY_LEAVE     = 163,  // C→S: empty
        PARTY_INFO      = 164,  // S→C: result(1) party_id(4) leader(8) count(1) {entity(8) level(4)}*N
        PARTY_KICK      = 165,  // C→S: target_entity(8u64)

        // 인스턴스 던전 (세션 21)
        INSTANCE_CREATE       = 170,  // C→S: dungeon_type(4u32)
        INSTANCE_ENTER        = 171,  // S→C: result(1) instance_id(4) dungeon_type(4) = 9B
        INSTANCE_LEAVE        = 172,  // C→S: empty
        INSTANCE_LEAVE_RESULT = 173,  // S→C: result(1) zone_id(4) x(4f) y(4f) z(4f) = 17B
        INSTANCE_INFO         = 174,  // S→C: instance_id(4) dungeon_type(4) player_count(1) monster_count(1) = 10B

        // 매칭 (세션 22)
        MATCH_ENQUEUE   = 180,  // C→S: dungeon_type(4u32)
        MATCH_DEQUEUE   = 181,  // C→S: empty
        MATCH_FOUND     = 182,  // S→C: match_id(4) dungeon_type(4) player_count(1) = 9B
        MATCH_ACCEPT    = 183,  // C→S: match_id(4u32)
        MATCH_STATUS    = 184,  // S→C: status(1) queue_position(4) = 5B

        // 인벤토리 (세션 23)
        INVENTORY_REQ    = 190,  // C→S: empty
        INVENTORY_RESP   = 191,  // S→C: count(1) {slot(1) item_id(4) count(2) equipped(1)}*N = 8B/entry
        ITEM_ADD         = 192,  // C→S: item_id(4u32) count(2u16)
        ITEM_ADD_RESULT  = 193,  // S→C: result(1) slot(1) item_id(4) count(2) = 8B
        ITEM_USE         = 194,  // C→S: slot(1u8)
        ITEM_USE_RESULT  = 195,  // S→C: result(1) slot(1) item_id(4) = 6B
        ITEM_EQUIP       = 196,  // C→S: slot(1u8)
        ITEM_UNEQUIP     = 197,  // C→S: slot(1u8)
        ITEM_EQUIP_RESULT = 198, // S→C: result(1) slot(1) item_id(4) equipped(1) = 7B

        // 버프 (세션 24)
        BUFF_LIST_REQ    = 200,  // C→S: empty
        BUFF_LIST_RESP   = 201,  // S→C: count(1) {buff_id(4) remaining_ms(4) stacks(1)}*N = 9B/entry
        BUFF_APPLY_REQ   = 202,  // C→S: buff_id(4u32)
        BUFF_RESULT      = 203,  // S→C: result(1) buff_id(4) stacks(1) duration_ms(4) = 10B
        BUFF_REMOVE_REQ  = 204,  // C→S: buff_id(4u32)
        BUFF_REMOVE_RESP = 205,  // S→C: result(1) buff_id(4) = 5B

        // 조건 엔진 (세션 25)
        CONDITION_EVAL   = 210,  // C→S: node_count(1) root(1) {type(1) p1(4) p2(4) left(2) right(2)}*N = 13B/entry
        CONDITION_RESULT = 211,  // S→C: result(1u8) = 1B

        // 공간 쿼리 (세션 26)
        SPATIAL_QUERY_REQ  = 215,  // C→S: x(4f) y(4f) z(4f) radius(4f) filter(1u8) = 17B
        SPATIAL_QUERY_RESP = 216,  // S→C: count(1) {entity(8) dist(4f)}*N = 12B/entry

        // 루팅 (세션 27)
        LOOT_ROLL_REQ = 220,  // C→S: table_id(4u32)
        LOOT_RESULT   = 221,  // S→C: count(1) {item_id(4) count(2)}*N = 6B/entry

        // 퀘스트 (세션 28)
        QUEST_LIST_REQ       = 230,  // C→S: empty
        QUEST_LIST_RESP      = 231,  // S→C: count(1) {quest_id(4) state(1) progress(4) target(4)}*N = 13B/entry
        QUEST_ACCEPT         = 232,  // C→S: quest_id(4u32)
        QUEST_ACCEPT_RESULT  = 233,  // S→C: result(1) quest_id(4) = 5B
        QUEST_PROGRESS       = 234,  // C→S: quest_id(4u32)
        QUEST_COMPLETE       = 235,  // C→S: quest_id(4u32)
        QUEST_COMPLETE_RESULT = 236, // S→C: result(1) quest_id(4) reward_exp(4) reward_item_id(4) reward_item_count(2) = 15B
    }

    /// <summary>패킷 헤더 크기: 4(length) + 2(type) = 6바이트</summary>
    public static class PacketConst
    {
        public const int HEADER_SIZE = 6;
        public const int MAX_PACKET_SIZE = 8192;
    }

    /// <summary>로그인 결과 코드</summary>
    public enum LoginResult : byte
    {
        Success         = 0,
        AccountNotFound = 1,
        WrongPassword   = 2,
        AlreadyOnline   = 3,
    }

    /// <summary>캐릭터 정보 (CHAR_LIST_RESP 파싱용)</summary>
    public class CharacterInfo
    {
        public uint CharId;
        public string Name;
        public int Level;
        public int JobClass;    // 0=전사, 1=궁수, 2=마법사
    }

    /// <summary>게임 진입 결과 (ENTER_GAME 파싱용)</summary>
    public class EnterGameResult
    {
        public byte ResultCode;     // 0=성공
        public ulong EntityId;
        public int ZoneId;
        public float X, Y, Z;
    }

    /// <summary>공격 결과 코드</summary>
    public enum AttackResult : byte
    {
        SUCCESS         = 0,
        TARGET_NOT_FOUND = 1,
        TARGET_DEAD     = 2,
        OUT_OF_RANGE    = 3,
        COOLDOWN        = 4,
        ATTACKER_DEAD   = 5,
        SELF_ATTACK     = 6,
    }

    /// <summary>스탯 동기화 데이터 (STAT_SYNC 파싱용)</summary>
    public class StatSyncData
    {
        public int Level;
        public int HP, MaxHP;
        public int MP, MaxMP;
        public int ATK, DEF;
        public int EXP, EXPNext;
    }

    /// <summary>공격 결과 데이터 (ATTACK_RESULT 파싱용)</summary>
    public class AttackResultData
    {
        public AttackResult Result;
        public ulong AttackerId;
        public ulong TargetId;
        public int Damage;
        public int TargetHP;
        public int TargetMaxHP;
    }

    /// <summary>사망 데이터 (COMBAT_DIED 파싱용)</summary>
    public class CombatDiedData
    {
        public ulong DeadEntityId;
        public ulong KillerEntityId;
    }

    /// <summary>부활 결과 데이터 (RESPAWN_RESULT 파싱용)</summary>
    public class RespawnResultData
    {
        public byte ResultCode;
        public int HP, MP;
        public float X, Y, Z;
    }

    /// <summary>게이트 라우팅 결과 (GATE_ROUTE_RESP 파싱용)</summary>
    public class GateRouteResult
    {
        public byte ResultCode;     // 0=성공
        public ushort Port;
        public string IP;
    }

    /// <summary>몬스터 스폰 데이터 (MONSTER_SPAWN 파싱용)</summary>
    public class MonsterSpawnData
    {
        public ulong EntityId;
        public uint MonsterId;
        public uint Level;
        public int HP, MaxHP;
        public float X, Y, Z;
    }

    /// <summary>몬스터 리스폰 데이터 (MONSTER_RESPAWN 파싱용)</summary>
    public class MonsterRespawnData
    {
        public ulong EntityId;
        public int HP, MaxHP;
        public float X, Y, Z;
    }

    // ━━━ 세션 16~28 Result Code Enums ━━━

    /// <summary>존 이동 결과 코드</summary>
    public enum ZoneTransferResult : byte
    {
        SUCCESS         = 0,
        ZONE_NOT_EXIST  = 1,
        ALREADY_SAME_ZONE = 2,
    }

    /// <summary>아이템 결과 코드</summary>
    public enum ItemResult : byte
    {
        SUCCESS         = 0,
        INVENTORY_FULL  = 1,
        EMPTY_SLOT      = 2,
        ALREADY_EQUIPPED = 3,
        CANNOT_EQUIP    = 4,
    }

    /// <summary>버프 결과 코드</summary>
    public enum BuffResult : byte
    {
        SUCCESS       = 0,
        BUFF_NOT_FOUND = 1,
        NO_SLOT       = 2,
        INACTIVE      = 3,
    }

    /// <summary>퀘스트 상태</summary>
    public enum QuestState : byte
    {
        NONE        = 0,
        ACCEPTED    = 1,
        IN_PROGRESS = 2,
        COMPLETE    = 3,
        REWARDED    = 4,
    }

    /// <summary>퀘스트 수락 결과 코드</summary>
    public enum QuestAcceptResult : byte
    {
        SUCCESS             = 0,
        QUEST_NOT_FOUND     = 1,
        ALREADY_ACCEPTED    = 2,
        QUEST_FULL          = 3,
        PREREQUISITES_NOT_MET = 4,
        LEVEL_TOO_LOW       = 5,
        INCOMPLETE          = 6,
    }

    /// <summary>공간 쿼리 필터</summary>
    public enum SpatialFilter : byte
    {
        ALL           = 0,
        PLAYERS_ONLY  = 1,
        MONSTERS_ONLY = 2,
    }

    // ━━━ 세션 16~28 Data Classes ━━━

    /// <summary>존 이동 결과 (ZONE_TRANSFER_RESULT 파싱용)</summary>
    public class ZoneTransferResultData
    {
        public ZoneTransferResult Result;
        public uint ZoneId;
        public float X, Y, Z;
    }

    /// <summary>스킬 정보 (SKILL_LIST_RESP 파싱용)</summary>
    public class SkillInfo
    {
        public uint SkillId;
        public string Name;
        public uint CooldownMs;
        public uint Damage;
        public uint ManaCost;
        public uint Range;
        public byte SkillType;
    }

    /// <summary>스킬 사용 결과 (SKILL_RESULT 파싱용)</summary>
    public class SkillResultData
    {
        public byte Result;
        public uint SkillId;
        public ulong CasterId;
        public ulong TargetId;
        public int Damage;
        public int TargetHP;
    }

    /// <summary>파티 멤버 정보</summary>
    public class PartyMemberInfo
    {
        public ulong EntityId;
        public uint Level;
    }

    /// <summary>파티 정보 (PARTY_INFO 파싱용)</summary>
    public class PartyInfoData
    {
        public byte Result;
        public uint PartyId;
        public ulong LeaderId;
        public PartyMemberInfo[] Members;
    }

    /// <summary>인스턴스 진입 결과 (INSTANCE_ENTER 파싱용)</summary>
    public class InstanceEnterData
    {
        public byte Result;
        public uint InstanceId;
        public uint DungeonType;
    }

    /// <summary>인스턴스 퇴장 결과 (INSTANCE_LEAVE_RESULT 파싱용)</summary>
    public class InstanceLeaveResultData
    {
        public byte Result;
        public uint ZoneId;
        public float X, Y, Z;
    }

    /// <summary>인스턴스 정보 (INSTANCE_INFO 파싱용)</summary>
    public class InstanceInfoData
    {
        public uint InstanceId;
        public uint DungeonType;
        public byte PlayerCount;
        public byte MonsterCount;
    }

    /// <summary>매치 발견 알림 (MATCH_FOUND 파싱용)</summary>
    public class MatchFoundData
    {
        public uint MatchId;
        public uint DungeonType;
        public byte PlayerCount;
    }

    /// <summary>매치 상태 (MATCH_STATUS 파싱용)</summary>
    public class MatchStatusData
    {
        public byte Status;
        public uint QueuePosition;
    }

    /// <summary>인벤토리 아이템 (INVENTORY_RESP 파싱용)</summary>
    public class InventoryItemInfo
    {
        public byte Slot;
        public uint ItemId;
        public ushort Count;
        public byte Equipped;
    }

    /// <summary>아이템 추가 결과 (ITEM_ADD_RESULT 파싱용)</summary>
    public class ItemAddResultData
    {
        public ItemResult Result;
        public byte Slot;
        public uint ItemId;
        public ushort Count;
    }

    /// <summary>아이템 사용 결과 (ITEM_USE_RESULT 파싱용)</summary>
    public class ItemUseResultData
    {
        public byte Result;
        public byte Slot;
        public uint ItemId;
    }

    /// <summary>아이템 장착 결과 (ITEM_EQUIP_RESULT 파싱용)</summary>
    public class ItemEquipResultData
    {
        public byte Result;
        public byte Slot;
        public uint ItemId;
        public byte Equipped;
    }

    /// <summary>버프 정보 (BUFF_LIST_RESP 파싱용)</summary>
    public class BuffInfo
    {
        public uint BuffId;
        public uint RemainingMs;
        public byte Stacks;
    }

    /// <summary>버프 적용 결과 (BUFF_RESULT 파싱용)</summary>
    public class BuffResultData
    {
        public BuffResult Result;
        public uint BuffId;
        public byte Stacks;
        public uint DurationMs;
    }

    /// <summary>버프 제거 결과 (BUFF_REMOVE_RESP 파싱용)</summary>
    public class BuffRemoveRespData
    {
        public byte Result;
        public uint BuffId;
    }

    /// <summary>공간 쿼리 결과 항목 (SPATIAL_QUERY_RESP 파싱용)</summary>
    public class SpatialQueryEntry
    {
        public ulong EntityId;
        public float Distance;
    }

    /// <summary>루팅 아이템 (LOOT_RESULT 파싱용)</summary>
    public class LootItemEntry
    {
        public uint ItemId;
        public ushort Count;
    }

    /// <summary>퀘스트 정보 (QUEST_LIST_RESP 파싱용)</summary>
    public class QuestInfo
    {
        public uint QuestId;
        public QuestState State;
        public uint Progress;
        public uint Target;
    }

    /// <summary>퀘스트 수락 결과 (QUEST_ACCEPT_RESULT 파싱용)</summary>
    public class QuestAcceptResultData
    {
        public QuestAcceptResult Result;
        public uint QuestId;
    }

    /// <summary>퀘스트 완료 결과 (QUEST_COMPLETE_RESULT 파싱용)</summary>
    public class QuestCompleteResultData
    {
        public byte Result;
        public uint QuestId;
        public uint RewardExp;
        public uint RewardItemId;
        public ushort RewardItemCount;
    }
}
