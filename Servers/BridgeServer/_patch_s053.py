"""
Patch S053: Battleground / Guild War / PvP Season (TASK 6)
- BATTLEGROUND_QUEUE(430)→BATTLEGROUND_STATUS(431)       -- 6v6 전장 큐(capture_point/payload)
- BATTLEGROUND_SCORE(432)→BATTLEGROUND_SCORE_UPDATE(433)  -- 실시간 점수 업데이트
- GUILD_WAR_DECLARE(434)→GUILD_WAR_STATUS(435)            -- 길드전 선언/수락
- PvP 시즌 리셋: 12주, soft_reset 공식, 티어별 보상
- 5 test cases

Battleground modes:
  capture_point: 3 points, capture_time:10s, score_per_second:1, win_score:1000
  payload: 2 phases, push_speed:2.0, checkpoints:3, phase_time:300s
Guild war: min_participants:10, 30min, destroy_crystal objective
PvP season: 12 weeks, soft_reset = 1000 + (rating-1000)*0.5
Tiers: Bronze(<1000)/Silver(1000-1299)/Gold(1300-1599)/Plat(1600-1899)/Diamond(1900-2199)/Master(2200-2499)/GM(2500+)

MsgType layout:
  430 BATTLEGROUND_QUEUE
  431 BATTLEGROUND_STATUS
  432 BATTLEGROUND_SCORE
  433 BATTLEGROUND_SCORE_UPDATE
  434 GUILD_WAR_DECLARE
  435 GUILD_WAR_STATUS
"""
import os
import sys
import re

DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_PATH = os.path.join(DIR, 'tcp_bridge.py')
TEST_PATH = os.path.join(DIR, 'test_tcp_bridge.py')

# ====================================================================
# 1. MsgType enums for Battleground (430-435)
# ====================================================================
MSGTYPE_BLOCK = (
    '\n'
    '    # Battleground / Guild War (TASK 6)\n'
    '    BATTLEGROUND_QUEUE = 430\n'
    '    BATTLEGROUND_STATUS = 431\n'
    '    BATTLEGROUND_SCORE = 432\n'
    '    BATTLEGROUND_SCORE_UPDATE = 433\n'
    '    GUILD_WAR_DECLARE = 434\n'
    '    GUILD_WAR_STATUS = 435\n'
)

# ====================================================================
# 2. Data constants (GDD pvp.yaml battleground)
# ====================================================================
DATA_CONSTANTS = r'''
# ---- Battleground / Guild War Data (GDD pvp.yaml) ----
# Battleground modes
BG_MODE_CAPTURE_POINT = 0
BG_MODE_PAYLOAD = 1
BG_MODES = ["capture_point", "payload"]
BG_TEAM_SIZE = 6
BG_MAP_SIZE = 200
BG_TIME_LIMIT = 900             # 15 minutes
BG_RESPAWN_TIMER = 10           # seconds
# Capture point
BG_CAPTURE_POINTS = 3
BG_CAPTURE_TIME = 10            # seconds to capture
BG_SCORE_PER_SECOND = 1
BG_WIN_SCORE = 1000
# Payload
BG_PAYLOAD_PHASES = 2
BG_PUSH_SPEED = 2.0
BG_PUSH_RADIUS = 5.0
BG_CHECKPOINTS = 3
BG_PHASE_TIME = 300             # 5 min per phase
# Guild war
GW_MIN_PARTICIPANTS = 10
GW_MAX_PARTICIPANTS = 20
GW_MAP_SIZE = 300
GW_TIME_LIMIT = 1800            # 30 minutes
GW_RESPAWN_TIMER = 15
GW_CRYSTAL_HP = 10000
# PvP season
PVP_SEASON_WEEKS = 12
PVP_INITIAL_RATING = 1000
PVP_PLACEMENT_MATCHES = 10
PVP_PLACEMENT_K_FACTOR = 64
PVP_DECAY_INACTIVITY_DAYS = 7
PVP_DECAY_PER_DAY = 25
PVP_TIERS = [
    {"name": "bronze",       "min": 0,    "max": 999,  "token": 100,  "title": "브론즈 투사"},
    {"name": "silver",       "min": 1000, "max": 1299, "token": 200,  "title": "실버 투사"},
    {"name": "gold",         "min": 1300, "max": 1599, "token": 500,  "title": "골드 투사"},
    {"name": "platinum",     "min": 1600, "max": 1899, "token": 1000, "title": "플래티넘 투사"},
    {"name": "diamond",      "min": 1900, "max": 2199, "token": 2000, "title": "다이아 투사"},
    {"name": "master",       "min": 2200, "max": 2499, "token": 3000, "title": "마스터"},
    {"name": "grandmaster",  "min": 2500, "max": 9999, "token": 5000, "title": "그랜드마스터"},
]
def _get_pvp_tier(rating):
    """Return tier dict for given rating."""
    for t in PVP_TIERS:
        if t["min"] <= rating <= t["max"]:
            return t
    return PVP_TIERS[0]

def _pvp_soft_reset(rating):
    """Season soft reset: new = 1000 + (current-1000)*0.5"""
    return int(1000 + (rating - 1000) * 0.5)

# Battleground queue state
_BG_QUEUE = {BG_MODE_CAPTURE_POINT: [], BG_MODE_PAYLOAD: []}
_BG_MATCH_NEXT_ID = 1
_BG_ACTIVE_MATCHES = {}  # match_id -> {mode, teams, scores, ...}
# Guild war state
_GW_PENDING = {}   # guild_id_a -> {target_guild_id, timestamp}
_GW_ACTIVE = {}    # war_id -> {guild_a, guild_b, crystals, scores, ...}
_GW_NEXT_ID = 1
'''

