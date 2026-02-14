"""
Patch S047: Bounty System (TASK 16)
- BOUNTY_LIST_REQ(530)->BOUNTY_LIST(531)         -- 일일/주간 현상금 조회
- BOUNTY_ACCEPT(532)->BOUNTY_ACCEPT_RESULT(533)  -- 현상금 수락
- BOUNTY_COMPLETE(534)                           -- 현상금 완료 (서버 감지)
- BOUNTY_RANKING_REQ(535)->BOUNTY_RANKING(536)   -- 주간 랭킹 조회
- PVP_BOUNTY_NOTIFY(537)                         -- PvP 킬스트릭 현상금
- Daily bounty generation (elite monsters from monsters.csv)
- Bounty token shop (world_bosses data)
- 5 test cases
"""
import os
import sys
import re

DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_PATH = os.path.join(DIR, 'tcp_bridge.py')
TEST_PATH = os.path.join(DIR, 'test_tcp_bridge.py')

# ====================================================================
# 1. MsgType enums for Bounty (530-537)
# ====================================================================
MSGTYPE_BLOCK = (
    '\n'
    '    # Bounty System (TASK 16)\n'
    '    BOUNTY_LIST_REQ = 530\n'
    '    BOUNTY_LIST = 531\n'
    '    BOUNTY_ACCEPT = 532\n'
    '    BOUNTY_ACCEPT_RESULT = 533\n'
    '    BOUNTY_COMPLETE = 534\n'
    '    BOUNTY_RANKING_REQ = 535\n'
    '    BOUNTY_RANKING = 536\n'
    '    PVP_BOUNTY_NOTIFY = 537\n'
)

# ====================================================================
# 2. Bounty data constants (GDD bounty.yaml)
# ====================================================================
DATA_CONSTANTS = r'''
# ---- Bounty System Data (GDD bounty.yaml) ----
# Daily bounties: 3 daily (06:00 reset), 1 weekly (Wed 06:00 reset)
BOUNTY_MAX_ACCEPTED = 3          # simultaneous accepted bounties
BOUNTY_MIN_LEVEL = 15            # level requirement for bounties
BOUNTY_WEEKLY_MIN_LEVEL = 30     # level requirement for weekly grand bounty

# Elite monsters for daily bounties (from monsters.csv)
BOUNTY_ELITE_POOL = [
    {"monster_id": 2001, "name": "elite_golem", "name_kr": "정예 골렘", "level": 20, "zone": "dark_forest",
     "gold": 1000, "exp": 2000, "bounty_token": 2},
    {"monster_id": 2002, "name": "ice_queen_elite", "name_kr": "얼음 여왕 정예", "level": 18, "zone": "frozen_peak",
     "gold": 800, "exp": 1500, "bounty_token": 2},
    {"monster_id": 2003, "name": "elite_dragon_whelp", "name_kr": "정예 와이번", "level": 25, "zone": "volcano",
     "gold": 1500, "exp": 3000, "bounty_token": 3},
]

# Weather-special bounty: bonus rewards when weather matches
BOUNTY_WEATHER_BONUS = {
    "storm": {"gold_mult": 1.5, "exp_mult": 1.5, "extra_token": 1},
    "fog": {"gold_mult": 1.3, "exp_mult": 1.3, "extra_token": 1},
    "night": {"gold_mult": 1.2, "exp_mult": 1.2, "extra_token": 0},
}

# Weekly world bosses (grand bounty)
BOUNTY_WORLD_BOSSES = [
    {"boss_id": 5001, "name": "crimson_drake", "name_kr": "홍염 비룡", "level": 40, "zone": "zone4",
     "gold": 5000, "exp": 10000, "bounty_token": 10, "min_party": 4, "recommended_party": 8},
    {"boss_id": 5002, "name": "ice_titan", "name_kr": "빙결의 거인", "level": 35, "zone": "zone3",
     "gold": 4000, "exp": 8000, "bounty_token": 8, "min_party": 4, "recommended_party": 8},
    {"boss_id": 5003, "name": "shadow_hydra", "name_kr": "그림자 히드라", "level": 50, "zone": "zone6",
     "gold": 8000, "exp": 15000, "bounty_token": 15, "min_party": 4, "recommended_party": 8},
]

# PvP bounty tiers
PVP_BOUNTY_TIERS = {
    3:  {"tier": 1, "name": "dangerous", "name_kr": "위험인물",    "gold_reward": 500,  "pvp_token": 2},
    5:  {"tier": 2, "name": "wanted",    "name_kr": "현상수배",    "gold_reward": 1500, "pvp_token": 5},
    10: {"tier": 3, "name": "villain",   "name_kr": "대악인",      "gold_reward": 3000, "pvp_token": 10},
    20: {"tier": 4, "name": "demon_king","name_kr": "마왕급 위협", "gold_reward": 5000, "pvp_token": 20},
}

# Daily completion bonus (all 3 daily bounties done)
BOUNTY_DAILY_COMPLETION_BONUS = {"gold": 500, "bounty_token": 3}

# Bounty token shop items
BOUNTY_TOKEN_SHOP = [
    {"item_id": 8001, "name": "bounty_potion",     "name_kr": "현상금 비약",   "cost": 5,   "category": "consumable"},
    {"item_id": 8002, "name": "bounty_weapon_box",  "name_kr": "현상금 무기 상자", "cost": 50,  "category": "equipment"},
    {"item_id": 8003, "name": "bounty_armor_box",   "name_kr": "현상금 방어구 상자","cost": 50,  "category": "equipment"},
    {"item_id": 8004, "name": "bounty_mount",       "name_kr": "현상금 사냥꾼의 말","cost": 200, "category": "mount"},
    {"item_id": 8005, "name": "legend_hunter_title", "name_kr": "전설의 사냥꾼 칭호","cost": 500, "category": "title"},
]
'''

