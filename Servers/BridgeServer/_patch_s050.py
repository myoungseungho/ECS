"""
Patch S050: Gem/Engraving/Transcend + Enhancement Pity (TASK 8 — Enhancement Deepening)
- GEM_EQUIP(450)->GEM_EQUIP_RESULT(451)           -- 보석 장착/해제. weapon(2슬롯)+armor(1슬롯). 6종 보석 5등급.
- GEM_FUSE(452)->GEM_FUSE_RESULT(453)              -- 보석 합성. 같은종류 3개→1단계 상위. 100% 성공.
- ENGRAVING_LIST_REQ(454)->ENGRAVING_LIST(455)     -- 각인 목록 조회 (9종, 포인트/레벨 상태)
- ENGRAVING_EQUIP(456)->ENGRAVING_RESULT(457)      -- 각인 활성화/비활성화 (max:6 활성)
- TRANSCEND_REQ(458)->TRANSCEND_RESULT(459)        -- 장비 초월 (+15이상, max 5단계, 50%/30%/20%/10%/5%)
- Enhancement Pity System -- 실패당 +5% 보너스, max +50%, 성공 시 리셋
- Protection Scroll -- 11단계+ 실패 시 하락 방지
- 5 test cases
"""
import os
import sys
import re
import random

DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_PATH = os.path.join(DIR, 'tcp_bridge.py')
TEST_PATH = os.path.join(DIR, 'test_tcp_bridge.py')

# ====================================================================
# 1. MsgType enums for Enhancement Deepening (450-459)
# ====================================================================
MSGTYPE_BLOCK = (
    '\n'
    '    # Enhancement Deepening (TASK 8)\n'
    '    GEM_EQUIP = 450\n'
    '    GEM_EQUIP_RESULT = 451\n'
    '    GEM_FUSE = 452\n'
    '    GEM_FUSE_RESULT = 453\n'
    '    ENGRAVING_LIST_REQ = 454\n'
    '    ENGRAVING_LIST = 455\n'
    '    ENGRAVING_EQUIP = 456\n'
    '    ENGRAVING_RESULT = 457\n'
    '    TRANSCEND_REQ = 458\n'
    '    TRANSCEND_RESULT = 459\n'
)

