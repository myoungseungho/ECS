"""
Patch S055: Secret Realm System (TASK 17 — 비경 탐험)
- SECRET_REALM_SPAWN(540)              -- 비경 포탈 스폰 (존 브로드캐스트)
- SECRET_REALM_ENTER(541)→ENTER_RESULT(542) -- 비경 입장 (일일3회/레벨20+/솔로or2인)
- SECRET_REALM_COMPLETE(543)           -- 비경 클리어 (등급 S/A/B/C + 보상)
- SECRET_REALM_FAIL(544)               -- 비경 실패

Realm Types (5종):
  trial:    시련의 방 (웨이브 전투, grade by clear_time)
  wisdom:   지혜의 방 (퍼즐, grade by time+hints)
  treasure: 보물의 방 (상자 수집, grade by chests_opened)
  training: 수련의 방 (콤보/회피, grade by fail_count)
  fortune:  운명의 방 (랜덤 보상, grade by luck_score)

Special Conditions (날씨+시간 조합 4종):
  night_fog → ghost_trial, storm_noon → thunder_training,
  snow_dawn → crystal_treasure, clear_evening → fortune_garden

4 test cases
"""
import os
import sys
import re

DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_PATH = os.path.join(DIR, 'tcp_bridge.py')
TEST_PATH = os.path.join(DIR, 'test_tcp_bridge.py')

# ====================================================================
# 1. MsgType enums for Secret Realm (540-544)
# ====================================================================
MSGTYPE_BLOCK = (
    '\n'
    '    # Secret Realm (TASK 17)\n'
    '    SECRET_REALM_SPAWN = 540\n'
    '    SECRET_REALM_ENTER = 541\n'
    '    SECRET_REALM_ENTER_RESULT = 542\n'
    '    SECRET_REALM_COMPLETE = 543\n'
    '    SECRET_REALM_FAIL = 544\n'
)

# ====================================================================
# 2. Data constants — realm types, special conditions, rewards
# ====================================================================
DATA_CONSTANTS = r'''
# ---- Secret Realm System Data (GDD secret_realm.yaml) ----
SECRET_REALM_UNLOCK_LEVEL = 20
SECRET_REALM_DAILY_LIMIT = 3
SECRET_REALM_SPAWN_INTERVAL = (300, 900)  # 5~15 min
SECRET_REALM_PER_ZONE = 1
SECRET_REALM_PORTAL_DURATION = 300  # 5min then despawn
SECRET_REALM_ELIGIBLE_ZONES = [1, 2, 3, 4, 5, 6, 7]
SECRET_REALM_MAX_PARTY = 2  # solo or 2-man

# Realm type definitions
REALM_TYPES = {
    "trial": {
        "name": "시련의 방", "time_limit": 300,
        "grade_criteria": "clear_time",
        "grade_thresholds": {"S": 180, "A": 240, "B": 280, "C": 300},
        "rewards": {
            "S": {"gold": 3000, "equipment_box": "rare+", "scroll_chance": 0.3},
            "A": {"gold": 2000, "equipment_box": "uncommon+", "scroll_chance": 0.1},
            "B": {"gold": 1000, "materials": 5},
            "C": {"gold": 500, "materials": 2},
        },
    },
    "wisdom": {
        "name": "지혜의 방", "time_limit": 240,
        "grade_criteria": "clear_time_hints",
        "grade_thresholds": {
            "S": {"time": 120, "hints": 0}, "A": {"time": 180, "hints": 1},
            "B": {"time": 240, "hints": 2}, "C": {"time": 240, "hints": 3},
        },
        "rewards": {
            "S": {"gold": 2000, "crafting_materials": "rare", "scroll_chance": 0.2},
            "A": {"gold": 1500, "crafting_materials": "uncommon"},
            "B": {"gold": 800, "crafting_materials": "common"},
            "C": {"gold": 400},
        },
    },
    "treasure": {
        "name": "보물의 방", "time_limit": 180,
        "grade_criteria": "chests_opened",
        "grade_thresholds": {"S": 18, "A": 14, "B": 10, "C": 5},
        "rewards": {
            "S": {"gold": 5000, "random_items": 5, "golden_chest_bonus": "epic_item"},
            "A": {"gold": 3000, "random_items": 3},
            "B": {"gold": 1500, "random_items": 2},
            "C": {"gold": 500, "random_items": 1},
        },
    },
    "training": {
        "name": "수련의 방", "time_limit": 300,
        "grade_criteria": "fail_count",
        "grade_thresholds": {"S": 0, "A": 2, "B": 5, "C": 99},
        "rewards": {
            "S": {"exp": 5000, "scroll_guaranteed": "tier_1~2", "skill_point": 1},
            "A": {"exp": 3000, "scroll_chance": 0.5},
            "B": {"exp": 2000},
            "C": {"exp": 1000},
        },
    },
    "fortune": {
        "name": "운명의 방", "time_limit": 120,
        "grade_criteria": "luck_score",
        "grade_thresholds": {"S": 80, "A": 50, "B": 20, "C": 0},
        "rewards": {
            "S": {"gold": 20000, "legendary_material": 1},
            "A": {"gold": 5000, "rare_material": 3},
            "B": {"gold": 1000, "materials": 5},
            "C": {"gold": 100},
        },
    },
}
REALM_TYPE_LIST = list(REALM_TYPES.keys())  # index order for protocol

# Special weather+time conditions
SPECIAL_REALM_CONDITIONS = {
    "night_fog":      {"weather": "fog",   "time": "night",   "realm": "ghost_trial",       "name": "유령의 시련",    "multiplier": 2.0},
    "storm_noon":     {"weather": "storm", "time": "noon",    "realm": "thunder_training",  "name": "뇌신의 수련장", "multiplier": 1.5},
    "snow_dawn":      {"weather": "snow",  "time": "dawn",    "realm": "crystal_treasure",  "name": "수정 보물고",   "multiplier": 1.5},
    "clear_evening":  {"weather": "clear", "time": "evening", "realm": "fortune_garden",    "name": "운명의 정원",   "multiplier": 1.5},
}
SPECIAL_REALM_SPAWN_CHANCE = 0.5  # 50% when condition met

# Active realm portals: zone_id -> {realm_type, spawn_time, special, instance_id}
_REALM_PORTALS = {}
_REALM_INSTANCES = {}  # instance_id -> {players: [sid], realm_type, start_time, special_multiplier}
_REALM_NEXT_ID = 1
'''