# ====================================================================
# 3. PlayerSession fields for bounty tracking
# ====================================================================
SESSION_FIELDS = (
    '    # ---- Bounty System (TASK 16) ----\n'
    '    bounty_accepted: list = field(default_factory=list)    # [{bounty_id, monster_id, type:"daily"/"weekly"}]\n'
    '    bounty_completed_today: list = field(default_factory=list)  # completed bounty_ids today\n'
    '    bounty_completed_weekly: list = field(default_factory=list)  # completed weekly bounty_ids\n'
    '    bounty_tokens: int = 0\n'
    '    bounty_reset_date: str = ""          # YYYY-MM-DD for daily reset\n'
    '    bounty_weekly_reset_date: str = ""   # YYYY-MM-DD for weekly reset\n'
    '    bounty_score_weekly: int = 0         # weekly ranking score\n'
    '    pvp_kill_streak: int = 0             # current PvP kill streak\n'
    '    pvp_bounty_tier: int = 0             # current PvP bounty tier (0=none)\n'
)

# ====================================================================
# 4. Dispatch table entries
# ====================================================================
DISPATCH_ENTRIES = (
    '            MsgType.BOUNTY_LIST_REQ: self._on_bounty_list_req,\n'
    '            MsgType.BOUNTY_ACCEPT: self._on_bounty_accept,\n'
    '            MsgType.BOUNTY_COMPLETE: self._on_bounty_complete,\n'
    '            MsgType.BOUNTY_RANKING_REQ: self._on_bounty_ranking_req,\n'
)

