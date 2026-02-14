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
        MOVE            = 10,   // C→S: x(4f) y(4f) z(4f) [timestamp(4)] (Model C: 16B 권장)
        MOVE_BROADCAST  = 11,   // S→C: entity(8u64) x(4f) y(4f) z(4f)
        POS_QUERY       = 12,

        // AOI
        APPEAR          = 13,   // S→C: entity(8u64) x(4f) y(4f) z(4f)
        DISAPPEAR       = 14,   // S→C: entity(8u64)

        // 이동 검증 (세션 35: Model C)
        POSITION_CORRECTION = 15, // S→C: x(4f) y(4f) z(4f) = 12B (강제 위치 보정)

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

        // 몬스터 (세션 14 + 세션 36 AI 확장)
        MONSTER_SPAWN   = 110,  // S→C: entity(8u64) monster_id(4u32) level(4u32) hp(4i) max_hp(4i) x(4f) y(4f) z(4f) = 36B
        MONSTER_MOVE    = 111,  // S→C: entity(8) x(4f) y(4f) z(4f) = 20B (몬스터 이동)
        MONSTER_AGGRO   = 112,  // S→C: monster_entity(8) target_entity(8) = 16B (어그로 변경, target=0이면 해제)
        MONSTER_RESPAWN = 113,  // S→C: entity(8u64) hp(4i) max_hp(4i) x(4f) y(4f) z(4f) = 28B

        // 존 이동 (세션 16)
        ZONE_TRANSFER_REQ    = 120,  // C→S: target_zone_id(4i32)
        ZONE_TRANSFER_RESULT = 121,  // S→C: result(1) zone_id(4u32) x(4f) y(4f) z(4f) = 17B

        // 게이트 서버 목록 (세션 17)
        FIELD_REGISTER       = 130,  // S2S
        FIELD_HEARTBEAT      = 131,  // S2S
        GATE_SERVER_LIST     = 133,  // C→S: empty
        GATE_SERVER_LIST_RESP = 134, // S→C: count(1) {port(2) ccu(4) max_ccu(4) status(1)}*N

        // 스킬 (세션 19 + 세션 33 확장)
        SKILL_LIST_REQ  = 150,  // C→S: empty
        SKILL_LIST_RESP = 151,  // S→C: count(1) {id(4) name(16) cd_ms(4) dmg(4) mp(4) range(4) type(1) level(1) effect(1) min_level(4)}*N = 43B/entry
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

        // 채팅 (세션 30)
        CHAT_SEND       = 240,  // C→S: channel(1) msg_len(1) message(N)
        CHAT_MESSAGE    = 241,  // S→C: channel(1) sender_entity(8) sender_name(32) msg_len(1) message(N)
        WHISPER_SEND    = 242,  // C→S: target_name_len(1) target_name(N) msg_len(1) message(N)
        WHISPER_RESULT  = 243,  // S→C: result(1) direction(1) other_name(32) msg_len(1) message(N)
        SYSTEM_MESSAGE  = 244,  // S→C: msg_len(1) message(N)

        // NPC 상점 (세션 32)
        SHOP_OPEN       = 250,  // C→S: npc_id(4)
        SHOP_LIST       = 251,  // S→C: npc_id(4) count(1) {item_id(4) price(4) stock(2)}*N = 10B/entry
        SHOP_BUY        = 252,  // C→S: npc_id(4) item_id(4) count(2) = 10B
        SHOP_SELL       = 253,  // C→S: slot(1) count(2) = 3B
        SHOP_RESULT     = 254,  // S→C: result(1) action(1) item_id(4) count(2) gold(4) = 12B

        // 스킬 확장 (세션 33)
        SKILL_LEVEL_UP        = 260,  // C→S: skill_id(4)
        SKILL_LEVEL_UP_RESULT = 261,  // S→C: result(1) skill_id(4) new_level(1) skill_points(4) = 10B
        SKILL_POINT_INFO      = 262,  // S→C: skill_points(4) total_spent(4) = 8B

        // 보스 메카닉 (세션 34)
        BOSS_SPAWN            = 270,  // S→C: entity(8) boss_id(4) name(32) level(4) hp(4) max_hp(4) phase(1) = 57B
        BOSS_PHASE_CHANGE     = 271,  // S→C: entity(8) boss_id(4) new_phase(1) hp(4) max_hp(4) = 21B
        BOSS_SPECIAL_ATTACK   = 272,  // S→C: entity(8) boss_id(4) attack_type(1) damage(4) = 17B
        BOSS_ENRAGE           = 273,  // S→C: entity(8) boss_id(4) = 12B
        BOSS_DEFEATED         = 274,  // S→C: entity(8) boss_id(4) killer_entity(8) = 20B

        // 어드민/핫리로드 (세션 37)
        ADMIN_RELOAD        = 280,  // C→S: name_len(1) name(N) (빈 name=전체 리로드)
        ADMIN_RELOAD_RESULT = 281,  // S→C: result(1) version(4) reload_count(4) name_len(1) name(N)
        ADMIN_GET_CONFIG    = 282,  // C→S: name_len(1) name(N) key_len(1) key(N)
        ADMIN_CONFIG_RESP   = 283,  // S→C: found(1) value_len(2) value(N)

        // 서버 선택 (S033)
        SERVER_LIST_REQ     = 320,  // C→S: empty
        SERVER_LIST         = 321,  // S→C: count(1) {name(32) status(1) population(2)}*N = 35B/entry

        // 캐릭터 CRUD (S033)
        CHARACTER_LIST_REQ     = 322,  // C→S: empty (로그인 필요)
        CHARACTER_LIST         = 323,  // S→C: count(1) {name(16) class(1) level(2) zone_id(4)}*N = 23B/entry
        CHARACTER_CREATE       = 324,  // C→S: name_len(1) name(var) class(1)
        CHARACTER_CREATE_RESULT = 325, // S→C: result(1) char_id(4) = 5B
        CHARACTER_DELETE       = 326,  // C→S: char_id(4)
        CHARACTER_DELETE_RESULT = 327, // S→C: result(1) char_id(4) = 5B

        // 튜토리얼 (S033)
        TUTORIAL_STEP_COMPLETE = 330,  // C→S: step_id(1)
        TUTORIAL_REWARD        = 331,  // S→C: step_id(1) reward_type(1) amount(4) = 6B

        // NPC 인터랙션 (S034)
        NPC_INTERACT    = 332,  // C→S: npc_entity_id(4)
        NPC_DIALOG      = 333,  // S→C: npc_id(2) npc_type(1) line_count(1) {speaker_len(1) speaker(N) text_len(2) text(N)}*N quest_count(1) {quest_id(4)}*N

        // 강화 (S034)
        ENHANCE_REQ     = 340,  // C→S: slot_index(1)
        ENHANCE_RESULT  = 341,  // S→C: slot_index(1) result(1) new_level(1) = 3B

        // 문파 Guild (S029)
        GUILD_CREATE       = 290,  // C→S: name_len(1) name(N) (최대 16B)
        GUILD_DISBAND      = 291,  // C→S: empty (파장만 가능)
        GUILD_INVITE       = 292,  // C→S: target_entity(8u64)
        GUILD_ACCEPT       = 293,  // C→S: empty
        GUILD_LEAVE        = 294,  // C→S: empty (파장은 불가→해산)
        GUILD_KICK         = 295,  // C→S: target_entity(8u64) (파장만 가능)
        GUILD_INFO_REQ     = 296,  // C→S: empty
        GUILD_INFO         = 297,  // S→C: guild_id(4) name(16) leader(8) count(1) {entity(8) rank(1)}*N
        GUILD_LIST_REQ     = 298,  // C→S: empty
        GUILD_LIST         = 299,  // S→C: count(1) {guild_id(4) name(16) member_count(1) leader_name(16)}*N = 37B/entry

        // 거래 Trade (S029)
        TRADE_REQUEST      = 300,  // C→S: target_entity(8u64)
        TRADE_ACCEPT       = 301,  // C→S: empty
        TRADE_DECLINE      = 302,  // C→S: empty
        TRADE_ADD_ITEM     = 303,  // C→S: slot_index(1)
        TRADE_ADD_GOLD     = 304,  // C→S: amount(4u32)
        TRADE_CONFIRM      = 305,  // C→S: empty
        TRADE_CANCEL       = 306,  // C→S: empty
        TRADE_RESULT       = 307,  // S→C: result(1) = 1B

        // 우편 Mail (S029)
        MAIL_SEND          = 310,  // C→S: recipient_len(1) recipient(N) title_len(1) title(N) body_len(2) body(N) gold(4) item_id(4) item_count(2)
        MAIL_LIST_REQ      = 311,  // C→S: empty
        MAIL_LIST          = 312,  // S→C: count(1) {mail_id(4) sender(16) title(32) read(1) has_attachment(1) timestamp(4)}*N = 58B/entry
        MAIL_READ          = 313,  // C→S: mail_id(4)
        MAIL_READ_RESP     = 314,  // S→C: mail_id(4) sender(16) title(32) body_len(2) body(N) gold(4) item_id(4) item_count(2)
        MAIL_CLAIM         = 315,  // C→S: mail_id(4)
        MAIL_CLAIM_RESULT  = 316,  // S→C: result(1) mail_id(4) = 5B
        MAIL_DELETE        = 317,  // C→S: mail_id(4)
        MAIL_DELETE_RESULT = 318,  // S→C: result(1) mail_id(4) = 5B

        // PvP 아레나 (S036)
        PVP_QUEUE_REQ      = 350,  // C→S: mode(1) (1=1v1, 2=3v3)
        PVP_QUEUE_CANCEL   = 351,  // C→S: empty
        PVP_QUEUE_STATUS   = 352,  // S→C: mode_id(1) status(1) queue_count(2)
        PVP_MATCH_FOUND    = 353,  // S→C: match_id(4) mode_id(1) team_id(1)
        PVP_MATCH_ACCEPT   = 354,  // C→S: match_id(4)
        PVP_MATCH_START    = 355,  // S→C: match_id(4) team_id(1) time_limit(2)
        PVP_MATCH_END      = 356,  // S→C: match_id(4) winner_team(1) won(1) new_rating(2) tier(16B)
        PVP_ATTACK         = 357,  // C→S: match_id(4) target_team(1) target_idx(1) skill_id(2) damage(2)
        PVP_ATTACK_RESULT  = 358,  // S→C: match_id(4) attacker_team(1) target_team(1) target_idx(1) damage(2) remaining_hp(4)
        PVP_RATING_INFO    = 359,  // S→C: rating(2) tier(16B) wins(2) losses(2)

        // 레이드 보스 (S036)
        RAID_BOSS_SPAWN    = 370,  // S→C: instance_id(4) boss_name(32) max_hp(4) current_hp(4) phase(1) max_phases(1) enrage_timer(2)
        RAID_PHASE_CHANGE  = 371,  // S→C: instance_id(4) phase(1) max_phases(1)
        RAID_MECHANIC      = 372,  // S→C: instance_id(4) mechanic_id(1) phase(1)
        RAID_MECHANIC_RESULT = 373, // S→C: instance_id(4) mechanic_id(1) success(1)
        RAID_STAGGER       = 374,  // S→C: instance_id(4) stagger_gauge(1)
        RAID_ENRAGE        = 375,  // S→C: instance_id(4)
        RAID_WIPE          = 376,  // S→C: instance_id(4) phase(1)
        RAID_CLEAR         = 377,  // S→C: instance_id(4) gold(4) exp(4) tokens(2)
        RAID_ATTACK        = 378,  // C→S: instance_id(4) skill_id(2) damage(4)
        RAID_ATTACK_RESULT = 379,  // S→C: instance_id(4) skill_id(2) damage(4) current_hp(4) max_hp(4)

        // 제작/채집/요리/인챈트 (S041 TASK 2)
        CRAFT_LIST_REQ     = 380,  // C→S: empty
        CRAFT_LIST         = 381,  // S→C: count(1) {recipe_id(2) name(32) category(1) proficiency(1) material_count(1) success_pct(1) gold(4)}*N
        CRAFT_EXECUTE      = 382,  // C→S: recipe_id(2)
        CRAFT_RESULT       = 383,  // S→C: status(1) recipe_id(2) item_id(4) count(2) bonus(1) = 10B
        GATHER_START       = 384,  // C→S: node_type(1)
        GATHER_RESULT      = 385,  // S→C: status(1) node_type(1) item_id(4) count(2) energy(2) = 10B
        COOK_EXECUTE       = 386,  // C→S: recipe_id(1)
        COOK_RESULT        = 387,  // S→C: status(1) recipe_id(1) buff_type(1) buff_value(2) buff_duration(2) = 7B
        ENCHANT_REQ        = 388,  // C→S: slot(1) element(1) level(1)
        ENCHANT_RESULT     = 389,  // S→C: status(1) slot(1) element(1) level(1) damage_pct(1) = 5B

        // 거래소 (S045 TASK 3)
        AUCTION_LIST_REQ           = 390,  // C→S: category(1) page(1) sort_by(1) = 3B
        AUCTION_LIST               = 391,  // S→C: total_count(2) total_pages(1) page(1) item_count(1) {auction_id(4) item_id(2) count(1) buyout(4) bid(4) seller_name_len(1) seller_name(N)}*N
        AUCTION_REGISTER           = 392,  // C→S: slot_idx(1) count(1) buyout_price(4) category(1) = 7B
        AUCTION_REGISTER_RESULT    = 393,  // S→C: result(1) auction_id(4) = 5B
        AUCTION_BUY                = 394,  // C→S: auction_id(4)
        AUCTION_BUY_RESULT         = 395,  // S→C: result(1) auction_id(4) = 5B
        AUCTION_BID                = 396,  // C→S: auction_id(4) bid_amount(4) = 8B
        AUCTION_BID_RESULT         = 397,  // S→C: result(1) auction_id(4) = 5B

        // 보석 (S041 TASK 8)
        GEM_EQUIP          = 450,  // C→S: item_slot(1) gem_slot(1) gem_item_id(4)
        GEM_EQUIP_RESULT   = 451,  // S→C: status(1) item_slot(1) gem_slot(1) gem_type(1) gem_tier(1) = 5B
        GEM_FUSE           = 452,  // C→S: gem_type(1) gem_tier(1)
        GEM_FUSE_RESULT    = 453,  // S→C: status(1) gem_type(1) new_tier(1) = 3B

        // ━━━ S042: Phase 5 — 캐시샵/배틀패스/이벤트 (TASK 11, MsgType 474-489) ━━━
        CASH_SHOP_LIST_REQ      = 474,  // C→S: category(1)
        CASH_SHOP_LIST          = 475,  // S→C: count(1) {item_id(4) name(32) category(1) price(4) currency(1)}*N = 42B/entry
        CASH_SHOP_BUY           = 476,  // C→S: item_id(4) count(1)
        CASH_SHOP_BUY_RESULT    = 477,  // S→C: result(1) item_id(4) remaining_crystals(4) = 9B
        BATTLEPASS_INFO_REQ     = 478,  // C→S: empty
        BATTLEPASS_INFO         = 479,  // S→C: season_id(2) level(1) exp(2) max_exp(2) is_premium(1) days_left(2) = 10B
        BATTLEPASS_REWARD_CLAIM = 480,  // C→S: level(1) track(1) (0=free, 1=premium)
        BATTLEPASS_REWARD_RESULT = 481, // S→C: result(1) level(1) track(1) reward_type(1) reward_id(4) reward_count(2) = 10B
        BATTLEPASS_BUY_PREMIUM  = 482,  // C→S: empty
        BATTLEPASS_BUY_RESULT   = 483,  // S→C: result(1) remaining_crystals(4) = 5B
        EVENT_LIST_REQ          = 484,  // C→S: empty
        EVENT_LIST              = 485,  // S→C: count(1) {event_id(2) type(1) name(32) remaining_sec(4)}*N = 39B/entry
        EVENT_CLAIM             = 486,  // C→S: event_id(2)
        EVENT_CLAIM_RESULT      = 487,  // S→C: result(1) event_id(2) reward_type(1) reward_id(4) reward_count(2) = 10B
        SUBSCRIPTION_INFO_REQ   = 488,  // C→S: empty
        SUBSCRIPTION_INFO       = 489,  // S→C: is_active(1) days_left(2) daily_crystals(2) = 5B

        // ━━━ S042: Phase 5 — 월드 시스템 (TASK 12, MsgType 490-501) ━━━
        WEATHER_UPDATE          = 490,  // S→C: zone_id(4) weather_type(1) transition_sec(1) = 6B
        TIME_UPDATE             = 491,  // S→C: game_time_sec(4) = 4B (0~3600 게임내 하루)
        TELEPORT_LIST_REQ       = 492,  // C→S: empty
        TELEPORT_LIST           = 493,  // S→C: count(1) {waypoint_id(2) zone_id(4) name(32) x(4f) y(4f) z(4f) cost(4)}*N = 50B/entry
        TELEPORT_REQ            = 494,  // C→S: waypoint_id(2)
        TELEPORT_RESULT         = 495,  // S→C: result(1) zone_id(4) x(4f) y(4f) z(4f) = 17B
        WORLD_OBJECT_INTERACT   = 496,  // C→S: object_id(4) action(1) = 5B
        WORLD_OBJECT_RESULT     = 497,  // S→C: result(1) object_id(4) item_id(4) count(2) gold(4) = 15B
        MOUNT_SUMMON            = 498,  // C→S: mount_id(4)
        MOUNT_RESULT            = 499,  // S→C: result(1) mount_id(4) speed_mult(2) = 7B (speed_mult * 100)
        MOUNT_DISMOUNT          = 500,  // C→S: empty
        MOUNT_DISMOUNT_RESULT   = 501,  // S→C: result(1) = 1B

        // ━━━ S042: Phase 5 — 출석/리셋/컨텐츠 해금 (TASK 13, MsgType 502-509) ━━━
        ATTENDANCE_INFO_REQ     = 502,  // C→S: empty
        ATTENDANCE_INFO         = 503,  // S→C: day(1) total_days(1) {claimed(1)}*14 = 16B
        ATTENDANCE_CLAIM        = 504,  // C→S: day(1)
        ATTENDANCE_CLAIM_RESULT = 505,  // S→C: result(1) day(1) reward_type(1) reward_id(4) reward_count(2) = 9B
        DAILY_RESET_NOTIFY      = 506,  // S→C: reset_type(1) timestamp(4) = 5B (0=daily, 1=weekly)
        CONTENT_UNLOCK_NOTIFY   = 507,  // S→C: unlock_type(1) system_name_len(1) system_name(N) description_len(1) description(N)
        CONTENT_UNLOCK_ACK      = 508,  // C→S: unlock_type(1) (클라 확인 응답)
        LOGIN_REWARD_NOTIFY     = 509,  // S→C: reward_type(1) reward_id(4) reward_count(2) = 7B

        // ━━━ S042: Phase 5 — 스토리/대화 시스템 (TASK 14, MsgType 510-517) ━━━
        DIALOG_CHOICE           = 510,  // C→S: npc_id(2) choice_index(1) = 3B
        DIALOG_CHOICE_RESULT    = 511,  // S→C: npc_id(2) next_line_count(1) {speaker_len(1) speaker(N) text_len(2) text(N)}*N choice_count(1) {text_len(1) text(N)}*N
        CUTSCENE_TRIGGER        = 512,  // S→C: cutscene_id(2) duration_sec(2) = 4B
        CUTSCENE_SKIP           = 513,  // C→S: cutscene_id(2)
        CUTSCENE_END            = 514,  // S→C: cutscene_id(2) = 2B
        STORY_PROGRESS_REQ      = 515,  // C→S: empty
        STORY_PROGRESS          = 516,  // S→C: chapter(1) quest_id(4) quest_state(1) = 6B
        MAIN_QUEST_DATA         = 517,  // S→C: quest_id(4) name(32) desc_len(2) desc(N) objective_count(1) {type(1) target(4) current(4) required(4)}*N

        // ━━━ S046: 비급 & 트라이포드 (TASK 15, MsgType 520-524) ━━━
        TRIPOD_LIST_REQ         = 520,  // C→S: empty
        TRIPOD_LIST             = 521,  // S→C: skill_count(1) {skill_id(2) tier_count(1) {tier(1) unlocked_count(1) {option_idx(1)}*N equipped_idx(1)}*N}*N
        TRIPOD_EQUIP            = 522,  // C→S: skill_id(2) tier(1) option_idx(1) = 4B
        TRIPOD_EQUIP_RESULT     = 523,  // S→C: result(1)
        SCROLL_DISCOVER         = 524,  // C→S: scroll_slot(1) | S→C: result(1) [+ skill_id(2) tier(1) option_idx(1) if success]

        // ━━━ S047: 현상금 시스템 (TASK 16, MsgType 530-537) ━━━
        BOUNTY_LIST_REQ         = 530,  // C→S: empty
        BOUNTY_LIST             = 531,  // S→C: daily_count(1) + [bounty_id(2)+monster_id(2)+level(1)+zone_len(1)+zone(str)+gold(4)+exp(4)+token(1)+accepted(1)+completed(1)] + has_weekly(1) + [weekly data] + accepted_count(1)
        BOUNTY_ACCEPT           = 532,  // C→S: bounty_id(2)
        BOUNTY_ACCEPT_RESULT    = 533,  // S→C: result(1) [+ bounty_id(2)]
        BOUNTY_COMPLETE         = 534,  // C→S: bounty_id(2) | S→C: result(1)+bounty_id(2)+gold(4)+exp(4)+token(1)
        BOUNTY_RANKING_REQ      = 535,  // C→S: empty
        BOUNTY_RANKING          = 536,  // S→C: rank_count(1) + [rank(1)+name_len(1)+name(str)+score(2)] + my_rank(1)+my_score(2)
        PVP_BOUNTY_NOTIFY       = 537,  // S→C: target_entity(8)+tier(1)+kill_streak(2)+gold_reward(4)+name_len(1)+name(str)
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

    /// <summary>스킬 정보 (SKILL_LIST_RESP 파싱용, 세션 33 확장: 43B/entry)</summary>
    public class SkillInfo
    {
        public uint SkillId;
        public string Name;
        public uint CooldownMs;
        public uint Damage;
        public uint ManaCost;
        public uint Range;
        public byte SkillType;
        public byte Level;          // 세션 33: 스킬 레벨 (0~5)
        public SkillEffect Effect;  // 세션 33: 효과 타입
        public int MinLevel;        // 세션 33: 습득 가능 최소 레벨
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

    // ━━━ 세션 30~37 Enums ━━━

    /// <summary>채팅 채널 타입</summary>
    public enum ChatChannel : byte
    {
        GENERAL = 0,    // 존 채팅
        PARTY   = 1,    // 파티 채팅
        WHISPER = 2,    // 귓속말
        SYSTEM  = 3,    // 시스템 메시지
    }

    /// <summary>귓속말 결과 코드</summary>
    public enum WhisperResult : byte
    {
        SUCCESS         = 0,
        TARGET_NOT_FOUND = 1,
        TARGET_OFFLINE  = 2,
    }

    /// <summary>귓속말 방향</summary>
    public enum WhisperDirection : byte
    {
        RECEIVED = 0,   // 수신한 귓속말
        SENT     = 1,   // 보낸 귓속말 에코
    }

    /// <summary>상점 거래 결과 코드</summary>
    public enum ShopResult : byte
    {
        SUCCESS         = 0,
        SHOP_NOT_FOUND  = 1,
        ITEM_NOT_FOUND  = 2,
        NOT_ENOUGH_GOLD = 3,
        INVENTORY_FULL  = 4,
        OUT_OF_STOCK    = 5,
        EMPTY_SLOT      = 6,
        INVALID_COUNT   = 7,
    }

    /// <summary>상점 거래 방향</summary>
    public enum ShopAction : byte
    {
        BUY  = 0,
        SELL = 1,
    }

    /// <summary>스킬 레벨업 결과 코드 (SkillComponents.h 기준)</summary>
    public enum SkillLevelUpResult : byte
    {
        SUCCESS         = 0,
        NO_SKILL_POINTS = 1,
        SKILL_NOT_FOUND = 2,
        MAX_LEVEL       = 3,
        LEVEL_TOO_LOW   = 4,
        SLOTS_FULL      = 5,
    }

    /// <summary>스킬 효과 타입 (세션 33)</summary>
    public enum SkillEffect : byte
    {
        DAMAGE      = 0,
        SELF_HEAL   = 1,
        SELF_BUFF   = 2,
        AOE_DAMAGE  = 3,
        DOT_DAMAGE  = 4,
    }

    /// <summary>보스 특수 공격 타입</summary>
    public enum BossAttackType : byte
    {
        GROUND_SLAM  = 0,
        FIRE_BREATH  = 1,
        TAIL_SWIPE   = 2,
        SUMMON_ADDS  = 3,
        STOMP        = 4,
        DARK_NOVA    = 5,
    }

    // ━━━ 세션 30~37 Data Classes ━━━

    /// <summary>채팅 메시지 데이터 (CHAT_MESSAGE 파싱용)</summary>
    public class ChatMessageData
    {
        public ChatChannel Channel;
        public ulong SenderEntityId;
        public string SenderName;
        public string Message;
    }

    /// <summary>귓속말 결과 데이터 (WHISPER_RESULT 파싱용)</summary>
    public class WhisperResultData
    {
        public WhisperResult Result;
        public WhisperDirection Direction;
        public string OtherName;
        public string Message;
    }

    /// <summary>상점 아이템 항목 (SHOP_LIST 파싱용)</summary>
    public class ShopItemInfo
    {
        public uint ItemId;
        public uint Price;
        public short Stock;     // -1 = 무한
    }

    /// <summary>상점 목록 데이터 (SHOP_LIST 파싱용)</summary>
    public class ShopListData
    {
        public uint NpcId;
        public ShopItemInfo[] Items;
    }

    /// <summary>상점 거래 결과 데이터 (SHOP_RESULT 파싱용)</summary>
    public class ShopResultData
    {
        public ShopResult Result;
        public ShopAction Action;
        public uint ItemId;
        public ushort Count;
        public uint Gold;       // 거래 후 남은 골드
    }

    /// <summary>스킬 레벨업 결과 데이터 (SKILL_LEVEL_UP_RESULT 파싱용)</summary>
    public class SkillLevelUpResultData
    {
        public SkillLevelUpResult Result;
        public uint SkillId;
        public byte NewLevel;
        public uint SkillPoints;
    }

    /// <summary>스킬 포인트 정보 (SKILL_POINT_INFO 파싱용)</summary>
    public class SkillPointInfoData
    {
        public uint SkillPoints;
        public uint TotalSpent;
    }

    /// <summary>보스 스폰 데이터 (BOSS_SPAWN 파싱용)</summary>
    public class BossSpawnData
    {
        public ulong EntityId;
        public uint BossId;
        public string Name;
        public int Level;
        public int HP, MaxHP;
        public byte Phase;
    }

    /// <summary>보스 페이즈 변경 데이터 (BOSS_PHASE_CHANGE 파싱용)</summary>
    public class BossPhaseChangeData
    {
        public ulong EntityId;
        public uint BossId;
        public byte NewPhase;
        public int HP, MaxHP;
    }

    /// <summary>보스 특수 공격 데이터 (BOSS_SPECIAL_ATTACK 파싱용)</summary>
    public class BossSpecialAttackData
    {
        public ulong EntityId;
        public uint BossId;
        public BossAttackType AttackType;
        public int Damage;
    }

    /// <summary>보스 인레이지 데이터 (BOSS_ENRAGE 파싱용)</summary>
    public class BossEnrageData
    {
        public ulong EntityId;
        public uint BossId;
    }

    /// <summary>보스 처치 데이터 (BOSS_DEFEATED 파싱용)</summary>
    public class BossDefeatedData
    {
        public ulong EntityId;
        public uint BossId;
        public ulong KillerEntityId;
    }

    /// <summary>몬스터 이동 데이터 (MONSTER_MOVE 파싱용)</summary>
    public class MonsterMoveData
    {
        public ulong EntityId;
        public float X, Y, Z;
    }

    /// <summary>몬스터 어그로 데이터 (MONSTER_AGGRO 파싱용)</summary>
    public class MonsterAggroData
    {
        public ulong MonsterEntityId;
        public ulong TargetEntityId;    // 0이면 어그로 해제
    }

    /// <summary>어드민 리로드 결과 (ADMIN_RELOAD_RESULT 파싱용)</summary>
    public class AdminReloadResultData
    {
        public byte Result;
        public uint Version;
        public uint ReloadCount;
        public string Name;
    }

    /// <summary>어드민 설정 응답 (ADMIN_CONFIG_RESP 파싱용)</summary>
    public class AdminConfigRespData
    {
        public bool Found;
        public string Value;
    }

    // ━━━ S033: 서버 선택 / 캐릭터 CRUD / 튜토리얼 ━━━

    /// <summary>서버 상태</summary>
    public enum ServerStatus : byte
    {
        OFF    = 0,
        NORMAL = 1,
        BUSY   = 2,
        FULL   = 3,
    }

    /// <summary>서버 정보 (SERVER_LIST 파싱용)</summary>
    public class ServerInfo
    {
        public string Name;
        public ServerStatus Status;
        public ushort Population;
    }

    /// <summary>캐릭터 직업</summary>
    public enum CharacterClass : byte
    {
        WARRIOR = 1,
        MAGE    = 2,
        ARCHER  = 3,
    }

    /// <summary>캐릭터 정보 (CHARACTER_LIST 파싱용)</summary>
    public class CharacterData
    {
        public string Name;
        public CharacterClass ClassType;
        public ushort Level;
        public uint ZoneId;
    }

    /// <summary>캐릭터 생성 결과</summary>
    public enum CharacterCreateResult : byte
    {
        SUCCESS      = 0,
        FAIL         = 1,
        NAME_EXISTS  = 2,
        NAME_INVALID = 3,
    }

    /// <summary>캐릭터 생성 결과 데이터 (CHARACTER_CREATE_RESULT 파싱용)</summary>
    public class CharacterCreateResultData
    {
        public CharacterCreateResult Result;
        public uint CharId;
    }

    /// <summary>캐릭터 삭제 결과</summary>
    public enum CharacterDeleteResult : byte
    {
        SUCCESS       = 0,
        NOT_FOUND     = 1,
        NOT_LOGGED_IN = 2,
    }

    /// <summary>캐릭터 삭제 결과 데이터 (CHARACTER_DELETE_RESULT 파싱용)</summary>
    public class CharacterDeleteResultData
    {
        public CharacterDeleteResult Result;
        public uint CharId;
    }

    /// <summary>튜토리얼 보상 타입</summary>
    public enum TutorialRewardType : byte
    {
        GOLD = 0,
        ITEM = 1,
        EXP  = 2,
    }

    /// <summary>튜토리얼 보상 데이터 (TUTORIAL_REWARD 파싱용)</summary>
    public class TutorialRewardData
    {
        public byte StepId;
        public TutorialRewardType RewardType;
        public uint Amount;
    }

    // ━━━ S034: NPC / 강화 ━━━

    /// <summary>NPC 타입</summary>
    public enum NpcType : byte
    {
        QUEST      = 0,
        SHOP       = 1,
        BLACKSMITH = 2,
        SKILL      = 3,
    }

    /// <summary>NPC 대화 라인</summary>
    public class NpcDialogLine
    {
        public string Speaker;
        public string Text;
    }

    /// <summary>NPC 대화 데이터 (NPC_DIALOG 파싱용)</summary>
    public class NpcDialogData
    {
        public ushort NpcId;
        public NpcType Type;
        public NpcDialogLine[] Lines;
        public uint[] QuestIds;
    }

    /// <summary>강화 결과</summary>
    public enum EnhanceResult : byte
    {
        SUCCESS      = 0,
        INVALID_SLOT = 1,
        NO_ITEM      = 2,
        MAX_LEVEL    = 3,
        NO_GOLD      = 4,
        FAIL         = 5,
    }

    /// <summary>강화 결과 데이터 (ENHANCE_RESULT 파싱용)</summary>
    public class EnhanceResultData
    {
        public byte SlotIndex;
        public EnhanceResult Result;
        public byte NewLevel;
    }

    // ━━━ S029: 문파 / 거래 / 우편 ━━━

    /// <summary>문파 멤버 정보 (GUILD_INFO 파싱용)</summary>
    public class GuildMemberInfo
    {
        public ulong EntityId;
        public byte Rank;       // 0=파장, 1=부파장, 2=일반
    }

    /// <summary>문파 정보 (GUILD_INFO 파싱용)</summary>
    public class GuildInfoData
    {
        public uint GuildId;
        public string Name;
        public ulong LeaderId;
        public GuildMemberInfo[] Members;
    }

    /// <summary>문파 목록 항목 (GUILD_LIST 파싱용)</summary>
    public class GuildListEntry
    {
        public uint GuildId;
        public string Name;
        public byte MemberCount;
        public string LeaderName;
    }

    /// <summary>거래 결과 코드</summary>
    public enum TradeResult : byte
    {
        SUCCESS          = 0,
        TARGET_NOT_FOUND = 1,
        TARGET_BUSY      = 2,
        DECLINED         = 3,
        CANCELLED        = 4,
        INVENTORY_FULL   = 5,
        INVALID_ITEM     = 6,
        NOT_ENOUGH_GOLD  = 7,
    }

    /// <summary>거래 결과 데이터 (TRADE_RESULT 파싱용)</summary>
    public class TradeResultData
    {
        public TradeResult Result;
    }

    /// <summary>우편 목록 항목 (MAIL_LIST 파싱용)</summary>
    public class MailListEntry
    {
        public uint MailId;
        public string Sender;
        public string Title;
        public bool IsRead;
        public bool HasAttachment;
        public uint Timestamp;
    }

    /// <summary>우편 내용 (MAIL_READ_RESP 파싱용)</summary>
    public class MailReadData
    {
        public uint MailId;
        public string Sender;
        public string Title;
        public string Body;
        public uint Gold;
        public uint ItemId;
        public ushort ItemCount;
    }

    /// <summary>우편 수령 결과</summary>
    public enum MailClaimResult : byte
    {
        SUCCESS            = 0,
        MAIL_NOT_FOUND     = 1,
        ALREADY_CLAIMED    = 2,
        INVENTORY_FULL     = 3,
    }

    /// <summary>우편 수령 결과 데이터 (MAIL_CLAIM_RESULT 파싱용)</summary>
    public class MailClaimResultData
    {
        public MailClaimResult Result;
        public uint MailId;
    }

    /// <summary>우편 삭제 결과</summary>
    public enum MailDeleteResult : byte
    {
        SUCCESS           = 0,
        MAIL_NOT_FOUND    = 1,
        HAS_UNCLAIMED     = 2,
    }

    /// <summary>우편 삭제 결과 데이터 (MAIL_DELETE_RESULT 파싱용)</summary>
    public class MailDeleteResultData
    {
        public MailDeleteResult Result;
        public uint MailId;
    }

    // ━━━ S036: PvP 아레나 ━━━

    /// <summary>PvP 큐 상태 코드</summary>
    public enum PvPQueueStatus : byte
    {
        QUEUED        = 0,
        INVALID_MODE  = 1,
        LEVEL_TOO_LOW = 2,
        ALREADY_QUEUED = 3,
        CANCELLED     = 4,
    }

    /// <summary>PvP 큐 상태 데이터 (PVP_QUEUE_STATUS 파싱용)</summary>
    public class PvPQueueStatusData
    {
        public byte ModeId;
        public PvPQueueStatus Status;
        public ushort QueueCount;
    }

    /// <summary>PvP 매치 발견 데이터 (PVP_MATCH_FOUND 파싱용)</summary>
    public class PvPMatchFoundData
    {
        public uint MatchId;
        public byte ModeId;
        public byte TeamId;
    }

    /// <summary>PvP 매치 시작 데이터 (PVP_MATCH_START 파싱용)</summary>
    public class PvPMatchStartData
    {
        public uint MatchId;
        public byte TeamId;
        public ushort TimeLimit;
    }

    /// <summary>PvP 공격 결과 데이터 (PVP_ATTACK_RESULT 파싱용)</summary>
    public class PvPAttackResultData
    {
        public uint MatchId;
        public byte AttackerTeam;
        public byte TargetTeam;
        public byte TargetIdx;
        public ushort Damage;
        public uint RemainingHP;
    }

    /// <summary>PvP 매치 종료 데이터 (PVP_MATCH_END 파싱용)</summary>
    public class PvPMatchEndData
    {
        public uint MatchId;
        public byte WinnerTeam;
        public byte Won;
        public ushort NewRating;
        public string Tier;
    }

    /// <summary>PvP 레이팅 정보 (PVP_RATING_INFO 파싱용)</summary>
    public class PvPRatingInfoData
    {
        public ushort Rating;
        public string Tier;
        public ushort Wins;
        public ushort Losses;
    }

    // ━━━ S036: 레이드 보스 ━━━

    /// <summary>레이드 기믹 ID</summary>
    public enum RaidMechanicId : byte
    {
        SAFE_ZONE      = 1,
        STAGGER_CHECK  = 2,
        COUNTER_ATTACK = 3,
        POSITION_SWAP  = 4,
        DPS_CHECK      = 5,
        COOPERATION    = 6,
    }

    /// <summary>레이드 보스 스폰 데이터 (RAID_BOSS_SPAWN 파싱용)</summary>
    public class RaidBossSpawnData
    {
        public uint InstanceId;
        public string BossName;
        public uint MaxHP;
        public uint CurrentHP;
        public byte Phase;
        public byte MaxPhases;
        public ushort EnrageTimer;
    }

    /// <summary>레이드 페이즈 변경 데이터 (RAID_PHASE_CHANGE 파싱용)</summary>
    public class RaidPhaseChangeData
    {
        public uint InstanceId;
        public byte Phase;
        public byte MaxPhases;
    }

    /// <summary>레이드 기믹 데이터 (RAID_MECHANIC 파싱용)</summary>
    public class RaidMechanicData
    {
        public uint InstanceId;
        public RaidMechanicId MechanicId;
        public byte Phase;
    }

    /// <summary>레이드 기믹 결과 (RAID_MECHANIC_RESULT 파싱용)</summary>
    public class RaidMechanicResultData
    {
        public uint InstanceId;
        public RaidMechanicId MechanicId;
        public bool Success;
    }

    /// <summary>레이드 스태거 데이터 (RAID_STAGGER 파싱용)</summary>
    public class RaidStaggerData
    {
        public uint InstanceId;
        public byte StaggerGauge;
    }

    /// <summary>레이드 공격 결과 (RAID_ATTACK_RESULT 파싱용)</summary>
    public class RaidAttackResultData
    {
        public uint InstanceId;
        public ushort SkillId;
        public uint Damage;
        public uint CurrentHP;
        public uint MaxHP;
    }

    /// <summary>레이드 클리어 데이터 (RAID_CLEAR 파싱용)</summary>
    public class RaidClearData
    {
        public uint InstanceId;
        public uint Gold;
        public uint Exp;
        public ushort Tokens;
    }

    /// <summary>레이드 와이프 데이터 (RAID_WIPE 파싱용)</summary>
    public class RaidWipeData
    {
        public uint InstanceId;
        public byte Phase;
    }

    // ━━━ S045: 거래소 ━━━

    /// <summary>거래소 카테고리</summary>
    public enum AuctionCategory : byte
    {
        ALL      = 0xFF,
        WEAPON   = 0,
        ARMOR    = 1,
        POTION   = 2,
        GEM      = 3,
        MATERIAL = 4,
        OTHER    = 5,
    }

    /// <summary>거래소 정렬 기준</summary>
    public enum AuctionSortBy : byte
    {
        PRICE_ASC  = 0,
        PRICE_DESC = 1,
        NEWEST     = 2,
    }

    /// <summary>거래소 등록 결과 코드</summary>
    public enum AuctionRegisterResult : byte
    {
        SUCCESS       = 0,
        NOT_IN_GAME   = 1,
        NO_ITEM       = 2,
        MAX_LISTINGS  = 3,
        NO_GOLD       = 4,
        INVALID_PRICE = 5,
    }

    /// <summary>거래소 구매 결과 코드</summary>
    public enum AuctionBuyResult : byte
    {
        SUCCESS    = 0,
        NOT_FOUND  = 1,
        SELF_BUY   = 2,
        NO_GOLD    = 3,
    }

    /// <summary>거래소 입찰 결과 코드</summary>
    public enum AuctionBidResult : byte
    {
        SUCCESS      = 0,
        NOT_FOUND    = 1,
        SELF_BID     = 2,
        NO_GOLD      = 3,
        BID_TOO_LOW  = 4,
    }

    /// <summary>거래소 목록 항목 (AUCTION_LIST 파싱용)</summary>
    public class AuctionListingInfo
    {
        public uint AuctionId;
        public ushort ItemId;
        public byte Count;
        public uint BuyoutPrice;
        public uint CurrentBid;
        public string SellerName;
    }

    /// <summary>거래소 목록 데이터 (AUCTION_LIST 파싱용)</summary>
    public class AuctionListData
    {
        public ushort TotalCount;
        public byte TotalPages;
        public byte CurrentPage;
        public AuctionListingInfo[] Items;
    }

    /// <summary>거래소 등록 결과 (AUCTION_REGISTER_RESULT 파싱용)</summary>
    public class AuctionRegisterResultData
    {
        public AuctionRegisterResult Result;
        public uint AuctionId;
    }

    /// <summary>거래소 구매 결과 (AUCTION_BUY_RESULT 파싱용)</summary>
    public class AuctionBuyResultData
    {
        public AuctionBuyResult Result;
        public uint AuctionId;
    }

    /// <summary>거래소 입찰 결과 (AUCTION_BID_RESULT 파싱용)</summary>
    public class AuctionBidResultData
    {
        public AuctionBidResult Result;
        public uint AuctionId;
    }

    // ━━━ S041: 제작/채집/요리/인챈트/보석 ━━━

    /// <summary>제작 카테고리</summary>
    public enum CraftCategory : byte
    {
        WEAPON   = 1,
        ARMOR    = 2,
        POTION   = 3,
        GEM      = 4,
        MATERIAL = 5,
    }

    /// <summary>제작 결과 코드</summary>
    public enum CraftResult : byte
    {
        SUCCESS           = 0,
        RECIPE_NOT_FOUND  = 1,
        LOW_PROFICIENCY   = 2,
        NO_MATERIALS      = 3,
        NO_GOLD           = 4,
        CRAFT_FAILED      = 5,
    }

    /// <summary>레시피 정보 (CRAFT_LIST 파싱용)</summary>
    public class CraftRecipeInfo
    {
        public ushort RecipeId;
        public string Name;
        public CraftCategory Category;
        public byte Proficiency;
        public byte MaterialCount;
        public byte SuccessPct;
        public uint Gold;
    }

    /// <summary>제작 결과 데이터 (CRAFT_RESULT 파싱용)</summary>
    public class CraftResultData
    {
        public CraftResult Status;
        public ushort RecipeId;
        public uint ItemId;
        public ushort Count;
        public byte Bonus;
    }

    /// <summary>채집 결과 코드</summary>
    public enum GatherResult : byte
    {
        SUCCESS        = 0,
        NODE_NOT_FOUND = 1,
        NO_ENERGY      = 2,
        NO_LOOT        = 3,
    }

    /// <summary>채집 결과 데이터 (GATHER_RESULT 파싱용)</summary>
    public class GatherResultData
    {
        public GatherResult Status;
        public byte NodeType;
        public uint ItemId;
        public ushort Count;
        public ushort Energy;
    }

    /// <summary>요리 결과 코드</summary>
    public enum CookResult : byte
    {
        SUCCESS       = 0,
        RECIPE_FAIL   = 1,
        NO_MATERIALS  = 2,
        BUFF_ACTIVE   = 3,
    }

    /// <summary>요리 버프 타입</summary>
    public enum CookBuffType : byte
    {
        ATK  = 1,
        HP   = 2,
        ALL  = 3,
    }

    /// <summary>요리 결과 데이터 (COOK_RESULT 파싱용)</summary>
    public class CookResultData
    {
        public CookResult Status;
        public byte RecipeId;
        public CookBuffType BuffType;
        public ushort BuffValue;
        public ushort BuffDuration;
    }

    /// <summary>인챈트 결과 코드</summary>
    public enum EnchantResult : byte
    {
        SUCCESS        = 0,
        INVALID_ELEMENT = 1,
        INVALID_LEVEL  = 2,
        NO_MATERIALS   = 3,
        NO_GOLD        = 4,
        INVALID_SLOT   = 5,
    }

    /// <summary>인챈트 결과 데이터 (ENCHANT_RESULT 파싱용)</summary>
    public class EnchantResultData
    {
        public EnchantResult Status;
        public byte Slot;
        public byte Element;
        public byte Level;
        public byte DamagePct;
    }

    /// <summary>보석 결과 코드</summary>
    public enum GemResult : byte
    {
        SUCCESS         = 0,
        INVALID_SLOT    = 1,
        INVALID_GEM     = 2,
        NO_GEMS         = 3,
        NO_GOLD         = 4,
        MAX_TIER        = 5,
    }

    /// <summary>보석 장착 결과 (GEM_EQUIP_RESULT 파싱용)</summary>
    public class GemEquipResultData
    {
        public GemResult Status;
        public byte ItemSlot;
        public byte GemSlot;
        public byte GemType;
        public byte GemTier;
    }

    /// <summary>보석 합성 결과 (GEM_FUSE_RESULT 파싱용)</summary>
    public class GemFuseResultData
    {
        public GemResult Status;
        public byte GemType;
        public byte NewTier;
    }

    // ━━━ S042: Phase 5 — 캐시샵/배틀패스/이벤트 (TASK 11) ━━━

    /// <summary>캐시샵 카테고리</summary>
    public enum CashShopCategory : byte
    {
        ALL         = 0,
        COSMETIC    = 1,
        CONVENIENCE = 2,
        MOUNT       = 3,
        PET         = 4,
        EMOTE       = 5,
    }

    /// <summary>캐시샵 화폐 타입</summary>
    public enum CashCurrency : byte
    {
        CRYSTAL = 0,
        GOLD    = 1,
    }

    /// <summary>캐시샵 구매 결과 코드</summary>
    public enum CashShopBuyResult : byte
    {
        SUCCESS          = 0,
        ITEM_NOT_FOUND   = 1,
        NOT_ENOUGH_CRYSTAL = 2,
        INVENTORY_FULL   = 3,
        PURCHASE_LIMIT   = 4,
    }

    /// <summary>캐시샵 아이템 정보 (CASH_SHOP_LIST 파싱용)</summary>
    public class CashShopItemInfo
    {
        public uint ItemId;
        public string Name;
        public CashShopCategory Category;
        public uint Price;
        public CashCurrency Currency;
    }

    /// <summary>캐시샵 구매 결과 (CASH_SHOP_BUY_RESULT 파싱용)</summary>
    public class CashShopBuyResultData
    {
        public CashShopBuyResult Result;
        public uint ItemId;
        public uint RemainingCrystals;
    }

    /// <summary>배틀패스 보상 트랙</summary>
    public enum BattlePassTrack : byte
    {
        FREE    = 0,
        PREMIUM = 1,
    }

    /// <summary>배틀패스 보상 결과 코드</summary>
    public enum BattlePassRewardResult : byte
    {
        SUCCESS          = 0,
        ALREADY_CLAIMED  = 1,
        LEVEL_NOT_REACHED = 2,
        NOT_PREMIUM      = 3,
        INVENTORY_FULL   = 4,
    }

    /// <summary>배틀패스 정보 (BATTLEPASS_INFO 파싱용)</summary>
    public class BattlePassInfoData
    {
        public ushort SeasonId;
        public byte Level;
        public ushort Exp;
        public ushort MaxExp;
        public bool IsPremium;
        public ushort DaysLeft;
    }

    /// <summary>배틀패스 보상 결과 (BATTLEPASS_REWARD_RESULT 파싱용)</summary>
    public class BattlePassRewardResultData
    {
        public BattlePassRewardResult Result;
        public byte Level;
        public BattlePassTrack Track;
        public byte RewardType;
        public uint RewardId;
        public ushort RewardCount;
    }

    /// <summary>배틀패스 구매 결과 (BATTLEPASS_BUY_RESULT 파싱용)</summary>
    public class BattlePassBuyResultData
    {
        public byte Result;
        public uint RemainingCrystals;
    }

    /// <summary>이벤트 타입</summary>
    public enum GameEventType : byte
    {
        LOGIN_EVENT     = 0,
        DOUBLE_EXP      = 1,
        BOSS_RUSH       = 2,
        SEASONAL        = 3,
    }

    /// <summary>이벤트 정보 (EVENT_LIST 파싱용)</summary>
    public class GameEventInfo
    {
        public ushort EventId;
        public GameEventType Type;
        public string Name;
        public uint RemainingSeconds;
    }

    /// <summary>이벤트 보상 결과 (EVENT_CLAIM_RESULT 파싱용)</summary>
    public class EventClaimResultData
    {
        public byte Result;
        public ushort EventId;
        public byte RewardType;
        public uint RewardId;
        public ushort RewardCount;
    }

    /// <summary>월정액 정보 (SUBSCRIPTION_INFO 파싱용)</summary>
    public class SubscriptionInfoData
    {
        public bool IsActive;
        public ushort DaysLeft;
        public ushort DailyCrystals;
    }

    // ━━━ S042: Phase 5 — 월드 시스템 (TASK 12) ━━━

    /// <summary>날씨 타입</summary>
    public enum WeatherType : byte
    {
        CLEAR     = 0,
        RAIN      = 1,
        SNOW      = 2,
        FOG       = 3,
        STORM     = 4,
        SANDSTORM = 5,
    }

    /// <summary>날씨 업데이트 데이터 (WEATHER_UPDATE 파싱용)</summary>
    public class WeatherUpdateData
    {
        public uint ZoneId;
        public WeatherType Weather;
        public byte TransitionSeconds;
    }

    /// <summary>텔레포트 결과 코드</summary>
    public enum TeleportResult : byte
    {
        SUCCESS            = 0,
        WAYPOINT_NOT_FOUND = 1,
        NOT_ENOUGH_GOLD    = 2,
        IN_COMBAT          = 3,
        COOLDOWN           = 4,
    }

    /// <summary>워프포인트 정보 (TELEPORT_LIST 파싱용)</summary>
    public class WaypointInfo
    {
        public ushort WaypointId;
        public uint ZoneId;
        public string Name;
        public float X, Y, Z;
        public uint Cost;
    }

    /// <summary>텔레포트 결과 (TELEPORT_RESULT 파싱용)</summary>
    public class TeleportResultData
    {
        public TeleportResult Result;
        public uint ZoneId;
        public float X, Y, Z;
    }

    /// <summary>월드 오브젝트 액션</summary>
    public enum WorldObjectAction : byte
    {
        INTERACT  = 0,
        DESTROY   = 1,
        OPEN      = 2,
    }

    /// <summary>월드 오브젝트 상호작용 결과 (WORLD_OBJECT_RESULT 파싱용)</summary>
    public class WorldObjectResultData
    {
        public byte Result;
        public uint ObjectId;
        public uint ItemId;
        public ushort Count;
        public uint Gold;
    }

    /// <summary>탈것 소환 결과 코드</summary>
    public enum MountResult : byte
    {
        SUCCESS        = 0,
        MOUNT_NOT_FOUND = 1,
        IN_COMBAT      = 2,
        ALREADY_MOUNTED = 3,
        LEVEL_TOO_LOW  = 4,
        CAST_INTERRUPTED = 5,
    }

    /// <summary>탈것 소환 결과 (MOUNT_RESULT 파싱용)</summary>
    public class MountResultData
    {
        public MountResult Result;
        public uint MountId;
        public ushort SpeedMultiplied;   // speed * 100 (예: 200 = 2.0x)
    }

    // ━━━ S042: Phase 5 — 출석/리셋/컨텐츠 해금 (TASK 13) ━━━

    /// <summary>출석 보상 결과 코드</summary>
    public enum AttendanceClaimResult : byte
    {
        SUCCESS          = 0,
        ALREADY_CLAIMED  = 1,
        DAY_NOT_REACHED  = 2,
        INVENTORY_FULL   = 3,
    }

    /// <summary>출석 정보 (ATTENDANCE_INFO 파싱용)</summary>
    public class AttendanceInfoData
    {
        public byte CurrentDay;
        public byte TotalDays;
        public bool[] Claimed;     // 14일 기준
    }

    /// <summary>출석 보상 결과 (ATTENDANCE_CLAIM_RESULT 파싱용)</summary>
    public class AttendanceClaimResultData
    {
        public AttendanceClaimResult Result;
        public byte Day;
        public byte RewardType;
        public uint RewardId;
        public ushort RewardCount;
    }

    /// <summary>리셋 타입</summary>
    public enum ResetType : byte
    {
        DAILY  = 0,
        WEEKLY = 1,
    }

    /// <summary>일일/주간 리셋 알림 (DAILY_RESET_NOTIFY 파싱용)</summary>
    public class DailyResetNotifyData
    {
        public ResetType Type;
        public uint Timestamp;
    }

    /// <summary>컨텐츠 해금 알림 (CONTENT_UNLOCK_NOTIFY 파싱용)</summary>
    public class ContentUnlockNotifyData
    {
        public byte UnlockType;
        public string SystemName;
        public string Description;
    }

    /// <summary>로그인 보상 알림 (LOGIN_REWARD_NOTIFY 파싱용)</summary>
    public class LoginRewardNotifyData
    {
        public byte RewardType;
        public uint RewardId;
        public ushort RewardCount;
    }

    // ━━━ S042: Phase 5 — 스토리/대화 시스템 (TASK 14) ━━━

    /// <summary>대화 선택지 (DIALOG_CHOICE_RESULT 파싱용)</summary>
    public class DialogChoiceResultData
    {
        public ushort NpcId;
        public NpcDialogLine[] Lines;
        public string[] Choices;
    }

    /// <summary>컷씬 트리거 데이터 (CUTSCENE_TRIGGER 파싱용)</summary>
    public class CutsceneTriggerData
    {
        public ushort CutsceneId;
        public ushort DurationSeconds;
    }

    /// <summary>스토리 진행 데이터 (STORY_PROGRESS 파싱용)</summary>
    public class StoryProgressData
    {
        public byte Chapter;
        public uint QuestId;
        public QuestState QuestState;
    }

    /// <summary>메인 퀘스트 목표 타입</summary>
    public enum MainQuestObjectiveType : byte
    {
        KILL     = 0,
        COLLECT  = 1,
        TALK     = 2,
        EXPLORE  = 3,
        DUNGEON  = 4,
    }

    /// <summary>메인 퀘스트 목표 항목</summary>
    public class MainQuestObjective
    {
        public MainQuestObjectiveType Type;
        public uint Target;
        public uint Current;
        public uint Required;
    }

    /// <summary>메인 퀘스트 데이터 (MAIN_QUEST_DATA 파싱용)</summary>
    public class MainQuestDataInfo
    {
        public uint QuestId;
        public string Name;
        public string Description;
        public MainQuestObjective[] Objectives;
    }

    // ━━━ S046: 비급 & 트라이포드 (TASK 15) ━━━

    /// <summary>트라이포드 장착 결과 코드</summary>
    public enum TripodEquipResult : byte
    {
        SUCCESS          = 0,
        NOT_LOGGED_IN    = 1,
        INVALID_SKILL    = 2,
        TIER_LEVEL_LOW   = 3,
        NOT_UNLOCKED     = 4,
        LOWER_TIER_REQUIRED = 5,
    }

    /// <summary>비급 발견 결과 코드</summary>
    public enum ScrollDiscoverResult : byte
    {
        SUCCESS          = 0,
        NOT_LOGGED_IN    = 1,
        ITEM_NOT_FOUND   = 2,
        ALREADY_UNLOCKED = 3,
        CLASS_MISMATCH   = 4,
    }

    /// <summary>트라이포드 티어 정보 (TRIPOD_LIST 파싱용)</summary>
    public class TripodTierInfo
    {
        public byte Tier;
        public byte[] UnlockedOptions;
        public byte EquippedIdx;    // 0xFF = 미장착
    }

    /// <summary>스킬별 트라이포드 정보 (TRIPOD_LIST 파싱용)</summary>
    public class TripodSkillInfo
    {
        public ushort SkillId;
        public TripodTierInfo[] Tiers;
    }

    /// <summary>트라이포드 목록 데이터 (TRIPOD_LIST 파싱용)</summary>
    public class TripodListData
    {
        public TripodSkillInfo[] Skills;
    }

    /// <summary>비급 발견 결과 데이터 (SCROLL_DISCOVER RESP 파싱용)</summary>
    public class ScrollDiscoverResultData
    {
        public ScrollDiscoverResult Result;
        public ushort SkillId;
        public byte Tier;
        public byte OptionIdx;
    }

    // ━━━ S047: 현상금 시스템 데이터 ━━━

    /// <summary>현상금 수락 결과 코드</summary>
    public enum BountyAcceptResult : byte
    {
        SUCCESS           = 0,
        ALREADY_ACCEPTED  = 1,
        MAX_LIMIT         = 2,
        ALREADY_COMPLETED = 3,
        LEVEL_TOO_LOW     = 4,
        NOT_FOUND         = 5,
    }

    /// <summary>현상금 완료 결과 코드</summary>
    public enum BountyCompleteResult : byte
    {
        SUCCESS           = 0,
        NOT_ACCEPTED      = 1,
        ALREADY_COMPLETED = 2,
    }

    /// <summary>현상금 정보 (BOUNTY_LIST 파싱용)</summary>
    public class BountyInfo
    {
        public ushort BountyId;
        public ushort MonsterId;
        public byte Level;
        public string Zone;
        public uint Gold;
        public uint Exp;
        public byte Token;
        public byte Accepted;   // 0=미수락, 1=수락
        public byte Completed;  // 0=미완료, 1=완료
    }

    /// <summary>현상금 목록 데이터 (BOUNTY_LIST 파싱용)</summary>
    public class BountyListData
    {
        public BountyInfo[] DailyBounties;
        public bool HasWeekly;
        public BountyInfo WeeklyBounty;
        public byte AcceptedCount;
    }

    /// <summary>현상금 수락 결과 데이터</summary>
    public class BountyAcceptResultData
    {
        public BountyAcceptResult Result;
        public ushort BountyId;
    }

    /// <summary>현상금 완료 결과 데이터</summary>
    public class BountyCompleteData
    {
        public BountyCompleteResult Result;
        public ushort BountyId;
        public uint Gold;
        public uint Exp;
        public byte Token;
    }

    /// <summary>현상금 랭킹 항목</summary>
    public class BountyRankEntry
    {
        public byte Rank;
        public string Name;
        public ushort Score;
    }

    /// <summary>현상금 랭킹 데이터 (BOUNTY_RANKING 파싱용)</summary>
    public class BountyRankingData
    {
        public BountyRankEntry[] Rankings;
        public byte MyRank;
        public ushort MyScore;
    }

    /// <summary>PvP 현상금 알림 데이터 (PVP_BOUNTY_NOTIFY 파싱용)</summary>
    public class PvPBountyNotifyData
    {
        public ulong TargetEntity;
        public byte Tier;
        public ushort KillStreak;
        public uint GoldReward;
        public string Name;
    }
}
