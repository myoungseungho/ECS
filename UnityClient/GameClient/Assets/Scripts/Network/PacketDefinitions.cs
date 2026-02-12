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
}