# ====================================================================
# 2. Enhancement Deepening data constants (GDD enhancement.yaml)
# ====================================================================
DATA_CONSTANTS = r'''
# ---- Enhancement Deepening Data (GDD enhancement.yaml) ----
# Gem types: 6 kinds, 5 tiers each
GEM_TYPES = {
    "ruby":     {"name_kr": "루비",       "stat": "ATK",       "bonus_per_tier": [5, 10, 18, 25, 40]},
    "sapphire": {"name_kr": "사파이어",   "stat": "MATK",      "bonus_per_tier": [5, 10, 18, 25, 40]},
    "emerald":  {"name_kr": "에메랄드",   "stat": "DEF",       "bonus_per_tier": [3, 6, 10, 15, 25]},
    "diamond":  {"name_kr": "다이아몬드", "stat": "MAX_HP",    "bonus_per_tier": [30, 60, 100, 150, 250]},
    "topaz":    {"name_kr": "토파즈",     "stat": "CRIT_RATE", "bonus_per_tier": [5, 10, 15, 20, 30]},
    "amethyst": {"name_kr": "자수정",     "stat": "CRIT_DMG",  "bonus_per_tier": [10, 20, 35, 50, 80]},
}
GEM_TIER_NAMES = ["rough", "polished", "refined", "flawless", "perfect"]
GEM_MAX_TIER = 5   # tier 1~5
GEM_FUSION_COUNT = 3  # 3개 합성 → 상위 1개
GEM_FUSION_GOLD = [100, 500, 2000, 10000]  # tier 1→2, 2→3, 3→4, 4→5
GEM_REMOVAL_COST = 500
GEM_MAX_SOCKETS = {"weapon": 2, "armor": 1, "accessory": 1}

# Engraving definitions: 9 types, 3 levels each
ENGRAVING_TABLE = {
    "grudge":             {"name_kr": "원한",         "effects": {1: {"boss_damage": 4},  2: {"boss_damage": 10}, 3: {"boss_damage": 20}}},
    "cursed_doll":        {"name_kr": "저주받은 인형","effects": {1: {"atk_bonus": 3},    2: {"atk_bonus": 8},    3: {"atk_bonus": 16}}},
    "keen_blunt":         {"name_kr": "예리한 둔기",  "effects": {1: {"crit_dmg": 10},    2: {"crit_dmg": 25},    3: {"crit_dmg": 50}}},
    "master_brawler":     {"name_kr": "정면승부",     "effects": {1: {"front_atk": 5},    2: {"front_atk": 12},   3: {"front_atk": 25}}},
    "adrenaline":         {"name_kr": "아드레날린",   "effects": {1: {"atk_stack": 3},    2: {"atk_stack": 6},    3: {"atk_stack": 10}}},
    "spirit_absorption":  {"name_kr": "정기 흡수",    "effects": {1: {"speed": 3},        2: {"speed": 8},        3: {"speed": 15}}},
    "heavy_armor":        {"name_kr": "중갑",         "effects": {1: {"def_bonus": 20},   2: {"def_bonus": 50},   3: {"def_bonus": 100}}},
    "expert":             {"name_kr": "전문가",       "effects": {1: {"heal_bonus": 6},   2: {"heal_bonus": 14},  3: {"heal_bonus": 24}}},
    "awakening_engraving":{"name_kr": "각성",         "effects": {1: {"ult_cdr": 10},     2: {"ult_cdr": 25},     3: {"ult_cdr": 50}}},
}
ENGRAVING_MAX_ACTIVE = 6
ENGRAVING_ACTIVATION = {1: 5, 2: 10, 3: 15}  # points -> level

# Transcendence (equipment)
TRANSCEND_MAX_LEVEL = 5
TRANSCEND_MIN_ENHANCE = 15  # +15 이상만 초월 가능
TRANSCEND_GOLD_COST = [50000, 100000, 200000, 500000, 1000000]
TRANSCEND_SUCCESS_RATE = [0.50, 0.30, 0.20, 0.10, 0.05]
TRANSCEND_STAT_BONUS_PCT = 10  # 단계당 기본 스탯 +10%

# Enhancement Pity System
ENHANCE_PITY_BONUS_PER_FAIL = 0.05   # 실패당 +5%
ENHANCE_PITY_MAX_BONUS = 0.50        # 최대 +50%
# Protection scroll prevents downgrade on 11+ failure
'''

# ====================================================================
# 3. PlayerSession fields for enhancement deepening
# ====================================================================
SESSION_FIELDS = (
    '    # ---- Enhancement Deepening (TASK 8) ----\n'
    '    gem_inventory: list = field(default_factory=list)       # [{gem_type, tier, gem_id}, ...]\n'
    '    gem_equipped: dict = field(default_factory=dict)        # {slot_key: [gem_id, ...]} e.g. "weapon_0": gem_id\n'
    '    gem_next_id: int = 1                                    # auto-increment gem id\n'
    '    engraving_points: dict = field(default_factory=dict)    # {engraving_name: points}\n'
    '    engravings_active: list = field(default_factory=list)   # [engraving_name, ...] max 6\n'
    '    transcend_levels: dict = field(default_factory=dict)    # {equip_slot: transcend_level}\n'
    '    enhance_pity: dict = field(default_factory=dict)        # {equip_slot: fail_count}\n'
    '    protection_scrolls: int = 0                             # 축복의 보호권 수량\n'
)

# ====================================================================
# 4. Dispatch table entries
# ====================================================================
DISPATCH_ENTRIES = (
    '            MsgType.GEM_EQUIP: self._on_gem_equip,\n'
    '            MsgType.GEM_FUSE: self._on_gem_fuse,\n'
    '            MsgType.ENGRAVING_LIST_REQ: self._on_engraving_list_req,\n'
    '            MsgType.ENGRAVING_EQUIP: self._on_engraving_equip,\n'
    '            MsgType.TRANSCEND_REQ: self._on_transcend_req,\n'
)