# ====================================================================
# 3. PlayerSession fields for battleground
# ====================================================================
SESSION_FIELDS = (
    '    # ---- Battleground / Guild War (TASK 6) ----\n'
    '    bg_queue_mode: int = -1                   # -1=not queued, 0=capture, 1=payload\n'
    '    bg_match_id: int = 0                      # active match id\n'
    '    bg_team: int = 0                          # 0=red, 1=blue\n'
    '    gw_war_id: int = 0                        # active guild war id\n'
    '    pvp_season_rating: int = 1000             # season rating (initial 1000)\n'
    '    pvp_season_matches: int = 0               # matches played this season\n'
    '    pvp_season_wins: int = 0                  # wins this season\n'
)

# ====================================================================
# 4. Dispatch table entries
# ====================================================================
DISPATCH_ENTRIES = (
    '            MsgType.BATTLEGROUND_QUEUE: self._on_battleground_queue,\n'
    '            MsgType.BATTLEGROUND_SCORE: self._on_battleground_score,\n'
    '            MsgType.GUILD_WAR_DECLARE: self._on_guild_war_declare,\n'
)

# ====================================================================
# 5. Handler implementations
# ====================================================================
HANDLER_CODE = r'''
    # ---- Battleground / Guild War (TASK 6: MsgType 430-435) ----

    async def _on_battleground_queue(self, session, payload: bytes):
        """BATTLEGROUND_QUEUE(430) -> BATTLEGROUND_STATUS(431)
        Request: action(u8) + mode(u8)
          action: 0=join queue, 1=cancel queue
          mode: 0=capture_point, 1=payload
        Response: status(u8) + match_id(u32) + mode(u8) + team(u8) + queue_count(u8)
          status: 0=QUEUED, 1=MATCH_FOUND, 2=CANCELLED, 3=ALREADY_IN_MATCH, 4=INVALID_MODE"""
        if not session.in_game or len(payload) < 2:
            return

        action = payload[0]
        mode = payload[1]

        def _send_status(status, match_id=0, m=0, team=0, qcount=0):
            self._send(session, MsgType.BATTLEGROUND_STATUS,
                       struct.pack('<B I B B B', status, match_id, m, team, qcount))

        # Cancel queue
        if action == 1:
            if session.bg_queue_mode >= 0:
                q = _BG_QUEUE.get(session.bg_queue_mode, [])
                if session.entity_id in q:
                    q.remove(session.entity_id)
                session.bg_queue_mode = -1
            _send_status(2)  # CANCELLED
            return

        # Validate mode
        if mode not in (BG_MODE_CAPTURE_POINT, BG_MODE_PAYLOAD):
            _send_status(4)  # INVALID_MODE
            return

        # Already in match?
        if session.bg_match_id > 0:
            _send_status(3, session.bg_match_id, mode, session.bg_team)
            return

        # Add to queue
        q = _BG_QUEUE.setdefault(mode, [])
        if session.entity_id not in q:
            q.append(session.entity_id)
        session.bg_queue_mode = mode

        # Check if enough players for match (BG_TEAM_SIZE * 2)
        needed = BG_TEAM_SIZE * 2
        if len(q) >= needed:
            global _BG_MATCH_NEXT_ID
            match_id = _BG_MATCH_NEXT_ID
            _BG_MATCH_NEXT_ID += 1

            # Pop players from queue
            players = q[:needed]
            del q[:needed]

            # Split teams
            red_team = players[:BG_TEAM_SIZE]
            blue_team = players[BG_TEAM_SIZE:]

            # Create match state
            if mode == BG_MODE_CAPTURE_POINT:
                match_state = {
                    "mode": mode,
                    "red_team": red_team, "blue_team": blue_team,
                    "red_score": 0, "blue_score": 0,
                    "win_score": BG_WIN_SCORE,
                    "capture_points": [0] * BG_CAPTURE_POINTS,  # 0=neutral, 1=red, 2=blue
                    "time_remaining": BG_TIME_LIMIT,
                }
            else:  # payload
                match_state = {
                    "mode": mode,
                    "red_team": red_team, "blue_team": blue_team,
                    "red_distance": 0.0, "blue_distance": 0.0,
                    "phase": 1,
                    "checkpoints": BG_CHECKPOINTS,
                    "time_remaining": BG_PHASE_TIME,
                }
            _BG_ACTIVE_MATCHES[match_id] = match_state

            # Notify all players in match
            for eid in red_team + blue_team:
                for s in self.sessions.values():
                    if s.entity_id == eid:
                        team = 0 if eid in red_team else 1
                        s.bg_match_id = match_id
                        s.bg_team = team
                        s.bg_queue_mode = -1
                        _send_status2 = lambda st, mid, md, tm, qc, ss=s: self._send(
                            ss, MsgType.BATTLEGROUND_STATUS,
                            struct.pack('<B I B B B', st, mid, md, tm, qc))
                        _send_status2(1, match_id, mode, team, 0)  # MATCH_FOUND
                        break
        else:
            # Still waiting
            _send_status(0, 0, mode, 0, len(q))  # QUEUED

    async def _on_battleground_score(self, session, payload: bytes):
        """BATTLEGROUND_SCORE(432) -> BATTLEGROUND_SCORE_UPDATE(433)
        Request: action(u8) + point_index(u8)
          action: 0=capture_point (point_index used), 1=push_payload, 2=query_score
        Response: mode(u8) + red_score(u32) + blue_score(u32) + time_remaining(u32) + point_data(variable)
        """
        if not session.in_game or len(payload) < 2:
            return

        action = payload[0]
        point_index = payload[1]

        match_id = session.bg_match_id
        if match_id <= 0 or match_id not in _BG_ACTIVE_MATCHES:
            # Not in match — send empty score
            self._send(session, MsgType.BATTLEGROUND_SCORE_UPDATE,
                       struct.pack('<B I I I B', 0, 0, 0, 0, 0))
            return

        match = _BG_ACTIVE_MATCHES[match_id]
        mode = match["mode"]

        if mode == BG_MODE_CAPTURE_POINT:
            if action == 0 and 0 <= point_index < BG_CAPTURE_POINTS:
                # Capture a point — team takes ownership
                team_val = 1 if session.bg_team == 0 else 2  # 1=red, 2=blue
                match["capture_points"][point_index] = team_val

                # Update scores based on controlled points
                red_owned = sum(1 for p in match["capture_points"] if p == 1)
                blue_owned = sum(1 for p in match["capture_points"] if p == 2)
                match["red_score"] += red_owned * BG_SCORE_PER_SECOND
                match["blue_score"] += blue_owned * BG_SCORE_PER_SECOND

            # Build response: mode + red_score + blue_score + time + num_points + [point_owner]
            data = struct.pack('<B I I I B', mode,
                               match["red_score"], match["blue_score"],
                               match["time_remaining"],
                               BG_CAPTURE_POINTS)
            for p in match["capture_points"]:
                data += struct.pack('<B', p)

            # Check win
            winner = -1
            if match["red_score"] >= BG_WIN_SCORE:
                winner = 0  # red wins
            elif match["blue_score"] >= BG_WIN_SCORE:
                winner = 1  # blue wins

            if winner >= 0:
                data += struct.pack('<b', winner)
                # Cleanup match
                self._bg_end_match(match_id, winner)
            else:
                data += struct.pack('<b', -1)  # no winner yet

            self._send(session, MsgType.BATTLEGROUND_SCORE_UPDATE, data)

        elif mode == BG_MODE_PAYLOAD:
            if action == 1:
                # Push payload
                key = "red_distance" if session.bg_team == 0 else "blue_distance"
                match[key] = match.get(key, 0.0) + BG_PUSH_SPEED

            # Build response
            data = struct.pack('<B I I I B',
                               mode,
                               int(match.get("red_distance", 0)),
                               int(match.get("blue_distance", 0)),
                               match["time_remaining"],
                               match.get("phase", 1))

            # Check checkpoint completion
            total_dist = BG_PUSH_SPEED * BG_PHASE_TIME  # max distance
            red_progress = match.get("red_distance", 0) / max(total_dist, 1)
            blue_progress = match.get("blue_distance", 0) / max(total_dist, 1)
            winner = -1
            if red_progress >= 1.0 and blue_progress >= 1.0:
                winner = 0 if match.get("red_distance", 0) > match.get("blue_distance", 0) else 1
            elif red_progress >= 1.0 and match.get("phase", 1) >= BG_PAYLOAD_PHASES:
                winner = 0
            elif blue_progress >= 1.0 and match.get("phase", 1) >= BG_PAYLOAD_PHASES:
                winner = 1

            data += struct.pack('<b', winner)
            if winner >= 0:
                self._bg_end_match(match_id, winner)

            self._send(session, MsgType.BATTLEGROUND_SCORE_UPDATE, data)
        else:
            # Query only
            self._send(session, MsgType.BATTLEGROUND_SCORE_UPDATE,
                       struct.pack('<B I I I B b', 0, 0, 0, 0, 0, -1))

    def _bg_end_match(self, match_id, winner_team):
        """End a battleground match. Award PvP rating to winners."""
        match = _BG_ACTIVE_MATCHES.pop(match_id, None)
        if not match:
            return
        all_players = match.get("red_team", []) + match.get("blue_team", [])
        red = set(match.get("red_team", []))
        for eid in all_players:
            for s in self.sessions.values():
                if s.entity_id == eid:
                    is_red = eid in red
                    won = (winner_team == 0 and is_red) or (winner_team == 1 and not is_red)
                    if won:
                        s.pvp_season_wins += 1
                        s.pvp_season_rating += 15
                    else:
                        s.pvp_season_rating = max(0, s.pvp_season_rating - 10)
                    s.pvp_season_matches += 1
                    s.bg_match_id = 0
                    s.bg_team = 0
                    break

    async def _on_guild_war_declare(self, session, payload: bytes):
        """GUILD_WAR_DECLARE(434) -> GUILD_WAR_STATUS(435)
        Request: action(u8) + target_guild_id(u32)
          action: 0=declare_war, 1=accept_war, 2=reject_war, 3=query_status
        Response: status(u8) + war_id(u32) + guild_a(u32) + guild_b(u32) +
                  crystal_hp_a(u32) + crystal_hp_b(u32) + time_remaining(u32)
          status: 0=WAR_DECLARED, 1=WAR_STARTED, 2=WAR_REJECTED, 3=NO_GUILD,
                  4=TOO_FEW_MEMBERS, 5=ALREADY_AT_WAR, 6=PENDING_INFO, 7=NO_WAR"""
        if not session.in_game or len(payload) < 5:
            return

        action = payload[0]
        target_guild_id = struct.unpack('<I', payload[1:5])[0]

        def _send_status(status, war_id=0, ga=0, gb=0, hp_a=0, hp_b=0, time_rem=0):
            self._send(session, MsgType.GUILD_WAR_STATUS,
                       struct.pack('<B I I I I I I', status, war_id, ga, gb, hp_a, hp_b, time_rem))

        # Must be in a guild
        if not session.guild_id:
            _send_status(3)  # NO_GUILD
            return

        my_guild = session.guild_id

        if action == 3:  # Query status
            # Check active war
            for wid, war in _GW_ACTIVE.items():
                if my_guild in (war["guild_a"], war["guild_b"]):
                    _send_status(1, wid, war["guild_a"], war["guild_b"],
                                 war["crystal_a"], war["crystal_b"], war["time_remaining"])
                    return
            # Check pending
            if my_guild in _GW_PENDING:
                pending = _GW_PENDING[my_guild]
                _send_status(6, 0, my_guild, pending["target_guild_id"], 0, 0, 0)
                return
            # Check if someone declared on us
            for gid, pending in _GW_PENDING.items():
                if pending["target_guild_id"] == my_guild:
                    _send_status(6, 0, gid, my_guild, 0, 0, 0)
                    return
            _send_status(7)  # NO_WAR
            return

        if action == 0:  # Declare war
            # Check not already at war
            for war in _GW_ACTIVE.values():
                if my_guild in (war["guild_a"], war["guild_b"]):
                    _send_status(5)  # ALREADY_AT_WAR
                    return
            if my_guild in _GW_PENDING:
                _send_status(5)
                return

            # Register pending war
            _GW_PENDING[my_guild] = {"target_guild_id": target_guild_id, "timestamp": 0}
            _send_status(0, 0, my_guild, target_guild_id)  # WAR_DECLARED
            return

        if action == 1:  # Accept war
            # Find pending war targeting my guild
            declaring_guild = None
            for gid, pending in list(_GW_PENDING.items()):
                if pending["target_guild_id"] == my_guild:
                    declaring_guild = gid
                    break
            # Or accept by target_guild_id
            if not declaring_guild and target_guild_id in _GW_PENDING:
                if _GW_PENDING[target_guild_id]["target_guild_id"] == my_guild:
                    declaring_guild = target_guild_id

            if not declaring_guild:
                _send_status(7)  # NO_WAR to accept
                return

            # Create active war
            global _GW_NEXT_ID
            war_id = _GW_NEXT_ID
            _GW_NEXT_ID += 1
            _GW_ACTIVE[war_id] = {
                "guild_a": declaring_guild,
                "guild_b": my_guild,
                "crystal_a": GW_CRYSTAL_HP,
                "crystal_b": GW_CRYSTAL_HP,
                "time_remaining": GW_TIME_LIMIT,
                "scores_a": 0, "scores_b": 0,
            }
            del _GW_PENDING[declaring_guild]

            # Update session
            session.gw_war_id = war_id
            _send_status(1, war_id, declaring_guild, my_guild,
                         GW_CRYSTAL_HP, GW_CRYSTAL_HP, GW_TIME_LIMIT)
            return

        if action == 2:  # Reject war
            for gid, pending in list(_GW_PENDING.items()):
                if pending["target_guild_id"] == my_guild:
                    del _GW_PENDING[gid]
                    _send_status(2, 0, gid, my_guild)
                    return
            _send_status(7)  # NO_WAR
            return

    def _pvp_season_reset_all(self):
        """Reset PvP season for all sessions. Soft reset + tier rewards (called on season end)."""
        for s in self.sessions.values():
            if s.pvp_season_matches > 0:
                tier = _get_pvp_tier(s.pvp_season_rating)
                # Simulate tier reward via gold (simplified — real system would use mail)
                s.gold += tier["token"]
                # Soft reset
                s.pvp_season_rating = _pvp_soft_reset(s.pvp_season_rating)
                s.pvp_season_matches = 0
                s.pvp_season_wins = 0
'''

