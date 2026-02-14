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

        /// <summary>MOVE: 위치 전송 (Model C: +timestamp 16B)</summary>
        public static byte[] Move(float x, float y, float z, uint timestampMs = 0)
        {
            byte[] payload = new byte[16];
            BitConverter.GetBytes(x).CopyTo(payload, 0);
            BitConverter.GetBytes(y).CopyTo(payload, 4);
            BitConverter.GetBytes(z).CopyTo(payload, 8);
            BitConverter.GetBytes(timestampMs).CopyTo(payload, 12);
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

        /// <summary>SKILL_LIST_RESP 파싱: count(1) {id(4) name(16) cd_ms(4) dmg(4) mp(4) range(4) type(1) level(1) effect(1) min_level(4)}*N = 43B/entry</summary>
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
                // 세션 33 확장 필드 (하위호환: 43B entry일 때만)
                if (off + 6 <= payload.Length && (off - 1 + 6) <= 1 + count * 43)
                {
                    s.Level    = payload[off]; off += 1;
                    s.Effect   = (SkillEffect)payload[off]; off += 1;
                    s.MinLevel = BitConverter.ToInt32(payload, off); off += 4;
                }
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

        // ━━━ 세션 35: 이동 검증 (Model C) ━━━

        /// <summary>POSITION_CORRECTION 파싱: x(4f) y(4f) z(4f) = 12B</summary>
        public static (float x, float y, float z) ParsePositionCorrection(byte[] payload)
        {
            float x = BitConverter.ToSingle(payload, 0);
            float y = BitConverter.ToSingle(payload, 4);
            float z = BitConverter.ToSingle(payload, 8);
            return (x, y, z);
        }

        // ━━━ 세션 30: 채팅 ━━━

        /// <summary>CHAT_SEND 빌드: channel(1) msg_len(1) message(N)</summary>
        public static byte[] ChatSend(ChatChannel channel, string message)
        {
            byte[] msgBytes = Encoding.UTF8.GetBytes(message);
            byte[] payload = new byte[2 + msgBytes.Length];
            payload[0] = (byte)channel;
            payload[1] = (byte)msgBytes.Length;
            Buffer.BlockCopy(msgBytes, 0, payload, 2, msgBytes.Length);
            return Build(MsgType.CHAT_SEND, payload);
        }

        /// <summary>WHISPER_SEND 빌드: target_name_len(1) target_name(N) msg_len(1) message(N)</summary>
        public static byte[] WhisperSend(string targetName, string message)
        {
            byte[] nameBytes = Encoding.UTF8.GetBytes(targetName);
            byte[] msgBytes = Encoding.UTF8.GetBytes(message);
            byte[] payload = new byte[1 + nameBytes.Length + 1 + msgBytes.Length];
            payload[0] = (byte)nameBytes.Length;
            Buffer.BlockCopy(nameBytes, 0, payload, 1, nameBytes.Length);
            payload[1 + nameBytes.Length] = (byte)msgBytes.Length;
            Buffer.BlockCopy(msgBytes, 0, payload, 2 + nameBytes.Length, msgBytes.Length);
            return Build(MsgType.WHISPER_SEND, payload);
        }

        /// <summary>CHAT_MESSAGE 파싱: channel(1) sender_entity(8) sender_name(32) msg_len(1) message(N)</summary>
        public static ChatMessageData ParseChatMessage(byte[] payload)
        {
            var d = new ChatMessageData();
            d.Channel = (ChatChannel)payload[0];
            d.SenderEntityId = BitConverter.ToUInt64(payload, 1);
            // sender_name: 32바이트 null-terminated
            int nameEnd = 9;
            while (nameEnd < 9 + 32 && payload[nameEnd] != 0) nameEnd++;
            d.SenderName = Encoding.UTF8.GetString(payload, 9, nameEnd - 9);
            byte msgLen = payload[41];
            d.Message = Encoding.UTF8.GetString(payload, 42, msgLen);
            return d;
        }

        /// <summary>WHISPER_RESULT 파싱: result(1) direction(1) other_name(32) msg_len(1) message(N)</summary>
        public static WhisperResultData ParseWhisperResult(byte[] payload)
        {
            var d = new WhisperResultData();
            d.Result = (WhisperResult)payload[0];
            d.Direction = (WhisperDirection)payload[1];
            // other_name: 32바이트 null-terminated
            int nameEnd = 2;
            while (nameEnd < 2 + 32 && payload[nameEnd] != 0) nameEnd++;
            d.OtherName = Encoding.UTF8.GetString(payload, 2, nameEnd - 2);
            byte msgLen = payload[34];
            d.Message = Encoding.UTF8.GetString(payload, 35, msgLen);
            return d;
        }

        /// <summary>SYSTEM_MESSAGE 파싱: msg_len(1) message(N)</summary>
        public static string ParseSystemMessage(byte[] payload)
        {
            byte msgLen = payload[0];
            return Encoding.UTF8.GetString(payload, 1, msgLen);
        }

        // ━━━ 세션 32: NPC 상점 ━━━

        /// <summary>SHOP_OPEN 빌드: npc_id(4)</summary>
        public static byte[] ShopOpen(uint npcId)
        {
            return Build(MsgType.SHOP_OPEN, BitConverter.GetBytes(npcId));
        }

        /// <summary>SHOP_BUY 빌드: npc_id(4) item_id(4) count(2) = 10B</summary>
        public static byte[] ShopBuy(uint npcId, uint itemId, ushort count)
        {
            byte[] payload = new byte[10];
            BitConverter.GetBytes(npcId).CopyTo(payload, 0);
            BitConverter.GetBytes(itemId).CopyTo(payload, 4);
            BitConverter.GetBytes(count).CopyTo(payload, 8);
            return Build(MsgType.SHOP_BUY, payload);
        }

        /// <summary>SHOP_SELL 빌드: slot(1) count(2) = 3B</summary>
        public static byte[] ShopSell(byte slot, ushort count)
        {
            byte[] payload = new byte[3];
            payload[0] = slot;
            BitConverter.GetBytes(count).CopyTo(payload, 1);
            return Build(MsgType.SHOP_SELL, payload);
        }

        /// <summary>SHOP_LIST 파싱: npc_id(4) count(1) {item_id(4) price(4) stock(2)}*N = 10B/entry</summary>
        public static ShopListData ParseShopList(byte[] payload)
        {
            var d = new ShopListData();
            d.NpcId = BitConverter.ToUInt32(payload, 0);
            byte count = payload[4];
            d.Items = new ShopItemInfo[count];
            int off = 5;
            for (int i = 0; i < count; i++)
            {
                var it = new ShopItemInfo();
                it.ItemId = BitConverter.ToUInt32(payload, off); off += 4;
                it.Price  = BitConverter.ToUInt32(payload, off); off += 4;
                it.Stock  = BitConverter.ToInt16(payload, off); off += 2;
                d.Items[i] = it;
            }
            return d;
        }

        /// <summary>SHOP_RESULT 파싱: result(1) action(1) item_id(4) count(2) gold(4) = 12B</summary>
        public static ShopResultData ParseShopResult(byte[] payload)
        {
            var d = new ShopResultData();
            d.Result = (ShopResult)payload[0];
            d.Action = (ShopAction)payload[1];
            d.ItemId = BitConverter.ToUInt32(payload, 2);
            d.Count  = BitConverter.ToUInt16(payload, 6);
            d.Gold   = BitConverter.ToUInt32(payload, 8);
            return d;
        }

        // ━━━ 세션 33: 스킬 레벨업 ━━━

        /// <summary>SKILL_LEVEL_UP 빌드: skill_id(4)</summary>
        public static byte[] SkillLevelUp(uint skillId)
        {
            return Build(MsgType.SKILL_LEVEL_UP, BitConverter.GetBytes(skillId));
        }

        /// <summary>SKILL_LEVEL_UP_RESULT 파싱: result(1) skill_id(4) new_level(1) skill_points(4) = 10B</summary>
        public static SkillLevelUpResultData ParseSkillLevelUpResult(byte[] payload)
        {
            var d = new SkillLevelUpResultData();
            d.Result      = (SkillLevelUpResult)payload[0];
            d.SkillId     = BitConverter.ToUInt32(payload, 1);
            d.NewLevel    = payload[5];
            d.SkillPoints = BitConverter.ToUInt32(payload, 6);
            return d;
        }

        /// <summary>SKILL_POINT_INFO 파싱: skill_points(4) total_spent(4) = 8B</summary>
        public static SkillPointInfoData ParseSkillPointInfo(byte[] payload)
        {
            var d = new SkillPointInfoData();
            d.SkillPoints = BitConverter.ToUInt32(payload, 0);
            d.TotalSpent  = BitConverter.ToUInt32(payload, 4);
            return d;
        }

        // ━━━ 세션 34: 보스 메카닉 ━━━

        /// <summary>BOSS_SPAWN 파싱: entity(8) boss_id(4) name(32) level(4) hp(4) max_hp(4) phase(1) = 57B</summary>
        public static BossSpawnData ParseBossSpawn(byte[] payload)
        {
            var d = new BossSpawnData();
            d.EntityId = BitConverter.ToUInt64(payload, 0);
            d.BossId   = BitConverter.ToUInt32(payload, 8);
            // name: 32바이트 null-terminated
            int nameEnd = 12;
            while (nameEnd < 12 + 32 && payload[nameEnd] != 0) nameEnd++;
            d.Name = Encoding.UTF8.GetString(payload, 12, nameEnd - 12);
            d.Level = BitConverter.ToInt32(payload, 44);
            d.HP    = BitConverter.ToInt32(payload, 48);
            d.MaxHP = BitConverter.ToInt32(payload, 52);
            d.Phase = payload[56];
            return d;
        }

        /// <summary>BOSS_PHASE_CHANGE 파싱: entity(8) boss_id(4) new_phase(1) hp(4) max_hp(4) = 21B</summary>
        public static BossPhaseChangeData ParseBossPhaseChange(byte[] payload)
        {
            var d = new BossPhaseChangeData();
            d.EntityId = BitConverter.ToUInt64(payload, 0);
            d.BossId   = BitConverter.ToUInt32(payload, 8);
            d.NewPhase = payload[12];
            d.HP       = BitConverter.ToInt32(payload, 13);
            d.MaxHP    = BitConverter.ToInt32(payload, 17);
            return d;
        }

        /// <summary>BOSS_SPECIAL_ATTACK 파싱: entity(8) boss_id(4) attack_type(1) damage(4) = 17B</summary>
        public static BossSpecialAttackData ParseBossSpecialAttack(byte[] payload)
        {
            var d = new BossSpecialAttackData();
            d.EntityId   = BitConverter.ToUInt64(payload, 0);
            d.BossId     = BitConverter.ToUInt32(payload, 8);
            d.AttackType = (BossAttackType)payload[12];
            d.Damage     = BitConverter.ToInt32(payload, 13);
            return d;
        }

        /// <summary>BOSS_ENRAGE 파싱: entity(8) boss_id(4) = 12B</summary>
        public static BossEnrageData ParseBossEnrage(byte[] payload)
        {
            var d = new BossEnrageData();
            d.EntityId = BitConverter.ToUInt64(payload, 0);
            d.BossId   = BitConverter.ToUInt32(payload, 8);
            return d;
        }

        /// <summary>BOSS_DEFEATED 파싱: entity(8) boss_id(4) killer_entity(8) = 20B</summary>
        public static BossDefeatedData ParseBossDefeated(byte[] payload)
        {
            var d = new BossDefeatedData();
            d.EntityId       = BitConverter.ToUInt64(payload, 0);
            d.BossId         = BitConverter.ToUInt32(payload, 8);
            d.KillerEntityId = BitConverter.ToUInt64(payload, 12);
            return d;
        }

        // ━━━ 세션 36: 몬스터 AI ━━━

        /// <summary>MONSTER_MOVE 파싱: entity(8) x(4f) y(4f) z(4f) = 20B</summary>
        public static MonsterMoveData ParseMonsterMove(byte[] payload)
        {
            var d = new MonsterMoveData();
            d.EntityId = BitConverter.ToUInt64(payload, 0);
            d.X = BitConverter.ToSingle(payload, 8);
            d.Y = BitConverter.ToSingle(payload, 12);
            d.Z = BitConverter.ToSingle(payload, 16);
            return d;
        }

        /// <summary>MONSTER_AGGRO 파싱: monster_entity(8) target_entity(8) = 16B</summary>
        public static MonsterAggroData ParseMonsterAggro(byte[] payload)
        {
            var d = new MonsterAggroData();
            d.MonsterEntityId = BitConverter.ToUInt64(payload, 0);
            d.TargetEntityId  = BitConverter.ToUInt64(payload, 8);
            return d;
        }

        // ━━━ 세션 37: 어드민/핫리로드 ━━━

        /// <summary>ADMIN_RELOAD 빌드: name_len(1) name(N)</summary>
        public static byte[] AdminReload(string configName = "")
        {
            byte[] nameBytes = Encoding.UTF8.GetBytes(configName);
            byte[] payload = new byte[1 + nameBytes.Length];
            payload[0] = (byte)nameBytes.Length;
            if (nameBytes.Length > 0)
                Buffer.BlockCopy(nameBytes, 0, payload, 1, nameBytes.Length);
            return Build(MsgType.ADMIN_RELOAD, payload);
        }

        /// <summary>ADMIN_GET_CONFIG 빌드: name_len(1) name(N) key_len(1) key(N)</summary>
        public static byte[] AdminGetConfig(string configName, string key)
        {
            byte[] nameBytes = Encoding.UTF8.GetBytes(configName);
            byte[] keyBytes = Encoding.UTF8.GetBytes(key);
            byte[] payload = new byte[1 + nameBytes.Length + 1 + keyBytes.Length];
            payload[0] = (byte)nameBytes.Length;
            Buffer.BlockCopy(nameBytes, 0, payload, 1, nameBytes.Length);
            payload[1 + nameBytes.Length] = (byte)keyBytes.Length;
            Buffer.BlockCopy(keyBytes, 0, payload, 2 + nameBytes.Length, keyBytes.Length);
            return Build(MsgType.ADMIN_GET_CONFIG, payload);
        }

        /// <summary>ADMIN_RELOAD_RESULT 파싱: result(1) version(4) reload_count(4) name_len(1) name(N)</summary>
        public static AdminReloadResultData ParseAdminReloadResult(byte[] payload)
        {
            var d = new AdminReloadResultData();
            d.Result      = payload[0];
            d.Version     = BitConverter.ToUInt32(payload, 1);
            d.ReloadCount = BitConverter.ToUInt32(payload, 5);
            byte nameLen = payload[9];
            d.Name = nameLen > 0 ? Encoding.UTF8.GetString(payload, 10, nameLen) : "";
            return d;
        }

        /// <summary>ADMIN_CONFIG_RESP 파싱: found(1) value_len(2) value(N)</summary>
        public static AdminConfigRespData ParseAdminConfigResp(byte[] payload)
        {
            var d = new AdminConfigRespData();
            d.Found = payload[0] == 1;
            ushort valueLen = BitConverter.ToUInt16(payload, 1);
            d.Value = valueLen > 0 ? Encoding.UTF8.GetString(payload, 3, valueLen) : "";
            return d;
        }

        // ━━━ S033: 서버 선택 ━━━

        /// <summary>SERVER_LIST_REQ 빌드: empty</summary>
        public static byte[] ServerListReq()
        {
            return Build(MsgType.SERVER_LIST_REQ);
        }

        /// <summary>SERVER_LIST 파싱: count(1) {name(32) status(1) population(2)}*N = 35B/entry</summary>
        public static ServerInfo[] ParseServerList(byte[] payload)
        {
            byte count = payload[0];
            var servers = new ServerInfo[count];
            int off = 1;
            for (int i = 0; i < count; i++)
            {
                var s = new ServerInfo();
                int nameEnd = off;
                while (nameEnd < off + 32 && payload[nameEnd] != 0) nameEnd++;
                s.Name = Encoding.UTF8.GetString(payload, off, nameEnd - off);
                off += 32;
                s.Status = (ServerStatus)payload[off]; off += 1;
                s.Population = BitConverter.ToUInt16(payload, off); off += 2;
                servers[i] = s;
            }
            return servers;
        }

        // ━━━ S033: 캐릭터 CRUD ━━━

        /// <summary>CHARACTER_LIST_REQ 빌드: empty</summary>
        public static byte[] CharacterListReq()
        {
            return Build(MsgType.CHARACTER_LIST_REQ);
        }

        /// <summary>CHARACTER_LIST 파싱: count(1) {name(16) class(1) level(2) zone_id(4)}*N = 23B/entry</summary>
        public static CharacterData[] ParseCharacterList(byte[] payload)
        {
            byte count = payload[0];
            var chars = new CharacterData[count];
            int off = 1;
            for (int i = 0; i < count; i++)
            {
                var c = new CharacterData();
                int nameEnd = off;
                while (nameEnd < off + 16 && payload[nameEnd] != 0) nameEnd++;
                c.Name = Encoding.UTF8.GetString(payload, off, nameEnd - off);
                off += 16;
                c.ClassType = (CharacterClass)payload[off]; off += 1;
                c.Level = BitConverter.ToUInt16(payload, off); off += 2;
                c.ZoneId = BitConverter.ToUInt32(payload, off); off += 4;
                chars[i] = c;
            }
            return chars;
        }

        /// <summary>CHARACTER_CREATE 빌드: name_len(1) name(var) class(1)</summary>
        public static byte[] CharacterCreate(string name, CharacterClass classType)
        {
            byte[] nameBytes = Encoding.UTF8.GetBytes(name);
            byte[] payload = new byte[1 + nameBytes.Length + 1];
            payload[0] = (byte)nameBytes.Length;
            Buffer.BlockCopy(nameBytes, 0, payload, 1, nameBytes.Length);
            payload[1 + nameBytes.Length] = (byte)classType;
            return Build(MsgType.CHARACTER_CREATE, payload);
        }

        /// <summary>CHARACTER_CREATE_RESULT 파싱: result(1) char_id(4) = 5B</summary>
        public static CharacterCreateResultData ParseCharacterCreateResult(byte[] payload)
        {
            var d = new CharacterCreateResultData();
            d.Result = (CharacterCreateResult)payload[0];
            d.CharId = BitConverter.ToUInt32(payload, 1);
            return d;
        }

        /// <summary>CHARACTER_DELETE 빌드: char_id(4)</summary>
        public static byte[] CharacterDelete(uint charId)
        {
            return Build(MsgType.CHARACTER_DELETE, BitConverter.GetBytes(charId));
        }

        /// <summary>CHARACTER_DELETE_RESULT 파싱: result(1) char_id(4) = 5B</summary>
        public static CharacterDeleteResultData ParseCharacterDeleteResult(byte[] payload)
        {
            var d = new CharacterDeleteResultData();
            d.Result = (CharacterDeleteResult)payload[0];
            d.CharId = BitConverter.ToUInt32(payload, 1);
            return d;
        }

        // ━━━ S033: 튜토리얼 ━━━

        /// <summary>TUTORIAL_STEP_COMPLETE 빌드: step_id(1)</summary>
        public static byte[] TutorialStepComplete(byte stepId)
        {
            return Build(MsgType.TUTORIAL_STEP_COMPLETE, new byte[] { stepId });
        }

        /// <summary>TUTORIAL_REWARD 파싱: step_id(1) reward_type(1) amount(4) = 6B</summary>
        public static TutorialRewardData ParseTutorialReward(byte[] payload)
        {
            var d = new TutorialRewardData();
            d.StepId = payload[0];
            d.RewardType = (TutorialRewardType)payload[1];
            d.Amount = BitConverter.ToUInt32(payload, 2);
            return d;
        }

        // ━━━ S034: NPC 인터랙션 ━━━

        /// <summary>NPC_INTERACT 빌드: npc_entity_id(4)</summary>
        public static byte[] NpcInteract(uint npcEntityId)
        {
            return Build(MsgType.NPC_INTERACT, BitConverter.GetBytes(npcEntityId));
        }

        /// <summary>NPC_DIALOG 파싱: npc_id(2) npc_type(1) line_count(1) {speaker_len(1) speaker(N) text_len(2) text(N)}*N quest_count(1) {quest_id(4)}*N</summary>
        public static NpcDialogData ParseNpcDialog(byte[] payload)
        {
            var d = new NpcDialogData();
            int off = 0;
            d.NpcId = BitConverter.ToUInt16(payload, off); off += 2;
            d.Type = (NpcType)payload[off]; off += 1;
            byte lineCount = payload[off]; off += 1;
            d.Lines = new NpcDialogLine[lineCount];
            for (int i = 0; i < lineCount; i++)
            {
                var line = new NpcDialogLine();
                byte speakerLen = payload[off]; off += 1;
                line.Speaker = Encoding.UTF8.GetString(payload, off, speakerLen); off += speakerLen;
                ushort textLen = BitConverter.ToUInt16(payload, off); off += 2;
                line.Text = Encoding.UTF8.GetString(payload, off, textLen); off += textLen;
                d.Lines[i] = line;
            }
            byte questCount = payload[off]; off += 1;
            d.QuestIds = new uint[questCount];
            for (int i = 0; i < questCount; i++)
            {
                d.QuestIds[i] = BitConverter.ToUInt32(payload, off); off += 4;
            }
            return d;
        }

        // ━━━ S034: 강화 ━━━

        /// <summary>ENHANCE_REQ 빌드: slot_index(1)</summary>
        public static byte[] EnhanceReq(byte slotIndex)
        {
            return Build(MsgType.ENHANCE_REQ, new byte[] { slotIndex });
        }

        /// <summary>ENHANCE_RESULT 파싱: slot_index(1) result(1) new_level(1) = 3B</summary>
        public static EnhanceResultData ParseEnhanceResult(byte[] payload)
        {
            var d = new EnhanceResultData();
            d.SlotIndex = payload[0];
            d.Result = (EnhanceResult)payload[1];
            d.NewLevel = payload[2];
            return d;
        }

        // ━━━ S029: 문파 (Guild) ━━━

        /// <summary>GUILD_CREATE 빌드: name_len(1) name(N)</summary>
        public static byte[] GuildCreate(string guildName)
        {
            byte[] nameBytes = Encoding.UTF8.GetBytes(guildName);
            byte[] payload = new byte[1 + nameBytes.Length];
            payload[0] = (byte)nameBytes.Length;
            if (nameBytes.Length > 0)
                Buffer.BlockCopy(nameBytes, 0, payload, 1, nameBytes.Length);
            return Build(MsgType.GUILD_CREATE, payload);
        }

        /// <summary>GUILD_DISBAND 빌드: empty</summary>
        public static byte[] GuildDisband()
        {
            return Build(MsgType.GUILD_DISBAND);
        }

        /// <summary>GUILD_INVITE 빌드: target_entity(8)</summary>
        public static byte[] GuildInvite(ulong targetEntity)
        {
            return Build(MsgType.GUILD_INVITE, BitConverter.GetBytes(targetEntity));
        }

        /// <summary>GUILD_ACCEPT 빌드: empty</summary>
        public static byte[] GuildAccept()
        {
            return Build(MsgType.GUILD_ACCEPT);
        }

        /// <summary>GUILD_LEAVE 빌드: empty</summary>
        public static byte[] GuildLeave()
        {
            return Build(MsgType.GUILD_LEAVE);
        }

        /// <summary>GUILD_KICK 빌드: target_entity(8)</summary>
        public static byte[] GuildKick(ulong targetEntity)
        {
            return Build(MsgType.GUILD_KICK, BitConverter.GetBytes(targetEntity));
        }

        /// <summary>GUILD_INFO_REQ 빌드: empty</summary>
        public static byte[] GuildInfoReq()
        {
            return Build(MsgType.GUILD_INFO_REQ);
        }

        /// <summary>GUILD_LIST_REQ 빌드: empty</summary>
        public static byte[] GuildListReq()
        {
            return Build(MsgType.GUILD_LIST_REQ);
        }

        /// <summary>GUILD_INFO 파싱: guild_id(4) name(16) leader(8) count(1) {entity(8) rank(1)}*N</summary>
        public static GuildInfoData ParseGuildInfo(byte[] payload)
        {
            var d = new GuildInfoData();
            int off = 0;
            d.GuildId = BitConverter.ToUInt32(payload, off); off += 4;
            int nameEnd = off;
            while (nameEnd < off + 16 && payload[nameEnd] != 0) nameEnd++;
            d.Name = Encoding.UTF8.GetString(payload, off, nameEnd - off);
            off += 16;
            d.LeaderId = BitConverter.ToUInt64(payload, off); off += 8;
            byte count = payload[off]; off += 1;
            d.Members = new GuildMemberInfo[count];
            for (int i = 0; i < count; i++)
            {
                var m = new GuildMemberInfo();
                m.EntityId = BitConverter.ToUInt64(payload, off); off += 8;
                m.Rank = payload[off]; off += 1;
                d.Members[i] = m;
            }
            return d;
        }

        /// <summary>GUILD_LIST 파싱: count(1) {guild_id(4) name(16) member_count(1) leader_name(16)}*N = 37B/entry</summary>
        public static GuildListEntry[] ParseGuildList(byte[] payload)
        {
            byte count = payload[0];
            var guilds = new GuildListEntry[count];
            int off = 1;
            for (int i = 0; i < count; i++)
            {
                var g = new GuildListEntry();
                g.GuildId = BitConverter.ToUInt32(payload, off); off += 4;
                int nameEnd = off;
                while (nameEnd < off + 16 && payload[nameEnd] != 0) nameEnd++;
                g.Name = Encoding.UTF8.GetString(payload, off, nameEnd - off);
                off += 16;
                g.MemberCount = payload[off]; off += 1;
                int leaderEnd = off;
                while (leaderEnd < off + 16 && payload[leaderEnd] != 0) leaderEnd++;
                g.LeaderName = Encoding.UTF8.GetString(payload, off, leaderEnd - off);
                off += 16;
                guilds[i] = g;
            }
            return guilds;
        }

        // ━━━ S029: 거래 (Trade) ━━━

        /// <summary>TRADE_REQUEST 빌드: target_entity(8)</summary>
        public static byte[] TradeRequest(ulong targetEntity)
        {
            return Build(MsgType.TRADE_REQUEST, BitConverter.GetBytes(targetEntity));
        }

        /// <summary>TRADE_ACCEPT 빌드: empty</summary>
        public static byte[] TradeAccept()
        {
            return Build(MsgType.TRADE_ACCEPT);
        }

        /// <summary>TRADE_DECLINE 빌드: empty</summary>
        public static byte[] TradeDecline()
        {
            return Build(MsgType.TRADE_DECLINE);
        }

        /// <summary>TRADE_ADD_ITEM 빌드: slot_index(1)</summary>
        public static byte[] TradeAddItem(byte slotIndex)
        {
            return Build(MsgType.TRADE_ADD_ITEM, new byte[] { slotIndex });
        }

        /// <summary>TRADE_ADD_GOLD 빌드: amount(4u32)</summary>
        public static byte[] TradeAddGold(uint amount)
        {
            return Build(MsgType.TRADE_ADD_GOLD, BitConverter.GetBytes(amount));
        }

        /// <summary>TRADE_CONFIRM 빌드: empty</summary>
        public static byte[] TradeConfirm()
        {
            return Build(MsgType.TRADE_CONFIRM);
        }

        /// <summary>TRADE_CANCEL 빌드: empty</summary>
        public static byte[] TradeCancel()
        {
            return Build(MsgType.TRADE_CANCEL);
        }

        /// <summary>TRADE_RESULT 파싱: result(1) = 1B</summary>
        public static TradeResultData ParseTradeResult(byte[] payload)
        {
            var d = new TradeResultData();
            d.Result = (TradeResult)payload[0];
            return d;
        }

        // ━━━ S029: 우편 (Mail) ━━━

        /// <summary>MAIL_SEND 빌드: recipient_len(1) recipient(N) title_len(1) title(N) body_len(2) body(N) gold(4) item_id(4) item_count(2)</summary>
        public static byte[] MailSend(string recipient, string title, string body, uint gold, uint itemId, ushort itemCount)
        {
            byte[] recipBytes = Encoding.UTF8.GetBytes(recipient);
            byte[] titleBytes = Encoding.UTF8.GetBytes(title);
            byte[] bodyBytes = Encoding.UTF8.GetBytes(body);
            byte[] payload = new byte[1 + recipBytes.Length + 1 + titleBytes.Length + 2 + bodyBytes.Length + 4 + 4 + 2];
            int off = 0;
            payload[off] = (byte)recipBytes.Length; off += 1;
            Buffer.BlockCopy(recipBytes, 0, payload, off, recipBytes.Length); off += recipBytes.Length;
            payload[off] = (byte)titleBytes.Length; off += 1;
            Buffer.BlockCopy(titleBytes, 0, payload, off, titleBytes.Length); off += titleBytes.Length;
            BitConverter.GetBytes((ushort)bodyBytes.Length).CopyTo(payload, off); off += 2;
            Buffer.BlockCopy(bodyBytes, 0, payload, off, bodyBytes.Length); off += bodyBytes.Length;
            BitConverter.GetBytes(gold).CopyTo(payload, off); off += 4;
            BitConverter.GetBytes(itemId).CopyTo(payload, off); off += 4;
            BitConverter.GetBytes(itemCount).CopyTo(payload, off);
            return Build(MsgType.MAIL_SEND, payload);
        }

        /// <summary>MAIL_LIST_REQ 빌드: empty</summary>
        public static byte[] MailListReq()
        {
            return Build(MsgType.MAIL_LIST_REQ);
        }

        /// <summary>MAIL_READ 빌드: mail_id(4)</summary>
        public static byte[] MailRead(uint mailId)
        {
            return Build(MsgType.MAIL_READ, BitConverter.GetBytes(mailId));
        }

        /// <summary>MAIL_CLAIM 빌드: mail_id(4)</summary>
        public static byte[] MailClaim(uint mailId)
        {
            return Build(MsgType.MAIL_CLAIM, BitConverter.GetBytes(mailId));
        }

        /// <summary>MAIL_DELETE 빌드: mail_id(4)</summary>
        public static byte[] MailDelete(uint mailId)
        {
            return Build(MsgType.MAIL_DELETE, BitConverter.GetBytes(mailId));
        }

        /// <summary>MAIL_LIST 파싱: count(1) {mail_id(4) sender(16) title(32) read(1) has_attachment(1) timestamp(4)}*N = 58B/entry</summary>
        public static MailListEntry[] ParseMailList(byte[] payload)
        {
            byte count = payload[0];
            var mails = new MailListEntry[count];
            int off = 1;
            for (int i = 0; i < count; i++)
            {
                var m = new MailListEntry();
                m.MailId = BitConverter.ToUInt32(payload, off); off += 4;
                int senderEnd = off;
                while (senderEnd < off + 16 && payload[senderEnd] != 0) senderEnd++;
                m.Sender = Encoding.UTF8.GetString(payload, off, senderEnd - off);
                off += 16;
                int titleEnd = off;
                while (titleEnd < off + 32 && payload[titleEnd] != 0) titleEnd++;
                m.Title = Encoding.UTF8.GetString(payload, off, titleEnd - off);
                off += 32;
                m.IsRead = payload[off] != 0; off += 1;
                m.HasAttachment = payload[off] != 0; off += 1;
                m.Timestamp = BitConverter.ToUInt32(payload, off); off += 4;
                mails[i] = m;
            }
            return mails;
        }

        /// <summary>MAIL_READ_RESP 파싱: mail_id(4) sender(16) title(32) body_len(2) body(N) gold(4) item_id(4) item_count(2)</summary>
        public static MailReadData ParseMailReadResp(byte[] payload)
        {
            var d = new MailReadData();
            int off = 0;
            d.MailId = BitConverter.ToUInt32(payload, off); off += 4;
            int senderEnd = off;
            while (senderEnd < off + 16 && payload[senderEnd] != 0) senderEnd++;
            d.Sender = Encoding.UTF8.GetString(payload, off, senderEnd - off);
            off += 16;
            int titleEnd = off;
            while (titleEnd < off + 32 && payload[titleEnd] != 0) titleEnd++;
            d.Title = Encoding.UTF8.GetString(payload, off, titleEnd - off);
            off += 32;
            ushort bodyLen = BitConverter.ToUInt16(payload, off); off += 2;
            d.Body = Encoding.UTF8.GetString(payload, off, bodyLen); off += bodyLen;
            d.Gold = BitConverter.ToUInt32(payload, off); off += 4;
            d.ItemId = BitConverter.ToUInt32(payload, off); off += 4;
            d.ItemCount = BitConverter.ToUInt16(payload, off);
            return d;
        }

        /// <summary>MAIL_CLAIM_RESULT 파싱: result(1) mail_id(4) = 5B</summary>
        public static MailClaimResultData ParseMailClaimResult(byte[] payload)
        {
            var d = new MailClaimResultData();
            d.Result = (MailClaimResult)payload[0];
            d.MailId = BitConverter.ToUInt32(payload, 1);
            return d;
        }

        /// <summary>MAIL_DELETE_RESULT 파싱: result(1) mail_id(4) = 5B</summary>
        public static MailDeleteResultData ParseMailDeleteResult(byte[] payload)
        {
            var d = new MailDeleteResultData();
            d.Result = (MailDeleteResult)payload[0];
            d.MailId = BitConverter.ToUInt32(payload, 1);
            return d;
        }

        // ━━━ S036: PvP 아레나 ━━━

        /// <summary>PVP_QUEUE_REQ 빌드: mode(1)</summary>
        public static byte[] PvPQueueReq(byte mode)
        {
            return Build(MsgType.PVP_QUEUE_REQ, new byte[] { mode });
        }

        /// <summary>PVP_QUEUE_CANCEL 빌드: empty</summary>
        public static byte[] PvPQueueCancel()
        {
            return Build(MsgType.PVP_QUEUE_CANCEL);
        }

        /// <summary>PVP_MATCH_ACCEPT 빌드: match_id(4)</summary>
        public static byte[] PvPMatchAccept(uint matchId)
        {
            return Build(MsgType.PVP_MATCH_ACCEPT, BitConverter.GetBytes(matchId));
        }

        /// <summary>PVP_ATTACK 빌드: match_id(4) target_team(1) target_idx(1) skill_id(2) damage(2) = 10B</summary>
        public static byte[] PvPAttack(uint matchId, byte targetTeam, byte targetIdx, ushort skillId, ushort damage)
        {
            byte[] payload = new byte[10];
            BitConverter.GetBytes(matchId).CopyTo(payload, 0);
            payload[4] = targetTeam;
            payload[5] = targetIdx;
            BitConverter.GetBytes(skillId).CopyTo(payload, 6);
            BitConverter.GetBytes(damage).CopyTo(payload, 8);
            return Build(MsgType.PVP_ATTACK, payload);
        }

        /// <summary>PVP_QUEUE_STATUS 파싱: mode_id(1) status(1) queue_count(2) = 4B</summary>
        public static PvPQueueStatusData ParsePvPQueueStatus(byte[] payload)
        {
            var d = new PvPQueueStatusData();
            d.ModeId = payload[0];
            d.Status = (PvPQueueStatus)payload[1];
            d.QueueCount = BitConverter.ToUInt16(payload, 2);
            return d;
        }

        /// <summary>PVP_MATCH_FOUND 파싱: match_id(4) mode_id(1) team_id(1) = 6B</summary>
        public static PvPMatchFoundData ParsePvPMatchFound(byte[] payload)
        {
            var d = new PvPMatchFoundData();
            d.MatchId = BitConverter.ToUInt32(payload, 0);
            d.ModeId = payload[4];
            d.TeamId = payload[5];
            return d;
        }

        /// <summary>PVP_MATCH_START 파싱: match_id(4) team_id(1) time_limit(2) = 7B</summary>
        public static PvPMatchStartData ParsePvPMatchStart(byte[] payload)
        {
            var d = new PvPMatchStartData();
            d.MatchId = BitConverter.ToUInt32(payload, 0);
            d.TeamId = payload[4];
            d.TimeLimit = BitConverter.ToUInt16(payload, 5);
            return d;
        }

        /// <summary>PVP_ATTACK_RESULT 파싱: match_id(4) attacker_team(1) target_team(1) target_idx(1) damage(2) remaining_hp(4) = 13B</summary>
        public static PvPAttackResultData ParsePvPAttackResult(byte[] payload)
        {
            var d = new PvPAttackResultData();
            d.MatchId = BitConverter.ToUInt32(payload, 0);
            d.AttackerTeam = payload[4];
            d.TargetTeam = payload[5];
            d.TargetIdx = payload[6];
            d.Damage = BitConverter.ToUInt16(payload, 7);
            d.RemainingHP = BitConverter.ToUInt32(payload, 9);
            return d;
        }

        /// <summary>PVP_MATCH_END 파싱: match_id(4) winner_team(1) won(1) new_rating(2) tier(16B) = 24B</summary>
        public static PvPMatchEndData ParsePvPMatchEnd(byte[] payload)
        {
            var d = new PvPMatchEndData();
            d.MatchId = BitConverter.ToUInt32(payload, 0);
            d.WinnerTeam = payload[4];
            d.Won = payload[5];
            d.NewRating = BitConverter.ToUInt16(payload, 6);
            int tierEnd = 8;
            while (tierEnd < 8 + 16 && tierEnd < payload.Length && payload[tierEnd] != 0) tierEnd++;
            d.Tier = Encoding.UTF8.GetString(payload, 8, tierEnd - 8);
            return d;
        }

        /// <summary>PVP_RATING_INFO 파싱: rating(2) tier(16B) wins(2) losses(2) = 22B</summary>
        public static PvPRatingInfoData ParsePvPRatingInfo(byte[] payload)
        {
            var d = new PvPRatingInfoData();
            d.Rating = BitConverter.ToUInt16(payload, 0);
            int tierEnd = 2;
            while (tierEnd < 2 + 16 && tierEnd < payload.Length && payload[tierEnd] != 0) tierEnd++;
            d.Tier = Encoding.UTF8.GetString(payload, 2, tierEnd - 2);
            d.Wins = BitConverter.ToUInt16(payload, 18);
            d.Losses = BitConverter.ToUInt16(payload, 20);
            return d;
        }

        // ━━━ S036: 레이드 보스 ━━━

        /// <summary>RAID_ATTACK 빌드: instance_id(4) skill_id(2) damage(4) = 10B</summary>
        public static byte[] RaidAttack(uint instanceId, ushort skillId, uint damage)
        {
            byte[] payload = new byte[10];
            BitConverter.GetBytes(instanceId).CopyTo(payload, 0);
            BitConverter.GetBytes(skillId).CopyTo(payload, 4);
            BitConverter.GetBytes(damage).CopyTo(payload, 6);
            return Build(MsgType.RAID_ATTACK, payload);
        }

        /// <summary>RAID_BOSS_SPAWN 파싱: instance_id(4) boss_name(32) max_hp(4) current_hp(4) phase(1) max_phases(1) enrage_timer(2) = 48B</summary>
        public static RaidBossSpawnData ParseRaidBossSpawn(byte[] payload)
        {
            var d = new RaidBossSpawnData();
            d.InstanceId = BitConverter.ToUInt32(payload, 0);
            int nameEnd = 4;
            while (nameEnd < 4 + 32 && nameEnd < payload.Length && payload[nameEnd] != 0) nameEnd++;
            d.BossName = Encoding.UTF8.GetString(payload, 4, nameEnd - 4);
            d.MaxHP = BitConverter.ToUInt32(payload, 36);
            d.CurrentHP = BitConverter.ToUInt32(payload, 40);
            d.Phase = payload[44];
            d.MaxPhases = payload[45];
            d.EnrageTimer = BitConverter.ToUInt16(payload, 46);
            return d;
        }

        /// <summary>RAID_PHASE_CHANGE 파싱: instance_id(4) phase(1) max_phases(1) = 6B</summary>
        public static RaidPhaseChangeData ParseRaidPhaseChange(byte[] payload)
        {
            var d = new RaidPhaseChangeData();
            d.InstanceId = BitConverter.ToUInt32(payload, 0);
            d.Phase = payload[4];
            d.MaxPhases = payload[5];
            return d;
        }

        /// <summary>RAID_MECHANIC 파싱: instance_id(4) mechanic_id(1) phase(1) = 6B</summary>
        public static RaidMechanicData ParseRaidMechanic(byte[] payload)
        {
            var d = new RaidMechanicData();
            d.InstanceId = BitConverter.ToUInt32(payload, 0);
            d.MechanicId = (RaidMechanicId)payload[4];
            d.Phase = payload[5];
            return d;
        }

        /// <summary>RAID_MECHANIC_RESULT 파싱: instance_id(4) mechanic_id(1) success(1) = 6B</summary>
        public static RaidMechanicResultData ParseRaidMechanicResult(byte[] payload)
        {
            var d = new RaidMechanicResultData();
            d.InstanceId = BitConverter.ToUInt32(payload, 0);
            d.MechanicId = (RaidMechanicId)payload[4];
            d.Success = payload[5] == 1;
            return d;
        }

        /// <summary>RAID_STAGGER 파싱: instance_id(4) stagger_gauge(1) = 5B</summary>
        public static RaidStaggerData ParseRaidStagger(byte[] payload)
        {
            var d = new RaidStaggerData();
            d.InstanceId = BitConverter.ToUInt32(payload, 0);
            d.StaggerGauge = payload[4];
            return d;
        }

        /// <summary>RAID_ATTACK_RESULT 파싱: instance_id(4) skill_id(2) damage(4) current_hp(4) max_hp(4) = 18B</summary>
        public static RaidAttackResultData ParseRaidAttackResult(byte[] payload)
        {
            var d = new RaidAttackResultData();
            d.InstanceId = BitConverter.ToUInt32(payload, 0);
            d.SkillId = BitConverter.ToUInt16(payload, 4);
            d.Damage = BitConverter.ToUInt32(payload, 6);
            d.CurrentHP = BitConverter.ToUInt32(payload, 10);
            d.MaxHP = BitConverter.ToUInt32(payload, 14);
            return d;
        }

        /// <summary>RAID_CLEAR 파싱: instance_id(4) gold(4) exp(4) tokens(2) = 14B</summary>
        public static RaidClearData ParseRaidClear(byte[] payload)
        {
            var d = new RaidClearData();
            d.InstanceId = BitConverter.ToUInt32(payload, 0);
            d.Gold = BitConverter.ToUInt32(payload, 4);
            d.Exp = BitConverter.ToUInt32(payload, 8);
            d.Tokens = BitConverter.ToUInt16(payload, 12);
            return d;
        }

        /// <summary>RAID_WIPE 파싱: instance_id(4) phase(1) = 5B</summary>
        public static RaidWipeData ParseRaidWipe(byte[] payload)
        {
            var d = new RaidWipeData();
            d.InstanceId = BitConverter.ToUInt32(payload, 0);
            d.Phase = payload[4];
            return d;
        }

        // ━━━ S045: 거래소 (Auction) ━━━

        /// <summary>AUCTION_LIST_REQ 빌드: category(1) page(1) sort_by(1) = 3B</summary>
        public static byte[] AuctionListReq(byte category, byte page, byte sortBy)
        {
            return Build(MsgType.AUCTION_LIST_REQ, new byte[] { category, page, sortBy });
        }

        /// <summary>AUCTION_REGISTER 빌드: slot_idx(1) count(1) buyout_price(4) category(1) = 7B</summary>
        public static byte[] AuctionRegister(byte slotIdx, byte count, uint buyoutPrice, byte category)
        {
            byte[] payload = new byte[7];
            payload[0] = slotIdx;
            payload[1] = count;
            BitConverter.GetBytes(buyoutPrice).CopyTo(payload, 2);
            payload[6] = category;
            return Build(MsgType.AUCTION_REGISTER, payload);
        }

        /// <summary>AUCTION_BUY 빌드: auction_id(4)</summary>
        public static byte[] AuctionBuy(uint auctionId)
        {
            return Build(MsgType.AUCTION_BUY, BitConverter.GetBytes(auctionId));
        }

        /// <summary>AUCTION_BID 빌드: auction_id(4) bid_amount(4) = 8B</summary>
        public static byte[] AuctionBid(uint auctionId, uint bidAmount)
        {
            byte[] payload = new byte[8];
            BitConverter.GetBytes(auctionId).CopyTo(payload, 0);
            BitConverter.GetBytes(bidAmount).CopyTo(payload, 4);
            return Build(MsgType.AUCTION_BID, payload);
        }

        /// <summary>AUCTION_LIST 파싱: total_count(2) total_pages(1) page(1) item_count(1) + items[]</summary>
        public static AuctionListData ParseAuctionList(byte[] payload)
        {
            var d = new AuctionListData();
            d.TotalCount = BitConverter.ToUInt16(payload, 0);
            d.TotalPages = payload[2];
            d.CurrentPage = payload[3];
            byte itemCount = payload[4];
            d.Items = new AuctionListingInfo[itemCount];
            int off = 5;
            for (int i = 0; i < itemCount; i++)
            {
                var it = new AuctionListingInfo();
                it.AuctionId = BitConverter.ToUInt32(payload, off); off += 4;
                it.ItemId = BitConverter.ToUInt16(payload, off); off += 2;
                it.Count = payload[off]; off += 1;
                it.BuyoutPrice = BitConverter.ToUInt32(payload, off); off += 4;
                it.CurrentBid = BitConverter.ToUInt32(payload, off); off += 4;
                byte nameLen = payload[off]; off += 1;
                it.SellerName = Encoding.UTF8.GetString(payload, off, nameLen); off += nameLen;
                d.Items[i] = it;
            }
            return d;
        }

        /// <summary>AUCTION_REGISTER_RESULT 파싱: result(1) auction_id(4) = 5B</summary>
        public static AuctionRegisterResultData ParseAuctionRegisterResult(byte[] payload)
        {
            var d = new AuctionRegisterResultData();
            d.Result = (AuctionRegisterResult)payload[0];
            d.AuctionId = BitConverter.ToUInt32(payload, 1);
            return d;
        }

        /// <summary>AUCTION_BUY_RESULT 파싱: result(1) auction_id(4) = 5B</summary>
        public static AuctionBuyResultData ParseAuctionBuyResult(byte[] payload)
        {
            var d = new AuctionBuyResultData();
            d.Result = (AuctionBuyResult)payload[0];
            d.AuctionId = BitConverter.ToUInt32(payload, 1);
            return d;
        }

        /// <summary>AUCTION_BID_RESULT 파싱: result(1) auction_id(4) = 5B</summary>
        public static AuctionBidResultData ParseAuctionBidResult(byte[] payload)
        {
            var d = new AuctionBidResultData();
            d.Result = (AuctionBidResult)payload[0];
            d.AuctionId = BitConverter.ToUInt32(payload, 1);
            return d;
        }

        // ━━━ S043: 제작 (Crafting) ━━━

        /// <summary>CRAFT_LIST_REQ 빌드: category(1) (0xFF=all)</summary>
        public static byte[] CraftListReq(byte category = 0xFF)
        {
            return Build(MsgType.CRAFT_LIST_REQ, new byte[] { category });
        }

        /// <summary>CRAFT_EXECUTE 빌드: rid_len(1) + recipe_id(str)</summary>
        public static byte[] CraftExecute(string recipeId)
        {
            byte[] rid = Encoding.UTF8.GetBytes(recipeId);
            byte[] payload = new byte[1 + rid.Length];
            payload[0] = (byte)rid.Length;
            Array.Copy(rid, 0, payload, 1, rid.Length);
            return Build(MsgType.CRAFT_EXECUTE, payload);
        }

        /// <summary>CRAFT_LIST 파싱 (S043): count(1) {rid_len(1) rid(str) prof_req(1) gold_cost(2) success_pct(1) item_id(2) item_count(1) mat_count(1)}*N</summary>
        public static CraftRecipeInfo[] ParseCraftList(byte[] payload)
        {
            byte count = payload[0];
            var recipes = new CraftRecipeInfo[count];
            int off = 1;
            for (int i = 0; i < count; i++)
            {
                var r = new CraftRecipeInfo();
                byte ridLen = payload[off]; off += 1;
                r.RecipeId = Encoding.UTF8.GetString(payload, off, ridLen); off += ridLen;
                r.Proficiency = payload[off]; off += 1;
                r.Gold = BitConverter.ToUInt16(payload, off); off += 2;
                r.SuccessPct = payload[off]; off += 1;
                r.ItemId = BitConverter.ToUInt16(payload, off); off += 2;
                r.ItemCount = payload[off]; off += 1;
                r.MaterialCount = payload[off]; off += 1;
                recipes[i] = r;
            }
            return recipes;
        }

        /// <summary>CRAFT_RESULT 파싱 (S043): result(1) [+ item_id(2) count(1) has_bonus(1)]</summary>
        public static CraftResultData ParseCraftResult(byte[] payload)
        {
            var d = new CraftResultData();
            d.Status = (CraftResult)payload[0];
            if (d.Status == CraftResult.SUCCESS && payload.Length >= 4)
            {
                d.ItemId = BitConverter.ToUInt16(payload, 1);
                d.Count = payload[3];
                d.HasBonus = payload.Length >= 5 ? payload[4] : (byte)0;
            }
            return d;
        }

        // ━━━ S043: 채집 (Gathering) ━━━

        /// <summary>GATHER_START 빌드: gather_type(1)</summary>
        public static byte[] GatherStart(byte gatherType)
        {
            return Build(MsgType.GATHER_START, new byte[] { gatherType });
        }

        /// <summary>GATHER_RESULT 파싱 (S043): result(1) energy(1) drop_count(1) {item_id(2)}*N</summary>
        public static GatherResultData ParseGatherResult(byte[] payload)
        {
            var d = new GatherResultData();
            d.Status = (GatherResult)payload[0];
            d.Energy = payload[1];
            byte dropCount = payload[2];
            d.Drops = new GatherDropItem[dropCount];
            int off = 3;
            for (int i = 0; i < dropCount; i++)
            {
                d.Drops[i] = new GatherDropItem();
                d.Drops[i].ItemId = BitConverter.ToUInt16(payload, off); off += 2;
            }
            return d;
        }

        // ━━━ S043: 요리 (Cooking) ━━━

        /// <summary>COOK_EXECUTE 빌드 (S043): rid_len(1) + recipe_id(str)</summary>
        public static byte[] CookExecute(string recipeId)
        {
            byte[] rid = Encoding.UTF8.GetBytes(recipeId);
            byte[] payload = new byte[1 + rid.Length];
            payload[0] = (byte)rid.Length;
            Array.Copy(rid, 0, payload, 1, rid.Length);
            return Build(MsgType.COOK_EXECUTE, payload);
        }

        /// <summary>COOK_RESULT 파싱 (S043): result(1) [+ duration(2) effect_count(1)]</summary>
        public static CookResultData ParseCookResult(byte[] payload)
        {
            var d = new CookResultData();
            d.Status = (CookResult)payload[0];
            if (d.Status == CookResult.SUCCESS && payload.Length >= 4)
            {
                d.Duration = BitConverter.ToUInt16(payload, 1);
                d.EffectCount = payload[3];
            }
            return d;
        }

        // ━━━ S043: 인챈트 (Enchant) ━━━

        /// <summary>ENCHANT_REQ 빌드: slot_idx(1) element_id(1) target_level(1) = 3B</summary>
        public static byte[] EnchantReq(byte slot, byte element, byte level)
        {
            return Build(MsgType.ENCHANT_REQ, new byte[] { slot, element, level });
        }

        /// <summary>ENCHANT_RESULT 파싱 (S043): result(1) [+ element_id(1) level(1) dmg_bonus_pct(1)]</summary>
        public static EnchantResultData ParseEnchantResultData(byte[] payload)
        {
            var d = new EnchantResultData();
            d.Status = (EnchantResult)payload[0];
            if (d.Status == EnchantResult.SUCCESS && payload.Length >= 4)
            {
                d.Element = payload[1];
                d.Level = payload[2];
                d.DamagePct = payload[3];
            }
            return d;
        }

        // ━━━ S041: 보석 (Gem) ━━━

        /// <summary>GEM_EQUIP 빌드: item_slot(1) gem_slot(1) gem_item_id(4) = 6B</summary>
        public static byte[] GemEquip(byte itemSlot, byte gemSlot, uint gemItemId)
        {
            byte[] payload = new byte[6];
            payload[0] = itemSlot;
            payload[1] = gemSlot;
            BitConverter.GetBytes(gemItemId).CopyTo(payload, 2);
            return Build(MsgType.GEM_EQUIP, payload);
        }

        /// <summary>GEM_FUSE 빌드: gem_type(1) gem_tier(1) = 2B</summary>
        public static byte[] GemFuse(byte gemType, byte gemTier)
        {
            return Build(MsgType.GEM_FUSE, new byte[] { gemType, gemTier });
        }

        /// <summary>GEM_EQUIP_RESULT 파싱: status(1) item_slot(1) gem_slot(1) gem_type(1) gem_tier(1) = 5B</summary>
        public static GemEquipResultData ParseGemEquipResult(byte[] payload)
        {
            var d = new GemEquipResultData();
            d.Status = (GemResult)payload[0];
            d.ItemSlot = payload[1];
            d.GemSlot = payload[2];
            d.GemType = payload[3];
            d.GemTier = payload[4];
            return d;
        }

        /// <summary>GEM_FUSE_RESULT 파싱: status(1) gem_type(1) new_tier(1) = 3B</summary>
        public static GemFuseResultData ParseGemFuseResult(byte[] payload)
        {
            var d = new GemFuseResultData();
            d.Status = (GemResult)payload[0];
            d.GemType = payload[1];
            d.NewTier = payload[2];
            return d;
        }

        // ━━━ S042: 캐시샵 (TASK 11) ━━━

        /// <summary>CASH_SHOP_LIST_REQ 빌드: category(1)</summary>
        public static byte[] CashShopListReq(byte category)
        {
            return Build(MsgType.CASH_SHOP_LIST_REQ, new byte[] { category });
        }

        /// <summary>CASH_SHOP_BUY 빌드: item_id(4) count(1) = 5B</summary>
        public static byte[] CashShopBuy(uint itemId, byte count)
        {
            byte[] payload = new byte[5];
            BitConverter.GetBytes(itemId).CopyTo(payload, 0);
            payload[4] = count;
            return Build(MsgType.CASH_SHOP_BUY, payload);
        }

        /// <summary>CASH_SHOP_LIST 파싱: count(1) {item_id(4) name(32) category(1) price(4) currency(1)}*N = 42B/entry</summary>
        public static CashShopItemInfo[] ParseCashShopList(byte[] payload)
        {
            byte count = payload[0];
            var items = new CashShopItemInfo[count];
            int off = 1;
            for (int i = 0; i < count; i++)
            {
                var it = new CashShopItemInfo();
                it.ItemId = BitConverter.ToUInt32(payload, off); off += 4;
                int nameEnd = off;
                while (nameEnd < off + 32 && payload[nameEnd] != 0) nameEnd++;
                it.Name = Encoding.UTF8.GetString(payload, off, nameEnd - off);
                off += 32;
                it.Category = (CashShopCategory)payload[off]; off += 1;
                it.Price = BitConverter.ToUInt32(payload, off); off += 4;
                it.Currency = (CashCurrency)payload[off]; off += 1;
                items[i] = it;
            }
            return items;
        }

        /// <summary>CASH_SHOP_BUY_RESULT 파싱: result(1) item_id(4) remaining_crystals(4) = 9B</summary>
        public static CashShopBuyResultData ParseCashShopBuyResult(byte[] payload)
        {
            var d = new CashShopBuyResultData();
            d.Result = (CashShopBuyResult)payload[0];
            d.ItemId = BitConverter.ToUInt32(payload, 1);
            d.RemainingCrystals = BitConverter.ToUInt32(payload, 5);
            return d;
        }

        // ━━━ S042: 배틀패스 (TASK 11) ━━━

        /// <summary>BATTLEPASS_INFO_REQ 빌드: empty</summary>
        public static byte[] BattlePassInfoReq()
        {
            return Build(MsgType.BATTLEPASS_INFO_REQ);
        }

        /// <summary>BATTLEPASS_REWARD_CLAIM 빌드: level(1) track(1) = 2B</summary>
        public static byte[] BattlePassRewardClaim(byte level, byte track)
        {
            return Build(MsgType.BATTLEPASS_REWARD_CLAIM, new byte[] { level, track });
        }

        /// <summary>BATTLEPASS_BUY_PREMIUM 빌드: empty</summary>
        public static byte[] BattlePassBuyPremium()
        {
            return Build(MsgType.BATTLEPASS_BUY_PREMIUM);
        }

        /// <summary>BATTLEPASS_INFO 파싱: season_id(2) level(1) exp(2) max_exp(2) is_premium(1) days_left(2) = 10B</summary>
        public static BattlePassInfoData ParseBattlePassInfo(byte[] payload)
        {
            var d = new BattlePassInfoData();
            d.SeasonId = BitConverter.ToUInt16(payload, 0);
            d.Level = payload[2];
            d.Exp = BitConverter.ToUInt16(payload, 3);
            d.MaxExp = BitConverter.ToUInt16(payload, 5);
            d.IsPremium = payload[7] != 0;
            d.DaysLeft = BitConverter.ToUInt16(payload, 8);
            return d;
        }

        /// <summary>BATTLEPASS_REWARD_RESULT 파싱: result(1) level(1) track(1) reward_type(1) reward_id(4) reward_count(2) = 10B</summary>
        public static BattlePassRewardResultData ParseBattlePassRewardResult(byte[] payload)
        {
            var d = new BattlePassRewardResultData();
            d.Result = (BattlePassRewardResult)payload[0];
            d.Level = payload[1];
            d.Track = (BattlePassTrack)payload[2];
            d.RewardType = payload[3];
            d.RewardId = BitConverter.ToUInt32(payload, 4);
            d.RewardCount = BitConverter.ToUInt16(payload, 8);
            return d;
        }

        /// <summary>BATTLEPASS_BUY_RESULT 파싱: result(1) remaining_crystals(4) = 5B</summary>
        public static BattlePassBuyResultData ParseBattlePassBuyResult(byte[] payload)
        {
            var d = new BattlePassBuyResultData();
            d.Result = payload[0];
            d.RemainingCrystals = BitConverter.ToUInt32(payload, 1);
            return d;
        }

        // ━━━ S042: 이벤트 (TASK 11) ━━━

        /// <summary>EVENT_LIST_REQ 빌드: empty</summary>
        public static byte[] EventListReq()
        {
            return Build(MsgType.EVENT_LIST_REQ);
        }

        /// <summary>EVENT_CLAIM 빌드: event_id(2)</summary>
        public static byte[] EventClaim(ushort eventId)
        {
            return Build(MsgType.EVENT_CLAIM, BitConverter.GetBytes(eventId));
        }

        /// <summary>EVENT_LIST 파싱: count(1) {event_id(2) type(1) name(32) remaining_sec(4)}*N = 39B/entry</summary>
        public static GameEventInfo[] ParseEventList(byte[] payload)
        {
            byte count = payload[0];
            var events = new GameEventInfo[count];
            int off = 1;
            for (int i = 0; i < count; i++)
            {
                var e = new GameEventInfo();
                e.EventId = BitConverter.ToUInt16(payload, off); off += 2;
                e.Type = (GameEventType)payload[off]; off += 1;
                int nameEnd = off;
                while (nameEnd < off + 32 && payload[nameEnd] != 0) nameEnd++;
                e.Name = Encoding.UTF8.GetString(payload, off, nameEnd - off);
                off += 32;
                e.RemainingSeconds = BitConverter.ToUInt32(payload, off); off += 4;
                events[i] = e;
            }
            return events;
        }

        /// <summary>EVENT_CLAIM_RESULT 파싱: result(1) event_id(2) reward_type(1) reward_id(4) reward_count(2) = 10B</summary>
        public static EventClaimResultData ParseEventClaimResult(byte[] payload)
        {
            var d = new EventClaimResultData();
            d.Result = payload[0];
            d.EventId = BitConverter.ToUInt16(payload, 1);
            d.RewardType = payload[3];
            d.RewardId = BitConverter.ToUInt32(payload, 4);
            d.RewardCount = BitConverter.ToUInt16(payload, 8);
            return d;
        }

        /// <summary>SUBSCRIPTION_INFO_REQ 빌드: empty</summary>
        public static byte[] SubscriptionInfoReq()
        {
            return Build(MsgType.SUBSCRIPTION_INFO_REQ);
        }

        /// <summary>SUBSCRIPTION_INFO 파싱: is_active(1) days_left(2) daily_crystals(2) = 5B</summary>
        public static SubscriptionInfoData ParseSubscriptionInfo(byte[] payload)
        {
            var d = new SubscriptionInfoData();
            d.IsActive = payload[0] != 0;
            d.DaysLeft = BitConverter.ToUInt16(payload, 1);
            d.DailyCrystals = BitConverter.ToUInt16(payload, 3);
            return d;
        }

        // ━━━ S042: 월드 시스템 (TASK 12) ━━━

        /// <summary>WEATHER_UPDATE 파싱: zone_id(4) weather_type(1) transition_sec(1) = 6B</summary>
        public static WeatherUpdateData ParseWeatherUpdate(byte[] payload)
        {
            var d = new WeatherUpdateData();
            d.ZoneId = BitConverter.ToUInt32(payload, 0);
            d.Weather = (WeatherType)payload[4];
            d.TransitionSeconds = payload[5];
            return d;
        }

        /// <summary>TELEPORT_LIST_REQ 빌드: empty</summary>
        public static byte[] TeleportListReq()
        {
            return Build(MsgType.TELEPORT_LIST_REQ);
        }

        /// <summary>TELEPORT_REQ 빌드: waypoint_id(2)</summary>
        public static byte[] TeleportReq(ushort waypointId)
        {
            return Build(MsgType.TELEPORT_REQ, BitConverter.GetBytes(waypointId));
        }

        /// <summary>TELEPORT_LIST 파싱: count(1) {waypoint_id(2) zone_id(4) name(32) x(4f) y(4f) z(4f) cost(4)}*N = 50B/entry</summary>
        public static WaypointInfo[] ParseTeleportList(byte[] payload)
        {
            byte count = payload[0];
            var waypoints = new WaypointInfo[count];
            int off = 1;
            for (int i = 0; i < count; i++)
            {
                var w = new WaypointInfo();
                w.WaypointId = BitConverter.ToUInt16(payload, off); off += 2;
                w.ZoneId = BitConverter.ToUInt32(payload, off); off += 4;
                int nameEnd = off;
                while (nameEnd < off + 32 && payload[nameEnd] != 0) nameEnd++;
                w.Name = Encoding.UTF8.GetString(payload, off, nameEnd - off);
                off += 32;
                w.X = BitConverter.ToSingle(payload, off); off += 4;
                w.Y = BitConverter.ToSingle(payload, off); off += 4;
                w.Z = BitConverter.ToSingle(payload, off); off += 4;
                w.Cost = BitConverter.ToUInt32(payload, off); off += 4;
                waypoints[i] = w;
            }
            return waypoints;
        }

        /// <summary>TELEPORT_RESULT 파싱: result(1) zone_id(4) x(4f) y(4f) z(4f) = 17B</summary>
        public static TeleportResultData ParseTeleportResult(byte[] payload)
        {
            var d = new TeleportResultData();
            d.Result = (TeleportResult)payload[0];
            d.ZoneId = BitConverter.ToUInt32(payload, 1);
            d.X = BitConverter.ToSingle(payload, 5);
            d.Y = BitConverter.ToSingle(payload, 9);
            d.Z = BitConverter.ToSingle(payload, 13);
            return d;
        }

        /// <summary>WORLD_OBJECT_INTERACT 빌드: object_id(4) action(1) = 5B</summary>
        public static byte[] WorldObjectInteract(uint objectId, byte action)
        {
            byte[] payload = new byte[5];
            BitConverter.GetBytes(objectId).CopyTo(payload, 0);
            payload[4] = action;
            return Build(MsgType.WORLD_OBJECT_INTERACT, payload);
        }

        /// <summary>WORLD_OBJECT_RESULT 파싱: result(1) object_id(4) item_id(4) count(2) gold(4) = 15B</summary>
        public static WorldObjectResultData ParseWorldObjectResult(byte[] payload)
        {
            var d = new WorldObjectResultData();
            d.Result = payload[0];
            d.ObjectId = BitConverter.ToUInt32(payload, 1);
            d.ItemId = BitConverter.ToUInt32(payload, 5);
            d.Count = BitConverter.ToUInt16(payload, 9);
            d.Gold = BitConverter.ToUInt32(payload, 11);
            return d;
        }

        /// <summary>MOUNT_SUMMON 빌드: mount_id(4)</summary>
        public static byte[] MountSummon(uint mountId)
        {
            return Build(MsgType.MOUNT_SUMMON, BitConverter.GetBytes(mountId));
        }

        /// <summary>MOUNT_DISMOUNT 빌드: empty</summary>
        public static byte[] MountDismount()
        {
            return Build(MsgType.MOUNT_DISMOUNT);
        }

        /// <summary>MOUNT_RESULT 파싱: result(1) mount_id(4) speed_mult(2) = 7B</summary>
        public static MountResultData ParseMountResult(byte[] payload)
        {
            var d = new MountResultData();
            d.Result = (MountResult)payload[0];
            d.MountId = BitConverter.ToUInt32(payload, 1);
            d.SpeedMultiplied = BitConverter.ToUInt16(payload, 5);
            return d;
        }

        // ━━━ S042: 출석/리셋/컨텐츠 해금 (TASK 13) ━━━

        /// <summary>ATTENDANCE_INFO_REQ 빌드: empty</summary>
        public static byte[] AttendanceInfoReq()
        {
            return Build(MsgType.ATTENDANCE_INFO_REQ);
        }

        /// <summary>ATTENDANCE_CLAIM 빌드: day(1)</summary>
        public static byte[] AttendanceClaim(byte day)
        {
            return Build(MsgType.ATTENDANCE_CLAIM, new byte[] { day });
        }

        /// <summary>ATTENDANCE_INFO 파싱: day(1) total_days(1) {claimed(1)}*14 = 16B</summary>
        public static AttendanceInfoData ParseAttendanceInfo(byte[] payload)
        {
            var d = new AttendanceInfoData();
            d.CurrentDay = payload[0];
            d.TotalDays = payload[1];
            d.Claimed = new bool[14];
            for (int i = 0; i < 14 && i + 2 < payload.Length; i++)
                d.Claimed[i] = payload[2 + i] != 0;
            return d;
        }

        /// <summary>ATTENDANCE_CLAIM_RESULT 파싱: result(1) day(1) reward_type(1) reward_id(4) reward_count(2) = 9B</summary>
        public static AttendanceClaimResultData ParseAttendanceClaimResult(byte[] payload)
        {
            var d = new AttendanceClaimResultData();
            d.Result = (AttendanceClaimResult)payload[0];
            d.Day = payload[1];
            d.RewardType = payload[2];
            d.RewardId = BitConverter.ToUInt32(payload, 3);
            d.RewardCount = BitConverter.ToUInt16(payload, 7);
            return d;
        }

        /// <summary>DAILY_RESET_NOTIFY 파싱: reset_type(1) timestamp(4) = 5B</summary>
        public static DailyResetNotifyData ParseDailyResetNotify(byte[] payload)
        {
            var d = new DailyResetNotifyData();
            d.Type = (ResetType)payload[0];
            d.Timestamp = BitConverter.ToUInt32(payload, 1);
            return d;
        }

        /// <summary>CONTENT_UNLOCK_NOTIFY 파싱: unlock_type(1) system_name_len(1) system_name(N) description_len(1) description(N)</summary>
        public static ContentUnlockNotifyData ParseContentUnlockNotify(byte[] payload)
        {
            var d = new ContentUnlockNotifyData();
            int off = 0;
            d.UnlockType = payload[off]; off += 1;
            byte nameLen = payload[off]; off += 1;
            d.SystemName = Encoding.UTF8.GetString(payload, off, nameLen); off += nameLen;
            byte descLen = payload[off]; off += 1;
            d.Description = Encoding.UTF8.GetString(payload, off, descLen);
            return d;
        }

        /// <summary>CONTENT_UNLOCK_ACK 빌드: unlock_type(1)</summary>
        public static byte[] ContentUnlockAck(byte unlockType)
        {
            return Build(MsgType.CONTENT_UNLOCK_ACK, new byte[] { unlockType });
        }

        /// <summary>LOGIN_REWARD_NOTIFY 파싱: reward_type(1) reward_id(4) reward_count(2) = 7B</summary>
        public static LoginRewardNotifyData ParseLoginRewardNotify(byte[] payload)
        {
            var d = new LoginRewardNotifyData();
            d.RewardType = payload[0];
            d.RewardId = BitConverter.ToUInt32(payload, 1);
            d.RewardCount = BitConverter.ToUInt16(payload, 5);
            return d;
        }

        // ━━━ S042: 스토리/대화 시스템 (TASK 14) ━━━

        /// <summary>DIALOG_CHOICE 빌드: npc_id(2) choice_index(1) = 3B</summary>
        public static byte[] DialogChoice(ushort npcId, byte choiceIndex)
        {
            byte[] payload = new byte[3];
            BitConverter.GetBytes(npcId).CopyTo(payload, 0);
            payload[2] = choiceIndex;
            return Build(MsgType.DIALOG_CHOICE, payload);
        }

        /// <summary>DIALOG_CHOICE_RESULT 파싱: npc_id(2) next_line_count(1) {speaker_len(1) speaker(N) text_len(2) text(N)}*N choice_count(1) {text_len(1) text(N)}*N</summary>
        public static DialogChoiceResultData ParseDialogChoiceResult(byte[] payload)
        {
            var d = new DialogChoiceResultData();
            int off = 0;
            d.NpcId = BitConverter.ToUInt16(payload, off); off += 2;
            byte lineCount = payload[off]; off += 1;
            d.Lines = new NpcDialogLine[lineCount];
            for (int i = 0; i < lineCount; i++)
            {
                var line = new NpcDialogLine();
                byte speakerLen = payload[off]; off += 1;
                line.Speaker = Encoding.UTF8.GetString(payload, off, speakerLen); off += speakerLen;
                ushort textLen = BitConverter.ToUInt16(payload, off); off += 2;
                line.Text = Encoding.UTF8.GetString(payload, off, textLen); off += textLen;
                d.Lines[i] = line;
            }
            byte choiceCount = payload[off]; off += 1;
            d.Choices = new string[choiceCount];
            for (int i = 0; i < choiceCount; i++)
            {
                byte textLen = payload[off]; off += 1;
                d.Choices[i] = Encoding.UTF8.GetString(payload, off, textLen); off += textLen;
            }
            return d;
        }

        /// <summary>CUTSCENE_SKIP 빌드: cutscene_id(2)</summary>
        public static byte[] CutsceneSkip(ushort cutsceneId)
        {
            return Build(MsgType.CUTSCENE_SKIP, BitConverter.GetBytes(cutsceneId));
        }

        /// <summary>CUTSCENE_TRIGGER 파싱: cutscene_id(2) duration_sec(2) = 4B</summary>
        public static CutsceneTriggerData ParseCutsceneTrigger(byte[] payload)
        {
            var d = new CutsceneTriggerData();
            d.CutsceneId = BitConverter.ToUInt16(payload, 0);
            d.DurationSeconds = BitConverter.ToUInt16(payload, 2);
            return d;
        }

        /// <summary>STORY_PROGRESS_REQ 빌드: empty</summary>
        public static byte[] StoryProgressReq()
        {
            return Build(MsgType.STORY_PROGRESS_REQ);
        }

        /// <summary>STORY_PROGRESS 파싱: chapter(1) quest_id(4) quest_state(1) = 6B</summary>
        public static StoryProgressData ParseStoryProgress(byte[] payload)
        {
            var d = new StoryProgressData();
            d.Chapter = payload[0];
            d.QuestId = BitConverter.ToUInt32(payload, 1);
            d.QuestState = (QuestState)payload[5];
            return d;
        }

        /// <summary>MAIN_QUEST_DATA 파싱: quest_id(4) name(32) desc_len(2) desc(N) objective_count(1) {type(1) target(4) current(4) required(4)}*N = 13B/objective</summary>
        public static MainQuestDataInfo ParseMainQuestData(byte[] payload)
        {
            var d = new MainQuestDataInfo();
            int off = 0;
            d.QuestId = BitConverter.ToUInt32(payload, off); off += 4;
            int nameEnd = off;
            while (nameEnd < off + 32 && payload[nameEnd] != 0) nameEnd++;
            d.Name = Encoding.UTF8.GetString(payload, off, nameEnd - off);
            off += 32;
            ushort descLen = BitConverter.ToUInt16(payload, off); off += 2;
            d.Description = Encoding.UTF8.GetString(payload, off, descLen); off += descLen;
            byte objCount = payload[off]; off += 1;
            d.Objectives = new MainQuestObjective[objCount];
            for (int i = 0; i < objCount; i++)
            {
                var obj = new MainQuestObjective();
                obj.Type = (MainQuestObjectiveType)payload[off]; off += 1;
                obj.Target = BitConverter.ToUInt32(payload, off); off += 4;
                obj.Current = BitConverter.ToUInt32(payload, off); off += 4;
                obj.Required = BitConverter.ToUInt32(payload, off); off += 4;
                d.Objectives[i] = obj;
            }
            return d;
        }

        // ━━━ S046: 비급 & 트라이포드 (TASK 15) ━━━

        /// <summary>TRIPOD_LIST_REQ 빌드: empty</summary>
        public static byte[] TripodListReq()
        {
            return Build(MsgType.TRIPOD_LIST_REQ);
        }

        /// <summary>TRIPOD_EQUIP 빌드: skill_id(2) tier(1) option_idx(1) = 4B</summary>
        public static byte[] TripodEquip(ushort skillId, byte tier, byte optionIdx)
        {
            byte[] payload = new byte[4];
            BitConverter.GetBytes(skillId).CopyTo(payload, 0);
            payload[2] = tier;
            payload[3] = optionIdx;
            return Build(MsgType.TRIPOD_EQUIP, payload);
        }

        /// <summary>SCROLL_DISCOVER 빌드: scroll_slot(1)</summary>
        public static byte[] ScrollDiscover(byte scrollSlot)
        {
            return Build(MsgType.SCROLL_DISCOVER, new byte[] { scrollSlot });
        }

        /// <summary>TRIPOD_LIST 파싱: skill_count(1) {skill_id(2) tier_count(1) {tier(1) unlocked_count(1) {option_idx(1)}*N equipped_idx(1)}*N}*N</summary>
        public static TripodListData ParseTripodList(byte[] payload)
        {
            var d = new TripodListData();
            int off = 0;
            byte skillCount = payload[off]; off += 1;
            d.Skills = new TripodSkillInfo[skillCount];
            for (int i = 0; i < skillCount; i++)
            {
                var skill = new TripodSkillInfo();
                skill.SkillId = BitConverter.ToUInt16(payload, off); off += 2;
                byte tierCount = payload[off]; off += 1;
                skill.Tiers = new TripodTierInfo[tierCount];
                for (int j = 0; j < tierCount; j++)
                {
                    var tier = new TripodTierInfo();
                    tier.Tier = payload[off]; off += 1;
                    byte unlockedCount = payload[off]; off += 1;
                    tier.UnlockedOptions = new byte[unlockedCount];
                    for (int k = 0; k < unlockedCount; k++)
                    {
                        tier.UnlockedOptions[k] = payload[off]; off += 1;
                    }
                    tier.EquippedIdx = payload[off]; off += 1;
                    skill.Tiers[j] = tier;
                }
                d.Skills[i] = skill;
            }
            return d;
        }

        /// <summary>TRIPOD_EQUIP_RESULT 파싱: result(1)</summary>
        public static TripodEquipResult ParseTripodEquipResult(byte[] payload)
        {
            return (TripodEquipResult)payload[0];
        }

        /// <summary>SCROLL_DISCOVER RESP 파싱: result(1) [+ skill_id(2) tier(1) option_idx(1) if success]</summary>
        public static ScrollDiscoverResultData ParseScrollDiscoverResult(byte[] payload)
        {
            var d = new ScrollDiscoverResultData();
            d.Result = (ScrollDiscoverResult)payload[0];
            if (d.Result == ScrollDiscoverResult.SUCCESS && payload.Length >= 5)
            {
                d.SkillId = BitConverter.ToUInt16(payload, 1);
                d.Tier = payload[3];
                d.OptionIdx = payload[4];
            }
            return d;
        }

        // ━━━ S047: 현상금 시스템 ━━━

        /// <summary>BOUNTY_LIST_REQ 빌더: empty</summary>
        public static byte[] BountyListReq()
        {
            return Build(MsgType.BOUNTY_LIST_REQ);
        }

        /// <summary>BOUNTY_ACCEPT 빌더: bounty_id(2)</summary>
        public static byte[] BountyAccept(ushort bountyId)
        {
            var payload = BitConverter.GetBytes(bountyId);
            return Build(MsgType.BOUNTY_ACCEPT, payload);
        }

        /// <summary>BOUNTY_COMPLETE REQ 빌더: bounty_id(2)</summary>
        public static byte[] BountyCompleteReq(ushort bountyId)
        {
            var payload = BitConverter.GetBytes(bountyId);
            return Build(MsgType.BOUNTY_COMPLETE, payload);
        }

        /// <summary>BOUNTY_RANKING_REQ 빌더: empty</summary>
        public static byte[] BountyRankingReq()
        {
            return Build(MsgType.BOUNTY_RANKING_REQ);
        }

        /// <summary>BOUNTY_LIST 파싱: daily_count(1) + [bounty entries] + has_weekly(1) + [weekly] + accepted_count(1)</summary>
        public static BountyListData ParseBountyList(byte[] payload)
        {
            var d = new BountyListData();
            int off = 0;

            byte dailyCount = payload[off]; off += 1;
            d.DailyBounties = new BountyInfo[dailyCount];
            for (int i = 0; i < dailyCount; i++)
            {
                d.DailyBounties[i] = ParseBountyInfoEntry(payload, ref off);
            }

            d.HasWeekly = payload[off] != 0; off += 1;
            if (d.HasWeekly)
            {
                d.WeeklyBounty = ParseBountyInfoEntry(payload, ref off);
            }

            d.AcceptedCount = payload[off]; off += 1;
            return d;
        }

        private static BountyInfo ParseBountyInfoEntry(byte[] payload, ref int off)
        {
            var b = new BountyInfo();
            b.BountyId = BitConverter.ToUInt16(payload, off); off += 2;
            b.MonsterId = BitConverter.ToUInt16(payload, off); off += 2;
            b.Level = payload[off]; off += 1;
            byte zoneLen = payload[off]; off += 1;
            b.Zone = System.Text.Encoding.UTF8.GetString(payload, off, zoneLen); off += zoneLen;
            b.Gold = BitConverter.ToUInt32(payload, off); off += 4;
            b.Exp = BitConverter.ToUInt32(payload, off); off += 4;
            b.Token = payload[off]; off += 1;
            b.Accepted = payload[off]; off += 1;
            b.Completed = payload[off]; off += 1;
            return b;
        }

        /// <summary>BOUNTY_ACCEPT_RESULT 파싱: result(1) [+ bounty_id(2)]</summary>
        public static BountyAcceptResultData ParseBountyAcceptResult(byte[] payload)
        {
            var d = new BountyAcceptResultData();
            d.Result = (BountyAcceptResult)payload[0];
            if (d.Result == BountyAcceptResult.SUCCESS && payload.Length >= 3)
            {
                d.BountyId = BitConverter.ToUInt16(payload, 1);
            }
            return d;
        }

        /// <summary>BOUNTY_COMPLETE RESP 파싱: result(1)+bounty_id(2)+gold(4)+exp(4)+token(1)</summary>
        public static BountyCompleteData ParseBountyComplete(byte[] payload)
        {
            var d = new BountyCompleteData();
            d.Result = (BountyCompleteResult)payload[0];
            if (d.Result == BountyCompleteResult.SUCCESS && payload.Length >= 12)
            {
                d.BountyId = BitConverter.ToUInt16(payload, 1);
                d.Gold = BitConverter.ToUInt32(payload, 3);
                d.Exp = BitConverter.ToUInt32(payload, 7);
                d.Token = payload[11];
            }
            else if (payload.Length >= 3)
            {
                d.BountyId = BitConverter.ToUInt16(payload, 1);
            }
            return d;
        }

        /// <summary>BOUNTY_RANKING 파싱: rank_count(1) + [rank(1)+name_len(1)+name(str)+score(2)] + my_rank(1)+my_score(2)</summary>
        public static BountyRankingData ParseBountyRanking(byte[] payload)
        {
            var d = new BountyRankingData();
            int off = 0;

            byte rankCount = payload[off]; off += 1;
            d.Rankings = new BountyRankEntry[rankCount];
            for (int i = 0; i < rankCount; i++)
            {
                var entry = new BountyRankEntry();
                entry.Rank = payload[off]; off += 1;
                byte nameLen = payload[off]; off += 1;
                entry.Name = System.Text.Encoding.UTF8.GetString(payload, off, nameLen); off += nameLen;
                entry.Score = BitConverter.ToUInt16(payload, off); off += 2;
                d.Rankings[i] = entry;
            }

            d.MyRank = payload[off]; off += 1;
            d.MyScore = BitConverter.ToUInt16(payload, off); off += 2;
            return d;
        }

        /// <summary>PVP_BOUNTY_NOTIFY 파싱: target_entity(8)+tier(1)+kill_streak(2)+gold_reward(4)+name_len(1)+name(str)</summary>
        public static PvPBountyNotifyData ParsePvPBountyNotify(byte[] payload)
        {
            var d = new PvPBountyNotifyData();
            int off = 0;
            d.TargetEntity = BitConverter.ToUInt64(payload, off); off += 8;
            d.Tier = payload[off]; off += 1;
            d.KillStreak = BitConverter.ToUInt16(payload, off); off += 2;
            d.GoldReward = BitConverter.ToUInt32(payload, off); off += 4;
            byte nameLen = payload[off]; off += 1;
            d.Name = System.Text.Encoding.UTF8.GetString(payload, off, nameLen); off += nameLen;
            return d;
        }

        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        //  S048: Phase 9 — 퀘스트 심화 (TASK 4, MsgType 400-405)
        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        /// <summary>DAILY_QUEST_LIST_REQ 빌더: empty</summary>
        public static byte[] DailyQuestListReq()
        {
            return Build(MsgType.DAILY_QUEST_LIST_REQ);
        }

        /// <summary>WEEKLY_QUEST_REQ 빌더: empty</summary>
        public static byte[] WeeklyQuestReq()
        {
            return Build(MsgType.WEEKLY_QUEST_REQ);
        }

        /// <summary>REPUTATION_QUERY 빌더: empty</summary>
        public static byte[] ReputationQuery()
        {
            return Build(MsgType.REPUTATION_QUERY);
        }

        /// <summary>DAILY_QUEST_LIST 파싱: quest_count(1) + [dq_id(2)+type_len(1)+type(str)+name_len(1)+name(str)+target_id(2)+count(1)+progress(1)+completed(1)+reward_exp(4)+reward_gold(4)+rep_faction_len(1)+rep_faction(str)+rep_amount(2)]</summary>
        public static DailyQuestListData ParseDailyQuestList(byte[] payload)
        {
            var d = new DailyQuestListData();
            int off = 0;

            byte questCount = payload[off]; off += 1;
            d.Quests = new DailyQuestInfo[questCount];

            for (int i = 0; i < questCount; i++)
            {
                var q = new DailyQuestInfo();
                q.DqId = BitConverter.ToUInt16(payload, off); off += 2;

                byte typeLen = payload[off]; off += 1;
                q.Type = System.Text.Encoding.UTF8.GetString(payload, off, typeLen); off += typeLen;

                byte nameLen = payload[off]; off += 1;
                q.NameKr = System.Text.Encoding.UTF8.GetString(payload, off, nameLen); off += nameLen;

                q.TargetId = BitConverter.ToUInt16(payload, off); off += 2;
                q.Count = payload[off]; off += 1;
                q.Progress = payload[off]; off += 1;
                q.Completed = payload[off]; off += 1;
                q.RewardExp = BitConverter.ToUInt32(payload, off); off += 4;
                q.RewardGold = BitConverter.ToUInt32(payload, off); off += 4;

                byte repFactionLen = payload[off]; off += 1;
                q.RepFaction = System.Text.Encoding.UTF8.GetString(payload, off, repFactionLen); off += repFactionLen;
                q.RepAmount = BitConverter.ToUInt16(payload, off); off += 2;

                d.Quests[i] = q;
            }

            return d;
        }

        /// <summary>WEEKLY_QUEST 파싱: has_quest(1) + [wq_id(2)+type_len(1)+type(str)+name_len(1)+name(str)+target_id(2)+count(1)+progress(1)+completed(1)+reward_exp(4)+reward_gold(4)+reward_dungeon_token(1)+rep_faction_len(1)+rep_faction(str)+rep_amount(2)]</summary>
        public static WeeklyQuestData ParseWeeklyQuest(byte[] payload)
        {
            var d = new WeeklyQuestData();
            int off = 0;

            byte hasQuest = payload[off]; off += 1;
            d.HasQuest = hasQuest != 0;

            if (d.HasQuest)
            {
                var q = new WeeklyQuestInfo();
                q.WqId = BitConverter.ToUInt16(payload, off); off += 2;

                byte typeLen = payload[off]; off += 1;
                q.Type = System.Text.Encoding.UTF8.GetString(payload, off, typeLen); off += typeLen;

                byte nameLen = payload[off]; off += 1;
                q.NameKr = System.Text.Encoding.UTF8.GetString(payload, off, nameLen); off += nameLen;

                q.TargetId = BitConverter.ToUInt16(payload, off); off += 2;
                q.Count = payload[off]; off += 1;
                q.Progress = payload[off]; off += 1;
                q.Completed = payload[off]; off += 1;
                q.RewardExp = BitConverter.ToUInt32(payload, off); off += 4;
                q.RewardGold = BitConverter.ToUInt32(payload, off); off += 4;
                q.RewardDungeonToken = payload[off]; off += 1;

                byte repFactionLen = payload[off]; off += 1;
                q.RepFaction = System.Text.Encoding.UTF8.GetString(payload, off, repFactionLen); off += repFactionLen;
                q.RepAmount = BitConverter.ToUInt16(payload, off); off += 2;

                d.Quest = q;
            }

            return d;
        }

        /// <summary>REPUTATION_INFO 파싱: faction_count(1) + [faction_len(1)+faction(str)+name_kr_len(1)+name_kr(str)+points(4)+tier_name_len(1)+tier_name(str)+next_tier_min(4)]</summary>
        public static ReputationInfoData ParseReputationInfo(byte[] payload)
        {
            var d = new ReputationInfoData();
            int off = 0;

            byte factionCount = payload[off]; off += 1;
            d.Factions = new ReputationFactionInfo[factionCount];

            for (int i = 0; i < factionCount; i++)
            {
                var f = new ReputationFactionInfo();

                byte factionLen = payload[off]; off += 1;
                f.Faction = System.Text.Encoding.UTF8.GetString(payload, off, factionLen); off += factionLen;

                byte nameKrLen = payload[off]; off += 1;
                f.NameKr = System.Text.Encoding.UTF8.GetString(payload, off, nameKrLen); off += nameKrLen;

                f.Points = BitConverter.ToUInt32(payload, off); off += 4;

                byte tierNameLen = payload[off]; off += 1;
                f.TierName = System.Text.Encoding.UTF8.GetString(payload, off, tierNameLen); off += tierNameLen;

                f.NextTierMin = BitConverter.ToUInt32(payload, off); off += 4;

                d.Factions[i] = f;
            }

            return d;
        }

        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        //  S049: 칭호/도감/2차전직 (TASK 7, MsgType 440-447)
        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        /// <summary>TITLE_LIST_REQ 빌더: empty</summary>
        public static byte[] TitleListReq()
        {
            return Build(MsgType.TITLE_LIST_REQ);
        }

        /// <summary>TITLE_EQUIP 빌더: title_id(u16) — 0이면 해제</summary>
        public static byte[] TitleEquip(ushort titleId)
        {
            return Build(MsgType.TITLE_EQUIP, BitConverter.GetBytes(titleId));
        }

        /// <summary>COLLECTION_QUERY 빌더: empty</summary>
        public static byte[] CollectionQuery()
        {
            return Build(MsgType.COLLECTION_QUERY);
        }

        /// <summary>JOB_CHANGE_REQ 빌더: job_name_len(u8) + job_name(utf8)</summary>
        public static byte[] JobChangeReq(string jobName)
        {
            byte[] nameBytes = Encoding.UTF8.GetBytes(jobName);
            byte[] payload = new byte[1 + nameBytes.Length];
            payload[0] = (byte)nameBytes.Length;
            if (nameBytes.Length > 0)
                Buffer.BlockCopy(nameBytes, 0, payload, 1, nameBytes.Length);
            return Build(MsgType.JOB_CHANGE_REQ, payload);
        }

        /// <summary>TITLE_LIST 파싱: equipped_id(u16) + count(u8) + [title_id(u16)+name_len(u8)+name(utf8)+bonus_type_len(u8)+bonus_type(utf8)+bonus_value(u16)+unlocked(u8)]*N</summary>
        public static TitleListData ParseTitleList(byte[] payload)
        {
            var d = new TitleListData();
            int off = 0;

            d.EquippedId = BitConverter.ToUInt16(payload, off); off += 2;
            byte count = payload[off]; off += 1;
            d.Titles = new TitleInfo[count];

            for (int i = 0; i < count; i++)
            {
                var t = new TitleInfo();
                t.TitleId = BitConverter.ToUInt16(payload, off); off += 2;

                byte nameLen = payload[off]; off += 1;
                t.Name = Encoding.UTF8.GetString(payload, off, nameLen); off += nameLen;

                byte bonusTypeLen = payload[off]; off += 1;
                t.BonusType = Encoding.UTF8.GetString(payload, off, bonusTypeLen); off += bonusTypeLen;

                t.BonusValue = BitConverter.ToUInt16(payload, off); off += 2;
                t.Unlocked = payload[off] != 0; off += 1;

                d.Titles[i] = t;
            }

            return d;
        }

        /// <summary>TITLE_EQUIP_RESULT 파싱: result(u8) + title_id(u16)</summary>
        public static TitleEquipResultData ParseTitleEquipResult(byte[] payload)
        {
            var d = new TitleEquipResultData();
            d.Result = (TitleEquipResult)payload[0];
            d.TitleId = BitConverter.ToUInt16(payload, 1);
            return d;
        }

        /// <summary>COLLECTION_INFO 파싱: monster_cat_count(u8) + [...] + equip_tier_count(u8) + [...]</summary>
        public static CollectionInfoData ParseCollectionInfo(byte[] payload)
        {
            var d = new CollectionInfoData();
            int off = 0;

            // 몬스터 도감
            byte monsterCatCount = payload[off]; off += 1;
            d.MonsterCategories = new MonsterCollectionCategory[monsterCatCount];
            for (int i = 0; i < monsterCatCount; i++)
            {
                var c = new MonsterCollectionCategory();
                c.CatId = payload[off]; off += 1;

                byte nameLen = payload[off]; off += 1;
                c.Name = Encoding.UTF8.GetString(payload, off, nameLen); off += nameLen;

                c.Total = payload[off]; off += 1;
                c.Registered = payload[off]; off += 1;
                c.Completed = payload[off]; off += 1;

                byte bonusTypeLen = payload[off]; off += 1;
                c.BonusType = Encoding.UTF8.GetString(payload, off, bonusTypeLen); off += bonusTypeLen;

                c.BonusValue = BitConverter.ToUInt16(payload, off); off += 2;

                d.MonsterCategories[i] = c;
            }

            // 장비 도감
            byte equipTierCount = payload[off]; off += 1;
            d.EquipTiers = new EquipCollectionTier[equipTierCount];
            for (int i = 0; i < equipTierCount; i++)
            {
                var e = new EquipCollectionTier();

                byte tierLen = payload[off]; off += 1;
                e.Tier = Encoding.UTF8.GetString(payload, off, tierLen); off += tierLen;

                byte tierKrLen = payload[off]; off += 1;
                e.TierKr = Encoding.UTF8.GetString(payload, off, tierKrLen); off += tierKrLen;

                e.Registered = payload[off]; off += 1;

                byte bonusTypeLen = payload[off]; off += 1;
                e.BonusType = Encoding.UTF8.GetString(payload, off, bonusTypeLen); off += bonusTypeLen;

                e.BonusValue = BitConverter.ToUInt16(payload, off); off += 2;

                d.EquipTiers[i] = e;
            }

            return d;
        }

        /// <summary>JOB_CHANGE_RESULT 파싱: result(u8)+job_name_len(u8)+job_name(utf8)+bonus_count(u8)+[bonus_key_len(u8)+bonus_key(utf8)+bonus_value(i16)]*N+new_skill_count(u8)+[skill_id(u16)]*M</summary>
        public static JobChangeResultData ParseJobChangeResult(byte[] payload)
        {
            var d = new JobChangeResultData();
            int off = 0;

            d.Result = (JobChangeResult)payload[off]; off += 1;

            byte jobNameLen = payload[off]; off += 1;
            d.JobName = Encoding.UTF8.GetString(payload, off, jobNameLen); off += jobNameLen;

            byte bonusCount = payload[off]; off += 1;
            d.Bonuses = new JobChangeBonusEntry[bonusCount];
            for (int i = 0; i < bonusCount; i++)
            {
                var b = new JobChangeBonusEntry();
                byte keyLen = payload[off]; off += 1;
                b.Key = Encoding.UTF8.GetString(payload, off, keyLen); off += keyLen;
                b.Value = BitConverter.ToInt16(payload, off); off += 2;
                d.Bonuses[i] = b;
            }

            byte skillCount = payload[off]; off += 1;
            d.NewSkills = new ushort[skillCount];
            for (int i = 0; i < skillCount; i++)
            {
                d.NewSkills[i] = BitConverter.ToUInt16(payload, off); off += 2;
            }

            return d;
        }

        // ━━━ S050: 각인/초월 (TASK 8 Enhancement) ━━━

        /// <summary>ENGRAVING_LIST_REQ 빌더: empty</summary>
        public static byte[] EngravingListReq()
        {
            return Build(MsgType.ENGRAVING_LIST_REQ);
        }

        /// <summary>ENGRAVING_EQUIP 빌더: action(1) + name_len(1) + name(str)</summary>
        public static byte[] EngravingEquip(byte action, string name)
        {
            byte[] nameBytes = System.Text.Encoding.UTF8.GetBytes(name);
            byte[] payload = new byte[2 + nameBytes.Length];
            payload[0] = action;
            payload[1] = (byte)nameBytes.Length;
            if (nameBytes.Length > 0)
                Buffer.BlockCopy(nameBytes, 0, payload, 2, nameBytes.Length);
            return Build(MsgType.ENGRAVING_EQUIP, payload);
        }

        /// <summary>TRANSCEND_REQ 빌더: slot_len(1) + slot(str)</summary>
        public static byte[] TranscendReq(string slot)
        {
            byte[] slotBytes = System.Text.Encoding.UTF8.GetBytes(slot);
            byte[] payload = new byte[1 + slotBytes.Length];
            payload[0] = (byte)slotBytes.Length;
            if (slotBytes.Length > 0)
                Buffer.BlockCopy(slotBytes, 0, payload, 1, slotBytes.Length);
            return Build(MsgType.TRANSCEND_REQ, payload);
        }

        /// <summary>ENGRAVING_LIST 파싱: count(1) + [name_len(1)+name+name_kr_len(1)+name_kr+points(1)+active_level(1)+is_active(1)+effect_key_len(1)+effect_key+effect_value(2)] * N</summary>
        public static EngravingListData ParseEngravingList(byte[] payload)
        {
            var d = new EngravingListData();
            int off = 0;

            byte count = payload[off]; off += 1;
            d.Engravings = new EngravingInfo[count];

            for (int i = 0; i < count; i++)
            {
                var e = new EngravingInfo();

                byte nameLen = payload[off]; off += 1;
                e.Name = System.Text.Encoding.UTF8.GetString(payload, off, nameLen); off += nameLen;

                byte nameKrLen = payload[off]; off += 1;
                e.NameKr = System.Text.Encoding.UTF8.GetString(payload, off, nameKrLen); off += nameKrLen;

                e.Points = payload[off]; off += 1;
                e.ActiveLevel = payload[off]; off += 1;
                e.IsActive = payload[off] != 0; off += 1;

                byte effectKeyLen = payload[off]; off += 1;
                e.EffectKey = System.Text.Encoding.UTF8.GetString(payload, off, effectKeyLen); off += effectKeyLen;

                e.EffectValue = BitConverter.ToUInt16(payload, off); off += 2;

                d.Engravings[i] = e;
            }

            return d;
        }

        /// <summary>ENGRAVING_RESULT 파싱: result(1) + name_len(1) + name(str) + active_count(1)</summary>
        public static EngravingResultData ParseEngravingResult(byte[] payload)
        {
            var d = new EngravingResultData();
            int off = 0;

            d.Result = (EngravingResult)payload[off]; off += 1;

            byte nameLen = payload[off]; off += 1;
            d.Name = System.Text.Encoding.UTF8.GetString(payload, off, nameLen); off += nameLen;

            d.ActiveCount = payload[off]; off += 1;

            return d;
        }

        /// <summary>TRANSCEND_RESULT 파싱: result(1) + slot_len(1) + slot(str) + new_level(1) + gold_cost(4) + success(1)</summary>
        public static TranscendResultData ParseTranscendResult(byte[] payload)
        {
            var d = new TranscendResultData();
            int off = 0;

            d.Result = (TranscendResult)payload[off]; off += 1;

            byte slotLen = payload[off]; off += 1;
            d.Slot = System.Text.Encoding.UTF8.GetString(payload, off, slotLen); off += slotLen;

            d.NewLevel = payload[off]; off += 1;
            d.GoldCost = BitConverter.ToUInt32(payload, off); off += 4;
            d.Success = payload[off] != 0; off += 1;

            return d;
        }

        // ━━━ S051: 소셜 심화 (TASK 5, MsgType 410-422) ━━━

        /// <summary>FRIEND_REQUEST 빌더: target_name_len(1) + target_name(N)</summary>
        public static byte[] FriendRequest(string targetName)
        {
            byte[] nameBytes = Encoding.UTF8.GetBytes(targetName);
            byte[] payload = new byte[1 + nameBytes.Length];
            payload[0] = (byte)nameBytes.Length;
            if (nameBytes.Length > 0)
                Buffer.BlockCopy(nameBytes, 0, payload, 1, nameBytes.Length);
            return Build(MsgType.FRIEND_REQUEST, payload);
        }

        /// <summary>FRIEND_ACCEPT 빌더: from_name_len(1) + from_name(N)</summary>
        public static byte[] FriendAccept(string fromName)
        {
            byte[] nameBytes = Encoding.UTF8.GetBytes(fromName);
            byte[] payload = new byte[1 + nameBytes.Length];
            payload[0] = (byte)nameBytes.Length;
            if (nameBytes.Length > 0)
                Buffer.BlockCopy(nameBytes, 0, payload, 1, nameBytes.Length);
            return Build(MsgType.FRIEND_ACCEPT, payload);
        }

        /// <summary>FRIEND_REJECT 빌더: from_name_len(1) + from_name(N)</summary>
        public static byte[] FriendReject(string fromName)
        {
            byte[] nameBytes = Encoding.UTF8.GetBytes(fromName);
            byte[] payload = new byte[1 + nameBytes.Length];
            payload[0] = (byte)nameBytes.Length;
            if (nameBytes.Length > 0)
                Buffer.BlockCopy(nameBytes, 0, payload, 1, nameBytes.Length);
            return Build(MsgType.FRIEND_REJECT, payload);
        }

        /// <summary>FRIEND_LIST_REQ 빌더: empty</summary>
        public static byte[] FriendListReq()
        {
            return Build(MsgType.FRIEND_LIST_REQ);
        }

        /// <summary>BLOCK_PLAYER 빌더: action(1) + name_len(1) + name(N)</summary>
        public static byte[] BlockPlayer(byte action, string name)
        {
            byte[] nameBytes = Encoding.UTF8.GetBytes(name);
            byte[] payload = new byte[2 + nameBytes.Length];
            payload[0] = action;
            payload[1] = (byte)nameBytes.Length;
            if (nameBytes.Length > 0)
                Buffer.BlockCopy(nameBytes, 0, payload, 2, nameBytes.Length);
            return Build(MsgType.BLOCK_PLAYER, payload);
        }

        /// <summary>BLOCK_LIST_REQ 빌더: empty</summary>
        public static byte[] BlockListReq()
        {
            return Build(MsgType.BLOCK_LIST_REQ);
        }

        /// <summary>PARTY_FINDER_LIST_REQ 빌더: category(1)</summary>
        public static byte[] PartyFinderListReq(byte category)
        {
            return Build(MsgType.PARTY_FINDER_LIST_REQ, new byte[] { category });
        }

        /// <summary>PARTY_FINDER_CREATE 빌더: title_len(1) + title(N) + category(1) + min_level(1) + role(1)</summary>
        public static byte[] PartyFinderCreate(string title, byte category, byte minLevel, byte role)
        {
            byte[] titleBytes = Encoding.UTF8.GetBytes(title);
            byte[] payload = new byte[1 + titleBytes.Length + 3];
            payload[0] = (byte)titleBytes.Length;
            if (titleBytes.Length > 0)
                Buffer.BlockCopy(titleBytes, 0, payload, 1, titleBytes.Length);
            int off = 1 + titleBytes.Length;
            payload[off] = category;
            payload[off + 1] = minLevel;
            payload[off + 2] = role;
            return Build(MsgType.PARTY_FINDER_CREATE, payload);
        }

        /// <summary>FRIEND_REQUEST_RESULT 파싱: result(1)</summary>
        public static FriendRequestResult ParseFriendRequestResult(byte[] payload)
        {
            return (FriendRequestResult)payload[0];
        }

        /// <summary>FRIEND_LIST 파싱: count(1) {name_len(1) name(N) is_online(1) zone_id(4)}*N</summary>
        public static FriendListData ParseFriendList(byte[] payload)
        {
            var d = new FriendListData();
            int off = 0;
            byte count = payload[off]; off += 1;
            d.Friends = new FriendInfo[count];

            for (int i = 0; i < count; i++)
            {
                var f = new FriendInfo();
                byte nameLen = payload[off]; off += 1;
                f.Name = Encoding.UTF8.GetString(payload, off, nameLen); off += nameLen;
                f.IsOnline = payload[off] != 0; off += 1;
                f.ZoneId = BitConverter.ToUInt32(payload, off); off += 4;
                d.Friends[i] = f;
            }
            return d;
        }

        /// <summary>BLOCK_RESULT 파싱: result(1)</summary>
        public static BlockPlayerResult ParseBlockResult(byte[] payload)
        {
            return (BlockPlayerResult)payload[0];
        }

        /// <summary>BLOCK_LIST 파싱: count(1) {name_len(1) name(N)}*N</summary>
        public static BlockListData ParseBlockList(byte[] payload)
        {
            var d = new BlockListData();
            int off = 0;
            byte count = payload[off]; off += 1;
            d.Names = new string[count];

            for (int i = 0; i < count; i++)
            {
                byte nameLen = payload[off]; off += 1;
                d.Names[i] = Encoding.UTF8.GetString(payload, off, nameLen); off += nameLen;
            }
            return d;
        }

        /// <summary>PARTY_FINDER_LIST 파싱: count(1) {listing_id(4) owner_len(1) owner(N) title_len(1) title(N) category(1) min_level(1) role(1)}*N</summary>
        public static PartyFinderListData ParsePartyFinderList(byte[] payload)
        {
            var d = new PartyFinderListData();
            int off = 0;
            byte count = payload[off]; off += 1;
            d.Listings = new PartyFinderListingInfo[count];

            for (int i = 0; i < count; i++)
            {
                var l = new PartyFinderListingInfo();
                l.ListingId = BitConverter.ToUInt32(payload, off); off += 4;

                byte ownerLen = payload[off]; off += 1;
                l.OwnerName = Encoding.UTF8.GetString(payload, off, ownerLen); off += ownerLen;

                byte titleLen = payload[off]; off += 1;
                l.Title = Encoding.UTF8.GetString(payload, off, titleLen); off += titleLen;

                l.Category = (PartyFinderCategory)payload[off]; off += 1;
                l.MinLevel = payload[off]; off += 1;
                l.Role = (PartyFinderRole)payload[off]; off += 1;

                d.Listings[i] = l;
            }
            return d;
        }

        // ━━━ S052: 내구도/수리/리롤 (TASK 9, MsgType 462-467) ━━━

        /// <summary>REPAIR_REQ 빌더: mode(1) + inv_slot(1)</summary>
        public static byte[] RepairReq(byte mode, byte invSlot)
        {
            return Build(MsgType.REPAIR_REQ, new byte[] { mode, invSlot });
        }

        /// <summary>REROLL_REQ 빌더: inv_slot(1) + lock_count(1) + [lock_idx(1)]*N</summary>
        public static byte[] RerollReq(byte invSlot, byte[] lockIndices)
        {
            int lockCount = lockIndices?.Length ?? 0;
            byte[] payload = new byte[2 + lockCount];
            payload[0] = invSlot;
            payload[1] = (byte)lockCount;
            if (lockCount > 0)
                Buffer.BlockCopy(lockIndices, 0, payload, 2, lockCount);
            return Build(MsgType.REROLL_REQ, payload);
        }

        /// <summary>DURABILITY_QUERY 빌더: empty</summary>
        public static byte[] DurabilityQuery()
        {
            return Build(MsgType.DURABILITY_QUERY);
        }

        /// <summary>REPAIR_RESULT 파싱: result(1) + total_cost(4u32) + repaired_count(1)</summary>
        public static RepairResultData ParseRepairResult(byte[] payload)
        {
            var d = new RepairResultData();
            d.Result = (RepairResult)payload[0];
            d.TotalCost = BitConverter.ToUInt32(payload, 1);
            d.RepairedCount = payload[5];
            return d;
        }

        /// <summary>REROLL_RESULT 파싱: result(1) + opt_count(1) + [stat_len(1)+stat(str)+value(2i16)+locked(1)]*N</summary>
        public static RerollResultData ParseRerollResult(byte[] payload)
        {
            var d = new RerollResultData();
            int off = 0;
            d.Result = (RerollResult)payload[off]; off += 1;
            byte optCount = payload[off]; off += 1;
            d.Options = new RandomOptionInfo[optCount];

            for (int i = 0; i < optCount; i++)
            {
                var opt = new RandomOptionInfo();
                byte statLen = payload[off]; off += 1;
                opt.StatName = Encoding.UTF8.GetString(payload, off, statLen); off += statLen;
                opt.Value = BitConverter.ToInt16(payload, off); off += 2;
                opt.Locked = payload[off] != 0; off += 1;
                d.Options[i] = opt;
            }
            return d;
        }

        /// <summary>DURABILITY_NOTIFY 파싱: inv_slot(1) + durability(4f32) + is_broken(1)</summary>
        public static DurabilityNotifyData ParseDurabilityNotify(byte[] payload)
        {
            var d = new DurabilityNotifyData();
            d.InvSlot = payload[0];
            d.Durability = BitConverter.ToSingle(payload, 1);
            d.IsBroken = payload[5] != 0;
            return d;
        }

        // ━━━ S053: 전장/길드전/PvP시즌 (TASK 6, MsgType 430-435) ━━━

        /// <summary>BATTLEGROUND_QUEUE 빌더: action(1) + mode(1)</summary>
        public static byte[] BattlegroundQueue(byte action, byte mode)
        {
            return Build(MsgType.BATTLEGROUND_QUEUE, new byte[] { action, mode });
        }

        /// <summary>BATTLEGROUND_SCORE 빌더: action(1) + point_index(1)</summary>
        public static byte[] BattlegroundScore(byte action, byte pointIndex)
        {
            return Build(MsgType.BATTLEGROUND_SCORE, new byte[] { action, pointIndex });
        }

        /// <summary>GUILD_WAR_DECLARE 빌더: action(1) + target_guild_id(4)</summary>
        public static byte[] GuildWarDeclare(byte action, uint targetGuildId)
        {
            byte[] payload = new byte[5];
            payload[0] = action;
            BitConverter.GetBytes(targetGuildId).CopyTo(payload, 1);
            return Build(MsgType.GUILD_WAR_DECLARE, payload);
        }

        /// <summary>BATTLEGROUND_STATUS 파싱: status(1)+match_id(4)+mode(1)+team(1)+queue_count(1)</summary>
        public static BattlegroundStatusData ParseBattlegroundStatus(byte[] payload)
        {
            var d = new BattlegroundStatusData();
            d.Status = (BattlegroundStatus)payload[0];
            d.MatchId = BitConverter.ToUInt32(payload, 1);
            d.Mode = (BattlegroundMode)payload[5];
            d.Team = (BattlegroundTeam)payload[6];
            d.QueueCount = payload[7];
            return d;
        }

        /// <summary>BATTLEGROUND_SCORE_UPDATE 파싱: mode(1)+red_score(4)+blue_score(4)+time(4)</summary>
        public static BattlegroundScoreUpdateData ParseBattlegroundScoreUpdate(byte[] payload)
        {
            var d = new BattlegroundScoreUpdateData();
            d.Mode = (BattlegroundMode)payload[0];
            d.RedScore = BitConverter.ToUInt32(payload, 1);
            d.BlueScore = BitConverter.ToUInt32(payload, 5);
            d.TimeRemaining = BitConverter.ToUInt32(payload, 9);
            return d;
        }

        /// <summary>GUILD_WAR_STATUS 파싱: status(1)+war_id(4)+guild_a(4)+guild_b(4)+crystal_hp_a(4)+crystal_hp_b(4)+time(4)</summary>
        public static GuildWarStatusData ParseGuildWarStatus(byte[] payload)
        {
            var d = new GuildWarStatusData();
            d.Status = (GuildWarStatus)payload[0];
            d.WarId = BitConverter.ToUInt32(payload, 1);
            d.GuildAId = BitConverter.ToUInt32(payload, 5);
            d.GuildBId = BitConverter.ToUInt32(payload, 9);
            d.CrystalHpA = BitConverter.ToUInt32(payload, 13);
            d.CrystalHpB = BitConverter.ToUInt32(payload, 17);
            d.TimeRemaining = BitConverter.ToUInt32(payload, 21);
            return d;
        }

        // ━━━ S054: 보조 화폐/토큰 상점 (TASK 10, MsgType 468-473) ━━━

        /// <summary>CURRENCY_QUERY 빌더: 빈 페이로드</summary>
        public static byte[] CurrencyQuery()
        {
            return Build(MsgType.CURRENCY_QUERY, new byte[0]);
        }

        /// <summary>TOKEN_SHOP_LIST 빌더: shop_type(1)</summary>
        public static byte[] TokenShopList(byte shopType)
        {
            return Build(MsgType.TOKEN_SHOP_LIST, new byte[] { shopType });
        }

        /// <summary>TOKEN_SHOP_BUY 빌더: shop_id(2) + quantity(1)</summary>
        public static byte[] TokenShopBuy(ushort shopId, byte quantity)
        {
            byte[] payload = new byte[3];
            BitConverter.GetBytes(shopId).CopyTo(payload, 0);
            payload[2] = quantity;
            return Build(MsgType.TOKEN_SHOP_BUY, payload);
        }

        /// <summary>CURRENCY_INFO 파싱: gold(4)+silver(4)+dungeon_token(4)+pvp_token(4)+guild_contribution(4)</summary>
        public static CurrencyInfoData ParseCurrencyInfo(byte[] payload)
        {
            var d = new CurrencyInfoData();
            d.Gold = BitConverter.ToUInt32(payload, 0);
            d.Silver = BitConverter.ToUInt32(payload, 4);
            d.DungeonToken = BitConverter.ToUInt32(payload, 8);
            d.PvpToken = BitConverter.ToUInt32(payload, 12);
            d.GuildContribution = BitConverter.ToUInt32(payload, 16);
            return d;
        }

        /// <summary>TOKEN_SHOP 파싱: shop_type(1)+count(1)+[shop_id(2)+price(4)+currency_type(1)+name_len(1)+name(N)]*N</summary>
        public static TokenShopData ParseTokenShop(byte[] payload)
        {
            var d = new TokenShopData();
            int off = 0;
            d.ShopType = (TokenShopType)payload[off]; off += 1;
            byte count = payload[off]; off += 1;
            d.Items = new TokenShopItem[count];

            for (int i = 0; i < count; i++)
            {
                var item = new TokenShopItem();
                item.ShopId = BitConverter.ToUInt16(payload, off); off += 2;
                item.Price = BitConverter.ToUInt32(payload, off); off += 4;
                item.CurrencyType = payload[off]; off += 1;
                byte nameLen = payload[off]; off += 1;
                item.Name = Encoding.UTF8.GetString(payload, off, nameLen); off += nameLen;
                d.Items[i] = item;
            }
            return d;
        }

        /// <summary>TOKEN_SHOP_BUY_RESULT 파싱: result(1)+shop_id(2)+remaining_currency(4)</summary>
        public static TokenShopBuyResultData ParseTokenShopBuyResult(byte[] payload)
        {
            var d = new TokenShopBuyResultData();
            d.Result = (TokenShopBuyResult)payload[0];
            d.ShopId = BitConverter.ToUInt16(payload, 1);
            d.RemainingCurrency = BitConverter.ToUInt32(payload, 3);
            return d;
        }

        // ━━━ S055: 비경 탐험 (TASK 17, MsgType 540-544) ━━━

        /// <summary>SECRET_REALM_ENTER 빌더: zone_id(1)+auto_spawn(1)</summary>
        public static byte[] SecretRealmEnter(byte zoneId, byte autoSpawn)
        {
            return Build(MsgType.SECRET_REALM_ENTER, new byte[] { zoneId, autoSpawn });
        }

        /// <summary>SECRET_REALM_COMPLETE 빌더: score_value(2)+extra_data(1)</summary>
        public static byte[] SecretRealmComplete(ushort scoreValue, byte extraData)
        {
            byte[] payload = new byte[3];
            BitConverter.GetBytes(scoreValue).CopyTo(payload, 0);
            payload[2] = extraData;
            return Build(MsgType.SECRET_REALM_COMPLETE, payload);
        }

        /// <summary>SECRET_REALM_FAIL 빌더: 빈 페이로드</summary>
        public static byte[] SecretRealmFail()
        {
            return Build(MsgType.SECRET_REALM_FAIL, new byte[0]);
        }

        /// <summary>SECRET_REALM_SPAWN 파싱: zone_id(1)+realm_type_idx(1)+is_special(1)+multiplier(2u16)+name_len(1)+name(utf8)</summary>
        public static SecretRealmSpawnData ParseSecretRealmSpawn(byte[] payload)
        {
            var d = new SecretRealmSpawnData();
            int off = 0;
            d.ZoneId = payload[off]; off += 1;
            d.RealmType = (SecretRealmType)payload[off]; off += 1;
            d.IsSpecial = payload[off] != 0; off += 1;
            ushort mulRaw = BitConverter.ToUInt16(payload, off); off += 2;
            d.Multiplier = mulRaw / 100f;
            byte nameLen = payload[off]; off += 1;
            d.Name = System.Text.Encoding.UTF8.GetString(payload, off, nameLen);
            return d;
        }

        /// <summary>SECRET_REALM_ENTER_RESULT 파싱: result(1)+instance_id(2)+realm_type(1)+time_limit(2)+is_special(1)+multiplier(2)</summary>
        public static SecretRealmEnterResultData ParseSecretRealmEnterResult(byte[] payload)
        {
            var d = new SecretRealmEnterResultData();
            int off = 0;
            d.Result = (SecretRealmEnterResult)payload[off]; off += 1;
            d.InstanceId = BitConverter.ToUInt16(payload, off); off += 2;
            d.RealmType = (SecretRealmType)payload[off]; off += 1;
            d.TimeLimit = BitConverter.ToUInt16(payload, off); off += 2;
            d.IsSpecial = payload[off] != 0; off += 1;
            ushort mulRaw = BitConverter.ToUInt16(payload, off); off += 2;
            d.Multiplier = mulRaw / 100f;
            return d;
        }

        /// <summary>SECRET_REALM_COMPLETE 파싱(서버응답): grade(1)+gold_reward(4)+bonus_info_len(1)+bonus_info(utf8)</summary>
        public static SecretRealmCompleteData ParseSecretRealmComplete(byte[] payload)
        {
            var d = new SecretRealmCompleteData();
            int off = 0;
            d.Grade = (SecretRealmGrade)payload[off]; off += 1;
            d.GoldReward = BitConverter.ToUInt32(payload, off); off += 4;
            byte bonusLen = payload[off]; off += 1;
            d.BonusInfo = bonusLen > 0 ? System.Text.Encoding.UTF8.GetString(payload, off, bonusLen) : "";
            return d;
        }

        /// <summary>SECRET_REALM_FAIL 파싱(서버응답): consolation_gold(4)</summary>
        public static SecretRealmFailData ParseSecretRealmFail(byte[] payload)
        {
            var d = new SecretRealmFailData();
            d.ConsolationGold = BitConverter.ToUInt32(payload, 0);
            return d;
        }
    }
}