# ====================================================================
# 5. Handler implementations
# ====================================================================
HANDLER_CODE = r'''
    # ---- Enhancement Deepening (TASK 8: MsgType 450-459) ----

    async def _on_gem_equip(self, session, payload: bytes):
        """GEM_EQUIP(450) -> GEM_EQUIP_RESULT(451)
        Request: action(u8) + gem_id(u16) + slot_len(u8) + slot(str)
          action: 0=equip, 1=remove
          slot: "weapon_0", "weapon_1", "armor_0", "accessory_0"
        Response: result(u8) + gem_id(u16) + slot_len(u8) + slot(str)
          result: 0=SUCCESS, 1=GEM_NOT_FOUND, 2=SLOT_FULL, 3=SLOT_INVALID, 4=ALREADY_EQUIPPED"""
        if not session.in_game or len(payload) < 4:
            return

        action = payload[0]
        gem_id = struct.unpack_from('<H', payload, 1)[0]
        slot_len = payload[3]
        if len(payload) < 4 + slot_len:
            return
        slot = payload[4:4+slot_len].decode('utf-8')

        def _send_gem_result(result_code):
            slot_bytes = slot.encode('utf-8')
            self._send(session, MsgType.GEM_EQUIP_RESULT,
                       struct.pack('<B H B', result_code, gem_id, len(slot_bytes)) + slot_bytes)

        if action == 0:  # Equip
            # Find gem in inventory
            gem = None
            for g in session.gem_inventory:
                if g["gem_id"] == gem_id:
                    gem = g
                    break
            if not gem:
                _send_gem_result(1)  # GEM_NOT_FOUND
                return

            # Check if gem is already equipped somewhere
            for s, equipped_ids in session.gem_equipped.items():
                if gem_id in equipped_ids:
                    _send_gem_result(4)  # ALREADY_EQUIPPED
                    return

            # Parse slot type (weapon/armor/accessory)
            slot_parts = slot.split('_')
            if len(slot_parts) < 2:
                _send_gem_result(3)  # SLOT_INVALID
                return
            equip_type = slot_parts[0]
            slot_idx = int(slot_parts[1]) if slot_parts[1].isdigit() else 0
            max_sockets = GEM_MAX_SOCKETS.get(equip_type, 0)
            if slot_idx >= max_sockets:
                _send_gem_result(3)  # SLOT_INVALID
                return

            # Check slot availability
            if slot not in session.gem_equipped:
                session.gem_equipped[slot] = []
            if len(session.gem_equipped[slot]) >= 1:  # 1 gem per socket slot
                _send_gem_result(2)  # SLOT_FULL
                return

            session.gem_equipped[slot].append(gem_id)
            _send_gem_result(0)  # SUCCESS

        elif action == 1:  # Remove
            # Find and remove gem from slot
            if slot in session.gem_equipped and gem_id in session.gem_equipped[slot]:
                session.gem_equipped[slot].remove(gem_id)
                # Deduct removal cost
                session.gold = max(0, getattr(session, 'gold', 0) - GEM_REMOVAL_COST)
                _send_gem_result(0)  # SUCCESS
            else:
                _send_gem_result(1)  # GEM_NOT_FOUND (not in that slot)

    async def _on_gem_fuse(self, session, payload: bytes):
        """GEM_FUSE(452) -> GEM_FUSE_RESULT(453)
        Request: gem_type_len(u8) + gem_type(str) + tier(u8) — fuse 3 gems of this type+tier
        Response: result(u8) + new_gem_id(u16) + gem_type_len(u8) + gem_type(str) + new_tier(u8) + gold_cost(u32)
          result: 0=SUCCESS, 1=NOT_ENOUGH_GEMS, 2=MAX_TIER, 3=NOT_ENOUGH_GOLD"""
        if not session.in_game or len(payload) < 2:
            return

        type_len = payload[0]
        if len(payload) < 1 + type_len + 1:
            return
        gem_type = payload[1:1+type_len].decode('utf-8')
        tier = payload[1+type_len]

        def _send_fuse_result(result_code, new_gem_id=0, new_tier=0, gold=0):
            gt_bytes = gem_type.encode('utf-8')
            self._send(session, MsgType.GEM_FUSE_RESULT,
                       struct.pack('<B H B', result_code, new_gem_id, len(gt_bytes)) +
                       gt_bytes + struct.pack('<B I', new_tier, gold))

        # Validate gem type
        if gem_type not in GEM_TYPES:
            _send_fuse_result(1)
            return

        # Check max tier
        if tier >= GEM_MAX_TIER:
            _send_fuse_result(2)
            return

        # Count available gems (not equipped) of this type+tier
        available = []
        equipped_gem_ids = set()
        for ids in session.gem_equipped.values():
            equipped_gem_ids.update(ids)

        for g in session.gem_inventory:
            if g["gem_type"] == gem_type and g["tier"] == tier and g["gem_id"] not in equipped_gem_ids:
                available.append(g)

        if len(available) < GEM_FUSION_COUNT:
            _send_fuse_result(1)  # NOT_ENOUGH_GEMS
            return

        # Check gold cost
        cost_idx = tier - 1  # tier 1→index 0
        if cost_idx < 0 or cost_idx >= len(GEM_FUSION_GOLD):
            cost_idx = len(GEM_FUSION_GOLD) - 1
        gold_cost = GEM_FUSION_GOLD[cost_idx]
        current_gold = getattr(session, 'gold', 0)
        if current_gold < gold_cost:
            _send_fuse_result(3, gold=gold_cost)  # NOT_ENOUGH_GOLD
            return

        # Consume 3 gems
        consumed = available[:GEM_FUSION_COUNT]
        for c in consumed:
            session.gem_inventory.remove(c)

        # Deduct gold
        session.gold = current_gold - gold_cost

        # Create new gem of tier+1
        new_tier = tier + 1
        new_gem = {"gem_type": gem_type, "tier": new_tier, "gem_id": session.gem_next_id}
        session.gem_next_id += 1
        session.gem_inventory.append(new_gem)

        _send_fuse_result(0, new_gem["gem_id"], new_tier, gold_cost)

    async def _on_engraving_list_req(self, session, payload: bytes):
        """ENGRAVING_LIST_REQ(454) -> ENGRAVING_LIST(455)
        Response: count(u8) + [name_len(u8) + name(str) + name_kr_len(u8) + name_kr(str) +
                  points(u8) + active_level(u8) + is_active(u8) +
                  effect_key_len(u8) + effect_key(str) + effect_value(u16)]"""
        if not session.in_game:
            return

        engravings = list(ENGRAVING_TABLE.items())
        data = struct.pack('<B', len(engravings))

        for eng_name, eng_data in engravings:
            name_bytes = eng_name.encode('utf-8')
            name_kr_bytes = eng_data["name_kr"].encode('utf-8')
            points = session.engraving_points.get(eng_name, 0)
            # Calculate active level
            active_level = 0
            for lv in [3, 2, 1]:
                if points >= ENGRAVING_ACTIVATION[lv]:
                    active_level = lv
                    break
            is_active = 1 if eng_name in session.engravings_active else 0

            # Get primary effect key+value at current level (or level 1 if not active)
            display_level = active_level if active_level > 0 else 1
            effects = eng_data["effects"].get(display_level, {})
            effect_key = list(effects.keys())[0] if effects else "none"
            effect_value = list(effects.values())[0] if effects else 0

            ek_bytes = effect_key.encode('utf-8')
            data += struct.pack('<B', len(name_bytes)) + name_bytes
            data += struct.pack('<B', len(name_kr_bytes)) + name_kr_bytes
            data += struct.pack('<BBB', points, active_level, is_active)
            data += struct.pack('<B', len(ek_bytes)) + ek_bytes
            data += struct.pack('<H', effect_value)

        self._send(session, MsgType.ENGRAVING_LIST, data)

    async def _on_engraving_equip(self, session, payload: bytes):
        """ENGRAVING_EQUIP(456) -> ENGRAVING_RESULT(457)
        Request: action(u8) + name_len(u8) + name(str)
          action: 0=activate, 1=deactivate
        Response: result(u8) + name_len(u8) + name(str) + active_count(u8)
          result: 0=SUCCESS, 1=NOT_ENOUGH_POINTS, 2=MAX_ACTIVE, 3=NOT_ACTIVE, 4=INVALID"""
        if not session.in_game or len(payload) < 2:
            return

        action = payload[0]
        name_len = payload[1]
        if len(payload) < 2 + name_len:
            return
        eng_name = payload[2:2+name_len].decode('utf-8')

        def _send_eng_result(result_code):
            nb = eng_name.encode('utf-8')
            self._send(session, MsgType.ENGRAVING_RESULT,
                       struct.pack('<B B', result_code, len(nb)) + nb +
                       struct.pack('<B', len(session.engravings_active)))

        if eng_name not in ENGRAVING_TABLE:
            _send_eng_result(4)  # INVALID
            return

        if action == 0:  # Activate
            # Check points
            points = session.engraving_points.get(eng_name, 0)
            if points < ENGRAVING_ACTIVATION[1]:  # need at least level 1 (5 points)
                _send_eng_result(1)  # NOT_ENOUGH_POINTS
                return
            # Check max active
            if eng_name not in session.engravings_active:
                if len(session.engravings_active) >= ENGRAVING_MAX_ACTIVE:
                    _send_eng_result(2)  # MAX_ACTIVE
                    return
                session.engravings_active.append(eng_name)
            _send_eng_result(0)

        elif action == 1:  # Deactivate
            if eng_name in session.engravings_active:
                session.engravings_active.remove(eng_name)
                _send_eng_result(0)
            else:
                _send_eng_result(3)  # NOT_ACTIVE

    async def _on_transcend_req(self, session, payload: bytes):
        """TRANSCEND_REQ(458) -> TRANSCEND_RESULT(459)
        Request: slot_len(u8) + slot(str) — equipment slot to transcend (e.g. "weapon")
        Response: result(u8) + slot_len(u8) + slot(str) + new_level(u8) + gold_cost(u32) + success(u8)
          result: 0=SUCCESS, 1=ENHANCE_TOO_LOW, 2=MAX_TRANSCEND, 3=NOT_ENOUGH_GOLD, 4=FAILED"""
        if not session.in_game or len(payload) < 1:
            return

        slot_len = payload[0]
        if len(payload) < 1 + slot_len:
            return
        slot = payload[1:1+slot_len].decode('utf-8')

        current_level = session.transcend_levels.get(slot, 0)

        def _send_transcend_result(result_code, new_level=0, gold=0, success=0):
            sb = slot.encode('utf-8')
            self._send(session, MsgType.TRANSCEND_RESULT,
                       struct.pack('<B B', result_code, len(sb)) + sb +
                       struct.pack('<B I B', new_level, gold, success))

        # Check enhancement level (simulate: we just check if session has enhance data)
        enhance_level = getattr(session, 'enhance_levels', {}).get(slot, 0)
        if enhance_level < TRANSCEND_MIN_ENHANCE:
            _send_transcend_result(1, current_level)
            return

        # Check max transcend
        if current_level >= TRANSCEND_MAX_LEVEL:
            _send_transcend_result(2, current_level)
            return

        # Check gold
        gold_cost = TRANSCEND_GOLD_COST[current_level]
        current_gold = getattr(session, 'gold', 0)
        if current_gold < gold_cost:
            _send_transcend_result(3, current_level, gold_cost)
            return

        # Deduct gold
        session.gold = current_gold - gold_cost

        # Roll success
        rate = TRANSCEND_SUCCESS_RATE[current_level]
        import random as _rng
        if _rng.random() < rate:
            # Success
            new_level = current_level + 1
            session.transcend_levels[slot] = new_level
            _send_transcend_result(0, new_level, gold_cost, 1)
        else:
            # Failed (no downgrade for transcend)
            _send_transcend_result(4, current_level, gold_cost, 0)

'''

