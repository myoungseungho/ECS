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
    }
}