# ====================================================================
# 6. Test cases (5 tests)
# ====================================================================
TEST_CODE = r'''
    # ━━━ Test: BG_QUEUE — 전장 큐 등록/취소 ━━━
    async def test_bg_queue():
        """전장 큐 등록 → QUEUED(0), 취소 → CANCELLED(2)."""
        c = await login_and_enter(port)
        # Join capture_point queue
        await c.send(MsgType.BATTLEGROUND_QUEUE, struct.pack('<B B', 0, 0))
        msg_type, resp = await c.recv_expect(MsgType.BATTLEGROUND_STATUS)
        assert msg_type == MsgType.BATTLEGROUND_STATUS, f"Expected BG_STATUS, got {msg_type}"
        status = resp[0]
        assert status in (0, 1), f"Expected QUEUED(0) or MATCH_FOUND(1), got {status}"

        # Cancel queue
        await c.send(MsgType.BATTLEGROUND_QUEUE, struct.pack('<B B', 1, 0))
        msg_type, resp = await c.recv_expect(MsgType.BATTLEGROUND_STATUS)
        status = resp[0]
        assert status == 2, f"Expected CANCELLED(2), got {status}"
        c.close()

    await test("BG_QUEUE: 전장 큐 등록/취소", test_bg_queue())

    # ━━━ Test: BG_INVALID_MODE — 잘못된 전장 모드 ━━━
    async def test_bg_invalid_mode():
        """잘못된 모드 전장 큐 → INVALID_MODE(4)."""
        c = await login_and_enter(port)
        await c.send(MsgType.BATTLEGROUND_QUEUE, struct.pack('<B B', 0, 99))
        msg_type, resp = await c.recv_expect(MsgType.BATTLEGROUND_STATUS)
        status = resp[0]
        assert status == 4, f"Expected INVALID_MODE(4), got {status}"
        c.close()

    await test("BG_INVALID_MODE: 잘못된 전장 모드 → INVALID_MODE", test_bg_invalid_mode())

    # ━━━ Test: BG_SCORE_NOT_IN_MATCH — 매치 없이 점수 조회 ━━━
    async def test_bg_score_no_match():
        """매치 없이 점수 조회 → 빈 응답."""
        c = await login_and_enter(port)
        await c.send(MsgType.BATTLEGROUND_SCORE, struct.pack('<B B', 2, 0))
        msg_type, resp = await c.recv_expect(MsgType.BATTLEGROUND_SCORE_UPDATE)
        assert msg_type == MsgType.BATTLEGROUND_SCORE_UPDATE
        mode = resp[0]
        assert mode == 0, f"Expected mode=0 (default), got {mode}"
        c.close()

    await test("BG_SCORE: 매치 없이 점수 조회 → 빈 응답", test_bg_score_no_match())

    # ━━━ Test: GW_DECLARE_NO_GUILD — 길드 없이 길드전 선언 ━━━
    async def test_gw_no_guild():
        """길드 없이 길드전 선언 → NO_GUILD(3)."""
        c = await login_and_enter(port)
        await c.send(MsgType.GUILD_WAR_DECLARE, struct.pack('<B I', 0, 999))
        msg_type, resp = await c.recv_expect(MsgType.GUILD_WAR_STATUS)
        assert msg_type == MsgType.GUILD_WAR_STATUS
        status = resp[0]
        assert status == 3, f"Expected NO_GUILD(3), got {status}"
        c.close()

    await test("GW_DECLARE: 길드 없이 길드전 선언 → NO_GUILD", test_gw_no_guild())

    # ━━━ Test: GW_QUERY_NO_WAR — 전쟁 없을 때 상태 조회 ━━━
    async def test_gw_query_no_war():
        """길드전 상태 조회 (전쟁 없음) → NO_WAR(7) or NO_GUILD(3)."""
        c = await login_and_enter(port)
        await c.send(MsgType.GUILD_WAR_DECLARE, struct.pack('<B I', 3, 0))
        msg_type, resp = await c.recv_expect(MsgType.GUILD_WAR_STATUS)
        assert msg_type == MsgType.GUILD_WAR_STATUS
        status = resp[0]
        assert status in (3, 7), f"Expected NO_GUILD(3) or NO_WAR(7), got {status}"
        c.close()

    await test("GW_QUERY: 길드전 상태 조회 (없음) → NO_WAR", test_gw_query_no_war())
'''


