// ━━━ PacketBuilder.cs ━━━
// 서버 BuildPacket() 함수의 C# 버전
// 패킷 조립(전송용) + 파싱(수신용) 유틸리티

using System;
using System.Text;

namespace Network
{
    public static class PacketBuilder
    {
        // ━━━ 패킷 조립 (전송용) ━━━

        /// <summary>헤더 + 페이로드 → 전송 가능한 바이트 배열</summary>
        public static byte[] Build(MsgType type, byte[] payload = null)
        {
            int payloadLen = payload?.Length ?? 0;
            int totalLen = PacketConst.HEADER_SIZE + payloadLen;
            byte[] buf = new byte[totalLen];

            // 헤더: length(4 LE) + type(2 LE)
            BitConverter.GetBytes((uint)totalLen).CopyTo(buf, 0);
            BitConverter.GetBytes((ushort)type).CopyTo(buf, 4);

            // 페이로드
            if (payload != null && payloadLen > 0)
                Buffer.BlockCopy(payload, 0, buf, PacketConst.HEADER_SIZE, payloadLen);

            return buf;
        }

        // ━━━ 전송 패킷 생성 헬퍼 ━━━

        /// <summary>GATE_ROUTE_REQ: 빈 페이로드</summary>
        public static byte[] GateRouteReq()
        {
            return Build(MsgType.GATE_ROUTE_REQ);
        }

        /// <summary>LOGIN: ID/PW 전송</summary>
        public static byte[] Login(string username, string password)
        {
            byte[] uBytes = Encoding.UTF8.GetBytes(username);
            byte[] pBytes = Encoding.UTF8.GetBytes(password);
            byte[] payload = new byte[1 + uBytes.Length + 1 + pBytes.Length];

            payload[0] = (byte)uBytes.Length;
            Buffer.BlockCopy(uBytes, 0, payload, 1, uBytes.Length);
            payload[1 + uBytes.Length] = (byte)pBytes.Length;
            Buffer.BlockCopy(pBytes, 0, payload, 2 + uBytes.Length, pBytes.Length);

            return Build(MsgType.LOGIN, payload);
        }

        /// <summary>CHAR_LIST_REQ: 빈 페이로드</summary>
        public static byte[] CharListReq()
        {
            return Build(MsgType.CHAR_LIST_REQ);
        }

        /// <summary>CHAR_SELECT: char_id 전송</summary>
        public static byte[] CharSelect(uint charId)
        {
            return Build(MsgType.CHAR_SELECT, BitConverter.GetBytes(charId));
        }

        /// <summary>CHANNEL_JOIN: channel_id 전송</summary>
        public static byte[] ChannelJoin(int channelId)
        {
            return Build(MsgType.CHANNEL_JOIN, BitConverter.GetBytes(channelId));
        }

        /// <summary>ZONE_ENTER: zone_id 전송</summary>
        public static byte[] ZoneEnter(int zoneId)
        {
            return Build(MsgType.ZONE_ENTER, BitConverter.GetBytes(zoneId));
        }

        /// <summary>STAT_QUERY: 빈 페이로드</summary>
        public static byte[] StatQuery()
        {
            return Build(MsgType.STAT_QUERY);
        }

        /// <summary>ATTACK_REQ: target_entity(8u64)</summary>
        public static byte[] AttackReq(ulong targetEntityId)
        {
            return Build(MsgType.ATTACK_REQ, BitConverter.GetBytes(targetEntityId));
        }

        /// <summary>RESPAWN_REQ: 빈 페이로드</summary>
        public static byte[] RespawnReq()
        {
            return Build(MsgType.RESPAWN_REQ);
        }

        /// <summary>MOVE: 위치 전송</summary>
        public static byte[] Move(float x, float y, float z)
        {
            byte[] payload = new byte[12];
            BitConverter.GetBytes(x).CopyTo(payload, 0);
            BitConverter.GetBytes(y).CopyTo(payload, 4);
            BitConverter.GetBytes(z).CopyTo(payload, 8);
            return Build(MsgType.MOVE, payload);
        }