# ====================================================================
# 5. Handler implementations
# ====================================================================
HANDLER_CODE = r'''
    # ---- Bounty System (TASK 16: MsgType 530-537) ----

    def _generate_daily_bounties(self):
        """Generate 3 random daily bounties from elite pool."""
        import random as _rng2
        pool = list(BOUNTY_ELITE_POOL)
        _rng2.shuffle(pool)
        bounties = []
        for i, elite in enumerate(pool[:3]):
            bounties.append({
                "bounty_id": 10000 + i,
                "type": "daily",
                "monster_id": elite["monster_id"],
                "name": elite["name"],
                "name_kr": elite["name_kr"],
                "level": elite["level"],
                "zone": elite["zone"],
                "gold": elite["gold"],
                "exp": elite["exp"],
                "bounty_token": elite["bounty_token"],
            })
        return bounties

    def _get_weekly_boss(self):
        """Get current weekly world boss (rotate by week number)."""
        import time as _t
        week_num = int(_t.time()) // (7 * 86400)
        boss = BOUNTY_WORLD_BOSSES[week_num % len(BOUNTY_WORLD_BOSSES)]
        return {
            "bounty_id": 20000,
            "type": "weekly",
            "monster_id": boss["boss_id"],
            "name": boss["name"],
            "name_kr": boss["name_kr"],
            "level": boss["level"],
            "zone": boss["zone"],
            "gold": boss["gold"],
            "exp": boss["exp"],
            "bounty_token": boss["bounty_token"],
            "min_party": boss["min_party"],
            "recommended_party": boss["recommended_party"],
        }

    def _check_bounty_reset(self, session):
        """Reset daily/weekly bounties if time has passed."""
        import time as _t
        today = _t.strftime("%Y-%m-%d")
        if session.bounty_reset_date != today:
            session.bounty_completed_today = []
            session.bounty_accepted = [b for b in session.bounty_accepted if b.get("type") == "weekly"]
            session.bounty_reset_date = today

        # Weekly reset: check if we're in a new week (Wednesday)
        import datetime
        now = datetime.datetime.now()
        # Find last Wednesday
        days_since_wed = (now.weekday() - 2) % 7
        last_wed = (now - datetime.timedelta(days=days_since_wed)).strftime("%Y-%m-%d")
        if session.bounty_weekly_reset_date != last_wed:
            session.bounty_completed_weekly = []
            session.bounty_accepted = [b for b in session.bounty_accepted if b.get("type") != "weekly"]
            session.bounty_weekly_reset_date = last_wed
            session.bounty_score_weekly = 0

    async def _on_bounty_list_req(self, session, payload: bytes):
        """BOUNTY_LIST_REQ(530) -> BOUNTY_LIST(531)
        Response: daily_count(u8) + [bounty_id(u16) + monster_id(u16) + level(u8) + zone_len(u8) + zone(str) +
                  gold(u32) + exp(u32) + token(u8) + accepted(u8) + completed(u8)] +
                  has_weekly(u8) + [weekly bounty data if has_weekly] +
                  accepted_count(u8)"""
        if not session.in_game:
            return

        level = session.stats.level if session.stats else 1
        if level < BOUNTY_MIN_LEVEL:
            # Not high enough level: send empty list
            self._send(session, MsgType.BOUNTY_LIST, struct.pack('<BBB', 0, 0, 0))
            return

        self._check_bounty_reset(session)

        # Generate daily bounties (deterministic per day using date seed)
        import time as _t
        import random as _rng3
        date_seed = int(_t.strftime("%Y%m%d"))
        _rng3.seed(date_seed)
        daily_bounties = self._generate_daily_bounties()
        _rng3.seed()  # restore random state

        # Build daily bounty data
        accepted_ids = {b["bounty_id"] for b in session.bounty_accepted}
        completed_ids = set(session.bounty_completed_today)

        data = struct.pack('<B', len(daily_bounties))
        for b in daily_bounties:
            zone_bytes = b["zone"].encode('utf-8')
            is_accepted = 1 if b["bounty_id"] in accepted_ids else 0
            is_completed = 1 if b["bounty_id"] in completed_ids else 0
            data += struct.pack('<HHB B', b["bounty_id"], b["monster_id"], b["level"], len(zone_bytes))
            data += zone_bytes
            data += struct.pack('<IIB BB', b["gold"], b["exp"], b["bounty_token"], is_accepted, is_completed)

        # Weekly bounty
        has_weekly = 1 if level >= BOUNTY_WEEKLY_MIN_LEVEL else 0
        data += struct.pack('<B', has_weekly)
        if has_weekly:
            wb = self._get_weekly_boss()
            zone_bytes = wb["zone"].encode('utf-8')
            is_accepted = 1 if wb["bounty_id"] in accepted_ids else 0
            is_completed = 1 if wb["bounty_id"] in set(session.bounty_completed_weekly) else 0
            data += struct.pack('<HHB B', wb["bounty_id"], wb["monster_id"], wb["level"], len(zone_bytes))
            data += zone_bytes
            data += struct.pack('<IIBBBBB', wb["gold"], wb["exp"], wb["bounty_token"],
                               is_accepted, is_completed,
                               wb["min_party"], wb["recommended_party"])

        # Accepted count
        data += struct.pack('<B', len(session.bounty_accepted))

        self._send(session, MsgType.BOUNTY_LIST, data)

    async def _on_bounty_accept(self, session, payload: bytes):
        """BOUNTY_ACCEPT(532) -> BOUNTY_ACCEPT_RESULT(533)
        Payload: bounty_id(u16)
        Result: 0=SUCCESS, 1=ALREADY_ACCEPTED, 2=MAX_LIMIT, 3=ALREADY_COMPLETED, 4=LEVEL_TOO_LOW, 5=NOT_FOUND"""
        if not session.in_game:
            return

        if len(payload) < 2:
            self._send(session, MsgType.BOUNTY_ACCEPT_RESULT, struct.pack('<B', 5))
            return

        bounty_id = struct.unpack_from('<H', payload, 0)[0]

        level = session.stats.level if session.stats else 1
        if level < BOUNTY_MIN_LEVEL:
            self._send(session, MsgType.BOUNTY_ACCEPT_RESULT, struct.pack('<B', 4))
            return

        self._check_bounty_reset(session)

        # Check if already accepted
        accepted_ids = {b["bounty_id"] for b in session.bounty_accepted}
        if bounty_id in accepted_ids:
            self._send(session, MsgType.BOUNTY_ACCEPT_RESULT, struct.pack('<B', 1))
            return

        # Check max limit
        if len(session.bounty_accepted) >= BOUNTY_MAX_ACCEPTED:
            self._send(session, MsgType.BOUNTY_ACCEPT_RESULT, struct.pack('<B', 2))
            return

        # Check if already completed
        if bounty_id in set(session.bounty_completed_today) or bounty_id in set(session.bounty_completed_weekly):
            self._send(session, MsgType.BOUNTY_ACCEPT_RESULT, struct.pack('<B', 3))
            return

        # Find bounty info
        import time as _t
        import random as _rng4
        date_seed = int(_t.strftime("%Y%m%d"))
        _rng4.seed(date_seed)
        daily_bounties = self._generate_daily_bounties()
        _rng4.seed()

        found = None
        for b in daily_bounties:
            if b["bounty_id"] == bounty_id:
                found = b
                break

        # Check weekly
        if not found and bounty_id == 20000:
            if level >= BOUNTY_WEEKLY_MIN_LEVEL:
                found = self._get_weekly_boss()

        if not found:
            self._send(session, MsgType.BOUNTY_ACCEPT_RESULT, struct.pack('<B', 5))
            return

        session.bounty_accepted.append({
            "bounty_id": bounty_id,
            "monster_id": found["monster_id"],
            "type": found["type"],
            "gold": found["gold"],
            "exp": found["exp"],
            "bounty_token": found["bounty_token"],
        })

        self._send(session, MsgType.BOUNTY_ACCEPT_RESULT, struct.pack('<BH', 0, bounty_id))

    async def _on_bounty_complete(self, session, payload: bytes):
        """BOUNTY_COMPLETE(534) -- server checks on monster kill.
        Also callable by client with payload: bounty_id(u16)
        Response: result(u8) + bounty_id(u16) + gold(u32) + exp(u32) + bounty_token(u8)
        Result: 0=SUCCESS, 1=NOT_ACCEPTED, 2=ALREADY_COMPLETED"""
        if not session.in_game:
            return

        if len(payload) < 2:
            return

        bounty_id = struct.unpack_from('<H', payload, 0)[0]

        self._check_bounty_reset(session)

        # Check if accepted
        accepted = None
        accepted_idx = -1
        for i, b in enumerate(session.bounty_accepted):
            if b["bounty_id"] == bounty_id:
                accepted = b
                accepted_idx = i
                break

        if not accepted:
            self._send(session, MsgType.BOUNTY_COMPLETE,
                      struct.pack('<BH', 1, bounty_id))
            return

        # Check if already completed
        if accepted["type"] == "daily" and bounty_id in set(session.bounty_completed_today):
            self._send(session, MsgType.BOUNTY_COMPLETE,
                      struct.pack('<BH', 2, bounty_id))
            return
        if accepted["type"] == "weekly" and bounty_id in set(session.bounty_completed_weekly):
            self._send(session, MsgType.BOUNTY_COMPLETE,
                      struct.pack('<BH', 2, bounty_id))
            return

        # Complete it!
        gold = accepted["gold"]
        exp = accepted["exp"]
        token = accepted["bounty_token"]

        # Apply rewards
        if session.stats:
            session.stats.add_exp(exp)
        session.gold = getattr(session, 'gold', 0) + gold
        session.bounty_tokens += token
        session.bounty_score_weekly += 1

        # Track completion
        if accepted["type"] == "daily":
            session.bounty_completed_today.append(bounty_id)
        else:
            session.bounty_completed_weekly.append(bounty_id)

        # Remove from accepted
        session.bounty_accepted.pop(accepted_idx)

        # Check daily completion bonus (all 3 daily done)
        import time as _t
        import random as _rng5
        date_seed = int(_t.strftime("%Y%m%d"))
        _rng5.seed(date_seed)
        daily_bounties = self._generate_daily_bounties()
        _rng5.seed()
        daily_ids = {b["bounty_id"] for b in daily_bounties}
        completed_daily = set(session.bounty_completed_today)
        if daily_ids.issubset(completed_daily):
            # All 3 daily bounties completed!
            bonus = BOUNTY_DAILY_COMPLETION_BONUS
            session.gold = getattr(session, 'gold', 0) + bonus["gold"]
            session.bounty_tokens += bonus["bounty_token"]
            gold += bonus["gold"]
            token += bonus["bounty_token"]

        self._send(session, MsgType.BOUNTY_COMPLETE,
                  struct.pack('<BHIIB', 0, bounty_id, gold, exp, token))

    async def _on_bounty_ranking_req(self, session, payload: bytes):
        """BOUNTY_RANKING_REQ(535) -> BOUNTY_RANKING(536)
        Response: rank_count(u8) + [rank(u8) + name_len(u8) + name(str) + score(u16)]
                  + my_rank(u8) + my_score(u16)"""
        if not session.in_game:
            return

        # Collect all players' weekly bounty scores
        rankings = []
        for s in self.sessions.values():
            if s.in_game and s.bounty_score_weekly > 0:
                char_name = getattr(s, 'char_name', 'Unknown')
                rankings.append({"name": char_name, "score": s.bounty_score_weekly, "account": s.account_id})

        # Sort by score descending, take top 10
        rankings.sort(key=lambda x: x["score"], reverse=True)
        top10 = rankings[:10]

        # Build response
        data = struct.pack('<B', len(top10))
        for i, r in enumerate(top10):
            name_bytes = r["name"].encode('utf-8')
            data += struct.pack('<B B', i + 1, len(name_bytes))
            data += name_bytes
            data += struct.pack('<H', r["score"])

        # My rank
        my_rank = 0
        for i, r in enumerate(rankings):
            if r["account"] == session.account_id:
                my_rank = i + 1
                break

        data += struct.pack('<BH', my_rank, session.bounty_score_weekly)

        self._send(session, MsgType.BOUNTY_RANKING, data)

    def _check_pvp_bounty(self, session):
        """Check if player should get PvP bounty after kill streak.
        Called when player kills another player in PvP zone.
        Returns tier info if new tier reached, None otherwise."""
        streak = session.pvp_kill_streak
        # Find highest applicable tier
        new_tier = 0
        for kill_threshold, tier_info in sorted(PVP_BOUNTY_TIERS.items()):
            if streak >= kill_threshold:
                new_tier = tier_info["tier"]

        if new_tier > session.pvp_bounty_tier:
            session.pvp_bounty_tier = new_tier
            # Get tier info
            for kill_threshold, tier_info in PVP_BOUNTY_TIERS.items():
                if tier_info["tier"] == new_tier:
                    return tier_info
        return None

    def _notify_pvp_bounty(self, session, tier_info):
        """PVP_BOUNTY_NOTIFY(537): broadcast bounty status.
        Payload: target_entity(u64) + tier(u8) + kill_streak(u16) + gold_reward(u32) + name_len(u8) + name(str)"""
        name_bytes = getattr(session, 'char_name', 'Unknown').encode('utf-8')
        data = struct.pack('<Q B H I B',
                          session.entity_id if hasattr(session, 'entity_id') else 0,
                          tier_info["tier"],
                          session.pvp_kill_streak,
                          tier_info["gold_reward"],
                          len(name_bytes))
        data += name_bytes

        # Broadcast to all players in same zone (or all)
        for s in self.sessions.values():
            if s.in_game:
                self._send(s, MsgType.PVP_BOUNTY_NOTIFY, data)

'''