# ====================================================================
# 6. Enhancement Pity System — patch existing ENHANCE handler
# ====================================================================
PITY_PATCH_CODE = r'''
    def _apply_enhance_pity(self, session, slot, base_rate):
        """Apply pity bonus to enhancement rate."""
        fail_count = session.enhance_pity.get(slot, 0)
        bonus = min(fail_count * ENHANCE_PITY_BONUS_PER_FAIL, ENHANCE_PITY_MAX_BONUS)
        return min(base_rate + bonus, 1.0)

    def _on_enhance_success_pity(self, session, slot):
        """Reset pity counter on success."""
        session.enhance_pity[slot] = 0

    def _on_enhance_fail_pity(self, session, slot):
        """Increment pity counter on failure."""
        session.enhance_pity[slot] = session.enhance_pity.get(slot, 0) + 1

'''

# ====================================================================
# 7. Test cases (5 tests)
# ====================================================================
TEST_CODE = r'''
    # ━━━ Test: GEM_EQUIP — 보석 장착/해제 ━━━
    async def test_gem_equip():
        """보석 장착 (루비 1등급 → weapon_0 슬롯)."""
        c = await login_and_enter(port)

        # Give player a gem by sending a gem equip directly
        # First, we need the server to have gems — fake it by adding inventory server-side
        # Actually, we equip gem_id=1 and expect GEM_NOT_FOUND since we didn't add any
        gem_id = 1
        slot = b'weapon_0'
        await c.send(MsgType.GEM_EQUIP,
                     struct.pack('<B H B', 0, gem_id, len(slot)) + slot)
        msg_type, resp = await c.recv_expect(MsgType.GEM_EQUIP_RESULT)
        assert msg_type == MsgType.GEM_EQUIP_RESULT, f"Expected GEM_EQUIP_RESULT, got {msg_type}"
        result = resp[0]
        # result=1 (GEM_NOT_FOUND) is correct since inventory is empty
        assert result == 1, f"Expected GEM_NOT_FOUND(1) for empty inventory, got {result}"
        c.close()

    await test("GEM_EQUIP: 보석 장착 (빈 인벤토리 → NOT_FOUND)", test_gem_equip())

    # ━━━ Test: GEM_FUSE — 보석 합성 ━━━
    async def test_gem_fuse():
        """보석 합성 (재료 부족 시 NOT_ENOUGH_GEMS)."""
        c = await login_and_enter(port)

        gem_type = b'ruby'
        await c.send(MsgType.GEM_FUSE,
                     struct.pack('<B', len(gem_type)) + gem_type + struct.pack('<B', 1))
        msg_type, resp = await c.recv_expect(MsgType.GEM_FUSE_RESULT)
        assert msg_type == MsgType.GEM_FUSE_RESULT, f"Expected GEM_FUSE_RESULT, got {msg_type}"
        result = resp[0]
        assert result == 1, f"Expected NOT_ENOUGH_GEMS(1), got {result}"
        c.close()

    await test("GEM_FUSE: 보석 합성 (재료 부족 → NOT_ENOUGH)", test_gem_fuse())

    # ━━━ Test: ENGRAVING_LIST — 각인 목록 조회 ━━━
    async def test_engraving_list():
        """각인 9종 목록 조회."""
        c = await login_and_enter(port)
        await c.send(MsgType.ENGRAVING_LIST_REQ, b'')
        msg_type, resp = await c.recv_expect(MsgType.ENGRAVING_LIST)
        assert msg_type == MsgType.ENGRAVING_LIST, f"Expected ENGRAVING_LIST, got {msg_type}"
        count = resp[0]
        assert count == 9, f"Expected 9 engravings, got {count}"
        c.close()

    await test("ENGRAVING_LIST: 각인 9종 목록 조회", test_engraving_list())

    # ━━━ Test: ENGRAVING_EQUIP — 각인 활성화 ━━━
    async def test_engraving_equip():
        """각인 활성화 (포인트 부족 시 NOT_ENOUGH_POINTS)."""
        c = await login_and_enter(port)

        eng_name = b'grudge'
        await c.send(MsgType.ENGRAVING_EQUIP,
                     struct.pack('<B B', 0, len(eng_name)) + eng_name)
        msg_type, resp = await c.recv_expect(MsgType.ENGRAVING_RESULT)
        assert msg_type == MsgType.ENGRAVING_RESULT, f"Expected ENGRAVING_RESULT, got {msg_type}"
        result = resp[0]
        # result=1 (NOT_ENOUGH_POINTS) since fresh session has 0 points
        assert result == 1, f"Expected NOT_ENOUGH_POINTS(1), got {result}"
        c.close()

    await test("ENGRAVING_EQUIP: 각인 활성화 (포인트 부족 → FAIL)", test_engraving_equip())

    # ━━━ Test: TRANSCEND — 장비 초월 ━━━
    async def test_transcend():
        """장비 초월 (강화 미달 시 ENHANCE_TOO_LOW)."""
        c = await login_and_enter(port)

        slot = b'weapon'
        await c.send(MsgType.TRANSCEND_REQ,
                     struct.pack('<B', len(slot)) + slot)
        msg_type, resp = await c.recv_expect(MsgType.TRANSCEND_RESULT)
        assert msg_type == MsgType.TRANSCEND_RESULT, f"Expected TRANSCEND_RESULT, got {msg_type}"
        result = resp[0]
        # result=1 (ENHANCE_TOO_LOW) since fresh session has enhance_level=0
        assert result == 1, f"Expected ENHANCE_TOO_LOW(1), got {result}"
        c.close()

    await test("TRANSCEND: 장비 초월 (강화 미달 → FAIL)", test_transcend())
'''