# ====================================================================
# 3. PlayerSession fields
# ====================================================================
SESSION_FIELDS = (
    '    # ---- Secret Realm (TASK 17) ----\n'
    '    realm_daily_count: int = 0                  # 오늘 비경 입장 횟수\n'
    '    realm_instance_id: int = 0                  # 현재 비경 인스턴스 (0=없음)\n'
)

# ====================================================================
# 4. Dispatch table entries
# ====================================================================
DISPATCH_ENTRIES = (
    '            MsgType.SECRET_REALM_ENTER: self._on_secret_realm_enter,\n'
    '            MsgType.SECRET_REALM_COMPLETE: self._on_secret_realm_complete,\n'
    '            MsgType.SECRET_REALM_FAIL: self._on_secret_realm_fail,\n'
)

# ====================================================================
# 5. Handler implementations
# ====================================================================
HANDLER_CODE = r'''
    # ---- Secret Realm System (TASK 17: MsgType 540-544) ----

    def _realm_grade(self, realm_type: str, score_value) -> str:
        """Calculate grade (S/A/B/C) based on realm_type and score.
        For trial/treasure: lower score = better (time/chest comparison).
        For training: lower fail_count = better.
        For wisdom: dict with time+hints.
        For fortune: higher luck_score = better.
        """
        rt = REALM_TYPES.get(realm_type)
        if not rt:
            return "C"
        criteria = rt["grade_criteria"]
        thresholds = rt["grade_thresholds"]

        if criteria == "clear_time":
            # score_value = seconds taken; lower is better
            for grade in ["S", "A", "B", "C"]:
                if score_value <= thresholds[grade]:
                    return grade
            return "C"
        elif criteria == "chests_opened":
            for grade in ["S", "A", "B", "C"]:
                if score_value >= thresholds[grade]:
                    return grade
            return "C"
        elif criteria == "fail_count":
            for grade in ["S", "A", "B", "C"]:
                if score_value <= thresholds[grade]:
                    return grade
            return "C"
        elif criteria == "luck_score":
            for grade in ["S", "A", "B", "C"]:
                if score_value >= thresholds[grade]:
                    return grade
            return "C"
        elif criteria == "clear_time_hints":
            # score_value = {"time": int, "hints": int}
            t = score_value.get("time", 999)
            h = score_value.get("hints", 99)
            for grade in ["S", "A", "B", "C"]:
                th = thresholds[grade]
                if t <= th["time"] and h <= th["hints"]:
                    return grade
            return "C"
        return "C"

    def _realm_rewards(self, realm_type: str, grade: str, multiplier: float = 1.0) -> dict:
        """Get reward dict for realm_type + grade, apply special multiplier to gold."""
        rt = REALM_TYPES.get(realm_type)
        if not rt:
            return {"gold": 100}
        rewards = dict(rt["rewards"].get(grade, rt["rewards"]["C"]))
        if "gold" in rewards:
            rewards["gold"] = int(rewards["gold"] * multiplier)
        return rewards

    def _check_special_realm(self) -> dict | None:
        """Check if current weather+time matches a special realm condition.
        Returns the special condition dict or None.
        Uses server weather/time state if available, else returns None.
        """
        weather = getattr(self, '_current_weather', 'clear')
        time_of_day = getattr(self, '_current_time_of_day', 'noon')
        for cond_name, cond in SPECIAL_REALM_CONDITIONS.items():
            if cond["weather"] == weather and cond["time"] == time_of_day:
                return cond
        return None

    async def _realm_spawn_portal(self, zone_id: int, realm_type: str = None, special: dict = None):
        """Spawn a secret realm portal in a zone. Broadcast to zone players."""
        global _REALM_PORTALS, _REALM_NEXT_ID
        import random, time as _time

        if zone_id in _REALM_PORTALS:
            return  # already has a portal

        if realm_type is None:
            realm_type = random.choice(REALM_TYPE_LIST)

        portal = {
            "realm_type": realm_type,
            "spawn_time": _time.time(),
            "special": special,
            "zone_id": zone_id,
        }
        _REALM_PORTALS[zone_id] = portal

        # Build spawn notification
        rt_idx = REALM_TYPE_LIST.index(realm_type) if realm_type in REALM_TYPE_LIST else 0
        is_special = 1 if special else 0
        multiplier_u16 = int((special["multiplier"] if special else 1.0) * 100)
        name_str = (special["name"] if special else REALM_TYPES[realm_type]["name"])
        name_bytes = name_str.encode('utf-8')[:50]
        import struct as _struct
        data = _struct.pack('<B B B H B', zone_id, rt_idx, is_special, multiplier_u16, len(name_bytes))
        data += name_bytes

        # Broadcast to zone
        for s in list(self.sessions.values()):
            if s.in_game and s.zone_id == zone_id:
                self._send(s, MsgType.SECRET_REALM_SPAWN, data)

    async def _on_secret_realm_enter(self, session, payload: bytes):
        """SECRET_REALM_ENTER(541) -> SECRET_REALM_ENTER_RESULT(542)
        Request: zone_id(u8) [+ auto_spawn(u8) — optional: 1=auto-create portal if none]
        Response: result(u8) + instance_id(u16) + realm_type(u8) + time_limit(u16) + is_special(u8) + multiplier(u16)
          result: 0=SUCCESS, 1=NO_PORTAL, 2=DAILY_LIMIT, 3=LEVEL_TOO_LOW, 4=ALREADY_IN_REALM, 5=PARTY_TOO_LARGE
        """
        global _REALM_PORTALS, _REALM_INSTANCES, _REALM_NEXT_ID
        import time as _time
        import random as _random

        if not session.in_game or len(payload) < 1:
            return

        zone_id = payload[0]
        auto_spawn = payload[1] if len(payload) >= 2 else 0

        def _send_fail(result_code):
            self._send(session, MsgType.SECRET_REALM_ENTER_RESULT,
                       struct.pack('<B H B H B H', result_code, 0, 0, 0, 0, 100))

        # Check already in realm
        if session.realm_instance_id > 0:
            _send_fail(4)  # ALREADY_IN_REALM
            return

        # Check level
        if session.stats.level < SECRET_REALM_UNLOCK_LEVEL:
            _send_fail(3)  # LEVEL_TOO_LOW
            return

        # Check daily limit
        if session.realm_daily_count >= SECRET_REALM_DAILY_LIMIT:
            _send_fail(2)  # DAILY_LIMIT
            return

        # Check portal exists (auto_spawn=1 creates one if missing)
        portal = _REALM_PORTALS.get(zone_id)
        if not portal:
            if auto_spawn == 1 and zone_id in SECRET_REALM_ELIGIBLE_ZONES:
                # Auto-spawn a random portal
                realm_type = _random.choice(REALM_TYPE_LIST)
                portal = {
                    "realm_type": realm_type,
                    "spawn_time": _time.time(),
                    "special": None,
                    "zone_id": zone_id,
                }
                _REALM_PORTALS[zone_id] = portal
            else:
                _send_fail(1)  # NO_PORTAL
                return

        # Check party size (solo or 2-man)
        party_id = getattr(session, 'party_id', 0)
        if party_id:
            party_members = [s for s in self.sessions.values()
                             if s.in_game and getattr(s, 'party_id', 0) == party_id]
            if len(party_members) > SECRET_REALM_MAX_PARTY:
                _send_fail(5)  # PARTY_TOO_LARGE
                return

        # Success — create instance
        realm_type = portal["realm_type"]
        special = portal.get("special")
        rt = REALM_TYPES.get(realm_type, REALM_TYPES["trial"])
        time_limit = rt["time_limit"]
        multiplier = special["multiplier"] if special else 1.0

        instance_id = _REALM_NEXT_ID
        _REALM_NEXT_ID += 1

        _REALM_INSTANCES[instance_id] = {
            "players": [session.entity_id],
            "realm_type": realm_type,
            "start_time": _time.time(),
            "special_multiplier": multiplier,
            "special": special,
        }

        session.realm_instance_id = instance_id
        session.realm_daily_count += 1

        # Remove portal from zone (consumed)
        _REALM_PORTALS.pop(zone_id, None)

        rt_idx = REALM_TYPE_LIST.index(realm_type) if realm_type in REALM_TYPE_LIST else 0
        is_special = 1 if special else 0
        mult_u16 = int(multiplier * 100)

        self._send(session, MsgType.SECRET_REALM_ENTER_RESULT,
                   struct.pack('<B H B H B H', 0, instance_id, rt_idx, time_limit, is_special, mult_u16))

    async def _on_secret_realm_complete(self, session, payload: bytes):
        """SECRET_REALM_COMPLETE(543)
        Request: score_value(u16) + extra_data(u8) — interpretation depends on realm_type
          trial/treasure: score_value=clear_time or chests_opened
          training: score_value=fail_count
          wisdom: score_value=clear_time, extra_data=hints_used
          fortune: score_value=luck_score
        Response: grade(u8: 0=S,1=A,2=B,3=C) + gold_reward(u32) + bonus_info_len(u8) + bonus_info(utf8)
        """
        if not session.in_game or len(payload) < 2:
            return

        instance_id = session.realm_instance_id
        if instance_id <= 0 or instance_id not in _REALM_INSTANCES:
            return

        inst = _REALM_INSTANCES[instance_id]
        realm_type = inst["realm_type"]
        multiplier = inst["special_multiplier"]

        score_value = struct.unpack('<H', payload[0:2])[0]
        extra_data = payload[2] if len(payload) >= 3 else 0

        # Build score for grading
        rt = REALM_TYPES.get(realm_type, REALM_TYPES["trial"])
        criteria = rt["grade_criteria"]
        if criteria == "clear_time_hints":
            score_input = {"time": score_value, "hints": extra_data}
        else:
            score_input = score_value

        grade = self._realm_grade(realm_type, score_input)
        rewards = self._realm_rewards(realm_type, grade, multiplier)

        # Apply gold reward
        gold_reward = rewards.get("gold", 0)
        session.gold = min(session.gold + gold_reward, 999999999)

        # Build bonus info string
        bonus_parts = []
        for k, v in rewards.items():
            if k != "gold":
                bonus_parts.append(f"{k}:{v}")
        bonus_str = ",".join(bonus_parts) if bonus_parts else ""
        bonus_bytes = bonus_str.encode('utf-8')[:100]

        grade_map = {"S": 0, "A": 1, "B": 2, "C": 3}
        grade_val = grade_map.get(grade, 3)

        self._send(session, MsgType.SECRET_REALM_COMPLETE,
                   struct.pack('<B I B', grade_val, gold_reward, len(bonus_bytes)) + bonus_bytes)

        # Cleanup
        session.realm_instance_id = 0
        _REALM_INSTANCES.pop(instance_id, None)

    async def _on_secret_realm_fail(self, session, payload: bytes):
        """SECRET_REALM_FAIL(544)
        Request: (empty)
        Response: echo SECRET_REALM_FAIL with consolation reward
          gold(u32) = 100 consolation
        """
        if not session.in_game:
            return

        instance_id = session.realm_instance_id
        if instance_id <= 0:
            return

        # Consolation reward
        consolation_gold = 100
        session.gold = min(session.gold + consolation_gold, 999999999)

        self._send(session, MsgType.SECRET_REALM_FAIL,
                   struct.pack('<I', consolation_gold))

        # Cleanup
        session.realm_instance_id = 0
        _REALM_INSTANCES.pop(instance_id, None)
'''