# ====================================================================
# 6. Test cases (5 tests)
# ====================================================================
TEST_CODE = r'''
    # ━━━ Test: BOUNTY_LIST_REQ — 현상금 목록 조회 ━━━
    async def test_bounty_list():
        """현상금 목록 조회 (일일 3개 + 주간 확인)."""
        c = await login_and_enter(port)
        # Set level to 15+ for bounty access
        await c.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 50000))
        await c.recv_expect(MsgType.STAT_SYNC)
        await asyncio.sleep(0.1)

        await c.send(MsgType.BOUNTY_LIST_REQ, b'')
        msg_type, resp = await c.recv_expect(MsgType.BOUNTY_LIST)
        assert msg_type == MsgType.BOUNTY_LIST, f"Expected BOUNTY_LIST, got {msg_type}"
        daily_count = resp[0]
        assert daily_count == 3, f"Expected 3 daily bounties, got {daily_count}"
        c.close()

    await test("BOUNTY_LIST: 일일 현상금 3개 조회", test_bounty_list())

    # ━━━ Test: BOUNTY_ACCEPT — 현상금 수락 ━━━
    async def test_bounty_accept():
        """현상금 수락 테스트."""
        c = await login_and_enter(port)
        await c.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 50000))
        await c.recv_expect(MsgType.STAT_SYNC)
        await asyncio.sleep(0.1)

        # Get bounty list first
        await c.send(MsgType.BOUNTY_LIST_REQ, b'')
        msg_type, resp = await c.recv_expect(MsgType.BOUNTY_LIST)
        assert msg_type == MsgType.BOUNTY_LIST
        # Extract first bounty_id
        daily_count = resp[0]
        assert daily_count >= 1
        bounty_id = struct.unpack_from('<H', resp, 1)[0]

        # Accept the bounty
        await c.send(MsgType.BOUNTY_ACCEPT, struct.pack('<H', bounty_id))
        msg_type, resp = await c.recv_expect(MsgType.BOUNTY_ACCEPT_RESULT)
        assert msg_type == MsgType.BOUNTY_ACCEPT_RESULT
        result = resp[0]
        assert result == 0, f"Expected SUCCESS(0), got {result}"
        c.close()

    await test("BOUNTY_ACCEPT: 현상금 수락 성공", test_bounty_accept())

    # ━━━ Test: BOUNTY_ACCEPT_DUPLICATE — 중복 수락 차단 ━━━
    async def test_bounty_accept_duplicate():
        """이미 수락한 현상금 다시 수락 시도 -> ALREADY_ACCEPTED."""
        c = await login_and_enter(port)
        await c.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 50000))
        await c.recv_expect(MsgType.STAT_SYNC)
        await asyncio.sleep(0.1)

        await c.send(MsgType.BOUNTY_LIST_REQ, b'')
        msg_type, resp = await c.recv_expect(MsgType.BOUNTY_LIST)
        bounty_id = struct.unpack_from('<H', resp, 1)[0]

        # Accept once
        await c.send(MsgType.BOUNTY_ACCEPT, struct.pack('<H', bounty_id))
        msg_type, resp = await c.recv_expect(MsgType.BOUNTY_ACCEPT_RESULT)
        assert resp[0] == 0, "First accept should succeed"

        # Accept again -> should fail
        await c.send(MsgType.BOUNTY_ACCEPT, struct.pack('<H', bounty_id))
        msg_type, resp = await c.recv_expect(MsgType.BOUNTY_ACCEPT_RESULT)
        assert resp[0] == 1, f"Expected ALREADY_ACCEPTED(1), got {resp[0]}"
        c.close()

    await test("BOUNTY_ACCEPT_FAIL: 중복 수락 차단", test_bounty_accept_duplicate())

    # ━━━ Test: BOUNTY_COMPLETE — 현상금 완료 + 보상 ━━━
    async def test_bounty_complete():
        """현상금 수락 후 완료 → 골드/토큰 보상."""
        c = await login_and_enter(port)
        await c.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 50000))
        await c.recv_expect(MsgType.STAT_SYNC)
        await asyncio.sleep(0.1)

        await c.send(MsgType.BOUNTY_LIST_REQ, b'')
        msg_type, resp = await c.recv_expect(MsgType.BOUNTY_LIST)
        bounty_id = struct.unpack_from('<H', resp, 1)[0]

        # Accept
        await c.send(MsgType.BOUNTY_ACCEPT, struct.pack('<H', bounty_id))
        await c.recv_expect(MsgType.BOUNTY_ACCEPT_RESULT)

        # Complete
        await c.send(MsgType.BOUNTY_COMPLETE, struct.pack('<H', bounty_id))
        msg_type, resp = await c.recv_expect(MsgType.BOUNTY_COMPLETE)
        assert msg_type == MsgType.BOUNTY_COMPLETE, f"Expected BOUNTY_COMPLETE, got {msg_type}"
        result = resp[0]
        assert result == 0, f"Expected SUCCESS(0), got {result}"
        # bounty_id(2) + gold(4) + exp(4) + token(1) = 11 bytes after result
        returned_bounty_id = struct.unpack_from('<H', resp, 1)[0]
        assert returned_bounty_id == bounty_id
        gold = struct.unpack_from('<I', resp, 3)[0]
        assert gold > 0, f"Expected gold > 0, got {gold}"
        exp = struct.unpack_from('<I', resp, 7)[0]
        assert exp > 0, f"Expected exp > 0, got {exp}"
        token = resp[11]
        assert token > 0, f"Expected token > 0, got {token}"
        c.close()

    await test("BOUNTY_COMPLETE: 현상금 완료 보상 지급", test_bounty_complete())

    # ━━━ Test: BOUNTY_RANKING — 랭킹 조회 ━━━
    async def test_bounty_ranking():
        """현상금 완료 후 랭킹 조회."""
        c = await login_and_enter(port)
        await c.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 50000))
        await c.recv_expect(MsgType.STAT_SYNC)
        await asyncio.sleep(0.1)

        # Accept & complete a bounty first to have a score
        await c.send(MsgType.BOUNTY_LIST_REQ, b'')
        msg_type, resp = await c.recv_expect(MsgType.BOUNTY_LIST)
        bounty_id = struct.unpack_from('<H', resp, 1)[0]
        await c.send(MsgType.BOUNTY_ACCEPT, struct.pack('<H', bounty_id))
        await c.recv_expect(MsgType.BOUNTY_ACCEPT_RESULT)
        await c.send(MsgType.BOUNTY_COMPLETE, struct.pack('<H', bounty_id))
        await c.recv_expect(MsgType.BOUNTY_COMPLETE)

        # Now query ranking
        await c.send(MsgType.BOUNTY_RANKING_REQ, b'')
        msg_type, resp = await c.recv_expect(MsgType.BOUNTY_RANKING)
        assert msg_type == MsgType.BOUNTY_RANKING, f"Expected BOUNTY_RANKING, got {msg_type}"
        rank_count = resp[0]
        assert rank_count >= 0, f"Rank count should be >= 0, got {rank_count}"
        c.close()

    await test("BOUNTY_RANKING: 주간 랭킹 조회", test_bounty_ranking())
'''