        // ━━━ 수신 패킷 파싱 헬퍼 ━━━

        /// <summary>GATE_ROUTE_RESP 파싱</summary>
        public static GateRouteResult ParseGateRouteResp(byte[] payload)
        {
            var r = new GateRouteResult();
            r.ResultCode = payload[0];
            if (r.ResultCode != 0 || payload.Length < 4) return r;

            r.Port = BitConverter.ToUInt16(payload, 1);
            byte ipLen = payload[3];
            r.IP = Encoding.UTF8.GetString(payload, 4, ipLen);
            return r;
        }

        /// <summary>LOGIN_RESULT 파싱</summary>
        public static (LoginResult result, uint accountId) ParseLoginResult(byte[] payload)
        {
            var result = (LoginResult)payload[0];
            uint accountId = 0;
            if (payload.Length >= 5)
                accountId = BitConverter.ToUInt32(payload, 1);
            return (result, accountId);
        }

        /// <summary>CHAR_LIST_RESP 파싱</summary>
        public static CharacterInfo[] ParseCharListResp(byte[] payload)
        {
            byte count = payload[0];
            var chars = new CharacterInfo[count];
            int off = 1;

            for (int i = 0; i < count; i++)
            {
                var c = new CharacterInfo();
                c.CharId = BitConverter.ToUInt32(payload, off); off += 4;

                // name: 32바이트 (null-terminated)
                int nameEnd = off;
                while (nameEnd < off + 32 && payload[nameEnd] != 0) nameEnd++;
                c.Name = Encoding.UTF8.GetString(payload, off, nameEnd - off);
                off += 32;

                c.Level = BitConverter.ToInt32(payload, off); off += 4;
                c.JobClass = BitConverter.ToInt32(payload, off); off += 4;
                chars[i] = c;
            }

            return chars;
        }

        /// <summary>ENTER_GAME 파싱</summary>
        public static EnterGameResult ParseEnterGame(byte[] payload)
        {
            var r = new EnterGameResult();
            r.ResultCode = payload[0];
            if (r.ResultCode != 0 || payload.Length < 25) return r;

            r.EntityId = BitConverter.ToUInt64(payload, 1);
            r.ZoneId = BitConverter.ToInt32(payload, 9);
            r.X = BitConverter.ToSingle(payload, 13);
            r.Y = BitConverter.ToSingle(payload, 17);
            r.Z = BitConverter.ToSingle(payload, 21);
            return r;
        }

        /// <summary>APPEAR / MOVE_BROADCAST 파싱: entity(8) x(4f) y(4f) z(4f)</summary>
        public static (ulong entityId, float x, float y, float z) ParseEntityPosition(byte[] payload)
        {
            ulong eid = BitConverter.ToUInt64(payload, 0);
            float x = BitConverter.ToSingle(payload, 8);
            float y = BitConverter.ToSingle(payload, 12);
            float z = BitConverter.ToSingle(payload, 16);
            return (eid, x, y, z);
        }

        /// <summary>DISAPPEAR 파싱: entity(8)</summary>
        public static ulong ParseDisappear(byte[] payload)
        {
            return BitConverter.ToUInt64(payload, 0);
        }

        /// <summary>STAT_SYNC 파싱: 9 x int32 = 36B</summary>
        public static StatSyncData ParseStatSync(byte[] payload)
        {
            var d = new StatSyncData();
            d.Level  = BitConverter.ToInt32(payload, 0);
            d.HP     = BitConverter.ToInt32(payload, 4);
            d.MaxHP  = BitConverter.ToInt32(payload, 8);
            d.MP     = BitConverter.ToInt32(payload, 12);
            d.MaxMP  = BitConverter.ToInt32(payload, 16);
            d.ATK    = BitConverter.ToInt32(payload, 20);
            d.DEF    = BitConverter.ToInt32(payload, 24);
            d.EXP    = BitConverter.ToInt32(payload, 28);
            d.EXPNext = BitConverter.ToInt32(payload, 32);
            return d;
        }