def patch_bridge():
    # NOTE: Do NOT restore from git — S053 must apply on top of S052's output.
    # Previous patches (S050-S052) restore from git and apply themselves.
    # S053 reads the already-patched file.
    with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Full completion check
    if 'BATTLEGROUND_QUEUE = 430' in content and 'def _on_battleground_queue' in content and '_bg_end_match' in content:
        print('[bridge] S053 already patched')
        return True

    changed = False

    # 1. MsgType -- after DURABILITY_QUERY = 467
    if 'BATTLEGROUND_QUEUE' not in content:
        marker = '    DURABILITY_QUERY = 467'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + MSGTYPE_BLOCK + content[end:]
            changed = True
            print('[bridge] Added MsgType 430-435')
        else:
            # Fallback: after PARTY_FINDER_CREATE = 422 (if S052 not applied yet)
            marker2 = '    PARTY_FINDER_CREATE = 422'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                end = content.index('\n', idx2) + 1
                content = content[:end] + MSGTYPE_BLOCK + content[end:]
                changed = True
                print('[bridge] Added MsgType 430-435 (fallback after 422)')
            else:
                print('[bridge] WARNING: Could not find MsgType insertion point')

    # 2. Data constants -- after REROLL_MAX_LOCKS or RANDOM_OPTION_RANGES closing brace
    if 'BG_MODE_CAPTURE_POINT' not in content:
        # Try after RANDOM_OPTION_RANGES block end
        marker = "REROLL_MAX_LOCKS"
        idx = content.find(marker)
        if idx >= 0:
            nl = content.index('\n', idx) + 1
            content = content[:nl] + DATA_CONSTANTS + content[nl:]
            changed = True
            print('[bridge] Added battleground data constants')
        else:
            # Fallback: after _PARTY_FINDER_NEXT_ID
            marker2 = "_PARTY_FINDER_NEXT_ID"
            idx2 = content.find(marker2)
            if idx2 >= 0:
                nl = content.index('\n', idx2) + 1
                content = content[:nl] + DATA_CONSTANTS + content[nl:]
                changed = True
                print('[bridge] Added battleground data constants (fallback)')
            else:
                print('[bridge] WARNING: Could not find data constants insertion point')

    # 3. PlayerSession fields -- after reappraisal_scrolls field
    if 'bg_queue_mode: int' not in content:
        marker = '    reappraisal_scrolls: int = 0'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + SESSION_FIELDS + content[end:]
            changed = True
            print('[bridge] Added PlayerSession battleground fields')
        else:
            # Fallback: after party_finder_listing
            marker2 = '    party_finder_listing: dict = field(default_factory=dict)'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                end = content.index('\n', idx2) + 1
                content = content[:end] + SESSION_FIELDS + content[end:]
                changed = True
                print('[bridge] Added PlayerSession battleground fields (fallback)')
            else:
                print('[bridge] WARNING: Could not find session fields insertion point')

    # 4. Dispatch table -- after durability_query dispatch
    if 'self._on_battleground_queue' not in content:
        marker = '            MsgType.DURABILITY_QUERY: self._on_durability_query,'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + DISPATCH_ENTRIES + content[end:]
            changed = True
            print('[bridge] Added dispatch table entries')
        else:
            # Fallback: after party_finder_create dispatch
            marker2 = '            MsgType.PARTY_FINDER_CREATE: self._on_party_finder_create,'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                end = content.index('\n', idx2) + 1
                content = content[:end] + DISPATCH_ENTRIES + content[end:]
                changed = True
                print('[bridge] Added dispatch table entries (fallback)')
            else:
                print('[bridge] WARNING: Could not find dispatch table insertion point')

    # 5. Handler implementations -- before Durability handlers
    if 'def _on_battleground_queue' not in content:
        marker = '    # ---- Durability / Repair / Reroll (TASK 9: MsgType 462-467) ----'
        idx = content.find(marker)
        if idx < 0:
            # Fallback: before Social Enhancement
            marker = '    # ---- Social Enhancement (TASK 5: MsgType 410-422) ----'
            idx = content.find(marker)
        if idx < 0:
            # Fallback: before Enhancement Deepening
            marker = '    # ---- Enhancement Deepening (TASK 8: MsgType 450-459) ----'
            idx = content.find(marker)
        if idx >= 0:
            content = content[:idx] + HANDLER_CODE + '\n' + content[idx:]
            changed = True
            print('[bridge] Added battleground handler implementations')
        else:
            print('[bridge] WARNING: Could not find handler insertion point')

    # Always write
    with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'[bridge] Written: {content.count(chr(10))} lines')

    # Verify
    checks = [
        'BATTLEGROUND_QUEUE = 430', 'BATTLEGROUND_STATUS = 431',
        'BATTLEGROUND_SCORE = 432', 'BATTLEGROUND_SCORE_UPDATE = 433',
        'GUILD_WAR_DECLARE = 434', 'GUILD_WAR_STATUS = 435',
        'BG_MODE_CAPTURE_POINT', 'BG_MODE_PAYLOAD', 'BG_TEAM_SIZE',
        'BG_WIN_SCORE', 'GW_CRYSTAL_HP', 'GW_MIN_PARTICIPANTS',
        'PVP_SEASON_WEEKS', 'PVP_TIERS', '_get_pvp_tier', '_pvp_soft_reset',
        '_BG_QUEUE', '_BG_ACTIVE_MATCHES', '_GW_PENDING', '_GW_ACTIVE',
        'def _on_battleground_queue', 'def _on_battleground_score',
        'def _on_guild_war_declare', 'def _bg_end_match',
        'def _pvp_season_reset_all',
        'self._on_battleground_queue', 'self._on_battleground_score',
        'self._on_guild_war_declare',
        'bg_queue_mode: int', 'bg_match_id: int', 'bg_team: int',
        'gw_war_id: int', 'pvp_season_rating: int',
    ]
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[bridge] MISSING: {missing}')
        return False
    print('[bridge] S053 patched OK -- battleground/guild_war/pvp_season')
    return True