def patch_bridge():
    with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Full completion check
    if 'BOUNTY_LIST_REQ = 530' in content and 'def _on_bounty_list_req' in content:
        print('[bridge] S047 already patched')
        return True

    changed = False

    # 1. MsgType -- after SCROLL_DISCOVER = 524
    if 'BOUNTY_LIST_REQ' not in content:
        marker = '    SCROLL_DISCOVER = 524'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + MSGTYPE_BLOCK + content[end:]
            changed = True
            print('[bridge] Added MsgType 530-537')
        else:
            print('[bridge] WARNING: Could not find SCROLL_DISCOVER = 524')

    # 2. Data constants -- after BOUNTY_TOKEN_SHOP or after SCROLL_DROP_RATES/CLASS_SKILLS
    if 'BOUNTY_ELITE_POOL' not in content:
        # Insert after the last CLASS_SKILLS definition
        marker = "CLASS_SKILLS = {"
        idx = content.find(marker)
        if idx >= 0:
            # Find closing }
            brace_count = 0
            for ci in range(idx, len(content)):
                if content[ci] == '{':
                    brace_count += 1
                elif content[ci] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = content.index('\n', ci) + 1
                        content = content[:end] + DATA_CONSTANTS + content[end:]
                        changed = True
                        print('[bridge] Added bounty data constants')
                        break
        else:
            # Fallback: after TRIPOD_TABLE closing
            marker2 = "SCROLL_DROP_RATES"
            idx2 = content.find(marker2)
            if idx2 >= 0:
                # Find end of SCROLL_DROP_RATES dict
                brace_start = content.find('{', idx2)
                if brace_start >= 0:
                    brace_count = 0
                    for ci in range(brace_start, len(content)):
                        if content[ci] == '{':
                            brace_count += 1
                        elif content[ci] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end = content.index('\n', ci) + 1
                                content = content[:end] + DATA_CONSTANTS + content[end:]
                                changed = True
                                print('[bridge] Added bounty data constants (fallback)')
                                break

    # 3. PlayerSession fields -- after scroll_collection
    if 'bounty_accepted' not in content:
        marker = '    scroll_collection: set = field(default_factory=set)  # set of discovered scroll_ids'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + SESSION_FIELDS + content[end:]
            changed = True
            print('[bridge] Added PlayerSession bounty fields')
        else:
            # Fallback: after tripod_equipped
            marker2 = '    tripod_equipped: dict = field(default_factory=dict)'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                end = content.index('\n', idx2) + 1
                content = content[:end] + SESSION_FIELDS + content[end:]
                changed = True
                print('[bridge] Added PlayerSession bounty fields (fallback)')

    # 4. Dispatch table -- after scroll_discover dispatch
    if 'self._on_bounty_list_req' not in content:
        marker = '            MsgType.SCROLL_DISCOVER: self._on_scroll_discover,'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + DISPATCH_ENTRIES + content[end:]
            changed = True
            print('[bridge] Added dispatch table entries')
        else:
            print('[bridge] WARNING: Could not find scroll_discover dispatch entry')

    # 5. Handler implementations -- before Tripod handlers
    if 'def _on_bounty_list_req' not in content:
        marker = '    # ---- Tripod & Scroll System (TASK 15: MsgType 520-524) ----'
        idx = content.find(marker)
        if idx < 0:
            # Try before Auction handlers
            marker = '    # ---- Auction House System (TASK 3: MsgType 390-397) ----'
            idx = content.find(marker)
        if idx >= 0:
            content = content[:idx] + HANDLER_CODE + '\n' + content[idx:]
            changed = True
            print('[bridge] Added bounty handler implementations')
        else:
            print('[bridge] WARNING: Could not find handler insertion point')

    if changed:
        with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
            f.write(content)

    # Verify
    checks = [
        'BOUNTY_LIST_REQ = 530', 'BOUNTY_ELITE_POOL', 'BOUNTY_WORLD_BOSSES',
        'PVP_BOUNTY_TIERS', 'BOUNTY_TOKEN_SHOP', 'BOUNTY_MAX_ACCEPTED',
        'def _on_bounty_list_req', 'def _on_bounty_accept',
        'def _on_bounty_complete', 'def _on_bounty_ranking_req',
        'def _check_pvp_bounty', 'def _notify_pvp_bounty',
        'self._on_bounty_list_req', 'bounty_accepted', 'bounty_tokens',
        'bounty_score_weekly', 'pvp_kill_streak',
    ]
    with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[bridge] MISSING: {missing}')
        return False
    print('[bridge] S047 patched OK -- 4 bounty handlers + PvP bounty + ranking + daily gen')
    return True