# ====================================================================
# 6. Test cases (4 tests)
# ====================================================================
TEST_CODE = r'''
    # ━━━ Test: SECRET_REALM_ENTER — 비경 입장 (레벨 부족) ━━━
    async def test_realm_enter_level_too_low():
        """레벨 20 미만 캐릭터 → LEVEL_TOO_LOW(3)."""
        c = await login_and_enter(port)
        # Default level is 1, need 20 — should fail
        await c.send(MsgType.SECRET_REALM_ENTER, struct.pack('<B', 1))
        msg_type, resp = await c.recv_expect(MsgType.SECRET_REALM_ENTER_RESULT)
        assert msg_type == MsgType.SECRET_REALM_ENTER_RESULT, f"Expected ENTER_RESULT, got {msg_type}"
        result = resp[0]
        assert result == 3, f"Expected LEVEL_TOO_LOW(3), got {result}"
        c.close()

    await test("SECRET_REALM_ENTER: 레벨 부족 → LEVEL_TOO_LOW", test_realm_enter_level_too_low())

    # ━━━ Test: SECRET_REALM_ENTER — 비경 입장 성공 (auto_spawn) ━━━
    async def test_realm_enter_success():
        """레벨업 후 auto_spawn=1로 입장 → SUCCESS(0) + instance_id."""
        c = await login_and_enter(port)
        # Level up to 20+
        await c.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 50000))
        await c.recv_all_packets(timeout=0.5)
        # Enter realm with auto_spawn=1
        await c.send(MsgType.SECRET_REALM_ENTER, struct.pack('<B B', 1, 1))
        msg_type, resp = await c.recv_expect(MsgType.SECRET_REALM_ENTER_RESULT)
        assert msg_type == MsgType.SECRET_REALM_ENTER_RESULT, f"Expected ENTER_RESULT, got {msg_type}"
        result = resp[0]
        assert result == 0, f"Expected SUCCESS(0), got {result}"
        instance_id = struct.unpack('<H', resp[1:3])[0]
        assert instance_id > 0, f"Expected instance_id > 0, got {instance_id}"
        c.close()

    await test("SECRET_REALM_ENTER: auto_spawn 입장 성공", test_realm_enter_success())

    # ━━━ Test: SECRET_REALM_COMPLETE — 비경 클리어 (등급 계산) ━━━
    async def test_realm_complete():
        """비경 클리어 → 등급(S/A/B/C) + 골드 보상."""
        c = await login_and_enter(port)
        await c.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 50000))
        await c.recv_all_packets(timeout=0.5)
        # Enter
        await c.send(MsgType.SECRET_REALM_ENTER, struct.pack('<B B', 1, 1))
        msg_type, resp = await c.recv_expect(MsgType.SECRET_REALM_ENTER_RESULT)
        assert msg_type == MsgType.SECRET_REALM_ENTER_RESULT
        assert resp[0] == 0, f"Expected SUCCESS, got {resp[0]}"
        realm_type_idx = resp[3]
        # Complete — send score 150 (for trial: S grade if <=180s)
        # For other types the grade varies, but we at least get a valid response
        await c.send(MsgType.SECRET_REALM_COMPLETE, struct.pack('<H B', 150, 0))
        msg_type2, resp2 = await c.recv_expect(MsgType.SECRET_REALM_COMPLETE)
        assert msg_type2 == MsgType.SECRET_REALM_COMPLETE, f"Expected COMPLETE, got {msg_type2}"
        grade = resp2[0]
        gold_reward = struct.unpack('<I', resp2[1:5])[0]
        assert grade in [0, 1, 2, 3], f"Grade must be 0-3 (S/A/B/C), got {grade}"
        assert gold_reward > 0, f"Expected gold_reward > 0, got {gold_reward}"
        c.close()

    await test("SECRET_REALM_COMPLETE: 비경 클리어 → 등급+골드", test_realm_complete())

    # ━━━ Test: SECRET_REALM_FAIL — 비경 실패 ━━━
    async def test_realm_fail():
        """비경 실패 → 위로 보상 100골드."""
        c = await login_and_enter(port)
        await c.send(MsgType.STAT_ADD_EXP, struct.pack('<I', 50000))
        await c.recv_all_packets(timeout=0.5)
        # Enter
        await c.send(MsgType.SECRET_REALM_ENTER, struct.pack('<B B', 1, 1))
        msg_type, resp = await c.recv_expect(MsgType.SECRET_REALM_ENTER_RESULT)
        assert msg_type == MsgType.SECRET_REALM_ENTER_RESULT
        assert resp[0] == 0, f"Expected SUCCESS, got {resp[0]}"
        # Fail
        await c.send(MsgType.SECRET_REALM_FAIL, b'')
        msg_type2, resp2 = await c.recv_expect(MsgType.SECRET_REALM_FAIL)
        assert msg_type2 == MsgType.SECRET_REALM_FAIL, f"Expected FAIL, got {msg_type2}"
        consolation_gold = struct.unpack('<I', resp2[:4])[0]
        assert consolation_gold == 100, f"Expected 100 consolation gold, got {consolation_gold}"
        c.close()

    await test("SECRET_REALM_FAIL: 비경 실패 → 위로 100골드", test_realm_fail())
'''