def patch_test():
    # NOTE: Do NOT restore from git — S053 must apply on top of S052's output.
    with open(TEST_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'test_bg_queue' in content and 'test_gw_no_guild' in content:
        print('[test] S053 already patched')
        return True

    # Update imports — add battleground constants
    old_import = (
        '    DURABILITY_MAX, REPAIR_COST_MULTIPLIER,\n'
        '    REROLL_GOLD_COST, REROLL_MATERIAL, REROLL_LOCK_COST\n'
        ')'
    )
    new_import = (
        '    DURABILITY_MAX, REPAIR_COST_MULTIPLIER,\n'
        '    REROLL_GOLD_COST, REROLL_MATERIAL, REROLL_LOCK_COST,\n'
        '    BG_MODE_CAPTURE_POINT, BG_MODE_PAYLOAD, BG_TEAM_SIZE,\n'
        '    BG_WIN_SCORE, GW_CRYSTAL_HP, GW_MIN_PARTICIPANTS\n'
        ')'
    )

    # If S052 import exists, update it
    if old_import in content:
        content = content.replace(old_import, new_import, 1)
        print('[test] Updated imports with battleground constants')
    else:
        # Try fallback: S052 might not have been patched to test yet
        old_import_v1 = (
            '    FRIEND_MAX, BLOCK_MAX, PARTY_FINDER_CATEGORIES,\n'
            '    PARTY_FINDER_MAX_LISTINGS, PARTY_FINDER_ROLES\n'
            ')'
        )
        new_import_v1 = (
            '    FRIEND_MAX, BLOCK_MAX, PARTY_FINDER_CATEGORIES,\n'
            '    PARTY_FINDER_MAX_LISTINGS, PARTY_FINDER_ROLES,\n'
            '    DURABILITY_MAX, REPAIR_COST_MULTIPLIER,\n'
            '    REROLL_GOLD_COST, REROLL_MATERIAL, REROLL_LOCK_COST,\n'
            '    BG_MODE_CAPTURE_POINT, BG_MODE_PAYLOAD, BG_TEAM_SIZE,\n'
            '    BG_WIN_SCORE, GW_CRYSTAL_HP, GW_MIN_PARTICIPANTS\n'
            ')'
        )
        if old_import_v1 in content:
            content = content.replace(old_import_v1, new_import_v1, 1)
            print('[test] Updated imports with battleground constants (v1 fallback)')
        else:
            print('[test] NOTE: Could not find expected import block — imports may already be correct')

    # Insert test cases before results section
    marker = '    # ━━━ 결과 ━━━'
    idx = content.find(marker)
    if idx < 0:
        match = re.search(r'^\s*print\(f"\\n{\'=\'', content, re.MULTILINE)
        if match:
            idx = match.start()

    if idx >= 0:
        content = content[:idx] + TEST_CODE + '\n' + content[idx:]
    else:
        print('[test] WARNING: Could not find insertion point')
        return False

    with open(TEST_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    checks = ['test_bg_queue', 'test_bg_invalid_mode', 'test_bg_score_no_match',
              'test_gw_no_guild', 'test_gw_query_no_war',
              'BATTLEGROUND_QUEUE', 'BATTLEGROUND_STATUS', 'GUILD_WAR_DECLARE',
              'GUILD_WAR_STATUS', 'BATTLEGROUND_SCORE']
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[test] MISSING: {missing}')
        return False
    print('[test] S053 patched OK -- 5 battleground tests')
    return True


if __name__ == '__main__':
    ok1 = patch_bridge()
    ok2 = patch_test()
    if ok1 and ok2:
        print('\nS053 all patches applied!')
    else:
        print('\nS053 PATCH FAILED!')
        sys.exit(1)