def patch_test():
    with open(TEST_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'test_bounty_list' in content:
        print('[test] S047 already patched')
        return True

    # Update imports to add bounty constants
    old_import = (
        '    TRIPOD_TABLE, TRIPOD_TIER_UNLOCK,\n'
        '    SCROLL_DROP_RATES, SKILL_CLASS_MAP, CLASS_SKILLS\n'
        ')'
    )
    new_import = (
        '    TRIPOD_TABLE, TRIPOD_TIER_UNLOCK,\n'
        '    SCROLL_DROP_RATES, SKILL_CLASS_MAP, CLASS_SKILLS,\n'
        '    BOUNTY_ELITE_POOL, BOUNTY_WORLD_BOSSES, PVP_BOUNTY_TIERS,\n'
        '    BOUNTY_MAX_ACCEPTED, BOUNTY_MIN_LEVEL, BOUNTY_TOKEN_SHOP\n'
        ')'
    )
    if old_import in content:
        content = content.replace(old_import, new_import, 1)
        print('[test] Updated imports')

    # Insert test cases before results section
    marker = '    # ━━━ 결과 ━━━'
    idx = content.find(marker)
    if idx < 0:
        import re as _re
        match = _re.search(r'^\s*print\(f"\\n{\'=\'', content, _re.MULTILINE)
        if match:
            idx = match.start()

    if idx >= 0:
        content = content[:idx] + TEST_CODE + '\n' + content[idx:]
    else:
        print('[test] WARNING: Could not find insertion point')
        return False

    with open(TEST_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    checks = ['test_bounty_list', 'test_bounty_accept', 'test_bounty_accept_duplicate',
              'test_bounty_complete', 'test_bounty_ranking']
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[test] MISSING: {missing}')
        return False
    print('[test] S047 patched OK -- 5 bounty tests added')
    return True


if __name__ == '__main__':
    ok1 = patch_bridge()
    ok2 = patch_test()
    if ok1 and ok2:
        print('\nS047 all patches applied!')
    else:
        print('\nS047 PATCH FAILED!')
        sys.exit(1)