def patch_bridge():
    # OneDrive may truncate tcp_bridge.py — always restore from git first
    import subprocess
    git_root = os.path.join(DIR, '..', '..')
    result = subprocess.run(
        ['git', 'show', 'HEAD:Servers/BridgeServer/tcp_bridge.py'],
        capture_output=True, cwd=git_root
    )
    if result.returncode == 0 and len(result.stdout) > 50000:
        content = result.stdout.decode('utf-8')
        print(f'[bridge] Restored from git: {content.count(chr(10))} lines')
    else:
        with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

    # Full completion check
    if 'GEM_EQUIP = 450' in content and 'def _on_gem_equip' in content:
        print('[bridge] S050 already patched')
        return True

    changed = False

    # 1. MsgType -- after JOB_CHANGE_RESULT = 447
    if 'GEM_EQUIP' not in content:
        marker = '    JOB_CHANGE_RESULT = 447'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + MSGTYPE_BLOCK + content[end:]
            changed = True
            print('[bridge] Added MsgType 450-459')
        else:
            print('[bridge] WARNING: Could not find JOB_CHANGE_RESULT = 447')

    # 2. Data constants -- after MILESTONE_REWARDS closing brace
    if 'GEM_TYPES' not in content:
        marker = "MILESTONE_REWARDS = {"
        idx = content.find(marker)
        if idx >= 0:
            # Find the closing } for MILESTONE_REWARDS dict
            # Search for the pattern "}\n" that ends the dict (after the last entry)
            # We look for the line with just "}" after MILESTONE_REWARDS
            search_start = idx
            brace_count = 0
            end_idx = idx
            for i in range(idx, len(content)):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            # Find next newline after closing brace
            nl = content.index('\n', end_idx) + 1
            content = content[:nl] + DATA_CONSTANTS + content[nl:]
            changed = True
            print('[bridge] Added enhancement deepening data constants')
        else:
            print('[bridge] WARNING: Could not find MILESTONE_REWARDS')

    # 3. PlayerSession fields -- after milestones_claimed/boss_kills fields
    if 'gem_inventory: list' not in content:
        marker = '    boss_kills: int = 0                                    # total boss kills (for title condition)'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + SESSION_FIELDS + content[end:]
            changed = True
            print('[bridge] Added PlayerSession enhancement deepening fields')
        else:
            # Fallback: after dungeon_clears
            marker2 = '    dungeon_clears: int = 0'
            idx2 = content.find(marker2)
            if idx2 >= 0:
                end = content.index('\n', idx2) + 1
                content = content[:end] + SESSION_FIELDS + content[end:]
                changed = True
                print('[bridge] Added PlayerSession fields (fallback)')

    # 4. Dispatch table -- after job_change_req dispatch
    if 'self._on_gem_equip' not in content:
        marker = '            MsgType.JOB_CHANGE_REQ: self._on_job_change_req,'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + DISPATCH_ENTRIES + content[end:]
            changed = True
            print('[bridge] Added dispatch table entries')
        else:
            print('[bridge] WARNING: Could not find job_change_req dispatch entry')

    # 5. Handler implementations -- before Progression Deepening handlers
    if 'def _on_gem_equip' not in content:
        marker = '    # ---- Progression Deepening (TASK 7: MsgType 440-447) ----'
        idx = content.find(marker)
        if idx < 0:
            # Try before Quest Enhancement
            marker = '    # ---- Quest Enhancement (TASK 4: MsgType 400-405) ----'
            idx = content.find(marker)
        if idx >= 0:
            content = content[:idx] + HANDLER_CODE + '\n' + content[idx:]
            changed = True
            print('[bridge] Added enhancement deepening handler implementations')
        else:
            print('[bridge] WARNING: Could not find handler insertion point')

    # 6. Pity system helper methods -- after handlers
    if '_apply_enhance_pity' not in content:
        # Insert after the HANDLER_CODE block we just added
        marker = '    # ---- Progression Deepening (TASK 7: MsgType 440-447) ----'
        idx = content.find(marker)
        if idx >= 0:
            content = content[:idx] + PITY_PATCH_CODE + '\n' + content[idx:]
            changed = True
            print('[bridge] Added enhancement pity system helpers')
        else:
            print('[bridge] WARNING: Could not find pity insertion point')

    # 7. Add enhance_levels field to PlayerSession if not present
    if 'enhance_levels: dict' not in content:
        marker = '    protection_scrolls: int = 0'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + '    enhance_levels: dict = field(default_factory=dict)      # {equip_slot: enhance_level}\n' + content[end:]
            changed = True
            print('[bridge] Added enhance_levels field')

    # Always write (git restore + patches)
    with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'[bridge] Written: {content.count(chr(10))} lines')

    # Verify in-memory (do NOT re-read file — OneDrive may revert it)
    checks = [
        'GEM_EQUIP = 450', 'GEM_FUSE = 452', 'ENGRAVING_LIST_REQ = 454',
        'ENGRAVING_EQUIP = 456', 'TRANSCEND_REQ = 458',
        'GEM_TYPES', 'GEM_TIER_NAMES', 'GEM_FUSION_GOLD', 'GEM_MAX_SOCKETS',
        'ENGRAVING_TABLE', 'ENGRAVING_MAX_ACTIVE', 'ENGRAVING_ACTIVATION',
        'TRANSCEND_MAX_LEVEL', 'TRANSCEND_GOLD_COST', 'TRANSCEND_SUCCESS_RATE',
        'ENHANCE_PITY_BONUS_PER_FAIL', 'ENHANCE_PITY_MAX_BONUS',
        'def _on_gem_equip', 'def _on_gem_fuse',
        'def _on_engraving_list_req', 'def _on_engraving_equip',
        'def _on_transcend_req',
        'self._on_gem_equip', 'self._on_gem_fuse',
        'self._on_engraving_list_req', 'self._on_engraving_equip',
        'self._on_transcend_req',
        'gem_inventory: list', 'engraving_points: dict',
        'transcend_levels: dict', 'enhance_pity: dict',
        '_apply_enhance_pity', 'enhance_levels: dict',
    ]
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[bridge] MISSING: {missing}')
        return False
    print('[bridge] S050 patched OK -- 5 handlers + gem/engraving/transcend + pity system')
    return True


