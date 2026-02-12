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

        // ━━━ 세션 16: 존 이동 ━━━

        /// <summary>ZONE_TRANSFER_REQ 빌드: target_zone_id(i32) = 4B</summary>
        public static byte[] ZoneTransferReq(int targetZoneId)
        {
            return Build(MsgType.ZONE_TRANSFER_REQ, BitConverter.GetBytes(targetZoneId));
        }

        /// <summary>ZONE_TRANSFER_RESULT 파싱: result(1) zone_id(4) x(4f) y(4f) z(4f) = 17B</summary>
        public static ZoneTransferResultData ParseZoneTransferResult(byte[] payload)
        {
            var d = new ZoneTransferResultData();
            d.Result = (ZoneTransferResult)payload[0];
            d.ZoneId = BitConverter.ToUInt32(payload, 1);
            d.X      = BitConverter.ToSingle(payload, 5);
            d.Y      = BitConverter.ToSingle(payload, 9);
            d.Z      = BitConverter.ToSingle(payload, 13);
            return d;
        }

        // ━━━ 세션 19: 스킬 ━━━

        /// <summary>SKILL_LIST_REQ 빌드: empty</summary>
        public static byte[] SkillListReq()
        {
            return Build(MsgType.SKILL_LIST_REQ);
        }

        /// <summary>SKILL_LIST_RESP 파싱: count(1) {id(4) name(16) cd_ms(4) dmg(4) mp(4) range(4) type(1)}*N = 37B/entry</summary>
        public static SkillInfo[] ParseSkillListResp(byte[] payload)
        {
            byte count = payload[0];
            var skills = new SkillInfo[count];
            int off = 1;

            for (int i = 0; i < count; i++)
            {
                var s = new SkillInfo();
                s.SkillId    = BitConverter.ToUInt32(payload, off); off += 4;

                int nameEnd = off;
                while (nameEnd < off + 16 && payload[nameEnd] != 0) nameEnd++;
                s.Name = Encoding.UTF8.GetString(payload, off, nameEnd - off);
                off += 16;

                s.CooldownMs = BitConverter.ToUInt32(payload, off); off += 4;
                s.Damage     = BitConverter.ToUInt32(payload, off); off += 4;
                s.ManaCost   = BitConverter.ToUInt32(payload, off); off += 4;
                s.Range      = BitConverter.ToUInt32(payload, off); off += 4;
                s.SkillType  = payload[off]; off += 1;
                skills[i] = s;
            }

            return skills;
        }

        /// <summary>SKILL_USE 빌드: skill_id(4) target_entity(8) = 12B</summary>
        public static byte[] SkillUse(uint skillId, ulong targetEntity)
        {
            byte[] payload = new byte[12];
            BitConverter.GetBytes(skillId).CopyTo(payload, 0);
            BitConverter.GetBytes(targetEntity).CopyTo(payload, 4);
            return Build(MsgType.SKILL_USE, payload);
        }

        /// <summary>SKILL_RESULT 파싱: result(1) skill_id(4) caster(8) target(8) damage(4i) target_hp(4i) = 29B</summary>
        public static SkillResultData ParseSkillResult(byte[] payload)
        {
            var d = new SkillResultData();
            d.Result   = payload[0];
            d.SkillId  = BitConverter.ToUInt32(payload, 1);
            d.CasterId = BitConverter.ToUInt64(payload, 5);
            d.TargetId = BitConverter.ToUInt64(payload, 13);
            d.Damage   = BitConverter.ToInt32(payload, 21);
            d.TargetHP = BitConverter.ToInt32(payload, 25);
            return d;
        }

        // ━━━ 세션 20: 파티 ━━━

        /// <summary>PARTY_CREATE 빌드: empty</summary>
        public static byte[] PartyCreate()
        {
            return Build(MsgType.PARTY_CREATE);
        }

        /// <summary>PARTY_INVITE 빌드: target_entity(8)</summary>
        public static byte[] PartyInvite(ulong targetEntity)
        {
            return Build(MsgType.PARTY_INVITE, BitConverter.GetBytes(targetEntity));
        }

        /// <summary>PARTY_ACCEPT 빌드: party_id(4)</summary>
        public static byte[] PartyAccept(uint partyId)
        {
            return Build(MsgType.PARTY_ACCEPT, BitConverter.GetBytes(partyId));
        }

        /// <summary>PARTY_LEAVE 빌드: empty</summary>
        public static byte[] PartyLeave()
        {
            return Build(MsgType.PARTY_LEAVE);
        }

        /// <summary>PARTY_KICK 빌드: target_entity(8)</summary>
        public static byte[] PartyKick(ulong targetEntity)
        {
            return Build(MsgType.PARTY_KICK, BitConverter.GetBytes(targetEntity));
        }

        /// <summary>PARTY_INFO 파싱: result(1) party_id(4) leader(8) count(1) {entity(8) level(4)}*N</summary>
        public static PartyInfoData ParsePartyInfo(byte[] payload)
        {
            var d = new PartyInfoData();
            d.Result   = payload[0];
            d.PartyId  = BitConverter.ToUInt32(payload, 1);
            d.LeaderId = BitConverter.ToUInt64(payload, 5);
            byte count = payload[13];
            d.Members = new PartyMemberInfo[count];
            int off = 14;
            for (int i = 0; i < count; i++)
            {
                var m = new PartyMemberInfo();
                m.EntityId = BitConverter.ToUInt64(payload, off); off += 8;
                m.Level    = BitConverter.ToUInt32(payload, off); off += 4;
                d.Members[i] = m;
            }
            return d;
        }

        // ━━━ 세션 21: 인스턴스 던전 ━━━

        /// <summary>INSTANCE_CREATE 빌드: dungeon_type(4)</summary>
        public static byte[] InstanceCreate(uint dungeonType)
        {
            return Build(MsgType.INSTANCE_CREATE, BitConverter.GetBytes(dungeonType));
        }

        /// <summary>INSTANCE_LEAVE 빌드: empty</summary>
        public static byte[] InstanceLeave()
        {
            return Build(MsgType.INSTANCE_LEAVE);
        }

        /// <summary>INSTANCE_ENTER 파싱: result(1) instance_id(4) dungeon_type(4) = 9B</summary>
        public static InstanceEnterData ParseInstanceEnter(byte[] payload)
        {
            var d = new InstanceEnterData();
            d.Result      = payload[0];
            d.InstanceId  = BitConverter.ToUInt32(payload, 1);
            d.DungeonType = BitConverter.ToUInt32(payload, 5);
            return d;
        }

        /// <summary>INSTANCE_LEAVE_RESULT 파싱: result(1) zone_id(4) x(4f) y(4f) z(4f) = 17B</summary>
        public static InstanceLeaveResultData ParseInstanceLeaveResult(byte[] payload)
        {
            var d = new InstanceLeaveResultData();
            d.Result = payload[0];
            d.ZoneId = BitConverter.ToUInt32(payload, 1);
            d.X      = BitConverter.ToSingle(payload, 5);
            d.Y      = BitConverter.ToSingle(payload, 9);
            d.Z      = BitConverter.ToSingle(payload, 13);
            return d;
        }

        /// <summary>INSTANCE_INFO 파싱: instance_id(4) dungeon_type(4) player_count(1) monster_count(1) = 10B</summary>
        public static InstanceInfoData ParseInstanceInfo(byte[] payload)
        {
            var d = new InstanceInfoData();
            d.InstanceId   = BitConverter.ToUInt32(payload, 0);
            d.DungeonType  = BitConverter.ToUInt32(payload, 4);
            d.PlayerCount  = payload[8];
            d.MonsterCount = payload[9];
            return d;
        }

        // ━━━ 세션 22: 매칭 ━━━

        /// <summary>MATCH_ENQUEUE 빌드: dungeon_type(4)</summary>
        public static byte[] MatchEnqueue(uint dungeonType)
        {
            return Build(MsgType.MATCH_ENQUEUE, BitConverter.GetBytes(dungeonType));
        }

        /// <summary>MATCH_DEQUEUE 빌드: empty</summary>
        public static byte[] MatchDequeue()
        {
            return Build(MsgType.MATCH_DEQUEUE);
        }

        /// <summary>MATCH_ACCEPT 빌드: match_id(4)</summary>
        public static byte[] MatchAccept(uint matchId)
        {
            return Build(MsgType.MATCH_ACCEPT, BitConverter.GetBytes(matchId));
        }

        /// <summary>MATCH_FOUND 파싱: match_id(4) dungeon_type(4) player_count(1) = 9B</summary>
        public static MatchFoundData ParseMatchFound(byte[] payload)
        {
            var d = new MatchFoundData();
            d.MatchId     = BitConverter.ToUInt32(payload, 0);
            d.DungeonType = BitConverter.ToUInt32(payload, 4);
            d.PlayerCount = payload[8];
            return d;
        }

        /// <summary>MATCH_STATUS 파싱: status(1) queue_position(4) = 5B</summary>
        public static MatchStatusData ParseMatchStatus(byte[] payload)
        {
            var d = new MatchStatusData();
            d.Status        = payload[0];
            d.QueuePosition = BitConverter.ToUInt32(payload, 1);
            return d;
        }

        // ━━━ 세션 23: 인벤토리 ━━━

        /// <summary>INVENTORY_REQ 빌드: empty</summary>
        public static byte[] InventoryReq()
        {
            return Build(MsgType.INVENTORY_REQ);
        }

        /// <summary>ITEM_ADD 빌드: item_id(4) count(2) = 6B</summary>
        public static byte[] ItemAdd(uint itemId, ushort count)
        {
            byte[] payload = new byte[6];
            BitConverter.GetBytes(itemId).CopyTo(payload, 0);
            BitConverter.GetBytes(count).CopyTo(payload, 4);
            return Build(MsgType.ITEM_ADD, payload);
        }

        /// <summary>ITEM_USE 빌드: slot(1)</summary>
        public static byte[] ItemUse(byte slot)
        {
            return Build(MsgType.ITEM_USE, new byte[] { slot });
        }

        /// <summary>ITEM_EQUIP 빌드: slot(1)</summary>
        public static byte[] ItemEquip(byte slot)
        {
            return Build(MsgType.ITEM_EQUIP, new byte[] { slot });
        }

        /// <summary>ITEM_UNEQUIP 빌드: slot(1)</summary>
        public static byte[] ItemUnequip(byte slot)
        {
            return Build(MsgType.ITEM_UNEQUIP, new byte[] { slot });
        }

        /// <summary>INVENTORY_RESP 파싱: count(1) {slot(1) item_id(4) count(2) equipped(1)}*N = 8B/entry</summary>
        public static InventoryItemInfo[] ParseInventoryResp(byte[] payload)
        {
            byte count = payload[0];
            var items = new InventoryItemInfo[count];
            int off = 1;
            for (int i = 0; i < count; i++)
            {
                var it = new InventoryItemInfo();
                it.Slot     = payload[off]; off += 1;
                it.ItemId   = BitConverter.ToUInt32(payload, off); off += 4;
                it.Count    = BitConverter.ToUInt16(payload, off); off += 2;
                it.Equipped = payload[off]; off += 1;
                items[i] = it;
            }
            return items;
        }

        /// <summary>ITEM_ADD_RESULT 파싱: result(1) slot(1) item_id(4) count(2) = 8B</summary>
        public static ItemAddResultData ParseItemAddResult(byte[] payload)
        {
            var d = new ItemAddResultData();
            d.Result = (ItemResult)payload[0];
            d.Slot   = payload[1];
            d.ItemId = BitConverter.ToUInt32(payload, 2);
            d.Count  = BitConverter.ToUInt16(payload, 6);
            return d;
        }

        /// <summary>ITEM_USE_RESULT 파싱: result(1) slot(1) item_id(4) = 6B</summary>
        public static ItemUseResultData ParseItemUseResult(byte[] payload)
        {
            var d = new ItemUseResultData();
            d.Result = payload[0];
            d.Slot   = payload[1];
            d.ItemId = BitConverter.ToUInt32(payload, 2);
            return d;
        }

        /// <summary>ITEM_EQUIP_RESULT 파싱: result(1) slot(1) item_id(4) equipped(1) = 7B</summary>
        public static ItemEquipResultData ParseItemEquipResult(byte[] payload)
        {
            var d = new ItemEquipResultData();
            d.Result   = payload[0];
            d.Slot     = payload[1];
            d.ItemId   = BitConverter.ToUInt32(payload, 2);
            d.Equipped = payload[6];
            return d;
        }

        // ━━━ 세션 24: 버프 ━━━

        /// <summary>BUFF_LIST_REQ 빌드: empty</summary>
        public static byte[] BuffListReq()
        {
            return Build(MsgType.BUFF_LIST_REQ);
        }

        /// <summary>BUFF_APPLY_REQ 빌드: buff_id(4)</summary>
        public static byte[] BuffApplyReq(uint buffId)
        {
            return Build(MsgType.BUFF_APPLY_REQ, BitConverter.GetBytes(buffId));
        }

        /// <summary>BUFF_REMOVE_REQ 빌드: buff_id(4)</summary>
        public static byte[] BuffRemoveReq(uint buffId)
        {
            return Build(MsgType.BUFF_REMOVE_REQ, BitConverter.GetBytes(buffId));
        }

        /// <summary>BUFF_LIST_RESP 파싱: count(1) {buff_id(4) remaining_ms(4) stacks(1)}*N = 9B/entry</summary>
        public static BuffInfo[] ParseBuffListResp(byte[] payload)
        {
            byte count = payload[0];
            var buffs = new BuffInfo[count];
            int off = 1;
            for (int i = 0; i < count; i++)
            {
                var b = new BuffInfo();
                b.BuffId      = BitConverter.ToUInt32(payload, off); off += 4;
                b.RemainingMs = BitConverter.ToUInt32(payload, off); off += 4;
                b.Stacks      = payload[off]; off += 1;
                buffs[i] = b;
            }
            return buffs;
        }

        /// <summary>BUFF_RESULT 파싱: result(1) buff_id(4) stacks(1) duration_ms(4) = 10B</summary>
        public static BuffResultData ParseBuffResult(byte[] payload)
        {
            var d = new BuffResultData();
            d.Result     = (BuffResult)payload[0];
            d.BuffId     = BitConverter.ToUInt32(payload, 1);
            d.Stacks     = payload[5];
            d.DurationMs = BitConverter.ToUInt32(payload, 6);
            return d;
        }

        /// <summary>BUFF_REMOVE_RESP 파싱: result(1) buff_id(4) = 5B</summary>
        public static BuffRemoveRespData ParseBuffRemoveResp(byte[] payload)
        {
            var d = new BuffRemoveRespData();
            d.Result = payload[0];
            d.BuffId = BitConverter.ToUInt32(payload, 1);
            return d;
        }

        // ━━━ 세션 26: 공간 쿼리 ━━━

        /// <summary>SPATIAL_QUERY_RESP 파싱: count(1) {entity(8) dist(4f)}*N = 12B/entry</summary>
        public static SpatialQueryEntry[] ParseSpatialQueryResp(byte[] payload)
        {
            byte count = payload[0];
            var results = new SpatialQueryEntry[count];
            int off = 1;
            for (int i = 0; i < count; i++)
            {
                var e = new SpatialQueryEntry();
                e.EntityId = BitConverter.ToUInt64(payload, off); off += 8;
                e.Distance = BitConverter.ToSingle(payload, off); off += 4;
                results[i] = e;
            }
            return results;
        }

        // ━━━ 세션 27: 루팅 ━━━

        /// <summary>LOOT_ROLL_REQ 빌드: table_id(4)</summary>
        public static byte[] LootRollReq(uint tableId)
        {
            return Build(MsgType.LOOT_ROLL_REQ, BitConverter.GetBytes(tableId));
        }

        /// <summary>LOOT_RESULT 파싱: count(1) {item_id(4) count(2)}*N = 6B/entry</summary>
        public static LootItemEntry[] ParseLootResult(byte[] payload)
        {
            byte count = payload[0];
            var items = new LootItemEntry[count];
            int off = 1;
            for (int i = 0; i < count; i++)
            {
                var it = new LootItemEntry();
                it.ItemId = BitConverter.ToUInt32(payload, off); off += 4;
                it.Count  = BitConverter.ToUInt16(payload, off); off += 2;
                items[i] = it;
            }
            return items;
        }

        // ━━━ 세션 28: 퀘스트 ━━━

        /// <summary>QUEST_LIST_REQ 빌드: empty</summary>
        public static byte[] QuestListReq()
        {
            return Build(MsgType.QUEST_LIST_REQ);
        }

        /// <summary>QUEST_ACCEPT 빌드: quest_id(4)</summary>
        public static byte[] QuestAccept(uint questId)
        {
            return Build(MsgType.QUEST_ACCEPT, BitConverter.GetBytes(questId));
        }

        /// <summary>QUEST_PROGRESS 빌드: quest_id(4)</summary>
        public static byte[] QuestProgress(uint questId)
        {
            return Build(MsgType.QUEST_PROGRESS, BitConverter.GetBytes(questId));
        }

        /// <summary>QUEST_COMPLETE 빌드: quest_id(4)</summary>
        public static byte[] QuestComplete(uint questId)
        {
            return Build(MsgType.QUEST_COMPLETE, BitConverter.GetBytes(questId));
        }

        /// <summary>QUEST_LIST_RESP 파싱: count(1) {quest_id(4) state(1) progress(4) target(4)}*N = 13B/entry</summary>
        public static QuestInfo[] ParseQuestListResp(byte[] payload)
        {
            byte count = payload[0];
            var quests = new QuestInfo[count];
            int off = 1;
            for (int i = 0; i < count; i++)
            {
                var q = new QuestInfo();
                q.QuestId  = BitConverter.ToUInt32(payload, off); off += 4;
                q.State    = (QuestState)payload[off]; off += 1;
                q.Progress = BitConverter.ToUInt32(payload, off); off += 4;
                q.Target   = BitConverter.ToUInt32(payload, off); off += 4;
                quests[i] = q;
            }
            return quests;
        }

        /// <summary>QUEST_ACCEPT_RESULT 파싱: result(1) quest_id(4) = 5B</summary>
        public static QuestAcceptResultData ParseQuestAcceptResult(byte[] payload)
        {
            var d = new QuestAcceptResultData();
            d.Result  = (QuestAcceptResult)payload[0];
            d.QuestId = BitConverter.ToUInt32(payload, 1);
            return d;
        }

        /// <summary>QUEST_COMPLETE_RESULT 파싱: result(1) quest_id(4) reward_exp(4) reward_item_id(4) reward_item_count(2) = 15B</summary>
        public static QuestCompleteResultData ParseQuestCompleteResult(byte[] payload)
        {
            var d = new QuestCompleteResultData();
            d.Result          = payload[0];
            d.QuestId         = BitConverter.ToUInt32(payload, 1);
            d.RewardExp       = BitConverter.ToUInt32(payload, 5);
            d.RewardItemId    = BitConverter.ToUInt32(payload, 9);
            d.RewardItemCount = BitConverter.ToUInt16(payload, 13);
            return d;
        }
    }
}