        /// <summary>ATTACK_RESULT 파싱: result(1) attacker(8) target(8) damage(4) target_hp(4) target_max_hp(4) = 29B</summary>
        public static AttackResultData ParseAttackResult(byte[] payload)
        {
            var d = new AttackResultData();
            d.Result      = (AttackResult)payload[0];
            d.AttackerId  = BitConverter.ToUInt64(payload, 1);
            d.TargetId    = BitConverter.ToUInt64(payload, 9);
            d.Damage      = BitConverter.ToInt32(payload, 17);
            d.TargetHP    = BitConverter.ToInt32(payload, 21);
            d.TargetMaxHP = BitConverter.ToInt32(payload, 25);
            return d;
        }

        /// <summary>COMBAT_DIED 파싱: dead_entity(8) killer_entity(8) = 16B</summary>
        public static CombatDiedData ParseCombatDied(byte[] payload)
        {
            var d = new CombatDiedData();
            d.DeadEntityId   = BitConverter.ToUInt64(payload, 0);
            d.KillerEntityId = BitConverter.ToUInt64(payload, 8);
            return d;
        }

        /// <summary>RESPAWN_RESULT 파싱: result(1) hp(4) mp(4) x(4f) y(4f) z(4f) = 21B</summary>
        public static RespawnResultData ParseRespawnResult(byte[] payload)
        {
            var d = new RespawnResultData();
            d.ResultCode = payload[0];
            d.HP = BitConverter.ToInt32(payload, 1);
            d.MP = BitConverter.ToInt32(payload, 5);
            d.X  = BitConverter.ToSingle(payload, 9);
            d.Y  = BitConverter.ToSingle(payload, 13);
            d.Z  = BitConverter.ToSingle(payload, 17);
            return d;
        }

        /// <summary>CHANNEL_INFO / ZONE_INFO 파싱: id(4 int32)</summary>
        public static int ParseIntResponse(byte[] payload)
        {
            return BitConverter.ToInt32(payload, 0);
        }

        /// <summary>MONSTER_SPAWN 파싱: entity(8) monster_id(4) level(4) hp(4) max_hp(4) x(4f) y(4f) z(4f) = 36B</summary>
        public static MonsterSpawnData ParseMonsterSpawn(byte[] payload)
        {
            var d = new MonsterSpawnData();
            d.EntityId  = BitConverter.ToUInt64(payload, 0);
            d.MonsterId = BitConverter.ToUInt32(payload, 8);
            d.Level     = BitConverter.ToUInt32(payload, 12);
            d.HP        = BitConverter.ToInt32(payload, 16);
            d.MaxHP     = BitConverter.ToInt32(payload, 20);
            d.X         = BitConverter.ToSingle(payload, 24);
            d.Y         = BitConverter.ToSingle(payload, 28);
            d.Z         = BitConverter.ToSingle(payload, 32);
            return d;
        }

        /// <summary>MONSTER_RESPAWN 파싱: entity(8) hp(4) max_hp(4) x(4f) y(4f) z(4f) = 28B</summary>
        public static MonsterRespawnData ParseMonsterRespawn(byte[] payload)
        {
            var d = new MonsterRespawnData();
            d.EntityId = BitConverter.ToUInt64(payload, 0);
            d.HP       = BitConverter.ToInt32(payload, 8);
            d.MaxHP    = BitConverter.ToInt32(payload, 12);
            d.X        = BitConverter.ToSingle(payload, 16);
            d.Y        = BitConverter.ToSingle(payload, 20);
            d.Z        = BitConverter.ToSingle(payload, 24);
            return d;
        }
    }
}