def patch_bridge():
    with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Full completion check
    if ('SECRET_REALM_SPAWN = 540' in content
            and 'def _on_secret_realm_enter' in content
            and 'REALM_TYPES' in content
            and 'def _on_secret_realm_complete' in content):
        print('[bridge] S055 already patched')
        return True

    changed = False

    # 1. MsgType -- after TOKEN_SHOP_BUY_RESULT = 473
    if 'SECRET_REALM_SPAWN' not in content:
        marker = '    TOKEN_SHOP_BUY_RESULT = 473'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + MSGTYPE_BLOCK + content[end:]
            changed = True
            print('[bridge] Added MsgType 540-544')
        else:
            print('[bridge] WARNING: Could not find MsgType insertion point (TOKEN_SHOP_BUY_RESULT = 473)')

    # 2. Data constants -- after TOKEN_SHOPS block (after the closing brace)
    if 'REALM_TYPES' not in content:
        marker = 'SILVER_SHOP_ITEMS'
        idx = content.find(marker)
        if idx >= 0:
            # Find end of SILVER_SHOP_ITEMS dict
            # Look for the closing brace + newline
            brace_count = 0
            start = content.index('{', idx)
            i = start
            while i < len(content):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        break
                i += 1
            nl = content.index('\n', i) + 1
            content = content[:nl] + DATA_CONSTANTS + content[nl:]
            changed = True
            print('[bridge] Added secret realm data constants')
        else:
            # Fallback: after _GW_NEXT_ID or CURRENCY_MAX
            marker2 = '_GW_NEXT_ID = 1'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                nl = content.index('\n', idx2) + 1
                content = content[:nl] + DATA_CONSTANTS + content[nl:]
                changed = True
                print('[bridge] Added secret realm data constants (fallback)')
            else:
                print('[bridge] WARNING: Could not find data constants insertion point')

    # 3. PlayerSession fields -- after guild_contribution field
    if 'realm_daily_count' not in content:
        marker = '    guild_contribution: int = 0'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + SESSION_FIELDS + content[end:]
            changed = True
            print('[bridge] Added PlayerSession realm fields')
        else:
            # Fallback: after pvp_token
            marker2 = '    pvp_token: int = 0'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                end = content.index('\n', idx2) + 1
                content = content[:end] + SESSION_FIELDS + content[end:]
                changed = True
                print('[bridge] Added PlayerSession realm fields (fallback)')
            else:
                print('[bridge] WARNING: Could not find session fields insertion point')

    # 4. Dispatch table -- after token_shop_buy dispatch
    if 'self._on_secret_realm_enter' not in content:
        marker = '            MsgType.TOKEN_SHOP_BUY: self._on_token_shop_buy,'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + DISPATCH_ENTRIES + content[end:]
            changed = True
            print('[bridge] Added dispatch table entries')
        else:
            # Fallback: after currency_query dispatch
            marker2 = '            MsgType.CURRENCY_QUERY: self._on_currency_query,'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                end = content.index('\n', idx2) + 1
                content = content[:end] + DISPATCH_ENTRIES + content[end:]
                changed = True
                print('[bridge] Added dispatch table entries (fallback)')
            else:
                print('[bridge] WARNING: Could not find dispatch table insertion point')

    # 5. Handler implementations -- before Sub-Currency handlers (or at end of handlers)
    if 'def _on_secret_realm_enter' not in content:
        marker = '    # ---- Sub-Currency / Token Shop (TASK 10: MsgType 468-473) ----'
        idx = content.find(marker)
        if idx < 0:
            # Fallback: before Battleground handlers
            marker = '    # ---- Battleground / Guild War (TASK 6: MsgType 430-435) ----'
            idx = content.find(marker)
        if idx >= 0:
            content = content[:idx] + HANDLER_CODE + '\n' + content[idx:]
            changed = True
            print('[bridge] Added secret realm handler implementations')
        else:
            print('[bridge] WARNING: Could not find handler insertion point')

    if changed:
        with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'[bridge] Written: {content.count(chr(10))} lines')

    # Verify
    checks = [
        'SECRET_REALM_SPAWN = 540', 'SECRET_REALM_ENTER = 541',
        'SECRET_REALM_ENTER_RESULT = 542', 'SECRET_REALM_COMPLETE = 543',
        'SECRET_REALM_FAIL = 544',
        'SECRET_REALM_UNLOCK_LEVEL', 'SECRET_REALM_DAILY_LIMIT',
        'REALM_TYPES', 'REALM_TYPE_LIST',
        'SPECIAL_REALM_CONDITIONS', '_REALM_PORTALS', '_REALM_INSTANCES',
        'def _realm_grade', 'def _realm_rewards',
        'def _on_secret_realm_enter', 'def _on_secret_realm_complete',
        'def _on_secret_realm_fail',
        'self._on_secret_realm_enter', 'self._on_secret_realm_complete',
        'self._on_secret_realm_fail',
        'realm_daily_count: int = 0', 'realm_instance_id: int = 0',
    ]
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[bridge] MISSING: {missing}')
        return False
    print('[bridge] S055 patched OK -- secret realm system')
    return True