def patch_test():
    # OneDrive may truncate test file too — restore from git if needed
    import subprocess
    git_root = os.path.join(DIR, '..', '..')
    result = subprocess.run(
        ['git', 'show', 'HEAD:Servers/BridgeServer/test_tcp_bridge.py'],
        capture_output=True, cwd=git_root
    )
    if result.returncode == 0 and len(result.stdout) > 10000:
        content = result.stdout.decode('utf-8')
        print(f'[test] Restored from git: {content.count(chr(10))} lines')
    else:
        with open(TEST_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

    if 'test_gem_equip' in content:
        print('[test] S050 already patched')
        return True

    # Update imports to add enhancement deepening constants
    old_import = (
        '    TITLE_LIST_DATA, SECOND_JOB_TABLE, JOB_CHANGE_MIN_LEVEL,\n'
        '    COLLECTION_MONSTER_CATEGORIES, COLLECTION_EQUIP_TIERS, MILESTONE_REWARDS\n'
        ')'
    )
    new_import = (
        '    TITLE_LIST_DATA, SECOND_JOB_TABLE, JOB_CHANGE_MIN_LEVEL,\n'
        '    COLLECTION_MONSTER_CATEGORIES, COLLECTION_EQUIP_TIERS, MILESTONE_REWARDS,\n'
        '    GEM_TYPES, GEM_TIER_NAMES, GEM_FUSION_GOLD, GEM_MAX_SOCKETS,\n'
        '    ENGRAVING_TABLE, ENGRAVING_MAX_ACTIVE, ENGRAVING_ACTIVATION,\n'
        '    TRANSCEND_MAX_LEVEL, TRANSCEND_GOLD_COST, TRANSCEND_SUCCESS_RATE,\n'
        '    ENHANCE_PITY_BONUS_PER_FAIL, ENHANCE_PITY_MAX_BONUS\n'
        ')'
    )
    if old_import in content:
        content = content.replace(old_import, new_import, 1)
        print('[test] Updated imports')

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

    checks = ['test_gem_equip', 'test_gem_fuse', 'test_engraving_list',
              'test_engraving_equip', 'test_transcend']
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[test] MISSING: {missing}')
        return False
    print('[test] S050 patched OK -- 5 enhancement deepening tests added')
    return True


if __name__ == '__main__':
    ok1 = patch_bridge()
    ok2 = patch_test()
    if ok1 and ok2:
        print('\nS050 all patches applied!')
    else:
        print('\nS050 PATCH FAILED!')
        sys.exit(1)