def patch_test():
    with open(TEST_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'test_realm_enter_no_portal' in content and 'test_realm_fail' in content:
        print('[test] S055 already patched')
        return True

    # Update imports — add secret realm constants
    # Find the last closing ) of the import block
    old_import = (
        '    CURRENCY_MAX, TOKEN_SHOP_DUNGEON, TOKEN_SHOP_PVP, TOKEN_SHOP_GUILD,\n'
        '    TOKEN_SHOPS, SILVER_SHOP_ITEMS, DUNGEON_TOKEN_REWARDS,\n'
        '    PVP_TOKEN_WIN, PVP_TOKEN_LOSS\n'
        ')'
    )
    new_import = (
        '    CURRENCY_MAX, TOKEN_SHOP_DUNGEON, TOKEN_SHOP_PVP, TOKEN_SHOP_GUILD,\n'
        '    TOKEN_SHOPS, SILVER_SHOP_ITEMS, DUNGEON_TOKEN_REWARDS,\n'
        '    PVP_TOKEN_WIN, PVP_TOKEN_LOSS,\n'
        '    SECRET_REALM_UNLOCK_LEVEL, SECRET_REALM_DAILY_LIMIT,\n'
        '    REALM_TYPES, REALM_TYPE_LIST, SPECIAL_REALM_CONDITIONS\n'
        ')'
    )

    if old_import in content:
        content = content.replace(old_import, new_import, 1)
        print('[test] Updated imports with secret realm constants')
    else:
        print('[test] NOTE: Could not find expected import block -- imports may need manual update')

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

    checks = ['test_realm_enter_level_too_low', 'test_realm_enter_success',
              'test_realm_complete', 'test_realm_fail',
              'SECRET_REALM_ENTER', 'SECRET_REALM_COMPLETE',
              'SECRET_REALM_FAIL']
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[test] MISSING: {missing}')
        return False
    print('[test] S055 patched OK -- 4 secret realm tests')
    return True


if __name__ == '__main__':
    ok1 = patch_bridge()
    ok2 = patch_test()
    if ok1 and ok2:
        print('\nS055 all patches applied!')
    else:
        print('\nS055 PATCH FAILED!')
        sys.exit(1)
